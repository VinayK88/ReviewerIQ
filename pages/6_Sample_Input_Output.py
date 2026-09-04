from __future__ import annotations
import streamlit as st
import pandas as pd
from engine import run, POLICIES

st.set_page_config(page_title="ReviewerIQ · Sample I/O", page_icon="↔", layout="wide")

st.markdown("""
<style>
html,body,[class*="css"],.stApp{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif;color:#1d1d1f}.stApp{background:linear-gradient(180deg,#fff 0%,#fbfbfd 100%)}.block-container{max-width:1380px;padding-top:2.2rem;padding-bottom:5rem}#MainMenu,footer,header{visibility:hidden}.hero{background:radial-gradient(circle at 8% 0%,rgba(0,113,227,.14),transparent 32%),linear-gradient(155deg,#fff,#f5f5f7);border:1px solid #e8e8ed;border-radius:34px;padding:44px 48px;margin-bottom:22px;box-shadow:0 18px 48px rgba(0,0,0,.04)}.eyebrow{color:#0071e3;font-size:.75rem;font-weight:750;letter-spacing:.12em;text-transform:uppercase}.hero h1{font-size:3rem;letter-spacing:-.055em;line-height:1;margin:.55rem 0 .7rem}.hero p{color:#6e6e73;max-width:920px;font-size:1.04rem;line-height:1.55}.card{background:#fff;border:1px solid #e8e8ed;border-radius:26px;padding:22px;box-shadow:0 8px 24px rgba(0,0,0,.025)}.step{color:#0071e3;font-size:.69rem;font-weight:760;letter-spacing:.1em;text-transform:uppercase}.big{font-size:1.35rem;font-weight:720;letter-spacing:-.03em;margin:.35rem 0}.muted{color:#6e6e73;font-size:.9rem;line-height:1.5}.arrow{text-align:center;font-size:2rem;color:#0071e3;padding-top:40px}.badge{display:inline-block;background:#f5f5f7;border:1px solid #e8e8ed;border-radius:999px;padding:7px 10px;margin:0 6px 6px 0;color:#515154;font-size:.78rem}</style>
<div class="hero"><div class="eyebrow">ReviewerIQ · Sample Input → Output</div><h1>See why one case enters the review queue.</h1><p>This page takes an actual synthetic case from the optimizer and shows the operational fields used for prioritization, followed by its priority score, utility per minute, and whether it fits inside the chosen analyst-hour budget.</p></div>
""",unsafe_allow_html=True)

policy=st.selectbox("Policy",POLICIES,index=POLICIES.index("hybrid"))
capacity=st.slider("Analyst capacity (hours)",20,160,80,10)

@st.cache_data(show_spinner=False)
def load(policy,capacity): return run(seed=42,n=6000,capacity_hours=capacity,policy=policy)

df,selected,remaining,ranked,comparison,metrics=load(policy,capacity)
idx=st.slider("Ranked case example",0,min(50,len(ranked)-1),0)
row=ranked.iloc[idx]
selected_ids=set(selected.case_id)

input_cols=["case_id","risk","uncertainty","expected_loss","novelty","information_gain","review_minutes","age_hours"]
output_df=pd.DataFrame([{"priority_score":row.priority_score,"utility_per_minute":row.utility_per_minute,"selected_for_review":row.case_id in selected_ids,"policy":policy,"severe_outcome":row.severe,"true_loss":row.true_loss}])

st.markdown("### Example flow")
c1,c2,c3=st.columns([1,0.12,1])
with c1:
    st.markdown('<div class="card"><div class="step">1 · Sample input</div><div class="big">Scored review candidate</div><div class="muted">A production adapter could source these fields from a SOC, fraud, IAM, Trust & Safety, or vulnerability-review queue.</div></div>',unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{k:row[k] for k in input_cols}]),hide_index=True,use_container_width=True)
with c2: st.markdown('<div class="arrow">→</div>',unsafe_allow_html=True)
with c3:
    st.markdown('<div class="card"><div class="step">2 · Queue output</div><div class="big">Priority + capacity decision</div><div class="muted">ReviewerIQ prioritizes human attention. It does not make the underlying enforcement decision.</div></div>',unsafe_allow_html=True)
    st.dataframe(output_df,hide_index=True,use_container_width=True)

st.markdown("### What the optimizer considered")
st.markdown('<span class="badge">risk</span><span class="badge">expected loss</span><span class="badge">uncertainty</span><span class="badge">novelty</span><span class="badge">information gain</span><span class="badge">queue age</span><span class="badge">review effort</span>',unsafe_allow_html=True)

st.markdown("### Example interpretation")
if row.case_id in selected_ids:
    st.success(f"**{row.case_id} is selected for review.** Its utility per review minute is {row.utility_per_minute:.4f}; under the current {capacity}-hour budget, it ranks high enough to consume scarce analyst capacity.")
else:
    st.info(f"**{row.case_id} remains in the backlog.** The case may still be risky, but its current utility per minute is not high enough to fit inside the {capacity}-hour budget under the **{policy}** policy.")

st.caption("All cases, expected losses, outcomes, and review times are synthetic. This page demonstrates the review-allocation input/output contract.")
