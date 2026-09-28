"""Pydantic contracts for model output and normalized evaluation data."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CriterionEvaluation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    criterion_id: int
    score: float
    max_score: float | None = None
    justification: str = ""
    evidence: str = ""


class EvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    supplier_name: str
    criteria: list[CriterionEvaluation] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    overall_summary: str = ""

