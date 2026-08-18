QUERIES = {


    "engagement_metrics": """
        SELECT
            -- Interactions (comments scored by NLP)
            (SELECT COUNT(*)
             FROM PIPE_DATABASE.<SCHEMA>.sl_impulse_score_by_channel_2020_02
             WHERE _sl_created_at >= DATE_TRUNC('YEAR', CURRENT_DATE())
            ) AS annual_interactions,

            -- Alerts (email + teams + slack combined)
            (SELECT COUNT(*)
             FROM PIPE_DATABASE.<SCHEMA>.alerts
             WHERE s_created_at >= DATE_TRUNC('YEAR', CURRENT_DATE())
            ) AS annual_alerts,

            -- ICA auto-assignments (last month × 12 for projection)
            (SELECT COUNT(DISTINCT object_id_reference) * 12
             FROM PIPE_DATABASE.<SCHEMA>.std_event_log
             WHERE event_source = 'ICA_AUTO_ASSIGNMENT'
               AND object_id_reference IS NOT NULL
               AND s_created_at >= DATE_TRUNC('MONTH', DATEADD(MONTH,-1,CURRENT_DATE()))
               AND s_created_at < DATE_TRUNC('MONTH', CURRENT_DATE())
            ) AS projected_annual_ica,

            -- Auto QA
            (SELECT COUNT(*)
             FROM PIPE_DATABASE.<SCHEMA>.std_ticket_review
             WHERE s_created_at >= DATE_TRUNC('YEAR', CURRENT_DATE())
               AND _fivetran_deleted = FALSE
            ) AS annual_auto_qa,

            -- Resolve/xFind API queries
            (SELECT COUNT(*)
             FROM PIPE_DATABASE.<SCHEMA>.std_object_action
             WHERE (action_type ILIKE '%resolve%'
                    OR action_type ILIKE '%xfind%'
                    OR action_type ILIKE '%search%'
                    OR action_type ILIKE '%knowledge%')
               AND s_created_at >= DATE_TRUNC('YEAR', CURRENT_DATE())
            ) AS annual_resolve_queries,

            -- AI Summaries (case + account + cohort + escalation)
            (SELECT COUNT(*)
             FROM PIPE_DATABASE.<SCHEMA>.std_generated_summary
             WHERE s_created_at >= DATE_TRUNC('YEAR', CURRENT_DATE())
            ) AS annual_summaries,

            -- Signals extracted (unique spans/signals from NLP)
            (SELECT COUNT(*)
             FROM PIPE_DATABASE.<SCHEMA>.sl_impulse_score_by_channel_2020_02
             WHERE _sl_created_at >= DATE_TRUNC('YEAR', CURRENT_DATE())
            ) AS annual_signals
    """,
    "case_volume_ytd": """
        SELECT
            COUNT(*)                                                AS ytd_cases,
            COUNT(DISTINCT DATE_TRUNC('MONTH', sl_created_at))     AS months_with_data,
            ROUND(COUNT(*) /
                NULLIF(COUNT(DISTINCT DATE_TRUNC('MONTH', sl_created_at)), 0), 0)
                                                                    AS avg_monthly,
            SUM(CASE WHEN DATE_TRUNC('MONTH', sl_created_at)
                          = DATE_TRUNC('MONTH', CURRENT_DATE())
                     THEN 1 ELSE 0 END)                             AS current_month_cases,
            SUM(CASE WHEN DATE_TRUNC('MONTH', sl_created_at)
                          = DATE_TRUNC('MONTH', DATEADD(MONTH,-1,CURRENT_DATE()))
                     THEN 1 ELSE 0 END)                             AS prev_month_cases
        FROM PIPE_DATABASE.<SCHEMA>.case_summary
        WHERE sl_created_at >= DATE_TRUNC('YEAR', CURRENT_DATE())
          AND sl_is_bot = FALSE
          AND is_deleted = FALSE
    """,

    "case_volume_monthly": """
        SELECT
            TO_CHAR(DATE_TRUNC('MONTH', sl_created_at), 'YYYY-MM') AS month,
            COUNT(*)                                                 AS total_cases,
            SUM(CASE WHEN sl_priority IN ('P1','P1-Critcal')
                     THEN 1 ELSE 0 END)                             AS p1_cases,
            SUM(CASE WHEN sl_priority IN ('P2','P2- High')
                     THEN 1 ELSE 0 END)                             AS p2_cases
        FROM PIPE_DATABASE.<SCHEMA>.case_summary
        WHERE sl_created_at >= DATE_TRUNC('YEAR', CURRENT_DATE())
          AND sl_is_bot = FALSE
          AND is_deleted = FALSE
        GROUP BY 1 ORDER BY 1
    """,

    "frt_monthly": """
        SELECT TO_VARCHAR(DATE_TRUNC('MONTH', sl_created_at), 'YYYY-MM') AS month,
            ROUND(AVG(sl_first_response_time_ms) / 3600000.0, 2) AS avg_frt_hours,
            COUNT(*) AS total_cases
        FROM PIPE_DATABASE.<SCHEMA>.case_summary
        WHERE sl_created_at >= '2025-06-01'
          AND sl_is_bot = FALSE
          AND is_deleted = FALSE AND sl_is_bot = FALSE
        GROUP BY 1 ORDER BY 1
    """,
    "escalation_monthly": """
        WITH t AS (
            SELECT DATE_TRUNC('MONTH', sl_created_at) AS md,
                COUNT(*) AS total_cases,
                SUM(CASE WHEN sl_escalated_at_first IS NOT NULL THEN 1 ELSE 0 END) AS escalated_cases
            FROM PIPE_DATABASE.<SCHEMA>.case_summary
            WHERE sl_created_at >= '2025-06-01'
          AND sl_is_bot = FALSE
          AND is_deleted = FALSE
              AND sl_created_at < CURRENT_DATE()
              AND sl_is_bot = FALSE
              AND is_deleted = FALSE
            GROUP BY 1
        )
        SELECT TO_CHAR(md,'YYYY-MM') AS month, total_cases, escalated_cases,
            ROUND(100.0 * escalated_cases / NULLIF(total_cases,0), 2) AS escalation_pct
        FROM t ORDER BY md
    """,
    "resolution_monthly": """
        WITH t AS (
            SELECT DATE_TRUNC('MONTH', sl_created_at) AS md,
                COUNT(DISTINCT sl_case_id) AS total_cases,
                ROUND(AVG(sl_open_time_ms) / 86400000, 2) AS avg_resolution_days
            FROM PIPE_DATABASE.<SCHEMA>.case_summary
            WHERE sl_created_at >= DATEADD(MONTH,-6,DATE_TRUNC('MONTH',CURRENT_DATE()))
              AND sl_open_time_ms IS NOT NULL
              AND sl_is_bot = FALSE
              AND is_deleted = FALSE
            GROUP BY 1
        )
        SELECT TO_CHAR(md,'YYYY-MM') AS month, total_cases, avg_resolution_days FROM t ORDER BY md
    """,
    "cases_per_agent_weekly": """
        SELECT DATE_TRUNC('WEEK', sl_created_at) AS week_start,
            ROUND(COUNT(*) / NULLIF(COUNT(DISTINCT sl_assignee_id),0), 0) AS cases_per_agent,
            COUNT(*) AS total_cases,
            COUNT(DISTINCT sl_assignee_id) AS active_agents
        FROM PIPE_DATABASE.<SCHEMA>.case_summary
        WHERE sl_created_at >= DATEADD(WEEK,-12,CURRENT_DATE()) AND sl_is_bot = FALSE
        GROUP BY 1 ORDER BY 1
    """,
    "reassignment_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', sl_created_at),'YYYY-MM') AS month,
            COUNT(*) AS total_cases,
            SUM(CASE WHEN sl_assignee_id_count_users_only > 1 THEN 1 ELSE 0 END) AS reassigned_cases,
            ROUND(100.0 * SUM(CASE WHEN sl_assignee_id_count_users_only > 1 THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*),0), 1) AS reassignment_pct
        FROM PIPE_DATABASE.<SCHEMA>.case_summary
        WHERE sl_created_at >= '2025-06-01'
          AND sl_is_bot = FALSE
          AND is_deleted = FALSE AND sl_is_bot = FALSE
        GROUP BY 1 ORDER BY 1
    """,
    "frt_by_priority": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', sl_created_at),'YYYY-MM') AS month,
            CASE
                WHEN sl_priority IN ('P1','P1-Critcal')  THEN 'P1 Critical'
                WHEN sl_priority IN ('P2','P2- High')    THEN 'P2 High'
                WHEN sl_priority ILIKE '%P3%'            THEN 'P3 Medium'
                ELSE 'P4/Other'
            END AS priority_tier,
            ROUND(AVG(sl_first_response_time_ms)/3600000.0, 2) AS avg_frt_hours,
            COUNT(*) AS case_count
        FROM PIPE_DATABASE.<SCHEMA>.case_summary
        WHERE sl_created_at >= '2025-12-01' AND sl_is_bot = FALSE
        GROUP BY 1,2 ORDER BY 1,2
    """,
    "priority_mix_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', sl_created_at),'YYYY-MM') AS month,
            COUNT(*) AS total_cases,
            SUM(CASE WHEN sl_priority IN ('P1','P1-Critcal','P2','P2- High') THEN 1 ELSE 0 END) AS critical_high,
            ROUND(100.0 * SUM(CASE WHEN sl_priority IN ('P1','P1-Critcal','P2','P2- High') THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*),0), 2) AS critical_high_pct
        FROM PIPE_DATABASE.<SCHEMA>.case_summary
        WHERE sl_created_at >= '2025-06-01'
          AND sl_is_bot = FALSE
          AND is_deleted = FALSE
        GROUP BY 1 ORDER BY 1
    """,
    "ica_events_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', event_time),'YYYY-MM') AS month,
            SUM(CASE WHEN event_source = 'ICA_AUTO_ASSIGNMENT' THEN 1 ELSE 0 END) AS auto_events,
            COUNT(DISTINCT CASE WHEN event_source = 'ICA_AUTO_ASSIGNMENT'
                AND object_id_reference IS NOT NULL AND object_id_reference != ''
                THEN object_id_reference END) AS auto_cases,
            COUNT(DISTINCT CASE WHEN event_source = 'ICA_MANUAL_ASSIGNMENT'
                AND object_id_reference IS NOT NULL AND object_id_reference != ''
                THEN object_id_reference END) AS manual_cases
        FROM PIPE_DATABASE.<SCHEMA>.std_event_log
        WHERE event_time >= '2025-06-01'
          AND event_source IN ('ICA_AUTO_ASSIGNMENT','ICA_MANUAL_ASSIGNMENT')
        GROUP BY 1 ORDER BY 1
    """,
    "ica_total_lifetime": """
        SELECT
            COUNT(DISTINCT CASE WHEN event_source = 'ICA_AUTO_ASSIGNMENT'
                AND object_id_reference IS NOT NULL AND object_id_reference != ''
                THEN object_id_reference END) AS total_auto_cases,
            COUNT(DISTINCT CASE WHEN event_source = 'ICA_MANUAL_ASSIGNMENT'
                AND object_id_reference IS NOT NULL AND object_id_reference != ''
                THEN object_id_reference END) AS total_manual_cases,
            SUM(CASE WHEN event_source = 'ICA_AUTO_ASSIGNMENT' THEN 1 ELSE 0 END) AS total_auto_events,
            SUM(CASE WHEN event_source = 'ICA_MANUAL_ASSIGNMENT' THEN 1 ELSE 0 END) AS total_manual_events
        FROM PIPE_DATABASE.<SCHEMA>.std_event_log
        WHERE event_source IN ('ICA_AUTO_ASSIGNMENT','ICA_MANUAL_ASSIGNMENT')
    """,
    "alerts_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', s_created_at),'YYYY-MM') AS month,
            COUNT(DISTINCT sl_case_id) AS alert_cases,
            COUNT(*) AS total_alerts
        FROM PIPE_DATABASE.<SCHEMA>.alerts
        WHERE s_created_at >= '2025-06-01' AND s_created_at < CURRENT_DATE()
        GROUP BY 1 ORDER BY 1
    """,
    "lte_accuracy_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', ep.ts),'YYYY-MM') AS month,
            COUNT(DISTINCT ep.sl_case_id) AS cases_predicted,
            COUNT(DISTINCT CASE WHEN cs.sl_escalated_at_first IS NOT NULL
                THEN ep.sl_case_id END) AS actually_escalated,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN cs.sl_escalated_at_first IS NOT NULL
                THEN ep.sl_case_id END)
                / NULLIF(COUNT(DISTINCT ep.sl_case_id),0), 1) AS hit_rate_pct
        FROM PIPE_DATABASE.<SCHEMA>.escalation_predictions ep
        JOIN PIPE_DATABASE.<SCHEMA>.case_summary cs ON ep.sl_case_id = cs.sl_case_id
        WHERE ep.sl_is_predicted_to_escalate = TRUE AND ep.ts >= '2025-06-01'
        GROUP BY 1 ORDER BY 1
    """,
    "sentiment_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', _sl_created_at),'YYYY-MM') AS month,
            ROUND(AVG(sl_sentiment_score),1) AS avg_sentiment,
            ROUND(AVG(sl_need_attention_score),1) AS avg_need_attention,
            COUNT(DISTINCT sl_case_id) AS cases_scored
        FROM PIPE_DATABASE.<SCHEMA>.sl_impulse_score_by_channel_2020_02
        WHERE _sl_created_at >= '2025-06-01'
        GROUP BY 1 ORDER BY 1
    """,
    "account_health_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', s_created_at),'YYYY-MM') AS month,
            ROUND(AVG(score_value),1) AS avg_health_score,
            COUNT(*) AS score_events
        FROM PIPE_DATABASE.<SCHEMA>.ml_prediction
        WHERE ml_prediction_type = 'ACCOUNT_HEALTH_SCORE' AND s_created_at >= '2024-01-01'
        GROUP BY 1 ORDER BY 1
    """,
    "platform_actions_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', s_created_at),'YYYY-MM') AS month,
            action_type, COUNT(*) AS cnt
        FROM PIPE_DATABASE.<SCHEMA>.std_object_action
        WHERE s_created_at >= '2025-06-01'
        GROUP BY 1,2 ORDER BY 1, cnt DESC
    """,
    "platform_actions_summary": """
        SELECT action_type, COUNT(*) AS total_actions
        FROM PIPE_DATABASE.<SCHEMA>.std_object_action
        GROUP BY 1 ORDER BY total_actions DESC
    """,
    "escalation_reviews_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', s_created_at),'YYYY-MM') AS month,
            status, COUNT(*) AS cnt
        FROM PIPE_DATABASE.<SCHEMA>.std_escalation_review
        GROUP BY 1,2 ORDER BY 1
    """,
    "ai_summaries_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', s_created_at),'YYYY-MM') AS month,
            summary_type, summary_status, COUNT(*) AS summaries_generated
        FROM PIPE_DATABASE.<SCHEMA>.std_generated_summary
        WHERE s_created_at >= '2025-06-01'
        GROUP BY 1,2,3 ORDER BY 1,2
    """,
    "ai_summaries_total": """
        SELECT summary_type,
            SUM(CASE WHEN summary_status = 'EVALUATED' THEN 1 ELSE 0 END) AS evaluated,
            COUNT(*) AS total
        FROM PIPE_DATABASE.<SCHEMA>.std_generated_summary
        GROUP BY 1 ORDER BY total DESC
    """,
    "sl_feedback_monthly": """
        SELECT TO_CHAR(DATE_TRUNC('MONTH', _sl_created_at),'YYYY-MM') AS month,
            label_class, COUNT(*) AS cnt
        FROM PIPE_DATABASE.<SCHEMA>.sl_feedback
        WHERE _sl_created_at >= '2025-06-01'
        GROUP BY 1,2 ORDER BY 1, cnt DESC
    """,
    "account_summaries_insight": """
        SELECT
            COUNT(DISTINCT object_id_target) AS accounts_summarized,
            COUNT(CASE WHEN summary_status = 'EVALUATED' THEN 1 END) AS evaluated_summaries,
            COUNT(*) AS total_summaries,
            MAX(s_created_at) AS latest_summary
        FROM PIPE_DATABASE.<SCHEMA>.std_generated_summary
        WHERE summary_type = 'ACCOUNT_SUMMARY'
    """,
    "at_risk_accounts_insight": """
        WITH latest_scores AS (
            SELECT s_object_id_creator AS account_id,
                score_value, score_label,
                ROW_NUMBER() OVER (PARTITION BY s_object_id_creator ORDER BY s_created_at DESC) AS rn
            FROM PIPE_DATABASE.<SCHEMA>.ml_prediction
            WHERE ml_prediction_type = 'ACCOUNT_HEALTH_SCORE'
        )
        SELECT
            COUNT(*) AS total_accounts_scored,
            SUM(CASE WHEN score_value < 60 THEN 1 ELSE 0 END) AS at_risk_accounts,
            SUM(CASE WHEN score_value >= 75 THEN 1 ELSE 0 END) AS healthy_accounts,
            ROUND(AVG(score_value), 1) AS avg_health_score
        FROM latest_scores WHERE rn = 1
    """,
}

QUERY_CATALOG = [
    {"id":"frt_monthly",              "name":"FRT monthly",                    "tab":"Routing",       "agent":"Routing Agent",        "tables":["CASE_SUMMARY"],                          "status":"stable"},
    {"id":"escalation_monthly",       "name":"Escalation rate monthly",        "tab":"Escalation",    "agent":"Escalation Agent",     "tables":["CASE_SUMMARY"],                          "status":"stable"},
    {"id":"resolution_monthly",       "name":"Resolution time monthly",        "tab":"Routing",       "agent":"Routing Agent",        "tables":["CASE_SUMMARY"],                          "status":"stable"},
    {"id":"cases_per_agent_weekly",   "name":"Cases per agent weekly",         "tab":"Routing",       "agent":"Routing Agent",        "tables":["CASE_SUMMARY"],                          "status":"stable"},
    {"id":"reassignment_monthly",     "name":"Reassignment rate monthly",      "tab":"Routing",       "agent":"Routing Agent (ICA)",  "tables":["CASE_SUMMARY"],                          "status":"stable"},
    {"id":"frt_by_priority",          "name":"FRT by priority",                "tab":"Routing",       "agent":"Routing Agent",        "tables":["CASE_SUMMARY"],                          "status":"stable"},
    {"id":"priority_mix_monthly",     "name":"Priority mix monthly",           "tab":"Snapshot",      "agent":"Prioritization Agent", "tables":["CASE_SUMMARY"],                          "status":"stable"},
    {"id":"ica_events_monthly",       "name":"ICA events monthly",             "tab":"Routing",       "agent":"Routing Agent (ICA)",  "tables":["STD_EVENT_LOG"],                         "status":"stable"},
    {"id":"ica_total_lifetime",       "name":"ICA lifetime totals",            "tab":"Routing",       "agent":"Routing Agent (ICA)",  "tables":["STD_EVENT_LOG"],                         "status":"stable"},
    {"id":"alerts_monthly",           "name":"Alerts monthly",                 "tab":"Sentiment",     "agent":"Escalation Agent",     "tables":["ALERTS"],                                "status":"stable"},
    {"id":"lte_accuracy_monthly",     "name":"LTE prediction accuracy",        "tab":"Escalation",    "agent":"Escalation Agent",     "tables":["ESCALATION_PREDICTIONS","CASE_SUMMARY"],  "status":"stable"},
    {"id":"sentiment_monthly",        "name":"Sentiment monthly",              "tab":"Sentiment",     "agent":"Sentiment Agent",      "tables":["SL_IMPULSE_SCORE_BY_CHANNEL_2020_02"],    "status":"stable"},
    {"id":"account_health_monthly",   "name":"Account health monthly",         "tab":"Snapshot",      "agent":"Account Health Agent", "tables":["ML_PREDICTION"],                         "status":"stable"},
    {"id":"platform_actions_monthly", "name":"Platform agent actions monthly", "tab":"Feature Usage", "agent":"Platform Engagement",  "tables":["STD_OBJECT_ACTION"],                     "status":"stable"},
    {"id":"platform_actions_summary", "name":"Platform actions summary",       "tab":"Feature Usage", "agent":"Platform Engagement",  "tables":["STD_OBJECT_ACTION"],                     "status":"stable"},
    {"id":"escalation_reviews_monthly","name":"Escalation swarming monthly",   "tab":"Escalation",    "agent":"Escalation Agent",     "tables":["STD_ESCALATION_REVIEW"],                 "status":"stable"},
    {"id":"ai_summaries_monthly",     "name":"AI summaries monthly",           "tab":"Feature Usage", "agent":"Summarization Agent",  "tables":["STD_GENERATED_SUMMARY"],                 "status":"stable"},
    {"id":"ai_summaries_total",       "name":"AI summaries total",             "tab":"Feature Usage", "agent":"Summarization Agent",  "tables":["STD_GENERATED_SUMMARY"],                 "status":"stable"},
    {"id":"sl_feedback_monthly",      "name":"Agent signal feedback monthly",  "tab":"Feature Usage", "agent":"Sentiment Agent",      "tables":["SL_FEEDBACK"],                           "status":"stable"},
    {"id":"account_summaries_insight","name":"Account summaries insight",      "tab":"Pendo",         "agent":"Summarization Agent",  "tables":["STD_GENERATED_SUMMARY"],                 "status":"stable"},
    {"id":"at_risk_accounts_insight", "name":"At-risk accounts insight",       "tab":"Pendo",         "agent":"Account Health Agent", "tables":["ML_PREDICTION"],                         "status":"stable"},
]
