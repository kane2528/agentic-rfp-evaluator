from copy import deepcopy

from tools.metadata import validate_supplier_metadata
from tools.ranking import rank_suppliers
from database.database import create_run, get_run, initialize_database, persist_results, save_run_export, seed_criteria


def test_alphabetical_final_tie_break():
    criteria = [{"criterion_id": 1, "name": "Quality", "weight": 100, "max_score": 10}]
    suppliers = [{"supplier_name": name, "submission_date": "2024-01-01", "experience_rating": 5,
                  "criteria": [{"criterion_id": 1, "name": "Quality", "score": 8, "max_score": 10}], "risks": [], "warnings": []}
                 for name in ["Zulu", "alpha", "Bravo"]]
    result = rank_suppliers(suppliers, criteria)
    assert [s["supplier_name"] for s in result] == ["alpha", "Bravo", "Zulu"]


@__import__("pytest").mark.parametrize("changes, message", [
    ({"supplier_name": ""}, "name is required"),
    ({"submission_date": "not-a-date"}, "valid ISO date"),
    ({"experience_rating": 11}, "from 0 to 10"),
    ({"experience_rating": "x"}, "must be a number"),
])
def test_invalid_supplier_metadata(changes, message):
    item = {"supplier_name": "Supplier", "submission_date": "2024-03-01", "experience_rating": 5, "pdf_bytes": b"pdf"}
    item.update(changes)
    try:
        validate_supplier_metadata([item])
    except ValueError as exc:
        assert message in str(exc)
    else:
        raise AssertionError("expected metadata validation failure")


def test_complete_result_persistence(tmp_path):
    db = tmp_path / "persist.db"
    initialize_database(db)
    seed_criteria(db)
    criteria = [{"criterion_id": 1, "name": "Quality", "weight": 100, "max_score": 10}]
    run_id = "RFP-TEST-PERSIST"
    create_run(run_id, "2025-01-01T00:00:00+00:00", "RUNNING", criteria, db)
    supplier = {"supplier_name": "A", "submission_date": "2024-01-01", "experience_rating": 7,
                "criteria": [{"criterion_id": 1, "name": "Quality", "score": 8, "max_score": 10}], "risks": ["Risk"],
                "overall_summary": "Complete summary", "warnings": ["Visible warning"]}
    ranked = rank_suppliers([supplier], criteria)
    persist_results(run_id, ranked, db)
    export = {"rfp_run_id": run_id, "created_at": "2025-01-01T00:00:00+00:00", "status": "COMPLETED", "mode": "DEMO",
              "criteria": criteria, "suppliers": ranked, "ranking": [{"rank": 1, "supplier_name": "A", "ppi": 80}],
              "tie_break_rules": ["Higher PPI first"], "warnings": ["Visible warning"]}
    save_run_export(run_id, export, db)
    saved = get_run(run_id, db)
    assert saved["status"] == "COMPLETED"
    assert saved["criteria"] == criteria
    assert saved["suppliers"][0]["risks"] == ["Risk"]
    assert saved["suppliers"][0]["warnings"] == ["Visible warning"]
    assert saved["suppliers"][0]["final_rank"] == 1
    assert saved["mode"] == "DEMO"
    assert saved["ranking"][0]["supplier_name"] == "A"
