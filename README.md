# SupportLogic Account Performance Dashboard

Internal Streamlit dashboard for CSM, Sales, and Leadership to monitor account health, ROI metrics, and renewal readiness — live against Snowflake.

---

## What it shows

| Page | Content |
|---|---|
| 📋 Account Snapshot | Health score, FRT, escalation rate, sentiment — open-it-and-know view |
| 🛡️ Escalation Intelligence | LTE predictions vs actuals, prevented escalations, rate vs benchmark |
| 😊 Sentiment | Sentiment score trend, need-attention score, alerts consumption |
| 🔀 Routing & Efficiency | ICA auto/manual split, reassignment rate, FRT by priority, workload |
| 📈 ROI Summary | Renewal-ready one-pager anchored to go-live date |
| ⚙️ Query Explorer | Browse, run, and download any registered query ad-hoc |

---

## Local setup (5 minutes)

### Prerequisites
- Python 3.12
- RSA private key for `CLAUDE_SERVICE_USER` at `/Users/dilipkumar/Downloads/rsa_key.p8`
- Access to `PIPE_DATABASE` on Snowflake

### Steps

```bash
# 1. Clone / copy the project
cd sl_dashboard

# 2. Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your Snowflake account identifier

# 5. Run
streamlit run Home.py
```

Open http://localhost:8501 in your browser.

---

## Deployment options

### Option A — Streamlit Community Cloud (free, recommended for internal sharing)

1. Push this repo to a **private** GitHub repo inside the SupportLogic org
2. Go to https://share.streamlit.io → New app → point to `Home.py`
3. Under **Advanced settings → Secrets**, paste the contents of `.streamlit/secrets.toml.example` filled in with real values
4. For the RSA key: paste the full PEM content into `private_key_str` in the secrets UI (multi-line strings work)
5. Share the generated URL with the team — add Google SSO restriction in Streamlit Cloud settings

### Option B — Internal server (Railway / Render / EC2)

```bash
# Dockerfile-free deploy on Railway or Render:
# Start command: streamlit run Home.py --server.port $PORT --server.address 0.0.0.0
# Set environment variables in the platform dashboard instead of .env
```

### Option C — Run locally and share via ngrok (quickest for demos)

```bash
brew install ngrok
streamlit run Home.py &
ngrok http 8501
# Share the ngrok URL — valid for the session
```

---

## Adding a new customer

Open `utils/customers.py` and add an entry:

```python
"CustomerName": {
    "schema":    "CUSTOMERNAME_PUBLIC",
    "go_live":   "2024-06-01",          # from Slack #general go-live notice
    "csm":       "Your Name",
    "sa":        "SA Name",
    "license":   "UBP",
    "goals":     ["Goal 1", "Goal 2"],
    "notes":     "Any relevant context",
    "benchmark_escalation_pct": 2.0,
},
```

The customer appears in the sidebar dropdown immediately — no other changes needed.

---

## Adding a new metric

See the **Query Explorer → How to add a new metric** tab in the running app, or follow these steps:

1. Add SQL to `queries/registry.py` → `QUERIES` dict (use `<SCHEMA>` as placeholder)
2. Add metadata to `QUERY_CATALOG` in the same file
3. Add the chart to the relevant page file

Results are auto-cached for 1 hour, auto-available in Query Explorer, and downloadable as CSV.

---

## Architecture

```
sl_dashboard/
├── Home.py                          # Entry point, sidebar, customer picker
├── pages/
│   ├── 1_📋_Account_Snapshot.py
│   ├── 2_🛡️_Escalation_Intelligence.py
│   ├── 3_😊_Sentiment.py
│   ├── 4_🔀_Routing_&_Efficiency.py
│   ├── 5_📈_ROI_Summary.py
│   └── 6_⚙️_Query_Explorer.py
├── queries/
│   └── registry.py                  # All SQL + catalog metadata
├── utils/
│   ├── snowflake_conn.py            # Connection, auth, caching
│   ├── customers.py                 # Customer registry
│   └── charts.py                   # Shared Plotly helpers
├── assets/                          # Logo, images
├── requirements.txt
├── .env.example
├── .gitignore
└── .streamlit/
    └── secrets.toml.example
```

---

## Security notes

- **Never commit** `.env`, `rsa_key.p8`, or `.streamlit/secrets.toml`
- All three are in `.gitignore`
- On Streamlit Cloud, secrets are stored encrypted in the platform — never in the repo
- The service user `CLAUDE_SERVICE_USER` has read-only access scoped to `PIPE_DATABASE`

---

## Warehouse notes

The app uses `SNOWFLAKE_LEARNING_WH` by default. If the warehouse is suspended, the connection utility calls `ALTER WAREHOUSE ... RESUME IF SUSPENDED` automatically before each query.

For production use, consider switching to `BI_REPORT_WH` (requires RESUME privilege for the service user — raise with SRE) or setting `AUTO_RESUME = TRUE` on the warehouse.

Heavy queries (follow-up response time, ICA assignment split) may take 30–60s on a cold warehouse. These are marked `"status": "slow"` in the catalog and shown with a warning in the Query Explorer.
# Tue Aug 18 16:03:25 IST 2026
