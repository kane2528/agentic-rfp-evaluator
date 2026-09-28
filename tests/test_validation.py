import pytest

from tools.validator import validate_evaluation


CRITERIA = [
    {"criterion_id": 1, "name": "Technical", "weight": 50, "max_score": 10},
    {"criterion_id": 2, "name": "Security", "weight": 50, "max_score": 5},
]


def test_missing_criterion_added_with_zero_and_warning():
    result = validate_evaluation({"supplier_name": "A", "criteria": [{"criterion_id": 1, "score": 8, "max_score": 10, "evidence": "API described"}]}, CRITERIA, "A")
    missing = result["criteria"][1]
    assert missing["score"] == 0
    assert "not present" in missing["evidence"]
    assert any("Missing criterion" in w for w in result["warnings"])


def test_score_clipped_to_range_and_configured_max_is_source_of_truth():
    result = validate_evaluation({"supplier_name": "A", "criteria": [
        {"criterion_id": 1, "score": -2, "max_score": 10},
        {"criterion_id": 2, "score": 20, "max_score": 10}], "risks": []}, CRITERIA, "A")
    assert [c["score"] for c in result["criteria"]] == [0, 5]
    assert result["criteria"][1]["max_score"] == 5
    assert any("clipped" in w for w in result["warnings"])
    assert any("max_score" in w for w in result["warnings"])


def test_malformed_json_attempts_safe_recovery_then_fails_clearly():
    with pytest.raises(ValueError, match="Malformed JSON"):
        validate_evaluation("Here is your answer: {broken", CRITERIA, "A")


def test_missing_evidence_is_preserved_and_warned_by_explicit_text():
    result = validate_evaluation({"supplier_name": "A", "criteria": [{"criterion_id": 1, "score": 6, "max_score": 10}, {"criterion_id": 2, "score": 4, "max_score": 5}]}, CRITERIA, "A")
    assert all("Evidence is not present" in c["evidence"] for c in result["criteria"])


def test_json_fence_and_duplicate_criteria_warning():
    raw = '```json\n{"supplier_name":"A","criteria":[{"criterion_id":1,"score":3},{"criterion_id":1,"score":9},{"criterion_id":2,"score":4}]}\n```'
    result = validate_evaluation(raw, CRITERIA, "A")
    assert result["criteria"][0]["score"] == 3
    assert any("Duplicate" in w for w in result["warnings"])
