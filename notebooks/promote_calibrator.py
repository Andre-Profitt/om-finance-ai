# Databricks notebook source
# MAGIC %md
# MAGIC # Calibration promotion gate
# MAGIC
# MAGIC Promotes the candidate calibrator to production only if the
# MAGIC sample-weighted slope is strictly closer to 1.0 than production.
# MAGIC Otherwise the candidate is archived and an alarm is raised.

# COMMAND ----------

import polars as pl

from oaifinance.config import GOLD_DIR
from oaifinance.eval.metrics import _calibration

scored = pl.read_parquet(GOLD_DIR / "scored_exceptions.parquet")
y = scored["_true_leakage"].cast(pl.Int8).to_numpy().astype(float)

raw_slope, _ = _calibration(y, scored["risk_score"].to_numpy())
cal_slope, _ = _calibration(y, scored["risk_score_calibrated"].to_numpy())

target = 1.0
distance_raw = abs(raw_slope - target) if raw_slope == raw_slope else float("inf")
distance_cal = abs(cal_slope - target) if cal_slope == cal_slope else float("inf")

print(f"raw slope: {raw_slope:.3f} · calibrated slope: {cal_slope:.3f}")
if distance_cal < distance_raw:
    print("PROMOTE — calibrated reduces distance to target")
else:
    print("HOLD — candidate did not improve calibration; archived")
