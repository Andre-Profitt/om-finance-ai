"""Audit Trail — append-only override log with model + prompt + source lineage."""

from __future__ import annotations

import polars as pl
import streamlit as st

from oaifinance import __version__
from oaifinance.ui import components as ui
from oaifinance.ui import data as ud
from oaifinance.ui import styles

st.set_page_config(
    page_title="Audit Trail · Control Tower",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()
styles.maybe_presenter_mode()

frames = ud.load_all()
override = frames.override

if override is None or len(override) == 0:
    ui.page_header("Audit trail", "Override log empty.")
    ui.empty_state(
        "No override decisions recorded.",
        "Run `make demo` to simulate top-100 reviewer decisions on the latest queue.",
    )
    st.stop()

n_decisions = len(override)
agree_rate = float(override["agreed_with_model"].mean())
n_abstention = int(override["was_abstention"].sum())
total_dollars = float(override["dollars_at_risk"].sum())

ui.page_header(
    "Audit trail",
    "Append-only reviewer-decision log with model + prompt + source lineage. SOX-aligned change control.",
    n_rows=n_decisions,
)
ui.governance_ribbon()

ui.kpi_grid(
    [
        ("Decisions", f"{n_decisions:,}", "append-only"),
        ("Reviewer agreement", ui.fmt_pct(agree_rate, places=0), None),
        ("On abstained items", f"{n_abstention:,}", "human-first decisions"),
        ("Dollars reviewed", ui.fmt_dollars(total_dollars), None),
    ]
)

ui.section("Filters")
reviewer_ids = sorted(override["reviewer_id"].unique().to_list())
decisions = sorted(override["decision"].unique().to_list())
rationales = sorted(override["rationale_category"].unique().to_list())

# decided_at is ISO-8601 with timezone offset; parse with explicit format
# so polars doesn't complain about ambiguous tz-handling on auto-inference.
override_dt = override.with_columns(
    pl.col("decided_at")
    .str.to_datetime(format="%Y-%m-%dT%H:%M:%S%.f%:z", strict=False)
    .alias("_decided_at_ts")
)
ts_min = override_dt["_decided_at_ts"].min()
ts_max = override_dt["_decided_at_ts"].max()

f1, f2, f3, f4 = st.columns([1.2, 1, 1, 1])
with f1:
    if ts_min is not None and ts_max is not None:
        date_range = st.date_input(
            "Decision date range",
            value=(ts_min.date(), ts_max.date()),
            min_value=ts_min.date(),
            max_value=ts_max.date(),
        )
    else:
        date_range = None
with f2:
    selected_reviewers = st.multiselect("Reviewer", reviewer_ids, default=reviewer_ids)
with f3:
    selected_decisions = st.multiselect("Decision", decisions, default=decisions)
with f4:
    selected_rationales = st.multiselect("Rationale", rationales, default=rationales)

filtered = override_dt.filter(
    pl.col("reviewer_id").is_in(selected_reviewers)
    & pl.col("decision").is_in(selected_decisions)
    & pl.col("rationale_category").is_in(selected_rationales)
)
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    filtered = filtered.filter(
        (pl.col("_decided_at_ts").dt.date() >= start) & (pl.col("_decided_at_ts").dt.date() <= end)
    )
filtered = filtered.drop("_decided_at_ts").sort("decided_at", descending=True)

ui.section(f"Log ({len(filtered):,} rows after filters)")
st.dataframe(
    filtered.select(
        "override_id",
        "exception_id",
        "reviewer_id",
        "decision",
        "agreed_with_model",
        "was_abstention",
        "rationale_category",
        "original_calibrated_score",
        "dollars_at_risk",
        "decided_at",
        "model_run_id",
    ),
    hide_index=True,
    use_container_width=True,
    height=560,
    column_config={
        "override_id": st.column_config.TextColumn("Override ID", width="small"),
        "exception_id": st.column_config.TextColumn("Claim", width="small"),
        "reviewer_id": st.column_config.TextColumn("Reviewer", width="small"),
        "decision": st.column_config.TextColumn("Decision", width="small"),
        "agreed_with_model": st.column_config.CheckboxColumn("Agreed", width="small"),
        "was_abstention": st.column_config.CheckboxColumn("Abstained", width="small"),
        "rationale_category": st.column_config.TextColumn("Rationale", width="medium"),
        "original_calibrated_score": st.column_config.ProgressColumn(
            "Calibrated risk", format="%.3f", min_value=0.0, max_value=1.0
        ),
        "dollars_at_risk": st.column_config.NumberColumn("$", format="$%.0f"),
        "decided_at": st.column_config.TextColumn("Decided at", width="medium"),
        "model_run_id": st.column_config.TextColumn("Model run", width="small"),
    },
)

ui.section("Retention")
st.markdown(
    "This view reflects the append-only override log per `docs/governance.md` §7. "
    "Production retention is 7 years on encrypted blob storage with customer-managed keys.",
    unsafe_allow_html=True,
)

ui.app_footer(version=__version__)
