from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

POLICIES=["random","risk","uncertainty","expected_value","hybrid"]

def generate_cases(seed=42,n=6000):
    rng=np.random.default_rng(seed)
    risk=np.clip(rng.beta(2.1,5.2,n)+rng.normal(0,.025,n),0,1)
    uncertainty=np.clip(4*risk*(1-risk)+rng.normal(0,.08,n),0,1)
    expected_loss=np.exp(rng.normal(5.0,1.0,n))
    novelty=np.clip(rng.beta(2.0,4.0,n)+.18*(uncertainty>.72),0,1)
    review_minutes=np.clip(rng.gamma(2.2,4.0,n)+2,2,45)
    age_hours=np.clip(rng.exponential(14,n),0,96)
    severity_score=.42*risk+.27*np.tanh(expected_loss/700)+.18*novelty+.13*uncertainty
    severe=(severity_score+rng.normal(0,.08,n)>.62).astype(int)
    true_loss=expected_loss*(.35+.65*severe)
    information_gain=np.clip(.58*uncertainty+.42*novelty,0,1)
    return pd.DataFrame({
        "case_id":[f"case_{i:06d}" for i in range(n)],"risk":risk,"uncertainty":uncertainty,
        "expected_loss":expected_loss,"novelty":novelty,"review_minutes":review_minutes,
        "age_hours":age_hours,"severe":severe,"true_loss":true_loss,"information_gain":information_gain
    })

def score_cases(df,policy,seed=42):
    rng=np.random.default_rng(seed);d=df.copy()
    if policy=="random":score=rng.random(len(d))
    elif policy=="risk":score=d.risk
    elif policy=="uncertainty":score=d.uncertainty
    elif policy=="expected_value":score=d.risk*np.log1p(d.expected_loss)
    elif policy=="hybrid":
        loss_norm=np.log1p(d.expected_loss)/np.log1p(d.expected_loss).max();age=np.clip(d.age_hours/48,0,1)
        score=.34*d.risk+.24*loss_norm+.18*d.uncertainty+.16*d.novelty+.08*age
    else:raise ValueError(f"unknown policy: {policy}")
    d["priority_score"]=score;d["utility_per_minute"]=(score*(.55+.45*d.information_gain))/d.review_minutes
    return d

def select_with_capacity(df,policy,capacity_hours=80,seed=42):
    d=score_cases(df,policy,seed);ranked=d.sort_values(["utility_per_minute","priority_score"],ascending=False).copy();budget=capacity_hours*60
    ranked["cum_minutes"]=ranked.review_minutes.cumsum();selected=ranked[ranked.cum_minutes<=budget].copy();remaining=ranked[ranked.cum_minutes>budget].copy()
    return selected,remaining,ranked

def evaluate_policy(df,policy,capacity_hours=80,seed=42):
    selected,remaining,ranked=select_with_capacity(df,policy,capacity_hours,seed);all_severe=max(int(df.severe.sum()),1);caught_loss=float(selected.loc[selected.severe.eq(1),"true_loss"].sum());hours=float(selected.review_minutes.sum()/60)
    return {"policy":policy,"cases_reviewed":int(len(selected)),"capacity_used_hours":hours,"severe_cases_caught":int(selected.severe.sum()),"severe_recall":float(selected.severe.sum()/all_severe),"review_precision":float(selected.severe.mean()) if len(selected) else 0,"risk_caught":float(selected.loc[selected.severe.eq(1),"true_loss"].sum()),"risk_per_hour":float(caught_loss/max(hours,1e-9)),"information_gain":float(selected.information_gain.mean()) if len(selected) else 0,"novelty_coverage":float(selected.novelty.mean()) if len(selected) else 0,"avg_review_minutes":float(selected.review_minutes.mean()) if len(selected) else 0,"p95_queue_age_hours":float(selected.age_hours.quantile(.95)) if len(selected) else 0,"missed_severe_cases":int(remaining.severe.sum()),"queue_remaining":int(len(remaining))}

def compare_policies(df,capacity_hours=80,seed=42):
    return pd.DataFrame([evaluate_policy(df,p,capacity_hours,seed) for p in POLICIES]).sort_values("risk_per_hour",ascending=False)

def run(seed=42,n=6000,capacity_hours=80,policy="hybrid"):
    df=generate_cases(seed,n);selected,remaining,ranked=select_with_capacity(df,policy,capacity_hours,seed);comparison=compare_policies(df,capacity_hours,seed);current=evaluate_policy(df,policy,capacity_hours,seed);baseline=comparison[comparison.policy=="risk"].iloc[0]
    metrics={"Cases in queue":int(len(df)),"Review capacity h":float(capacity_hours),"Selected cases":int(len(selected)),"Capacity utilization":float(selected.review_minutes.sum()/(capacity_hours*60)),"Severe prevalence":float(df.severe.mean()),"Selected severe rate":float(selected.severe.mean()) if len(selected) else 0,"Severe recall":current["severe_recall"],"Risk caught":current["risk_caught"],"Risk / analyst hour":current["risk_per_hour"],"Risk-policy baseline / h":float(baseline.risk_per_hour),"Lift vs risk-only":float(current["risk_per_hour"]/max(float(baseline.risk_per_hour),1e-9)-1),"Information gain":current["information_gain"],"Novelty coverage":current["novelty_coverage"],"Avg review minutes":current["avg_review_minutes"],"P95 selected age h":current["p95_queue_age_hours"],"Missed severe cases":current["missed_severe_cases"],"Queue remaining":current["queue_remaining"],"Policies compared":len(POLICIES),"Optimization policy":policy,"Synthetic queue":"Yes"}
    return df,selected,remaining,ranked,comparison,metrics

def main():
    p=argparse.ArgumentParser(description="ReviewerIQ capacity-constrained review optimizer");p.add_argument("--out",default="artifacts");p.add_argument("--rows",type=int,default=6000);p.add_argument("--capacity-hours",type=float,default=80);p.add_argument("--policy",choices=POLICIES,default="hybrid");p.add_argument("--seed",type=int,default=42)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);df,selected,remaining,ranked,comparison,metrics=run(a.seed,a.rows,a.capacity_hours,a.policy);selected.to_csv(out/"selected_reviews.csv",index=False);comparison.to_csv(out/"policy_comparison.csv",index=False);pd.Series(metrics).to_json(out/"metrics.json",indent=2);print(pd.Series(metrics).to_string())

if __name__=="__main__":main()
