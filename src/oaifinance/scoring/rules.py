"""Rule-based exception candidates.

Deterministic triggers that seed the work queue before any ML scoring.
Contract-economics rules (gpo_340b_rebate_excluded, biosimilar_conversion_miss,
chargeback_validity_fail) take priority over the generic revenue-cycle rules
(ndc_hcpcs_mismatch, asp_drift, underpayment, denial) so each candidate has
a single, specific exception_type for evidence retrieval.
"""

from __future__ import annotations

import polars as pl

from oaifinance.config import GOLD_DIR, SILVER_DIR

ASP_DRIFT_THRESHOLD = 1.50
UNDERPAYMENT_THRESHOLD = 0.90
CHARGEBACK_ASP_THRESHOLD = 1.75


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
        pl.col("gpo_340b_double_dip").alias("rule_gpo_340b_excluded"),
        (pl.col("billed_to_asp_ratio") > CHARGEBACK_ASP_THRESHOLD).alias(
            "rule_chargeback_validity_fail"
        ),
    ).with_columns(
        # Biosimilar-conversion-miss is a *specialization* of other revenue-cycle
        # rules — only fires when the claim was already flagged for another
        # reason AND the claim involves a reference biologic on a commercial
        # payer (where the biosimilar is payer-preferred). This keeps the
        # candidate universe bounded.
        (
            pl.col("is_biosimilar_reference")
            & pl.col("payer").is_in(["commercial_national", "commercial_regional"])
            & (
                pl.col("rule_denied")
                | pl.col("rule_asp_drift")
                | pl.col("rule_underpayment")
                | pl.col("rule_ndc_mismatch")
            )
        ).alias("rule_biosimilar_conversion_miss"),
    )

    any_rule = (
        pl.col("rule_asp_drift")
        | pl.col("rule_ndc_mismatch")
        | pl.col("rule_denied")
        | pl.col("rule_underpayment")
        | pl.col("rule_gpo_340b_excluded")
        | pl.col("rule_biosimilar_conversion_miss")
        | pl.col("rule_chargeback_validity_fail")
    )

    # Priority: contract-economics rules first, then revenue-cycle rules.
    exc_type = (
        pl.when(pl.col("rule_gpo_340b_excluded"))
        .then(pl.lit("gpo_340b_rebate_excluded"))
        .when(pl.col("rule_chargeback_validity_fail"))
        .then(pl.lit("chargeback_validity_fail"))
        .when(pl.col("rule_biosimilar_conversion_miss") & pl.col("rule_denied"))
        .then(pl.lit("biosimilar_conversion_miss"))
        .when(pl.col("rule_biosimilar_conversion_miss") & pl.col("rule_underpayment"))
        .then(pl.lit("biosimilar_conversion_miss"))
        .when(pl.col("rule_biosimilar_conversion_miss") & pl.col("rule_asp_drift"))
        .then(pl.lit("biosimilar_conversion_miss"))
        .when(pl.col("rule_ndc_mismatch"))
        .then(pl.lit("ndc_hcpcs_mismatch"))
        .when(pl.col("rule_asp_drift"))
        .then(pl.lit("asp_drift"))
        .when(pl.col("rule_underpayment"))
        .then(pl.lit("underpayment"))
        .when(pl.col("rule_denied"))
        .then(pl.lit("denial"))
        .otherwise(pl.lit("other"))
        .alias("exception_type")
    )

    exceptions = flagged.filter(any_rule).with_columns(
        exc_type,
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
