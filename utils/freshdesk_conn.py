"""
utils/freshdesk_conn.py
Freshdesk API connector — fetches renewal dates and company metadata.
Cached 7 days — renewal dates change infrequently.
Only called once per customer per week.
"""

import os
import time
import requests
import streamlit as st
from datetime import datetime


FRESHDESK_DOMAIN = "supportlogic.freshdesk.com"
BASE = f"https://{FRESHDESK_DOMAIN}/api/v2"

# Customer name → search term mapping
# Handles cases where Freshdesk name differs from customers.py name
CUSTOMER_SEARCH_MAP = {
    "AVEVA":              "AVEVA",
    "Hyland":             "Hyland",
    "NICE":               "NICE",
    "Saviynt":            "Saviynt",
    "BlueGrace":          "BlueGrace",
    "Basware":            "Basware",
    "Alteryx":            "Alteryx",
    "Infoblox":           "Infoblox",
    "TraceLink":          "TraceLink",
    "CyberArk":           "CyberArk",
    "Cvent":              "Cvent",
    "NTT Data":           "NTT",
    "Coupa":              "Coupa",
    "Q2":                 "Q2",
    "Proofpoint":         "Proofpoint",
    "ESRI":               "ESRI",
    "Litera":             "Litera",
    "CrowdStrike":        "CrowdStrike",
    "Automation Anywhere":"Automation Anywhere",
    "Qlik":               "Qlik",
    "Rubrik":             "Rubrik",
    "F5":                 "F5",
    "Fivetran":           "Fivetran",
    "Braze":              "Braze",
    "Phenom People":      "Phenom",
    "Grafana Labs":       "Grafana",
    "ABBYY":              "ABBYY",
    "Appspace":           "Appspace",
    "Deep Instinct":      "Deep Instinct",
    "Freshworks":         "Freshworks",
    "Mews":               "Mews",
    "BigPanda":           "BigPanda",
    "Databricks":         "Databricks",
    "Restaurant365":      "Restaurant365",
    "BMC":                "BMC",
    "HPE Zerto":          "Zerto",
    "HPE Nimble Storage": "Nimble",
    "CommScope":          "CommScope",
    "Coveo":              "Coveo",
    "SPS Commerce":       "SPS Commerce",
    "Vercara":            "Vercara",
    "Informatica":        "Informatica",
    "Certinia":           "Certinia",
    "SL4SL":              "SupportLogic",
}


def _get_api_key() -> str:
    key = os.getenv("FRESHDESK_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("FRESHDESK_API_KEY", "")
        except Exception:
            pass
    return key


@st.cache_data(ttl=604800, show_spinner=False)  # 7-day cache
def get_renewal_date(customer_name: str) -> dict:
    """
    Fetch renewal date and company metadata for a customer from Freshdesk.
    Returns dict with: renewal_date, lifecycle_stage, arr, company_name
    Cached 7 days — renewal dates rarely change.
    """
    key = _get_api_key()
    if not key:
        return {"error": "No Freshdesk API key configured"}

    AUTH   = (key, "X")
    search = CUSTOMER_SEARCH_MAP.get(customer_name, customer_name)

    try:
        # Step 1: find company by name
        r = requests.get(
            f"{BASE}/companies/autocomplete?name={search}",
            auth=AUTH, timeout=10
        )
        if r.status_code != 200:
            return {"error": f"Freshdesk API error: {r.status_code}"}

        companies = r.json().get("companies", [])
        if not companies:
            return {"error": f"Company not found in Freshdesk: {search}"}

        company_id   = companies[0]["id"]
        company_name = companies[0]["name"]

        # Step 2: fetch full company details
        r2 = requests.get(f"{BASE}/companies/{company_id}", auth=AUTH, timeout=10)
        if r2.status_code != 200:
            return {"error": f"Could not fetch company details: {r2.status_code}"}

        c  = r2.json()
        cf = c.get("custom_fields", {})

        # Parse renewal date — try multiple fields
        renewal_raw = c.get("renewal_date") or cf.get("subscription_end_date")
        renewal_dt  = None
        renewal_str = None
        if renewal_raw:
            try:
                renewal_dt  = datetime.fromisoformat(str(renewal_raw).replace("Z",""))
                renewal_str = renewal_dt.strftime("%d %b %Y")
            except Exception:
                renewal_str = str(renewal_raw)[:10]

        return {
            "company_name":    company_name,
            "company_id":      company_id,
            "renewal_date":    renewal_dt,
            "renewal_str":     renewal_str,
            "lifecycle_stage": cf.get("lifecycle_stage"),
            "arr":             cf.get("current_arr") or cf.get("account_acv"),
            "go_live_date":    cf.get("go_live_date"),
            "error":           None,
        }

    except Exception as e:
        return {"error": str(e)}


def is_available() -> bool:
    return bool(_get_api_key())
