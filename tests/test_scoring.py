from utils.scoring import absolute_weighted_score, benchmark_and_peer_metrics
from tools.ranking import rank_suppliers


CRITERIA = [
    {"criterion_id": 1, "name": "Technical", "weight": 60.0, "max_score": 10.0},
    {"criterion_id": 2, "name": "Commercial", "weight": 40.0, "max_score": 10.0},
]


def supplier(name, first, second, date="2025-01-01", experience=5):
    return {"supplier_name": name, "submission_date": date, "experience_rating": experience,
            "criteria": [{"criterion_id": 1, "name": "Technical", "score": first, "max_score": 10},
                         {"criterion_id": 2, "name": "Commercial", "score": second, "max_score": 10}],
            "risks": [], "overall_summary": "summary", "warnings": []}


def test_absolute_weighted_score():
    assert absolute_weighted_score([{"criterion_id": 1, "score": 8}, {"criterion_id": 2, "score": 5}], CRITERIA) == 68


def test_benchmark_gap_relative_and_weighted_ppi():
    ranked = rank_suppliers([supplier("A", 10, 5), supplier("B", 5, 10)], CRITERIA)
    by_name = {s["supplier_name"]: s for s in ranked}
    a = {c["criterion_id"]: c for c in by_name["A"]["criteria"]}
    assert a[1]["benchmark"] == 10
    assert a[1]["gap"] == 0
    assert a[2]["gap"] == -5
    assert a[2]["relative_performance_pct"] == 50
    assert by_name["A"]["ppi"] == 80
    assert by_name["B"]["ppi"] == 70


def test_benchmark_zero_has_safe_relative_value():
    criteria = [{"criterion_id": 1, "name": "Only", "weight": 100.0, "max_score": 10.0}]
    ranked = rank_suppliers([{"supplier_name": n, "submission_date": "2025-01-01", "experience_rating": 1,
                              "criteria": [{"criterion_id": 1, "name": "Only", "score": 0, "max_score": 10}], "risks": [], "warnings": []}
                             for n in ["A", "B"]], criteria)
    assert all(s["ppi"] == 100 for s in ranked)
    assert all(s["criteria"][0]["relative_performance_pct"] == 100 for s in ranked)


def test_ranking_tie_break_order_and_deterministic_repeat():
    entries = [supplier("Zeta", 8, 8, "2025-02-01", 9), supplier("Alpha", 8, 8, "2025-01-01", 2),
               supplier("Beta", 8, 8, "2025-01-01", 8), supplier("Aardvark", 8, 8, "2025-01-01", 8)]
    first = rank_suppliers([dict(s, criteria=[dict(c) for c in s["criteria"]]) for s in entries], CRITERIA)
    second = rank_suppliers([dict(s, criteria=[dict(c) for c in s["criteria"]]) for s in entries], CRITERIA)
    expected = ["Aardvark", "Beta", "Alpha", "Zeta"]
    assert [s["supplier_name"] for s in first] == expected
    assert [s["supplier_name"] for s in second] == expected
    assert [s["final_rank"] for s in first] == [1, 2, 3, 4]


def test_weight_sum_is_required():
    try:
        rank_suppliers([supplier("A", 5, 5)], [{**CRITERIA[0], "weight": 30}, {**CRITERIA[1], "weight": 30}])
    except ValueError as exc:
        assert "100%" in str(exc)
    else:
        raise AssertionError("expected weight validation")
