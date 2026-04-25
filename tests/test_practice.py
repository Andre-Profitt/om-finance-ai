"""Unit tests for the practice performance + acquisition module."""

from __future__ import annotations


from oaifinance.practice import performance


def test_analyze_returns_network_summary(pipeline_report):
    model = performance.analyze()
    summary = model.network_summary
    assert summary["n_practices"] >= 5, "expected at least 5 practices in synthetic network"
    assert summary["n_claims_total"] > 0
    assert summary["total_at_risk"] > 0
    assert summary["expected_recovery_calibrated"] > 0


def test_target_practice_has_exceptions(pipeline_report):
    """Target practice must have at least one scored exception.

    Production data (n_claims=5000) easily clears the 50-exception cold-start
    threshold; the test fixture runs n_claims=1000 to keep CI fast, so the
    fallback path is exercised here. Either branch should still produce a
    non-empty target.
    """
    model = performance.analyze()
    target = model.target_summary
    assert target["n_exceptions"] >= 1


def test_initiative_projections_non_negative(pipeline_report):
    model = performance.analyze()
    assert len(model.initiatives) == 5, "expected 5 sequenced 100-day initiatives"
    for ini in model.initiatives:
        assert ini["addressable_dollars"] >= 0
        assert ini["projected_recovery"] >= 0
        assert ini["reviewer_hours"] >= 0
        assert ini["reviewer_cost"] >= 0
        assert 0.0 <= ini["confidence"] <= 1.0


def test_total_q1_net_value_positive(pipeline_report):
    model = performance.analyze()
    assert model.total_projected_recovery_q1 > 0
    assert model.total_projected_net_value > 0, (
        "expected positive net value from 100-day initiatives"
    )


def test_explicit_target_override_works(pipeline_report):
    """Passing target_practice should override auto-selection."""
    import polars as pl

    from oaifinance.config import GOLD_DIR

    model_auto = performance.analyze()

    practices = pl.read_parquet(GOLD_DIR / "practice_performance.parquet")
    candidates = (
        practices.filter(pl.col("n_exceptions") >= 1)
        .sort("expected_recovery_calibrated", descending=True)["practice_id"]
        .to_list()
    )
    assert len(candidates) >= 2, "need ≥ 2 practices with at least one exception"
    other = candidates[1] if candidates[0] == model_auto.target_practice else candidates[0]

    model_override = performance.analyze(target_practice=other)
    assert model_override.target_practice == other


def test_payback_finite_when_net_positive(pipeline_report):
    model = performance.analyze()
    if model.total_projected_net_value > 0:
        assert model.payback_months_modeled > 0
        assert model.payback_months_modeled < 240, "modeled payback should clamp to under 20 years"
