"""
utils/slack_feed.py
Fetches and formats recent Slack activity for a customer channel.
Returns structured highlights: meeting notes, outages, open issues, data sync alerts.
"""

CUSTOMER_CHANNELS = {
    "Automation Anywhere": "C03FF1F2X1Q",
    "Qlik":               "CRYKUMR88",
    "Rubrik":             "CBRK79PEU",
    "F5":                 "C09UVN09NTX",
    "Fivetran":           "C014WA724LD",
    "Braze":              "C074JBTUTRN",
    "Phenom People":      "C031V2LE4BS",
    "Grafana Labs":       "C0874FVLVJL",
    "AVEVA":     "C064QE64ZCY",
    "Hyland":    "C09G2AJ18G7",
    "NICE":      "C0565AP28LS",
    "BlueGrace": "C08QZ8Z76A2",
    "Alteryx":   "C03HR817G4U",
    "Infoblox":  "C07ANSZQRTN",
    "TraceLink": "C0AH2AX81DW",
    "CyberArk":  "C048PFTBYRL",
    "Demo3":   None,
    "CyberArk": None,
}

# Pre-extracted highlights from #internal-aveva (Jun 2026)
# In production this would be fetched live via the Slack API
SLACK_HIGHLIGHTS = {

    "Hyland": [
        {
            "date":    "Jul 29 2026",
            "type":    "meeting",
            "title":   "Weekly sync — Assign + Elevate + Genesys",
            "summary": "Chose SupportLogic over AptEdge (competitor). Assign keyword list complete — Aaron reviewing. Elevate weekly Thursday call scheduled. Genesys sandbox not feasible — evaluating live session. Resolve Assist 30-40s latency reported by users under investigation. Salesforce writeback two options presented to Aaron/David.",
            "risk":    "medium",
            "actions": [
                "Aaron: Confirm logout fix and decide Salesforce writeback path",
                "Dilip: Investigate Resolve Assist latency",
                "Dilip: Schedule Thursday Elevate call",
                "Thamizh: Schedule Assign module kickoff",
            ],
        },
        {
            "date":    "Aug 3 2026",
            "type":    "maintenance",
            "title":   "ICA account-level field mapping (CO-2106)",
            "summary": "Thamizharasan working on adding account-level fields for ICA routing. CRM importer restarted briefly. Elevate field mapping (CO-2102) and Product Line keyword fields (CO-2100) also in progress.",
            "risk":    "low",
            "actions": [],
        },
    ],

    "Infoblox": [
        {
            "date":    "Jul 28 2026",
            "type":    "meeting",
            "title":   "Fivetran reliability — customer requesting alternative",
            "summary": "Infoblox frustrated with recurring Fivetran data sync issues impacting ACA case assignments. Requesting alternative connector. Manochitra collated 3 months of ACA issues for Engineering review. Balki and Krishna involved.",
            "risk":    "high",
            "actions": [
                "Engineering: Evaluate alternative connector to Fivetran for Infoblox",
                "Manochitra: Share ACA issue log with Engineering",
            ],
        },
        {
            "date":    "May 6 2026",
            "type":    "meeting",
            "title":   "Custom Object writeback request — LTE + sentiment signals",
            "summary": "Infoblox requesting writeback of LTE prediction timestamps, signal acknowledgements, sentiment scores, and Needs Attention scores to CRM as Custom Objects. Thomas Evans to confirm if additional cost involved.",
            "risk":    "low",
            "actions": ["Thomas Evans: Confirm PS cost for Custom Object writeback"],
        },
    ],

    "TraceLink": [
        {
            "date":    "Aug 3 2026",
            "type":    "meeting",
            "title":   "ResolveSX weekly status — credentials blocked",
            "summary": "Integration stalled waiting for Confluence/Jira service account credentials from Ankit. Fallback plan: proceed with Salesforce-only sources. Role mapping patched by Sreejith. Regular Wednesday call cancelled this week — async updates via email.",
            "risk":    "medium",
            "actions": [
                "Ankit Solanki: Provide Confluence/Jira credentials ETA",
                "Ankit Solanki: Identify first-time user for role-mapping UAT",
                "Sreejith: Complete role remapping today",
            ],
        },
    ],

    "CyberArk": [
        {
            "date":    "May 13 2026",
            "type":    "meeting",
            "title":   "CHURN NOTICE — PANW discontinuing SupportLogic",
            "summary": "Paul Kozlov confirmed Palo Alto Networks (post-CyberArk acquisition) will not renew — building internal Salesforce-native solution. Contract runs until Salesforce migration (~Aug 2026). Contract is NON-CANCELLABLE through Dec 2027 ($310k/yr). PANW acknowledged SL has stronger sentiment and AI signals. SL strategy: executive business review before termination discussion.",
            "risk":    "high",
            "actions": [
                "Melanie: Secure executive-level meeting with PANW decision makers",
                "Melanie: Build usage/value business case",
                "Yaron (PANW Procurement): Will reach out to Melanie",
            ],
        },
    ],

    "Alteryx": [
        {
            "date":    "Jun 24 2026",
            "type":    "maintenance",
            "title":   "Fivetran connector broken — re-auth required",
            "summary": "Alteryx Fivetran connector broken causing data sync alerts for 24+ hours. Customer informed and working with internal IT to reauthorize. Tracked in support ticket 10594.",
            "risk":    "medium",
            "actions": ["Alteryx IT: Reauthorize Fivetran connector"],
        },
    ],

    "AVEVA": [
        {
            "date":    "16 Jun 2026",
            "type":    "meeting",
            "title":   "Monthly sync — Jun 16",
            "summary": "Gustavo flagged two critical widget regressions (missing follow-up sentiment signal, sentiment mismatch). Fix for outbound-activity bug ready pending Engineering deployment. Value deck reviewed — metrics need refinement. Renewal due Nov/Dec — at risk if quality issues persist.",
            "risk":    "high",
            "actions": [
                "Dilip: Verify regression screenshots with Engineering",
                "Dilip: Email Gustavo deployment timeline for outbound-activity fix",
                "Dilip: Schedule follow-up to refine value-deck metrics",
            ],
        },
        {
            "date":    "11 Jun 2026",
            "type":    "maintenance",
            "title":   "Accounts data consolidation — 13 Jun weekend",
            "summary": "AVEVA consolidating ~92,800 cases (Tech Support + Success Service Requests). Translation on ingest disabled during maintenance window (Fri evening – Mon morning) to prevent API cost spike.",
            "risk":    "medium",
            "actions": [],
        },
        {
            "date":    "12 May 2026",
            "type":    "meeting",
            "title":   "iframe UAT status check — May 12",
            "summary": "7 open defects reviewed: 2 fixed (tone button, feedback errors), 3 still red (case summary error, sentiment mismatch, customer-ID glitch). Gustavo expressed low confidence — warned month-long delay risks adoption. Next release 9.7.1 targeted.",
            "risk":    "high",
            "actions": [
                "Dilip: Confirm backend fix timeline and schedule Thursday status call",
                "Trevor: Validate case-summary bug with end-users Alex & Anthony",
            ],
        },
        {
            "date":    "11 Apr 2026",
            "type":    "maintenance",
            "title":   "Bulk case update — 575K records impacted",
            "summary": "AVEVA bulk-updated 575K case records over the weekend. Fivetran sync and downstream processes were impacted. Translation on ingest disabled during window. Matt re-enabled Monday.",
            "risk":    "low",
            "actions": [],
        },
        {
            "date":    "29 Apr 2026",
            "type":    "meeting",
            "title":   "Monthly sync — Apr 29",
            "summary": "Reviewed widget issues (thumbs feedback bug, tone selector, reference-ID mismatch, Send button greyed). Engineering fixes targeted first week of May. Gustavo stressed urgency — 600 engineers at risk of losing trust if early bugs persist.",
            "risk":    "medium",
            "actions": [
                "Dilip: Coordinate fix release date and communicate to Gustavo",
                "Gustavo: Move Alex Van Fossen to Manager profile for testing",
                "Alberto: Update defect tracker and share with Dilip",
            ],
        },
    ],
    "Fourth": [
        {
            "date":    "Recent",
            "type":    "info",
            "title":   "No recent highlights loaded",
            "summary": "Load #internal-fourth channel for latest activity.",
            "risk":    "low",
            "actions": [],
        },
    ],
}

RISK_STYLE = {
    "high":   ("🔴", "#3a1a1a", "#E24B4A"),
    "medium": ("🟡", "#3a2e10", "#BA7517"),
    "low":    ("🟢", "#1a3a2a", "#1D9E75"),
}

TYPE_ICON = {
    "meeting":     "📋",
    "maintenance": "🔧",
    "outage":      "⚠️",
    "info":        "ℹ️",
}


def get_highlights(customer_name: str) -> list[dict]:
    return SLACK_HIGHLIGHTS.get(customer_name, [])


def has_channel(customer_name: str) -> bool:
    return CUSTOMER_CHANNELS.get(customer_name) is not None
