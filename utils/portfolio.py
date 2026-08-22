"""
utils/portfolio.py
Portfolio Intelligence data loader.

Architecture:
- Loads account metadata from accounts.xlsx (local) or Google Sheets (if public)
- Deduplicates to one row per customer (latest/highest ARR row)
- Merges with customers.py for schema/pendo/go_live data
- Cached 5 minutes — all filtering done in pandas, zero Snowflake queries
- When Google Sheet is made public, set PORTFOLIO_SHEET_ID in .env
"""

import os
import io
import pathlib
import pandas as pd
import requests
import streamlit as st
from datetime import datetime, date

# ── Config ────────────────────────────────────────────────────────────────────
SHEET_ID  = "1QhcklrfWoEyHRRmRIdzC0qUQ1VqiYkK3"
SHEET_GID = "1187190574"
LOCAL_FILE = pathlib.Path("data/accounts.xlsx")

# Column name mapping from xlsx → internal field names
COL_MAP = {
    "Customer name":                "name",
    "Lifecycle Stage":              "lifecycle",
    "Customer Success Manager":     "csm",
    "SOR":                          "crm",
    "ARR":                          "arr",
    "Licensed Annual Case Volume":  "licensed_case_volume",
    "Actual Annual Case Volume":    "actual_case_volume",
    "Account Director":             "account_director",
    "Assigned TSE":                 "tse",
    "Initial Contract Date":        "contract_date",
    "Live on Core since":           "live_since",
    "Renewal Date":                 "renewal_date",
    "Core SX purchased":            "core_purchased",
    "Assign purchased":             "assign_purchased",
    "Assist purchased":             "assist_purchased",
    "Expand purchased":             "expand_purchased",
    "Elevate purchased":            "elevate_purchased",
    "Resolve (with xFind) purchased": "resolve_purchased",
    "Data Cloud In Scope":          "data_cloud_scope",
    "MCP in Scope":                 "mcp_scope",
    "Core Status":                  "core_status",
    "Core iFrames Status":          "core_iframe_status",
    "Assign Status":                "assign_status",
    "Assist Status":                "assist_status",
    "Expand Status":                "expand_status",
    "Elevate Customers":            "elevate_status",
    "Resolve Status":               "resolve_status",
    "Data Cloud Status":            "data_cloud_status",
    "Gainsight integration Status": "gainsight_status",
    "CRM Widgets enabled":          "crm_widgets",
    "SSO Provider":                 "sso",
    "CRM Importer":                 "crm_importer",
    "Write backs":                  "writebacks",
    "Contract type":                "contract_type",
    "Customer URLs":                "customer_url",
    "Notes":                        "notes",
    "FDE":                          "fde",
    "Allows Beta Features":         "beta_features",
    "Allows AI summarizations":     "ai_summarizations",
    "MCP":                          "mcp_status",
}

# Status → is_live logic
def _is_live(val) -> bool:
    if not val or str(val).strip() in ("", "None", "--", "nan"):
        return False
    v = str(val).lower()
    return "live" in v and "churn" not in v

def _is_purchased(val) -> bool:
    if not val or str(val).strip() in ("", "None", "--", "nan"):
        return False
    v = str(val).lower()
    return v not in ("no", "n/a", "not purchased", "") and len(v) > 0

def _crm_normalize(val) -> str:
    if not val or str(val).strip() in ("", "None", "nan"):
        return "Unknown"
    v = str(val).lower()
    if "salesforce" in v or "sfdc" in v:
        return "Salesforce"
    if "zendesk" in v:
        return "Zendesk"
    if "freshdesk" in v or "freshservice" in v:
        return "Freshdesk"
    if "jira" in v or "servicenow" in v or "devrev" in v:
        return "Other"
    return "Other"

def _arr_segment(arr) -> str:
    if not arr or pd.isna(arr):
        return "Unknown"
    try:
        a = float(arr)
        if a >= 1_000_000:  return "$1M+"
        if a >= 500_000:    return "$500K–$1M"
        if a >= 250_000:    return "$250K–$500K"
        return "<$250K"
    except:
        return "Unknown"

