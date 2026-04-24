"""Append-only override log.

Captures reviewer decisions on flagged exceptions for controllership /
auditability. The log is append-only at the storage layer (Parquet partitioned
by decided_at month in production; single Parquet file for the demo) and
never overwrites historical decisions.

Simulates a realistic distribution of reviewer behavior on the explained
queue so the eval harness can report override-rate distribution without a
live reviewer UI.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import polars as pl

from oaifinance.config import GOLD_DIR, RANDOM_SEED

RATIONALE_CATEGORIES = [
    "agree_submit",
    "agree_resubmit_corrected",
    "disagree_legitimate_claim",
    "disagree_documentation_on_file",
    "escalate_coding_team",
    "escalate_payer_contact",
    "defer_more_information",
]

# Behavior model: reviewer agrees with high-confidence, calibrated explanations
# with cited evidence; disagrees more often on abstained items.
AGREE_RATE_EXPLAINED = 0.78
AGREE_RATE_ABSTAINED = 0.52


def _rationale(rng: np.random.Generator, agree: bool, abstained: bool) -> str:
    if agree and not abstained:
        return str(rng.choice(["agree_submit", "agree_resubmit_corrected"]))
    if agree and abstained:
        return "defer_more_information"
    if not agree and abstained:
        return str(rng.choice(["disagree_legitimate_claim", "disagree_documentation_on_file"]))
    return str(
        rng.choice(
            [
                "disagree_legitimate_claim",
                "escalate_coding_team",
                "escalate_payer_contact",
            ]
        )
    )


def simulate(
    explained: pl.DataFrame | None = None,
    top_k: int = 100,
    reviewer_ids: tuple[str, ...] = ("rev-001", "rev-002"),
    seed: int = RANDOM_SEED,
) -> pl.DataFrame:
    if explained is None:
        explained = pl.read_parquet(GOLD_DIR / "explained_exceptions.parquet")

    rank_col = (
        "expected_recovery_calibrated"
        if "expected_recovery_calibrated" in explained.columns
        else "expected_recovery"
    )
    queue = explained.sort(rank_col, descending=True).head(top_k)

    rng = np.random.default_rng(seed)
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for i, row in enumerate(queue.iter_rows(named=True)):
        abstained = bool(row.get("abstained", False))
        agree_p = AGREE_RATE_ABSTAINED if abstained else AGREE_RATE_EXPLAINED
        agree = rng.random() < agree_p
        rationale = _rationale(rng, agree, abstained)
        if agree and not abstained:
            decision = "approve"
        elif agree and abstained:
            decision = "defer"
        elif (not agree) and abstained:
            decision = "reject"
        else:
            decision = "escalate"

        rows.append(
            {
                "override_id": f"OVR-{i:06d}",
                "exception_id": row["claim_id"],
                "reviewer_id": str(reviewer_ids[rng.integers(0, len(reviewer_ids))]),
                "original_risk_score": float(row["risk_score"]),
                "original_calibrated_score": float(
                    row.get("risk_score_calibrated", row["risk_score"])
                ),
                "dollars_at_risk": float(row["dollars_at_risk"]),
                "decision": decision,
                "agreed_with_model": bool(agree),
                "was_abstention": abstained,
                "rationale_category": rationale,
                "decided_at": now,
                "model_run_id": row.get("model_run_id"),
            }
        )

    log = pl.DataFrame(rows)
    path = GOLD_DIR / "override_log.parquet"
    if path.exists():
        existing = pl.read_parquet(path)
        log = pl.concat([existing, log], how="vertical_relaxed")
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    log.write_parquet(path)
    return log


if __name__ == "__main__":
    df = simulate()
    print(f"logged {len(df)} overrides")
    print(df.group_by("decision").len().sort("len", descending=True))
