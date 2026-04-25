-- ALARM: calibration slope outside [0.85, 1.15] on the most recent run.
-- Per docs/governance.md §6, two consecutive runs outside the band opens a
-- model-refresh ticket. This query returns the latest slope; pair with a
-- 2-of-2 alert rule in Databricks SQL Alerts.

SELECT
    run_id,
    scored_at,
    calibration_slope_calibrated,
    CASE
        WHEN calibration_slope_calibrated < 0.85 OR calibration_slope_calibrated > 1.15 THEN 'OUT_OF_BAND'
        ELSE 'OK'
    END AS status
FROM rev_integrity.governance.eval_metrics
WHERE scored_at = (SELECT MAX(scored_at) FROM rev_integrity.governance.eval_metrics);
