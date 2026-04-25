# Databricks notebook source
# MAGIC %md
# MAGIC # Control Tower — practice analysis driver
# MAGIC
# MAGIC Wraps `oaifinance.practice.performance.analyze` for execution under
# MAGIC the Databricks Asset Bundle daily-pipeline job.

# COMMAND ----------

# MAGIC %pip install -e .

# COMMAND ----------

from oaifinance.practice import performance

model = performance.analyze()
performance.print_summary(model)
