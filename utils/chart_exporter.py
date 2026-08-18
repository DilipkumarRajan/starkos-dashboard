"""
utils/chart_exporter.py
Exports Plotly charts as PNG images, uploads to Google Drive,
and returns public URLs for embedding in Google Slides.

Flow:
  1. Build Plotly figure (same charts as dashboard)
  2. Export to PNG bytes using kaleido
  3. Upload to a temp folder in Google Drive
  4. Make file publicly readable
  5. Return URL for use in createImage Slides request

Install: pip install kaleido plotly
"""

import io
import base64
import tempfile
import pathlib
import pandas as pd
import plotly.graph_objects as go
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ── Chart color palette (matches dashboard) ───────────────────────────────────
C = {
    "navy":        "#0A1931",
    "blue":        "#185FA5",
    "blue_light":  "rgba(24,95,165,0.15)",
    "teal":        "#0F6E56",
    "teal_light":  "rgba(15,110,86,0.15)",
    "red":         "#E24B4A",
    "red_light":   "rgba(226,75,74,0.12)",
    "purple":      "#534AB7",
    "amber":       "#BA7517",
    "amber_light": "rgba(186,117,23,0.12)",
    "gray":        "#B4B2A9",
    "green":       "#1D9E75",
    "white":       "#FFFFFF",
    "light":       "#F4F6F9",
}

# Chart layout defaults — clean, white background for slide embedding
LAYOUT = dict(
    paper_bgcolor=C["white"],
    plot_bgcolor=C["light"],
    font=dict(family="Google Sans, Arial, sans-serif", size=12, color="#1C2B3A"),
    margin=dict(l=50, r=30, t=50, b=60),
    height=400,
    width=800,
    xaxis=dict(showgrid=False, tickfont=dict(size=11), tickangle=-30),
    yaxis=dict(gridcolor="rgba(0,0,0,0.06)", tickfont=dict(size=11)),
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="left", x=0,
                font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
)


def _apply_layout(fig, title="", height=400, width=800):
    layout = {**LAYOUT, "height": height, "width": width}
    if title:
        layout["title"] = dict(text=f"<b>{title}</b>", font=dict(size=14, color="#0A1931"),
                               x=0, xanchor="left", pad=dict(t=8))
        layout["margin"]["t"] = 65
    fig.update_layout(**layout)
    return fig


# ── Chart builders ────────────────────────────────────────────────────────────

def chart_frt_trend(df_frt: pd.DataFrame) -> go.Figure:
    """FRT monthly trend — area chart with annotation."""
    if df_frt.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_frt["month"], y=df_frt["avg_frt_hours"],
        name="Avg FRT (hours)",
        line=dict(color=C["blue"], width=2.5),
        fill="tozeroy",
        fillcolor=C["blue_light"],
        mode="lines+markers",
        marker=dict(size=5, color=C["blue"]),
    ))
    # Annotate first and last
    if len(df_frt) >= 2:
        fig.add_annotation(x=df_frt["month"].iloc[0], y=float(df_frt["avg_frt_hours"].iloc[0]),
            text=f"{df_frt['avg_frt_hours'].iloc[0]} hrs", showarrow=True,
            arrowhead=2, ax=30, ay=-30, font=dict(size=10, color=C["red"]))
        fig.add_annotation(x=df_frt["month"].iloc[-2], y=float(df_frt["avg_frt_hours"].iloc[-2]),
            text=f"{df_frt['avg_frt_hours'].iloc[-2]} hrs", showarrow=True,
            arrowhead=2, ax=30, ay=-30, font=dict(size=10, color=C["teal"]))
    return _apply_layout(fig, "First Response Time — Monthly Trend (Hours)", height=380)


