"""End-to-end smoke test — ensures the pipeline runs and produces sensible outputs."""

from __future__ import annotations

from oaifinance import pipeline


def test_pipeline_runs():
    report = pipeline.run(n_claims=1000)
    assert report.n_exceptions > 0, "no exception candidates flagged"
    assert 0.0 <= report.base_rate <= 1.0
    assert 0.0 <= report.precision_at_20 <= 1.0
    assert report.precision_at_20 >= report.base_rate, (
        "model ranking should be at least as good as random at top-20"
    )
    assert report.dollars_at_risk_total > 0, "ground-truth leakage should be non-zero"
