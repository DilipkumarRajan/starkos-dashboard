# ════════════════════════════════════════════════════════════════════════════
# PORTFOLIO INTELLIGENCE TAB — Executive Dashboard
# Wire in Home.py as: elif tab == 11:
# Add to TABS list as: ("🌐", "Portfolio")
# ════════════════════════════════════════════════════════════════════════════

elif tab == 11:
    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px
    from utils.portfolio import load_portfolio, get_portfolio_kpis, fmt_arr

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner("Loading portfolio intelligence..."):
        df_all = load_portfolio()

    if df_all.empty:
        st.error("Could not load portfolio data. Ensure data/accounts.xlsx exists.", icon="❌")
        st.stop()

    kpis = get_portfolio_kpis(df_all)

    # Helper: renewal badge
    def renewal_badge(days):
        if days is None or pd.isna(days): return ""
        try:
            d = int(days)
            if d < 0:    return "🔴"
            if d <= 90:  return "🟡"
            if d <= 180: return "🟠"
            return ""
        except: return ""

    # Card builder
    def account_pill(name, arr, badge="", extra=""):
        arr_str = fmt_arr(arr) if arr and not pd.isna(arr) else "—"
        return (
            f"<div style='display:inline-flex;align-items:center;gap:6px;"
            f"background:#1c2128;border:0.5px solid #30363d;border-radius:20px;"
            f"padding:4px 10px;margin:2px;font-size:11px'>"
            f"<span style='color:#e6edf3;font-weight:500'>{badge}{name}</span>"
            f"<span style='color:#1D9E75;font-weight:600'>{arr_str}</span>"
            f"{('<span style=\"color:#8b949e\">·</span><span style=\"color:#8b949e;font-size:10px\">' + extra + '</span>') if extra else ''}"
            f"</div>"
        )

    def section_header(icon, title, subtitle=""):
        st.markdown(f"""
<div style='margin-bottom:12px;margin-top:4px'>
  <span style='font-size:16px;font-weight:700;color:#e6edf3'>{icon} {title}</span>
  {'<span style="font-size:11px;color:#8b949e;margin-left:8px">' + subtitle + '</span>' if subtitle else ''}
</div>""", unsafe_allow_html=True)

    def stat_box(label, value, color="#1D9E75", sublabel=""):
        return (
            f"<div style='background:#161b22;border:0.5px solid {color};"
            f"border-radius:10px;padding:14px 16px;text-align:center'>"
            f"<div style='font-size:22px;font-weight:700;color:{color}'>{value}</div>"
            f"<div style='font-size:10px;color:#8b949e;margin-top:2px'>{label}</div>"
            f"{'<div style=\"font-size:9px;color:#484f58;margin-top:2px\">' + sublabel + '</div>' if sublabel else ''}"
            f"</div>"
        )

    # ── Page title ────────────────────────────────────────────────────────────
    col_title, col_refresh = st.columns([5,1])
    with col_title:
        st.markdown("""
<div style='margin-bottom:8px'>
  <div style='font-size:22px;font-weight:700;color:#e6edf3'>🌐 Portfolio Intelligence</div>
  <div style='font-size:11px;color:#8b949e'>
    Executive view across all accounts · No Snowflake queries · Cached 5 min
  </div>
</div>""", unsafe_allow_html=True)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — PORTFOLIO AT A GLANCE
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
    border-radius:12px;padding:20px 24px;margin-bottom:16px'>""",
    unsafe_allow_html=True)

    section_header("📊", "Portfolio at a glance",
                   f"{kpis['total_accounts']} accounts · as of today")

    g1,g2,g3,g4,g5,g6 = st.columns(6)
    g1.markdown(stat_box("Total accounts",  kpis["total_accounts"],   "#e6edf3"), unsafe_allow_html=True)
    g2.markdown(stat_box("Total ARR",       fmt_arr(kpis["total_arr"]), "#1D9E75"), unsafe_allow_html=True)
    g3.markdown(stat_box("Avg ARR",         fmt_arr(kpis["avg_arr"]),   "#185FA5"), unsafe_allow_html=True)
    g4.markdown(stat_box("Median ARR",      fmt_arr(kpis["median_arr"]),"#534AB7"), unsafe_allow_html=True)
    g5.markdown(stat_box("$500K+ accounts", kpis["accounts_500k_plus"], "#BA7517",
                         f"{round(kpis['accounts_500k_plus']/kpis['total_accounts']*100)}% of portfolio"), unsafe_allow_html=True)
    g6.markdown(stat_box("Renewals in 90d", kpis["renewal_90d"],
                         "#E24B4A" if kpis["renewal_90d"] > 0 else "#444",
                         "need attention" if kpis["renewal_90d"] > 0 else "no urgency"), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — TOP 10 BY ARR + ARR DISTRIBUTION (side by side)
    # ════════════════════════════════════════════════════════════════════════
    col_top, col_dist = st.columns([1, 1])

    with col_top:
        st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
        border-radius:12px;padding:20px 24px;height:100%'>""", unsafe_allow_html=True)
        section_header("🏆", "Top 10 accounts by ARR")

        top10 = df_all[df_all["arr"].notna()].sort_values("arr", ascending=False).head(10)
        max_arr = top10["arr"].max()

        for rank, (_, row) in enumerate(top10.iterrows(), 1):
            arr   = row.get("arr", 0) or 0
            name  = str(row.get("name", "—"))[:22]
            pct   = round(arr / max_arr * 100)
            rdys  = row.get("days_to_renewal")
            badge = renewal_badge(rdys)
            crm   = str(row.get("crm_type", ""))

            rank_color = "#FFD700" if rank == 1 else "#C0C0C0" if rank == 2 else "#CD7F32" if rank == 3 else "#8b949e"
            st.markdown(f"""
<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px'>
  <span style='color:{rank_color};font-size:12px;font-weight:700;width:20px'>{rank}</span>
  <div style='flex:1'>
    <div style='display:flex;justify-content:space-between;margin-bottom:2px'>
      <span style='font-size:12px;color:#e6edf3;font-weight:500'>{badge}{name}</span>
      <span style='font-size:12px;color:#1D9E75;font-weight:600'>{fmt_arr(arr)}</span>
    </div>
    <div style='background:#21262d;border-radius:4px;height:4px'>
      <div style='background:linear-gradient(90deg,#1D9E75,#185FA5);
           border-radius:4px;height:4px;width:{pct}%'></div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_dist:
        st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
        border-radius:12px;padding:20px 24px;height:100%'>""", unsafe_allow_html=True)
        section_header("💰", "ARR distribution")

        seg_order  = ["$1M+", "$500K–$1M", "$250K–$500K", "<$250K"]
        seg_colors_list = ["#1D9E75", "#185FA5", "#534AB7", "#BA7517"]
        seg_counts = []
        seg_arrs   = []
        total_arr  = df_all["arr"].sum()

        for seg in seg_order:
            seg_df = df_all[df_all["arr_segment"] == seg]
            seg_counts.append(len(seg_df))
            seg_arrs.append(seg_df["arr"].sum())

        for i, (seg, color, n, arr_s) in enumerate(zip(seg_order, seg_colors_list, seg_counts, seg_arrs)):
            pct_n   = round(n / kpis["total_accounts"] * 100)
            pct_arr = round(arr_s / total_arr * 100) if total_arr else 0
            accounts_in_seg = df_all[df_all["arr_segment"] == seg]["name"].tolist()
            names_str = " · ".join(accounts_in_seg[:4])
            if len(accounts_in_seg) > 4:
                names_str += f" +{len(accounts_in_seg)-4} more"

            st.markdown(f"""
<div style='background:#161b22;border:0.5px solid {color};border-radius:8px;
     padding:10px 14px;margin-bottom:8px'>
  <div style='display:flex;justify-content:space-between;align-items:center'>
    <span style='font-size:12px;font-weight:700;color:{color}'>{seg}</span>
    <div style='text-align:right'>
      <span style='font-size:14px;font-weight:700;color:#e6edf3'>{n} accounts</span>
      <span style='font-size:10px;color:#8b949e;margin-left:6px'>{fmt_arr(arr_s)} · {pct_arr}% of ARR</span>
    </div>
  </div>
  <div style='font-size:10px;color:#484f58;margin-top:4px'>{names_str}</div>
</div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — CRM LANDSCAPE + MODULE ADOPTION (side by side)
    # ════════════════════════════════════════════════════════════════════════
    col_crm, col_mod = st.columns([1, 1])

    with col_crm:
        st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
        border-radius:12px;padding:20px 24px;height:100%'>""", unsafe_allow_html=True)
        section_header("🔧", "CRM landscape",
                       "how customers connect to SupportLogic")

        crm_data = {
            "Salesforce": ("#185FA5", "🔵"),
            "Zendesk":    ("#1D9E75", "🟢"),
            "Freshdesk":  ("#534AB7", "🟣"),
            "Other":      ("#BA7517", "🟡"),
            "Unknown":    ("#444",    "⚪"),
        }

        for crm, (color, emoji) in crm_data.items():
            crm_df = df_all[df_all["crm_type"] == crm]
            n = len(crm_df)
            if n == 0: continue
            arr_total = crm_df["arr"].sum()
            pct = round(n / kpis["total_accounts"] * 100)
            names = " · ".join(crm_df.sort_values("arr", ascending=False)["name"].head(4).tolist())
            if n > 4: names += f" +{n-4} more"

            st.markdown(f"""
<div style='background:#161b22;border:0.5px solid {color};border-radius:8px;
     padding:12px 16px;margin-bottom:8px'>
  <div style='display:flex;justify-content:space-between;align-items:center'>
    <div style='display:flex;align-items:center;gap:8px'>
      <span style='font-size:16px'>{emoji}</span>
      <span style='font-size:13px;font-weight:700;color:#e6edf3'>{crm}</span>
    </div>
    <div style='text-align:right'>
      <span style='font-size:14px;font-weight:700;color:{color}'>{n}</span>
      <span style='font-size:10px;color:#8b949e'> accounts · {fmt_arr(arr_total)}</span>
    </div>
  </div>
  <div style='margin-top:6px'>
    <div style='background:#21262d;border-radius:4px;height:3px'>
      <div style='background:{color};border-radius:4px;height:3px;width:{pct}%'></div>
    </div>
  </div>
  <div style='font-size:10px;color:#484f58;margin-top:6px'>{names}</div>
</div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_mod:
        st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
        border-radius:12px;padding:20px 24px;height:100%'>""", unsafe_allow_html=True)
        section_header("🔬", "Module adoption",
                       "how many accounts have each module live")

        modules = [
            ("Core SX",    "core_live",    "#1D9E75", "Foundation module"),
            ("Assign/ICA", "assign_live",  "#185FA5", "Intelligent case routing"),
            ("Assist",     "assist_live",  "#534AB7", "AI knowledge assist"),
            ("Elevate",    "elevate_live", "#E24B4A", "QA & coaching"),
            ("Resolve",    "resolve_live", "#0F6E56", "xFind knowledge search"),
            ("Expand",     "expand_live",  "#BA7517", "Account insights"),
        ]

        for label, col_m, color, desc in modules:
            n     = df_all[col_m].sum() if col_m in df_all.columns else 0
            total = kpis["total_accounts"]
            pct   = round(n / total * 100) if total else 0
            names = " · ".join(
                df_all[df_all.get(col_m, pd.Series([False]*len(df_all))) == True]
                .sort_values("arr", ascending=False)["name"].head(3).tolist()
            )

            st.markdown(f"""
<div style='margin-bottom:10px'>
  <div style='display:flex;justify-content:space-between;margin-bottom:3px'>
    <div>
      <span style='font-size:12px;font-weight:600;color:#e6edf3'>{label}</span>
      <span style='font-size:10px;color:#8b949e;margin-left:6px'>{desc}</span>
    </div>
    <span style='font-size:12px;font-weight:700;color:{color}'>{n}/{total} · {pct}%</span>
  </div>
  <div style='background:#21262d;border-radius:4px;height:6px'>
    <div style='background:{color};border-radius:4px;height:6px;width:{pct}%'></div>
  </div>
  <div style='font-size:9px;color:#484f58;margin-top:2px'>{names}</div>
</div>""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4 — RENEWAL RADAR
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
    border-radius:12px;padding:20px 24px;margin-bottom:12px'>""",
    unsafe_allow_html=True)
    section_header("📅", "Renewal radar",
                   "accounts requiring attention in the next 180 days")

    if "days_to_renewal" in df_all.columns:
        overdue = df_all[df_all["days_to_renewal"] < 0].sort_values("days_to_renewal")
        next30  = df_all[(df_all["days_to_renewal"] >= 0) & (df_all["days_to_renewal"] <= 30)].sort_values("days_to_renewal")
        next90  = df_all[(df_all["days_to_renewal"] > 30)  & (df_all["days_to_renewal"] <= 90)].sort_values("days_to_renewal")
        next180 = df_all[(df_all["days_to_renewal"] > 90)  & (df_all["days_to_renewal"] <= 180)].sort_values("days_to_renewal")

        rr1, rr2, rr3, rr4 = st.columns(4)

        for col_r, label, bucket, color in [
            (rr1, "🔴 Overdue",     overdue, "#E24B4A"),
            (rr2, "🟡 Next 30 days",next30,  "#E24B4A"),
            (rr3, "🟠 30–90 days",  next90,  "#BA7517"),
            (rr4, "🟢 90–180 days", next180, "#1D9E75"),
        ]:
            with col_r:
                st.markdown(f"<div style='font-size:11px;font-weight:600;color:{color};margin-bottom:6px'>{label} ({len(bucket)})</div>", unsafe_allow_html=True)
                if bucket.empty:
                    st.markdown("<div style='font-size:10px;color:#484f58'>None</div>", unsafe_allow_html=True)
                else:
                    for _, r in bucket.iterrows():
                        days = int(r.get("days_to_renewal", 0))
                        days_str = f"{abs(days)}d overdue" if days < 0 else f"{days}d"
                        st.markdown(
                            f"<div style='background:#161b22;border:0.5px solid {color};"
                            f"border-radius:6px;padding:6px 10px;margin-bottom:4px'>"
                            f"<div style='font-size:11px;font-weight:500;color:#e6edf3'>{str(r.get('name',''))[:20]}</div>"
                            f"<div style='font-size:10px;color:{color}'>{days_str}</div>"
                            f"<div style='font-size:10px;color:#8b949e'>{fmt_arr(r.get('arr'))}</div>"
                            f"</div>", unsafe_allow_html=True)
    else:
        st.info("Renewal date data not available.")

    st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 5 — CUSTOMER CLUSTERS (analytical groupings)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
    border-radius:12px;padding:20px 24px;margin-bottom:12px'>""",
    unsafe_allow_html=True)
    section_header("🧩", "Customer clusters",
                   "accounts grouped by similarity — who looks like whom?")

    clusters = [
        {
            "name":   "Enterprise power users",
            "desc":   "$500K+ ARR with 3+ modules live",
            "color":  "#1D9E75",
            "filter": lambda r: (r.get("arr") or 0) >= 500_000 and (r.get("live_module_count") or 0) >= 3,
        },
        {
            "name":   "High-value, low adoption",
            "desc":   "$250K+ ARR with fewer than 2 modules live",
            "color":  "#BA7517",
            "filter": lambda r: (r.get("arr") or 0) >= 250_000 and (r.get("live_module_count") or 0) < 2,
        },
        {
            "name":   "ICA-led accounts",
            "desc":   "Assign/ICA is their primary active module",
            "color":  "#185FA5",
            "filter": lambda r: r.get("assign_live") == True,
        },
        {
            "name":   "AI-ready accounts",
            "desc":   "Resolve or Assist live (knowledge + response AI)",
            "color":  "#534AB7",
            "filter": lambda r: r.get("resolve_live") == True or r.get("assist_live") == True,
        },
        {
            "name":   "Elevate / QA accounts",
            "desc":   "Elevate live (QA and coaching enabled)",
            "color":  "#E24B4A",
            "filter": lambda r: r.get("elevate_live") == True,
        },
        {
            "name":   "CoreSX only",
            "desc":   "Live on Core with no additional modules",
            "color":  "#484f58",
            "filter": lambda r: r.get("core_live") == True and (r.get("live_module_count") or 0) == 1,
        },
    ]

    cl_cols = st.columns(3)
    for i, cluster in enumerate(clusters):
        try:
            cluster_df = df_all[df_all.apply(cluster["filter"], axis=1)]
        except: cluster_df = pd.DataFrame()
        n = len(cluster_df)
        color = cluster["color"]
        names_html = "".join([
            f"<span style='background:#21262d;border-radius:12px;padding:2px 8px;"
            f"margin:2px;font-size:10px;color:#e6edf3;display:inline-block'>"
            f"{str(r.get('name',''))[:18]}</span>"
            for _, r in cluster_df.sort_values("arr", ascending=False, na_position="last").head(6).iterrows()
        ])
        if n > 6:
            names_html += f"<span style='font-size:10px;color:#484f58'> +{n-6} more</span>"

        with cl_cols[i % 3]:
            st.markdown(f"""
<div style='background:#161b22;border:0.5px solid {color};border-radius:10px;
     padding:14px 16px;margin-bottom:10px;min-height:120px'>
  <div style='font-size:12px;font-weight:700;color:{color};margin-bottom:2px'>{cluster["name"]}</div>
  <div style='font-size:10px;color:#8b949e;margin-bottom:8px'>{cluster["desc"]}</div>
  <div style='font-size:18px;font-weight:700;color:#e6edf3;margin-bottom:6px'>{n} accounts</div>
  <div style='line-height:1.8'>{names_html if names_html else '<span style="font-size:10px;color:#484f58">None</span>'}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 6 — STRATEGIC OPPORTUNITIES
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
    border-radius:12px;padding:20px 24px;margin-bottom:12px'>""",
    unsafe_allow_html=True)
    section_header("🎯", "Strategic opportunities",
                   "where to focus for expansion and retention")

    op1, op2, op3 = st.columns(3)

    # ICA upsell
    ica_upsell = df_all[
        (df_all["arr"] >= 200_000) &
        (~df_all.get("assign_live", pd.Series([False]*len(df_all))).fillna(False))
    ].sort_values("arr", ascending=False, na_position="last")

    with op1:
        st.markdown(f"""
<div style='background:#0A1931;border:0.5px solid #185FA5;border-radius:10px;padding:14px'>
  <div style='font-size:12px;font-weight:700;color:#185FA5;margin-bottom:4px'>🔀 ICA upsell</div>
  <div style='font-size:10px;color:#8b949e;margin-bottom:8px'>$200K+ ARR without ICA live · {len(ica_upsell)} accounts</div>""",
        unsafe_allow_html=True)
        for _, r in ica_upsell.head(5).iterrows():
            st.markdown(
                f"<div style='font-size:11px;color:#e6edf3;padding:3px 0;border-bottom:0.5px solid #21262d'>"
                f"<b>{str(r.get('name',''))[:20]}</b>"
                f"<span style='float:right;color:#185FA5'>{fmt_arr(r.get('arr'))}</span></div>",
                unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Resolve upsell
    res_upsell = df_all[
        (df_all["arr"] >= 200_000) &
        (~df_all.get("resolve_live", pd.Series([False]*len(df_all))).fillna(False))
    ].sort_values("arr", ascending=False, na_position="last")

    with op2:
        st.markdown(f"""
<div style='background:#0a1a14;border:0.5px solid #0F6E56;border-radius:10px;padding:14px'>
  <div style='font-size:12px;font-weight:700;color:#0F6E56;margin-bottom:4px'>📚 Resolve upsell</div>
  <div style='font-size:10px;color:#8b949e;margin-bottom:8px'>$200K+ ARR without Resolve live · {len(res_upsell)} accounts</div>""",
        unsafe_allow_html=True)
        for _, r in res_upsell.head(5).iterrows():
            st.markdown(
                f"<div style='font-size:11px;color:#e6edf3;padding:3px 0;border-bottom:0.5px solid #21262d'>"
                f"<b>{str(r.get('name',''))[:20]}</b>"
                f"<span style='float:right;color:#0F6E56'>{fmt_arr(r.get('arr'))}</span></div>",
                unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Elevate upsell
    elev_upsell = df_all[
        (df_all["arr"] >= 200_000) &
        (~df_all.get("elevate_live", pd.Series([False]*len(df_all))).fillna(False))
    ].sort_values("arr", ascending=False, na_position="last")

    with op3:
        st.markdown(f"""
<div style='background:#1a0a0a;border:0.5px solid #E24B4A;border-radius:10px;padding:14px'>
  <div style='font-size:12px;font-weight:700;color:#E24B4A;margin-bottom:4px'>⭐ Elevate upsell</div>
  <div style='font-size:10px;color:#8b949e;margin-bottom:8px'>$200K+ ARR without Elevate live · {len(elev_upsell)} accounts</div>""",
        unsafe_allow_html=True)
        for _, r in elev_upsell.head(5).iterrows():
            st.markdown(
                f"<div style='font-size:11px;color:#e6edf3;padding:3px 0;border-bottom:0.5px solid #21262d'>"
                f"<b>{str(r.get('name',''))[:20]}</b>"
                f"<span style='float:right;color:#E24B4A'>{fmt_arr(r.get('arr'))}</span></div>",
                unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 7 — CSM / TSE PORTFOLIO BREAKDOWN
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("""<div style='background:#0d1117;border:0.5px solid #21262d;
    border-radius:12px;padding:20px 24px;margin-bottom:12px'>""",
    unsafe_allow_html=True)
    section_header("👤", "Team portfolio breakdown",
                   "accounts and ARR owned per CSM / TSE")

    csm_col = "csm" if "csm" in df_all.columns else "csm_sl"
    tse_col = "tse" if "tse" in df_all.columns else "tse_sl"

    tb1, tb2 = st.columns(2)

    for col_t, field, label in [(tb1, csm_col, "CSM"), (tb2, tse_col, "TSE")]:
        with col_t:
            st.markdown(f"**By {label}**")
            if field in df_all.columns:
                grp = (df_all[df_all[field].notna() & (df_all[field].str.strip() != "")]
                       .groupby(field)
                       .agg(accounts=("name","count"), total_arr=("arr","sum"))
                       .sort_values("total_arr", ascending=False)
                       .reset_index())
                for _, r in grp.iterrows():
                    pct = round(r["total_arr"] / df_all["arr"].sum() * 100) if df_all["arr"].sum() else 0
                    st.markdown(f"""
<div style='display:flex;justify-content:space-between;align-items:center;
     padding:6px 0;border-bottom:0.5px solid #21262d'>
  <span style='font-size:12px;color:#e6edf3'>{str(r[field])[:25]}</span>
  <div style='text-align:right'>
    <span style='font-size:11px;color:#1D9E75;font-weight:600'>{fmt_arr(r["total_arr"])}</span>
    <span style='font-size:10px;color:#8b949e;margin-left:6px'>{int(r["accounts"])} accts · {pct}%</span>
  </div>
</div>""", unsafe_allow_html=True)
            else:
                st.info(f"No {label} data available.")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Footer ────────────────────────────────────────────────────────────────
    st.caption(
        f"Portfolio Intelligence · {kpis['total_accounts']} accounts · "
        f"Source: accounts.xlsx → Google Sheets (when public) · "
        f"Zero Snowflake queries · Cached 5 min · "
        f"{pd.Timestamp.now().strftime('%d %b %Y %H:%M')}"
    )
