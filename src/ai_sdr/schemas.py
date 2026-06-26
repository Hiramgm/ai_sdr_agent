from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class RawLead:
    """A lead as it arrives from a source, before enrichment."""

    full_name: str
    title: str
    company: str
    location: str = ""
    email: str = ""
    linkedin_url: str = ""
    company_website: str = ""
    industry: str = ""
    source: str = "unknown"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Lead:
    """A normalized, enriched lead ready for scoring and outreach."""

    lead_id: str
    full_name: str
    title: str
    company: str
    company_domain: str
    location: str
    region: str
    seniority: str
    industry: str
    email: str
    linkedin_url: str
    source: str
    icp_score: int
    icp_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchProfile:
    """Structured context a research agent produces before outreach writing."""

    lead_id: str
    full_name: str
    title: str
    company: str
    icp_score: int | float | str
    match_score: float
    lead_summary: str
    icp_fit: str
    personalization_angles: list[str] = field(default_factory=list)
    possible_pain_points: list[str] = field(default_factory=list)
    outreach_hook: str = ""
    missing_info: list[str] = field(default_factory=list)
    source_context: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OutreachMessageDraft:
    """A first outbound message generated from a research profile."""

    lead_id: str
    subject: str
    body: str
    call_to_action: str
    personalization_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OutreachReview:
    """LLM review result for an outreach draft."""

    approved: bool
    score: int
    checks: dict[str, bool] = field(default_factory=dict)
    feedback: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OutreachWorkflowRun:
    """End-to-end orchestration output for research -> write -> review."""

    query: str
    profile: ResearchProfile
    draft: OutreachMessageDraft
    review: OutreachReview

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
