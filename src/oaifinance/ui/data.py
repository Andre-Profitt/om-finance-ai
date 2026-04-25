"""Cached data loaders for the Streamlit app."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD = REPO_ROOT / "data" / "gold"
ARTIFACTS = REPO_ROOT / "artifacts"


BRONZE = REPO_ROOT / "data" / "bronze"


@dataclass
class Frames:
    scored: pl.DataFrame | None
    explained: pl.DataFrame | None
    practice: pl.DataFrame | None
    override: pl.DataFrame | None
    claims: pl.DataFrame | None
    eval_report: dict | None


@st.cache_data(ttl=120, show_spinner=False)
def load_all() -> Frames:
    def _read(path: Path) -> pl.DataFrame | None:
        return pl.read_parquet(path) if path.exists() else None

    eval_report: dict | None = None
    eval_path = ARTIFACTS / "eval_report.json"
    if eval_path.exists():
        try:
            eval_report = json.loads(eval_path.read_text())
        except json.JSONDecodeError:
            eval_report = None

    return Frames(
        scored=_read(GOLD / "scored_exceptions.parquet"),
        explained=_read(GOLD / "explained_exceptions.parquet"),
        practice=_read(GOLD / "practice_performance.parquet"),
        override=_read(GOLD / "override_log.parquet"),
        claims=_read(BRONZE / "claims_raw.parquet"),
        eval_report=eval_report,
    )


@st.cache_data(ttl=120, show_spinner=False)
def daily_exposure_series() -> dict[str, list[float]]:
    """Daily aggregations over claim service_date for sparkline KPIs."""
    f = load_all()
    if f.claims is None:
        return {}
    by_day = (
        f.claims.with_columns(pl.col("service_date").cast(pl.Date))
        .group_by("service_date")
        .agg(
            pl.len().alias("n_claims"),
            pl.col("allowed_total").sum().alias("dollars_billed"),
            pl.col("_true_leakage_amount").sum().alias("leakage_dollars"),
            pl.col("_true_leakage").cast(pl.Int8).sum().alias("n_leakage"),
            pl.col("access_delay_cost").sum().alias("access_delay"),
        )
        .sort("service_date")
    )
    return {
        "n_claims": [float(x) for x in by_day["n_claims"].to_list()],
        "dollars_billed": [float(x) for x in by_day["dollars_billed"].to_list()],
        "leakage_dollars": [float(x) for x in by_day["leakage_dollars"].to_list()],
        "n_leakage": [float(x) for x in by_day["n_leakage"].to_list()],
        "access_delay": [float(x) for x in by_day["access_delay"].to_list()],
    }


@st.cache_data(ttl=120, show_spinner=False)
def merged_queue() -> pl.DataFrame | None:
    f = load_all()
    if f.scored is None or f.explained is None:
        return None
    return f.scored.join(
        f.explained.select(
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


def rank_col(df: pl.DataFrame) -> str:
    if "expected_recovery_calibrated" in df.columns:
        return "expected_recovery_calibrated"
    return "expected_recovery"
