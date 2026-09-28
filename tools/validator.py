"""Validation tool: parse, normalize, and make every repair auditable."""
from __future__ import annotations

import json
import math
import re
from typing import Any

from models.schemas import CriterionEvaluation, EvaluationResponse


def _safe_text(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def parse_json_response(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise ValueError("LLM response was not JSON text.")
    content = raw.strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as original:
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end <= start:
            raise ValueError(f"Malformed JSON: {original.msg}") from original
        try:
            parsed = json.loads(content[start:end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON must be an object.")
    return parsed


def validate_evaluation(raw: str | dict[str, Any], criteria: list[dict[str, Any]], expected_supplier: str) -> dict[str, Any]:
    """Return normalized supplier evaluation with all detected problems in warnings.

    Missing criteria use score 0 and an explicit absent-evidence explanation.
    Duplicate criterion entries keep the first and record a warning.
    """
    data = parse_json_response(raw)
    warnings: list[str] = []
    try:
        # Pydantic checks the response contract before the tool applies policy repairs.
        EvaluationResponse.model_validate(data)
    except Exception as exc:
        warnings.append(f"Pydantic schema validation required normalization: {str(exc).splitlines()[0][:240]}.")
    if not isinstance(data.get("criteria"), list):
        warnings.append("Criteria array was missing or malformed; no criterion scores were accepted.")
        data["criteria"] = []
    candidate_by_id: dict[int, dict[str, Any]] = {}
    for item in data["criteria"]:
        if not isinstance(item, dict):
            warnings.append("Ignored a malformed criterion entry that was not an object.")
            continue
        try:
            CriterionEvaluation.model_validate(item)
        except Exception:
            # Keep the raw object for safe clipping/coercion and make the issue visible.
            warnings.append("A criterion entry failed Pydantic validation and was normalized where possible.")
        try:
            cid = int(item.get("criterion_id"))
        except (TypeError, ValueError):
            warnings.append("Ignored a criterion entry with an invalid criterion_id.")
            continue
        if cid in candidate_by_id:
            warnings.append(f"Duplicate result for criterion_id {cid}; kept the first entry.")
            continue
        candidate_by_id[cid] = item
    active_ids = {int(c["criterion_id"]) for c in criteria}
    for extra in sorted(set(candidate_by_id) - active_ids):
        warnings.append(f"Ignored inactive or unknown criterion_id {extra}.")

    normalized: list[dict[str, Any]] = []
    for criterion in criteria:
        cid = int(criterion["criterion_id"])
        configured_max = float(criterion["max_score"])
        item = candidate_by_id.get(cid)
        if item is None:
            warnings.append(f"Missing criterion '{criterion['name']}'; normalized score to 0.")
            normalized.append({"criterion_id": cid, "name": criterion["name"], "score": 0.0, "max_score": configured_max,
                               "justification": "No model evaluation was returned for this criterion.",
                               "evidence": "Evidence is not present in the evaluation response."})
            continue
        given_max = item.get("max_score")
        try:
            if given_max is not None and not math.isclose(float(given_max), configured_max):
                warnings.append(f"Criterion '{criterion['name']}' max_score {given_max} did not match configured {configured_max}; used database value.")
        except (TypeError, ValueError):
            warnings.append(f"Criterion '{criterion['name']}' had invalid max_score; used database value {configured_max}.")
        try:
            score = float(item.get("score"))
            if not math.isfinite(score):
                raise ValueError
        except (TypeError, ValueError):
            score = 0.0
            warnings.append(f"Criterion '{criterion['name']}' had an invalid score; normalized to 0.")
        clipped = min(configured_max, max(0.0, score))
        if clipped != score:
            warnings.append(f"Criterion '{criterion['name']}' score {score:g} was clipped to {clipped:g}.")
        normalized.append({"criterion_id": cid, "name": criterion["name"], "score": clipped, "max_score": configured_max,
                           "justification": _safe_text(item.get("justification"), "No justification was supplied."),
                           "evidence": _safe_text(item.get("evidence"), "Evidence is not present in the evaluation response.")})
    model_name = data.get("supplier_name")
    if model_name and str(model_name).strip() != expected_supplier:
        warnings.append(f"LLM supplier name '{str(model_name).strip()}' did not match entered name '{expected_supplier}'; used entered metadata.")
    risks = data.get("risks", [])
    if not isinstance(risks, list):
        warnings.append("Risks were malformed; normalized to an empty list.")
        risks = []
    risks = [str(r).strip() for r in risks if str(r).strip()]
    return {"supplier_name": expected_supplier, "criteria": normalized, "risks": risks,
            "overall_summary": _safe_text(data.get("overall_summary"), "No overall summary was supplied."), "warnings": warnings}
