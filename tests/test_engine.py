import pandas as pd
import pytest

from engine import compare_policies, generate_cases, score_cases, select_with_capacity, run


def test_capacity_is_respected_and_filled_after_oversized_case():
    cases = pd.DataFrame([
        {"case_id": "large", "risk": 1.0, "uncertainty": 0.1, "expected_loss": 1000, "novelty": 0.1, "review_minutes": 70, "age_hours": 1, "severe": 1, "true_loss": 1000, "information_gain": 0.1},
        {"case_id": "fit-a", "risk": .8, "uncertainty": .2, "expected_loss": 500, "novelty": .2, "review_minutes": 35, "age_hours": 1, "severe": 1, "true_loss": 500, "information_gain": .2},
        {"case_id": "fit-b", "risk": .7, "uncertainty": .3, "expected_loss": 400, "novelty": .3, "review_minutes": 20, "age_hours": 1, "severe": 1, "true_loss": 400, "information_gain": .3},
    ])
    selected, _, _ = select_with_capacity(cases, "risk", capacity_hours=1)
    assert selected.review_minutes.sum() <= 60
    assert set(selected.case_id) == {"fit-a", "fit-b"}


def test_policy_scores_preserve_baseline_meaning():
    cases = generate_cases(seed=2, n=100)
    risk = score_cases(cases, "risk")
    uncertainty = score_cases(cases, "uncertainty")
    assert risk["priority_score"].equals(cases["risk"])
    assert uncertainty["priority_score"].equals(cases["uncertainty"])


def test_zero_and_negative_capacity():
    cases = generate_cases(seed=3, n=100)
    selected, remaining, _ = select_with_capacity(cases, "hybrid", capacity_hours=0)
    assert selected.empty and len(remaining) == len(cases)
    with pytest.raises(ValueError):
        select_with_capacity(cases, "hybrid", capacity_hours=-1)


def test_policy_comparison_has_all_policies():
    cases = generate_cases(seed=3, n=2500)
    comparison = compare_policies(cases, capacity_hours=30, seed=3)
    assert set(comparison.policy) == {"random", "risk", "uncertainty", "expected_value", "hybrid"}
    assert comparison["capacity_utilization"].between(0, 1).all()


def test_run_is_reproducible_and_hashed():
    *_, first = run(seed=4, n=1000, capacity_hours=20, policy="hybrid")
    *_, second = run(seed=4, n=1000, capacity_hours=20, policy="hybrid")
    assert first["Selected-case SHA-256"] == second["Selected-case SHA-256"]
    assert first["Selected cases"] > 0
    assert first["Synthetic queue"] == "Yes"
