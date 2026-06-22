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
