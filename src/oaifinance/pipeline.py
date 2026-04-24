"""End-to-end pipeline orchestrator."""

from __future__ import annotations

import time

from rich.console import Console

from oaifinance.config import ensure_dirs
from oaifinance.eval.metrics import EvalReport
from oaifinance.eval.report import generate as generate_eval
from oaifinance.ingest import cms_asp, ndc_hcpcs, synthetic_claims
from oaifinance.scoring import model, rules
from oaifinance.silver import claim_lines, drug_economics

console = Console()


def run(n_claims: int | None = None, live: bool = False) -> EvalReport:
    ensure_dirs()
    t0 = time.time()

    console.rule("[bold cyan]1. Bronze — CMS ingest")
    asp = cms_asp.ingest(live=live)
    crosswalk = ndc_hcpcs.ingest(live=live)
    console.print(f"  asp rows: {len(asp)}  crosswalk rows: {len(crosswalk)}")

    console.rule("[bold cyan]2. Bronze — synthetic claims")
    claims = synthetic_claims.ingest(asp, crosswalk, n_claims=n_claims if n_claims else 5000)
    console.print(f"  claims generated: {len(claims)}")

    console.rule("[bold cyan]3. Silver — drug economics + claim lines")
    drug_econ = drug_economics.build(asp, crosswalk)
    cl = claim_lines.build(claims, drug_econ)
    console.print(f"  claim_lines rows: {len(cl)}")
    console.print(
        f"  denied: {cl['is_denied'].sum()}  ndc_invalid: {(~cl['ndc_hcpcs_valid']).sum()}"
    )

    console.rule("[bold cyan]4. Gold — exception candidates (rules)")
    exceptions = rules.flag(cl)
    console.print(f"  candidates flagged: {len(exceptions)}")
    by_type = exceptions.group_by("exception_type").len().sort("len", descending=True)
    for row in by_type.iter_rows(named=True):
        console.print(f"    {row['exception_type']}: {row['len']}")

    console.rule("[bold cyan]5. Gold — LightGBM risk scoring + MLflow")
    scored = model.train_and_score(exceptions)
    console.print(f"  scored rows: {len(scored)}")

    console.rule("[bold cyan]6. Eval — business-outcome report")
    report = generate_eval(scored, all_claims=claims)
    console.print(
        f"  ranked by P(leakage): precision@100={report.by_risk_score.precision_at_100:.1%}"
        f" / ${report.by_risk_score.dollars_captured_at_100:,.0f} captured"
    )
    console.print(
        f"  ranked by expected $: precision@100={report.by_expected_recovery.precision_at_100:.1%}"
        f" / ${report.by_expected_recovery.dollars_captured_at_100:,.0f} captured"
    )
    console.print(
        f"  rules-only baseline: ${report.rules_only_baseline_dollars:,.0f} in "
        f"{report.rules_only_baseline_hours:.1f}h; model @ 100 in 8.3h captures "
        f"{report.by_expected_recovery.dollars_captured_at_100 / max(report.rules_only_baseline_dollars, 1):.0%}"
    )
    console.print(f"  calibration slope: {report.calibration_slope:.3f} (target 0.9–1.1)")

    console.rule("[bold green]pipeline complete")
    console.print(f"  elapsed: {time.time() - t0:.1f}s")
    console.print("  artifacts: artifacts/eval_report.md, calibration.png, top_k_curve.png")
    console.print("  mlflow UI: `uv run mlflow ui --backend-store-uri file://$(pwd)/mlruns`")

    return report


if __name__ == "__main__":
    run()
