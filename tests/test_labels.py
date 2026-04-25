"""V2 retrospective-label adapter tests (Track B3)."""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from oaifinance.governance.labels import (
    AppealOutcome,
    ChargebackResolution,
    ReAdjudication,
    adapt_to_outcome_labels,
)


def test_appeal_overturned_marks_recovered():
    a = AppealOutcome(
        claim_id="C1",
        appeal_filed_at=datetime(2026, 4, 10),
        appeal_decision="overturned",
        decided_at=datetime(2026, 4, 25),
        recovered_dollars=4500.0,
        original_carc="CO-50",
    )
    out = adapt_to_outcome_labels(appeals=[a])
    row = out.row(0, named=True)
    assert row["claim_id"] == "C1"
    assert row["is_recovered"] is True
    assert row["recovered_dollars"] == 4500.0
    assert row["label_source"] == "appeal"


def test_appeal_upheld_marks_not_recovered():
    a = AppealOutcome(
        claim_id="C2",
        appeal_filed_at=datetime(2026, 4, 10),
        appeal_decision="upheld",
        decided_at=datetime(2026, 4, 25),
        recovered_dollars=0.0,
    )
    out = adapt_to_outcome_labels(appeals=[a])
    assert out.row(0, named=True)["is_recovered"] is False


def test_pending_appeal_emits_none_label():
    a = AppealOutcome(
        claim_id="C3",
        appeal_filed_at=datetime(2026, 4, 10),
        appeal_decision="pending",
        recovered_dollars=0.0,
    )
    out = adapt_to_outcome_labels(appeals=[a])
    assert out.row(0, named=True)["is_recovered"] is None


def test_re_adjudication_overrides_appeal():
    """Precedence rule: re-adjudication beats appeal beats chargeback."""
    a = AppealOutcome(
        claim_id="C4",
        appeal_filed_at=datetime(2026, 4, 10),
        appeal_decision="upheld",
        decided_at=datetime(2026, 4, 20),
        recovered_dollars=0.0,
    )
    rj = ReAdjudication(
        claim_id="C4",
        original_paid=1000.0,
        corrected_paid=2500.0,
        recovered_dollars=1500.0,
        re_adjudicated_at=datetime(2026, 4, 28),
        correction_reason="NDC-HCPCS coding correction",
    )
    out = adapt_to_outcome_labels(appeals=[a], re_adjudications=[rj])
    row = out.row(0, named=True)
    assert row["is_recovered"] is True
    assert row["recovered_dollars"] == 1500.0
    assert row["label_source"] == "re_adjudication"


def test_chargeback_accepted_marks_recovered():
    cb = ChargebackResolution(
        chargeback_id="CB-1",
        claim_id="C5",
        resolution_status="accepted",
        recovered_dollars=750.0,
        resolved_at=datetime(2026, 4, 27),
    )
    out = adapt_to_outcome_labels(chargebacks=[cb])
    assert out.row(0, named=True)["is_recovered"] is True
    assert out.row(0, named=True)["label_source"] == "chargeback"


def test_validation_rejects_negative_dollars():
    with pytest.raises(ValidationError):
        AppealOutcome(
            claim_id="X",
            appeal_filed_at=datetime(2026, 4, 10),
            appeal_decision="overturned",
            recovered_dollars=-100.0,
        )


def test_validation_rejects_implausible_amounts():
    with pytest.raises(ValidationError):
        AppealOutcome(
            claim_id="X",
            appeal_filed_at=datetime(2026, 4, 10),
            appeal_decision="overturned",
            recovered_dollars=99_999_999.0,
        )
