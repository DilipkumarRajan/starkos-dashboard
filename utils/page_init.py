"""
utils/page_init.py
Call init_page() at the top of every page.
Handles the case where someone navigates directly to a page
without going through Home.py first (session_state would be empty).
"""

import streamlit as st
from utils.customers import CUSTOMERS


def init_page(title: str):
    """
    Ensures session state is populated and returns (schema, customer_name, customer_dict).
    If session state is missing (direct page navigation), bootstraps from the sidebar.
    """
    # ── Sidebar customer picker — always visible on every page ───────────────
    with st.sidebar:
        st.markdown("## 📊 SupportLogic")
        st.divider()

        selected = st.selectbox(
            "Customer",
            options=list(CUSTOMERS.keys()),
            index=list(CUSTOMERS.keys()).index(
                st.session_state.get("customer_name", list(CUSTOMERS.keys())[0])
            ),
            key="sidebar_customer_select",
        )

        customer = CUSTOMERS[selected]

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
        st.caption("Data refreshes every hour")

        if st.button("🔄 Clear cache & refresh", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

    # ── Sync session state ────────────────────────────────────────────────────
    st.session_state["customer_name"] = selected
    st.session_state["customer"]      = customer
    st.session_state["schema"]        = customer["schema"]

    # ── Page header ───────────────────────────────────────────────────────────
    st.caption(
        f"Customer: **{selected}** · Schema: `{customer['schema']}`"
        + (f" · Go-live: {customer['go_live']}" if customer.get("go_live") else "")
    )

    return customer["schema"], selected, customer