def _days_to_renewal(renewal_date) -> int:
    if not renewal_date or pd.isna(renewal_date):
        return None
    try:
        if isinstance(renewal_date, (datetime, date)):
            rd = pd.Timestamp(renewal_date)
        else:
            rd = pd.to_datetime(renewal_date)
        return (rd - pd.Timestamp.now()).days
    except:
        return None

def _module_count(row) -> int:
    modules = ["core_purchased", "assign_purchased", "assist_purchased",
               "expand_purchased", "elevate_purchased", "resolve_purchased"]
    return sum(1 for m in modules if _is_purchased(row.get(m)))

def _live_module_count(row) -> int:
    statuses = ["core_status", "assign_status", "assist_status",
                "expand_status", "elevate_status", "resolve_status"]
    return sum(1 for s in statuses if _is_live(row.get(s)))


@st.cache_data(ttl=300, show_spinner=False)
def load_portfolio() -> pd.DataFrame:
    """
    Load and clean portfolio data.
    Tries Google Sheets first, falls back to local xlsx.
    Returns one row per customer with all portfolio fields.
    Cached 5 minutes.
    """
    raw = None

    # 1. Try Google Sheets (if public)
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and "DOCTYPE" not in r.text[:100]:
            raw = pd.read_csv(io.StringIO(r.text), dtype=str)
    except Exception:
        pass

    # 2. Fall back to local xlsx
    if raw is None:
        if not LOCAL_FILE.exists():
            return pd.DataFrame()
        import openpyxl
        wb = openpyxl.load_workbook(str(LOCAL_FILE), read_only=True, data_only=True)
        ws = wb["Up to date"]
        rows = list(ws.iter_rows(values_only=True))
        headers = [str(h).strip() if h else f"col_{i}" for i,h in enumerate(rows[0])]
        data = [dict(zip(headers, [str(v) if v is not None else "" for v in r]))
                for r in rows[1:] if any(v is not None for v in r)]
        raw = pd.DataFrame(data)
        wb.close()

    if raw is None or raw.empty:
        return pd.DataFrame()

    # Rename columns
    rename = {k: v for k, v in COL_MAP.items() if k in raw.columns}
    raw = raw.rename(columns=rename)

    # Clean name
    if "name" not in raw.columns:
        return pd.DataFrame()
    raw["name"] = raw["name"].astype(str).str.strip()
    raw = raw[raw["name"].notna() & (raw["name"] != "") & (raw["name"] != "nan")]

    # Parse ARR
    if "arr" in raw.columns:
        raw["arr"] = pd.to_numeric(raw["arr"], errors="coerce")

    # Parse dates
    for dc in ["renewal_date", "live_since", "contract_date"]:
        if dc in raw.columns:
            raw[dc] = pd.to_datetime(raw[dc], errors="coerce")

    # Deduplicate: one row per customer name — keep highest ARR row
    if "arr" in raw.columns:
        raw = raw.sort_values("arr", ascending=False)
    raw = raw.drop_duplicates(subset="name", keep="first")

    # Merge with customers.py for schema/pendo data
    try:
        from utils.customers import CUSTOMERS
        cust_data = []
        for cname, cdict in CUSTOMERS.items():
            cust_data.append({
                "name_key":   cname,
                "schema":     cdict.get("schema", ""),
                "pendo_id":   cdict.get("pendo_id", ""),
                "go_live":    cdict.get("go_live", ""),
                "license_sl": cdict.get("license", ""),
                "goals":      ", ".join(cdict.get("goals", [])),
                "csm_sl":     cdict.get("csm", ""),
                "tse_sl":     cdict.get("sa", ""),
            })
        df_cust = pd.DataFrame(cust_data)

        # Fuzzy match: try exact then partial
        def match_customer(name):
            name_l = str(name).lower().strip()
            for _, c in df_cust.iterrows():
                if c["name_key"].lower() == name_l:
                    return c["name_key"]
            for _, c in df_cust.iterrows():
                if c["name_key"].lower() in name_l or name_l in c["name_key"].lower():
                    return c["name_key"]
            return None

        raw["name_key"] = raw["name"].apply(match_customer)
        raw = raw.merge(df_cust, on="name_key", how="left")
    except Exception:
        pass

    # Derived fields
    raw["arr_segment"]    = raw["arr"].apply(_arr_segment)
    raw["crm_type"]       = raw.get("crm", pd.Series(["Unknown"]*len(raw))).apply(_crm_normalize)
    raw["days_to_renewal"]= raw.get("renewal_date", pd.Series([None]*len(raw))).apply(_days_to_renewal)
    raw["module_count"]   = raw.apply(_module_count, axis=1)
    raw["live_module_count"] = raw.apply(_live_module_count, axis=1)

    # Boolean module flags
    for mod, col in [
        ("core",    "core_purchased"),
        ("assign",  "assign_purchased"),
        ("assist",  "assist_purchased"),
        ("expand",  "expand_purchased"),
        ("elevate", "elevate_purchased"),
        ("resolve", "resolve_purchased"),
    ]:
        raw[f"{mod}_has"] = raw.get(col, pd.Series([""]*len(raw))).apply(_is_purchased)

    for mod, col in [
        ("core",    "core_status"),
        ("assign",  "assign_status"),
        ("assist",  "assist_status"),
        ("expand",  "expand_status"),
        ("elevate", "elevate_status"),
        ("resolve", "resolve_status"),
    ]:
        raw[f"{mod}_live"] = raw.get(col, pd.Series([""]*len(raw))).apply(_is_live)

    # ICA = assign module
    raw["ica_live"] = raw["assign_live"]

    return raw.reset_index(drop=True)


