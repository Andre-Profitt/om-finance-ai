"""Pre-bill prior-authorization propensity model (Track C4).

V1 `access_pa_gap` is post-bill — it fires after the payer denies with CO-197.
By that point the practice has already lost cycle time. This pre-bill model
scores claims at submission time using ONLY pre-bill signals (payer, drug,
specialty, billed amounts, 340B flags, whether the practice has a PA on
file) and predicts the probability the claim will be denied for PA reasons.

Surfaced as a separate registered MLflow model so the production reviewer
queue can route high-propensity pre-bill items to the access team BEFORE
submission.
"""

from __future__ import annotations

from dataclasses import dataclass

import lightgbm as lgb
import mlflow
import numpy as np
import polars as pl
from sklearn.model_selection import train_test_split

from oaifinance.config import (
    BRONZE_DIR,
    GOLD_DIR,
    MLFLOW_EXPERIMENT,
    MLRUNS_DIR,
    RANDOM_SEED,
)

PA_PROPENSITY_MODEL_NAME = "rev_integrity.pa_propensity"
PA_FEATURE_COLS = [
    "payer_medicare_ffs",
    "payer_commercial_national",
    "payer_commercial_regional",
    "payer_medicaid_managed",
    "is_biosimilar_reference",
    "is_340b_practice",
    "is_340b_purchased",
    "billed_total",
    "allowed_total",
    "asp_rate_at_service",
    "specialty_oncology",
    "specialty_retinal",
    "specialty_rheumatology",
    "specialty_gastroenterology",
    "specialty_neurology",
    "hcpcs_ordinal",
    # Pre-bill access signal: did the practice know PA was required and have
    # it on file? Available at submission time.
    "pa_required",
    "pa_on_file",
]
LABEL_COL = "label_pa_gap"


@dataclass
class PaPropensityReport:
    n_train: int
    n_valid: int
    valid_auc: float | None
    n_high_propensity: int  # > 0.5
    high_propensity_dollars: float


def _featurize(claims: pl.DataFrame) -> pl.DataFrame:
    hcpcs_codes = sorted(claims["hcpcs_code"].unique().to_list())
    hcpcs_map = {h: i for i, h in enumerate(hcpcs_codes)}
    return claims.with_columns(
        pl.col("hcpcs_code")
        .map_elements(hcpcs_map.get, return_dtype=pl.Int32)
        .alias("hcpcs_ordinal"),
        pl.col("payer").eq("medicare_ffs").cast(pl.Int8).alias("payer_medicare_ffs"),
        pl.col("payer").eq("commercial_national").cast(pl.Int8).alias("payer_commercial_national"),
        pl.col("payer").eq("commercial_regional").cast(pl.Int8).alias("payer_commercial_regional"),
        pl.col("payer").eq("medicaid_managed").cast(pl.Int8).alias("payer_medicaid_managed"),
        pl.col("practice_specialty").eq("oncology").cast(pl.Int8).alias("specialty_oncology"),
        pl.col("practice_specialty").eq("retinal").cast(pl.Int8).alias("specialty_retinal"),
        pl.col("practice_specialty")
        .eq("rheumatology")
        .cast(pl.Int8)
        .alias("specialty_rheumatology"),
        pl.col("practice_specialty")
        .eq("gastroenterology")
        .cast(pl.Int8)
        .alias("specialty_gastroenterology"),
        pl.col("practice_specialty").eq("neurology").cast(pl.Int8).alias("specialty_neurology"),
        pl.col("is_biosimilar_reference").cast(pl.Int8),
        pl.col("is_340b_practice").cast(pl.Int8),
        pl.col("is_340b_purchased").cast(pl.Int8),
        pl.col("pa_required").cast(pl.Int8),
        pl.col("pa_on_file").cast(pl.Int8),
        pl.col("pa_gap").cast(pl.Int8).alias(LABEL_COL),
    )


def train_and_score(
    claims: pl.DataFrame | None = None,
) -> tuple[pl.DataFrame, PaPropensityReport]:
    if claims is None:
        claims = pl.read_parquet(BRONZE_DIR / "claims_raw.parquet")

    # Train only on PA-required claims; non-PA claims have label=0 trivially.
    pa_pool = claims.filter(pl.col("pa_required"))
    if len(pa_pool) < 50:
        return claims.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("pa_gap_propensity")
        ), PaPropensityReport(0, 0, None, 0, 0.0)

    feat = _featurize(pa_pool)
    X = feat.select(PA_FEATURE_COLS).to_pandas()
    y = feat[LABEL_COL].to_numpy()

    if len(np.unique(y)) < 2:
        return claims.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("pa_gap_propensity")
        ), PaPropensityReport(len(X), 0, None, 0, 0.0)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_SEED, stratify=y
    )
    train_ds = lgb.Dataset(X_train, label=y_train)
    valid_ds = lgb.Dataset(X_val, label=y_val, reference=train_ds)
    params = {
        "objective": "binary",
        "metric": "auc",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_data_in_leaf": 20,
        "verbose": -1,
        "seed": RANDOM_SEED,
    }

    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"file://{MLRUNS_DIR.resolve()}")
    mlflow.set_experiment(MLFLOW_EXPERIMENT)

    valid_auc: float | None = None
    with mlflow.start_run(run_name="pa_propensity_v1"):
        mlflow.log_params(params)
        mlflow.log_param("n_train", len(X_train))
        mlflow.log_param("n_valid", len(X_val))

        model = lgb.train(
            params,
            train_ds,
            num_boost_round=200,
            valid_sets=[train_ds, valid_ds],
            valid_names=["train", "valid"],
            callbacks=[lgb.early_stopping(20), lgb.log_evaluation(0)],
        )
        try:
            valid_auc = float(model.best_score["valid"]["auc"])
            mlflow.log_metric("valid_auc", valid_auc)
        except KeyError:
            pass

        # Score every claim — non-PA-required rows get 0.0.
        all_feat = _featurize(claims)
        propensity = np.zeros(len(all_feat), dtype=float)
        pa_mask = all_feat["pa_required"].to_numpy().astype(bool)
        if pa_mask.any():
            X_all = all_feat.filter(pl.col("pa_required")).select(PA_FEATURE_COLS).to_pandas()
            propensity[pa_mask] = model.predict(X_all)

    out = claims.with_columns(pl.Series("pa_gap_propensity", propensity))
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    out.write_parquet(GOLD_DIR / "pa_propensity_scores.parquet")

    high = out.filter(pl.col("pa_gap_propensity") > 0.5)
    report = PaPropensityReport(
        n_train=int(len(X_train)),
        n_valid=int(len(X_val)),
        valid_auc=valid_auc,
        n_high_propensity=int(len(high)),
        high_propensity_dollars=float(high["allowed_total"].sum()),
    )
    return out, report


if __name__ == "__main__":
    df, rep = train_and_score()
    print(rep)