def chart_escalation_trend(df_esc: pd.DataFrame, benchmark=2.0) -> go.Figure:
    """Escalation rate trend with benchmark line."""
    if df_esc.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_esc["month"], y=df_esc["total_cases"],
        name="Case volume", marker_color=C["blue_light"],
        yaxis="y2", opacity=0.6,
    ))
    fig.add_trace(go.Scatter(
        x=df_esc["month"], y=df_esc["escalation_pct"],
        name="Escalation rate (%)",
        line=dict(color=C["red"], width=2.5),
        mode="lines+markers",
        marker=dict(size=5, color=C["red"]),
        yaxis="y",
    ))
    fig.add_hline(y=benchmark, line_dash="dash", line_color=C["red"],
                  annotation_text=f"{benchmark}% benchmark",
                  annotation_position="top right",
                  annotation_font=dict(size=10, color=C["red"]))
    fig.update_layout(
        **{**LAYOUT,
           "height": 380, "width": 800,
           "title": dict(text="<b>Escalation Rate vs Case Volume</b>",
                         font=dict(size=14, color="#0A1931"), x=0, xanchor="left"),
           "margin": {**LAYOUT["margin"], "t": 65},
           "yaxis": dict(gridcolor="rgba(0,0,0,0.06)", tickfont=dict(size=11),
                         title="Escalation %", titlefont=dict(size=11)),
           "yaxis2": dict(overlaying="y", side="right", showgrid=False,
                          tickfont=dict(size=11), title="Cases",
                          titlefont=dict(size=11)),
        }
    )
    return fig


def chart_lte_predictions(df_lte: pd.DataFrame) -> go.Figure:
    """LTE predictions vs actual escalations."""
    if df_lte.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_lte["month"], y=df_lte["cases_predicted"],
        name="Cases flagged by LTE",
        marker_color=C["amber_light"],
    ))
    fig.add_trace(go.Scatter(
        x=df_lte["month"], y=df_lte["actually_escalated"],
        name="Actually escalated",
        line=dict(color=C["red"], width=2.5),
        mode="lines+markers",
        marker=dict(size=5, color=C["red"]),
    ))
    return _apply_layout(fig, "LTE Predictions vs Actual Escalations", height=380)


def chart_sentiment_trend(df_sent: pd.DataFrame) -> go.Figure:
    """Sentiment and need-attention score trend."""
    if df_sent.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sent["month"], y=df_sent["avg_sentiment"],
        name="Avg sentiment (higher = better)",
        line=dict(color=C["teal"], width=2.5),
        fill="tozeroy", fillcolor=C["teal_light"],
        mode="lines+markers", marker=dict(size=5, color=C["teal"]),
    ))
    fig.add_trace(go.Scatter(
        x=df_sent["month"], y=df_sent["avg_need_attention"],
        name="Need-attention score (lower = better)",
        line=dict(color=C["amber"], width=2, dash="dot"),
        mode="lines+markers", marker=dict(size=5, color=C["amber"]),
    ))
    fig.add_hline(y=70, line_dash="dash", line_color=C["gray"],
                  annotation_text="Healthy threshold (70)",
                  annotation_position="top right",
                  annotation_font=dict(size=9, color=C["gray"]))
    return _apply_layout(fig, "Sentiment Score vs Need-Attention Score", height=380)


def chart_reassignment(df_re: pd.DataFrame) -> go.Figure:
    """Reassignment rate colored by severity."""
    if df_re.empty:
        return None
    colors = [
        C["red"] if v > 5 else C["amber"] if v > 1 else C["teal"]
        for v in df_re["reassignment_pct"]
    ]
    fig = go.Figure(go.Bar(
        x=df_re["month"], y=df_re["reassignment_pct"],
        marker_color=colors, name="Reassignment rate (%)",
    ))
    fig.add_hline(y=1, line_dash="dash", line_color=C["teal"],
                  annotation_text="Target (<1%)",
                  annotation_position="top right",
                  annotation_font=dict(size=9, color=C["teal"]))
    return _apply_layout(fig, "Reassignment Rate — Monthly (red >5%, amber 1–5%, green <1%)", height=360)


