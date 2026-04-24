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
    ), "expected-recovery ranking should capture at least as much $ as P(leakage) at top-100"

    assert report.dollars_at_risk_total > 0

    # Week 2 invariants: calibration + RAG shipped
    assert report.calibration_slope_calibrated is not None, "isotonic calibration missing"
    assert 0.85 <= report.calibration_slope_calibrated <= 1.15, (
        f"calibrated slope {report.calibration_slope_calibrated:.3f} outside (0.85, 1.15)"
    )

    assert report.citation_precision is not None, "RAG citation eval missing"
    assert report.citation_precision >= 0.85, (
        f"citation precision {report.citation_precision:.3f} below 0.85"
    )

    assert report.abstention_rate is not None
    assert 0.0 <= report.abstention_rate <= 1.0
