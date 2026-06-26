from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from ai_sdr.config import REPORTS_DIR
from ai_sdr.llm.groq_client import complete_json
from ai_sdr.memory.lead_memory import PineconeLeadMemory
from ai_sdr.memory.search import build_metadata_filter
from ai_sdr.schemas import ResearchProfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a lead research profile.")
    parser.add_argument("query", help="Natural-language lead research query.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of lead-memory records to retrieve before choosing the best match.",
    )
    parser.add_argument("--region", help="Only retrieve leads from this normalized region.")
    parser.add_argument("--industry", help="Only retrieve leads from this industry.")
    parser.add_argument("--seniority", help="Only retrieve leads with this seniority.")
    parser.add_argument(
        "--min-icp-score",
        type=int,
        help="Only retrieve leads with an ICP score greater than or equal to this value.",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the profile under reports/research_profiles/.",
    )
    return parser.parse_args()


def _hit_fields(hit: Any) -> dict[str, Any]:
    fields = getattr(hit, "fields", None)
    return fields if isinstance(fields, dict) else {}


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "research-profile"


def generate_profile_from_hit(hit: Any) -> ResearchProfile:
    """Use Groq to turn retrieved lead memory into a research profile."""
    fields = _hit_fields(hit)
    memory_text = str(fields.get("text", ""))
    lead_id = str(fields.get("lead_id") or getattr(hit, "id", "unknown"))
    full_name = str(fields.get("full_name") or "Unknown lead")
    title = str(fields.get("title") or "Unknown title")
    company = str(fields.get("company") or "Unknown company")
    icp_score = fields.get("icp_score", "unknown")
    match_score = float(getattr(hit, "score", 0.0))

    system_prompt = (
        "You are a senior B2B sales research analyst. Build concise, professional "
        "research notes for executive-level outbound personalization. Use only "
        "the supplied retrieved lead memory. Return strict JSON only."
    )
    user_prompt = f"""
Create a research profile for this retrieved lead.

Rules:
- Do not invent facts that are not present in the retrieved memory.
- You may infer likely pain points only when they are clearly grounded in role, company type, industry, or ICP reasons.
- Keep each list to 3-5 useful items.
- Do not write sales copy and do not say "our solution".
- Write in third person, as internal research notes for an SDR.
- Use professional, specific business language. Avoid hype, filler, and casual phrasing.
- Avoid vague claims like "optimize marketing", "drive growth", or "improve engagement" unless grounded in the context.
- personalization_angles must be short internal angles, not full email sentences.
- outreach_hook must be an internal angle, not a line addressed to the lead.
- outreach_hook must not start with "Hi", "I", "I'd", "Let's", or "Would".
- missing_info should list facts that would improve personalization later.

Return this JSON object:
{{
  "lead_summary": "string",
  "icp_fit": "string",
  "personalization_angles": ["string"],
  "possible_pain_points": ["string"],
  "outreach_hook": "string",
  "missing_info": ["string"]
}}

Fixed metadata:
{json.dumps(
    {
        "lead_id": lead_id,
        "full_name": full_name,
        "title": title,
        "company": company,
        "icp_score": icp_score,
        "match_score": match_score,
        "fields": fields,
    },
    indent=2,
)}

Retrieved memory:
{memory_text}
"""
    result = complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=1000,
    )

    required_strings = ["lead_summary", "icp_fit", "outreach_hook"]
    missing = [key for key in required_strings if not str(result.get(key, "")).strip()]
    if missing:
        raise ValueError(f"Groq research response missing required fields: {missing}")

    return ResearchProfile(
        lead_id=lead_id,
        full_name=full_name,
        title=title,
        company=company,
        icp_score=icp_score,
        match_score=match_score,
        lead_summary=str(result["lead_summary"]).strip(),
        icp_fit=str(result["icp_fit"]).strip(),
        personalization_angles=[
            str(item).strip()
            for item in result.get("personalization_angles", [])
            if str(item).strip()
        ],
        possible_pain_points=[
            str(item).strip()
            for item in result.get("possible_pain_points", [])
            if str(item).strip()
        ],
        outreach_hook=str(result["outreach_hook"]).strip(),
        missing_info=[
            str(item).strip()
            for item in result.get("missing_info", [])
            if str(item).strip()
        ],
        source_context=memory_text.splitlines(),
    )


def retrieve_best_hit(
    query: str,
    top_k: int = 3,
    metadata_filter: dict[str, Any] | None = None,
) -> Any | None:
    result = PineconeLeadMemory().search(
        query=query,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )
    hits = getattr(getattr(result, "result", None), "hits", [])
    return hits[0] if hits else None


def generate_research_profile(
    query: str,
    top_k: int = 3,
    metadata_filter: dict[str, Any] | None = None,
) -> ResearchProfile | None:
    hit = retrieve_best_hit(query=query, top_k=top_k, metadata_filter=metadata_filter)
    if hit is None:
        return None
    return generate_profile_from_hit(hit)


def format_profile(profile: ResearchProfile) -> str:
    lines = [
        f"# Research Profile: {profile.full_name}",
        "",
        f"- **Company:** {profile.company}",
        f"- **Title:** {profile.title}",
        f"- **Lead ID:** `{profile.lead_id}`",
        f"- **Match score:** {profile.match_score:.3f}",
        f"- **ICP score:** {profile.icp_score}",
        "",
        "## Lead Summary",
        "",
        profile.lead_summary,
        "",
        "## Why This Lead Fits ICP",
        "",
        profile.icp_fit,
        "",
        "## Personalization Angles",
        "",
    ]
    lines.extend(f"- {angle}" for angle in profile.personalization_angles)
    lines.extend(["", "## Possible Pain Points", ""])
    lines.extend(f"- {pain_point}" for pain_point in profile.possible_pain_points)
    lines.extend(["", "## Suggested Outreach Hook", "", profile.outreach_hook])
    lines.extend(["", "## Missing Info To Research Later", ""])
    lines.extend(f"- {item}" for item in profile.missing_info)
    lines.extend(["", "## Source Context", ""])
    lines.extend(f"- {line}" for line in profile.source_context)
    return "\n".join(lines)


def save_profile(profile: ResearchProfile) -> Path:
    output_dir = REPORTS_DIR / "research_profiles"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{_slugify(profile.lead_id)}.md"
    output_path.write_text(format_profile(profile), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    metadata_filter = build_metadata_filter(
        region=args.region,
        industry=args.industry,
        seniority=args.seniority,
        min_icp_score=args.min_icp_score,
    )
    profile = generate_research_profile(
        query=args.query,
        top_k=args.top_k,
        metadata_filter=metadata_filter,
    )
    if profile is None:
        print("No matching lead memory records found.")
        return

    print(format_profile(profile))
    if args.save:
        output_path = save_profile(profile)
        print(f"\nSaved research profile: {output_path}")


if __name__ == "__main__":
    main()

