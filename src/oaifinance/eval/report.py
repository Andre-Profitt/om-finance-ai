"""Eval report generator — Markdown summary + plots."""

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

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfect")

    for col, color, label in [
        ("risk_score", "#2a6f97", "uncalibrated"),
        ("risk_score_calibrated", "#e07a5f", "isotonic"),
    ]:
        if col not in scored.columns:
            continue
        y_score = scored[col].to_numpy()
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
        sizes = [max(20, n * 0.5) for n in ns]
        ax.scatter(xs, ys, s=sizes, alpha=0.7, label=label, color=color)

    ax.set_xlabel("predicted risk (mean of bucket)")
    ax.set_ylabel("empirical leakage rate")
    ax.set_title("Calibration — uncalibrated vs. isotonic")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _plot_capture_curves(scored: pl.DataFrame, out_path) -> None:
    total = float(scored["_true_leakage_amount"].sum())
    n = len(scored)

    fig, ax = plt.subplots(figsize=(8, 5))
    curves = [
        ("risk_score", "#2a6f97", "ranked by P(leakage)"),
        ("expected_recovery", "#e07a5f", "ranked by expected recovery ($)"),
    ]
    if "expected_recovery_calibrated" in scored.columns:
        curves.append(
            (
                "expected_recovery_calibrated",
                "#bc4749",
                "ranked by expected recovery (calibrated)",
            )
        )
    for rank_col, color, label in curves:
        sorted_df = scored.sort(rank_col, descending=True)
        cum_captured = np.cumsum(sorted_df["_true_leakage_amount"].to_numpy())
        ks = np.arange(1, len(sorted_df) + 1)
        ax.plot(ks, cum_captured / max(total, 1.0), color=color, label=label, lw=2)

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
    ax.set_title("Leakage capture vs. reviewer effort")
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
    by_cal = report.by_expected_recovery_calibrated

    lines = [
        "# Eval Report — Revenue Integrity Control Tower",
        "",
        "_Auto-generated. All claims synthetic; drug prices anchored to CMS ASP sample._",
        "",
        "## Coverage",
        "",
    ]
    if report.n_all_claims:
        lines.append(f"- Total claims scanned: **{report.n_all_claims:,}**")
    if report.base_rate_all_claims is not None:
        lines.append(f"- Universe leakage rate: **{report.base_rate_all_claims:.1%}**")
    lines += [
        f"- Exceptions flagged by rules: **{report.n_exceptions:,}**",
        f"- Base leakage rate within candidates: **{report.base_rate_candidates:.1%}**",
        f"- Total dollars-at-risk (ground truth): **${report.dollars_at_risk_total:,.0f}**",
        "",
        "## Reviewer queue — three rankings",
        "",
        "The same 100 reviewer-hours deployed against different ranking strategies "
        "yield materially different outcomes:",
        "",
        "| Metric | P(leakage) | expected recovery | expected recovery (calibrated) |",
        "|---|---|---|---|",
        f"| Precision@20 | {by_risk.precision_at_20:.1%} | {by_rec.precision_at_20:.1%} | "
        + (f"{by_cal.precision_at_20:.1%}" if by_cal else "—")
        + " |",
        f"| Precision@100 | {by_risk.precision_at_100:.1%} | {by_rec.precision_at_100:.1%} | "
        + (f"{by_cal.precision_at_100:.1%}" if by_cal else "—")
        + " |",
        f"| Dollars @ top-20 | ${by_risk.dollars_captured_at_20:,.0f} | ${by_rec.dollars_captured_at_20:,.0f} | "
        + (f"${by_cal.dollars_captured_at_20:,.0f}" if by_cal else "—")
        + " |",
        f"| Dollars @ top-100 | ${by_risk.dollars_captured_at_100:,.0f} | ${by_rec.dollars_captured_at_100:,.0f} | "
        + (f"${by_cal.dollars_captured_at_100:,.0f}" if by_cal else "—")
        + " |",
        f"| $/reviewer-hour @ 100 | ${by_risk.dollars_per_reviewer_hour_at_100:,.0f}/h | "
        f"${by_rec.dollars_per_reviewer_hour_at_100:,.0f}/h | "
        + (f"${by_cal.dollars_per_reviewer_hour_at_100:,.0f}/h" if by_cal else "—")
        + " |",
        "",
        "**Product read:** the recommended reviewer queue ranks on expected recovery "
        "calibrated; this trades a small amount of precision for materially more "
        "dollars captured per hour.",
        "",
        "## vs. rules-only baseline",
        "",
        f"- Rules-only (work all {report.n_exceptions} candidates uniformly): "
        f"**${report.rules_only_baseline_dollars:,.0f}** captured in "
        f"**{report.rules_only_baseline_hours:.1f} reviewer-hours**",
        f"- Model + expected recovery @ top-100: "
        f"**${by_rec.dollars_captured_at_100:,.0f}** captured in "
        f"**8.3 reviewer-hours** — "
        f"{by_rec.dollars_captured_at_100 / max(report.rules_only_baseline_dollars, 1):.0%} "
        f"of max at {100 / max(report.n_exceptions, 1):.0%} of effort",
        f"- Reviewer cost @ top-100 (loaded ≈ ${cost_100:.0f}): net value ≈ "
        f"**${by_rec.dollars_captured_at_100 - cost_100:,.0f}**",
        "",
    ]

    if report.citation_precision is not None:
        lines += [
            "## Evidence grounding (RAG)",
            "",
            f"- Citation precision overall: **{report.citation_precision:.1%}**",
            f"- Abstention rate: **{report.abstention_rate:.1%}**",
            "",
            "Citation precision by exception type:",
            "",
            "| Exception type | Citation precision |",
            "|---|---|",
        ]
        for et, p in sorted(report.citation_precision_by_type.items()):
            lines.append(f"| {et} | {p:.1%} |")
        lines.append("")
        lines += [
            "**Product read:** the system is required to cite a policy or contract "
            "clause for every explained exception, or abstain and route to human. "
            "Citation precision and abstention rate together define the "
            "controllership-readiness of the RAG layer.",
            "",
        ]

    lines += [
        "## Model diagnostics (internal)",
        "",
        f"- AUC on exception candidates: {report.auc:.3f}",
        f"- Calibration slope (uncalibrated): {report.calibration_slope:.3f} (target 0.9–1.1)",
    ]
    if report.calibration_slope_calibrated is not None:
        lines.append(f"- Calibration slope (isotonic): {report.calibration_slope_calibrated:.3f}")
    lines += [
        "",
        "## Limitations",
        "",
        "- Labels are synthetic ground truth; production deployment requires "
        "retrospective overpayment / denial / appeal-outcome labels.",
        "- Reviewer throughput (5 min/item) is a placeholder; real throughput varies "
        "by exception type and reviewer experience.",
        "- Citation precision evaluated against a hand-curated golden map; "
        "production would require a multi-rater rubric.",
        "- Isotonic calibration here is fit on the same frame for demo brevity; "
        "production must use a held-out calibration fold.",
        "- Override simulation uses a stylized reviewer model; real override rates "
        "and rationales can only be measured with reviewers in the loop.",
        "",
    ]
    return "\n".join(lines)


def generate(
    scored: pl.DataFrame | None = None,
    all_claims: pl.DataFrame | None = None,
    explained: pl.DataFrame | None = None,
) -> EvalReport:
    if scored is None:
        scored = pl.read_parquet(GOLD_DIR / "scored_exceptions.parquet")
    if all_claims is None:
        try:
            all_claims = pl.read_parquet(BRONZE_DIR / "claims_raw.parquet")
        except FileNotFoundError:
            all_claims = None
    if explained is None:
        path = GOLD_DIR / "explained_exceptions.parquet"
        if path.exists():
            explained = pl.read_parquet(path)

    report = evaluate(scored, all_claims=all_claims, explained=explained)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    (ARTIFACTS_DIR / "eval_report.json").write_text(
        json.dumps(report_dict(report), indent=2, default=str)
    )
    (ARTIFACTS_DIR / "eval_report.md").write_text(_markdown(report))
    _plot_calibration(scored, ARTIFACTS_DIR / "calibration.png")
    _plot_capture_curves(scored, ARTIFACTS_DIR / "capture_curves.png")

    return report


if __name__ == "__main__":
    r = generate()
    print(json.dumps(report_dict(r), indent=2, default=str))
