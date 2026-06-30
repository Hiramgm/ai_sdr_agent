from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_sdr.config import REPORTS_DIR
from ai_sdr.evaluation.outreach import run_from_dict
from ai_sdr.observability import log_event, trace_span
from ai_sdr.schemas import OutreachEvaluation, OutreachWorkflowRun


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export an outreach run to a real Ragas Dataset.")
    parser.add_argument("run_json", type=Path, help="Path to an OutreachWorkflowRun JSON file.")
    parser.add_argument("--evaluation-json", type=Path, help="Optional OutreachEvaluation JSON file.")
    parser.add_argument(
        "--dataset-name",
        default="ai_sdr_outreach",
        help="Ragas dataset name.",
    )
    parser.add_argument(
        "--root-dir",
        type=Path,
        help="Ragas local dataset root. Defaults to reports/ragas/.",
    )
    parser.add_argument(
        "--jsonl-output",
        type=Path,
        help="Optional debug JSONL output path. Defaults to reports/evaluation_datasets/ragas_outreach.jsonl.",
    )
    return parser.parse_args()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "outreach"


def _contexts(run: OutreachWorkflowRun) -> list[str]:
    contexts = [
        run.profile.lead_summary,
        run.profile.icp_fit,
        run.profile.outreach_hook,
        *run.profile.personalization_angles,
        *run.profile.possible_pain_points,
        *run.profile.source_context,
    ]
    return [context for context in contexts if context]


def _evaluation_dict(evaluation: OutreachEvaluation | dict[str, Any] | None) -> dict[str, Any]:
    if evaluation is None:
        return {}
    if isinstance(evaluation, OutreachEvaluation):
        return evaluation.to_dict()
    return evaluation


def _install_ragas_vertex_compat() -> None:
    """Work around Ragas 0.4.3's eager legacy VertexAI import.

    Ragas' top-level import currently imports VertexAI from an old
    ``langchain_community`` path even when VertexAI is not used. The shim is
    deliberately tiny and only lets ``from ragas import Dataset`` complete for
    our local Dataset export path.
    """
    module_name = "langchain_community.chat_models.vertexai"
    if module_name not in sys.modules:
        vertex_module = types.ModuleType(module_name)
        vertex_module.ChatVertexAI = type("ChatVertexAI", (object,), {})
        sys.modules[module_name] = vertex_module

    try:
        lc_llms = importlib.import_module("langchain_community.llms")
    except Exception:
        return
    if not hasattr(lc_llms, "VertexAI"):
        lc_llms.VertexAI = type("VertexAI", (object,), {})


def _ragas_dataset_class():
    _install_ragas_vertex_compat()
    try:
        ragas = importlib.import_module("ragas")
    except Exception as error:  # noqa: BLE001 - normalize import failures for CLI/API users.
        raise RuntimeError(
            "Ragas is installed but could not be imported. Try reinstalling dependencies "
            "with `python -m pip install -e .`, or upgrade ragas once the VertexAI import "
            "bug is fixed upstream."
        ) from error
    return ragas.Dataset


def build_ragas_row(
    run: OutreachWorkflowRun,
    evaluation: OutreachEvaluation | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one JSON-serializable row compatible with common RAGAS dataset fields."""
    evaluation_data = _evaluation_dict(evaluation)
    row = {
        "question": run.query,
        "answer": run.draft.body,
        "contexts": _contexts(run),
        "ground_truth": "",
        "metadata": {
            "lead_id": run.profile.lead_id,
            "full_name": run.profile.full_name,
            "company": run.profile.company,
            "subject": run.draft.subject,
            "call_to_action": run.draft.call_to_action,
            "review_score": run.review.score,
            "review_approved": run.review.approved,
            "evaluation": evaluation_data,
            "exported_at": datetime.now(UTC).isoformat(),
        },
    }
    trace_span(
        "ragas_export_row_built",
        inputs={"lead_id": run.profile.lead_id, "query": run.query},
        outputs={"context_count": len(row["contexts"])},
        metadata={"format": "ragas_jsonl"},
    )
    return row


def append_ragas_row(
    row: dict[str, Any],
    output_path: Path | None = None,
) -> Path:
    """Append one RAGAS-style row to a JSONL dataset file."""
    target = output_path or REPORTS_DIR / "evaluation_datasets" / "ragas_outreach.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, default=str) + "\n")
    metadata = row.get("metadata", {})
    log_event(
        "ragas_row_exported",
        {
            "lead_id": metadata.get("lead_id"),
            "output_path": str(target),
        },
    )
    return target


def save_ragas_dataset(
    row: dict[str, Any],
    dataset_name: str = "ai_sdr_outreach",
    root_dir: Path | None = None,
) -> Path:
    """Save one row into a real Ragas local Dataset using the quickstart API."""
    Dataset = _ragas_dataset_class()
    target_root = root_dir or REPORTS_DIR / "ragas"
    target_root.mkdir(parents=True, exist_ok=True)

    dataset = Dataset(name=dataset_name, backend="local/csv", root_dir=str(target_root))
    dataset.append(row)
    dataset.save()

    metadata = row.get("metadata", {})
    log_event(
        "ragas_dataset_saved",
        {
            "lead_id": metadata.get("lead_id"),
            "dataset_name": dataset_name,
            "root_dir": str(target_root),
        },
    )
    trace_span(
        "ragas_dataset_saved",
        inputs={"lead_id": metadata.get("lead_id"), "dataset_name": dataset_name},
        outputs={"root_dir": str(target_root)},
        metadata={"backend": "local/csv"},
    )
    return target_root


def load_evaluation(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("evaluation-json must contain a JSON object.")
    return data


def main() -> None:
    args = parse_args()
    data = json.loads(args.run_json.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("run_json must contain a JSON object.")
    run = run_from_dict(data)
    row = build_ragas_row(run, load_evaluation(args.evaluation_json))
    root_dir = save_ragas_dataset(row, dataset_name=args.dataset_name, root_dir=args.root_dir)
    jsonl_path = append_ragas_row(row, args.jsonl_output)
    print(f"Saved real Ragas Dataset `{args.dataset_name}` under: {root_dir}")
    print(f"Also wrote JSONL debug row for `{_slugify(run.profile.lead_id)}`: {jsonl_path}")


if __name__ == "__main__":
    main()
