from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
from engine import run, POLICIES

st.set_page_config(page_title="ReviewerIQ", page_icon="◎", layout="wide")
CSS="""<style>html,body,[class*="css"],.stApp{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif;color:#1d1d1f}.stApp{background:#fff}.block-container{max-width:1440px;padding-top:2.2rem;padding-bottom:4rem}#MainMenu,footer,header{visibility:hidden}.hero{background:radial-gradient(circle at 13% 9%,rgba(0,113,227,.12),transparent 31%),linear-gradient(180deg,#fff,#f5f5f7);border:1px solid #e8e8ed;border-radius:32px;padding:44px 48px 40px;margin-bottom:22px;box-shadow:0 12px 34px rgba(0,0,0,.035)}.eyebrow{color:#0071e3;font-weight:700;font-size:.78rem;letter-spacing:.11em;text-transform:uppercase}.hero h1{font-size:3.15rem;letter-spacing:-.055em;line-height:1.02;margin:.45rem 0 .7rem;font-weight:700}.hero p{color:#6e6e73;max-width:930px;font-size:1.06rem;line-height:1.55;margin:0}.pills{margin-top:18px;display:flex;gap:8px;flex-wrap:wrap}.pill{background:#fff;color:#515154;border:1px solid #e8e8ed;padding:7px 11px;border-radius:999px;font-size:.79rem}.kpi{background:#f5f5f7;border:1px solid #ececf0;border-radius:24px;padding:18px;min-height:116px;box-shadow:0 8px 22px rgba(0,0,0,.025)}.kpi-label{color:#6e6e73;text-transform:uppercase;letter-spacing:.075em;font-size:.68rem;font-weight:700}.kpi-value{font-size:1.45rem;font-weight:700;letter-spacing:-.035em;margin-top:9px}.section-title{font-size:1.5rem;letter-spacing:-.03em;margin:26px 0 12px;font-weight:700}.note{color:#6e6e73;font-size:.85rem}</style>"""
st.markdown(CSS,unsafe_allow_html=True)

def fmt(v):
    if isinstance(v,int):return f"{v:,}"
    if isinstance(v,float):
        if -1<=v<=1:return f"{v:.3f}"
        return f"{v:,.1f}"
    return str(v).replace("_"," ")

def cards(items,cols=5):
    for s in range(0,len(items),cols):
        cs=st.columns(cols)
        for i,(k,v) in enumerate(items[s:s+cols]):cs[i].markdown(f'<div class="kpi"><div class="kpi-label">{k}</div><div class="kpi-value">{fmt(v)}</div></div>',unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load(seed,n,capacity,policy): return run(seed,n,capacity,policy)

with st.sidebar:
    st.markdown("### ReviewerIQ");seed=st.number_input("Synthetic seed",1,9999,42);n=st.slider("Queue size",2500,15000,6000,500);capacity=st.slider("Analyst capacity (hours)",20,240,80,10);policy=st.selectbox("Review policy",POLICIES,index=POLICIES.index("hybrid"));st.caption("The optimizer allocates a fixed review-time budget; it does not autonomously enforce outcomes.")

df,selected,remaining,ranked,comparison,metrics=load(seed,n,capacity,policy)
st.markdown("""<div class="hero"><div class="eyebrow">Human-in-the-loop · Review economics</div><h1>Spend scarce human attention where it changes the outcome.</h1><p>ReviewerIQ prioritizes a constrained security/fraud review queue using risk, uncertainty, expected loss, novelty, queue age, information gain, and review effort—then measures risk caught per analyst hour.</p><div class="pills"><span class="pill">Capacity constraint</span><span class="pill">Active-learning signals</span><span class="pill">Expected loss</span><span class="pill">Novelty</span><span class="pill">Policy comparison</span><span class="pill">Human review</span></div></div>""",unsafe_allow_html=True)
st.markdown('<div class="section-title">Review efficiency</div>',unsafe_allow_html=True);cards(list(metrics.items()),5)
tabs=st.tabs(["Policy comparison","Selected queue","Efficiency frontier","Information value","Queue"])
with tabs[0]:
    show=comparison.copy();st.dataframe(show,hide_index=True,use_container_width=True);fig=px.bar(show.sort_values("risk_per_hour"),x="risk_per_hour",y="policy",orientation="h",title="Risk caught per analyst hour");fig.update_layout(template="plotly_white",height=390);st.plotly_chart(fig,use_container_width=True)
with tabs[1]:
    c1,c2=st.columns([1.25,.75])
    with c1:
        fig=px.scatter(selected,x="risk",y="expected_loss",size="review_minutes",color="novelty",hover_data=["case_id","uncertainty","severe"],title="Selected review portfolio");fig.update_layout(template="plotly_white",height=440);st.plotly_chart(fig,use_container_width=True)
    with c2:
        st.markdown("#### Highest priority");st.dataframe(selected.nlargest(20,"priority_score")[["case_id","priority_score","risk","uncertainty","expected_loss","novelty","review_minutes","severe"]],hide_index=True,use_container_width=True,height=440)
with tabs[2]:
    frontier=comparison[["policy","risk_per_hour","severe_recall","information_gain","capacity_used_hours"]];fig=px.scatter(frontier,x="risk_per_hour",y="severe_recall",size="information_gain",text="policy",title="Review policy efficiency frontier");fig.update_traces(textposition="top center");fig.update_layout(template="plotly_white",height=440);st.plotly_chart(fig,use_container_width=True);st.caption("Policies are compared under the same analyst-hour budget.")
with tabs[3]:
    fig=px.scatter(df.sample(min(2500,len(df)),random_state=7),x="uncertainty",y="novelty",color="information_gain",size="expected_loss",title="Information-gain landscape");fig.update_layout(template="plotly_white",height=440);st.plotly_chart(fig,use_container_width=True);st.info("High risk is not the only useful review target: uncertain, novel cases can improve future learning even when immediate risk is lower.")
with tabs[4]:
    st.dataframe(ranked.head(1000),hide_index=True,use_container_width=True);st.download_button("Export selected reviews",selected.to_csv(index=False),"revieweriq_selected.csv","text/csv")
st.markdown('<p class="note">Synthetic queue and outcomes. “Risk caught” is a simulation metric, not a claim about real fraud loss or incident prevention.</p>',unsafe_allow_html=True)
