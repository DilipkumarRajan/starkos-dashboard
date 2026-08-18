"""pages/5 — Feature Usage: which SL features are active, platform engagement, AI adoption."""
import streamlit as st
import pandas as pd
from utils.snowflake_conn import run_query
from utils.charts import COLORS, stacked_bar, donut_chart, bar_chart, line_chart, area_chart
from queries.registry import QUERIES

st.set_page_config(page_title="Feature Usage", layout="wide")
st.title("🔬 Feature usage")
from utils.page_init import init_page
schema, customer_name, customer = init_page("Feature Usage")

with st.spinner("Loading..."):
    df_actions  = run_query(QUERIES["platform_actions_monthly"], schema)
    df_act_sum  = run_query(QUERIES["platform_actions_summary"], schema)
    df_summ_tot = run_query(QUERIES["ai_summaries_total"], schema)
    df_summ_mo  = run_query(QUERIES["ai_summaries_monthly"], schema)
    df_ica_tot  = run_query(QUERIES["ica_total_lifetime"], schema)
    df_lte      = run_query(QUERIES["lte_accuracy_monthly"], schema)
    df_alerts   = run_query(QUERIES["alerts_monthly"], schema)
    df_sent     = run_query(QUERIES["sentiment_monthly"], schema)

# ── Feature status grid ───────────────────────────────────────────────────────
st.subheader("Licensed features — activation status")

features = [
    {"name":"Routing Agent (ICA)",      "status":"active",      "evidence": f"{int(df_ica_tot['total_auto'].iloc[0]):,} auto-assignments" if not df_ica_tot.empty else "data available"},
    {"name":"Escalation Agent (LTE)",   "status":"active",      "evidence": f"{int(df_lte['cases_predicted'].sum()):,} predictions made" if not df_lte.empty else "data available"},
    {"name":"Sentiment Agent",          "status":"active",      "evidence": f"{int(df_sent['cases_scored'].sum()):,} cases scored" if not df_sent.empty else "data available"},
    {"name":"Account Health Agent",     "status":"active",      "evidence": "ML health scores generated monthly"},
    {"name":"Alerts",                   "status":"active",      "evidence": f"{int(df_alerts['total_alerts'].sum()):,} alerts fired" if not df_alerts.empty else "data available"},
    {"name":"Summarization Agent",      "status":"partial",     "evidence": "Case + account summaries generated (growing)"},
    {"name":"Escalation Swarming",      "status":"active",      "evidence": "Escalation reviews in std_escalation_review"},
    {"name":"Elevate / QA Agent",       "status":"not_licensed","evidence": "No ticket review data in schema"},
    {"name":"ResolveSX / Knowledge",    "status":"not_licensed","evidence": "Not present in schema"},
]

status_color = {"active":"✅","partial":"🟡","not_licensed":"⬜"}
cols = st.columns(3)
for i, f in enumerate(features):
    with cols[i % 3]:
        icon = status_color[f["status"]]
        color = ("var(--color-background-success)" if f["status"]=="active"
                 else "var(--color-background-warning)" if f["status"]=="partial"
                 else "var(--color-background-secondary)")
        st.markdown(f"""<div style='padding:10px 14px;border-radius:8px;background:{color};margin-bottom:8px'>
            <div style='font-size:13px;font-weight:500'>{icon} {f['name']}</div>
            <div style='font-size:11px;color:var(--color-text-secondary);margin-top:2px'>{f['evidence']}</div>
        </div>""", unsafe_allow_html=True)

st.divider()

# ── Platform engagement ───────────────────────────────────────────────────────
col_l, col_r = st.columns(2)
if not df_act_sum.empty:
    with col_l:
        st.markdown("**Agent actions on SL signals (lifetime breakdown)**")
        action_colors = [COLORS["teal"],COLORS["blue"],COLORS["purple"],COLORS["amber"],
                         COLORS["red"],COLORS["green"],COLORS["coral"],COLORS["gray"]]
        st.plotly_chart(bar_chart(df_act_sum, x="action_type",
            y_cols=[{"col":"total_actions","name":"Actions","color":[action_colors[i%len(action_colors)] for i in range(len(df_act_sum))],
                     "colors":[action_colors[i%len(action_colors)] for i in range(len(df_act_sum))]}],
            height=280, horizontal=True), use_container_width=True)

if not df_actions.empty:
    with col_r:
        pivot = df_actions.pivot_table(index="month", columns="action_type", values="cnt",
                                       aggfunc="sum", fill_value=0).reset_index()
        action_cols_list = [c for c in pivot.columns if c != "month"]
        action_colors2 = [COLORS["teal"],COLORS["blue"],COLORS["purple"],COLORS["amber"],
                          COLORS["red"],COLORS["green"],COLORS["coral"],COLORS["gray"]]
        y_cols = [{"col":c,"name":c.replace("_"," ").title(),"color":action_colors2[i%len(action_colors2)]}
                  for i,c in enumerate(action_cols_list)]
        st.markdown("**Platform engagement by action type — monthly**")
        st.plotly_chart(stacked_bar(pivot, x="month", y_cols=y_cols, height=280), use_container_width=True)

st.divider()

# ── AI Summarization adoption ─────────────────────────────────────────────────
col_l2, col_r2 = st.columns(2)
if not df_summ_tot.empty:
    with col_l2:
        st.markdown("**AI summaries generated — by type (lifetime)**")
        st.plotly_chart(donut_chart(
            labels=df_summ_tot["summary_type"].tolist(),
            values=df_summ_tot["total"].tolist(),
            colors=[COLORS["blue"],COLORS["teal"],COLORS["purple"],COLORS["amber"]],
            height=260,
            center_text=f"{int(df_summ_tot['total'].sum()):,} total",
        ), use_container_width=True)

if not df_summ_mo.empty:
    with col_r2:
        pivot2 = df_summ_mo.groupby(["month","summary_type"])["summaries_generated"].sum().reset_index()
        pivot2 = pivot2.pivot_table(index="month", columns="summary_type", values="summaries_generated",
                                    aggfunc="sum", fill_value=0).reset_index()
        st_cols = [c for c in pivot2.columns if c != "month"]
        c_map = [COLORS["blue"],COLORS["teal"],COLORS["purple"],COLORS["amber"]]
        y2 = [{"col":c,"name":c.replace("_"," ").title(),"color":c_map[i%len(c_map)]} for i,c in enumerate(st_cols)]
        st.markdown("**AI summaries generated — monthly trend**")
        st.plotly_chart(stacked_bar(pivot2, x="month", y_cols=y2, height=260), use_container_width=True)
