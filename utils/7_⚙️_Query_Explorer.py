"""pages/7 — Query Explorer: browse, run, download any registered query."""
import streamlit as st
from utils.snowflake_conn import run_query
from queries.registry import QUERIES, QUERY_CATALOG

st.set_page_config(page_title="Query Explorer", layout="wide")
st.title("⚙️ Query explorer")
from utils.page_init import init_page
schema, customer_name, customer = init_page("Query Explorer")

st.caption(f"Running against: `PIPE_DATABASE.{schema}` ({customer_name})")
tab1, tab2 = st.tabs(["Browse & run queries", "How to add a metric"])

with tab1:
    agents   = ["All"] + sorted(set(q["agent"] for q in QUERY_CATALOG))
    tabs_f   = ["All"] + sorted(set(q["tab"]   for q in QUERY_CATALOG))
    statuses = ["All","stable","slow"]
    cf1,cf2,cf3 = st.columns(3)
    fa = cf1.selectbox("Agent",  agents)
    ft = cf2.selectbox("Tab",    tabs_f)
    fs = cf3.selectbox("Status", statuses)
    catalog = [q for q in QUERY_CATALOG
               if (fa=="All" or q["agent"]==fa)
               and (ft=="All" or q["tab"]==ft)
               and (fs=="All" or q["status"]==fs)]
    for entry in catalog:
        badge = "🟢" if entry["status"]=="stable" else "🟡"
        with st.expander(f"{badge} **{entry['name']}** — {entry['agent']} · {entry['tab']}"):
            st.markdown(f"**Tables:** `{'`, `'.join(entry['tables'])}`")
            st.code(QUERIES[entry["id"]].strip(), language="sql")
            if entry["status"]=="slow":
                st.warning("Heavy query — may take 30–60s on cold warehouse.", icon="⏱️")
            if st.button(f"▶ Run", key=f"run_{entry['id']}"):
                with st.spinner(f"Running..."):
                    df = run_query(QUERIES[entry["id"]], schema)
                if not df.empty:
                    st.success(f"✓ {len(df)} rows")
                    st.dataframe(df, use_container_width=True)
                    st.download_button("⬇ CSV", df.to_csv(index=False),
                                       f"{customer_name}_{entry['id']}.csv","text/csv",
                                       key=f"dl_{entry['id']}")
                else:
                    st.warning("No rows returned.")

with tab2:
    st.markdown("""
### Adding a new metric — 3 steps

**Step 1** — Add SQL to `queries/registry.py`:
```python
"my_metric": \"\"\"
    SELECT TO_CHAR(DATE_TRUNC('MONTH', sl_created_at),'YYYY-MM') AS month,
        COUNT(*) AS my_count
    FROM PIPE_DATABASE.<SCHEMA>.case_summary
    WHERE sl_created_at >= '2025-06-01'
    GROUP BY 1 ORDER BY 1
\"\"\",
```

**Step 2** — Add metadata to `QUERY_CATALOG` in the same file:
```python
{"id":"my_metric","name":"My metric monthly","tab":"Routing","agent":"Routing Agent",
 "tables":["CASE_SUMMARY"],"status":"stable"},
```

**Step 3** — Add the chart to the relevant page:
```python
df = run_query(QUERIES["my_metric"], schema)
if not df.empty:
    st.markdown("**My metric title**")
    st.plotly_chart(line_chart(df, x="month",
        y_cols=[{"col":"my_count","name":"My metric","color":COLORS["teal"]}]),
        use_container_width=True)
```

Available chart types: `line_chart`, `area_chart`, `bar_chart`, `combo_chart`,
`stacked_bar`, `donut_chart`, `gauge_chart`, `bubble_chart`, `step_line`
""")
