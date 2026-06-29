from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path

from ai_sdr.config import REPORTS_DIR
from ai_sdr.llm.groq_client import complete_json
from ai_sdr.schemas import ReplyClassification

ALLOWED_INTENTS = {
    "interested",
    "objection",
    "not_now",
    "unsubscribe",
    "out_of_office",
    "referral",
    "wrong_person",
    "neutral",
    "unknown",
}
ALLOWED_SENTIMENTS = {"positive", "neutral", "negative", "unknown"}
ALLOWED_URGENCY = {"high", "medium", "low", "unknown"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify an inbound prospect reply.")
    parser.add_argument(
        "reply",
        nargs="?",
        help="Reply text to classify. Use --input-file for longer replies.",
    )
    parser.add_argument("--input-file", type=Path, help="Read reply text from a file.")
    parser.add_argument("--lead-id", help="Optional lead ID used when saving the artifact.")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the classification under reports/reply_classifications/.",
    )
    return parser.parse_args()


def _normalize_choice(value: object, allowed: set[str], default: str = "unknown") -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in allowed else default


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "reply-classification"


def classify_reply(reply_text: str) -> ReplyClassification:
    """Use Groq to classify an inbound reply and recommend the next action."""
    if not reply_text.strip():
        raise ValueError("Reply text is required.")

    system_prompt = (
        "You are a B2B SDR reply triage agent. Classify inbound prospect replies "
        "for a professional outbound workflow. Return strict JSON only."
    )
    user_prompt = f"""
Classify this inbound prospect reply.

Allowed intent values:
- interested: wants to talk, asks for details, or agrees to a meeting
- objection: raises a concern about price, timing, relevance, trust, or fit
- not_now: asks to follow up later but does not reject permanently
- unsubscribe: asks not to be contacted again
- out_of_office: automatic or temporary absence reply
- referral: points to another person
- wrong_person: says they are not the right contact
- neutral: acknowledgement without clear interest or rejection
- unknown: unclear or too little information

Allowed sentiment values: positive, neutral, negative, unknown.
Allowed urgency values: high, medium, low, unknown.

Rules:
- Do not invent context beyond the reply.
- Set needs_human_review to true for unsubscribe, angry/negative replies, legal/compliance issues, or low confidence.
- recommended_action should be one practical next step for the SDR system.
- confidence must be a number from 0.0 to 1.0.
- Keep summary and reasons concise.

Return this JSON object:
{{
  "intent": "interested",
  "sentiment": "positive",
  "urgency": "medium",
  "confidence": 0.0,
  "summary": "string",
  "recommended_action": "string",
  "needs_human_review": false,
  "reasons": ["string"]
}}

Reply:
{reply_text}
"""
    result = complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.1,
        max_tokens=700,
    )
    intent = _normalize_choice(result.get("intent"), ALLOWED_INTENTS)
    sentiment = _normalize_choice(result.get("sentiment"), ALLOWED_SENTIMENTS)
    urgency = _normalize_choice(result.get("urgency"), ALLOWED_URGENCY)
    confidence = max(0.0, min(1.0, float(result.get("confidence", 0.0))))
    summary = str(result.get("summary", "")).strip()
    recommended_action = str(result.get("recommended_action", "")).strip()
    reasons = [
        str(item).strip()
        for item in result.get("reasons", [])
        if str(item).strip()
    ]
    needs_human_review = bool(result.get("needs_human_review", confidence < 0.65))
    if intent == "unsubscribe" or confidence < 0.65:
        needs_human_review = True
    if not summary or not recommended_action:
        raise ValueError("Groq reply classifier response must include summary and recommended_action.")

    return ReplyClassification(
        intent=intent,
        sentiment=sentiment,
        urgency=urgency,
        confidence=confidence,
        summary=summary,
        recommended_action=recommended_action,
        needs_human_review=needs_human_review,
        reasons=reasons or ["Groq returned no classification reasons."],
    )


def format_reply_classification(
    classification: ReplyClassification,
    reply_text: str,
    lead_id: str | None = None,
) -> str:
    lines = [
        "# Reply Classification",
        "",
    ]
    if lead_id:
        lines.extend([f"- **Lead ID:** `{lead_id}`"])
    lines.extend(
        [
            f"- **Intent:** {classification.intent}",
            f"- **Sentiment:** {classification.sentiment}",
            f"- **Urgency:** {classification.urgency}",
            f"- **Confidence:** {classification.confidence:.2f}",
            f"- **Needs human review:** {'yes' if classification.needs_human_review else 'no'}",
            "",
            "## Summary",
            "",
            classification.summary,
            "",
            "## Recommended Action",
            "",
            classification.recommended_action,
            "",
            "## Reasons",
            "",
        ]
    )
    lines.extend(f"- {reason}" for reason in classification.reasons)
    lines.extend(["", "## Reply", "", reply_text])
    return "\n".join(lines)


def save_reply_classification(
    classification: ReplyClassification,
    reply_text: str,
    lead_id: str | None = None,
) -> Path:
    output_dir = REPORTS_DIR / "reply_classifications"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    name = lead_id or classification.intent
    output_path = output_dir / f"{_slugify(name)}-{timestamp}.md"
    output_path.write_text(
        format_reply_classification(classification, reply_text, lead_id),
        encoding="utf-8",
    )
    return output_path


def _load_reply_text(args: argparse.Namespace) -> str:
    if args.input_file:
        return args.input_file.read_text(encoding="utf-8")
    if args.reply:
        return args.reply
    raise ValueError("Provide reply text or --input-file.")


def main() -> None:
    args = parse_args()
    reply_text = _load_reply_text(args)
    classification = classify_reply(reply_text)
    print(format_reply_classification(classification, reply_text, args.lead_id))
    if args.save:
        output_path = save_reply_classification(
            classification,
            reply_text,
            args.lead_id,
        )
        print(f"\nSaved reply classification: {output_path}")


if __name__ == "__main__":
    main()
