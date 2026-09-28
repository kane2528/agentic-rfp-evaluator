"""Pure business calculations. No LLM or database access."""
from __future__ import annotations

from typing import Any


def absolute_weighted_score(criteria_scores: list[dict[str, Any]], criteria: list[dict[str, Any]]) -> float:
    by_id = {int(item["criterion_id"]): float(item["score"]) for item in criteria_scores}
    total = sum(float(c["weight"]) for c in criteria)
    if total <= 0:
        raise ValueError("Active criteria must have a positive total weight.")
    return sum((by_id[int(c["criterion_id"])] / float(c["max_score"])) * float(c["weight"]) for c in criteria) * (100.0 / total)


def benchmark_and_peer_metrics(suppliers: list[dict[str, Any]], criteria: list[dict[str, Any]]) -> dict[str, dict[int, dict[str, float]]]:
    benchmarks = {int(c["criterion_id"]): max((float(s["criteria_by_id"][int(c["criterion_id"])]["score"]) for s in suppliers), default=0.0) for c in criteria}
    results: dict[str, dict[int, dict[str, float]]] = {}
    weight_total = sum(float(c["weight"]) for c in criteria)
    for supplier in suppliers:
        metrics = {}
        weighted_relative = 0.0
        for criterion in criteria:
            cid = int(criterion["criterion_id"])
            score, benchmark = float(supplier["criteria_by_id"][cid]["score"]), benchmarks[cid]
            relative = (score / benchmark * 100.0) if benchmark > 0 else 100.0
            metrics[cid] = {"benchmark": benchmark, "gap": score - benchmark, "relative_performance_pct": relative}
            weighted_relative += relative * float(criterion["weight"])
        results[supplier["supplier_name"]] = {**metrics, "_ppi": {"ppi": weighted_relative / weight_total if weight_total else 0.0}}
    return results
