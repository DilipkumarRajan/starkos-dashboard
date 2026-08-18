"""pages/1 — Account Snapshot: gauges + area charts for at-a-glance view."""
import streamlit as st
import pandas as pd
from utils.snowflake_conn import run_query
from utils.charts import COLORS, area_chart, combo_chart, gauge_chart, donut_chart
from queries.registry import QUERIES

st.set_page_config(page_title="Account Snapshot", layout="wide")
st.title("📋 Account snapshot")
from utils.page_init import init_page
schema, customer_name, customer = init_page("Account Snapshot")

with st.spinner("Loading..."):
    df_frt    = run_query(QUERIES["frt_monthly"], schema)
    df_esc    = run_query(QUERIES["escalation_monthly"], schema)
    df_health = run_query(QUERIES["account_health_monthly"], schema)
    df_sent   = run_query(QUERIES["sentiment_monthly"], schema)
    df_ica    = run_query(QUERIES["ica_total_lifetime"], schema)

# ── KPI metrics ──────────────────────────────────────────────────────────────
c1,c2,c3,c4,c5 = st.columns(5)
if not df_frt.empty:
    lf = float(df_frt["avg_frt_hours"].iloc[-2])
    ff = float(df_frt["avg_frt_hours"].iloc[0])
    c1.metric("First response time", f"{lf} hrs", f"↓ {round((1-lf/ff)*100)}% since go-live", delta_color="normal")
if not df_esc.empty:
    le = float(df_esc["escalation_pct"].iloc[-2])
    c2.metric("Escalation rate", f"{le}%", "✓ Below 2% benchmark" if le<2 else "⚠ Above benchmark", delta_color="inverse")
if not df_health.empty:
    lh = float(df_health["avg_health_score"].iloc[-1])
    ph = float(df_health["avg_health_score"].iloc[-2])
    dh = round(lh-ph,1)
    c3.metric("Account health", f"{lh}/100", f"{'+' if dh>=0 else ''}{dh} vs prior month", delta_color="normal" if dh>=0 else "inverse")
if not df_sent.empty:
    c4.metric("Avg sentiment", f"{float(df_sent['avg_sentiment'].iloc[-1])}/100", "Stable")
if not df_ica.empty:
    auto = int(df_ica["total_auto"].iloc[0])
    c5.metric("ICA auto-assignments", f"{auto:,}", "Lifetime total")

st.divider()

# ── Row 1: Gauges + area chart ────────────────────────────────────────────────
col_g1, col_g2, col_g3, col_area = st.columns([1,1,1,3])
if not df_health.empty:
    lh = float(df_health["avg_health_score"].iloc[-1])
    with col_g1:
        st.markdown("**Health score**")
        st.plotly_chart(gauge_chart(lh, label="/ 100"), use_container_width=True)
if not df_sent.empty:
    ls = float(df_sent["avg_sentiment"].iloc[-1])
    with col_g2:
        st.markdown("**Sentiment**")
        st.plotly_chart(gauge_chart(ls, label="/ 100"), use_container_width=True)
if not df_esc.empty:
    le = float(df_esc["escalation_pct"].iloc[-2])
    with col_g3:
        st.markdown("**Esc. rate**")
        st.plotly_chart(gauge_chart(le, min_val=0, max_val=5,
            thresholds=[{"range":[0,1],"color":COLORS["teal_light"]},
                        {"range":[1,2],"color":COLORS["amber_light"]},
                        {"range":[2,5],"color":COLORS["red_light"]}],
            label="%"), use_container_width=True)
if not df_frt.empty:
    with col_area:
        st.markdown("**First response time — monthly (hrs)**")
        st.plotly_chart(area_chart(df_frt, x="month",
            y_cols=[{"col":"avg_frt_hours","name":"FRT (hrs)","color":COLORS["blue"],"fill":"rgba(24,95,165,0.1)"}],
            height=200), use_container_width=True)

st.divider()

# ── Row 2: ICA donut + escalation combo ──────────────────────────────────────
col_d, col_c = st.columns([1,2])
if not df_ica.empty:
    auto = int(df_ica["total_auto"].iloc[0])
    manual = int(df_ica["total_manual"].iloc[0])
    with col_d:
        st.markdown("**ICA auto vs manual assignments (lifetime)**")
        st.plotly_chart(donut_chart(
            labels=["Auto (ICA)","Manual"],
            values=[auto, manual],
            colors=[COLORS["teal"], COLORS["gray"]],
            height=240,
            center_text=f"{round(auto/(auto+manual)*100)}% auto",
        ), use_container_width=True)
if not df_esc.empty:
    with col_c:
        st.markdown("**Escalation rate vs case volume**")
        st.plotly_chart(combo_chart(df_esc, x="month",
            bar_col={"col":"total_cases","name":"Cases","color":COLORS["gray_light"]},
            line_col={"col":"escalation_pct","name":"Esc %","color":COLORS["red"]},
            reference_lines=[{"y":2.0,"label":"2% benchmark","color":COLORS["red"]}],
            height=240), use_container_width=True)

# ── Row 3: health + sentiment area ───────────────────────────────────────────
col_h, col_s = st.columns(2)
if not df_health.empty:
    with col_h:
        st.markdown("**Account health score trend**")
        st.plotly_chart(area_chart(df_health, x="month",
            y_cols=[{"col":"avg_health_score","name":"Health score","color":COLORS["purple"],"fill":"rgba(83,74,183,0.1)"}],
            reference_lines=[{"y":80,"label":"Score 80","color":COLORS["gray"]}],
            height=220), use_container_width=True)
if not df_sent.empty:
    with col_s:
        st.markdown("**Sentiment vs need-attention**")
        st.plotly_chart(area_chart(df_sent, x="month",
            y_cols=[
                {"col":"avg_sentiment","name":"Sentiment","color":COLORS["teal"],"fill":"rgba(15,110,86,0.1)"},
                {"col":"avg_need_attention","name":"Need attention","color":COLORS["amber"],"fill":"rgba(186,117,23,0.08)"},
            ], height=220), use_container_width=True)