def get_portfolio_kpis(df: pd.DataFrame) -> dict:
    """Compute top-level portfolio KPIs from the cached dataframe."""
    arr = df["arr"].dropna()
    return {
        "total_accounts":    len(df),
        "total_arr":         arr.sum(),
        "avg_arr":           arr.mean() if len(arr) else 0,
        "median_arr":        arr.median() if len(arr) else 0,
        "accounts_500k_plus": (arr >= 500_000).sum(),
        "accounts_1m_plus":  (arr >= 1_000_000).sum(),
        "sf_count":          (df["crm_type"] == "Salesforce").sum(),
        "zd_count":          (df["crm_type"] == "Zendesk").sum(),
        "fd_count":          (df["crm_type"] == "Freshdesk").sum(),
        "core_live":         df.get("core_live", pd.Series([False]*len(df))).sum(),
        "assign_live":       df.get("assign_live", pd.Series([False]*len(df))).sum(),
        "assist_live":       df.get("assist_live", pd.Series([False]*len(df))).sum(),
        "expand_live":       df.get("expand_live", pd.Series([False]*len(df))).sum(),
        "elevate_live":      df.get("elevate_live", pd.Series([False]*len(df))).sum(),
        "resolve_live":      df.get("resolve_live", pd.Series([False]*len(df))).sum(),
        "ica_live":          df.get("ica_live", pd.Series([False]*len(df))).sum(),
        "renewal_90d":       ((df["days_to_renewal"] >= 0) & (df["days_to_renewal"] <= 90)).sum() if "days_to_renewal" in df.columns else 0,
    }


def fmt_arr(v) -> str:
    """Format ARR value as human-readable string."""
    if not v or (hasattr(v, '__class__') and v.__class__.__name__ == 'float' and v != v):
        return "—"
    try:
        n = float(v)
        if pd.isna(n): return "—"
        if n >= 1_000_000: return f"${n/1_000_000:.1f}M"
        if n >= 1_000:     return f"${n/1_000:.0f}K"
        return f"${n:,.0f}"
    except: return "—"
