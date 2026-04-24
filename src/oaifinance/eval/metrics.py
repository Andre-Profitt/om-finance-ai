"""Business-outcome eval metrics.

Two rankings are compared so the TPM demo surfaces the core product tradeoff:
- `risk_score` queue: highest-probability leakage first (maximizes precision)
- `expected_recovery` queue: P(leakage) × dollars-at-risk (maximizes $ captured)

Also reports a "rules-only baseline" — what you'd get without the model, working
rule-flagged candidates uniformly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import polars as pl

from oaifinance.config import REVIEWER_LOADED_HOURLY, REVIEWER_REVIEW_MINUTES


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
    by_risk_score: RankedReport
    by_expected_recovery: RankedReport
    rules_only_baseline_dollars: float
    rules_only_baseline_hours: float
    uplift_dollars_vs_rules_at_100: float


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


def evaluate(scored: pl.DataFrame, all_claims: pl.DataFrame | None = None) -> EvalReport:
    y_true = scored["_true_leakage"].cast(pl.Int8).to_numpy()
    y_score = scored["risk_score"].to_numpy()

    auc = _auc(y_true, y_score)
    slope, intercept = _calibration(y_true.astype(float), y_score)

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

    return EvalReport(
        n_exceptions=len(scored),
        n_all_claims=n_all,
        base_rate_candidates=float(y_true.mean()),
        base_rate_all_claims=base_all,
        dollars_at_risk_total=total_at_risk,
        auc=auc,
        calibration_slope=slope,
        calibration_intercept=intercept,
        by_risk_score=by_risk,
        by_expected_recovery=by_recovery,
        rules_only_baseline_dollars=rules_only_dollars,
        rules_only_baseline_hours=rules_only_hours,
        uplift_dollars_vs_rules_at_100=uplift,
    )


def report_dict(report: EvalReport) -> dict:
    d = asdict(report)
    return d


def reviewer_cost_at_k(k: int) -> float:
    return REVIEWER_LOADED_HOURLY * ((k * REVIEWER_REVIEW_MINUTES) / 60.0)
