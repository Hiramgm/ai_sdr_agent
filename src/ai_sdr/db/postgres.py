"""PostgreSQL persistence for structured data (leads and campaigns).

We use psycopg 3 with plain SQL so the schema and queries stay explicit and
easy to reason about. The `leads` table mirrors the `Lead` dataclass; the
`campaigns` table is a small scaffold we will grow later.
"""

from __future__ import annotations

import psycopg
from psycopg.types.json import Jsonb

from ..config import SETTINGS
from ..schemas import Lead

CREATE_LEADS_TABLE = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id        TEXT PRIMARY KEY,
    full_name      TEXT NOT NULL,
    title          TEXT,
    company        TEXT,
    company_domain TEXT,
    location       TEXT,
    region         TEXT,
    seniority      TEXT,
    industry       TEXT,
    email          TEXT,
    linkedin_url   TEXT,
    source         TEXT,
    icp_score      INTEGER NOT NULL DEFAULT 0,
    icp_reasons    JSONB   NOT NULL DEFAULT '[]'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

CREATE_CAMPAIGNS_TABLE = """
CREATE TABLE IF NOT EXISTS campaigns (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

# Upsert: insert a lead, or update it in place if we have seen its lead_id
# before. This makes re-running the pipeline idempotent (no duplicate rows).
UPSERT_LEAD = """
INSERT INTO leads (
    lead_id, full_name, title, company, company_domain, location, region,
    seniority, industry, email, linkedin_url, source, icp_score, icp_reasons
)
VALUES (
    %(lead_id)s, %(full_name)s, %(title)s, %(company)s, %(company_domain)s,
    %(location)s, %(region)s, %(seniority)s, %(industry)s, %(email)s,
    %(linkedin_url)s, %(source)s, %(icp_score)s, %(icp_reasons)s
)
ON CONFLICT (lead_id) DO UPDATE SET
    full_name      = EXCLUDED.full_name,
    title          = EXCLUDED.title,
    company        = EXCLUDED.company,
    company_domain = EXCLUDED.company_domain,
    location       = EXCLUDED.location,
    region         = EXCLUDED.region,
    seniority      = EXCLUDED.seniority,
    industry       = EXCLUDED.industry,
    email          = EXCLUDED.email,
    linkedin_url   = EXCLUDED.linkedin_url,
    source         = EXCLUDED.source,
    icp_score      = EXCLUDED.icp_score,
    icp_reasons    = EXCLUDED.icp_reasons,
    updated_at     = now();
"""


def connect(dsn: str | None = None, connect_timeout: int = 10) -> psycopg.Connection:
    """Open a PostgreSQL connection using the configured DSN.

    A connect timeout guarantees we fail fast instead of hanging forever if the
    database is unreachable.
    """
    return psycopg.connect(dsn or SETTINGS.postgres_url, connect_timeout=connect_timeout)


def init_schema(conn: psycopg.Connection) -> None:
    """Create tables if they do not already exist."""
    with conn.cursor() as cur:
        cur.execute(CREATE_LEADS_TABLE)
        cur.execute(CREATE_CAMPAIGNS_TABLE)
    conn.commit()


def _lead_to_params(lead: Lead) -> dict[str, object]:
    params = lead.to_dict()
    # JSON columns must be wrapped so psycopg adapts the list to JSONB.
    params["icp_reasons"] = Jsonb(lead.icp_reasons)
    return params


def upsert_leads(conn: psycopg.Connection, leads: list[Lead]) -> int:
    """Insert or update the given leads. Returns the number of rows written."""
    if not leads:
        return 0
    params = [_lead_to_params(lead) for lead in leads]
    with conn.cursor() as cur:
        cur.executemany(UPSERT_LEAD, params)
    conn.commit()
    return len(params)


def count_leads(conn: psycopg.Connection) -> int:
    """Return the total number of leads currently stored."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM leads;")
        row = cur.fetchone()
    return int(row[0]) if row else 0
