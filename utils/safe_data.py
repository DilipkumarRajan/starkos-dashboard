"""
utils/safe_data.py
Safe data access helpers — never raise KeyError or IndexError.
Use these everywhere instead of df["col"].iloc[0] directly.
"""
import pandas as pd


def safe_int(df: pd.DataFrame, col: str, default: int = 0) -> int:
    """Safely get integer sum of a column."""
    if df is None or df.empty or col not in df.columns:
        return default
    try:
        return int(df[col].sum())
    except Exception:
        return default


def safe_float(df: pd.DataFrame, col: str, idx: int = -1, default: float = 0.0) -> float:
    """Safely get a float from a column at a given index (default last row)."""
    if df is None or df.empty or col not in df.columns:
        return default
    try:
        return float(df[col].iloc[idx])
    except Exception:
        return default


def safe_str(df: pd.DataFrame, col: str, idx: int = 0, default: str = "—") -> str:
    """Safely get a string from a column at a given index."""
    if df is None or df.empty or col not in df.columns:
        return default
    try:
        return str(df[col].iloc[idx])
    except Exception:
        return default


def ica_active(df_ica: pd.DataFrame) -> bool:
    """ICA is only active if real cases were auto-routed (not just scheduler heartbeats)."""
    return safe_int(df_ica, "total_auto_cases") > 0


def ica_counts(df_ica: pd.DataFrame) -> tuple[int, int]:
    """Returns (auto_cases, manual_cases) safely."""
    return (
        safe_int(df_ica, "total_auto_cases"),
        safe_int(df_ica, "total_manual_cases"),
    )
