"""Eval report generator — Markdown summary + calibration and top-k plots."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from oaifinance.config import ARTIFACTS_DIR, BRONZE_DIR, GOLD_DIR  # noqa: E402
from oaifinance.eval.metrics import (  # noqa: E402
    EvalReport,
    evaluate,
    report_dict,
    reviewer_cost_at_k,
)


def _plot_calibration(scored: pl.DataFrame, out_path) -> None:
    y_true = scored["_true_leakage"].cast(pl.Int8).to_numpy().astype(float)
    y_score = scored["risk_score"].to_numpy()

    bins = 10
    bucket = np.clip((y_score * bins).astype(int), 0, bins - 1)
    xs, ys, ns = [], [], []
    for b in range(bins):
        mask = bucket == b
        if mask.sum() < 1:
            continue
        xs.append(float(y_score[mask].mean()))
        ys.append(float(y_true[mask].mean()))
        ns.append(int(mask.sum()))

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfect calibration")
    sizes = [max(20, n * 0.5) for n in ns]
    ax.scatter(xs, ys, s=sizes, alpha=0.7, label="observed")
    ax.set_xlabel("predicted risk (mean of bucket)")
    ax.set_ylabel("empirical leakage rate")
    ax.set_title("Calibration — Revenue Integrity Risk Scorer")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _plot_capture_curves(scored: pl.DataFrame, out_path) -> None:
    total = float(scored["_true_leakage_amount"].sum())

    fig, ax = plt.subplots(figsize=(8, 5))
    for rank_col, color, label in [
        ("risk_score", "#2a6f97", "ranked by P(leakage)"),
        ("expected_recovery", "#e07a5f", "ranked by expected recovery ($)"),
    ]:
        sorted_df = scored.sort(rank_col, descending=True)
        cum_captured = np.cumsum(sorted_df["_true_leakage_amount"].to_numpy())
        ks = np.arange(1, len(sorted_df) + 1)
        ax.plot(ks, cum_captured / max(total, 1.0), color=color, label=label, lw=2)

    n = len(scored)
    rules_only_line = np.linspace(0, 1, n + 1)[1:]
    ax.plot(
        np.arange(1, n + 1),
        rules_only_line,
        color="gray",
        linestyle=":",
        label="rules-only (uniform review)",
    )

    ax.set_xlabel("top-k reviewed")
    ax.set_ylabel("share of total leakage $ captured")
    ax.set_title("Leakage capture vs. reviewer effort — two ranking strategies")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    for k in (20, 100, 200):
        if k <= n:
            ax.axvline(k, linestyle=":", color="lightgray", alpha=0.7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _markdown(report: EvalReport) -> str:
    cost_100 = reviewer_cost_at_k(100)

    by_risk = report.by_risk_score
    by_rec = report.by_expected_recovery

    lines = [
        "# Eval Report — Revenue Integrity Control Tower",
        "",
        "_Auto-generated. All claims synthetic; drug prices anchored to CMS ASP sample._",
        "",
        "## Coverage",
        "",
        f"- Total claims scanned: **{report.n_all_claims:,}**"
        if report.n_all_claims
        else "- Total claims scanned: (all)",
        f"- Universe leakage rate: **{report.base_rate_all_claims:.1%}**"
        if report.base_rate_all_claims is not None
        else "",
        f"- Exceptions flagged by rules: **{report.n_exceptions:,}**",
        f"- Base leakage rate within candidates: **{report.base_rate_candidates:.1%}**",
        f"- Total dollars-at-risk (ground truth): **${report.dollars_at_risk_total:,.0f}**",
        "",
        "## Reviewer queue — two rankings",
        "",
        "The same 100 reviewer-hours deployed against two ranking strategies yield materially different outcomes:",
        "",
        "| Metric | ranked by P(leakage) | ranked by expected recovery ($) |",
        "|---|---|---|",
        f"| Precision@20 | {by_risk.precision_at_20:.1%} | {by_rec.precision_at_20:.1%} |",
        f"| Precision@50 | {by_risk.precision_at_50:.1%} | {by_rec.precision_at_50:.1%} |",
        f"| Precision@100 | {by_risk.precision_at_100:.1%} | {by_rec.precision_at_100:.1%} |",
        f"| Dollars captured @ top-20 | ${by_risk.dollars_captured_at_20:,.0f} | ${by_rec.dollars_captured_at_20:,.0f} |",
        f"| Dollars captured @ top-100 | ${by_risk.dollars_captured_at_100:,.0f} | ${by_rec.dollars_captured_at_100:,.0f} |",
        f"| Dollars / reviewer-hour @ 100 | ${by_risk.dollars_per_reviewer_hour_at_100:,.0f}/h | ${by_rec.dollars_per_reviewer_hour_at_100:,.0f}/h |",
        "",
        "**Product read:** ranking by expected recovery trades a small amount of precision for a material lift in dollars captured per reviewer hour. The recommended reviewer queue uses expected recovery.",
        "",
        "## vs. rules-only baseline",
        "",
        f"- Rules-only (work all {report.n_exceptions} candidates uniformly): **${report.rules_only_baseline_dollars:,.0f}** captured in **{report.rules_only_baseline_hours:.1f} reviewer-hours**",
        f"- Model + recovery ranking (work top 100): **${by_rec.dollars_captured_at_100:,.0f}** captured in **{(100 * 5) / 60:.1f} reviewer-hours** ({by_rec.dollars_captured_at_100 / max(report.rules_only_baseline_dollars, 1):.0%} of max at **{100 / max(report.n_exceptions, 1):.0%}** of effort)",
        f"- Reviewer cost @ top-100 (loaded ≈ ${reviewer_cost_at_k(100):.0f}): top-100 net value ≈ **${by_rec.dollars_captured_at_100 - cost_100:,.0f}**",
        "",
        "## Model diagnostics (internal)",
        "",
        f"- AUC on exception candidates: {report.auc:.3f}",
        f"- Calibration slope: {report.calibration_slope:.3f} (target 0.9–1.1)",
        f"- Calibration intercept: {report.calibration_intercept:.3f}",
        "",
        "## Limitations",
        "",
        "- Labels are synthetic ground truth from the generator. Production deployment requires retrospective overpayment/denial/appeal-outcome labels.",
        "- Reviewer throughput (5 min/item) is a placeholder; production throughput varies by exception type.",
        "- Eval does not yet measure citation precision (RAG layer is Week 2).",
        "- Override-rate distribution cannot be measured without reviewers in the loop.",
        "- Calibration is uncorrected; v2 adds isotonic or Platt scaling prior to the recovery ranking.",
        "",
    ]
    return "\n".join([ln for ln in lines if ln != ""])


def generate(
    scored: pl.DataFrame | None = None,
    all_claims: pl.DataFrame | None = None,
) -> EvalReport:
    if scored is None:
        scored = pl.read_parquet(GOLD_DIR / "scored_exceptions.parquet")
    if all_claims is None:
        try:
            all_claims = pl.read_parquet(BRONZE_DIR / "claims_raw.parquet")
        except FileNotFoundError:
            all_claims = None

    report = evaluate(scored, all_claims=all_claims)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    (ARTIFACTS_DIR / "eval_report.json").write_text(json.dumps(report_dict(report), indent=2))
    (ARTIFACTS_DIR / "eval_report.md").write_text(_markdown(report))
    _plot_calibration(scored, ARTIFACTS_DIR / "calibration.png")
    _plot_capture_curves(scored, ARTIFACTS_DIR / "capture_curves.png")

    return report


if __name__ == "__main__":
    r = generate()
    print(json.dumps(report_dict(r), indent=2, default=str))
