from __future__ import annotations

import argparse
from typing import Any

from ai_sdr.memory.lead_memory import PineconeLeadMemory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search Pinecone lead memory.")
    parser.add_argument("query", help="Natural-language query to search lead memory.")
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of matching memory records to return.",
    )
    parser.add_argument(
        "--show-text",
        action="store_true",
        help="Print the full stored lead memory text for each match.",
    )
    parser.add_argument("--region", help="Only return leads from this normalized region.")
    parser.add_argument("--industry", help="Only return leads from this industry.")
    parser.add_argument("--seniority", help="Only return leads with this seniority.")
    parser.add_argument(
        "--min-icp-score",
        type=int,
        help="Only return leads with an ICP score greater than or equal to this value.",
    )
    return parser.parse_args()


def build_metadata_filter(
    region: str | None = None,
    industry: str | None = None,
    seniority: str | None = None,
    min_icp_score: int | None = None,
) -> dict[str, Any] | None:
    filters: dict[str, Any] = {}
    if region:
        filters["region"] = {"$eq": region.strip().lower()}
    if industry:
        filters["industry"] = {"$eq": industry.strip()}
    if seniority:
        filters["seniority"] = {"$eq": seniority.strip().lower()}
    if min_icp_score is not None:
        filters["icp_score"] = {"$gte": min_icp_score}

    return filters or None


def _hit_fields(hit: Any) -> dict[str, Any]:
    fields = getattr(hit, "fields", None)
    return fields if isinstance(fields, dict) else {}


def format_hit(hit: Any, rank: int, show_text: bool = False) -> str:
    fields = _hit_fields(hit)
    score = getattr(hit, "score", 0.0)
    lead_id = fields.get("lead_id", getattr(hit, "id", "unknown"))
    full_name = fields.get("full_name", "Unknown lead")
    title = fields.get("title", "Unknown title")
    company = fields.get("company", "Unknown company")
    industry = fields.get("industry", "unknown")
    region = fields.get("region", "unknown")
    seniority = fields.get("seniority", "unknown")
    icp_score = fields.get("icp_score", "unknown")

    lines = [
        f"{rank}. {full_name} at {company}",
        f"   title: {title}",
        f"   lead_id: {lead_id}",
        f"   match_score: {float(score):.3f}",
        f"   region: {region}",
        f"   industry: {industry}",
        f"   seniority: {seniority}",
        f"   icp_score: {icp_score}",
    ]

    if show_text and fields.get("text"):
        lines.append("   memory:")
        lines.extend(f"     {line}" for line in str(fields["text"]).splitlines())

    return "\n".join(lines)


def search_lead_memory(
    query: str,
    top_k: int = 3,
    show_text: bool = False,
    metadata_filter: dict[str, Any] | None = None,
) -> str:
    result = PineconeLeadMemory().search(
        query=query,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )
    hits = getattr(getattr(result, "result", None), "hits", [])
    if not hits:
        return "No matching lead memory records found."

    formatted_hits = [
        format_hit(hit, rank=index, show_text=show_text)
        for index, hit in enumerate(hits, start=1)
    ]
    return "\n\n".join(formatted_hits)


def main() -> None:
    args = parse_args()
    metadata_filter = build_metadata_filter(
        region=args.region,
        industry=args.industry,
        seniority=args.seniority,
        min_icp_score=args.min_icp_score,
    )
    print(
        search_lead_memory(
            args.query,
            top_k=args.top_k,
            show_text=args.show_text,
            metadata_filter=metadata_filter,
        )
    )


if __name__ == "__main__":
    main()

