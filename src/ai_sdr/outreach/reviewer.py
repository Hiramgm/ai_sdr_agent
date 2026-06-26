from __future__ import annotations

import json

from ai_sdr.llm.groq_client import complete_json
from ai_sdr.schemas import OutreachMessageDraft, OutreachReview, ResearchProfile


def review_draft(
    draft: OutreachMessageDraft,
    profile: ResearchProfile,
) -> OutreachReview:
    """Use Groq to review an outreach draft against the research profile."""
    system_prompt = (
        "You are a strict B2B SDR email reviewer for professional executive "
        "outreach. Decide whether the draft is ready to send. Return strict JSON only."
    )
    user_prompt = f"""
Review this first-touch outbound email.

Evaluate:
- concise_under_120_words
- specific_to_lead_or_company
- uses_research_profile
- has_single_clear_cta
- avoids_unsupported_claims
- natural_tone
- professional_tone

Return this JSON object:
{{
  "approved": true,
  "score": 0,
  "checks": {{
    "concise_under_120_words": true,
    "specific_to_lead_or_company": true,
    "uses_research_profile": true,
    "has_single_clear_cta": true,
    "avoids_unsupported_claims": true,
    "natural_tone": true,
    "professional_tone": true
  }},
  "feedback": ["string"]
}}

Important:
- "score" must be an integer quality score from 0 to 100, not a count of checks.
- Use 90-100 for excellent, 80-89 for sendable, 60-79 for needs revision, and below 60 for poor.
- "approved" should be true only when the draft is sendable.
- If all checks are true and score is 80 or higher, "approved" must be true.
- If "approved" is false, at least one check should be false and feedback must explain why.
- Reject drafts that sound generic, overhyped, too casual, or like a marketing brochure.

Research profile:
{json.dumps(profile.to_dict(), indent=2)}

Draft:
{json.dumps(draft.to_dict(), indent=2)}
"""
    result = complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.1,
    )
    checks_raw = result.get("checks", {})
    checks = (
        {str(name): bool(value) for name, value in checks_raw.items()}
        if isinstance(checks_raw, dict)
        else {}
    )
    score = int(result.get("score", 0))
    feedback = [
        str(item).strip()
        for item in result.get("feedback", [])
        if str(item).strip()
    ]
    approved = bool(result.get("approved", score >= 80))
    if checks and all(checks.values()) and score >= 80:
        approved = True
    if approved and not feedback:
        feedback.append("Draft is professional and ready to send.")

    return OutreachReview(
        approved=approved,
        score=score,
        checks=checks,
        feedback=feedback or ["Groq returned no reviewer feedback."],
    )

