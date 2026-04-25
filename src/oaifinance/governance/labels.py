"""Retrospective label schemas + adapter for V2 production-data ingest.

V1 uses synthetic ground truth from the generator. V2 ingests real
appeal-outcome / re-adjudication / chargeback-resolution data from the
practice billing system under DUA. The schemas here define what V2
expects; the adapter shows how an Epic / Cerner / Meditech-shaped feed
maps onto our `_true_leakage` ground-truth column.

The pipeline only consumes the joined `claim_outcome_label` table. The
adapter encapsulates the source-system-specific mapping so the rest of
the pipeline doesn't change between V1 (synthetic) and V2 (production).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator


AppealDecision = Literal["upheld", "overturned", "partial", "withdrawn", "pending"]


class AppealOutcome(BaseModel):
    """Appeal outcome row from the practice billing system."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    claim_id: str
    appeal_filed_at: datetime
    appeal_decision: AppealDecision
    decided_at: datetime | None = None
    recovered_dollars: float = Field(ge=0)
    original_carc: str | None = None
    overturning_documentation: str | None = None

    @field_validator("recovered_dollars")
    @classmethod
    def _bounded(cls, v: float) -> float:
        if v > 10_000_000:
            raise ValueError("recovered_dollars exceeds plausible single-claim ceiling")
        return v


class ReAdjudication(BaseModel):
    """A claim re-adjudicated by the payer after corrected resubmission."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    original_paid: float = Field(ge=0)
    corrected_paid: float = Field(ge=0)
    recovered_dollars: float = Field(ge=0)
    re_adjudicated_at: datetime
    correction_reason: str


class ChargebackResolution(BaseModel):
    """Resolution of a chargeback/claim economics dispute with the payer or GPO."""

    model_config = ConfigDict(extra="forbid")

    chargeback_id: str
    claim_id: str | None = None
    resolution_status: Literal["accepted", "disputed", "withdrawn", "audit_pending"]
    recovered_dollars: float = Field(ge=0)
    resolved_at: datetime | None = None
    resolution_notes: str | None = None


@dataclass(frozen=True)
class ClaimOutcomeLabel:
    """Joined outcome label per claim.

    `is_recovered` ∈ {True, False, None} is the V2 replacement for V1's
    synthetic `_true_leakage`. None means the outcome window has not yet
    closed (claim is still in appeal / pending / unresolved); these rows
    are excluded from training but still scored at inference time.
    """

    claim_id: str
    is_recovered: bool | None
    recovered_dollars: float
    label_source: str  # "appeal" | "re_adjudication" | "chargeback" | "no_outcome"
    label_observed_at: datetime | None


def adapt_to_outcome_labels(
    appeals: Iterable[AppealOutcome] = (),
    re_adjudications: Iterable[ReAdjudication] = (),
    chargebacks: Iterable[ChargebackResolution] = (),
) -> pl.DataFrame:
    """Map V2 source-system feeds onto a single `claim_outcome_label` frame.

    Precedence rule: `re_adjudication` > `chargeback` > `appeal`.
    A claim with multiple outcomes (e.g. denied → appealed → re-adjudicated)
    takes the strongest evidence of recovery.
    """
    rows: dict[str, ClaimOutcomeLabel] = {}

    for ap in appeals:
        is_rec = (
            True
            if ap.appeal_decision in ("overturned", "partial")
            else False
            if ap.appeal_decision == "upheld"
            else None
        )
        rows[ap.claim_id] = ClaimOutcomeLabel(
            claim_id=ap.claim_id,
            is_recovered=is_rec,
            recovered_dollars=ap.recovered_dollars,
            label_source="appeal",
            label_observed_at=ap.decided_at,
        )

    for cb in chargebacks:
        if cb.claim_id is None:
            continue
        if cb.resolution_status in ("accepted", "withdrawn"):
            is_rec = cb.resolution_status == "accepted"
            rows[cb.claim_id] = ClaimOutcomeLabel(
                claim_id=cb.claim_id,
                is_recovered=is_rec,
                recovered_dollars=cb.recovered_dollars,
                label_source="chargeback",
                label_observed_at=cb.resolved_at,
            )

    for rj in re_adjudications:
        rows[rj.claim_id] = ClaimOutcomeLabel(
            claim_id=rj.claim_id,
            is_recovered=rj.recovered_dollars > 0,
            recovered_dollars=rj.recovered_dollars,
            label_source="re_adjudication",
            label_observed_at=rj.re_adjudicated_at,
        )

    return pl.DataFrame(
        [
            {
                "claim_id": r.claim_id,
                "is_recovered": r.is_recovered,
                "recovered_dollars": r.recovered_dollars,
                "label_source": r.label_source,
                "label_observed_at": r.label_observed_at,
            }
            for r in rows.values()
        ]
    )
