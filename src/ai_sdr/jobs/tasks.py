"""Task functions executed by RQ workers.

These must be importable by their dotted path (for example
``ai_sdr.jobs.tasks.run_outreach_task``) so the worker can load and run them.
Each task returns a JSON-serializable dict so the result is safe to store in
Redis and return over HTTP.
"""

from __future__ import annotations

from typing import Any

from ai_sdr.memory.search import build_metadata_filter
from ai_sdr.outreach.workflow import run_outreach_workflow


def run_outreach_task(
    query: str,
    top_k: int = 3,
    region: str | None = None,
    industry: str | None = None,
    seniority: str | None = None,
    min_icp_score: int | None = None,
) -> dict[str, Any]:
    """Run the full outreach workflow as a background job."""
    metadata_filter = build_metadata_filter(
        region=region,
        industry=industry,
        seniority=seniority,
        min_icp_score=min_icp_score,
    )
    run = run_outreach_workflow(
        query=query,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )
    if run is None:
        return {"found": False, "message": "No matching lead memory records found."}
    return {"found": True, "run": run.to_dict()}
