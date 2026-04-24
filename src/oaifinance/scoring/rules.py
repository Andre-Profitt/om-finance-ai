"""Rule-based exception candidates.

Deterministic triggers that seed the work queue before any ML scoring. Each
rule emits an exception_type and human-readable trigger_reason so the
evidence-grounded RAG layer has something concrete to cite.
"""

from __future__ import annotations

import polars as pl

from oaifinance.config import GOLD_DIR, SILVER_DIR

ASP_DRIFT_THRESHOLD = 1.50
UNDERPAYMENT_THRESHOLD = 0.90


def flag(claim_lines: pl.DataFrame | None = None) -> pl.DataFrame:
    if claim_lines is None:
        claim_lines = pl.read_parquet(SILVER_DIR / "claim_lines.parquet")

    flagged = claim_lines.with_columns(
        (pl.col("billed_to_asp_ratio") > ASP_DRIFT_THRESHOLD).alias("rule_asp_drift"),
        (~pl.col("ndc_hcpcs_valid")).alias("rule_ndc_mismatch"),
        pl.col("is_denied").alias("rule_denied"),
        (
            (pl.col("adjudication_status") == "paid")
            & (pl.col("paid_to_allowed_ratio") < UNDERPAYMENT_THRESHOLD)
        ).alias("rule_underpayment"),
    )

    exceptions = flagged.filter(
        pl.col("rule_asp_drift")
        | pl.col("rule_ndc_mismatch")
        | pl.col("rule_denied")
        | pl.col("rule_underpayment")
    ).with_columns(
        pl.when(pl.col("rule_ndc_mismatch"))
        .then(pl.lit("ndc_hcpcs_mismatch"))
        .when(pl.col("rule_asp_drift"))
        .then(pl.lit("asp_drift"))
        .when(pl.col("rule_underpayment"))
        .then(pl.lit("underpayment"))
        .when(pl.col("rule_denied"))
        .then(pl.lit("denial"))
        .otherwise(pl.lit("other"))
        .alias("exception_type"),
        pl.max_horizontal(
            pl.col("allowed_total") - pl.col("paid_total"),
            pl.lit(0.0),
        ).alias("dollars_at_risk"),
    )

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    exceptions.write_parquet(GOLD_DIR / "exception_candidates.parquet")
    return exceptions


if __name__ == "__main__":
    df = flag()
    print(f"flagged {len(df)} candidates")
    print(df.group_by("exception_type").len().sort("len", descending=True))
