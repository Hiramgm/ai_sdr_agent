from __future__ import annotations

import json

from ai_sdr.llm.groq_client import complete_json
from ai_sdr.schemas import OutreachMessageDraft, ResearchProfile


def write_first_touch(profile: ResearchProfile) -> OutreachMessageDraft:
    """Use Groq to write a first-touch email from a research profile."""
    system_prompt = (
        "You are an expert B2B SDR copywriter for professional executive outreach. "
        "Write concise, specific first-touch emails using only the supplied research "
        "profile. Return strict JSON only."
    )
    user_prompt = f"""
Create one first-touch outbound email.

Rules:
- Keep the body under 120 words.
- Use a polished, professional, human tone.
- Write like a credible operator, not a marketing brochure.
- Mention the lead or company specifically.
- Include exactly one clear, low-pressure CTA question.
- Do not invent facts beyond the research profile.
- Do not use generic phrases like "our solution" or "potential strategies".
- Avoid vague phrases like "streamline", "optimize", "drive growth", and "enhance" unless the research profile supports them.
- Avoid overclaiming; frame the AI SDR workflow as something to discuss, not a guaranteed outcome.
- If you mention the product, call it an "AI SDR workflow".
- Do not use emojis.
- Sign as Hira.

Return this JSON object:
{{
  "subject": "string",
  "body": "string",
  "call_to_action": "string",
  "personalization_used": ["string"]
}}

Research profile:
{json.dumps(profile.to_dict(), indent=2)}
"""
    result = complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
    subject = str(result.get("subject", "")).strip()
    body = str(result.get("body", "")).strip()
    call_to_action = str(result.get("call_to_action", "")).strip()
    if not subject or not body or not call_to_action:
        raise ValueError("Groq writer response must include subject, body, and call_to_action.")

    return OutreachMessageDraft(
        lead_id=profile.lead_id,
        subject=subject,
        body=body,
        call_to_action=call_to_action,
        personalization_used=[
            str(item).strip()
            for item in result.get("personalization_used", [])
            if str(item).strip()
        ],
    )

