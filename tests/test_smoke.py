"""End-to-end smoke test — pipeline runs and produces sensible outputs."""

from __future__ import annotations

from oaifinance import pipeline


def test_pipeline_runs():
    report = pipeline.run(n_claims=1000)

    assert report.n_exceptions > 0, "no exception candidates flagged"
    assert 0.0 <= report.base_rate_candidates <= 1.0
    assert 0.0 <= report.by_risk_score.precision_at_20 <= 1.0
    assert 0.0 <= report.by_expected_recovery.precision_at_20 <= 1.0

    assert report.by_risk_score.precision_at_20 >= report.base_rate_candidates, (
        "model P(leakage) ranking should beat the candidate base rate at top-20"
    )

    assert report.by_expected_recovery.dollars_captured_at_100 > 0, (
        "expected-recovery ranking should capture non-zero leakage in the top-100"
    )

    assert (
        report.by_expected_recovery.dollars_captured_at_100
        >= report.by_risk_score.dollars_captured_at_100
    ), (
        "expected-recovery ranking should capture at least as much $ as P(leakage) ranking at top-100"
    )

    assert report.dollars_at_risk_total > 0, "ground-truth leakage should be non-zero"
