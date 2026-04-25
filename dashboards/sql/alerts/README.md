# Alert queries — drift / quality / coverage

Six SQL alarms wired to thresholds in [docs/governance.md §6](../../../docs/governance.md). Each query returns rows with a `status` column — `OK` or a specific failure code. In Databricks SQL Alerts, configure each as a 1-row alert that fires when `status != 'OK'`.

| File                                   | Threshold                                          | Source                                          |
| -------------------------------------- | -------------------------------------------------- | ----------------------------------------------- |
| `01_calibration_slope_drift.sql`       | calibrated slope outside [0.85, 1.15]              | `governance.eval_metrics`                       |
| `02_citation_precision_regression.sql` | below 0.90 for two consecutive runs                | `governance.eval_metrics`                       |
| `03_abstention_rate_out_of_band.sql`   | < 5% (threshold too lenient) or > 40% (corpus gap) | `governance.eval_metrics`                       |
| `04_override_rate_spike.sql`           | reviewer-disagree rate > 25% sustained 30 days     | `gold.override_log`                             |
| `05_scoring_coverage_gap.sql`          | scored / total claims < 99% over 7 days            | `silver.claim_lines` + `gold.scored_exceptions` |
| `06_dollar_capture_below_target.sql`   | $-captured / modeled target < 70% over 14 days     | `governance.eval_metrics`                       |

## Required upstream

`governance.eval_metrics` is a per-run row of headline eval numbers (run_id, scored_at, calibration_slope_calibrated, citation_precision, abstention_rate, dollars_captured_top_100_calibrated, modeled_target_dollars_top_100). It is **not** in the V1 pipeline — V2's scheduled calibration / eval refresh job (refinement plan B4) writes to it. The alert queries assume that target schema; until B4 ships, these queries are templates.

## Action runbook (governance.md §6)

| Alarm                         | First action                                           | Owner             |
| ----------------------------- | ------------------------------------------------------ | ----------------- |
| Calibration drift             | Open model-refresh ticket; schedule isotonic refit     | Staff ML Engineer |
| Citation precision regression | Per-type review; corpus / prompt diff                  | TPM + ML Eng      |
| Abstention out of band        | Corpus coverage audit (high) or threshold review (low) | TPM               |
| Override-rate spike           | Top-100 quality review; consider model retrain         | TPM + RCM ops     |
| Coverage gap                  | Ingest / feature pipeline incident                     | Staff Data Eng    |
| Dollar capture below target   | Product review on exception-type weights vs. payer mix | TPM               |
