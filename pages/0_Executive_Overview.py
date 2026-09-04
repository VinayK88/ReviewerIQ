from __future__ import annotations
import numbers
import streamlit as st
import pandas as pd
import plotly.express as px
from engine import run, POLICIES

st.set_page_config(page_title="ReviewerIQ · Executive Overview", page_icon="◎", layout="wide")
CSS="""
<style>
:root{--ink:#1d1d1f;--muted:#6e6e73;--soft:#f5f5f7;--line:#e8e8ed;--blue:#0071e3}
html,body,[class*="css"],.stApp,p,li,div,span,button,input,label{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif!important;-webkit-font-smoothing:antialiased;color:var(--ink);font-size:16px}.stApp{background:linear-gradient(180deg,#fff,#fbfbfd)}.block-container{max-width:1500px;padding:2.3rem 2.2rem 5rem}#MainMenu,footer,header{visibility:hidden}[data-testid="stSidebar"]{background:#f5f5f7;border-right:1px solid var(--line)}[data-testid="stSidebar"] *{font-size:15px!important}.hero{background:radial-gradient(circle at 8% 0%,rgba(0,113,227,.16),transparent 32%),linear-gradient(155deg,#fff,#f5f5f7);border:1px solid var(--line);border-radius:36px;padding:54px 56px 48px;box-shadow:0 18px 48px rgba(0,0,0,.045)}.hero h1{font-size:3.65rem;line-height:.98;letter-spacing:-.062em;margin:.55rem 0 .9rem;font-weight:720;max-width:1020px}.hero p{color:var(--muted);font-size:1.12rem;line-height:1.6;max-width:960px;margin:0}.eyebrow{color:var(--blue);font-weight:760;font-size:.78rem;letter-spacing:.13em;text-transform:uppercase}.pills{margin-top:22px;display:flex;flex-wrap:wrap;gap:9px}.pill{background:#fff;border:1px solid var(--line);border-radius:999px;padding:8px 13px;color:#515154;font-size:.8rem}.section{font-size:1.72rem;letter-spacing:-.04em;font-weight:720;margin:32px 0 6px}.sub{color:var(--muted);font-size:.96rem;margin-bottom:16px}.kpi{background:#fff;border:1px solid var(--line);border-radius:26px;padding:20px;min-height:122px;box-shadow:0 8px 24px rgba(0,0,0,.028)}.kpi-label{color:var(--muted);font-size:.70rem;font-weight:760;letter-spacing:.08em;text-transform:uppercase}.kpi-value{font-size:1.62rem;line-height:1.03;font-weight:720;letter-spacing:-.045em;margin-top:12px}.callout{background:#fff;border:1px solid var(--line);border-radius:28px;padding:24px;min-height:162px;box-shadow:0 8px 24px rgba(0,0,0,.025)}.callout .cap{color:var(--blue);font-size:.70rem;font-weight:760;letter-spacing:.1em;text-transform:uppercase}.callout h3{font-size:1.25rem;letter-spacing:-.03em;margin:.55rem 0 .45rem}.callout p{color:var(--muted);font-size:.92rem;line-height:1.55;margin:0}</style>
"""
st.markdown(CSS,unsafe_allow_html=True)

def fmt(v):
    if isinstance(v,bool): return "Yes" if v else "No"
    if isinstance(v,numbers.Integral): return f"{int(v):,}"
    if isinstance(v,numbers.Real):
        v=float(v)
        if -1<=v<=1:return f"{v:.3f}"
        if abs(v)>=1000:return f"{v:,.0f}"
        return f"{v:,.2f}"
    return str(v).replace("_"," ")

def cards(items,cols=5):
    for s in range(0,len(items),cols):
        row=st.columns(cols)
        for i,(k,v) in enumerate(items[s:s+cols]):row[i].markdown(f'<div class="kpi"><div class="kpi-label">{k}</div><div class="kpi-value">{fmt(v)}</div></div>',unsafe_allow_html=True)

def style(fig,h=420):
    fig.update_layout(template="plotly_white",height=h,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family='-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial',size=14,color="#1d1d1f"),title_font=dict(size=20),margin=dict(l=12,r=12,t=60,b=12),legend_title_text="")
    fig.update_xaxes(gridcolor="#ececf0");fig.update_yaxes(gridcolor="#ececf0");return fig

with st.sidebar:
    st.markdown("### ReviewerIQ")
    seed=st.number_input("Synthetic seed",1,9999,42)
    n=st.slider("Queue size",2500,15000,6000,500)
    capacity=st.slider("Analyst capacity (hours)",20,240,80,10)
    policy=st.selectbox("Policy",POLICIES,index=POLICIES.index("hybrid"))
    st.caption("Executive view compares queue economics under the same analyst-hour constraint.")

df,selected,remaining,ranked,comparison,base=run(seed,n,capacity,policy)
selected_hours=float(selected.review_minutes.sum()/60)
all_risk=float(df.loc[df.severe.eq(1),"true_loss"].sum())
selected_risk=float(selected.loc[selected.severe.eq(1),"true_loss"].sum())
risk_base=float(comparison.loc[comparison.policy=="risk","risk_per_hour"].iloc[0])
random_base=float(comparison.loc[comparison.policy=="random","risk_per_hour"].iloc[0])
best_row=comparison.sort_values("risk_per_hour",ascending=False).iloc[0]

