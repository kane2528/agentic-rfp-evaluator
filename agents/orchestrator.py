"""Orchestrator Agent: execute the required tools in sequence for a supplier batch."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from agents.evaluation_agent import EvaluationAgentError, evaluate
from database.database import create_run, persist_results, save_run_export, update_run_status
from tools.pdf_extractor import extract_pdf_text
from tools.metadata import validate_supplier_metadata
from tools.ranking import TIE_BREAK_RULES, rank_suppliers
from tools.validator import validate_evaluation

ProgressCallback = Callable[[int, str, str], None]


def run_evaluation(inputs: list[dict[str, Any]], criteria: list[dict[str, Any]], progress: ProgressCallback | None = None) -> dict[str, Any]:
    validate_supplier_metadata(inputs)
    if not criteria:
        raise ValueError("Activate at least one evaluation criterion.")
    weight_sum = sum(float(c["weight"]) for c in criteria)
    if abs(weight_sum - 100.0) > 1e-6:
        raise ValueError(f"Active criteria weights total {weight_sum:g}%; they must total 100%. Update Criteria before evaluating.")
    run_id = f"RFP-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    create_run(run_id, created_at, "RUNNING", criteria)
    normalized: list[dict[str, Any]] = []
    modes: set[str] = set()
    try:
        for index, entry in enumerate(inputs):
            name = entry["supplier_name"].strip()
            if progress:
                progress(index, "Extracting PDF", name)
            text = extract_pdf_text(entry["pdf_bytes"])
            if progress:
                progress(index, "Evaluating proposal", name)
            raw, mode = evaluate(name, criteria, text)
            modes.add(mode)
            if progress:
                progress(index, "Validating AI output", name)
            result = validate_evaluation(raw, criteria, name)
            result.update({"submission_date": entry["submission_date"], "experience_rating": float(entry["experience_rating"])})
            normalized.append(result)
            if progress:
                progress(index + 1, "Supplier evaluated", name)
        if progress:
            progress(len(inputs), "Calculating scores and criterion benchmarks", "All suppliers")
        if progress:
            progress(len(inputs), "Ranking suppliers", "All suppliers")
        ranked = rank_suppliers(normalized, criteria)
        if progress:
            progress(len(inputs), "Saving results", run_id)
        export = {"rfp_run_id": run_id, "created_at": created_at, "status": "COMPLETED",
                  "mode": "DEMO" if modes == {"DEMO"} else ("LLM" if modes == {"LLM"} else "MIXED"),
                  "criteria": criteria, "suppliers": ranked,
                  "ranking": [{"rank": s["final_rank"], "supplier_name": s["supplier_name"], "ppi": s["ppi"]} for s in ranked],
                  "tie_break_rules": TIE_BREAK_RULES,
                  "warnings": [w for s in ranked for w in s["warnings"]]}
        persist_results(run_id, ranked)
        save_run_export(run_id, export)
        update_run_status(run_id, "COMPLETED")
        return export
    except Exception as exc:
        update_run_status(run_id, "FAILED", str(exc))
        if isinstance(exc, (ValueError, EvaluationAgentError)):
            raise
        raise RuntimeError(f"Evaluation run {run_id} failed: {exc}") from exc
