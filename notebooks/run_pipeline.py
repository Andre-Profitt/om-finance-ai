# Databricks notebook source
# MAGIC %md
# MAGIC # Control Tower — daily pipeline driver
# MAGIC
# MAGIC Wraps `oaifinance.pipeline.run` for execution under the Databricks
# MAGIC Asset Bundle daily-pipeline job. Local dev runs the CLI directly:
# MAGIC `make demo`.

# COMMAND ----------

# MAGIC %pip install -e .

# COMMAND ----------

from oaifinance import pipeline

report = pipeline.run()
print(
    f"pipeline complete · candidates={report.n_exceptions} · "
    f"calibrated_precision_at_100={report.by_expected_recovery_calibrated.precision_at_100 if report.by_expected_recovery_calibrated else None}"
)
