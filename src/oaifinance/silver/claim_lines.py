"""Silver: claim_lines — normalized claims with drug-economics features."""

from __future__ import annotations

import polars as pl

from oaifinance.config import BRONZE_DIR, SILVER_DIR


def build(
    claims: pl.DataFrame | None = None, drug_econ: pl.DataFrame | None = None
) -> pl.DataFrame:
    if claims is None:
        claims = pl.read_parquet(BRONZE_DIR / "claims_raw.parquet")
    if drug_econ is None:
        drug_econ = pl.read_parquet(SILVER_DIR / "drug_economics.parquet")

    valid_ndc = drug_econ.select("hcpcs_code", "ndc_code").with_columns(
        pl.lit(True).alias("_ndc_hcpcs_valid")
    )

    claim_lines = (
        claims.join(valid_ndc, on=["hcpcs_code", "ndc_code"], how="left")
        .with_columns(
            pl.col("_ndc_hcpcs_valid").fill_null(False),
        )
        .join(
            drug_econ.select("hcpcs_code", "asp_per_mg", "dosage_per_unit_mg").unique(
                subset=["hcpcs_code"]
            ),
            on="hcpcs_code",
            how="left",
        )
        .with_columns(
            (pl.col("billed_per_unit") / pl.col("asp_rate_at_service")).alias(
                "billed_to_asp_ratio"
            ),
            (pl.col("paid_total") / pl.col("allowed_total")).alias("paid_to_allowed_ratio"),
            (pl.col("adjudication_status") == "denied").alias("is_denied"),
        )
        .rename({"_ndc_hcpcs_valid": "ndc_hcpcs_valid"})
    )

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    claim_lines.write_parquet(SILVER_DIR / "claim_lines.parquet")
    return claim_lines


if __name__ == "__main__":
    df = build()
    print(df.head())
    print(f"rows={len(df)}")
    print(f"denied={df['is_denied'].sum()}")
    print(f"ndc_invalid={(~df['ndc_hcpcs_valid']).sum()}")
