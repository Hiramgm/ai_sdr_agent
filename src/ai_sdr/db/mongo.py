"""MongoDB persistence for unstructured data (raw leads and run logs).

MongoDB is a good fit here because raw source data can have a loose, changing
shape, and run logs are append-only history. We use two collections:

- ``raw_leads``: the lead exactly as it arrived from a source (upserted on a
  natural key so re-runs do not create duplicates).
- ``run_logs``: one document per pipeline run, capturing what happened.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database

from ..config import SETTINGS
from ..schemas import RawLead

DEFAULT_DB_NAME = "ai_sdr"


def connect(uri: str | None = None, server_timeout_ms: int = 10000) -> MongoClient:
    """Open a MongoClient. Fails fast if the server cannot be reached."""
    return MongoClient(uri or SETTINGS.mongodb_uri, serverSelectionTimeoutMS=server_timeout_ms)


def get_db(client: MongoClient) -> Database:
    """Return the target database (from the URI if present, else the default)."""
    try:
        return client.get_default_database()
    except Exception:
        return client[DEFAULT_DB_NAME]


def ping(client: MongoClient) -> bool:
    """Verify connectivity by issuing a ping command."""
    client.admin.command("ping")
    return True


def _raw_lead_key(raw: RawLead) -> str:
    """Stable id for a raw lead so repeated ingests upsert instead of duplicate."""
    basis = raw.email or raw.linkedin_url or f"{raw.full_name}|{raw.company}"
    return hashlib.sha1(basis.lower().encode("utf-8")).hexdigest()


def store_raw_leads(db: Database, raws: list[RawLead]) -> int:
    """Upsert raw leads into the ``raw_leads`` collection. Returns count written."""
    if not raws:
        return 0
    collection = db["raw_leads"]
    now = datetime.now(timezone.utc)
    for raw in raws:
        doc = raw.to_dict()
        doc["ingested_at"] = now
        collection.replace_one({"_id": _raw_lead_key(raw)}, {"_id": _raw_lead_key(raw), **doc}, upsert=True)
    return len(raws)


def log_run(db: Database, info: dict[str, Any]) -> str:
    """Append one run-log document. Returns the inserted document id as a string."""
    doc = {"created_at": datetime.now(timezone.utc), **info}
    result = db["run_logs"].insert_one(doc)
    return str(result.inserted_id)
