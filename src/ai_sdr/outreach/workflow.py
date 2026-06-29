from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from ai_sdr.config import REPORTS_DIR
from ai_sdr.memory.search import build_metadata_filter
from ai_sdr.outreach.graph import run_langgraph_outreach_workflow
from ai_sdr.research.profile import format_profile
from ai_sdr.schemas import OutreachWorkflowRun


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Groq-powered outreach orchestration: research -> write -> review."
    )
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
        help="Save the workflow run under reports/outreach_runs/.",
    )
    return parser.parse_args()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "outreach-run"


def run_outreach_workflow(
    query: str,
    top_k: int = 3,
    metadata_filter: dict[str, Any] | None = None,
) -> OutreachWorkflowRun | None:
    return run_langgraph_outreach_workflow(
        query=query,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )


def format_workflow_run(run: OutreachWorkflowRun) -> str:
    review_status = "approved" if run.review.approved else "needs revision"
    lines = [
        f"# Outreach Workflow Run: {run.profile.full_name}",
        "",
        f"- **Query:** {run.query}",
        f"- **Lead ID:** `{run.profile.lead_id}`",
        f"- **Review status:** {review_status}",
        f"- **Review score:** {run.review.score}",
        "",
        "## Step 1: Research",
        "",
        format_profile(run.profile),
        "",
        "## Step 2: Write",
        "",
        f"**Subject:** {run.draft.subject}",
        "",
        run.draft.body,
        "",
        "### Personalization Used",
        "",
    ]
    lines.extend(f"- {item}" for item in run.draft.personalization_used)
    lines.extend(["", "## Step 3: Review", ""])
    lines.extend(
        f"- **{name.replace('_', ' ').title()}:** {'pass' if passed else 'fail'}"
        for name, passed in run.review.checks.items()
    )
    lines.extend(["", "### Feedback", ""])
    lines.extend(f"- {item}" for item in run.review.feedback)
    return "\n".join(lines)


def save_workflow_run(run: OutreachWorkflowRun) -> Path:
    output_dir = REPORTS_DIR / "outreach_runs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{_slugify(run.profile.lead_id)}.md"
    output_path.write_text(format_workflow_run(run), encoding="utf-8")
    return output_path


def main() -> None:
    args = parse_args()
    metadata_filter = build_metadata_filter(
        region=args.region,
        industry=args.industry,
        seniority=args.seniority,
        min_icp_score=args.min_icp_score,
    )
    run = run_outreach_workflow(
        query=args.query,
        top_k=args.top_k,
        metadata_filter=metadata_filter,
    )
    if run is None:
        print("No matching lead memory records found.")
        return

    print(format_workflow_run(run))
    if args.save:
        output_path = save_workflow_run(run)
        print(f"\nSaved outreach workflow run: {output_path}")


if __name__ == "__main__":
    main()

