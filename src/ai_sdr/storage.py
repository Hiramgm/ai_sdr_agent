from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .schemas import Lead, RawLead


def write_jsonl(records: Iterable[dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_raw_leads(raws: list[RawLead], output_path: Path) -> None:
    write_jsonl((raw.to_dict() for raw in raws), output_path)


def write_leads(leads: list[Lead], output_path: Path) -> None:
    write_jsonl((lead.to_dict() for lead in leads), output_path)
