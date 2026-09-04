from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

POLICIES = ["random", "risk", "uncertainty", "expected_value", "hybrid"]


def generate_cases(seed: int = 42, n: int = 6000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    risk = np.clip(rng.beta(2.1, 5.2, n) + rng.normal(0, .025, n), 0, 1)
    uncertainty = np.clip(4 * risk * (1 - risk) + rng.normal(0, .08, n), 0, 1)
    expected_loss = np.exp(rng.normal(5.0, 1.0, n))
    novelty = np.clip(rng.beta(2.0, 4.0, n) + .18 * (uncertainty > .72), 0, 1)
    review_minutes = np.clip(rng.gamma(2.2, 4.0, n) + 2, 2, 45)
    age_hours = np.clip(rng.exponential(14, n), 0, 96)
    severity_score = .42 * risk + .27 * np.tanh(expected_loss / 700) + .18 * novelty + .13 * uncertainty
    severe = (severity_score + rng.normal(0, .08, n) > .62).astype(int)
    true_loss = expected_loss * (.35 + .65 * severe)
    information_gain = np.clip(.58 * uncertainty + .42 * novelty, 0, 1)
    return pd.DataFrame({
        "case_id": [f"case_{i:06d}" for i in range(n)],
        "risk": risk,
        "uncertainty": uncertainty,
        "expected_loss": expected_loss,
        "novelty": novelty,
        "review_minutes": review_minutes,
        "age_hours": age_hours,
        "severe": severe,
        "true_loss": true_loss,
        "information_gain": information_gain,
    })


def score_cases(df: pd.DataFrame, policy: str, seed: int = 42) -> pd.DataFrame:
    """Create a policy-specific objective without contaminating simpler baselines."""
    rng = np.random.default_rng(seed)
    output = df.copy()
    if policy == "random":
        objective = rng.random(len(output))
    elif policy == "risk":
        objective = output.risk
    elif policy == "uncertainty":
        objective = output.uncertainty
    elif policy == "expected_value":
        objective = output.risk * np.log1p(output.expected_loss)
    elif policy == "hybrid":
        loss = np.log1p(output.expected_loss) / np.log1p(output.expected_loss).max()
        age = np.clip(output.age_hours / 48, 0, 1)
        objective = (
            .34 * output.risk + .24 * loss + .18 * output.uncertainty
            + .16 * output.novelty + .08 * age
        )
    else:
        raise ValueError(f"unknown policy: {policy}")

    output["priority_score"] = objective
    # Duration is handled consistently for every capacity-constrained policy.
    # Information gain is reported separately rather than leaking into risk-only baselines.
    output["utility_per_minute"] = objective / output.review_minutes.clip(lower=1e-9)
    return output


def select_with_capacity(
    df: pd.DataFrame,
    policy: str,
    capacity_hours: float = 80,
    seed: int = 42,
):
    """Greedily allocate a fixed budget while skipping cases that do not fit."""
    if capacity_hours < 0:
        raise ValueError("capacity_hours must be non-negative")
    ranked = score_cases(df, policy, seed).sort_values(
        ["utility_per_minute", "priority_score"], ascending=False
    ).copy()
    budget = capacity_hours * 60
    used = 0.0
    chosen: list[object] = []
    for index, minutes in ranked["review_minutes"].items():
        duration = float(minutes)
        if used + duration <= budget + 1e-9:
            chosen.append(index)
            used += duration

    selected = ranked.loc[chosen].copy()
    selected["allocated_cum_minutes"] = selected.review_minutes.cumsum()
    remaining = ranked.drop(index=chosen).copy()
    ranked["selected"] = ranked.index.isin(chosen)
    return selected, remaining, ranked


def evaluate_policy(df: pd.DataFrame, policy: str, capacity_hours: float = 80, seed: int = 42) -> dict:
    selected, remaining, _ = select_with_capacity(df, policy, capacity_hours, seed)
    all_severe = max(int(df.severe.sum()), 1)
    caught_loss = float(selected.loc[selected.severe.eq(1), "true_loss"].sum())
    hours = float(selected.review_minutes.sum() / 60)
    return {
        "policy": policy,
        "cases_reviewed": int(len(selected)),
        "capacity_used_hours": hours,
        "capacity_utilization": hours / capacity_hours if capacity_hours else 0.0,
        "severe_cases_caught": int(selected.severe.sum()),
        "severe_recall": float(selected.severe.sum() / all_severe),
        "review_precision": float(selected.severe.mean()) if len(selected) else 0.0,
        "risk_caught": caught_loss,
        "risk_per_hour": float(caught_loss / max(hours, 1e-9)),
        "information_gain": float(selected.information_gain.mean()) if len(selected) else 0.0,
        "novelty_coverage": float(selected.novelty.mean()) if len(selected) else 0.0,
        "avg_review_minutes": float(selected.review_minutes.mean()) if len(selected) else 0.0,
        "p95_queue_age_hours": float(selected.age_hours.quantile(.95)) if len(selected) else 0.0,
        "missed_severe_cases": int(remaining.severe.sum()),
        "queue_remaining": int(len(remaining)),
    }


def compare_policies(df: pd.DataFrame, capacity_hours: float = 80, seed: int = 42) -> pd.DataFrame:
    return pd.DataFrame([
        evaluate_policy(df, policy, capacity_hours, seed) for policy in POLICIES
    ]).sort_values("risk_per_hour", ascending=False)


def _selection_sha256(selected: pd.DataFrame) -> str:
    stable = selected[["case_id", "priority_score", "review_minutes"]].sort_values("case_id")
    return hashlib.sha256(stable.to_csv(index=False, float_format="%.12g").encode()).hexdigest()


def run(seed: int = 42, n: int = 6000, capacity_hours: float = 80, policy: str = "hybrid"):
    cases = generate_cases(seed, n)
    selected, remaining, ranked = select_with_capacity(cases, policy, capacity_hours, seed)
    comparison = compare_policies(cases, capacity_hours, seed)
    current = evaluate_policy(cases, policy, capacity_hours, seed)
    baseline = comparison[comparison.policy == "risk"].iloc[0]
    metrics = {
        "Cases in queue": int(len(cases)),
        "Review capacity h": float(capacity_hours),
        "Selected cases": int(len(selected)),
        "Capacity utilization": current["capacity_utilization"],
        "Severe prevalence": float(cases.severe.mean()),
        "Selected severe rate": float(selected.severe.mean()) if len(selected) else 0.0,
        "Severe recall": current["severe_recall"],
        "Risk caught": current["risk_caught"],
        "Risk / analyst hour": current["risk_per_hour"],
        "Risk-efficiency baseline / h": float(baseline.risk_per_hour),
        "Lift vs risk-efficiency baseline": float(
            current["risk_per_hour"] / max(float(baseline.risk_per_hour), 1e-9) - 1
        ),
        "Information gain": current["information_gain"],
        "Novelty coverage": current["novelty_coverage"],
        "Missed severe cases": current["missed_severe_cases"],
        "Queue remaining": current["queue_remaining"],
        "Policies compared": len(POLICIES),
        "Optimization policy": policy,
        "Selected-case SHA-256": _selection_sha256(selected),
        "Synthetic queue": "Yes",
    }
    return cases, selected, remaining, ranked, comparison, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="ReviewerIQ capacity-constrained review optimizer")
    parser.add_argument("--out", default="artifacts")
    parser.add_argument("--rows", type=int, default=6000)
    parser.add_argument("--capacity-hours", type=float, default=80)
    parser.add_argument("--policy", choices=POLICIES, default="hybrid")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    cases, selected, remaining, ranked, comparison, metrics = run(
        args.seed, args.rows, args.capacity_hours, args.policy
    )
    selected.to_csv(output / "selected_reviews.csv", index=False)
    comparison.to_csv(output / "policy_comparison.csv", index=False)
    manifest = {
        "schema_version": 1,
        "seed": args.seed,
        "rows": args.rows,
        "capacity_hours": args.capacity_hours,
        "policy": args.policy,
        "selected_case_sha256": metrics["Selected-case SHA-256"],
        "synthetic": True,
    }
    (output / "benchmark_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    pd.Series(metrics).to_json(output / "metrics.json", indent=2)
    print(pd.Series(metrics).to_string())


if __name__ == "__main__":
    main()
