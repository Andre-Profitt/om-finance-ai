"""CMS NDC-HCPCS crosswalk ingestion."""

from __future__ import annotations

import polars as pl

from oaifinance.config import BRONZE_DIR, SAMPLES_DIR


def load_sample() -> pl.DataFrame:
    path = SAMPLES_DIR / "ndc_hcpcs_sample.csv"
    return pl.read_csv(path)


def ingest(live: bool = False) -> pl.DataFrame:
    if live:
        raise NotImplementedError(
            "Live NDC-HCPCS fetch not implemented in v0. Refresh from CMS quarterly."
        )

    df = load_sample()
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(BRONZE_DIR / "ndc_hcpcs_raw.parquet")
    return df


if __name__ == "__main__":
    df = ingest()
    print(f"ingested {len(df)} NDC-HCPCS rows")
    print(df)
