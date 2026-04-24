"""Silver: drug_economics — ASP joined to NDC-HCPCS crosswalk."""

from __future__ import annotations

import polars as pl

from oaifinance.config import BRONZE_DIR, SILVER_DIR


def build(asp: pl.DataFrame | None = None, crosswalk: pl.DataFrame | None = None) -> pl.DataFrame:
    if asp is None:
        asp = pl.read_parquet(BRONZE_DIR / "asp_raw.parquet")
    if crosswalk is None:
        crosswalk = pl.read_parquet(BRONZE_DIR / "ndc_hcpcs_raw.parquet")

    joined = crosswalk.join(asp, on="hcpcs_code", how="inner")
    drug_econ = joined.with_columns(
        (pl.col("payment_limit_per_unit") / pl.col("dosage_per_unit_mg")).alias("asp_per_mg"),
    ).select(
        "hcpcs_code",
        "ndc_code",
        "short_description",
        "brand_name",
        "labeler_name",
        "dosage_per_unit_mg",
        "payment_limit_per_unit",
        "asp_per_mg",
        "package_size_mg",
        "billed_units_per_package",
        "effective_date",
        "biosimilar_reference",
    )

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    drug_econ.write_parquet(SILVER_DIR / "drug_economics.parquet")
    return drug_econ


if __name__ == "__main__":
    df = build()
    print(df)
