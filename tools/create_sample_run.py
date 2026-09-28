"""Create a reproducible, no-key DEMO run and export it to outputs/sample_run.json."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from agents.orchestrator import run_evaluation
from database.database import initialize_database, seed_criteria, list_criteria


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.environ.pop("LLM_API_KEY", None)
    os.environ["RFP_DATABASE_PATH"] = str(root / "database" / "rfp_evaluator.db")
    initialize_database()
    seed_criteria()
    metadata = [
        ("Apex Systems", "apex_systems.pdf", "2025-01-10", 8.5),
        ("BrightPath Tech", "brightpath_tech.pdf", "2025-01-12", 3.0),
        ("NexaWorks", "nexaworks.pdf", "2025-01-09", 8.0),
        ("Orbit Digital", "orbit_digital.pdf", "2025-01-11", 9.5),
    ]
    inputs = [{"supplier_name": name, "submission_date": submitted, "experience_rating": experience,
               "pdf_bytes": (root / "sample_rfps" / filename).read_bytes()}
              for name, filename, submitted, experience in metadata]
    result = run_evaluation(inputs, list_criteria(active_only=True))
    output = root / "outputs" / "sample_run.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved deterministic DEMO run: {output}")
    print("Ranking: " + " > ".join(s["supplier_name"] for s in result["suppliers"]))


if __name__ == "__main__":
    main()
