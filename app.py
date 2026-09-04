from __future__ import annotations
import numbers
import streamlit as st
import pandas as pd
import plotly.express as px
from engine import run, POLICIES

st.set_page_config(page_title="ReviewerIQ", page_icon="◎", layout="wide")

CSS="""
<style>
html,body,[class*="css"],.stApp{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif;color:#1d1d1f}
.stApp{background:linear-gradient(180deg,#ffffff 0%,#fbfbfd 100%)}
.block-container{max-width:1480px;padding-top:2rem;padding-bottom:5rem}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background:#f5f5f7;border-right:1px solid #e8e8ed}
.hero{position:relative;overflow:hidden;background:radial-gradient(circle at 9% 0%,rgba(0,113,227,.15),transparent 31%),linear-gradient(155deg,#fff,#f5f5f7);border:1px solid #e8e8ed;border-radius:34px;padding:50px 52px 44px;margin-bottom:18px;box-shadow:0 18px 48px rgba(0,0,0,.045)}
.hero:after{content:"";position:absolute;width:290px;height:290px;right:-90px;top:-105px;border-radius:50%;background:rgba(0,113,227,.05)}
.eyebrow{color:#0071e3;font-weight:750;font-size:.76rem;letter-spacing:.12em;text-transform:uppercase}.hero h1{font-size:3.45rem;letter-spacing:-.06em;line-height:.98;margin:.55rem 0 .8rem;font-weight:730;max-width:1000px}.hero p{color:#6e6e73;max-width:970px;font-size:1.08rem;line-height:1.58;margin:0}.pills{margin-top:20px;display:flex;gap:8px;flex-wrap:wrap}.pill{background:rgba(255,255,255,.9);color:#515154;border:1px solid #e8e8ed;padding:7px 12px;border-radius:999px;font-size:.79rem}
.status-row{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 24px}.status{display:inline-flex;align-items:center;gap:8px;padding:9px 13px;background:#fff;border:1px solid #e8e8ed;border-radius:999px;font-size:.79rem;color:#515154;box-shadow:0 6px 18px rgba(0,0,0,.025)}.dot{width:8px;height:8px;border-radius:50%;background:#34c759;display:inline-block}
.section-title{font-size:1.55rem;letter-spacing:-.035em;margin:30px 0 13px;font-weight:720}.section-sub{color:#6e6e73;font-size:.91rem;margin-top:-6px;margin-bottom:15px}
.kpi{background:rgba(255,255,255,.97);border:1px solid #e8e8ed;border-radius:25px;padding:18px;min-height:116px;box-shadow:0 8px 24px rgba(0,0,0,.028)}.kpi:hover{box-shadow:0 12px 30px rgba(0,0,0,.045);transform:translateY(-1px);transition:.16s ease}.kpi-label{color:#6e6e73;text-transform:uppercase;letter-spacing:.075em;font-size:.67rem;font-weight:760}.kpi-value{font-size:1.46rem;font-weight:730;letter-spacing:-.04em;margin-top:10px;line-height:1.05}
.insight{background:#fff;border:1px solid #e8e8ed;border-radius:26px;padding:22px 23px;min-height:148px;box-shadow:0 8px 24px rgba(0,0,0,.025)}.insight .cap{color:#0071e3;text-transform:uppercase;letter-spacing:.09em;font-size:.68rem;font-weight:760}.insight h3{font-size:1.15rem;letter-spacing:-.025em;margin:.55rem 0 .45rem}.insight p{color:#6e6e73;font-size:.88rem;line-height:1.48;margin:0}.note{color:#6e6e73;font-size:.84rem}
div[data-baseweb="tab-list"]{gap:8px}button[data-baseweb="tab"]{border-radius:999px;padding-left:14px;padding-right:14px}
</style>
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
        cs=st.columns(cols)
        for i,(k,v) in enumerate(items[s:s+cols]):
            cs[i].markdown(f'<div class="kpi"><div class="kpi-label">{k}</div><div class="kpi-value">{fmt(v)}</div></div>',unsafe_allow_html=True)


def style_fig(fig,height=430):
    fig.update_layout(template="plotly_white",height=height,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family='-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial',color="#1d1d1f"),title_font=dict(size=18),margin=dict(l=12,r=12,t=58,b=12),legend_title_text="")
    fig.update_xaxes(gridcolor="#eeeeF2",zerolinecolor="#eeeeF2")
    fig.update_yaxes(gridcolor="#eeeeF2",zerolinecolor="#eeeeF2")
    return fig


@st.cache_data(show_spinner=False)
def load(seed,n,capacity,policy): return run(seed,n,capacity,policy)


with st.sidebar:
    st.markdown("### ReviewerIQ")
    st.caption("Human-review optimization")
    seed=st.number_input("Synthetic seed",1,9999,42)
    n=st.slider("Queue size",2500,15000,6000,500)
    capacity=st.slider("Analyst capacity (hours)",20,240,80,10)
    policy=st.selectbox("Review policy",POLICIES,index=POLICIES.index("hybrid"))
    st.divider()
    st.caption("The optimizer allocates a fixed review-time budget. It prioritizes cases for humans; it does not autonomously enforce outcomes.")


df,selected,remaining,ranked,comparison,metrics=load(seed,n,capacity,policy)

all_severe=int(df.severe.sum())
selected_severe=int(selected.severe.sum())
missed_severe=int(remaining.severe.sum())
all_severe_loss=float(df.loc[df.severe.eq(1),"true_loss"].sum())
selected_severe_loss=float(selected.loc[selected.severe.eq(1),"true_loss"].sum())
risk_capture_rate=float(selected_severe_loss/max(all_severe_loss,1e-9))
queue_compression=float(len(selected)/max(len(df),1))
review_hours=float(selected.review_minutes.sum()/60)
capacity_remaining=float(max(capacity-review_hours,0))
cases_per_hour=float(len(selected)/max(review_hours,1e-9))
severe_per_hour=float(selected_severe/max(review_hours,1e-9))
selected_avg_risk=float(selected.risk.mean()) if len(selected) else 0.0
queue_avg_risk=float(df.risk.mean())
selected_avg_unc=float(selected.uncertainty.mean()) if len(selected) else 0.0
queue_avg_unc=float(df.uncertainty.mean())
selected_avg_novelty=float(selected.novelty.mean()) if len(selected) else 0.0
queue_avg_novelty=float(df.novelty.mean())
median_review=float(selected.review_minutes.median()) if len(selected) else 0.0
p95_review=float(selected.review_minutes.quantile(.95)) if len(selected) else 0.0
p95_queue_age=float(df.age_hours.quantile(.95))
high_novelty=int((selected.novelty>=.75).sum())
high_uncertainty=int((selected.uncertainty>=.75).sum())
high_loss=int((selected.expected_loss>=df.expected_loss.quantile(.90)).sum())
info_total=float(selected.information_gain.sum())
random_row=comparison[comparison.policy=="random"].iloc[0]
risk_row=comparison[comparison.policy=="risk"].iloc[0]
current_row=comparison[comparison.policy==policy].iloc[0]
lift_vs_random=float(current_row.risk_per_hour/max(random_row.risk_per_hour,1e-9)-1)
lift_vs_risk=float(current_row.risk_per_hour/max(risk_row.risk_per_hour,1e-9)-1)
best_policy=str(comparison.sort_values("risk_per_hour",ascending=False).iloc[0].policy)

extended=dict(metrics)
extended.update({
    "Queue compression ratio":queue_compression,
    "Total severe cases":all_severe,
    "Severe caught":selected_severe,
    "Severe missed":missed_severe,
    "Risk capture rate":risk_capture_rate,
    "Review hours used":review_hours,
    "Capacity remaining h":capacity_remaining,
    "Cases / analyst hour":cases_per_hour,
    "Severe / analyst hour":severe_per_hour,
    "Selected avg risk":selected_avg_risk,
    "Queue avg risk":queue_avg_risk,
    "Selected avg uncertainty":selected_avg_unc,
    "Queue avg uncertainty":queue_avg_unc,
    "Selected avg novelty":selected_avg_novelty,
    "Queue avg novelty":queue_avg_novelty,
    "Median review min":median_review,
    "P95 review min":p95_review,
    "P95 queue age h":p95_queue_age,
    "High-novelty reviews":high_novelty,
    "High-uncertainty reviews":high_uncertainty,
    "Top-decile loss reviews":high_loss,
    "Total information value":info_total,
    "Lift vs random":lift_vs_random,
    "Lift vs risk-only":lift_vs_risk,
    "Best policy / risk-hour":best_policy,
})

st.markdown("""<div class="hero"><div class="eyebrow">Human-in-the-loop · Review economics</div><h1>Put human attention where it changes the outcome.</h1><p>ReviewerIQ prioritizes a capacity-constrained security or fraud queue using risk, uncertainty, expected loss, novelty, queue age, information gain, and review effort—then compares multiple policies under the exact same analyst-hour budget.</p><div class="pills"><span class="pill">Capacity constraint</span><span class="pill">Expected loss</span><span class="pill">Uncertainty</span><span class="pill">Novelty</span><span class="pill">Information gain</span><span class="pill">Policy frontier</span><span class="pill">Human review</span></div></div><div class="status-row"><div class="status"><span class="dot"></span>Synthetic queue healthy</div><div class="status">Fixed analyst-hour budget</div><div class="status">No autonomous enforcement</div></div>""",unsafe_allow_html=True)

st.markdown('<div class="section-title">Review efficiency</div>',unsafe_allow_html=True)
st.markdown('<div class="section-sub">30+ capacity, risk, queue, learning-value, and policy metrics around the same review budget.</div>',unsafe_allow_html=True)
cards(list(extended.items()),5)

st.markdown('<div class="section-title">Executive readout</div>',unsafe_allow_html=True)
ins=st.columns(3)
ins[0].markdown(f'<div class="insight"><div class="cap">Risk efficiency</div><h3>{metrics["Risk / analyst hour"]:,.0f} / hour</h3><p>Synthetic severe-loss value captured per analyst hour. This is the central operational efficiency metric.</p></div>',unsafe_allow_html=True)
ins[1].markdown(f'<div class="insight"><div class="cap">Coverage</div><h3>{metrics["Severe recall"]:.1%} severe recall</h3><p>{selected_severe:,} severe cases are selected while {missed_severe:,} remain outside the current review budget.</p></div>',unsafe_allow_html=True)
ins[2].markdown(f'<div class="insight"><div class="cap">Learning value</div><h3>{metrics["Information gain"]:.3f}</h3><p>Mean information gain keeps novelty and uncertainty visible so review is not reduced to a pure risk ranking.</p></div>',unsafe_allow_html=True)


tabs=st.tabs(["Policy comparison","Selected queue","Efficiency frontier","Information value","Queue"])

with tabs[0]:
    show=comparison.copy()
    st.dataframe(show,hide_index=True,use_container_width=True)
    c1,c2=st.columns(2)
    with c1:
        fig=px.bar(show.sort_values("risk_per_hour"),x="risk_per_hour",y="policy",orientation="h",title="Risk caught per analyst hour")
        st.plotly_chart(style_fig(fig,400),use_container_width=True)
    with c2:
        fig=px.bar(show.sort_values("severe_recall"),x="severe_recall",y="policy",orientation="h",title="Severe-case recall under the same budget")
        st.plotly_chart(style_fig(fig,400),use_container_width=True)

with tabs[1]:
    c1,c2=st.columns([1.25,.75])
    with c1:
        fig=px.scatter(selected,x="risk",y="expected_loss",size="review_minutes",color="novelty",hover_data=["case_id","uncertainty","information_gain","severe"],title="Selected review portfolio")
        st.plotly_chart(style_fig(fig,455),use_container_width=True)
    with c2:
        st.markdown("#### Highest priority")
        st.dataframe(selected.nlargest(25,"priority_score")[["case_id","priority_score","risk","uncertainty","expected_loss","novelty","review_minutes","severe"]],hide_index=True,use_container_width=True,height=455)

with tabs[2]:
    frontier=comparison[["policy","risk_per_hour","severe_recall","information_gain","capacity_used_hours"]]
    fig=px.scatter(frontier,x="risk_per_hour",y="severe_recall",size="information_gain",text="policy",title="Review-policy efficiency frontier")
    fig.update_traces(textposition="top center")
    st.plotly_chart(style_fig(fig,455),use_container_width=True)
    st.caption("Every policy sees the same synthetic queue and the same analyst-hour constraint. Bubble size represents information gain.")

with tabs[3]:
    sample=df.sample(min(2800,len(df)),random_state=7)
    fig=px.scatter(sample,x="uncertainty",y="novelty",color="information_gain",size="expected_loss",hover_data=["risk","review_minutes","severe"],title="Information-gain landscape")
    st.plotly_chart(style_fig(fig,455),use_container_width=True)
    st.info("A lower-risk case can still be valuable if it is uncertain, novel, high-loss, and cheap to review. The hybrid policy makes that tradeoff explicit.")

with tabs[4]:
    st.markdown("#### Ranked queue")
    queue_view=ranked.head(1200)
    st.dataframe(queue_view,hide_index=True,use_container_width=True)
    st.download_button("Export selected reviews",selected.to_csv(index=False),"revieweriq_selected.csv","text/csv")

st.markdown('<p class="note">Synthetic queue and outcomes. “Risk caught” is a simulation metric, not a claim about real fraud loss, security incident prevention, or analyst performance.</p>',unsafe_allow_html=True)
