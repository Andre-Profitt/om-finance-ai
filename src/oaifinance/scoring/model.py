"""LightGBM risk scorer with MLflow tracking and native feature importance.

Feature attribution uses LightGBM's gain-based importance as the v1 explainer.
SHAP local explanations are a v2 addition; the current importance report is
sufficient for the top-k reviewer queue's 'why flagged' column.
"""

from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import mlflow
import numpy as np
import polars as pl
from sklearn.model_selection import train_test_split

from oaifinance.config import (
    ARTIFACTS_DIR,
    GOLD_DIR,
    MLFLOW_EXPERIMENT,
    MLRUNS_DIR,
    MODEL_NAME,
    RANDOM_SEED,
)
from oaifinance.scoring.features import FEATURE_COLS, LABEL_COL, build as build_features


def _setup_mlflow() -> None:
    MLRUNS_DIR.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"file://{MLRUNS_DIR.resolve()}")
    mlflow.set_experiment(MLFLOW_EXPERIMENT)


def train_and_score(exceptions: pl.DataFrame | None = None) -> pl.DataFrame:
    if exceptions is None:
        exceptions = pl.read_parquet(GOLD_DIR / "exception_candidates.parquet")

    featurized = build_features(exceptions)
    X = featurized.select(FEATURE_COLS).to_pandas()
    y = featurized[LABEL_COL].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=RANDOM_SEED,
        stratify=y if len(np.unique(y)) > 1 else None,
    )

    params = {
        "objective": "binary",
        "metric": "auc",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "min_data_in_leaf": 20,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 5,
        "verbose": -1,
        "seed": RANDOM_SEED,
    }

    train_ds = lgb.Dataset(X_train, label=y_train)
    valid_ds = lgb.Dataset(X_test, label=y_test, reference=train_ds)

    _setup_mlflow()

    with mlflow.start_run(run_name="lgb_risk_scorer_v1") as run:
        mlflow.log_params(params)
        mlflow.log_param("n_train", len(X_train))
        mlflow.log_param("n_test", len(X_test))
        mlflow.log_param("n_features", len(FEATURE_COLS))

        model = lgb.train(
            params,
            train_ds,
            num_boost_round=300,
            valid_sets=[train_ds, valid_ds],
            valid_names=["train", "valid"],
            callbacks=[lgb.early_stopping(25), lgb.log_evaluation(0)],
        )

        try:
            train_score = model.best_score["train"]["auc"]
            valid_score = model.best_score["valid"]["auc"]
            mlflow.log_metric("train_auc", train_score)
            mlflow.log_metric("valid_auc", valid_score)
        except KeyError:
            pass

        all_scores = model.predict(X)

        gain_importance = model.feature_importance(importance_type="gain")
        split_importance = model.feature_importance(importance_type="split")
        importance = {
            "gain": {
                f: float(v)
                for f, v in sorted(
                    zip(FEATURE_COLS, gain_importance, strict=True),
                    key=lambda kv: kv[1],
                    reverse=True,
                )
            },
            "split": {f: int(v) for f, v in zip(FEATURE_COLS, split_importance, strict=True)},
            "top_5_by_gain": [
                f
                for f, _ in sorted(
                    zip(FEATURE_COLS, gain_importance, strict=True),
                    key=lambda kv: kv[1],
                    reverse=True,
                )[:5]
            ],
        }
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        importance_path = ARTIFACTS_DIR / "feature_importance.json"
        importance_path.write_text(json.dumps(importance, indent=2))
        mlflow.log_artifact(str(importance_path))

        model_path = ARTIFACTS_DIR / "lgb_risk_scorer.txt"
        model.save_model(str(model_path))
        mlflow.log_artifact(str(model_path))

        mlflow.log_metric("model_size_bytes", Path(model_path).stat().st_size)

        run_id = run.info.run_id

    scored = exceptions.with_columns(
        pl.Series(name="risk_score", values=all_scores),
        pl.lit(run_id).alias("model_run_id"),
        pl.lit(MODEL_NAME).alias("model_name"),
    ).with_columns(
        (pl.col("risk_score") * pl.col("dollars_at_risk")).alias("expected_recovery"),
    )

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    scored.write_parquet(GOLD_DIR / "scored_exceptions.parquet")

    return scored


if __name__ == "__main__":
    df = train_and_score()
    print(
        df.select("claim_id", "exception_type", "dollars_at_risk", "risk_score")
        .sort("risk_score", descending=True)
        .head(10)
    )
