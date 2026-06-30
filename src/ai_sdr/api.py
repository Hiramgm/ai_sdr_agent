from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ai_sdr.config import SETTINGS
from ai_sdr.evaluation.outreach import evaluate_outreach_run, run_from_dict
from ai_sdr.jobs.queue import QueueUnavailable, enqueue, fetch_job_state
from ai_sdr.memory.search import build_metadata_filter
from ai_sdr.observability import log_event, read_recent_events
from ai_sdr.outreach.reply import classify_reply
from ai_sdr.outreach.scheduling import propose_meeting
from ai_sdr.outreach.workflow import run_outreach_workflow

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(title="AI SDR Agent", version="0.1.0")


class OutreachRequest(BaseModel):
    query: str
    top_k: int = 3
    region: str | None = None
    industry: str | None = None
    seniority: str | None = None
    min_icp_score: int | None = None


class ReplyRequest(BaseModel):
    reply_text: str
    lead_id: str | None = None


class ScheduleRequest(BaseModel):
    reply_text: str
    lead_id: str = "unknown"
    lead_name: str | None = None


class OutreachEvaluationRequest(BaseModel):
    run: dict[str, Any]


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "groq_configured": bool(SETTINGS.groq_api_key),
        "pinecone_configured": bool(SETTINGS.pinecone_api_key),
        "model": SETTINGS.groq_model,
        "redis_url": SETTINGS.redis_url,
    }


@app.post("/api/outreach")
def outreach(request: OutreachRequest) -> dict[str, Any]:
    metadata_filter = build_metadata_filter(
        region=request.region,
        industry=request.industry,
        seniority=request.seniority,
        min_icp_score=request.min_icp_score,
    )
    try:
        run = run_outreach_workflow(
            query=request.query,
            top_k=request.top_k,
            metadata_filter=metadata_filter,
        )
    except Exception as error:  # noqa: BLE001 - surface a clean message to the UI.
        raise HTTPException(status_code=502, detail=str(error)) from error
    if run is None:
        raise HTTPException(status_code=404, detail="No matching lead memory records found.")
    log_event("outreach_completed", {"lead_id": run.profile.lead_id, "review_score": run.review.score})
    return run.to_dict()


@app.post("/api/reply")
def reply(request: ReplyRequest) -> dict[str, Any]:
    if not request.reply_text.strip():
        raise HTTPException(status_code=400, detail="reply_text is required.")
    try:
        classification = classify_reply(request.reply_text)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(error)) from error
    log_event("reply_classified", {"intent": classification.intent, "confidence": classification.confidence})
    return classification.to_dict()


@app.post("/api/schedule")
def schedule(request: ScheduleRequest) -> dict[str, Any]:
    if not request.reply_text.strip():
        raise HTTPException(status_code=400, detail="reply_text is required.")
    try:
        classification = classify_reply(request.reply_text)
        proposal = propose_meeting(
            classification=classification,
            reply_text=request.reply_text,
            lead_id=request.lead_id,
            lead_name=request.lead_name,
        )
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "classification": classification.to_dict(),
        "proposal": proposal.to_dict(),
    }


@app.post("/api/evaluate/outreach")
def evaluate_outreach(request: OutreachEvaluationRequest) -> dict[str, Any]:
    try:
        run = run_from_dict(request.run)
        evaluation = evaluate_outreach_run(run)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(error)) from error
    return evaluation.to_dict()


@app.get("/api/observability/events")
def observability_events(limit: int = 20) -> dict[str, Any]:
    return {"events": read_recent_events(limit=limit)}


@app.post("/api/jobs/outreach")
def enqueue_outreach(request: OutreachRequest) -> dict[str, Any]:
    try:
        job = enqueue(
            "ai_sdr.jobs.tasks.run_outreach_task",
            job_kwargs={
                "query": request.query,
                "top_k": request.top_k,
                "region": request.region,
                "industry": request.industry,
                "seniority": request.seniority,
                "min_icp_score": request.min_icp_score,
            },
        )
    except QueueUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"job_id": job.id, "status": job.get_status(refresh=False)}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    try:
        return fetch_job_state(job_id)
    except QueueUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
