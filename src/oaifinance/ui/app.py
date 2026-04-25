"""Home — O&M Finance AI Control Tower.

Multi-page Streamlit application. Pages discoverable via the sidebar:
  1. Reviewer Queue
  2. Network View
  3. Model Ops
  4. Audit Trail
"""

from __future__ import annotations

import polars as pl
import streamlit as st

from oaifinance import __version__
from oaifinance.ui import components as ui
from oaifinance.ui import data as ud
from oaifinance.ui import styles


def main() -> None:
    st.set_page_config(
        page_title="O&M Finance AI Control Tower",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    styles.inject()
    presenter = styles.maybe_presenter_mode()

    with st.sidebar:
        st.markdown(
            """
<div style="padding: 0.5rem 0 1rem 0; border-bottom: 1px solid var(--color-border); margin-bottom: 1rem;">
  <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--color-text-muted);">Product</div>
  <div style="font-size: 0.95rem; font-weight: 600; color: var(--color-text); margin-top: 0.15rem;">O&M Finance AI<br>Control Tower</div>
  <div style="font-size: 0.7rem; color: var(--color-text-faint); margin-top: 0.25rem;">v1 · synthetic data</div>
</div>
""",
            unsafe_allow_html=True,
        )

    frames = ud.load_all()
    if frames.scored is None or frames.explained is None:
        ui.page_header(
            "O&M Finance AI Control Tower",
            "Pipeline outputs not found — run the demo to populate this view.",
        )
        ui.empty_state(
            "No pipeline output detected.",
            "Run `make demo` to ingest the sample data, score exceptions, and "
            "produce the explained queue. Then return to this page.",
        )
        return

    ranked_col = ud.rank_col(frames.scored)
    n_exceptions = len(frames.scored)
    total_at_risk = float(frames.scored["dollars_at_risk"].sum())
    expected_recovery = float(frames.scored[ranked_col].sum())
    n_practices = int(len(frames.practice)) if frames.practice is not None else 0

    model_run_id = (
        frames.scored["model_run_id"][0] if "model_run_id" in frames.scored.columns else None
    )

    ui.page_header(
        "Control Tower — overview",
        "Finance-side operating layer for oncology + multispecialty revenue integrity, access, and contract economics.",
        run_id=str(model_run_id) if model_run_id else None,
        n_rows=n_exceptions,
    )

    daily = ud.daily_exposure_series()
    ui.kpi_with_spark_row(
        [
            (
                "Exception candidates",
                f"{n_exceptions:,}",
                daily.get("n_leakage", []) or [0],
                "true-leakage daily count (90 days)",
            ),
            (
                "Dollars at risk",
                ui.fmt_dollars(total_at_risk),
                daily.get("leakage_dollars", []) or [0],
                "daily recoverable leakage",
            ),
            (
                "Expected recovery",
                ui.fmt_dollars(expected_recovery),
                daily.get("dollars_billed", []) or [0],
                "daily allowed-amount throughput",
            ),
            (
                "Practices",
                str(n_practices) if n_practices else "—",
                daily.get("n_claims", []) or [0],
                "daily claim volume",
            ),
        ]
    )

    ui.section("Quick navigation")
    nav_cols = st.columns(4)
    nav_targets = [
        (
            "Reviewer Queue",
            "Top-100 by expected recovery, with cited explanations and abstention pills.",
        ),
        (
            "Network View",
            "Per-practice exposure, exception mix, and the auto-selected acquisition target.",
        ),
        ("Model Ops", "Calibration health, abstention trends, override agreement."),
        ("Audit Trail", "Append-only override log with model and prompt lineage."),
    ]
    for col, (title, blurb) in zip(nav_cols, nav_targets, strict=True):
        with col:
            st.markdown(
                f"""
<div class="kpi-card" style="height: 100%;">
  <div class="label">Page</div>
  <div class="value" style="font-size: 1rem; font-weight: 600;">{title}</div>
  <div class="footnote">{blurb}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    ui.section("Headline metrics")
    if frames.eval_report:
        report = frames.eval_report
        by_cal = report.get("by_expected_recovery_calibrated") or report.get("by_expected_recovery")
        precision_at_100 = by_cal.get("precision_at_100") if by_cal else None
        dollars_at_100 = by_cal.get("dollars_captured_at_100") if by_cal else None
        per_hour = by_cal.get("dollars_per_reviewer_hour_at_100") if by_cal else None
        slope_cal = report.get("calibration_slope_calibrated")
        cit_p = report.get("citation_precision")
        abst = report.get("abstention_rate")

        ui.kpi_grid(
            [
                (
                    "Precision @ top-100",
                    ui.fmt_pct(precision_at_100, places=1),
                    "ranked by calibrated expected recovery",
                ),
                (
                    "Dollars captured @ top-100",
                    ui.fmt_dollars(dollars_at_100),
                    "real recoverable leakage in the top of the queue",
                ),
                (
                    "Dollars per reviewer-hour",
                    ui.fmt_dollars(per_hour) + "/h" if per_hour else "—",
                    "value yield per analyst hour at top-100",
                ),
                (
                    "Citation precision",
                    ui.fmt_pct(cit_p, places=1),
                    f"abstention rate {ui.fmt_pct(abst, places=1)}",
                ),
            ],
            accent_first=False,
        )
        ui.section("Model calibration")
        slope_band = (
            "high"
            if slope_cal is not None and (slope_cal < 0.85 or slope_cal > 1.15)
            else "explained"
        )
        st.markdown(
            f"Calibrated slope target band <strong>0.85 – 1.15</strong>. Current: "
            f"<strong>{slope_cal:.3f}</strong> {ui.status_pill(slope_band, slope_band)}."
            if slope_cal is not None
            else "Calibration data not available.",
            unsafe_allow_html=True,
        )
    else:
        ui.empty_state(
            "Eval report not found.",
            "Run `make demo` once to produce `artifacts/eval_report.json`, then refresh.",
        )

    if frames.practice is not None and len(frames.practice) > 0:
        ui.section("Network exposure by specialty")
        spec = (
            frames.practice.group_by("practice_specialty")
            .agg(
                pl.col("expected_recovery_calibrated").sum().alias("expected_recovery"),
                pl.col("total_at_risk").sum().alias("total_at_risk"),
                pl.col("n_exceptions").sum().alias("n_exceptions"),
                pl.len().alias("n_practices"),
            )
            .sort("expected_recovery", descending=True)
        )
        st.dataframe(
            spec,
            hide_index=True,
            use_container_width=True,
            column_config={
                "practice_specialty": st.column_config.TextColumn("Specialty"),
                "n_practices": st.column_config.NumberColumn("Practices", format="%d"),
                "n_exceptions": st.column_config.NumberColumn("Exceptions", format="%d"),
                "total_at_risk": st.column_config.NumberColumn("Dollars at risk", format="$%.0f"),
                "expected_recovery": st.column_config.NumberColumn(
                    "Expected recovery", format="$%.0f"
                ),
            },
        )

    ui.app_footer(version=__version__, model_run_id=str(model_run_id) if model_run_id else None)
    if presenter:
        st.markdown(
            '<div class="hint" style="text-align:center;margin-top:0.5rem;color:var(--color-text-faint);">'
            "presenter mode · sidebar hidden · append <code>?presenter=1</code> to any page URL</div>",
            unsafe_allow_html=True,
        )


main()
