"""Deterministic score, benchmark, PPI, and stable tie-break ranking tool."""
from __future__ import annotations

from typing import Any

from utils.scoring import absolute_weighted_score, benchmark_and_peer_metrics

TIE_BREAK_RULES = [
    "Higher Peer Performance Index (PPI) first.",
    "Earlier submission date first.",
    "Higher historical experience rating first.",
    "Supplier name ascending alphabetically (case-insensitive).",
    "Sequential ranks are assigned only after the complete sort.",
]


def rank_suppliers(suppliers: list[dict[str, Any]], criteria: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not criteria or abs(sum(float(c["weight"]) for c in criteria) - 100.0) > 1e-6:
        raise ValueError("Active criterion weights must total exactly 100% before ranking.")
    for supplier in suppliers:
        supplier["criteria_by_id"] = {int(c["criterion_id"]): c for c in supplier["criteria"]}
        supplier["absolute_score"] = absolute_weighted_score(supplier["criteria"], criteria)
    metrics = benchmark_and_peer_metrics(suppliers, criteria)
    for supplier in suppliers:
        item_metrics = metrics[supplier["supplier_name"]]
        supplier["ppi"] = item_metrics["_ppi"]["ppi"]
        for criterion in supplier["criteria"]:
            criterion.update(item_metrics[int(criterion["criterion_id"])])
        supplier.pop("criteria_by_id", None)
    ranked = sorted(suppliers, key=lambda s: (-float(s["ppi"]), str(s["submission_date"]), -float(s["experience_rating"]), str(s["supplier_name"]).casefold()))
    for rank, supplier in enumerate(ranked, start=1):
        supplier["final_rank"] = rank
    return ranked
