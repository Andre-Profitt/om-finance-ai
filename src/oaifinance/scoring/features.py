"""Feature engineering for the LightGBM risk scorer."""

from __future__ import annotations

import polars as pl

from oaifinance.config import SPECIALTIES

FEATURE_COLS = [
    "units",
    "billed_per_unit",
    "billed_total",
    "allowed_total",
    "billed_to_asp_ratio",
    "asp_rate_at_service",
    "is_biosimilar_reference",
    "is_340b_practice",
    "is_340b_purchased",
    "gpo_rebate_claimed",
    "pa_required",
    "pa_on_file",
    "rule_asp_drift",
    "rule_ndc_mismatch",
    "rule_denied",
    "rule_underpayment",
    "rule_gpo_340b_excluded",
    "rule_biosimilar_conversion_miss",
    "rule_chargeback_validity_fail",
    "rule_access_pa_gap",
    "rule_jw_drug_waste",
    "rule_site_of_care_underpayment",
    "payer_medicare_ffs",
    "payer_commercial_national",
    "payer_commercial_regional",
    "payer_medicaid_managed",
    "specialty_oncology",
    "specialty_retinal",
    "specialty_rheumatology",
    "specialty_gastroenterology",
    "specialty_neurology",
    "hcpcs_ordinal",
]

LABEL_COL = "label_leakage"


def build(exceptions: pl.DataFrame) -> pl.DataFrame:
    hcpcs_codes = sorted(exceptions["hcpcs_code"].unique().to_list())
    hcpcs_map = {h: i for i, h in enumerate(hcpcs_codes)}

    specialty_cols = [
        pl.col("practice_specialty").eq(s).cast(pl.Int8).alias(f"specialty_{s}")
        for s in SPECIALTIES
    ]

    df = exceptions.with_columns(
        pl.col("hcpcs_code")
        .map_elements(hcpcs_map.get, return_dtype=pl.Int32)
        .alias("hcpcs_ordinal"),
        pl.col("payer").eq("medicare_ffs").cast(pl.Int8).alias("payer_medicare_ffs"),
        pl.col("payer").eq("commercial_national").cast(pl.Int8).alias("payer_commercial_national"),
        pl.col("payer").eq("commercial_regional").cast(pl.Int8).alias("payer_commercial_regional"),
        pl.col("payer").eq("medicaid_managed").cast(pl.Int8).alias("payer_medicaid_managed"),
        *specialty_cols,
        pl.col("rule_asp_drift").cast(pl.Int8),
        pl.col("rule_ndc_mismatch").cast(pl.Int8),
        pl.col("rule_denied").cast(pl.Int8),
        pl.col("rule_underpayment").cast(pl.Int8),
        pl.col("rule_gpo_340b_excluded").cast(pl.Int8),
        pl.col("rule_biosimilar_conversion_miss").cast(pl.Int8),
        pl.col("rule_chargeback_validity_fail").cast(pl.Int8),
        pl.col("rule_access_pa_gap").cast(pl.Int8),
        pl.col("rule_jw_drug_waste").cast(pl.Int8),
        pl.col("rule_site_of_care_underpayment").cast(pl.Int8),
        pl.col("is_biosimilar_reference").cast(pl.Int8),
        pl.col("is_340b_practice").cast(pl.Int8),
        pl.col("is_340b_purchased").cast(pl.Int8),
        pl.col("gpo_rebate_claimed").cast(pl.Int8),
        pl.col("pa_required").cast(pl.Int8),
        pl.col("pa_on_file").cast(pl.Int8),
        pl.col("_true_leakage").cast(pl.Int8).alias(LABEL_COL),
    )
    return df
