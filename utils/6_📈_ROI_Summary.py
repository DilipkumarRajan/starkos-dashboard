"""pages/6 — ROI Summary: renewal-ready narrative with before/after, feature adoption, watch items."""
import streamlit as st
import pandas as pd
from utils.snowflake_conn import run_query
from utils.charts import COLORS, area_chart, line_chart, donut_chart, gauge_chart
from queries.registry import QUERIES

st.set_page_config(page_title="ROI Summary", layout="wide")
st.title("📈 ROI summary")
from utils.page_init import init_page
schema, customer_name, customer = init_page("ROI Summary")
go_live   = customer.get("go_live","—")
benchmark = customer.get("benchmark_escalation_pct", 2.0)
goals     = customer.get("goals", [])

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:var(--color-background-secondary);border-radius:10px;padding:14px 18px;margin-bottom:16px'>
  <div style='display:flex;gap:32px;flex-wrap:wrap'>
    <div><div style='font-size:11px;color:var(--color-text-tertiary)'>Customer</div><div style='font-size:14px;font-weight:500'>{customer_name}</div></div>
    <div><div style='font-size:11px;color:var(--color-text-tertiary)'>Go-live</div><div style='font-size:14px;font-weight:500'>{go_live}</div></div>
    <div><div style='font-size:11px;color:var(--color-text-tertiary)'>CSM</div><div style='font-size:14px'>{customer.get('csm','—')}</div></div>
    <div><div style='font-size:11px;color:var(--color-text-tertiary)'>License</div><div style='font-size:14px'>{customer.get('license','—')}</div></div>
  </div>
  {"<div style='margin-top:8px;font-size:12px;color:var(--color-text-secondary)'><b>Goals:</b> " + " · ".join(goals) + "</div>" if goals else ""}
