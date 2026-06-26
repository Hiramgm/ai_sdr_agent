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
    parser = argparse.ArgumentParser(description="AI SDR lead ingestion pipeline.")
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
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Also persist results to PostgreSQL (leads) and MongoDB (raw + run log).",
    )
    parser.add_argument(
        "--index-memory",
        action="store_true",
        help="Also upsert enriched leads into Pinecone vector memory.",
    )
    return parser.parse_args()


def persist_to_databases(
    raw_leads: list,
    leads: list,
    source: str,
    threshold: int,
    qualified: int,
) -> None:
    """Write structured leads to Postgres and raw leads + a run log to Mongo.

    Drivers are imported lazily so the default (no --persist) run needs no DB.
    """
    from .db import mongo
    from .db import postgres as pg

    conn = pg.connect()
    pg.init_schema(conn)
    written = pg.upsert_leads(conn, leads)
    pg_total = pg.count_leads(conn)
    conn.close()
    print(f"Postgres: upserted {written} leads (total now {pg_total})")

    client = mongo.connect()
    try:
        db = mongo.get_db(client)
        raw_written = mongo.store_raw_leads(db, raw_leads)
        run_id = mongo.log_run(
            db,
            {
                "source": source,
                "threshold": threshold,
                "total_leads": len(leads),
                "qualified_leads": qualified,
            },
        )
        print(f"MongoDB: stored {raw_written} raw leads; run_logs id {run_id}")
    finally:
        client.close()


def index_lead_memory(leads: list) -> None:
    """Write enriched leads to Pinecone only when explicitly requested."""
    from .memory.lead_memory import PineconeLeadMemory

    memory = PineconeLeadMemory()
    written = memory.upsert_leads(leads)
    print(f"Pinecone: upserted {written} lead memory records")


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

    if args.persist:
        persist_to_databases(raw_leads, leads, args.source, args.threshold, qualified)

    if args.index_memory:
        index_lead_memory(leads)


if __name__ == "__main__":
    main()
