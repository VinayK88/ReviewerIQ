from engine import generate_cases, select_with_capacity, compare_policies, run

def test_capacity_is_respected():
    df=generate_cases(seed=2,n=3000);selected,_,_=select_with_capacity(df,"hybrid",capacity_hours=20,seed=2);assert selected.review_minutes.sum() <= 20*60 + 1e-9

def test_policy_comparison_has_all_policies():
    df=generate_cases(seed=3,n=2500);comp=compare_policies(df,capacity_hours=30,seed=3);assert len(comp)==5;assert {"risk","hybrid","random"}.issubset(set(comp.policy))

def test_run_metrics():
    *_,metrics=run(seed=4,n=3000,capacity_hours=35,policy="hybrid");assert metrics["Selected cases"]>0;assert metrics["Queue remaining"]>0;assert metrics["Synthetic queue"]=="Yes"
