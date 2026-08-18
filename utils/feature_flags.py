"""
utils/feature_flags.py
Derives which SL features are genuinely active from live data.

ICA detection logic:
  - ICA_AUTO_ASSIGNMENT events with 0 unique cases = scheduler heartbeats, NOT real routing
  - Real ICA deployment = total_auto_cases > 0 (actual cases assigned to agents via ICA)
"""
import pandas as pd


def detect_features(data: dict) -> list[dict]:

    def col_sum(df, col):
        if df is None or df.empty or col not in df.columns:
            return 0
        return int(df[col].sum())

    # ── ICA: only count real case assignments, not heartbeat events ──────────
    df_ica       = data.get("ica_total_lifetime")
    ica_auto_cases   = col_sum(df_ica, "total_auto_cases")   # unique cases auto-routed
    ica_manual_cases = col_sum(df_ica, "total_manual_cases") # unique cases manually assigned
    ica_active   = ica_auto_cases > 0                         # only True if cases were actually routed

    # ── Other features ────────────────────────────────────────────────────────
    lte_pred     = col_sum(data.get("lte_accuracy_monthly"),      "cases_predicted")
    sent_cases   = col_sum(data.get("sentiment_monthly"),         "cases_scored")
    alerts_total = col_sum(data.get("alerts_monthly"),            "total_alerts")
    summ_total   = col_sum(data.get("ai_summaries_total"),        "total")
    act_total    = col_sum(data.get("platform_actions_summary"),  "total_actions")
    rev_total    = col_sum(data.get("escalation_reviews_monthly"),"cnt")

    df_health    = data.get("account_health_monthly")
    health_active = df_health is not None and not df_health.empty

    return [
        {
            "name":   "Routing Agent (ICA)",
            "status": "active" if ica_active else "not_deployed",
            "evidence": (
                f"{ica_auto_cases:,} cases auto-routed, {ica_manual_cases:,} manual assignments"
                if ica_active else
                "No real case assignments found — scheduler events exist but ICA is not routing cases"
            ),
        },
        {
            "name":   "Escalation Agent (LTE)",
            "status": "active" if lte_pred > 0 else "not_deployed",
            "evidence": f"{lte_pred:,} predictions made" if lte_pred > 0 else "No LTE prediction events found",
        },
        {
            "name":   "Sentiment Agent",
            "status": "active" if sent_cases > 0 else "not_deployed",
            "evidence": f"{sent_cases:,} cases scored" if sent_cases > 0 else "No sentiment scores found",
        },
        {
            "name":   "Account Health Agent",
            "status": "active" if health_active else "not_deployed",
            "evidence": "ML health scores generated monthly" if health_active else "No health scores found",
        },
        {
            "name":   "Alerts",
            "status": "active" if alerts_total > 0 else "not_deployed",
            "evidence": f"{alerts_total:,} alerts fired" if alerts_total > 0 else "No alert events found",
        },
        {
            "name":   "Summarization Agent",
            "status": "active" if summ_total > 0 else "not_deployed",
            "evidence": f"{summ_total:,} summaries generated" if summ_total > 0 else "No summaries found",
        },
        {
            "name":   "Escalation Swarming",
            "status": "active" if rev_total > 0 else "not_deployed",
            "evidence": f"{rev_total:,} escalation reviews" if rev_total > 0 else "No escalation review activity found",
        },
        {
            "name":   "Platform Engagement (Agent Actions)",
            "status": "active" if act_total > 0 else "not_deployed",
            "evidence": f"{act_total:,} agent actions on SL signals" if act_total > 0 else "No agent action events found",
        },
        {
            "name":   "Elevate / QA Agent",
            "status": "not_licensed",
            "evidence": "No ticket review data in schema",
        },
        {
            "name":   "ResolveSX / Knowledge Agent",
            "status": "not_licensed",
            "evidence": "Not present in schema",
        },
    ]
