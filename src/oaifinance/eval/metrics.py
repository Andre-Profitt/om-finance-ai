"""Business-outcome eval metrics.

Two rankings are reported so the TPM demo surfaces the core product tradeoff:
- `risk_score` queue: highest-probability leakage first (maximizes precision)
- `expected_recovery` queue: P(leakage) × dollars-at-risk (maximizes $ captured)

A rules-only baseline (uniform review of all candidates) is also reported.

When an `explained` frame is provided, citation precision and abstention rate
are rolled into the headline report.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import polars as pl

from oaifinance.config import REVIEWER_LOADED_HOURLY, REVIEWER_REVIEW_MINUTES
from oaifinance.eval.citation import evaluate as evaluate_citations


@dataclass
class RankedReport:
    rank_by: str
    precision_at_20: float
    precision_at_50: float
    precision_at_100: float
    dollars_captured_at_20: float
    dollars_captured_at_50: float
    dollars_captured_at_100: float
    dollars_per_reviewer_hour_at_100: float


@dataclass
class EvalReport:
    n_exceptions: int
    n_all_claims: int | None
    base_rate_candidates: float
    base_rate_all_claims: float | None
    dollars_at_risk_total: float
    auc: float
    calibration_slope: float
    calibration_intercept: float
    calibration_slope_calibrated: float | None
    by_risk_score: RankedReport
    by_expected_recovery: RankedReport
    by_expected_recovery_calibrated: RankedReport | None
    rules_only_baseline_dollars: float
    rules_only_baseline_hours: float
    uplift_dollars_vs_rules_at_100: float
    citation_precision: float | None
    abstention_rate: float | None
    citation_precision_by_type: dict[str, float] = field(default_factory=dict)
    precision_by_specialty: dict[str, float] = field(default_factory=dict)
    dollars_captured_by_specialty: dict[str, float] = field(default_factory=dict)
    exposure_by_specialty: dict[str, float] = field(default_factory=dict)
    candidates_by_specialty: dict[str, int] = field(default_factory=dict)


def _auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    order = np.argsort(-y_score)
    y = y_true[order]
    pos = float(y.sum())
    neg = float(len(y) - pos)
    if pos == 0 or neg == 0:
        return float("nan")
    cum_pos = np.cumsum(y)
    return float((cum_pos * (1 - y)).sum() / (pos * neg))


def _calibration(y_true: np.ndarray, y_score: np.ndarray, bins: int = 10) -> tuple[float, float]:
    if len(np.unique(y_score)) < 2:
        return float("nan"), float("nan")
    bucket = np.clip((y_score * bins).astype(int), 0, bins - 1)
    xs, ys = [], []
    for b in range(bins):
        mask = bucket == b
        if mask.sum() < 5:
            continue
        xs.append(float(y_score[mask].mean()))
        ys.append(float(y_true[mask].mean()))
    if len(xs) < 2:
        return float("nan"), float("nan")
    slope, intercept = np.polyfit(np.array(xs), np.array(ys), 1)
    return float(slope), float(intercept)


def _rank_metrics(scored: pl.DataFrame, rank_col: str) -> RankedReport:
    ranked = scored.sort(rank_col, descending=True)

    def metrics_at(k: int) -> tuple[float, float]:
        top = ranked.head(k)
        if len(top) == 0:
            return 0.0, 0.0
        precision = float(top["_true_leakage"].sum() / len(top))
        dollars = float(top["_true_leakage_amount"].sum())
        return precision, dollars

    p20, d20 = metrics_at(20)
    p50, d50 = metrics_at(50)
    p100, d100 = metrics_at(100)
    hours_100 = (100 * REVIEWER_REVIEW_MINUTES) / 60.0
    return RankedReport(
        rank_by=rank_col,
        precision_at_20=p20,
        precision_at_50=p50,
        precision_at_100=p100,
        dollars_captured_at_20=d20,
        dollars_captured_at_50=d50,
        dollars_captured_at_100=d100,
        dollars_per_reviewer_hour_at_100=d100 / hours_100 if hours_100 > 0 else 0.0,
    )


def evaluate(
    scored: pl.DataFrame,
    all_claims: pl.DataFrame | None = None,
    explained: pl.DataFrame | None = None,
) -> EvalReport:
    y_true = scored["_true_leakage"].cast(pl.Int8).to_numpy()
    y_score = scored["risk_score"].to_numpy()

    auc = _auc(y_true, y_score)
    slope, intercept = _calibration(y_true.astype(float), y_score)

    slope_cal = None
    by_recovery_cal = None
    if "risk_score_calibrated" in scored.columns:
        s_cal = scored["risk_score_calibrated"].to_numpy()
        slope_cal, _ = _calibration(y_true.astype(float), s_cal)
        by_recovery_cal = _rank_metrics(scored, "expected_recovery_calibrated")

    by_risk = _rank_metrics(scored, "risk_score")
    by_recovery = _rank_metrics(scored, "expected_recovery")

    total_at_risk = float(scored["_true_leakage_amount"].sum())
    rules_only_dollars = total_at_risk
    rules_only_hours = (len(scored) * REVIEWER_REVIEW_MINUTES) / 60.0

    uplift = by_recovery.dollars_captured_at_100 - (
        rules_only_dollars * (100.0 / max(len(scored), 1))
    )

    n_all = int(len(all_claims)) if all_claims is not None else None
    base_all = float(all_claims["_true_leakage"].mean()) if all_claims is not None else None

    cit_precision = None
    abst_rate = None
    cit_by_type: dict[str, float] = {}
    if explained is not None:
        c = evaluate_citations(explained)
        cit_precision = c.citation_precision
        abst_rate = c.abstention_rate
        cit_by_type = c.precision_by_type

    # Per-specialty slicing on the calibrated expected-recovery ranking.
    rank_col = (
        "expected_recovery_calibrated"
        if "expected_recovery_calibrated" in scored.columns
        else "expected_recovery"
    )
    ranked = scored.sort(rank_col, descending=True).head(100)
    precision_by_specialty: dict[str, float] = {}
    dollars_by_specialty: dict[str, float] = {}
    exposure_by_specialty: dict[str, float] = {}
    candidates_by_specialty: dict[str, int] = {}
    if "practice_specialty" in ranked.columns and len(ranked) > 0:
        by_spec = ranked.group_by("practice_specialty").agg(
            pl.col("_true_leakage").cast(pl.Int8).sum().alias("n_leakage"),
            pl.len().alias("n"),
            pl.col("_true_leakage_amount").sum().alias("d"),
        )
        for row in by_spec.iter_rows(named=True):
            sp = row["practice_specialty"]
            precision_by_specialty[sp] = float(row["n_leakage"]) / row["n"] if row["n"] else 0.0
            dollars_by_specialty[sp] = float(row["d"])
    if "practice_specialty" in scored.columns:
        by_all = scored.group_by("practice_specialty").agg(
            pl.col("dollars_at_risk").sum().alias("d"),
            pl.len().alias("n"),
        )
        for row in by_all.iter_rows(named=True):
            exposure_by_specialty[row["practice_specialty"]] = float(row["d"])
            candidates_by_specialty[row["practice_specialty"]] = int(row["n"])

    return EvalReport(
        n_exceptions=len(scored),
        n_all_claims=n_all,
        base_rate_candidates=float(y_true.mean()),
        base_rate_all_claims=base_all,
        dollars_at_risk_total=total_at_risk,
        auc=auc,
        calibration_slope=slope,
        calibration_intercept=intercept,
        calibration_slope_calibrated=slope_cal,
        by_risk_score=by_risk,
        by_expected_recovery=by_recovery,
        by_expected_recovery_calibrated=by_recovery_cal,
        rules_only_baseline_dollars=rules_only_dollars,
        rules_only_baseline_hours=rules_only_hours,
        uplift_dollars_vs_rules_at_100=uplift,
        citation_precision=cit_precision,
        abstention_rate=abst_rate,
        citation_precision_by_type=cit_by_type,
        precision_by_specialty=precision_by_specialty,
        dollars_captured_by_specialty=dollars_by_specialty,
        exposure_by_specialty=exposure_by_specialty,
        candidates_by_specialty=candidates_by_specialty,
    )


def report_dict(report: EvalReport) -> dict:
    return asdict(report)


def reviewer_cost_at_k(k: int) -> float:
    return REVIEWER_LOADED_HOURLY * ((k * REVIEWER_REVIEW_MINUTES) / 60.0)
