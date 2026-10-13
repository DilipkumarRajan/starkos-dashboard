#!/usr/bin/env python3.12
import sys, os, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.snowflake_conn import run_query

if len(sys.argv) < 3:
    print("Usage: python3.12 scripts/add_customer.py \"Customer Name\" \"SCHEMA_PUBLIC\"")
    sys.exit(1)

CUSTOMER_NAME = sys.argv[1]
SCHEMA        = sys.argv[2]
name          = CUSTOMER_NAME.strip()

print(f"\n{chr(61)*60}\n  STARKos Onboarding: {CUSTOMER_NAME}\n{chr(61)*60}\n")

# 1. Snowflake
print("1. Checking Snowflake...")
sf_ok, case_count, first_case = False, 0, None
try:
    df = run_query(f"""
        SELECT COUNT(*) AS cnt, MIN(sl_created_at)::DATE AS first_case
        FROM PIPE_DATABASE.{SCHEMA}.case_summary
        WHERE sl_is_bot = FALSE AND is_deleted = FALSE
    """, SCHEMA)
    case_count = int(df["cnt"].iloc[0])
    first_case = str(df["first_case"].iloc[0])[:7]
    sf_ok = True
    print(f"   OK: {case_count:,} cases from {first_case}")
except Exception as e:
    print(f"   FAIL: {e}")

# 2. Pendo
print("\n2. Checking Pendo...")
key = os.getenv("PENDO_API_KEY", "")
H   = {"x-pendo-integration-key": key, "Content-Type": "application/json"}
variants = set([
    name, name.lower(), name.upper(), name.title(),
    name.replace(" ",""), name.replace(" ","").lower(),
    name.replace(" ","-"), name.replace(" ","-").lower(),
    name.replace(" ","_"), name.replace(" ","_").lower(),
])
pendo_ids = []
for v in sorted(variants):
    r = requests.get(f"https://app.pendo.io/api/v1/account/{v}", headers=H, timeout=10)
    if r.status_code == 200:
        pendo_ids.append(v)
        print(f"   OK: {v}")
if not pendo_ids:
    print("   FAIL: No Pendo account found")
    pendo_ids = [name.lower()]

# 3. Freshdesk
print("\n3. Checking Freshdesk...")
fd_key = os.getenv("FRESHDESK_API_KEY", "")
r = requests.get(
    f"https://supportlogic.freshdesk.com/api/v2/companies/autocomplete?name={name}",
    auth=(fd_key, "X"), timeout=10)
fd_name = None
if r.status_code == 200:
    companies = r.json().get("companies", [])
    if companies:
        fd_name = companies[0]["name"]
        print(f"   OK: {fd_name}")
    else:
        print("   FAIL: Not found")

# Output
gcp  = name.lower().replace(" ","")
live = f"{first_case}-01" if first_case else "None"
sep  = chr(61)*60

print(f"\n{sep}\nPASTE INTO utils/customers.py:\n{sep}")
print(f"""
    "{CUSTOMER_NAME}": {{
        "schema":    "{SCHEMA}",
        "pendo_id":  "{pendo_ids[0]}",
        "pendo_ids": {pendo_ids},
        "go_live":   "{live}",
        "csm":       "",
        "sa":        "",
        "license":   "CoreSX",
        "goals":     [],
        "notes":     "{case_count:,} cases. Data from {first_case}.",
        "gcp_hostname": "{gcp}",
        "benchmark_escalation_pct": 2.0,
    }},
""")

fd_search = fd_name.split()[0] if fd_name else name
print(f"{sep}\nPASTE INTO utils/freshdesk_conn.py CUSTOMER_SEARCH_MAP:\n{sep}")
print(f'\n    "{CUSTOMER_NAME}": "{fd_search}",\n')

if not sf_ok:
    print(f"DevOps grant needed:")
    print(f"  GRANT SELECT ON ALL TABLES IN SCHEMA PIPE_DATABASE.{SCHEMA} TO ROLE CLAUDE_READONLY;")
    print(f"  GRANT SELECT ON FUTURE TABLES IN SCHEMA PIPE_DATABASE.{SCHEMA} TO ROLE CLAUDE_READONLY;")
