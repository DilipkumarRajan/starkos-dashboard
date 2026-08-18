"""
utils/brief_generator.py
Generates an AI Account Intelligence Brief using live dashboard data.
"""

import os, json, requests
import pandas as pd
from datetime import datetime
from utils.safe_data import safe_float, safe_int, ica_active, ica_counts


def _has_api_key() -> bool:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
    return bool(key)


def _get_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
    return key


def _compile_facts(customer_name, customer, data, pendo_data=None):
    df_frt    = data.get("frt_monthly",          pd.DataFrame())
    df_esc    = data.get("escalation_monthly",   pd.DataFrame())
    df_lte    = data.get("lte_accuracy_monthly", pd.DataFrame())
    df_re     = data.get("reassignment_monthly", pd.DataFrame())
    df_health = data.get("account_health_monthly", pd.DataFrame())
    df_sent   = data.get("sentiment_monthly",    pd.DataFrame())
    df_alerts = data.get("alerts_monthly",       pd.DataFrame())
    df_ica    = data.get("ica_total_lifetime",   pd.DataFrame())
    df_summ   = data.get("ai_summaries_total",   pd.DataFrame())
    df_act    = data.get("platform_actions_summary", pd.DataFrame())

    go_live = customer.get("go_live", "—")
    bm      = customer.get("benchmark_escalation_pct", 2.0)

    period_start = df_frt["month"].iloc[0]  if not df_frt.empty else go_live
    period_end   = df_frt["month"].iloc[-2] if not df_frt.empty and len(df_frt)>=2 else "present"
    period_label = f"{period_start} to {period_end}"

    frt_base    = safe_float(df_frt, "avg_frt_hours", idx=0)
    frt_cur     = safe_float(df_frt, "avg_frt_hours", idx=-2)
    frt_pct     = round((1-frt_cur/frt_base)*100) if frt_base else 0
    frt_ms      = df_frt["month"].iloc[0]  if not df_frt.empty else "—"
    frt_me      = df_frt["month"].iloc[-2] if not df_frt.empty and len(df_frt)>=2 else "—"

    esc_cur  = safe_float(df_esc, "escalation_pct", idx=-2)
    esc_base = safe_float(df_esc, "escalation_pct", idx=0)
    esc_mon  = df_esc["month"].iloc[-2] if not df_esc.empty and len(df_esc)>=2 else "—"
    tot_cases= safe_int(df_esc, "total_cases")

    lte_pred = safe_int(df_lte, "cases_predicted")
    lte_act  = safe_int(df_lte, "actually_escalated")
    lte_prev = lte_pred - lte_act
    lte_per  = f"{df_lte['month'].iloc[0]} to {df_lte['month'].iloc[-1]}" if not df_lte.empty and len(df_lte)>=2 else period_label

    re_base  = safe_float(df_re, "reassignment_pct", idx=0)
    re_cur   = safe_float(df_re, "reassignment_pct", idx=-2)
    re_mon   = df_re["month"].iloc[-2] if not df_re.empty and len(df_re)>=2 else "—"

    s_cur    = safe_float(df_sent, "avg_sentiment", idx=-1)
    s_base   = safe_float(df_sent, "avg_sentiment", idx=0)
    s_mon    = df_sent["month"].iloc[-1] if not df_sent.empty else "—"
    s_cases  = safe_int(df_sent, "cases_scored")
    s_dir    = "stable" if abs(s_cur-s_base)<3 else ("improved" if s_cur>s_base else "declined")

    h_cur    = safe_float(df_health, "avg_health_score", idx=-1)
    h_peak   = float(df_health["avg_health_score"].max()) if not df_health.empty else 0
    h_mon    = df_health["month"].iloc[-1] if not df_health.empty else "—"
    h_label  = "Good" if h_cur>=70 else "Fair" if h_cur>=50 else "Poor"

    ica_on   = ica_active(df_ica)
    ac, _    = ica_counts(df_ica)
    tot_asgn = ac + _
    ica_pct  = round(ac/tot_asgn*100) if tot_asgn else 0

    al_tot   = safe_int(df_alerts, "total_alerts")
    al_per   = f"{df_alerts['month'].iloc[0]} to {df_alerts['month'].iloc[-1]}" if not df_alerts.empty and len(df_alerts)>=2 else period_label
    su_tot   = safe_int(df_summ, "total")
    act_tot  = safe_int(df_act,  "total_actions")

    pt = pendo_data or {}
    tiers = pt.get("tiers", {})
    mods  = pt.get("top_modules")
    top_mod = str(mods.iloc[0].get("page_name","—")) if mods is not None and not mods.empty else "—"

    return dict(
        customer_name=customer_name, go_live=go_live,
        license=customer.get("license","—"), goals=customer.get("goals",[]),
        period_label=period_label, period_start=period_start, period_end=period_end,
        total_cases=tot_cases, benchmark=bm,
        frt_base=frt_base, frt_cur=frt_cur, frt_pct=frt_pct, frt_ms=frt_ms, frt_me=frt_me,
        esc_cur=esc_cur, esc_base=esc_base, esc_mon=esc_mon,
        esc_vs=("below" if esc_cur<bm else "above"),
        lte_pred=lte_pred, lte_act=lte_act, lte_prev=lte_prev, lte_per=lte_per,
        re_base=re_base, re_cur=re_cur, re_mon=re_mon,
        s_cur=s_cur, s_base=s_base, s_mon=s_mon, s_cases=s_cases, s_dir=s_dir,
        h_cur=h_cur, h_peak=h_peak, h_mon=h_mon, h_label=h_label,
        ica_on=ica_on, ica_auto=ac, ica_pct=ica_pct,
        al_tot=al_tot, al_per=al_per, su_tot=su_tot, act_tot=act_tot,
        pendo_ok=bool(pendo_data),
        p_vis=pt.get("visitors",0), p_dau=pt.get("avg_dau",0), p_days=pt.get("days",30),
        p_act=tiers.get("active_pct",0), p_mod=tiers.get("moderate_pct",0),
        p_low=tiers.get("low_pct",0), p_tot=tiers.get("total",0),
        top_mod=top_mod,
    )


