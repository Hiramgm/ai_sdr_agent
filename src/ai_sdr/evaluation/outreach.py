from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_sdr.config import REPORTS_DIR
from ai_sdr.llm.groq_client import complete_json
from ai_sdr.observability import log_event
from ai_sdr.schemas import (
    OutreachEvaluation,
    OutreachMessageDraft,
    OutreachReview,
    OutreachWorkflowRun,
    ResearchProfile,
)

EXPECTED_METRICS = {
    "research_grounding",
    "personalization",
    "clarity",
    "tone",
    "cta_quality",
    "risk_control",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an outreach workflow run JSON file.")
    parser.add_argument("run_json", type=Path, help="Path to a JSON file containing OutreachWorkflowRun data.")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the evaluation under reports/evaluations/.",
    )
    return parser.parse_args()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "outreach-evaluation"


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _score(value: object) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _metrics(raw: object) -> dict[str, int]:
    values = raw if isinstance(raw, dict) else {}
    return {name: _score(values.get(name, 0)) for name in EXPECTED_METRICS}


def evaluate_outreach_run(run: OutreachWorkflowRun) -> OutreachEvaluation:
    """Use Groq to evaluate message quality and grounding for an outreach run."""
    system_prompt = (
        "You are a strict outbound quality evaluator for B2B SDR workflows. "
        "Score the generated outreach against the research profile and reviewer "
        "result. Return strict JSON only."
    )
    user_prompt = f"""
Evaluate this outreach workflow run.

Metrics, each scored 0-100:
- research_grounding: uses only facts supported by the research profile
- personalization: specific to the lead/company instead of generic
- clarity: clear, concise, and easy to understand
- tone: professional, human, and not overhyped
- cta_quality: has one low-pressure and actionable CTA
- risk_control: avoids unsupported claims, spamminess, and compliance issues

Rules:
- overall_score must be an integer from 0 to 100.
- passed should be true only when overall_score >= 80 and risk_control >= 80.
- risks should list concrete issues or be empty.
- recommendations should list practical improvements or be empty.
- Do not invent facts beyond the supplied workflow run.

Return this JSON object:
{{
  "overall_score": 0,
  "passed": false,
  "metrics": {{
    "research_grounding": 0,
    "personalization": 0,
    "clarity": 0,
    "tone": 0,
    "cta_quality": 0,
    "risk_control": 0
  }},
  "summary": "string",
  "risks": ["string"],
  "recommendations": ["string"]
}}

Workflow run:
{json.dumps(run.to_dict(), indent=2)}
"""
    result = complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.1,
        max_tokens=900,
    )
    metrics = _metrics(result.get("metrics"))
    overall_score = _score(result.get("overall_score"))
    passed = bool(result.get("passed", overall_score >= 80 and metrics["risk_control"] >= 80))
    if overall_score < 80 or metrics["risk_control"] < 80:
        passed = False
    evaluation = OutreachEvaluation(
        overall_score=overall_score,
        passed=passed,
        metrics=metrics,
        summary=str(result.get("summary", "")).strip(),
        risks=_list_of_strings(result.get("risks")),
        recommendations=_list_of_strings(result.get("recommendations")),
    )
    log_event(
        "outreach_evaluated",
        {
            "lead_id": run.profile.lead_id,
            "overall_score": evaluation.overall_score,
            "passed": evaluation.passed,
        },
    )
    return evaluation


def format_outreach_evaluation(evaluation: OutreachEvaluation) -> str:
    status = "passed" if evaluation.passed else "needs improvement"
    lines = [
        "# Outreach Evaluation",
        "",
        f"- **Status:** {status}",
        f"- **Overall score:** {evaluation.overall_score}",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(
        f"- **{name.replace('_', ' ').title()}:** {score}"
        for name, score in evaluation.metrics.items()
    )
    lines.extend(["", "## Summary", "", evaluation.summary or "No summary returned."])
    lines.extend(["", "## Risks", ""])
    lines.extend(f"- {risk}" for risk in evaluation.risks or ["No major risks identified."])
    lines.extend(["", "## Recommendations", ""])
    lines.extend(
        f"- {recommendation}"
        for recommendation in evaluation.recommendations or ["No recommendations returned."]
    )
    return "\n".join(lines)


def save_outreach_evaluation(
    evaluation: OutreachEvaluation,
    lead_id: str,
) -> Path:
    output_dir = REPORTS_DIR / "evaluations"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    output_path = output_dir / f"{_slugify(lead_id)}-{timestamp}.md"
    output_path.write_text(format_outreach_evaluation(evaluation), encoding="utf-8")
    return output_path


def run_from_dict(data: dict[str, Any]) -> OutreachWorkflowRun:
    """Build an OutreachWorkflowRun from JSON-compatible dict data."""
    profile_raw = data.get("profile", {})
    draft_raw = data.get("draft", {})
    review_raw = data.get("review", {})
    if not isinstance(profile_raw, dict) or not isinstance(draft_raw, dict) or not isinstance(review_raw, dict):
        raise ValueError("run_json must include profile, draft, and review objects.")
    profile = ResearchProfile(
        lead_id=str(profile_raw.get("lead_id", "")),
        full_name=str(profile_raw.get("full_name", "")),
        title=str(profile_raw.get("title", "")),
        company=str(profile_raw.get("company", "")),
        icp_score=profile_raw.get("icp_score", ""),
        match_score=float(profile_raw.get("match_score", 0.0)),
        lead_summary=str(profile_raw.get("lead_summary", "")),
        icp_fit=str(profile_raw.get("icp_fit", "")),
        personalization_angles=_list_of_strings(profile_raw.get("personalization_angles")),
        possible_pain_points=_list_of_strings(profile_raw.get("possible_pain_points")),
        outreach_hook=str(profile_raw.get("outreach_hook", "")),
        missing_info=_list_of_strings(profile_raw.get("missing_info")),
        source_context=_list_of_strings(profile_raw.get("source_context")),
    )
    draft = OutreachMessageDraft(
        lead_id=str(draft_raw.get("lead_id", "")),
        subject=str(draft_raw.get("subject", "")),
        body=str(draft_raw.get("body", "")),
        call_to_action=str(draft_raw.get("call_to_action", "")),
        personalization_used=_list_of_strings(draft_raw.get("personalization_used")),
    )
    checks_raw = review_raw.get("checks", {})
    review = OutreachReview(
        approved=bool(review_raw.get("approved", False)),
        score=_score(review_raw.get("score")),
        checks={str(name): bool(value) for name, value in checks_raw.items()} if isinstance(checks_raw, dict) else {},
        feedback=_list_of_strings(review_raw.get("feedback")),
    )
    return OutreachWorkflowRun(
        query=str(data.get("query", "")),
        profile=profile,
        draft=draft,
        review=review,
    )


def main() -> None:
    args = parse_args()
    data = json.loads(args.run_json.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("run_json must contain a JSON object.")
    run = run_from_dict(data)
    evaluation = evaluate_outreach_run(run)
    print(format_outreach_evaluation(evaluation))
    if args.save:
        output_path = save_outreach_evaluation(evaluation, run.profile.lead_id)
        print(f"\nSaved outreach evaluation: {output_path}")


if __name__ == "__main__":
    main()
