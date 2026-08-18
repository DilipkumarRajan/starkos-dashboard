"""pages/2 — Escalation Intelligence: LTE predictions, swarming, rate vs benchmark."""
import streamlit as st
import pandas as pd
from utils.snowflake_conn import run_query
from utils.charts import COLORS, line_chart, combo_chart, stacked_bar, donut_chart
from queries.registry import QUERIES

st.set_page_config(page_title="Escalation Intelligence", layout="wide")
st.title("🛡️ Escalation intelligence")
from utils.page_init import init_page
schema, customer_name, customer = init_page("Escalation Intelligence")
benchmark = customer.get("benchmark_escalation_pct", 2.0)

with st.spinner("Loading..."):
    df_esc  = run_query(QUERIES["escalation_monthly"], schema)
    df_lte  = run_query(QUERIES["lte_accuracy_monthly"], schema)
    df_rev  = run_query(QUERIES["escalation_reviews_monthly"], schema)

c1,c2,c3,c4 = st.columns(4)
if not df_lte.empty:
    pred  = int(df_lte["cases_predicted"].sum())
    act   = int(df_lte["actually_escalated"].sum())
    prev  = pred - act
    c1.metric("Cases flagged by LTE", f"{pred:,}")
    c2.metric("Escalations prevented", f"{prev:,}", f"{round(prev/pred*100)}% intercepted", delta_color="normal")
    c3.metric("Avg LTE hit rate", f"{round(float(df_lte['hit_rate_pct'].mean()),1)}%", "Low = agents intervening ✓", delta_color="off")
if not df_esc.empty:
    le = float(df_esc["escalation_pct"].iloc[-2])
    c4.metric("Latest esc. rate", f"{le}%", f"{'✓ Below' if le<benchmark else '⚠ Above'} {benchmark}% benchmark",
              delta_color="normal" if le<benchmark else "inverse")

st.info("**LTE hit rate:** Low (3–8%) = SupportLogic is flagging risk early enough for agents to intervene before a formal escalation is filed. This is the intended outcome.", icon="ℹ️")
st.divider()

col_l, col_r = st.columns(2)
if not df_lte.empty:
    with col_l:
        st.markdown("**LTE predictions vs actual escalations**")
        st.plotly_chart(combo_chart(df_lte, x="month",
            bar_col={"col":"cases_predicted","name":"Predicted (LTE)","color":COLORS["amber_light"]},
            line_col={"col":"actually_escalated","name":"Actually escalated","color":COLORS["red"]},
            height=260), use_container_width=True)
if not df_esc.empty:
    with col_r:
        st.markdown("**Escalation rate trend vs benchmark**")
        st.plotly_chart(line_chart(df_esc, x="month",
            y_cols=[{"col":"escalation_pct","name":"Esc %","color":COLORS["red"]}],
            reference_lines=[{"y":benchmark,"label":f"{benchmark}% benchmark","color":COLORS["red"]}],
            height=260), use_container_width=True)

col_l2, col_r2 = st.columns(2)
if not df_lte.empty:
    with col_l2:
        st.markdown("**LTE hit rate % — monthly**")
        st.plotly_chart(line_chart(df_lte, x="month",
            y_cols=[{"col":"hit_rate_pct","name":"Hit rate %","color":COLORS["purple"]}],
            height=240), use_container_width=True)

if not df_rev.empty:
    with col_r2:
        st.markdown("**Escalation review swarming — monthly**")
        pivot = df_rev.pivot_table(index="month", columns="status", values="cnt", aggfunc="sum", fill_value=0).reset_index()
        status_colors = {"COMPLETED":COLORS["teal"],"PENDING":COLORS["amber"],"SNOOZED":COLORS["blue"],"REJECTED":COLORS["red"]}
        y_cols = [{"col":s,"name":s.capitalize(),"color":status_colors.get(s,COLORS["gray"])}
                  for s in [c for c in pivot.columns if c != "month"]]
        st.plotly_chart(stacked_bar(pivot, x="month", y_cols=y_cols, height=240), use_container_width=True)
        total_rev = int(df_rev["cnt"].sum())
        completed = int(df_rev[df_rev["status"]=="COMPLETED"]["cnt"].sum())
        st.caption(f"Total escalation reviews: {total_rev} · Completed: {completed} ({round(completed/total_rev*100) if total_rev else 0}%)")
