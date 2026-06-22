from __future__ import annotations

from collections import Counter
from pathlib import Path

from .schemas import Lead


def qualified_leads(leads: list[Lead], threshold: int = 60) -> list[Lead]:
    return [lead for lead in leads if lead.icp_score >= threshold]


def write_report(leads: list[Lead], output_path: Path, threshold: int = 60) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    qualified = qualified_leads(leads, threshold)
    region_counts = Counter(lead.region for lead in leads)
    seniority_counts = Counter(lead.seniority for lead in leads)

    lines = [
        "# Lead Ingestion Report",
        "",
        f"Total leads ingested: {len(leads)}",
        f"Qualified leads (ICP score >= {threshold}): {len(qualified)}",
        "",
        "## Seniority Breakdown",
        "",
    ]
    for seniority, count in seniority_counts.most_common():
        lines.append(f"- **{seniority}**: {count}")

    lines.extend(["", "## Region Breakdown", ""])
    for region, count in region_counts.most_common():
        lines.append(f"- **{region}**: {count}")

    lines.extend(["", "## Top Leads by ICP Score", ""])
    for lead in sorted(leads, key=lambda item: item.icp_score, reverse=True)[:10]:
        lines.append(f"- **{lead.full_name}** — {lead.title} at {lead.company}")
        lines.append(f"  - ICP score: {lead.icp_score}")
        lines.append(f"  - Region: {lead.region} | Seniority: {lead.seniority}")
        lines.append(f"  - Why: {'; '.join(lead.icp_reasons)}")

    lines.extend(
        [
            "",
            "## Pipeline Notes",
            "",
            "- Raw leads are stored in `data/raw/leads_raw.jsonl`.",
            "- Enriched and scored leads are stored in `data/processed/leads.jsonl`.",
            "- ICP scoring is rule-based today and will be augmented with an LLM agent in a later day.",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")
