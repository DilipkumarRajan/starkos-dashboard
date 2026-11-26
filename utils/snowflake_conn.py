"""
utils/snowflake_conn.py
Handles Snowflake connection with RSA key-pair auth.
Supports both local (.env / key file) and Streamlit Cloud (secrets.toml PEM string).
"""

import os
import pathlib
import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

# ── Always load .env relative to the project root (not the CWD of each page)
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")


def _get_config(key: str, env_var: str, default: str = "") -> str:
    """Read from Streamlit secrets first, fall back to .env / environment."""
    try:
        val = st.secrets["snowflake"].get(key, "")
        if val:
            return val
    except (KeyError, AttributeError, FileNotFoundError):
        pass
    return os.getenv(env_var, default)


def _load_private_key() -> bytes:
    """
    Load RSA private key.
    Priority:
      1. Streamlit secrets → private_key_str  (PEM string, for cloud deploy)
      2. .env → SNOWFLAKE_PRIVATE_KEY_PATH    (local dev, absolute path)
    Raises a clear error if neither is found.
    """
    # 1. Try PEM string from Streamlit secrets
    try:
        pem_str = st.secrets["snowflake"].get("private_key_str", "")
        if pem_str:
            pem_bytes = pem_str.strip().encode()
            passphrase = _get_passphrase()
            return _der_from_pem(pem_bytes, passphrase)
    except (KeyError, AttributeError, FileNotFoundError):
        pass

    # 2. Try key file path from .env
    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "")
    if not key_path:
        raise FileNotFoundError(
            "RSA private key not found.\n"
            "Set SNOWFLAKE_PRIVATE_KEY_PATH in your .env file, "
            "or private_key_str in .streamlit/secrets.toml."
        )

    key_path = pathlib.Path(key_path).expanduser()
    if not key_path.exists():
        raise FileNotFoundError(
            f"RSA key file not found at: {key_path}\n"
            "Check SNOWFLAKE_PRIVATE_KEY_PATH in your .env file."
        )

    with open(key_path, "rb") as f:
        pem_bytes = f.read()

    return _der_from_pem(pem_bytes, _get_passphrase())


def _get_passphrase() -> bytes | None:
    pw = _get_config("private_key_passphrase", "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "")
    return pw.encode() if pw else None


def _der_from_pem(pem_bytes: bytes, passphrase: bytes | None) -> bytes:
    private_key = serialization.load_pem_private_key(
        pem_bytes, password=passphrase, backend=default_backend()
    )
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@st.cache_resource(show_spinner=False)
def get_connection():
    """
    Cached Snowflake connection — one per app session.
    If this raises, the error is shown clearly in the UI.
    """
    account   = _get_config("account",   "SNOWFLAKE_ACCOUNT")
    user      = _get_config("user",      "SNOWFLAKE_USER",      "CLAUDE_SERVICE_USER")
    database  = _get_config("database",  "SNOWFLAKE_DATABASE",  "PIPE_DATABASE")
    warehouse = _get_config("warehouse", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_LEARNING_WH")
    role      = _get_config("role",      "SNOWFLAKE_ROLE") or None

    if not account:
        raise ValueError(
            "SNOWFLAKE_ACCOUNT is not set.\n"
            "Add it to your .env file (e.g. SNOWFLAKE_ACCOUNT=xy12345.us-east-1)."
        )

    return snowflake.connector.connect(
        account=account,
        user=user,
        private_key=_load_private_key(),
        database=database,
        warehouse=warehouse,
        role=role,
        client_session_keep_alive=True,
        network_timeout=30,
        login_timeout=30,
    )


def resume_warehouse(conn):
    """Resume warehouse if suspended — safe to call before every query."""
    wh = _get_config("warehouse", "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_LEARNING_WH")
    try:
        conn.cursor().execute(f"ALTER WAREHOUSE {wh} RESUME IF SUSPENDED")
    except Exception:
        pass  # already running, or no RESUME privilege — safe to continue


def _get_fresh_connection():
    """
    Return a working connection, clearing the cache and reconnecting
    if the existing connection has gone stale (e.g. after idle timeout).
    """
    try:
        conn = get_connection()
        conn.cursor().execute("SELECT 1")  # lightweight liveness check
        return conn
    except Exception:
        get_connection.clear()  # evict stale connection from cache
        return get_connection()


@st.cache_data(ttl=3600, show_spinner=False)
def run_query(sql: str, schema: str) -> pd.DataFrame:
    """
    Run a SQL query, replacing <SCHEMA> with the customer schema.
    Results cached for 1 hour per (sql, schema) pair.
    Surfaces clear errors rather than silent empty DataFrames.
    """
    try:
        conn = _get_fresh_connection()
    except Exception as e:
        st.error(f"**Snowflake connection failed:** {e}", icon="🔌")
        return pd.DataFrame()

    resume_warehouse(conn)
    sql_resolved = sql.replace("<SCHEMA>", schema)

    try:
        cur = conn.cursor()
        cur.execute(sql_resolved)
        df = cur.fetch_pandas_all()
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"**Query failed:** {e}", icon="❌")
        return pd.DataFrame()


# -- Pending-schema guard ------------------------------------------------------
# Schemas in WATCH_SCHEMAS return an empty DataFrame (no query, no error box)
# until PIPE_DATABASE.<schema>.CASE_SUMMARY is readable by this role. After that
# the guard switches itself off. Every other schema goes straight to run_query.
import time as _time

WATCH_SCHEMAS = {"ONEOCEAN_PUBLIC"}
_READY_SCHEMAS = set()
_orig_run_query = run_query


@st.cache_data(ttl=3600, show_spinner=False)
def _probe_schema(schema: str, bucket: int) -> bool:
    try:
        df = _orig_run_query(
            "SELECT COUNT(*) AS cnt FROM PIPE_DATABASE.information_schema.tables "
            f"WHERE table_schema = '{schema}' AND table_name = 'CASE_SUMMARY' "
            f"/* probe {bucket} */",
            schema,
        )
        return (not df.empty) and int(df.iloc[0, 0]) > 0
    except Exception:
        return False


def snowflake_pending(schema: str) -> bool:
    if schema not in WATCH_SCHEMAS or schema in _READY_SCHEMAS:
        return False
    if _probe_schema(schema, int(_time.time() // 3600)):
        _READY_SCHEMAS.add(schema)
        return False
    return True


def run_query(*args, **kwargs):
    schema = kwargs.get("schema") if "schema" in kwargs else (args[1] if len(args) > 1 else None)
    if schema and snowflake_pending(schema):
        return pd.DataFrame()
    return _orig_run_query(*args, **kwargs)


run_query.clear = getattr(_orig_run_query, "clear", lambda: None)
