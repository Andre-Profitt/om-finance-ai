"""Rule-based exception candidates.

Priority order (first match wins):
  1. access_pa_gap              — prior-auth documentation missing (CoverMyMeds-shaped)
  2. jw_drug_waste              — JW modifier missing on single-dose container claim
  3. gpo_340b_rebate_excluded   — 340B + GPO rebate double-dip
  4. chargeback_validity_fail   — billed > 1.75x ASP
  5. biosimilar_conversion_miss — reference on commercial where biosim preferred
  6. ndc_hcpcs_mismatch         — crosswalk violation
  7. asp_drift                  — billed > 1.5x ASP (non-chargeback)
  8. underpayment               — paid < 0.9x allowed
  9. denial                     — generic denial (non-PA)
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
        (pl.col("denial_reason_pa") | (pl.col("pa_gap") & pl.col("is_denied"))).alias(
            "rule_access_pa_gap"
        ),
        pl.col("jw_gap").alias("rule_jw_drug_waste"),
        (pl.col("site_mismatch") & (pl.col("adjudication_status") == "paid")).alias(
            "rule_site_of_care_underpayment"
        ),
    ).with_columns(
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
        | pl.col("rule_access_pa_gap")
        | pl.col("rule_jw_drug_waste")
        | pl.col("rule_site_of_care_underpayment")
    )

    exc_type = (
        pl.when(pl.col("rule_access_pa_gap"))
        .then(pl.lit("access_pa_gap"))
        .when(pl.col("rule_jw_drug_waste"))
        .then(pl.lit("jw_drug_waste"))
        .when(pl.col("rule_gpo_340b_excluded"))
        .then(pl.lit("gpo_340b_rebate_excluded"))
        .when(pl.col("rule_chargeback_validity_fail"))
        .then(pl.lit("chargeback_validity_fail"))
        .when(pl.col("rule_biosimilar_conversion_miss"))
        .then(pl.lit("biosimilar_conversion_miss"))
        .when(pl.col("rule_site_of_care_underpayment"))
        .then(pl.lit("site_of_care_underpayment"))
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
    print(df.group_by(["exception_type", "practice_specialty"]).len().sort("len", descending=True))
