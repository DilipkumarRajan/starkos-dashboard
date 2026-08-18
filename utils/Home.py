"""
Home.py — SupportLogic Account Performance Dashboard
Main entry point. Run with: streamlit run Home.py
"""

import streamlit as st
from utils.customers import CUSTOMERS

st.set_page_config(
    page_title="SL Account Dashboard",
    page_icon="assets/sl_logo.png" if __import__("os").path.exists("assets/sl_logo.png") else "📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0d1117; }
    [data-testid="stSidebar"] * { color: #e6edf3 !important; }
    [data-testid="stSidebar"] .stSelectbox label { color: #8b949e !important; font-size: 12px; }
    .metric-card { background: #f8f9fa; border-radius: 8px; padding: 14px 16px; border: 1px solid #e9ecef; }
    .sl-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
    .badge-green { background: #d4edda; color: #155724; }
    .badge-amber { background: #fff3cd; color: #856404; }
    .badge-red   { background: #f8d7da; color: #721c24; }
    .badge-blue  { background: #d1ecf1; color: #0c5460; }
    div[data-testid="metric-container"] { background: #f8f9fa; border-radius: 8px; padding: 12px; border: 1px solid #e9ecef; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { font-size: 13px; padding: 8px 16px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 SupportLogic")
    st.markdown("**Account Performance Dashboard**")
    st.divider()

    selected_customer = st.selectbox(
        "Customer",
        options=list(CUSTOMERS.keys()),
        index=0,
        help="Select a customer to load their metrics",
    )

    customer = CUSTOMERS[selected_customer]

    st.markdown("---")
    st.markdown(f"**Schema:** `{customer['schema']}`")
    if customer.get("go_live"):
        st.markdown(f"**Go-live:** {customer['go_live']}")
    if customer.get("csm"):
        st.markdown(f"**CSM:** {customer['csm']}")
    if customer.get("sa"):
        st.markdown(f"**SA:** {customer['sa']}")
    if customer.get("license"):
        st.markdown(f"**License:** {customer['license']}")
    if customer.get("goals"):
        st.markdown("**Goals:**")
        for g in customer["goals"]:
            st.markdown(f"  • {g}")
    if customer.get("notes"):
        st.markdown("---")
        st.caption(customer["notes"])

    st.markdown("---")
    st.caption("Data refreshes every hour · Snowflake PIPE_DATABASE")

    if st.button("🔄 Clear cache & refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Store selection in session so pages can access it ────────────────────────
st.session_state["customer_name"] = selected_customer
st.session_state["customer"]      = customer
st.session_state["schema"]        = customer["schema"]

# ── Main content (rendered by pages when navigated, or show landing here) ───
st.markdown(f"## {selected_customer} — Account performance")

go_live = customer.get("go_live")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"**Go-live:** {go_live or '—'}")
with col2:
    st.markdown(f"**CSM:** {customer.get('csm') or '—'}")
with col3:
    st.markdown(f"**License:** {customer.get('license') or '—'}")

st.info("👈 Use the sidebar to select a customer. Navigate with the pages below.")

st.markdown("""
### Dashboard pages
| Page | What it shows |
|---|---|
| 📋 Account Snapshot | Health score, volume, escalation & sentiment at a glance |
| 🛡️ Escalation Intelligence | LTE predictions, escalation rate vs benchmark, prevented escalations |
| 😊 Sentiment | Sentiment score trend, need-attention score, alerts consumption |
| 🔀 Routing & Efficiency | ICA auto/manual split, reassignment rate, FRT by priority, workload |
| 📈 ROI Summary | Renewal-ready one-pager anchored to go-live baseline |
| ⚙️ Query Explorer | Browse & run any query from the registry directly |
""")
