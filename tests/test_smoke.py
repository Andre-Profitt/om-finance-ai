"""End-to-end smoke test — pipeline runs and produces sensible outputs."""

from __future__ import annotations

import polars as pl

from oaifinance.config import GOLD_DIR


def test_pipeline_runs(pipeline_report):
    report = pipeline_report

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


def test_calibration_invariants(pipeline_report):
    report = pipeline_report
    assert report.calibration_slope_calibrated is not None, "isotonic calibration missing"
    assert 0.80 <= report.calibration_slope_calibrated <= 1.20, (
        f"calibrated slope {report.calibration_slope_calibrated:.3f} outside [0.80, 1.20]"
    )


def test_rag_invariants(pipeline_report):
    report = pipeline_report
    assert report.citation_precision is not None, "RAG citation eval missing"
    assert report.citation_precision >= 0.85, (
        f"citation precision {report.citation_precision:.3f} below 0.85"
    )
    assert report.abstention_rate is not None
    assert 0.0 <= report.abstention_rate <= 1.0


def test_contract_economics_present(pipeline_report):
    """Week 3 invariant — contract-economics exception types must appear."""
    exceptions = pl.read_parquet(GOLD_DIR / "exception_candidates.parquet")
    types = set(exceptions["exception_type"].unique().to_list())
    contract_types = {
        "gpo_340b_rebate_excluded",
        "biosimilar_conversion_miss",
        "chargeback_validity_fail",
    }
    assert contract_types.issubset(types), (
        f"missing contract-economics exception types: {contract_types - types}"
    )


def test_access_and_multispecialty_present(pipeline_report):
    """Week 4 invariant — access PA module + multispecialty coverage."""
    exceptions = pl.read_parquet(GOLD_DIR / "exception_candidates.parquet")
    types = set(exceptions["exception_type"].unique().to_list())
    assert "access_pa_gap" in types, "missing access_pa_gap exception type"
    specialties = set(exceptions["practice_specialty"].unique().to_list())
    assert "oncology" in specialties, "oncology specialty missing"
    assert len(specialties) >= 2, f"expected multispecialty coverage, saw only: {specialties}"


def test_equal_effort_specialty_slice(pipeline_report):
    """Week 5 polish — equal-effort slicing produces a value per present specialty."""
    report = pipeline_report
    assert report.items_per_specialty_equal_effort > 0
    assert len(report.precision_by_specialty_equal_effort) >= 2, (
        "equal-effort slice should produce ≥ 2 specialties"
    )
    for sp, p in report.precision_by_specialty_equal_effort.items():
        assert 0.0 <= p <= 1.0, f"precision out of range for {sp}: {p}"


def test_jw_drug_waste_present(pipeline_report):
    """C3 invariant — JW drug-waste exception type fires + carries dollars at risk."""
    exceptions = pl.read_parquet(GOLD_DIR / "exception_candidates.parquet")
    types = set(exceptions["exception_type"].unique().to_list())
    assert "jw_drug_waste" in types, "missing jw_drug_waste exception type"
    jw_rows = exceptions.filter(pl.col("exception_type") == "jw_drug_waste")
    assert len(jw_rows) > 0, "no JW gap candidates flagged"
    assert jw_rows["dollars_at_risk"].sum() > 0
