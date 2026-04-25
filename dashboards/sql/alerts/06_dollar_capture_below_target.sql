-- ALARM: dollar capture @ top-100 below 70% of modeled target over a
-- 2-week window. Per docs/governance.md §6, this triggers a product
-- review — exception types may be miscalibrated to current payer mix.

WITH recent_runs AS (
    SELECT
        scored_at,
        dollars_captured_top_100_calibrated,
        modeled_target_dollars_top_100
    FROM rev_integrity.governance.eval_metrics
    WHERE scored_at >= CURRENT_TIMESTAMP - INTERVAL 14 DAYS
)
SELECT
    AVG(dollars_captured_top_100_calibrated) AS avg_captured_2wk,
    AVG(modeled_target_dollars_top_100) AS avg_target_2wk,
    AVG(dollars_captured_top_100_calibrated) / NULLIF(AVG(modeled_target_dollars_top_100), 0) AS attainment_ratio,
    CASE
        WHEN AVG(dollars_captured_top_100_calibrated) / NULLIF(AVG(modeled_target_dollars_top_100), 0) < 0.70 THEN 'BELOW_TARGET'
        ELSE 'OK'
    END AS status
FROM recent_runs;
