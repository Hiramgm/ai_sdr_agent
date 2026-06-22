from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import ICP, PROCESSED_DIR, RAW_DIR, REPORTS_DIR
from .ingestion.enrich import enrich_leads
from .ingestion.sources import load_raw_leads
from .reporting import write_report
from .storage import write_leads, write_raw_leads


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI SDR lead ingestion pipeline (Day 1).")
    parser.add_argument(
        "--source",
        choices=["sample", "file"],
        default="sample",
        help="Use curated sample leads or load from a JSON/CSV file.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Path to a JSON or CSV file when --source file.",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=60,
        help="Minimum ICP score to count a lead as qualified.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()

    raw_leads = load_raw_leads(args.source, args.input)
    leads = enrich_leads(raw_leads, ICP)

    raw_path = RAW_DIR / "leads_raw.jsonl"
    leads_path = PROCESSED_DIR / "leads.jsonl"
    report_path = REPORTS_DIR / "ingestion_report.md"

    write_raw_leads(raw_leads, raw_path)
    write_leads(leads, leads_path)
    write_report(leads, report_path, args.threshold)

    qualified = sum(1 for lead in leads if lead.icp_score >= args.threshold)
    print(f"Ingested leads: {len(leads)}")
    print(f"Qualified leads (>= {args.threshold}): {qualified}")
    print(f"Wrote raw leads: {raw_path}")
    print(f"Wrote enriched leads: {leads_path}")
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()