def generate_brief(customer_name, customer, data, pendo_data=None):
    f = _compile_facts(customer_name, customer, data, pendo_data)

    pendo_block = f"""
- Total lifetime visitors (Pendo): {f['p_vis']:,}
- Avg daily active users (last {f['p_days']}d): {f['p_dau']:,}
- Active users (3+ hrs in last {f['p_days']}d): {f['p_act']}% of {f['p_tot']} users
- Moderate users (1-3 hrs): {f['p_mod']}% | Low users (<1 hr): {f['p_low']}%
- Most visited module: {f['top_mod']}""" if f['pendo_ok'] else "- Pendo data not available for this customer"

    prompt = f"""You are a Senior Customer Success Analyst at SupportLogic writing an Account Intelligence Brief for {f['customer_name']}.

This brief will be read by CSMs, AEs, Product teams, and Leadership. Write for all audiences simultaneously.

RULES — follow strictly:
1. Every metric you mention MUST include the time period it covers
2. Every change (increase/decrease) must state: from what value, to what value, over what period
3. Use only the numbers provided — do not invent or estimate anything not given
4. Be direct and factual — neither overly positive nor negative
5. If something underperforms vs benchmark, say so with the data
6. Keep each section to 2-4 sentences maximum
7. Industry benchmarks for context (use to frame performance): FRT <4hrs is excellent, escalation rate <2% is healthy, sentiment 65-75 is stable, reassignment <3% is good

ACCOUNT DATA:
Customer: {f['customer_name']} | Go-live: {f['go_live']} | License: {f['license']}
Goals: {', '.join(f['goals']) if f['goals'] else 'Not specified'}
Measurement period for all metrics: {f['period_label']}
Total cases processed: {f['total_cases']:,}

OPERATIONAL METRICS:
- FRT: {f['frt_base']} hrs ({f['frt_ms']}) → {f['frt_cur']} hrs ({f['frt_me']}) = {f['frt_pct']}% improvement. FRT = time from case creation to first non-bot agent response.
- Escalation rate: {f['esc_base']}% ({f['period_start']}) → {f['esc_cur']}% ({f['esc_mon']}). Benchmark: {f['benchmark']}%. Status: {f['esc_vs']} benchmark.
- LTE predictions ({f['lte_per']}): {f['lte_pred']:,} flagged, {f['lte_act']:,} actually escalated, {f['lte_prev']:,} intercepted.
- Reassignment rate: {f['re_base']}% (go-live) → {f['re_cur']}% ({f['re_mon']}). Target: <3%. Reassignment = case sent to more than one agent.
- Sentiment: {f['s_base']}/100 ({f['period_start']}) → {f['s_cur']}/100 ({f['s_mon']}) = {f['s_dir']}. Across {f['s_cases']:,} interactions. Healthy: 65-75/100.
- Account health: {f['h_cur']}/100 ({f['h_label']}) as of {f['h_mon']}. Peak was {f['h_peak']}/100.
- ICA: {'Active — ' + str(f['ica_auto']) + ' cases auto-routed (' + str(f['ica_pct']) + '% auto-assignment rate) since go-live' if f['ica_on'] else 'Not deployed — manual case assignment in use'}
- Alerts fired: {f['al_tot']:,} ({f['al_per']})
- AI summaries: {f['su_tot']:,} total generated
- Agent platform actions (signal acknowledgements etc): {f['act_tot']:,} total

PLATFORM ADOPTION (Pendo):
{pendo_block}

Write the brief as JSON with these exact keys. Each value is a plain string, no markdown:
{{
  "account_status": "Single sentence: current health and the one most important data point. Include period.",
  "value_delivered": "Measurable improvements SupportLogic has driven since go-live. Lead with biggest win. Every metric must include period and comparison.",
  "platform_adoption": "How agents engage with SupportLogic — user counts, adoption tiers, top module. Include period. Note if Pendo unavailable.",
  "working_well": "2-3 specific strengths with data and periods. Say what makes each noteworthy vs benchmark.",
  "watch_items": "2-3 specific concerns with data. State the risk clearly. Do not soften.",
  "renewal_outlook": "One honest sentence on renewal readiness. Name the single factor that will determine the outcome."
}}
Return ONLY the JSON. No markdown, no preamble."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json",
                     "x-api-key": _get_api_key(),
                     "anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":1200,
                  "messages":[{"role":"user","content":prompt}]},
            timeout=45,
        )
        text = resp.json()["content"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("\n",1)[1].rsplit("```",1)[0]
        sections = json.loads(text)
    except Exception as e:
        sections = {k:"—" for k in ["account_status","value_delivered",
                                     "platform_adoption","working_well",
                                     "watch_items","renewal_outlook"]}
        sections["account_status"] = f"Brief generation failed: {e}"

    return {**sections,
            "generated_at": datetime.now().strftime("%d %b %Y, %H:%M"),
            "facts": f}


def is_available() -> bool:
    return _has_api_key()
