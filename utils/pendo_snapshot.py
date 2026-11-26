"""
utils/pendo_snapshot.py
Pendo-only engagement block for the Snap tab.

Used only while a customer's Snowflake schema isn't available yet (see
snowflake_pending in utils/snowflake_conn.py). Customers with Snowflake data
keep using the full engagement section in Home.py; this file isn't involved.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.pendo_conn import (
    get_page_views,
    get_combined_page_views,
    get_combined_visitor_count,
    get_page_map,
)

PURPLE = "#9B59B6"


def _pendo_ids(customer, customer_name):
    ids = customer.get("pendo_ids")
    return ids if ids else [customer.get("pendo_id", customer_name.lower())]


def _page_views(ids, days):
    if len(ids) > 1:
        return get_combined_page_views(ids, days)
    return get_page_views(ids[0], days)


def _iframe_mau(df, page_map):
    """Unique visitors on pages whose name contains 'iframe'. None if we can't tell."""
    if df.empty or not page_map or "pageId" not in df.columns or "visitorId" not in df.columns:
        return None
    names = df["pageId"].map(lambda p: str(page_map.get(p, "")))
    return int(df.loc[names.str.contains("[iframe]", case=False, regex=False, na=False), "visitorId"].nunique())


def _trend_chart(x, y, title, suffix="", bar=False, height=220):
    fig = go.Figure()
    if bar:
        fig.add_trace(go.Bar(x=x, y=y, marker_color=PURPLE, opacity=0.8))
    else:
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines+markers",
            line=dict(color=PURPLE, width=2),
            fill="tozeroy", fillcolor="rgba(155,89,182,0.15)",
            marker=dict(size=4),
        ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#e6edf3")),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8b949e", size=10), height=height,
        margin=dict(l=0, r=0, t=36, b=0), showlegend=False,
        xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=9)),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", ticksuffix=suffix),
    )
    return fig


def render_pendo_only_snapshot(customer, customer_name):
    ids = _pendo_ids(customer, customer_name)

    st.markdown("#### 📊 Engagement (Pendo)")
    st.caption("Case-based metrics (volume, FRT, escalations, AI summaries) appear here "
               "once Snowflake data is available.")

    with st.spinner("Loading Pendo data..."):
        df_30 = _page_views(ids, 30)
        df_180 = _page_views(ids, 180)
        mau_90 = get_combined_visitor_count(ids, 90)
        try:
            page_map = get_page_map()
        except Exception:
            page_map = {}

    if df_180.empty or "date" not in df_180.columns:
        st.info("No Pendo activity found in the last 180 days for this account.")
        return

    iframe = _iframe_mau(df_30, page_map)
    c1, c2, _, _ = st.columns(4)
    c1.metric("Iframe MAU (last 30d)", f"{iframe:,}" if iframe is not None else "—",
              "Agents via CRM iframe only · Pendo", delta_color="off")
    c2.metric("Active UI users (90d)", f"{mau_90:,}",
              "Unique users who opened SL UI · last 90d", delta_color="off")

    df = df_180.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["week"] = df["date"].dt.to_period("W").dt.start_time
    weekly = (df.groupby("week")
                .agg(total_minutes=("numMinutes", "sum"),
                     total_events=("numEvents", "sum"),
                     unique_users=("visitorId", "nunique"))
                .reset_index())
    weekly["label"] = weekly["week"].dt.strftime("%b %d")
    weekly["hours"] = (weekly["total_minutes"] / 60).round(1)

    st.markdown("#### 📈 Platform engagement trends (last 6 months · weekly)")
    st.caption("Source: Pendo · Time on platform and views/clicks rolled up weekly")
    t1, t2 = st.columns(2)
    t1.plotly_chart(_trend_chart(weekly["label"], weekly["hours"],
                                 "⏱ Time on platform (hrs/week)", suffix="h"))
    t2.plotly_chart(_trend_chart(weekly["label"], weekly["total_events"],
                                 "👆 Views & clicks (events/week)"))
    st.plotly_chart(_trend_chart(weekly["label"], weekly["unique_users"],
                                 "👥 Weekly active users", bar=True, height=180))
