# Databricks notebook source
# MAGIC %md
# MAGIC # Calibration refresh (Track B4)
# MAGIC
# MAGIC Refit isotonic on a rolling 30-day held-out fold and stage the
# MAGIC candidate calibrator. Promotion is gated by a separate task that
# MAGIC compares the candidate's slope against production.

# COMMAND ----------

# MAGIC %pip install -e .

# COMMAND ----------

from oaifinance.scoring import calibration

# In production this notebook runs against the latest 30 days of held-out
# label rows from `governance.held_out_labels`. The local dev path falls
# back to the smoke pipeline output.
calibrated = calibration.calibrate()
print("candidate calibration written to data/gold/scored_exceptions.parquet")
