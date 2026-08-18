# ════════════════════════════════════════════════════════════════════════════
# TAB 8 — GCP LOG TROUBLESHOOTER
# Source: Data Pipeline Runbook (Confluence 1778089987)
#         ACA Logs & Debugging Guide (Confluence 2165932051)
#         Debugging ACA + ML Prediction (Confluence 1512767532)
# ════════════════════════════════════════════════════════════════════════════

elif tab == 8:
    import urllib.parse
    from datetime import datetime, timedelta, timezone

    GCP_PROJECT = "supportlogic"

    # ── Customer hostname mapping ─────────────────────────────────────────────
    HOSTNAME_OVERRIDES = {}
    hostname = HOSTNAME_OVERRIDES.get(
        customer_name,
        customer.get("gcp_hostname", customer_name.lower().replace(" ", ""))
    )

    # ── Container catalogue from Data Pipeline Runbook ────────────────────────
    # layer: "backend" = customer-backend server
    #        "frontend" = customer UI server
    #        "shared"   = idt-backend (shared across all customers)
    #        "ml"       = ML service (shared)
    CONTAINERS = {
        # ── CRM Ingestion ──────────────────────────────────────────────────
        "crm_importer": {
            "layer": "backend",
            "desc": "Fetches CRM data → uds_case, uds_comment, uds_user, uds_account, sl_case_history",
            "pipeline_stage": "CRM ingestion",
            "symptom": "Missing cases, comments, or users in SL UI",
        },
        # ── Data processing pipeline ───────────────────────────────────────
        "comment_metrics": {
            "layer": "backend",
            "desc": "uds_comment → sl_comment_metric_2020_02",
            "pipeline_stage": "Metrics",
            "symptom": "Missing comment metrics",
        },
        "case_progress": {
            "layer": "backend",
            "desc": "sl_case_history → sl_case_progress",
            "pipeline_stage": "Case progress",
            "symptom": "Incorrect case progress data",
        },
        "user_metrics": {
            "layer": "backend",
            "desc": "uds_case/comment/user → sl_user_metrics",
            "pipeline_stage": "User metrics",
            "symptom": "Incorrect agent metrics",
        },
        "user_stitcher": {
            "layer": "backend",
            "desc": "uds_user + sl_user_metrics → user",
            "pipeline_stage": "User stitching",
            "symptom": "User data missing or stale",
        },
        # ── ML / NLP pipeline ──────────────────────────────────────────────
        "email_predictor": {
            "layer": "ml",
            "desc": "uds_comment → span_doc_email (ML)",
            "pipeline_stage": "NLP — email classification",
            "symptom": "No sentiment signals, missing spans",
        },
        "diverse_v3": {
            "layer": "ml",
            "desc": "span_doc_email → span_doc_diverse (ML)",
            "pipeline_stage": "NLP — diverse signals",
            "symptom": "Missing sentiment categories",
        },
        "flex_ner": {
            "layer": "ml",
            "desc": "ontology + uds_case + span_doc_email → span_doc_ner (ML)",
            "pipeline_stage": "NLP — named entity recognition",
            "symptom": "Missing entity/keyword detection",
        },
        "span_stitcher": {
            "layer": "backend",
            "desc": "span_doc_diverse + email + sl_feedback → span_doc_consolidated",
            "pipeline_stage": "Span stitching",
            "symptom": "Sentiments missing or very few in dashboard",
        },
        "impulse_scorer": {
            "layer": "backend",
            "desc": "span_doc_consolidated → sl_impulse_score_by_channel_2020_02",
            "pipeline_stage": "Sentiment scoring",
            "symptom": "No sentiment scores visible",
        },
        "customer_scorer": {
            "layer": "backend",
            "desc": "sl_impulse_score_summary → sl_customer_score",
            "pipeline_stage": "Account scoring",
            "symptom": "Account health scores stale",
        },
        "feedback_sweeper": {
            "layer": "backend",
            "desc": "sl_feedback (RDB) → sl_feedback (PIPE SQL)",
            "pipeline_stage": "Feedback sync",
            "symptom": "Agent signal feedback not reflected",
        },
        "escalation_predictor": {
            "layer": "ml",
            "desc": "ML service for escalation prediction",
            "pipeline_stage": "LTE / Escalation prediction",
            "symptom": "LTE predictions not updating",
        },
        "escalation_prediction_summarizer": {
            "layer": "backend",
            "desc": "escalation_predictions → escalation_predictions_summary",
            "pipeline_stage": "Escalation summarization",
            "symptom": "Escalation summary stale",
        },
        # ── Case summary & alerting ────────────────────────────────────────
        "account_stitcher": {
            "layer": "backend",
            "desc": "uds_account + sl_customer_score → account",
            "pipeline_stage": "Account stitching",
            "symptom": "Account data stale or missing",
        },
        "entity_stitcher": {
            "layer": "backend",
            "desc": "span_doc_ner → entity_row, entity_summary",
            "pipeline_stage": "Entity stitching",
            "symptom": "Entities/keywords missing",
        },
        "case_summarizer": {
            "layer": "backend",
            "desc": "uds_case + all metrics → case_summary",
            "pipeline_stage": "Case summarization",
            "symptom": "Case summary data stale",
        },
        "case_summary_alerter": {
            "layer": "backend",
            "desc": "case_summary → alert_events",
            "pipeline_stage": "Alert triggering",
            "symptom": "Alerts not firing on case changes",
        },
        "timed_alerter": {
            "layer": "backend",
            "desc": "case_summary → alert_events (time-based)",
            "pipeline_stage": "Timed alerts",
            "symptom": "Time-based alerts not firing",
        },
        "alert_router": {
            "layer": "backend",
            "desc": "alert_events → alerts (routes to Slack/email/Teams)",
            "pipeline_stage": "Alert routing",
            "symptom": "Alerts fired but not delivered",
        },
        # ── Broker services (PIPE → UI RDB) ───────────────────────────────
        "case_summary_broker": {
            "layer": "frontend",
            "desc": "case_summary (PIPE) → case_summary (UI RDB). Missing cases in SL UI.",
            "pipeline_stage": "Broker — cases",
            "symptom": "Cases missing or stale in SL UI",
        },
        "unified_span_broker": {
            "layer": "frontend",
            "desc": "uds_comment + impulse_score → unified_spans (UI RDB)",
            "pipeline_stage": "Broker — spans/sentiments",
            "symptom": "Sentiments not showing in case view",
        },
        "account_broker": {
            "layer": "frontend",
            "desc": "account (PIPE) → companies (UI RDB)",
            "pipeline_stage": "Broker — accounts",
            "symptom": "Account data missing in SL UI",
        },
        "ontology_broker": {
            "layer": "frontend",
            "desc": "ontology_v4 → sl_ontology (UI RDB)",
            "pipeline_stage": "Broker — ontology",
            "symptom": "Signal categories not loading",
        },
        "user_broker": {
            "layer": "frontend",
            "desc": "user (PIPE) → users (UI RDB)",
            "pipeline_stage": "Broker — users",
            "symptom": "User/agent data stale in UI",
        },
        # ── Search / Elastic ───────────────────────────────────────────────
        "elastic_feeder": {
            "layer": "backend",
            "desc": "uds_case/comment/account/user → Elasticsearch",
            "pipeline_stage": "Search indexing",
            "symptom": "Search results missing or returning no results",
        },
        # ── ICA / Assignment ───────────────────────────────────────────────
        "aca_service": {
            "layer": "shared",
            "desc": "ICA daemon — auto-assignment of cases to agents",
            "pipeline_stage": "Case assignment (ICA)",
            "symptom": "Cases not being auto-assigned",
        },
        # ── UI / iframe ────────────────────────────────────────────────────
        "iframe_v2_ui": {
            "layer": "frontend",
            "desc": "SL embedded iframe widget served to CRM",
            "pipeline_stage": "UI",
            "symptom": "iframe not loading, widget errors, 500s",
        },
        # ── Writeback / UWF ────────────────────────────────────────────────
        "webhook_event_propagation_daemon": {
            "layer": "shared",
            "desc": "UWF — writes SL signals back to CRM (sentiment, health score, escalation flag)",
            "pipeline_stage": "CRM writeback (UWF)",
            "symptom": "CRM fields not updating (health score, sentiment etc)",
        },
        "dbss": {
            "layer": "frontend",
            "desc": "Database service — serves data to SL UI",
            "pipeline_stage": "UI data service",
            "symptom": "UI data not loading, API errors",
        },
        "backend_init": {
            "layer": "backend",
            "desc": "Bootstrap container — used to run static jobs and ack pubsub batches",
            "pipeline_stage": "Ops / maintenance",
            "symptom": "Used for manual interventions only",
        },
    }

    LAYER_COLOR = {
        "backend":  ("#1a3a2a", "#1D9E75", "🟢 Backend"),
        "frontend": ("#1a1a3a", "#534AB7", "🟣 Frontend"),
        "shared":   ("#3a2e10", "#BA7517", "🟡 Shared"),
        "ml":       ("#2a1a3a", "#E24B4A", "🔴 ML Service"),
    }

    # ── Sentiment pipeline ordered ─────────────────────────────────────────
    SENTIMENT_PIPELINE = [
        "email_predictor", "diverse_v3", "flex_ner",
        "span_stitcher", "impulse_scorer", "unified_span_broker"
    ]

    st.subheader("🔍 GCP Log Troubleshooter")
    st.caption(
        f"Customer: **{customer_name}** · Hostname: `{hostname}` · "
        f"Project: `{GCP_PROJECT}` · "
        f"Source: [Data Pipeline Runbook](https://supportlogic.atlassian.net/wiki/spaces/ENG/pages/1778089987)"
    )
    st.info(
        "Click **Open in Log Explorer** to open GCP Logs Explorer pre-filtered in your browser. "
        "Must be signed in with your SupportLogic Google account.",
        icon="ℹ️"
    )

    # ── Controls ──────────────────────────────────────────────────────────────
    col_t1, col_t2, col_t3, col_t4 = st.columns([1.2, 1, 1.2, 1.6])
    time_window = col_t1.selectbox("Time window",
        ["Last 1 hour", "Last 6 hours", "Last 24 hours", "Last 3 days", "Last 7 days"], index=1)
    severity = col_t2.selectbox("Min severity",
        ["DEFAULT", "INFO", "WARNING", "ERROR", "CRITICAL"], index=2)
    case_id = col_t3.text_input("Case ID", placeholder="e.g. 500Vy00000vUZ7fIAG")
    keyword = col_t4.text_input("Keyword / message filter", placeholder="e.g. CASE_SKIPPED or error text")

    window_map = {
        "Last 1 hour":   timedelta(hours=1),
        "Last 6 hours":  timedelta(hours=6),
        "Last 24 hours": timedelta(hours=24),
        "Last 3 days":   timedelta(days=3),
        "Last 7 days":   timedelta(days=7),
    }
    duration_map = {
        "Last 1 hour":   "PT1H",
        "Last 6 hours":  "PT6H",
        "Last 24 hours": "PT24H",
        "Last 3 days":   "P3D",
        "Last 7 days":   "P7D",
    }
    delta = window_map[time_window]
    now   = datetime.now(timezone.utc)
    start = now - delta

    def build_url(filter_lines: list) -> str:
        parts = list(filter_lines)
        if severity != "DEFAULT":
            parts.append(f"severity>={severity}")
        if case_id.strip():
            parts.append(f'SEARCH("{case_id.strip()}")')
        if keyword.strip():
            parts.append(f'jsonPayload.MESSAGE=~"{keyword.strip()}"')
        query   = "\n".join(parts)
        encoded = urllib.parse.quote(query, safe="")
        return (f"https://console.cloud.google.com/logs/query"
                f";query={encoded}"
                f";duration={duration_map[time_window]}"
                f"?project={GCP_PROJECT}")

    def filter_preview(filter_lines: list) -> str:
        parts = list(filter_lines)
        if severity != "DEFAULT":
            parts.append(f"severity>={severity}")
        if case_id.strip():
            parts.append(f'SEARCH("{case_id.strip()}")')
        if keyword.strip():
            parts.append(f'jsonPayload.MESSAGE=~"{keyword.strip()}"')
        return "\n".join(parts)

    def container_hostname(c_name: str) -> str:
        """Return the right _HOSTNAME pattern for a container."""
        layer = CONTAINERS.get(c_name, {}).get("layer", "backend")
        if layer == "shared" or layer == "ml":
            return "idt-backend"
        if layer == "backend":
            return f"{hostname}-backend"
        # frontend containers use just hostname (e.g. "fourth")
        return hostname

    def render_container_card(c_name: str, extra_filters: list = None):
        info = CONTAINERS.get(c_name, {})
        layer = info.get("layer", "backend")
        bg, border, layer_label = LAYER_COLOR.get(layer, LAYER_COLOR["backend"])
        h = container_hostname(c_name)
        base = [
            f'jsonPayload.CONTAINER_NAME="{c_name}"',
            f'jsonPayload._HOSTNAME=~"{h}"',
        ]
        if extra_filters:
            base.extend(extra_filters)
        url = build_url(base)

        col_info, col_btn = st.columns([3, 1])
        with col_info:
            st.markdown(
                f"<div style='background:{bg};border:0.5px solid {border};"
                f"border-radius:8px;padding:10px 14px;margin-bottom:4px'>"
                f"<div style='font-size:13px;font-weight:500;color:#e6edf3'>"
                f"<code style='background:transparent;color:{border}'>{c_name}</code>"
                f"  <span style='font-size:10px;color:#8b949e;margin-left:6px'>{layer_label}</span></div>"
                f"<div style='font-size:11px;color:#8b949e;margin-top:3px'>{info.get('desc','')}</div>"
                f"<div style='font-size:11px;color:#BA7517;margin-top:2px'>⚠ {info.get('symptom','')}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            with st.expander("Show filter", expanded=False):
                st.code(filter_preview(base), language="text")
        with col_btn:
            st.link_button("Open in Log Explorer →", url, use_container_width=True)

    st.divider()

    # ── Legend ────────────────────────────────────────────────────────────────
    st.markdown("**Container layer legend:**")
    leg_cols = st.columns(4)
    for i, (layer, (bg, border, label)) in enumerate(LAYER_COLOR.items()):
        leg_cols[i].markdown(
            f"<div style='background:{bg};border:0.5px solid {border};border-radius:6px;"
            f"padding:6px 10px;font-size:12px;color:#e6edf3'>{label}</div>",
            unsafe_allow_html=True
        )
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Quick issue templates ─────────────────────────────────────────────────
    st.subheader("🚨 Quick issue templates")
    st.caption("Start here — each template maps to a known symptom")

    ISSUE_TEMPLATES = [
        {
            "title": "Cases / comments missing in SL UI",
            "desc": "Check CRM ingestion → case broker → search indexing chain",
            "containers": ["crm_importer", "case_summary_broker", "elastic_feeder"],
        },
        {
            "title": "Sentiments missing or very few",
            "desc": "Full NLP pipeline: email_predictor → diverse_v3 → flex_ner → span_stitcher → impulse_scorer → unified_span_broker",
            "containers": SENTIMENT_PIPELINE,
        },
        {
            "title": "Cases not auto-assigning (ICA)",
            "desc": "ICA daemon on shared backend — check for CASE_SKIPPED, ML failures, no agents in queue",
            "containers": ["aca_service"],
            "extra": {'aca_service': ['jsonPayload._HOSTNAME="idt-backend"']},
        },
        {
            "title": "Alerts not firing or not delivered",
            "desc": "Alert generation + routing chain",
            "containers": ["case_summary_alerter", "timed_alerter", "alert_router"],
        },
        {
            "title": "CRM writeback not working (UWF)",
            "desc": "Webhook propagation daemon — checks health score, sentiment, escalation flag writebacks",
            "containers": ["webhook_event_propagation_daemon"],
            "extra": {"webhook_event_propagation_daemon": [f'jsonPayload._HOSTNAME=~"{hostname}-backend"']},
        },
        {
            "title": "iframe widget errors / 500s",
            "desc": "Frontend iframe service for this customer",
            "containers": ["iframe_v2_ui", "dbss"],
        },
        {
            "title": "LTE / escalation predictions stale",
            "desc": "ML prediction service and summarizer",
            "containers": ["escalation_predictor", "escalation_prediction_summarizer"],
        },
        {
            "title": "Account / user data stale in UI",
            "desc": "Account and user stitching + broker services",
            "containers": ["account_stitcher", "user_stitcher", "account_broker", "user_broker"],
        },
    ]

    for tmpl in ISSUE_TEMPLATES:
        with st.expander(f"**{tmpl['title']}** — {tmpl['desc']}", expanded=False):
            extra_map = tmpl.get("extra", {})
            for c_name in tmpl["containers"]:
                info = CONTAINERS.get(c_name, {})
                layer = info.get("layer", "backend")
                h = extra_map.get(c_name, [f'jsonPayload._HOSTNAME=~"{container_hostname(c_name)}"'])
                base = [f'jsonPayload.CONTAINER_NAME="{c_name}"'] + h
                url  = build_url(base)
                _, border, layer_label = LAYER_COLOR.get(layer, LAYER_COLOR["backend"])
                col_i, col_b = st.columns([3, 1])
                with col_i:
                    st.markdown(
                        f"<code style='color:{border}'>{c_name}</code>"
                        f" <span style='font-size:10px;color:#8b949e'>{layer_label} · {info.get('pipeline_stage','')}</span>"
                        f"<br><span style='font-size:11px;color:#BA7517'>⚠ {info.get('symptom','')}</span>",
                        unsafe_allow_html=True,
                    )
                with col_b:
                    st.link_button("Open →", url, use_container_width=True)
                st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)

    st.divider()

    # ── All containers by layer ───────────────────────────────────────────────
    st.subheader("📦 All containers — browse by layer")

    layer_tabs = st.tabs(["🟢 Backend", "🟣 Frontend", "🟡 Shared", "🔴 ML Services"])
    layer_map  = {"backend": 0, "frontend": 1, "shared": 2, "ml": 3}

    for c_name, info in CONTAINERS.items():
        layer = info.get("layer", "backend")
        with layer_tabs[layer_map[layer]]:
            render_container_card(c_name)

    st.divider()

    # ── Custom query builder ──────────────────────────────────────────────────
    st.subheader("🔧 Custom query builder")
    col_c1, col_c2 = st.columns(2)
    custom_container = col_c1.text_input("CONTAINER_NAME", placeholder="e.g. span_stitcher")
    custom_hostname  = col_c2.text_input("_HOSTNAME", value=hostname)
    custom_message   = st.text_input("MESSAGE contains", placeholder="e.g. error or CASE_SKIPPED")
    custom_extra     = st.text_area("Additional filter lines (one per line)",
                                     placeholder='jsonPayload.MESSAGE=~"my_pattern"', height=80)

    if st.button("🔗 Build & open", type="primary"):
        lines = []
        if custom_container:
            lines.append(f'jsonPayload.CONTAINER_NAME="{custom_container}"')
        if custom_hostname:
            lines.append(f'jsonPayload._HOSTNAME=~"{custom_hostname}"')
        if custom_message:
            lines.append(f'jsonPayload.MESSAGE=~"{custom_message}"')
        if custom_extra.strip():
            lines.extend([l.strip() for l in custom_extra.strip().split("\n") if l.strip()])
        url = build_url(lines)
        st.code(filter_preview(lines), language="text")
        st.link_button("Open in Log Explorer →", url, type="primary")

    st.divider()
    st.caption(
        f"Hostname: `{hostname}` · Override via `gcp_hostname` in `utils/customers.py` · "
        f"[Data Pipeline Runbook](https://supportlogic.atlassian.net/wiki/spaces/ENG/pages/1778089987) · "
        f"[ACA Debugging Guide](https://supportlogic.atlassian.net/wiki/spaces/ENG/pages/2165932051)"
    )