def chart_health_trend(df_health: pd.DataFrame) -> go.Figure:
    """Account health score trend."""
    if df_health.empty:
        return None
    colors = [C["teal"] if v >= 70 else C["amber"] if v >= 50 else C["red"]
              for v in df_health["avg_health_score"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_health["month"], y=df_health["avg_health_score"],
        name="Health score (0–100)",
        line=dict(color=C["purple"], width=2.5),
        mode="lines+markers",
        marker=dict(size=8, color=colors),
    ))
    fig.add_hline(y=70, line_dash="dash", line_color=C["teal"],
                  annotation_text="Good threshold (70)",
                  annotation_position="top right",
                  annotation_font=dict(size=9, color=C["teal"]))
    fig.add_hline(y=50, line_dash="dash", line_color=C["red"],
                  annotation_text="At-risk threshold (50)",
                  annotation_position="bottom right",
                  annotation_font=dict(size=9, color=C["red"]))
    return _apply_layout(fig, "Account Health Score Trend", height=360)


def chart_alerts_monthly(df_alerts: pd.DataFrame) -> go.Figure:
    """Alerts fired monthly — stacked."""
    if df_alerts.empty:
        return None
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_alerts["month"], y=df_alerts["total_alerts"],
                         name="Total alerts fired", marker_color=C["teal"]))
    fig.add_trace(go.Scatter(
        x=df_alerts["month"], y=df_alerts["alert_cases"],
        name="Unique cases alerted",
        line=dict(color=C["blue"], width=2), mode="lines+markers",
        marker=dict(size=5),
    ))
    return _apply_layout(fig, "Alerts Fired — Monthly", height=360)


# ── PNG export and Drive upload ───────────────────────────────────────────────

def fig_to_png_bytes(fig: go.Figure, scale: float = 2.0) -> bytes:
    """Export Plotly figure to PNG bytes using kaleido direct API (works with Plotly 5.x)."""
    import kaleido
    import io as _io
    buf = _io.BytesIO()
    kaleido.write_fig(fig, buf, format="png", scale=scale)
    return buf.getvalue()


def upload_png_to_drive(png_bytes: bytes, filename: str, drive_svc) -> str:
    """
    Upload PNG to Google Drive in appDataFolder (hidden, no clutter).
    Returns a publicly accessible URL.
    """
    fh = io.BytesIO(png_bytes)
    media = MediaIoBaseUpload(fh, mimetype="image/png", resumable=False)

    # Upload
    file_meta = {
        "name": filename,
        "parents": ["appDataFolder"],
    }
    uploaded = drive_svc.files().create(
        body=file_meta, media_body=media, fields="id"
    ).execute()
    file_id = uploaded["id"]

    # Make publicly readable
    drive_svc.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()

    # Return direct download URL
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def export_charts(data: dict, drive_svc, benchmark=2.0) -> dict:
    """
    Build all charts, export to PNG, upload to Drive.
    Returns dict of {chart_name: url} for embedding in slides.

    Only exports charts where data is available.
    """
    chart_builders = {
        "frt_trend":       (chart_frt_trend,        [data.get("frt_monthly",         pd.DataFrame())]),
        "escalation_trend":(chart_escalation_trend,  [data.get("escalation_monthly",  pd.DataFrame()), benchmark]),
        "lte_predictions": (chart_lte_predictions,   [data.get("lte_accuracy_monthly",pd.DataFrame())]),
        "sentiment_trend": (chart_sentiment_trend,   [data.get("sentiment_monthly",   pd.DataFrame())]),
        "reassignment":    (chart_reassignment,      [data.get("reassignment_monthly",pd.DataFrame())]),
        "health_trend":    (chart_health_trend,      [data.get("account_health_monthly",pd.DataFrame())]),
        "alerts_monthly":  (chart_alerts_monthly,    [data.get("alerts_monthly",      pd.DataFrame())]),
    }

    urls = {}
    for name, (builder, args) in chart_builders.items():
        try:
            fig = builder(*args)
            if fig is None:
                continue
            png_bytes = fig_to_png_bytes(fig)
            url = upload_png_to_drive(png_bytes, f"sl_deck_{name}.png", drive_svc)
            urls[name] = url
            print(f"  ✅ {name} uploaded")
        except Exception as e:
            print(f"  ⚠️ {name} failed: {e}")

    return urls
