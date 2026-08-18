"""pages/3 — Sentiment: area charts, alerts stacked bar."""
import streamlit as st
from utils.snowflake_conn import run_query
from utils.charts import COLORS, area_chart, stacked_bar, bar_chart
from queries.registry import QUERIES

st.set_page_config(page_title="Sentiment", layout="wide")
st.title("😊 Sentiment & voice of customer")
from utils.page_init import init_page
schema, customer_name, customer = init_page("Sentiment")

with st.spinner("Loading..."):
    df_sent   = run_query(QUERIES["sentiment_monthly"], schema)
    df_alerts = run_query(QUERIES["alerts_monthly"], schema)

c1,c2,c3,c4 = st.columns(4)
if not df_sent.empty:
    c1.metric("Avg sentiment (latest)", f"{float(df_sent['avg_sentiment'].iloc[-1])}/100")
    c2.metric("Need-attention score",   f"{float(df_sent['avg_need_attention'].iloc[-1])}/100", "Lower = healthier", delta_color="off")
    c3.metric("Cases scored (latest)",  f"{int(df_sent['cases_scored'].iloc[-1]):,}", "100% comment coverage")
if not df_alerts.empty:
    c4.metric("Total alerts (period)",  f"{int(df_alerts['total_alerts'].sum()):,}")

st.divider()
col_l, col_r = st.columns(2)
if not df_sent.empty:
    with col_l:
        st.markdown("**Sentiment & need-attention score — monthly**")
        st.plotly_chart(area_chart(df_sent, x="month",
            y_cols=[
                {"col":"avg_sentiment","name":"Sentiment (higher = better)","color":COLORS["teal"],"fill":"rgba(15,110,86,0.12)"},
                {"col":"avg_need_attention","name":"Need-attention (lower = better)","color":COLORS["amber"],"fill":"rgba(186,117,23,0.08)"},
            ], height=280), use_container_width=True)

if not df_alerts.empty:
    with col_r:
        st.markdown("**Alerts consumption — monthly**")
        st.plotly_chart(stacked_bar(df_alerts, x="month",
            y_cols=[
                {"col":"alert_cases","name":"Unique alert cases","color":COLORS["teal"]},
                {"col":"total_alerts","name":"Total alerts fired","color":COLORS["teal_light"]},
            ], height=280), use_container_width=True)

st.caption("Sentiment scored from every inbound and outbound comment via SupportLogic NLP. "
           "Stable 70–72 range with need-attention below 35 indicates a well-managed account.")
