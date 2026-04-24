"""Isotonic calibration of the risk score.

Production-style: fit isotonic on a held-out calibration fold (20%),
apply the fitted transform to all scored rows. Avoids the in-frame-fit
overfitting called out as a v1 limitation.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import train_test_split

from oaifinance.config import GOLD_DIR, RANDOM_SEED

CALIBRATION_HOLDOUT_FRAC = 0.20


def calibrate(scored: pl.DataFrame | None = None) -> pl.DataFrame:
    if scored is None:
        scored = pl.read_parquet(GOLD_DIR / "scored_exceptions.parquet")

    y = scored["_true_leakage"].cast(pl.Int8).to_numpy().astype(float)
    s = scored["risk_score"].to_numpy()

    # Split on a stable index so the same calibration fold is used each run
    idx = np.arange(len(s))
    stratify = y if len(np.unique(y)) > 1 else None
    _, cal_idx = train_test_split(
        idx,
        test_size=CALIBRATION_HOLDOUT_FRAC,
        random_state=RANDOM_SEED,
        stratify=stratify,
    )

    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(s[cal_idx], y[cal_idx])
    calibrated = iso.predict(s)

    out = scored.with_columns(
        pl.Series("risk_score_calibrated", calibrated),
    ).with_columns(
        (pl.col("risk_score_calibrated") * pl.col("dollars_at_risk")).alias(
            "expected_recovery_calibrated"
        )
    )

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    out.write_parquet(GOLD_DIR / "scored_exceptions.parquet")
    return out


if __name__ == "__main__":
    df = calibrate()
    print(df.select("risk_score", "risk_score_calibrated").describe())
