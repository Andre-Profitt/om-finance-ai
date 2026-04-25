"""Model Ops — calibration health, abstention trends, override agreement."""

from __future__ import annotations

import polars as pl
import streamlit as st

from oaifinance import __version__
from oaifinance.ui import components as ui
from oaifinance.ui import data as ud
from oaifinance.ui import styles

st.set_page_config(
    page_title="Model Ops · Control Tower",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()
styles.maybe_presenter_mode()

frames = ud.load_all()
report = frames.eval_report
explained = frames.explained
override = frames.override
scored = frames.scored

if report is None or scored is None:
    ui.page_header("Model ops", "Eval report not found.")
    ui.empty_state("Run `make demo` to produce `artifacts/eval_report.json`.")
    st.stop()

slope_uncal = report.get("calibration_slope")
slope_cal = report.get("calibration_slope_calibrated")
auc = report.get("auc")
cit_p = report.get("citation_precision")
abst = report.get("abstention_rate")
n_exceptions = report.get("n_exceptions")

ui.page_header(
    "Model ops",
    "Calibration health · citation quality · reviewer agreement.",
    n_rows=n_exceptions,
)

ui.kpi_grid(
    [
        ("Calibration (uncal)", ui.fmt_score(slope_uncal), "target band 0.85–1.15"),
        ("Calibration (isotonic)", ui.fmt_score(slope_cal), "5-fold CV"),
        ("AUC (debug)", ui.fmt_score(auc), "internal model-debug only"),
        ("Citation precision", ui.fmt_pct(cit_p), None),
        ("Abstention rate", ui.fmt_pct(abst), None),
    ]
)

ui.section("Calibration plot")
from oaifinance.config import ARTIFACTS_DIR

_cal_png = ARTIFACTS_DIR / "calibration.png"
_cap_png = ARTIFACTS_DIR / "capture_curves.png"
img_cols = st.columns(2)
with img_cols[0]:
    if _cal_png.exists():
        st.image(
            str(_cal_png),
            caption="Predicted vs. observed leakage rate by score decile (uncal vs. isotonic)",
            use_container_width=True,
        )
    else:
        ui.empty_state(
            "calibration.png not found.", "Run `make demo` to regenerate eval artifacts."
        )
with img_cols[1]:
    if _cap_png.exists():
        st.image(
            str(_cap_png),
            caption="Leakage capture vs. reviewer effort across three rankings",
            use_container_width=True,
        )
    else:
        ui.empty_state(
            "capture_curves.png not found.", "Run `make demo` to regenerate eval artifacts."
        )

ui.section("Calibration band")
if slope_cal is not None:
    in_band = 0.85 <= slope_cal <= 1.15
    pill_kind = "explained" if in_band else "abstained"
    msg = "within target band" if in_band else "outside target band — refresh queued"
    st.markdown(
        f"Current calibrated slope <strong>{slope_cal:.3f}</strong> · "
        f"{ui.status_pill(msg, pill_kind)}",
        unsafe_allow_html=True,
    )

ui.section("Citation precision by exception type")
cit_by_type = report.get("citation_precision_by_type") or {}
if cit_by_type:
    cit_df = pl.DataFrame(
        [{"exception_type": k, "precision": float(v)} for k, v in cit_by_type.items()]
    ).sort("precision", descending=True)
    st.dataframe(
        cit_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "exception_type": st.column_config.TextColumn("Exception type"),
            "precision": st.column_config.ProgressColumn(
                "Precision", format="%.1%%", min_value=0.0, max_value=1.0
            ),
        },
    )
else:
    ui.empty_state("Citation eval not present in this run.")

ui.section("Specialty coverage across all candidates")
exposure = report.get("exposure_by_specialty") or {}
candidates = report.get("candidates_by_specialty") or {}
if exposure:
    rows = [
        {
            "specialty": k,
            "candidates": int(candidates.get(k, 0)),
            "dollars_at_risk": float(v),
        }
        for k, v in sorted(exposure.items(), key=lambda kv: -kv[1])
    ]
    st.dataframe(
        pl.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "specialty": st.column_config.TextColumn("Specialty"),
            "candidates": st.column_config.NumberColumn("Candidates", format="%d"),
            "dollars_at_risk": st.column_config.NumberColumn("$ at risk", format="$%.0f"),
        },
    )
else:
    ui.empty_state("Specialty exposure not present in this run.")

if explained is not None:
    ui.section("Abstention by exception type")
    abst_df = (
        explained.group_by("exception_type")
        .agg(
            pl.len().alias("n"),
            pl.col("abstained").cast(pl.Int8).sum().alias("n_abstained"),
            pl.col("explained").cast(pl.Int8).sum().alias("n_explained"),
        )
        .with_columns((pl.col("n_abstained") / pl.col("n")).alias("abstention_rate"))
        .sort("abstention_rate", descending=True)
    )
    st.dataframe(
        abst_df.select("exception_type", "n", "n_abstained", "abstention_rate"),
        hide_index=True,
        use_container_width=True,
        column_config={
            "exception_type": st.column_config.TextColumn("Exception type"),
            "n": st.column_config.NumberColumn("Total", format="%d"),
            "n_abstained": st.column_config.NumberColumn("Abstained", format="%d"),
            "abstention_rate": st.column_config.ProgressColumn(
                "Abstention rate", format="%.1%%", min_value=0.0, max_value=1.0
            ),
        },
    )

if override is not None and len(override) > 0:
    ui.section("Reviewer agreement (simulated)")
    agree_rate = float(override["agreed_with_model"].mean())
    n_decisions = len(override)
    by_decision = override.group_by("decision").len().sort("len", descending=True)
    by_rationale = override.group_by("rationale_category").len().sort("len", descending=True)

    ui.kpi_grid(
        [
            ("Decisions logged", f"{n_decisions:,}", None),
            ("Reviewer agreement", ui.fmt_pct(agree_rate, places=0), None),
        ],
        accent_first=False,
    )

    a, b = st.columns(2)
    with a:
        st.markdown('<div class="section-h">By decision</div>', unsafe_allow_html=True)
        st.dataframe(
            by_decision,
            hide_index=True,
            use_container_width=True,
            column_config={
                "decision": st.column_config.TextColumn("Decision"),
                "len": st.column_config.NumberColumn("Count", format="%d"),
            },
        )
    with b:
        st.markdown('<div class="section-h">By rationale</div>', unsafe_allow_html=True)
        st.dataframe(
            by_rationale,
            hide_index=True,
            use_container_width=True,
            column_config={
                "rationale_category": st.column_config.TextColumn("Rationale"),
                "len": st.column_config.NumberColumn("Count", format="%d"),
            },
        )

ui.app_footer(version=__version__)