kpis=dict(base)
kpis.update({
    "Total severe cases":int(df.severe.sum()),"Selected severe cases":int(selected.severe.sum()),"Remaining severe cases":int(remaining.severe.sum()),"Queue compression":float(len(selected)/len(df)),
    "Review hours consumed":selected_hours,"Capacity remaining h":float(capacity-selected_hours),"Cases / analyst hour":float(len(selected)/max(selected_hours,1e-9)),"Severe cases / hour":float(selected.severe.sum()/max(selected_hours,1e-9)),
    "Total severe risk":all_risk,"Risk capture rate":float(selected_risk/max(all_risk,1e-9)),"Risk / selected case":float(selected_risk/max(len(selected),1)),"Risk / severe selected":float(selected_risk/max(selected.severe.sum(),1)),
    "Random baseline / h":random_base,"Lift vs random":float(base["Risk / analyst hour"]/max(random_base,1e-9)-1),"Lift vs risk-only":float(base["Risk / analyst hour"]/max(risk_base,1e-9)-1),"Best policy":best_row.policy,
    "Best policy risk / h":float(best_row.risk_per_hour),"Mean queue risk":float(df.risk.mean()),"Mean selected risk":float(selected.risk.mean()),"Risk uplift selected":float(selected.risk.mean()-df.risk.mean()),
    "Mean queue uncertainty":float(df.uncertainty.mean()),"Mean selected uncertainty":float(selected.uncertainty.mean()),"Uncertainty uplift":float(selected.uncertainty.mean()-df.uncertainty.mean()),
    "Mean queue novelty":float(df.novelty.mean()),"Mean selected novelty":float(selected.novelty.mean()),"Novelty uplift":float(selected.novelty.mean()-df.novelty.mean()),
    "High-novelty selected":int((selected.novelty>.75).sum()),"High-uncertainty selected":int((selected.uncertainty>.75).sum()),"Total information value":float(selected.information_gain.sum()),
    "Mean priority score":float(selected.priority_score.mean()),"P95 priority score":float(selected.priority_score.quantile(.95)),"Mean utility / minute":float(selected.utility_per_minute.mean()),"P95 utility / minute":float(selected.utility_per_minute.quantile(.95)),
    "Mean selected age h":float(selected.age_hours.mean()),"Max selected age h":float(selected.age_hours.max()),"Mean review minutes":float(selected.review_minutes.mean()),"P95 review minutes":float(selected.review_minutes.quantile(.95)),
    "Policies compared":int(len(comparison)),"Synthetic queue":"Yes"
})

st.markdown('''<div class="hero"><div class="eyebrow">ReviewerIQ · Executive review intelligence</div><h1>Measure what every analyst hour buys.</h1><p>A product-level view of capacity, severe-risk capture, information gain, novelty, uncertainty, queue health, and policy efficiency.</p><div class="pills"><span class="pill">45+ KPIs</span><span class="pill">Analyst capacity</span><span class="pill">Risk / hour</span><span class="pill">Information gain</span><span class="pill">Policy frontier</span></div></div>''',unsafe_allow_html=True)
st.markdown('<div class="section">Executive scorecard</div><div class="sub">Expanded capacity, risk, learning-value, and policy-efficiency metrics with a more readable type system.</div>',unsafe_allow_html=True)
cards(list(kpis.items()),5)

st.markdown('<div class="section">Three things to notice</div>',unsafe_allow_html=True)
c=st.columns(3)
c[0].markdown(f'<div class="callout"><div class="cap">Capacity</div><h3>{selected_hours:.1f} / {capacity} h used</h3><p>The policy is evaluated under an explicit human-review budget rather than an unlimited queue assumption.</p></div>',unsafe_allow_html=True)
c[1].markdown(f'<div class="callout"><div class="cap">Risk efficiency</div><h3>{base["Risk / analyst hour"]:,.1f} / h</h3><p>This is the core operational metric: how much synthetic severe risk each analyst hour captures.</p></div>',unsafe_allow_html=True)
c[2].markdown(f'<div class="callout"><div class="cap">Learning value</div><h3>{selected.information_gain.mean():.3f}</h3><p>Selected cases retain uncertainty and novelty so review produces future learning, not only immediate triage.</p></div>',unsafe_allow_html=True)

c1,c2=st.columns(2)
with c1:
    fig=px.bar(comparison.sort_values("risk_per_hour"),x="risk_per_hour",y="policy",orientation="h",title="Risk caught per analyst hour");st.plotly_chart(style(fig,430),use_container_width=True)
with c2:
    fig=px.scatter(comparison,x="risk_per_hour",y="severe_recall",size="information_gain",text="policy",title="Policy efficiency frontier");fig.update_traces(textposition="top center");st.plotly_chart(style(fig,430),use_container_width=True)

st.caption("All cases, losses, and outcomes are synthetic. ReviewerIQ prioritizes human review; it does not autonomously enforce an outcome.")
