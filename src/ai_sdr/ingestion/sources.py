from __future__ import annotations

import csv
import json
from pathlib import Path

from ..sample_leads import get_sample_leads
from ..schemas import RawLead

RAW_LEAD_FIELDS = {
    "full_name",
    "title",
    "company",
    "location",
    "email",
    "linkedin_url",
    "company_website",
    "industry",
    "source",
}


def _raw_from_dict(record: dict[str, object]) -> RawLead:
    values = {key: str(record.get(key, "")) for key in RAW_LEAD_FIELDS}
    if not values["source"]:
        values["source"] = "file"
    return RawLead(**values)  # type: ignore[arg-type]


def load_leads_from_json(path: Path) -> list[RawLead]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("leads", [])
    return [_raw_from_dict(record) for record in payload if isinstance(record, dict)]


def load_leads_from_csv(path: Path) -> list[RawLead]:
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [_raw_from_dict(row) for row in reader]


def load_leads_from_file(path: Path) -> list[RawLead]:
    if path.suffix.lower() == ".json":
        return load_leads_from_json(path)
    if path.suffix.lower() == ".csv":
        return load_leads_from_csv(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def load_raw_leads(source: str, input_path: Path | None) -> list[RawLead]:
    if source == "sample":
        return get_sample_leads()
    if source == "file":
        if input_path is None:
            raise ValueError("--input is required when --source file")
        return load_leads_from_file(input_path)
    raise ValueError(f"Unsupported source: {source}")
