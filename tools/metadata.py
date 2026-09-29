"""Validation for supplier batch metadata before orchestration begins."""
from __future__ import annotations

from datetime import date
from typing import Any


def validate_supplier_metadata(inputs: list[dict[str, Any]]) -> None:
    if not inputs:
        raise ValueError("Upload at least one supplier proposal document.")
    names: set[str] = set()
    for index, item in enumerate(inputs, 1):
        name = item.get("supplier_name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Supplier {index}: supplier name is required.")
        key = name.strip().casefold()
        if key in names:
            raise ValueError(f"Supplier names must be unique within a batch: {name.strip()}.")
        names.add(key)
        raw_date = item.get("submission_date")
        try:
            submitted = date.fromisoformat(str(raw_date))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name.strip()}: submission date must be a valid ISO date (YYYY-MM-DD).") from exc
        if submitted > date.today():
            raise ValueError(f"{name.strip()}: submission date cannot be in the future.")
        try:
            experience = float(item.get("experience_rating"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name.strip()}: experience rating must be a number from 0 to 10.") from exc
        if not 0 <= experience <= 10:
            raise ValueError(f"{name.strip()}: experience rating must be from 0 to 10.")
        if not isinstance(item.get("pdf_bytes"), bytes) or not item["pdf_bytes"]:
            raise ValueError(f"{name.strip()}: proposal document is empty or missing.")