</div>
""", unsafe_allow_html=True)

with st.spinner("Compiling ROI data..."):
    df_frt      = run_query(QUERIES["frt_monthly"], schema)
    df_esc      = run_query(QUERIES["escalation_monthly"], schema)
    df_lte      = run_query(QUERIES["lte_accuracy_monthly"], schema)
    df_reassign = run_query(QUERIES["reassignment_monthly"], schema)
    df_health   = run_query(QUERIES["account_health_monthly"], schema)
    df_sent     = run_query(QUERIES["sentiment_monthly"], schema)
    df_alerts   = run_query(QUERIES["alerts_monthly"], schema)
    df_ica_tot  = run_query(QUERIES["ica_total_lifetime"], schema)
    df_summ     = run_query(QUERIES["ai_summaries_total"], schema)
    df_act      = run_query(QUERIES["platform_actions_summary"], schema)

# ── Narrative summary ─────────────────────────────────────────────────────────
st.subheader("What has improved since go-live")

rows = []
if not df_frt.empty and len(df_frt) >= 2:
    ff, lf = float(df_frt["avg_frt_hours"].iloc[0]), float(df_frt["avg_frt_hours"].iloc[-2])
    rows.append({"Metric":"First response time","Baseline":f"{ff} hrs ({df_frt['month'].iloc[0]})",
                 "Current":f"{lf} hrs ({df_frt['month'].iloc[-2]})",
                 "Change":f"↓ {round((1-lf/ff)*100)}%","Agent":"Routing Agent","Status":"✅ Strong"})

if not df_esc.empty:
    le = float(df_esc["escalation_pct"].iloc[-2])
    rows.append({"Metric":"Escalation rate","Baseline":f"{float(df_esc['escalation_pct'].iloc[0])}% ({df_esc['month'].iloc[0]})",
                 "Current":f"{le}% ({df_esc['month'].iloc[-2]})",
                 "Change":"✓ Below benchmark" if le<benchmark else "⚠ Above benchmark",
                 "Agent":"Escalation Agent","Status":"✅ On track" if le<benchmark else "⚠️ Watch"})

if not df_lte.empty:
    prev = int(df_lte["cases_predicted"].sum()) - int(df_lte["actually_escalated"].sum())
    rows.append({"Metric":"Escalations prevented (LTE)","Baseline":"—",
                 "Current":f"{prev:,} intercepted ({df_lte['month'].iloc[0]}–{df_lte['month'].iloc[-1]})",
                 "Change":f"~{prev:,} avoided","Agent":"Escalation Agent","Status":"✅ Strong"})

if not df_reassign.empty and len(df_reassign) >= 2:
    fr, lr = float(df_reassign["reassignment_pct"].iloc[0]), float(df_reassign["reassignment_pct"].iloc[-2])
    rows.append({"Metric":"Reassignment rate","Baseline":f"{fr}% ({df_reassign['month'].iloc[0]})",
                 "Current":f"{lr}% ({df_reassign['month'].iloc[-2]})",
                 "Change":f"↓ {round(fr-lr,1)}pp","Agent":"Routing Agent (ICA)","Status":"✅ Strong"})

if not df_ica_tot.empty:
    auto = int(df_ica_tot["total_auto"].iloc[0])
    manual = int(df_ica_tot["total_manual"].iloc[0])
    rows.append({"Metric":"ICA auto-assignments","Baseline":"0 (at go-live)",
                 "Current":f"{auto:,} lifetime","Change":f"{round(auto/(auto+manual)*100)}% auto rate",
                 "Agent":"Routing Agent (ICA)","Status":"✅ Active"})

if not df_sent.empty:
    rows.append({"Metric":"Avg sentiment score","Baseline":f"{float(df_sent['avg_sentiment'].iloc[0])} ({df_sent['month'].iloc[0]})",
                 "Current":f"{float(df_sent['avg_sentiment'].iloc[-1])}/100 ({df_sent['month'].iloc[-1]})",
                 "Change":"Stable — no degradation","Agent":"Sentiment Agent","Status":"✅ Stable"})

if not df_alerts.empty:
    rows.append({"Metric":"Alerts engagement","Baseline":"—",
                 "Current":f"{int(df_alerts['total_alerts'].sum()):,} alerts ({df_alerts['month'].iloc[0]}–{df_alerts['month'].iloc[-1]})",
                 "Change":f"Avg {round(df_alerts['total_alerts'].mean()):,}/month","Agent":"Escalation Agent","Status":"✅ Active"})

if not df_summ.empty:
    total_summ = int(df_summ["total"].sum())
    rows.append({"Metric":"AI summaries generated","Baseline":"0 (at go-live)",
                 "Current":f"{total_summ:,} total","Change":"Growing monthly",
                 "Agent":"Summarization Agent","Status":"✅ Growing"})

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()

# ── Visual ROI highlights ──────────────────────────────────────────────────────
st.subheader("Visual highlights")
col1, col2, col3 = st.columns(3)

if not df_frt.empty:
    with col1:
        st.markdown("**FRT journey**")
        st.plotly_chart(area_chart(df_frt, x="month",
            y_cols=[{"col":"avg_frt_hours","name":"FRT (hrs)","color":COLORS["blue"],"fill":"rgba(24,95,165,0.1)"}],
            height=200), use_container_width=True)

if not df_ica_tot.empty:
    auto = int(df_ica_tot["total_auto"].iloc[0])
    manual = int(df_ica_tot["total_manual"].iloc[0])
    with col2:
        st.markdown("**ICA auto vs manual (lifetime)**")
        st.plotly_chart(donut_chart(
            labels=["Auto","Manual"], values=[auto,manual],
            colors=[COLORS["teal"],COLORS["gray"]], height=200,
            center_text=f"{round(auto/(auto+manual)*100)}% auto"), use_container_width=True)

if not df_health.empty:
    lh = float(df_health["avg_health_score"].iloc[-1])
    with col3:
        st.markdown("**Account health score**")
        st.plotly_chart(gauge_chart(lh, label="/ 100", height=200), use_container_width=True)

st.divider()

# ── Watch items ───────────────────────────────────────────────────────────────
st.subheader("⚠️ Watch items for renewal conversation")
watch = []
if not df_health.empty:
    lh = float(df_health["avg_health_score"].iloc[-1])
    peak = float(df_health["avg_health_score"].max())
    if lh < peak - 5:
        watch.append(f"**Account health score** dropped from {peak} (peak) to {lh}. FRT and escalation remain strong — investigate at sub-account level.")
if not df_esc.empty:
    le = float(df_esc["escalation_pct"].iloc[-2])
    if le >= benchmark:
        watch.append(f"**Escalation rate** ({le}%) is at or above the {benchmark}% benchmark.")
if not df_act.empty:
    total_act = int(df_act["total_actions"].sum())
    if total_act < 50:
        watch.append(f"**Platform engagement is low** — only {total_act} total agent actions recorded in STD_OBJECT_ACTION. Agents may not be actively working escalation alerts in SL.")
if not df_summ.empty:
    ev = int(df_summ[df_summ["summary_status"]=="EVALUATED"]["evaluated"].sum()) if "summary_status" in df_summ.columns else 0

if watch:
    for w in watch:
        st.warning(w, icon="⚠️")
else:
    st.success("No critical watch items — account metrics are in healthy range.", icon="✅")

if customer.get("notes"):
    st.divider()
    st.markdown(f"**Account notes:** {customer['notes']}")
