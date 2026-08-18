"""
utils/pendo_conn.py
Pendo Aggregation API connector.

Key findings from API exploration:
- group aggregator does NOT support field definitions — aggregate in pandas instead
- pageEvents raw rows: pageId, visitorId, day, numEvents, numMinutes
- featureEvents raw rows: featureId, visitorId, day, numEvents
- Account IDs match customer name lowercase e.g. "aveva", "fourth"
"""

import os
import requests
import pandas as pd
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

PENDO_BASE = "https://app.pendo.io/api/v1"


def _key() -> str:
    k = os.getenv("PENDO_API_KEY", "")
    if not k:
        try:
            k = st.secrets.get("PENDO_API_KEY", "")
        except Exception:
            pass
    return k


def _h() -> dict:
    return {"x-pendo-integration-key": _key(), "Content-Type": "application/json"}


def _post(pipeline: list, rid: str = "q") -> list:
    try:
        r = requests.post(f"{PENDO_BASE}/aggregation", headers=_h(),
            json={"response": {"mimeType": "application/json"},
                  "request": {"requestId": rid, "pipeline": pipeline}},
            timeout=30)
        return r.json().get("results", []) if r.status_code == 200 else []
    except Exception:
        return []


@st.cache_data(ttl=86400, show_spinner=False)
def get_page_map() -> dict:
    try:
        r = requests.get(f"{PENDO_BASE}/page", headers=_h(), timeout=15)
        return {p["id"]: p.get("name", p["id"]) for p in r.json()} if r.ok else {}
    except Exception:
        return {}


@st.cache_data(ttl=86400, show_spinner=False)
def get_feature_map() -> dict:
    try:
        r = requests.get(f"{PENDO_BASE}/feature", headers=_h(), timeout=15)
        return {f["id"]: f.get("name", f["id"]) for f in r.json()} if r.ok else {}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def get_visitor_count(account_id: str) -> int:
    results = _post([
        {"source": {"visitors": {"account": {"id": account_id}}}},
        {"count": None},
    ], "visitor-count")
    return results[0].get("count", 0) if results else 0


@st.cache_data(ttl=3600, show_spinner=False)
def get_page_views(account_id: str, days: int = 30) -> pd.DataFrame:
    results = _post([
        {"source": {"pageEvents": None,
                    "timeSeries": {"period": "dayRange", "first": "now()", "count": -days}}},
        {"filter": f'accountId == "{account_id}"'},
        {"limit": 10000},
    ], f"pg-{account_id}-{days}")
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["day"], unit="ms").dt.strftime("%Y-%m-%d")
    geo_cols = ["country","region","latitude","longitude"]
    keep = ["pageId","visitorId","date","numEvents","numMinutes"] + geo_cols
    cols = [c for c in keep if c in df.columns]
    return df[cols].copy()


@st.cache_data(ttl=3600, show_spinner=False)
def get_feature_events(account_id: str, days: int = 30) -> pd.DataFrame:
    results = _post([
        {"source": {"featureEvents": None,
                    "timeSeries": {"period": "dayRange", "first": "now()", "count": -days}}},
        {"filter": f'accountId == "{account_id}"'},
        {"limit": 10000},
    ], f"ft-{account_id}-{days}")
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["day"], unit="ms").dt.strftime("%Y-%m-%d")
    cols = [c for c in ["featureId","visitorId","date","numEvents"] if c in df.columns]
    return df[cols].copy()


