"""CMS ASP Part B pricing file ingestion.

Falls back to bundled sample when live fetch unavailable. Production deployment
pulls the current-quarter file from the CMS ASP pricing page.
"""

from __future__ import annotations


import polars as pl

from oaifinance.config import BRONZE_DIR, SAMPLES_DIR


def load_sample() -> pl.DataFrame:
    path = SAMPLES_DIR / "cms_asp_sample.csv"
    return pl.read_csv(path, try_parse_dates=True)


def ingest(live: bool = False) -> pl.DataFrame:
    """Ingest the CMS ASP file to bronze.

    Args:
        live: If True, attempt live fetch from CMS. Not implemented in v0;
            raises NotImplementedError to avoid silent degradation. Use sample
            for reproducible demos.
    """
    if live:
        raise NotImplementedError(
            "Live CMS ASP fetch not implemented in v0. "
            "The ASP pricing page serves ZIP-wrapped Excel files whose exact URL "
            "rotates each quarter. Add a scraper in v1 that resolves the current "
            "ZIP link from the CMS landing page. For now, refresh the sample "
            "CSV manually from the latest CMS quarterly file."
        )

    df = load_sample()

    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(BRONZE_DIR / "asp_raw.parquet")
    return df


if __name__ == "__main__":
    df = ingest()
    print(f"ingested {len(df)} ASP rows")
    print(df)
