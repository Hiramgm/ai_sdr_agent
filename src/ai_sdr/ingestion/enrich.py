from __future__ import annotations

import re
from urllib.parse import urlparse

from ..config import ICPConfig
from ..schemas import Lead, RawLead

SENIORITY_RULES: list[tuple[str, list[str]]] = [
    ("c-level", ["ceo", "cto", "coo", "cmo", "chief"]),
    ("founder", ["founder", "co-founder", "cofounder"]),
    ("vp", ["vp", "vice president"]),
    ("head", ["head of", "head,"]),
    ("director", ["director"]),
    ("manager", ["manager", "lead"]),
    ("individual", ["specialist", "coordinator", "associate", "administrator"]),
]

REGION_RULES: list[tuple[str, list[str]]] = [
    ("uk", ["united kingdom", "uk", "london", "manchester"]),
    ("germany", ["germany", "berlin", "munich", "hamburg"]),
    ("finland", ["finland", "helsinki"]),
    ("remote", ["remote", "worldwide", "anywhere"]),
    ("europe", ["europe", "eu"]),
]


def slugify_company(company: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "", company.lower())
    return cleaned or "company"


def derive_domain(lead: RawLead) -> str:
    if lead.company_website:
        host = urlparse(lead.company_website).netloc or lead.company_website
        return host.lower().lstrip("www.")
    if lead.email and "@" in lead.email:
        return lead.email.split("@", 1)[1].lower()
    return f"{slugify_company(lead.company)}.example"


def detect_seniority(title: str) -> str:
    lowered = title.lower()
    for label, keywords in SENIORITY_RULES:
        if any(keyword in lowered for keyword in keywords):
            return label
    return "unknown"


def detect_region(location: str) -> str:
    lowered = location.lower()
    for label, keywords in REGION_RULES:
        if any(keyword in lowered for keyword in keywords):
            return label
    return "other"


def make_lead_id(lead: RawLead, domain: str) -> str:
    name_slug = re.sub(r"[^a-z0-9]+", "-", lead.full_name.lower()).strip("-")
    return f"{name_slug}@{domain}"


def score_icp(
    title: str,
    seniority: str,
    region: str,
    industry: str,
    icp: ICPConfig,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    lowered_title = title.lower()

    if any(target in lowered_title for target in icp.target_titles):
        score += 40
        reasons.append("Title matches target buyer persona")
    if seniority in icp.target_seniorities:
        score += 25
        reasons.append(f"Seniority '{seniority}' is a decision maker")
    if region in icp.target_regions:
        score += 20
        reasons.append(f"Region '{region}' is in target market")
    if industry.lower() in icp.target_industries:
        score += 15
        reasons.append(f"Industry '{industry}' fits ICP")

    if not reasons:
        reasons.append("No strong ICP signals matched")

    return min(score, 100), reasons


def enrich_lead(raw: RawLead, icp: ICPConfig) -> Lead:
    domain = derive_domain(raw)
    seniority = detect_seniority(raw.title)
    region = detect_region(raw.location)
    icp_score, reasons = score_icp(raw.title, seniority, region, raw.industry, icp)

    return Lead(
        lead_id=make_lead_id(raw, domain),
        full_name=raw.full_name,
        title=raw.title,
        company=raw.company,
        company_domain=domain,
        location=raw.location,
        region=region,
        seniority=seniority,
        industry=raw.industry,
        email=raw.email,
        linkedin_url=raw.linkedin_url,
        source=raw.source,
        icp_score=icp_score,
        icp_reasons=reasons,
    )


def enrich_leads(raws: list[RawLead], icp: ICPConfig) -> list[Lead]:
    return [enrich_lead(raw, icp) for raw in raws]
