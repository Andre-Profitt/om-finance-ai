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

f1, f2, f3 = st.columns(3)
with f1:
    selected_reviewers = st.multiselect("Reviewer", reviewer_ids, default=reviewer_ids)
with f2:
    selected_decisions = st.multiselect("Decision", decisions, default=decisions)
with f3:
    selected_rationales = st.multiselect("Rationale", rationales, default=rationales)

filtered = override.filter(
    pl.col("reviewer_id").is_in(selected_reviewers)
    & pl.col("decision").is_in(selected_decisions)
    & pl.col("rationale_category").is_in(selected_rationales)
).sort("decided_at", descending=True)

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
