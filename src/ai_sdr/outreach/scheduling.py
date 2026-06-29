from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_sdr.config import REPORTS_DIR
from ai_sdr.llm.groq_client import complete_json
from ai_sdr.outreach.reply import classify_reply
from ai_sdr.schemas import MeetingProposal, ReplyClassification

ALLOWED_MEETING_TYPES = {"intro_call", "demo", "follow_up", "discovery"}
SCHEDULABLE_INTENTS = {"interested", "referral"}
DEFAULT_DURATION_MINUTES = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Propose a meeting from an inbound prospect reply."
    )
    parser.add_argument(
        "reply",
        nargs="?",
        help="Reply text to act on. Use --input-file for longer replies.",
    )
    parser.add_argument("--input-file", type=Path, help="Read reply text from a file.")
    parser.add_argument("--lead-id", default="unknown", help="Lead ID for the proposal.")
    parser.add_argument("--lead-name", help="Lead full name for personalization.")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the proposal under reports/meeting_proposals/.",
    )
    return parser.parse_args()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "meeting-proposal"


def _normalize_meeting_type(value: object) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in ALLOWED_MEETING_TYPES else "intro_call"


def candidate_slots(now: datetime | None = None, count: int = 3) -> list[str]:
    """Generate human-readable business-day meeting slots, grounded in real dates."""
    current = now or datetime.now(UTC)
    slots: list[str] = []
    cursor = current
    hours = [10, 14, 16]
    while len(slots) < count:
        cursor = cursor + timedelta(days=1)
        if cursor.weekday() >= 5:  # Skip Saturday and Sunday.
            continue
        hour = hours[len(slots) % len(hours)]
        slot = cursor.replace(hour=hour, minute=0, second=0, microsecond=0)
        slots.append(slot.strftime("%A, %b %d at %H:%M UTC"))
    return slots


def propose_meeting(
    classification: ReplyClassification,
    reply_text: str,
    lead_id: str = "unknown",
    lead_name: str | None = None,
    now: datetime | None = None,
) -> MeetingProposal:
    """Use Groq to turn an interested reply into a concrete meeting proposal."""
    slots = candidate_slots(now=now)
    should_schedule = classification.intent in SCHEDULABLE_INTENTS

    if not should_schedule:
        return MeetingProposal(
            lead_id=lead_id,
            should_schedule=False,
            meeting_type="intro_call",
            duration_minutes=DEFAULT_DURATION_MINUTES,
            proposed_slots=[],
            agenda=[],
            reply_message="",
            reasons=[
                f"Reply intent '{classification.intent}' is not ready for scheduling.",
                "Scheduling triggers only on interested or referral replies.",
            ],
        )

    system_prompt = (
        "You are a B2B SDR scheduling agent. The prospect is interested. Propose a "
        "concise meeting and write a short reply offering the supplied time slots. "
        "Return strict JSON only."
    )
    name = lead_name or "there"
    user_prompt = f"""
Propose a meeting for this interested prospect.

Rules:
- Choose meeting_type from: intro_call, demo, follow_up, discovery.
- Offer exactly the provided candidate slots; do not invent other times.
- duration_minutes should be 15, 20, 30, or 45.
- agenda must be 2-4 short bullet points.
- reply_message is a short, professional email body offering the slots.
- Address the prospect as "{name}" and sign as Hira.
- Do not use emojis. Do not overclaim.

Candidate slots (offer these exact strings):
{chr(10).join(f"- {slot}" for slot in slots)}

Reply classification:
- intent: {classification.intent}
- sentiment: {classification.sentiment}
- urgency: {classification.urgency}
- summary: {classification.summary}

Prospect reply:
{reply_text}

Return this JSON object:
{{
  "meeting_type": "intro_call",
  "duration_minutes": 30,
  "agenda": ["string"],
  "reply_message": "string"
}}
"""
    result = complete_json(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=700,
    )

    meeting_type = _normalize_meeting_type(result.get("meeting_type"))
    try:
        duration_minutes = int(result.get("duration_minutes", DEFAULT_DURATION_MINUTES))
    except (TypeError, ValueError):
        duration_minutes = DEFAULT_DURATION_MINUTES
    if duration_minutes not in {15, 20, 30, 45}:
        duration_minutes = DEFAULT_DURATION_MINUTES
    agenda = [
        str(item).strip()
        for item in result.get("agenda", [])
        if str(item).strip()
    ]
    reply_message = str(result.get("reply_message", "")).strip()
    if not reply_message:
        raise ValueError("Groq scheduling response must include a reply_message.")

    return MeetingProposal(
        lead_id=lead_id,
        should_schedule=True,
        meeting_type=meeting_type,
        duration_minutes=duration_minutes,
        proposed_slots=slots,
        agenda=agenda or ["Introductions and context", "Discuss the AI SDR workflow"],
        reply_message=reply_message,
        reasons=[f"Reply intent '{classification.intent}' is ready for scheduling."],
    )


def format_meeting_proposal(proposal: MeetingProposal) -> str:
    lines = [
        "# Meeting Proposal",
        "",
        f"- **Lead ID:** `{proposal.lead_id}`",
        f"- **Should schedule:** {'yes' if proposal.should_schedule else 'no'}",
        f"- **Meeting type:** {proposal.meeting_type}",
        f"- **Duration:** {proposal.duration_minutes} minutes",
        "",
    ]
    if proposal.proposed_slots:
        lines.extend(["## Proposed Slots", ""])
        lines.extend(f"- {slot}" for slot in proposal.proposed_slots)
        lines.append("")
    if proposal.agenda:
        lines.extend(["## Agenda", ""])
        lines.extend(f"- {item}" for item in proposal.agenda)
        lines.append("")
    if proposal.reply_message:
        lines.extend(["## Reply Message", "", proposal.reply_message, ""])
    lines.extend(["## Reasons", ""])
    lines.extend(f"- {reason}" for reason in proposal.reasons)
    return "\n".join(lines)


def save_meeting_proposal(proposal: MeetingProposal) -> Path:
    output_dir = REPORTS_DIR / "meeting_proposals"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    output_path = output_dir / f"{_slugify(proposal.lead_id)}-{timestamp}.md"
    output_path.write_text(format_meeting_proposal(proposal), encoding="utf-8")
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
    proposal = propose_meeting(
        classification=classification,
        reply_text=reply_text,
        lead_id=args.lead_id,
        lead_name=args.lead_name,
    )
    print(format_meeting_proposal(proposal))
    if args.save:
        output_path = save_meeting_proposal(proposal)
        print(f"\nSaved meeting proposal: {output_path}")


if __name__ == "__main__":
    main()
