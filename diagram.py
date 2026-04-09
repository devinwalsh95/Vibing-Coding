"""
Process flow diagram renderer — horseshoe layout using Plotly.
"""

import json
import math
import re
import textwrap

import plotly.graph_objects as go

# ── Colours (SAP palette) ──────────────────────────────────────────────────────
NODE_FILL   = "#3DBFB8"   # teal
NODE_BORDER = "#2B9A94"
TRACK_COLOR = "rgba(61,191,184,0.25)"
ARROW_COLOR = "#0066A1"   # SAP blue
TEXT_COLOR  = "#1A1A2E"
TITLE_COLOR = "#0066A1"

# ── Layout constants ───────────────────────────────────────────────────────────
H_SPACING   = 2.8   # horizontal gap between nodes
V_GAP       = 1.8   # vertical distance between top and bottom rows
NODE_R      = 0.55  # visual radius (for annotation offsets)
LABEL_LINES = 2     # max lines to wrap node labels to


def _wrap(text: str, width: int = 12) -> str:
    """Wrap label text to at most LABEL_LINES lines."""
    lines = textwrap.wrap(text, width=width)
    return "<br>".join(lines[:LABEL_LINES])


def _compute_layout(n: int) -> list[tuple[float, float]]:
    """
    Horseshoe: top row L→R, bottom row R→L.

    Returns list of (x, y) in order of process stages.
    """
    top_n = math.ceil(n / 2)
    bot_n = n - top_n

    coords: list[tuple[float, float]] = []

    # Top row — left to right
    for i in range(top_n):
        coords.append((i * H_SPACING, V_GAP))

    # Bottom row — right to left (wraps under the top row)
    for j in range(bot_n):
        x = (top_n - 2 - j) * H_SPACING
        coords.append((x, 0.0))

    return coords


def _spline_through(coords: list[tuple[float, float]]) -> tuple[list[float], list[float]]:
    """
    Build a smooth path through the node centres for the background track.
    Uses simple mid-point smoothing with None separators (Plotly spline).
    """
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    return xs, ys


def render_process_flow(flow_data: dict) -> "go.Figure | None":
    """
    Build a horseshoe process-flow Plotly figure from flow_data.

    flow_data schema:
        {
          "title": str,
          "processes": [
            {"label": str, "action_to_next": str | null},
            ...
          ]
        }
    """
    processes = flow_data.get("processes", [])
    if not processes:
        return None

    n = len(processes)
    coords = _compute_layout(n)

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]

    fig = go.Figure()

    # ── Background track (thick translucent line through all nodes) ────────────
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines",
            line=dict(
                color=TRACK_COLOR,
                width=90,
                shape="spline",
                smoothing=0.8,
            ),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # ── Arrows between consecutive nodes ──────────────────────────────────────
    top_n = math.ceil(n / 2)

    for i in range(n - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]

        # Turn arrow (top-row last → bottom-row first): curved annotation path
        if i == top_n - 1:
            # Use a shape bezier for the right-side U-turn
            # Bezier: start at (x0, y0-NODE_R), control points, end at (x1, y1+NODE_R)
            ctrl_x = x0 + H_SPACING * 0.6
            fig.add_shape(
                type="path",
                path=(
                    f"M {x0},{y0 - NODE_R} "
                    f"C {ctrl_x},{y0 - NODE_R * 2} "
                    f"  {ctrl_x},{y1 + NODE_R * 2} "
                    f"  {x1},{y1 + NODE_R}"
                ),
                line=dict(color=ARROW_COLOR, width=2),
                fillcolor="rgba(0,0,0,0)",
            )
            # Arrowhead at (x1, y1+NODE_R) pointing downward
            fig.add_annotation(
                x=x1, y=y1 + NODE_R,
                ax=x1, ay=y1 + NODE_R * 2.5,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.2,
                arrowwidth=2,
                arrowcolor=ARROW_COLOR,
                text="",
            )
        else:
            # Straight arrow
            mid_x = (x0 + x1) / 2
            mid_y = (y0 + y1) / 2
            fig.add_annotation(
                x=x1, y=y1,
                ax=x0, ay=y0,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1.2,
                arrowwidth=2,
                arrowcolor=ARROW_COLOR,
                text="",
            )
            # Action label on the arrow midpoint
            action = processes[i].get("action_to_next") or ""
            if action:
                offset_y = 0.22 if y0 == y1 else 0.0
                fig.add_annotation(
                    x=mid_x, y=mid_y + offset_y,
                    text=f"<b>{action}</b>",
                    showarrow=False,
                    font=dict(size=9, color=ARROW_COLOR),
                    bgcolor="rgba(255,255,255,0.7)",
                    borderpad=2,
                )

    # ── Node circles ──────────────────────────────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+text",
            marker=dict(
                size=72,
                color=NODE_FILL,
                line=dict(color=NODE_BORDER, width=2),
                symbol="circle",
            ),
            text=[str(i + 1) for i in range(n)],
            textfont=dict(size=18, color="white"),
            textposition="middle center",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # ── Node labels (below each node) ─────────────────────────────────────────
    for i, proc in enumerate(processes):
        x, y = coords[i]
        label = _wrap(proc.get("label", f"Step {i+1}"))
        label_y = y - NODE_R - 0.15
        fig.add_annotation(
            x=x, y=label_y,
            text=f"<b>{label}</b>",
            showarrow=False,
            font=dict(size=11, color=TEXT_COLOR),
            align="center",
            yanchor="top",
        )

    # ── Layout ────────────────────────────────────────────────────────────────
    x_min = min(xs) - 1.0
    x_max = max(xs) + 1.0
    y_min = -0.9
    y_max = V_GAP + 1.0

    title_text = flow_data.get("title", "Business Process Flow")

    fig.update_layout(
        title=dict(
            text=f"<b>{title_text}</b>",
            font=dict(size=15, color=TITLE_COLOR),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(visible=False, range=[x_min, x_max]),
        yaxis=dict(visible=False, range=[y_min, y_max], scaleanchor="x", scaleratio=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=20, r=20, t=50, b=20),
        height=340,
    )

    return fig


def extract_process_flow(markdown_text: str) -> tuple[str, "dict | None"]:
    """
    Find and extract a ```process-flow ... ``` fenced block from the markdown.

    Returns:
        (clean_markdown, flow_data_dict | None)
    clean_markdown has the fenced block removed.
    """
    pattern = r"```process-flow\s*\n(.*?)\n```"
    match = re.search(pattern, markdown_text, re.DOTALL)
    if not match:
        return markdown_text, None

    raw_json = match.group(1).strip()
    clean = markdown_text[: match.start()].rstrip() + markdown_text[match.end() :]

    try:
        flow_data = json.loads(raw_json)
        return clean, flow_data
    except json.JSONDecodeError:
        return clean, None
