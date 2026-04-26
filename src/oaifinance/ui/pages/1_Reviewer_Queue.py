"""Reviewer Queue — top-N work queue with cited explanations."""

from __future__ import annotations

import polars as pl
import streamlit as st

from oaifinance import __version__
from oaifinance.ui import components as ui
from oaifinance.ui import data as ud
from oaifinance.ui import styles

st.set_page_config(
    page_title="Reviewer Queue · Control Tower",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()
styles.maybe_presenter_mode()

merged = ud.merged_queue()
frames = ud.load_all()

if merged is None:
    ui.page_header(
        "Reviewer queue",
        "Pipeline outputs not found.",
    )
    ui.empty_state("Run `make demo` to populate the queue.")
    st.stop()

rank_col = ud.rank_col(merged)
specialties = sorted(merged["practice_specialty"].unique().to_list())
exception_types = sorted(merged["exception_type"].unique().to_list())
payers = sorted(merged["payer"].unique().to_list())

with st.sidebar:
    st.markdown(
        '<div class="section-h" style="margin-top:0;">Filters</div>', unsafe_allow_html=True
    )
    selected_specialties = st.multiselect("Practice specialty", specialties, default=specialties)
    selected_types = st.multiselect("Exception type", exception_types, default=exception_types)
    selected_payers = st.multiselect("Payer", payers, default=payers)
    top_k = st.slider("Queue size", min_value=20, max_value=200, value=50, step=10)
    show_abstained_only = st.checkbox("Abstained only", value=False)
    min_dollars = st.number_input(
        "Minimum dollars at risk", min_value=0, value=0, step=1000, format="%d"
    )

filtered = merged.filter(
    pl.col("practice_specialty").is_in(selected_specialties)
    & pl.col("exception_type").is_in(selected_types)
    & pl.col("payer").is_in(selected_payers)
    & (pl.col("dollars_at_risk") >= min_dollars)
)
if show_abstained_only:
    filtered = filtered.filter(pl.col("abstained"))

queue = filtered.sort(rank_col, descending=True).head(top_k)

model_run_id = (
    str(queue["model_run_id"][0]) if len(queue) and "model_run_id" in queue.columns else None
)

ui.page_header(
    "Reviewer queue",
    f"Top-{top_k} ranked by calibrated expected recovery.",
    run_id=model_run_id,
    n_rows=len(queue),
)

n = len(queue)
total_dollars = float(queue["dollars_at_risk"].sum()) if n else 0.0
expected = float(queue[rank_col].sum()) if n else 0.0
abstention_share = (
    float(queue["abstained"].fill_null(False).cast(pl.Float64).mean() * 100) if n else 0.0
)
n_specialties = queue["practice_specialty"].n_unique() if n else 0

ui.kpi_grid(
    [
        ("Items", f"{n:,}", "after filters + top-k"),
        ("Dollars at risk", ui.fmt_dollars(total_dollars), None),
        ("Expected recovery", ui.fmt_dollars(expected), None),
        ("Abstention share", f"{abstention_share:.1f}%", "system declined to cite"),
        ("Specialties present", str(n_specialties), None),
    ],
    accent_first=True,
)

if n == 0:
    ui.empty_state(
        "No exceptions match your filters.",
        "Loosen a filter or increase the queue size.",
    )
    st.stop()

ui.section("Queue")
queue_display = queue.with_columns(
    pl.when(pl.col("abstained"))
    .then(pl.lit("abstained"))
    .when(pl.col("explained"))
    .then(pl.lit("explained"))
    .otherwise(pl.lit("unscored"))
    .alias("status"),
).select(
    "claim_id",
    "practice_id",
    "practice_specialty",
    "payer",
    "hcpcs_code",
    "exception_type",
    "dollars_at_risk",
    "risk_score_calibrated",
    rank_col,
    "status",
    "citation_doc_id",
    "citation_score",
)

selection = st.dataframe(
    queue_display,
    hide_index=True,
    use_container_width=True,
    height=420,
    on_select="rerun",
    selection_mode="multi-row",
    key="queue_table",
    column_config={
        "claim_id": st.column_config.TextColumn("Claim", width="small"),
        "practice_id": st.column_config.TextColumn("Practice", width="small"),
        "practice_specialty": st.column_config.TextColumn("Specialty", width="small"),
        "payer": st.column_config.TextColumn("Payer", width="small"),
        "hcpcs_code": st.column_config.TextColumn("HCPCS", width="small"),
        "exception_type": st.column_config.TextColumn("Type", width="medium"),
        "dollars_at_risk": st.column_config.NumberColumn("$ at risk", format="$%.0f"),
        "risk_score_calibrated": st.column_config.ProgressColumn(
            "Risk (calibrated)",
            format="%.3f",
            min_value=0.0,
            max_value=1.0,
        ),
        rank_col: st.column_config.NumberColumn("Expected recovery", format="$%.0f"),
        "status": st.column_config.TextColumn("Status", width="small"),
        "citation_doc_id": st.column_config.TextColumn("Citation source", width="medium"),
        "citation_score": st.column_config.ProgressColumn(
            "Cite sim",
            format="%.2f",
            min_value=0.0,
            max_value=1.0,
        ),
    },
)

selected_rows = []
try:
    selected_rows = list(selection.selection.rows) if selection else []
except Exception:
    selected_rows = []

if selected_rows:
    selected_claim_ids = [queue["claim_id"][i] for i in selected_rows]
    bulk_dollars = sum(float(queue["dollars_at_risk"][i]) for i in selected_rows)
    ui.section(f"Bulk action — {len(selected_claim_ids)} selected ({ui.fmt_dollars(bulk_dollars)})")
    st.markdown(
        '<div class="hint">Bulk dispositions are previewed only; the override log is not written from this view.</div>',
        unsafe_allow_html=True,
    )
    bb = st.columns([1, 1, 1, 1, 3])
    if bb[0].button("Approve all", use_container_width=True, key="bulk_approve"):
        st.toast(
            f"Preview: approve · {len(selected_claim_ids)} items · {ui.fmt_dollars(bulk_dollars)}"
        )
    if bb[1].button("Resubmit all", use_container_width=True, key="bulk_resubmit"):
        st.toast(f"Preview: resubmit corrected · {len(selected_claim_ids)} items")
    if bb[2].button("Escalate all", use_container_width=True, key="bulk_escalate"):
        st.toast(f"Preview: escalate · {len(selected_claim_ids)} items")
    if bb[3].button("Reject all", use_container_width=True, key="bulk_reject"):
        st.toast(f"Preview: reject · {len(selected_claim_ids)} items")
    drill_default_index = selected_rows[0]
else:
    drill_default_index = 0

ui.section("Drill-in")
queue_claim_ids = queue["claim_id"].to_list()
selected = st.selectbox(
    "Select a claim",
    queue_claim_ids,
    index=min(drill_default_index, len(queue_claim_ids) - 1),
    label_visibility="collapsed",
)
row = merged.filter(pl.col("claim_id") == selected).row(0, named=True)

left, right = st.columns([2, 1])

with left:
    pills = " ".join(
        [
            ui.explained_pill(bool(row.get("explained")), bool(row.get("abstained"))),
            ui.severity_pill(float(row.get("risk_score_calibrated") or 0.0)),
            ui.specialty_pill(row.get("practice_specialty")),
        ]
    )
    st.markdown(
        f"""
<div style="margin-bottom: 0.75rem;">
  <span style="font-size: 1.1rem; font-weight: 600;">{row["claim_id"]}</span>
  <span style="color: var(--color-text-muted); margin-left: 0.5rem;">·</span>
  <span style="color: var(--color-text-muted); margin-left: 0.25rem; font-size: 0.95rem;">{row["exception_type"]}</span>
  <span style="margin-left: 0.75rem;">{pills}</span>
</div>
<div style="color: var(--color-text-muted); font-size: 0.85rem;">
  Practice <strong>{row["practice_id"]}</strong> · Payer <strong>{row["payer"]}</strong>
  · HCPCS <code>{row["hcpcs_code"]}</code> · NDC <code>{row["ndc_code"]}</code>
</div>
""",
        unsafe_allow_html=True,
    )

    text = row.get("explanation_text") or "No explanation produced."
    if row.get("abstained"):
        ui.section("Abstention")
        st.markdown(
            f'<div class="citation-card" style="border-color: #fde68a; background: var(--color-warning-soft);">{text}</div>',
            unsafe_allow_html=True,
        )
    else:
        ui.section("Explanation")
        st.markdown(
            f'<div class="citation-card" style="background: var(--color-bg);">{text}</div>',
            unsafe_allow_html=True,
        )
        if row.get("citation_doc_id"):
            ui.citation_card(
                doc_id=row.get("citation_doc_id"),
                section_title=row.get("citation_section"),
                similarity=float(row.get("citation_score") or 0.0),
                clause=row.get("citation_doc_id", "") + " · " + (row.get("citation_section") or ""),
            )

    ui.section("Disposition (preview)")
    st.markdown(
        '<div class="hint">Disposition actions are previewed in this view; the override log is not written until the action is bound to a reviewer session in production.</div>',
        unsafe_allow_html=True,
    )
    b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
    if b1.button("Approve", use_container_width=True):
        st.toast(f"Recorded preview: approve · rationale=agree_submit · {row['claim_id']}")
    if b2.button("Resubmit corrected", use_container_width=True):
        st.toast(
            f"Recorded preview: resubmit · rationale=agree_resubmit_corrected · {row['claim_id']}"
        )
    if b3.button("Escalate", use_container_width=True):
        st.toast(f"Recorded preview: escalate · rationale=escalate_coding_team · {row['claim_id']}")
    if b4.button("Reject", use_container_width=True):
        st.toast(
            f"Recorded preview: reject · rationale=disagree_legitimate_claim · {row['claim_id']}"
        )

with right:
    ui.kpi_grid(
        [
            ("Dollars at risk", ui.fmt_dollars(float(row["dollars_at_risk"])), None),
            (
                "Calibrated risk",
                ui.fmt_score(float(row.get("risk_score_calibrated") or 0.0)),
                None,
            ),
            (
                "Expected recovery",
                ui.fmt_dollars(float(row.get(rank_col) or 0.0)),
                None,
            ),
            (
                "Cite similarity",
                ui.fmt_score(float(row.get("citation_score") or 0.0), places=2),
                None,
            ),
        ],
        accent_first=False,
    )

    ui.section("Lineage")
    st.markdown(
        f"""
<div class="kpi-card">
  <div class="label">Model</div>
  <div class="value" style="font-size: 0.9rem; font-weight: 500;">{row.get("model_name", "—")}</div>
  <div class="footnote">run <code>{(row.get("model_run_id") or "")[:10]}…</code></div>
</div>
""",
        unsafe_allow_html=True,
    )

ui.app_footer(
    version=__version__,
    model_run_id=str(row.get("model_run_id") or "") or None,
)
