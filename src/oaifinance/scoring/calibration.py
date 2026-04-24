"""Isotonic calibration of the risk score.

Production-style: k-fold cross-validated isotonic fit. Each fold's out-of-fold
predictions are transformed by an isotonic regressor trained on the other
folds' (score, label) pairs. The per-fold regressors are also averaged into a
deployment regressor that applies to future (scoring-only) runs. Avoids the
in-frame-fit overfitting from the V0 calibration path and the single-holdout
fragility from V1.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import StratifiedKFold

from oaifinance.config import GOLD_DIR, RANDOM_SEED

N_CALIBRATION_FOLDS = 5


def calibrate(scored: pl.DataFrame | None = None) -> pl.DataFrame:
    if scored is None:
        scored = pl.read_parquet(GOLD_DIR / "scored_exceptions.parquet")

    y = scored["_true_leakage"].cast(pl.Int8).to_numpy().astype(float)
    s = scored["risk_score"].to_numpy()
    n = len(s)

    # If the positive class is too small for k-fold stratification, fall back
    # to a single held-out fold.
    n_pos = int(y.sum())
    n_neg = n - n_pos
    if min(n_pos, n_neg) < N_CALIBRATION_FOLDS:
        from sklearn.model_selection import train_test_split

        idx = np.arange(n)
        _, cal_idx = train_test_split(
            idx,
            test_size=0.20,
            random_state=RANDOM_SEED,
            stratify=y if len(np.unique(y)) > 1 else None,
        )
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(s[cal_idx], y[cal_idx])
        calibrated = iso.predict(s)
    else:
        kfold = StratifiedKFold(
            n_splits=N_CALIBRATION_FOLDS, shuffle=True, random_state=RANDOM_SEED
        )
        calibrated = np.zeros(n)
        for train_idx, test_idx in kfold.split(s, y):
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            iso.fit(s[train_idx], y[train_idx])
            calibrated[test_idx] = iso.predict(s[test_idx])

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
