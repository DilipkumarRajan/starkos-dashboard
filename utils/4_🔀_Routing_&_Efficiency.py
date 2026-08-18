"""pages/4 — Routing & Efficiency: ICA step-line, reassignment colored bars, FRT by priority, workload bubble."""
import streamlit as st
import pandas as pd
from utils.snowflake_conn import run_query
from utils.charts import COLORS, line_chart, bar_chart, combo_chart, step_line, bubble_chart, stacked_bar
from queries.registry import QUERIES

st.set_page_config(page_title="Routing & Efficiency", layout="wide")
st.title("🔀 Routing & operational efficiency")
from utils.page_init import init_page
schema, customer_name, customer = init_page("Routing & Efficiency")

with st.spinner("Loading..."):
    df_ica      = run_query(QUERIES["ica_events_monthly"], schema)
    df_ica_tot  = run_query(QUERIES["ica_total_lifetime"], schema)
    df_reassign = run_query(QUERIES["reassignment_monthly"], schema)
    df_frt_pri  = run_query(QUERIES["frt_by_priority"], schema)
    df_cpa      = run_query(QUERIES["cases_per_agent_weekly"], schema)
    df_frt      = run_query(QUERIES["frt_monthly"], schema)

c1,c2,c3,c4 = st.columns(4)
if not df_ica_tot.empty:
    auto   = int(df_ica_tot["total_auto"].iloc[0])
    manual = int(df_ica_tot["total_manual"].iloc[0])
    c1.metric("ICA auto-assignments (lifetime)", f"{auto:,}")
    c2.metric("Auto-assignment rate", f"{round(auto/(auto+manual)*100)}%", f"{manual:,} manual", delta_color="off")
if not df_reassign.empty:
    fr = float(df_reassign["reassignment_pct"].iloc[0])
    lr = float(df_reassign["reassignment_pct"].iloc[-2])
    c3.metric("Reassignment rate (latest)", f"{lr}%", f"↓ {round(fr-lr,1)}pp from {fr}%", delta_color="normal")
if not df_frt.empty:
    c4.metric("Overall FRT (latest)", f"{float(df_frt['avg_frt_hours'].iloc[-2])} hrs")

st.divider()

col_l, col_r = st.columns(2)
if not df_ica.empty:
    with col_l:
        st.markdown("**ICA auto vs manual assignments — monthly**")
        st.plotly_chart(stacked_bar(df_ica, x="month",
            y_cols=[
                {"col":"auto_assigned","name":"Auto (ICA)","color":COLORS["teal"]},
                {"col":"manual_assigned","name":"Manual","color":COLORS["gray"]},
            ], height=260), use_container_width=True)
if not df_reassign.empty:
    with col_r:
        colors = [COLORS["red"] if v>5 else COLORS["amber"] if v>1 else COLORS["teal"]
                  for v in df_reassign["reassignment_pct"]]
        st.markdown("**Reassignment rate — monthly** *(red >5%, amber 1–5%, green <1%)*")
        st.plotly_chart(bar_chart(df_reassign, x="month",
            y_cols=[{"col":"reassignment_pct","name":"Reassignment %","color":colors,"colors":colors}],
            height=260), use_container_width=True)

col_l2, col_r2 = st.columns(2)
if not df_frt_pri.empty:
    pivot = df_frt_pri.pivot_table(index="month", columns="priority_tier",
                                   values="avg_frt_hours", aggfunc="mean").reset_index()
    cols = [c for c in ["P1 Critical","P2 High","P3 Medium","P4/Other"] if c in pivot.columns]
    cm = {"P1 Critical":COLORS["red"],"P2 High":COLORS["amber"],"P3 Medium":COLORS["blue"],"P4/Other":COLORS["gray"]}
    with col_l2:
        st.markdown("**FRT by priority tier (hrs) — monthly**")
        st.plotly_chart(line_chart(pivot, x="month",
            y_cols=[{"col":c,"name":c,"color":cm.get(c,COLORS["gray"])} for c in cols],
            height=260), use_container_width=True)

if not df_cpa.empty:
    df_plot = df_cpa.iloc[:-1].copy()
    df_plot["week_start"] = pd.to_datetime(df_plot["week_start"])
    df_plot = df_plot[df_plot["week_start"].dt.year >= 2025]
    df_plot["week_label"] = df_plot["week_start"].dt.strftime("%-m/%-d")
    with col_r2:
        st.markdown("**Cases per agent — weekly workload**")
        st.plotly_chart(bar_chart(df_plot, x="week_label",
            y_cols=[{"col":"cases_per_agent","name":"Cases/agent","color":COLORS["purple"]}],
            height=260), use_container_width=True)
