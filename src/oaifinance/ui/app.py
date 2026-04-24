"""Streamlit reviewer-queue mock.

Run: `make reviewer-ui` (or `uv run streamlit run src/oaifinance/ui/app.py`)

Reads the pipeline outputs from `data/gold/` and renders the top-k reviewer
queue with cited explanations, abstention flags, and mock disposition
actions. Not a production UI — a product mock that shows what the reviewer
workflow looks like end-to-end on synthetic data.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD = REPO_ROOT / "data" / "gold"
SCORED = GOLD / "scored_exceptions.parquet"
EXPLAINED = GOLD / "explained_exceptions.parquet"
PRACTICE = GOLD / "practice_performance.parquet"


@st.cache_data(show_spinner=False)
def _load() -> dict[str, pl.DataFrame]:
    frames: dict[str, pl.DataFrame] = {}
    if SCORED.exists():
        frames["scored"] = pl.read_parquet(SCORED)
    if EXPLAINED.exists():
        frames["explained"] = pl.read_parquet(EXPLAINED)
    if PRACTICE.exists():
        frames["practice"] = pl.read_parquet(PRACTICE)
    return frames


def _dollars(x: float) -> str:
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:.2f}M"
    if abs(x) >= 1_000:
        return f"${x / 1_000:.1f}K"
    return f"${x:,.0f}"


def main() -> None:
    st.set_page_config(page_title="O&M Finance AI Control Tower", layout="wide")
    st.title("O&M Finance AI Control Tower — Reviewer Queue")
    st.caption(
        "Mock reviewer workflow on synthetic data. Drug prices anchored to public CMS ASP. No PHI."
    )

    frames = _load()
    if "scored" not in frames or "explained" not in frames:
        st.error("Pipeline outputs not found under data/gold/. Run `make demo` first.")
        return

    scored = frames["scored"]
    explained = frames["explained"]
    merged = scored.join(
        explained.select(
            "claim_id",
            "citation_doc_id",
            "citation_section",
            "citation_score",
            "explained",
            "abstained",
            "explanation_text",
        ),
        on="claim_id",
        how="left",
    )

    rank_col = (
        "expected_recovery_calibrated"
        if "expected_recovery_calibrated" in merged.columns
        else "expected_recovery"
    )

    with st.sidebar:
        st.header("Filters")
        specialties = sorted(merged["practice_specialty"].unique().to_list())
        selected_specialties = st.multiselect(
            "Practice specialty", specialties, default=specialties
        )
        exception_types = sorted(merged["exception_type"].unique().to_list())
        selected_types = st.multiselect("Exception type", exception_types, default=exception_types)
        top_k = st.slider("Queue size (top-k)", min_value=20, max_value=200, value=50, step=10)
        show_abstained_only = st.checkbox("Abstained only")

    filtered = merged.filter(
        pl.col("practice_specialty").is_in(selected_specialties)
        & pl.col("exception_type").is_in(selected_types)
    )
    if show_abstained_only:
        filtered = filtered.filter(pl.col("abstained"))

    queue = filtered.sort(rank_col, descending=True).head(top_k)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Items in queue", f"{len(queue):,}")
    c2.metric(
        "Total dollars at risk",
        _dollars(float(queue["dollars_at_risk"].sum())) if len(queue) else "$0",
    )
    c3.metric(
        "Expected recovery",
        _dollars(float(queue[rank_col].sum())) if len(queue) else "$0",
    )
    c4.metric(
        "Abstention rate",
        f"{float(queue['abstained'].mean() * 100) if len(queue) else 0:.1f}%",
    )

    st.subheader("Reviewer queue")
    display_cols = [
        "claim_id",
        "practice_id",
        "practice_specialty",
        "payer",
        "hcpcs_code",
        "exception_type",
        "dollars_at_risk",
        "risk_score_calibrated",
        rank_col,
        "citation_doc_id",
        "citation_section",
        "abstained",
    ]
    display_cols = [c for c in display_cols if c in queue.columns]
    st.dataframe(queue.select(display_cols), hide_index=True, use_container_width=True)

    st.subheader("Drill-in")
    if len(queue) > 0:
        claim_options = queue["claim_id"].to_list()
        selected = st.selectbox("Claim", claim_options, index=0)
        row = merged.filter(pl.col("claim_id") == selected).row(0, named=True)

        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"### {row['claim_id']}  ·  {row['exception_type']}")
            st.write(
                f"**{row['practice_id']}** ({row['practice_specialty']})  ·  "
                f"**{row['payer']}**  ·  HCPCS `{row['hcpcs_code']}`  ·  NDC `{row['ndc_code']}`"
            )
            st.markdown("#### Explanation")
            text = row.get("explanation_text") or "(no explanation produced)"
            if row.get("abstained"):
                st.warning(text)
            else:
                st.info(text)

            if row.get("citation_doc_id"):
                st.caption(
                    f"Cited: **{row['citation_doc_id']}** § {row['citation_section']}"
                    f"  ·  similarity {float(row.get('citation_score') or 0):.3f}"
                )

            st.markdown("#### Mock disposition")
            b1, b2, b3 = st.columns(3)
            if b1.button("Approve / submit"):
                st.success(
                    "(mock) override_log would write decision=approve with rationale=agree_submit"
                )
            if b2.button("Escalate to coding"):
                st.success(
                    "(mock) override_log would write decision=escalate with rationale=escalate_coding_team"
                )
            if b3.button("Reject"):
                st.success(
                    "(mock) override_log would write decision=reject with rationale=disagree_legitimate_claim"
                )

        with right:
            st.markdown("#### Risk + $")
            st.metric("Dollars at risk", _dollars(float(row["dollars_at_risk"])))
            st.metric(
                "Calibrated risk",
                f"{float(row.get('risk_score_calibrated') or 0):.3f}",
            )
            st.metric(
                "Expected recovery",
                _dollars(float(row.get(rank_col) or 0)),
            )
            st.caption(
                f"Model run: `{row.get('model_run_id', '—')[:10] if row.get('model_run_id') else '—'}…`"
            )

    if "practice" in frames:
        with st.expander("Network view — per-practice exposure"):
            st.dataframe(
                frames["practice"].sort("expected_recovery_calibrated", descending=True),
                hide_index=True,
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
