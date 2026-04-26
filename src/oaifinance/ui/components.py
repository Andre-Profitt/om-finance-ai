"""Reusable UI components built on Streamlit + custom HTML.

Strict patterns:
- KPI cards always show label + value + optional footnote
- Status pills are colored semantically (success / warning / danger / info)
- Citation card renders the retrieved clause as a left-bordered blockquote
- All numeric values use tabular-nums via the global CSS for grid alignment
"""

from __future__ import annotations

from html import escape
from typing import Sequence

import altair as alt  # noqa: F401  — used by _spark_chart
import polars as pl  # noqa: F401  — used by _spark_chart
import streamlit as st


def page_header(
    title: str, subtitle: str, run_id: str | None = None, n_rows: int | None = None
) -> None:
    meta_bits = []
    if run_id:
        meta_bits.append(f"run <code>{escape(str(run_id)[:10])}…</code>")
    if n_rows is not None:
        meta_bits.append(f"{n_rows:,} rows")
    meta_html = "<br>".join(meta_bits) if meta_bits else "&nbsp;"

    st.markdown(
        f"""
<div class="page-header">
  <div>
    <h1>{escape(title)}</h1>
    <p class="subtitle">{escape(subtitle)}</p>
  </div>
  <div class="meta">{meta_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(
        f'<div class="section-h">{escape(title)}</div>',
        unsafe_allow_html=True,
    )


def fmt_dollars(x: float | int | None) -> str:
    if x is None:
        return "—"
    x = float(x)
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:.2f}M"
    if abs(x) >= 1_000:
        return f"${x / 1_000:.1f}K"
    return f"${x:,.0f}"


def fmt_pct(x: float | None, places: int = 1) -> str:
    if x is None:
        return "—"
    return f"{float(x) * 100:.{places}f}%"


def fmt_score(x: float | None, places: int = 3) -> str:
    if x is None:
        return "—"
    return f"{float(x):.{places}f}"


def kpi_grid(cards: list[tuple[str, str, str | None]], accent_first: bool = True) -> None:
    """Render a horizontal grid of KPI cards.

    Each card is (label, value, footnote_or_none).

    HTML is emitted with NO leading whitespace per line — Streamlit's markdown
    parser treats 4+ spaces as a code block, which would dump raw HTML into
    the page instead of rendering it.
    """
    parts = ['<div class="kpi-grid">']
    for i, (label, value, footnote) in enumerate(cards):
        accent_class = " accent" if accent_first and i == 0 else ""
        foot_html = f'<div class="footnote">{escape(footnote)}</div>' if footnote else ""
        parts.append(
            f'<div class="kpi-card{accent_class}">'
            f'<div class="label">{escape(label)}</div>'
            f'<div class="value">{escape(value)}</div>'
            f"{foot_html}"
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def status_pill(label: str, kind: str = "info") -> str:
    """Return an HTML span for a status pill. Use inside markdown blocks."""
    return f'<span class="pill {escape(kind)}">{escape(label)}</span>'


def citation_card(
    doc_id: str | None, section_title: str | None, similarity: float | None, clause: str | None
) -> None:
    if not clause:
        return
    doc = (
        f"<strong>{escape(doc_id or '')}</strong> §{escape(section_title or '')}" if doc_id else "—"
    )
    sim = f"similarity {similarity:.3f}" if similarity is not None else ""
    body = escape(clause)
    st.markdown(
        f"""
<div class="citation-card">
  <div class="header">
    <span class="doc">{doc}</span>
    <span class="similarity">{sim}</span>
  </div>
  <blockquote>{body}</blockquote>
</div>
""",
        unsafe_allow_html=True,
    )


def severity_pill(score: float | None) -> str:
    if score is None:
        return status_pill("—", "low")
    if score >= 0.85:
        return status_pill("high", "high")
    if score >= 0.6:
        return status_pill("medium", "medium")
    return status_pill("low", "low")


def explained_pill(explained: bool, abstained: bool) -> str:
    if abstained:
        return status_pill("abstained", "abstained")
    if explained:
        return status_pill("explained", "explained")
    return status_pill("unscored", "low")


def specialty_pill(specialty: str | None) -> str:
    if not specialty:
        return ""
    return status_pill(specialty, "specialty")


def app_footer(version: str, run_id: str | None = None, model_run_id: str | None = None) -> None:
    bits = [f"version <code>{escape(version)}</code>"]
    if run_id:
        bits.append(f"data run <code>{escape(str(run_id)[:8])}</code>")
    if model_run_id:
        bits.append(f"model run <code>{escape(str(model_run_id)[:10])}</code>")
    left = " · ".join(bits)
    right = "Synthetic data anchored to public CMS ASP. No PHI. Not affiliated with McKesson."
    st.markdown(
        f'<div class="app-footer"><div>{left}</div><div>{escape(right)}</div></div>',
        unsafe_allow_html=True,
    )


def _spark_chart(series: Sequence[float] | pl.Series, color: str = "#1e3a5f") -> alt.Chart:
    if isinstance(series, pl.Series):
        values = series.to_list()
    else:
        values = list(series)
    df = pl.DataFrame({"i": list(range(len(values))), "y": values}).to_pandas()
    base = (
        alt.Chart(df)
        .mark_area(
            line={"color": color, "strokeWidth": 1.5},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color=color, offset=0.0),
                    alt.GradientStop(color="#ffffff", offset=1.0),
                ],
                x1=1,
                x2=1,
                y1=0,
                y2=1,
            ),
            opacity=0.55,
        )
        .encode(
            x=alt.X("i:Q", axis=None),
            y=alt.Y("y:Q", axis=None, scale=alt.Scale(zero=False, padding=2)),
            tooltip=alt.Tooltip("y:Q", format=",.0f"),
        )
        .properties(height=48)
        .configure_view(stroke=None)
        .configure_axis(grid=False)
    )
    return base


def kpi_with_spark(
    label: str, value: str, spark: Sequence[float] | pl.Series, footnote: str | None = None
) -> None:
    st.markdown(
        f'<div class="kpi-spark"><div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div></div>',
        unsafe_allow_html=True,
    )
    try:
        st.altair_chart(_spark_chart(spark), use_container_width=True)
    except Exception:
        pass
    if footnote:
        st.markdown(
            f'<div class="footnote" style="font-size:0.75rem;color:var(--color-text-muted);'
            f'margin:-0.5rem 0 0.75rem 0;">{escape(footnote)}</div>',
            unsafe_allow_html=True,
        )


def kpi_with_spark_row(
    cards: list[tuple[str, str, Sequence[float] | pl.Series, str | None]],
) -> None:
    """Render a row of spark-backed KPI cards across equal-width columns."""
    cols = st.columns(len(cards))
    for col, (label, value, spark, footnote) in zip(cols, cards, strict=True):
        with col:
            kpi_with_spark(label, value, spark, footnote)


def governance_ribbon(
    *,
    environment: str = "Demo / synthetic",
    phi: str = "None",
    citation_gate: str = "Enforced",
    calibration_gate: str = "Pass",
    reviewer_mode: str = "Human-in-the-loop",
    promotion_status: str = "Not production eligible",
) -> None:
    """Compact governance posture ribbon shown under every page header.

    Signals to a reviewer or executive at a glance that this artifact is a
    governed surface: synthetic data, no PHI, citation enforcement on,
    calibration in band, no auto-actions, and not production-promoted.
    """
    kpi_grid(
        [
            ("Environment", environment, "portfolio artifact"),
            ("PHI", phi, "synthetic claims only"),
            ("Citation gate", citation_gate, "quote-or-abstain"),
            ("Calibration gate", calibration_gate, "0.85–1.15 slope band"),
            ("Reviewer mode", reviewer_mode, "actions require human approval"),
            ("Promotion", promotion_status, "pilot gates required"),
        ],
        accent_first=False,
    )


def release_gate_table(rows: list[tuple[str, str, str]]) -> None:
    """Render a release-gate pass/monitor/fail/blocked table.

    Each row is (gate_name, status, evidence). Status is rendered as a pill
    with a semantic color; evidence is the supporting metric or rationale.
    """
    pill_kind = {
        "pass": "explained",
        "monitor": "medium",
        "fail": "abstained",
        "blocked": "abstained",
        "no": "low",
    }
    parts = ['<div class="release-gate-table">']
    parts.append(
        '<div class="release-gate-row release-gate-head">'
        "<div>Gate</div><div>Status</div><div>Evidence</div>"
        "</div>"
    )
    for gate, status, evidence in rows:
        kind = pill_kind.get(status.lower(), "info")
        parts.append(
            '<div class="release-gate-row">'
            f"<div>{escape(gate)}</div>"
            f"<div>{status_pill(status, kind)}</div>"
            f"<div>{escape(evidence)}</div>"
            "</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def audit_event_preview_panel() -> None:
    """Render the session-scoped audit-event preview log.

    Production binding writes the same payload to the append-only override
    log after reviewer authentication; in this view, events live only in
    `st.session_state` and disappear on tab close.
    """
    events = st.session_state.get("audit_preview_events", [])
    if not events:
        st.markdown(
            '<div class="hint">No audit events recorded yet this session. '
            "Disposition actions in the drill-in will write a session-scoped "
            "preview event here — production binding writes the same payload "
            "to the append-only override log.</div>",
            unsafe_allow_html=True,
        )
        return
    parts = ['<div class="audit-event-list">']
    for ev in events:
        rows = "".join(
            f'<div class="audit-event-row">'
            f'<span class="audit-event-key">{escape(str(k))}</span>'
            f'<span class="audit-event-val">{escape(str(v))}</span>'
            "</div>"
            for k, v in ev.items()
        )
        parts.append(f'<div class="audit-event-card">{rows}</div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def empty_state(message: str, hint: str | None = None) -> None:
    st.markdown(
        f"""
<div style="
    background: var(--color-surface);
    border: 1px dashed var(--color-border-strong);
    border-radius: 6px;
    padding: 2rem 1rem;
    text-align: center;
    color: var(--color-text-muted);
">
  <div style="font-size: 0.95rem; font-weight: 500; color: var(--color-text);">{escape(message)}</div>
  {('<div class="hint">' + escape(hint) + "</div>") if hint else ""}
</div>
""",
        unsafe_allow_html=True,
    )
