"""
utils/charts.py  —  Shared Plotly chart helpers.
Varied chart types: line, bar, combo, area, scatter-bubble, donut, gauge, heatmap-style.
All titles passed via st.markdown outside the chart. Legend sits below to avoid collision.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import copy

COLORS = {
    "blue":         "#185FA5",
    "blue_light":   "rgba(24,95,165,0.15)",
    "teal":         "#0F6E56",
    "teal_light":   "rgba(29,158,117,0.2)",
    "red":          "#E24B4A",
    "red_light":    "rgba(226,75,74,0.12)",
    "purple":       "#534AB7",
    "purple_light": "rgba(83,74,183,0.15)",
    "amber":        "#BA7517",
    "amber_light":  "rgba(186,117,23,0.12)",
    "gray":         "#B4B2A9",
    "gray_light":   "rgba(136,135,128,0.15)",
    "green":        "#1D9E75",
    "green_light":  "rgba(29,158,117,0.15)",
    "coral":        "#D85A30",
    "coral_light":  "rgba(216,90,48,0.12)",
}

_BASE = dict(
    margin=dict(l=4, r=20, t=10, b=52),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", size=11, color="#888"),
    xaxis=dict(showgrid=False, tickfont=dict(size=10), tickangle=-30, automargin=True),
    yaxis=dict(gridcolor="rgba(130,130,130,0.08)", tickfont=dict(size=10), automargin=True),
    legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0,
                font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
    height=260,
)

def _layout(**kw):
    l = copy.deepcopy(_BASE)
    l.update(kw)
    return l


# ── 1. Smooth area chart (great for sentiment, health scores) ────────────────
def area_chart(df, x, y_cols, height=260, reference_lines=None):
    fig = go.Figure()
    for i, y in enumerate(y_cols):
        rgba = y["color"].replace("#", "")
        fig.add_trace(go.Scatter(
            x=df[x], y=df[y["col"]], name=y["name"],
            line=dict(color=y["color"], width=2),
            fill="tozeroy" if i == 0 else "tonexty",
            fillcolor=y.get("fill", y["color"].replace(")", ",0.08)").replace("rgb", "rgba") if "rgb" in y["color"] else y["color"] + "14"),
            mode="lines",
        ))
    if reference_lines:
        for rl in reference_lines:
            fig.add_hline(y=rl["y"], line_dash="dash", line_color=rl["color"],
                          annotation_text=rl["label"], annotation_position="top right",
                          annotation_font_size=10, annotation_font_color=rl["color"])
    fig.update_layout(**_layout(height=height))
    return fig


# ── 2. Line chart with markers ───────────────────────────────────────────────
def line_chart(df, x, y_cols, height=260, reference_lines=None):
    fig = go.Figure()
    for y in y_cols:
        fig.add_trace(go.Scatter(
            x=df[x], y=df[y["col"]], name=y["name"],
            line=dict(color=y["color"], width=2),
            mode="lines+markers", marker=dict(size=4, color=y["color"]),
        ))
    if reference_lines:
        for rl in reference_lines:
            fig.add_hline(y=rl["y"], line_dash="dash", line_color=rl["color"],
                          annotation_text=rl["label"], annotation_position="top right",
                          annotation_font_size=10, annotation_font_color=rl["color"])
    fig.update_layout(**_layout(height=height))
    return fig


# ── 3. Bar chart ─────────────────────────────────────────────────────────────
def bar_chart(df, x, y_cols, height=240, horizontal=False):
    fig = go.Figure()
    for y in y_cols:
        colors = y.get("colors")
        if horizontal:
            fig.add_trace(go.Bar(
                y=df[x], x=df[y["col"]], name=y["name"],
                marker_color=colors or y["color"], marker_line_width=0,
                orientation="h",
            ))
        else:
            fig.add_trace(go.Bar(
                x=df[x], y=df[y["col"]], name=y["name"],
                marker_color=colors or y["color"], marker_line_width=0,
            ))
    layout = _layout(height=height, barmode="group")
    if horizontal:
        layout["xaxis"], layout["yaxis"] = layout["yaxis"], layout["xaxis"]
        layout["xaxis"]["showgrid"] = True
        layout["yaxis"]["showgrid"] = False
        layout["yaxis"]["tickangle"] = 0
        layout["margin"]["b"] = 20
        layout["margin"]["l"] = 20
    fig.update_layout(**layout)
    return fig


# ── 4. Combo: bar (volume) + line (rate) on dual Y ──────────────────────────
def combo_chart(df, x, bar_col, line_col, height=260, reference_lines=None):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df[x], y=df[bar_col["col"]], name=bar_col["name"],
        marker_color=bar_col["color"], yaxis="y2", marker_line_width=0, opacity=0.5,
    ))
    fig.add_trace(go.Scatter(
        x=df[x], y=df[line_col["col"]], name=line_col["name"],
        line=dict(color=line_col["color"], width=2.5),
        mode="lines+markers", marker=dict(size=4), yaxis="y",
    ))
    if reference_lines:
        for rl in reference_lines:
            fig.add_hline(y=rl["y"], yref="y", line_dash="dash", line_color=rl["color"],
                          annotation_text=rl["label"], annotation_position="top right",
                          annotation_font_size=10, annotation_font_color=rl["color"])
    fig.update_layout(**_layout(
        height=height,
        yaxis=dict(gridcolor="rgba(130,130,130,0.08)", tickfont=dict(size=10), automargin=True),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, tickfont=dict(size=10), automargin=True),
    ))
    return fig


# ── 5. Donut chart (feature adoption / split) ───────────────────────────────
def donut_chart(labels, values, colors, height=240, center_text=""):
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(width=0)),
        textinfo="label+percent",
        textfont=dict(size=11),
        insidetextorientation="radial",
    ))
    fig.update_layout(**_layout(height=height, margin=dict(l=4, r=4, t=10, b=52),
                                showlegend=False))
    if center_text:
        fig.add_annotation(text=center_text, x=0.5, y=0.5, font_size=13,
                           showarrow=False, font_color="#888")
    return fig


# ── 6. Scatter / bubble chart (cases per agent × reassignment) ───────────────
def bubble_chart(df, x, y, size, color, labels, height=260, size_scale=40):
    fig = go.Figure(go.Scatter(
        x=df[x], y=df[y],
        mode="markers+text",
        text=df[labels] if labels else None,
        textposition="top center",
        textfont=dict(size=9),
        marker=dict(
            size=df[size],
            sizemode="area",
            sizeref=2.0 * df[size].max() / (size_scale ** 2),
            sizemin=4,
            color=df[y],
            colorscale=[[0, COLORS["teal_light"]], [0.5, COLORS["blue"]], [1, COLORS["red"]]],
            showscale=False,
            opacity=0.75,
        ),
    ))
    fig.update_layout(**_layout(height=height))
    return fig


# ── 7. Stacked bar (feature usage breakdown) ─────────────────────────────────
def stacked_bar(df, x, y_cols, height=240):
    fig = go.Figure()
    for y in y_cols:
        fig.add_trace(go.Bar(
            x=df[x], y=df[y["col"]], name=y["name"],
            marker_color=y["color"], marker_line_width=0,
        ))
    fig.update_layout(**_layout(height=height, barmode="stack"))
    return fig


# ── 8. Gauge (single KPI — health score, sentiment) ─────────────────────────
def gauge_chart(value, min_val=0, max_val=100, thresholds=None, label="", height=200):
    thresholds = thresholds or [
        {"range": [0, 40],  "color": COLORS["red_light"]},
        {"range": [40, 70], "color": COLORS["amber_light"]},
        {"range": [70, 100],"color": COLORS["teal_light"]},
    ]
    steps = [{"range": t["range"], "color": t["color"]} for t in thresholds]
    needle_color = COLORS["red"] if value < 40 else COLORS["amber"] if value < 70 else COLORS["teal"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"font": {"size": 28, "color": needle_color}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickfont": {"size": 10}},
            "bar": {"color": needle_color, "thickness": 0.25},
            "steps": steps,
            "threshold": {"line": {"color": needle_color, "width": 3}, "value": value},
            "bgcolor": "rgba(0,0,0,0)",
        },
        title={"text": label, "font": {"size": 12, "color": "#888"}},
    ))
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=10),
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)",
                      height=height)
    return fig


# ── 9. Step/waterfall-style line (for ICA volume milestones) ─────────────────
def step_line(df, x, y_cols, height=260):
    fig = go.Figure()
    for y in y_cols:
        fig.add_trace(go.Scatter(
            x=df[x], y=df[y["col"]], name=y["name"],
            line=dict(color=y["color"], width=2, shape="hvh"),
            mode="lines+markers", marker=dict(size=5, color=y["color"]),
        ))
    fig.update_layout(**_layout(height=height))
    return fig


def metric_delta(current, previous, invert=False):
    if previous is None or previous == 0:
        return "—", "gray"
    pct = (current - previous) / abs(previous) * 100
    direction = "↑" if pct > 0 else "↓"
    good = pct < 0 if invert else pct > 0
    return f"{direction} {abs(pct):.1f}%", "green" if good else "red"