def dau(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "visitorId" not in df.columns:
        return pd.DataFrame()
    return (df.groupby("date")["visitorId"].nunique()
              .reset_index().rename(columns={"visitorId":"dau"}).sort_values("date"))


def wau(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    d = df.copy()
    d["week"] = pd.to_datetime(d["date"]).dt.to_period("W").dt.start_time.dt.strftime("%Y-%m-%d")
    return (d.groupby("week")["visitorId"].nunique()
              .reset_index().rename(columns={"visitorId":"wau"}).sort_values("week"))


def top_pages(df: pd.DataFrame, page_map: dict, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    agg = (df.groupby("pageId")
             .agg(total_views=("numEvents","sum"),
                  unique_users=("visitorId","nunique"),
                  avg_minutes=("numMinutes","mean"))
             .reset_index()
             .sort_values("total_views", ascending=False)
             .head(n))
    agg["page_name"] = (agg["pageId"].map(page_map)
                          .fillna(agg["pageId"])
                          .str.replace(r"^\[IFrame\]\s*", "", regex=True)
                          .str.strip())
    return agg[["page_name","total_views","unique_users","avg_minutes"]].round(1)


def top_features(df: pd.DataFrame, feature_map: dict, n: int = 10) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    agg = (df.groupby("featureId")
             .agg(total_clicks=("numEvents","sum"),
                  unique_users=("visitorId","nunique"))
             .reset_index()
             .sort_values("total_clicks", ascending=False)
             .head(n))
    agg["feature_name"] = (agg["featureId"].map(feature_map)
                             .fillna(agg["featureId"])
                             .str.replace(r"^\[IFrame\]\s*", "", regex=True)
                             .str.strip())
    return agg[["feature_name","total_clicks","unique_users"]]


def time_in_platform(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "numMinutes" not in df.columns:
        return pd.DataFrame()
    return (df.groupby("date")["numMinutes"].sum()
              .reset_index().rename(columns={"numMinutes":"total_minutes"})
              .sort_values("date"))


def adoption_tiers(df: pd.DataFrame) -> dict:
    """
    Segment users into adoption tiers based on total minutes in period.
    Active:   >= 180 min (3+ hrs)
    Moderate: 60–179 min (1–3 hrs)
    Low:      < 60 min
    Returns dict with counts, percentages, and per-user breakdown.
    """
    if df.empty or "visitorId" not in df.columns or "numMinutes" not in df.columns:
        return {"total": 0, "active": 0, "moderate": 0, "low": 0,
                "active_pct": 0, "moderate_pct": 0, "low_pct": 0, "per_user": pd.DataFrame()}

    per_user = (df.groupby("visitorId")["numMinutes"]
                  .sum()
                  .reset_index()
                  .rename(columns={"numMinutes": "total_minutes"}))

    total    = len(per_user)
    active   = len(per_user[per_user["total_minutes"] >= 180])
    moderate = len(per_user[(per_user["total_minutes"] >= 60) & (per_user["total_minutes"] < 180)])
    low      = len(per_user[per_user["total_minutes"] < 60])

    def pct(n): return round(n / total * 100) if total else 0

    per_user["tier"] = per_user["total_minutes"].apply(
        lambda m: "Active" if m >= 180 else "Moderate" if m >= 60 else "Low"
    )
    per_user["hours"] = (per_user["total_minutes"] / 60).round(1)

    return {
        "total":        total,
        "active":       active,
        "moderate":     moderate,
        "low":          low,
        "active_pct":   pct(active),
        "moderate_pct": pct(moderate),
        "low_pct":      pct(low),
        "per_user":     per_user.sort_values("total_minutes", ascending=False),
    }


def top_modules(df: pd.DataFrame, page_map: dict, n: int = 3) -> pd.DataFrame:
    """Top N pages by total views with name, unique users, total time."""
    if df.empty:
        return pd.DataFrame()
    agg = (df.groupby("pageId")
             .agg(total_views=("numEvents", "sum"),
                  unique_users=("visitorId", "nunique"),
                  total_mins=("numMinutes", "sum"))
             .reset_index()
             .sort_values("total_views", ascending=False)
             .head(n))
    agg["page_name"] = (agg["pageId"].map(page_map)
                          .fillna(agg["pageId"])
                          .str.replace(r"^\[IFrame\]\s*", "", regex=True)
                          .str.strip())
    agg["total_hrs"] = (agg["total_mins"] / 60).round(1)
    return agg[["page_name", "total_views", "unique_users", "total_hrs"]].reset_index(drop=True)


def classify_region(row: dict) -> str:
    """Classify a Pendo event row into EMEA / APAC / Americas / Unknown."""
    lat = row.get("latitude", 0) or 0
    lon = row.get("longitude", 0) or 0
    if lat == 0 and lon == 0:
        return "Unknown"
    if lon >= 60:
        return "APAC"
    if lon >= -30:
        return "EMEA"
    return "Americas"


def geo_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns per-user region classification.
    Columns: visitorId, geo_region, country, sessions
    """
    if df.empty or "visitorId" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["geo_region"] = df.apply(classify_region, axis=1)

    # Build agg dict dynamically based on available columns
    agg_dict = {
        "geo_region": ("geo_region", lambda x: x.mode()[0] if len(x) else "Unknown"),
        "sessions":   ("numEvents",  "sum") if "numEvents" in df.columns else ("geo_region", "count"),
    }
    if "country" in df.columns:
        agg_dict["country"] = ("country", lambda x: x.mode()[0] if len(x) else "—")

    user_geo = df.groupby("visitorId").agg(**agg_dict).reset_index()

    if "country" not in user_geo.columns:
        user_geo["country"] = "—"
    return user_geo


def region_summary(df_geo: pd.DataFrame) -> pd.DataFrame:
    """
    Returns region-level summary.
    Columns: geo_region, users, sessions, pct
    """
    if df_geo.empty:
        return pd.DataFrame()
    total = len(df_geo)
    summary = (
        df_geo.groupby("geo_region")
              .agg(users=("visitorId","count"), sessions=("sessions","sum"))
              .reset_index()
              .sort_values("users", ascending=False)
    )
    summary["pct"] = (summary["users"] / total * 100).round(1)
    return summary


def country_breakdown(df_geo: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Top N countries by unique users."""
    if df_geo.empty or "country" not in df_geo.columns:
        return pd.DataFrame()
    return (
        df_geo.groupby("country")
              .agg(users=("visitorId","count"))
              .reset_index()
              .sort_values("users", ascending=False)
              .head(top_n)
    )
