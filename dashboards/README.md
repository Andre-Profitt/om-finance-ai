# Dashboards

Databricks SQL queries that power the Revenue Integrity Control Tower dashboard. Each `.sql` file in `sql/` is a single query ready to drop into a Databricks SQL Warehouse panel (or any Spark/DuckDB engine pointed at the Delta tables).

## Queries

| File                                    | Panel                 | What it answers                                                                                                               |
| --------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `sql/01_leakage_summary.sql`            | Top-of-dashboard KPIs | Total dollars at risk, expected recovery, 340B + biosimilar exposure                                                          |
| `sql/02_reviewer_queue_top100.sql`      | Reviewer queue        | The top-100 work queue with citation path, abstention flag, explanation text                                                  |
| `sql/03_exposure_by_exception_type.sql` | Exception mix         | Breakdown by exception type, with contract-economics types broken out                                                         |
| `sql/04_practice_leakage_heatmap.sql`   | Network CFO view      | Per-practice exposure + contract-economics share; feeds acquisition/performance model                                         |
| `sql/05_calibration_health.sql`         | Model ops             | Observed vs. predicted rate by score decile; triggers model-refresh SLA on drift                                              |
| `sql/06_override_distribution.sql`      | Reviewer behavior     | Override rate, rationale distribution, abstention-routed vs. explained outcomes                                               |
| `sql/07_specialty_mix.sql`              | Multispecialty mix    | Exposure by practice specialty (oncology, retinal, rheum, GI, neuro); contract + PA slices                                    |
| `sql/08_access_pa_performance.sql`      | Access / PA ops       | Per-payer PA-gap volume, access delay cost, expected recovery on access exceptions                                            |
| `sql/09_working_capital_exposure.sql`   | Working-capital + DSO | Inventory days, buy-and-bill cash lag, rebate variance, PA/denial DSO impact (V2 — needs realized_outcomes + GPO portal feed) |

## Local / demo execution

The queries reference fully-qualified Unity Catalog paths (`rev_integrity.gold.*`) for production. For a local demo, point any SQL engine at the Parquet outputs:

```python
import duckdb, polars as pl
con = duckdb.connect()
con.execute("CREATE VIEW scored_exceptions AS SELECT * FROM read_parquet('data/gold/scored_exceptions.parquet')")
con.execute("CREATE VIEW explained_exceptions AS SELECT * FROM read_parquet('data/gold/explained_exceptions.parquet')")
con.execute("CREATE VIEW override_log AS SELECT * FROM read_parquet('data/gold/override_log.parquet')")
# Replace the three-part names in .sql files with the unqualified view names above.
```

## Production deployment

In Databricks on Azure:

1. Land `scored_exceptions`, `explained_exceptions`, `override_log` as Delta tables under `rev_integrity.gold.*` via the Databricks Asset Bundle
2. Register a SQL Warehouse query for each `.sql` file
3. Attach queries to a dashboard layout with drill-through from `01_leakage_summary` → `02_reviewer_queue_top100`
4. Alert on `05_calibration_health` when the observed-vs-predicted gap exceeds 15% in any decile for two consecutive runs
