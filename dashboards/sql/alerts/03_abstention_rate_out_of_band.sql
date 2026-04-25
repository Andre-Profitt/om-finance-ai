-- ALARM: abstention rate above 40% or below 5% for two consecutive runs.
-- High abstention → corpus coverage gap; low → threshold too lenient (model
-- citing weak retrievals). Per docs/governance.md §6, both extremes open a
-- corpus / threshold review ticket.

WITH last_two AS (
    SELECT
        run_id,
        scored_at,
        abstention_rate,
        ROW_NUMBER() OVER (ORDER BY scored_at DESC) AS rn
    FROM rev_integrity.governance.eval_metrics
)
SELECT
    MAX(scored_at) AS latest_run,
    MIN(abstention_rate) AS min_rate,
    MAX(abstention_rate) AS max_rate,
    CASE
        WHEN MIN(abstention_rate) < 0.05 THEN 'TOO_LOW_threshold_too_lenient'
        WHEN MAX(abstention_rate) > 0.40 THEN 'TOO_HIGH_corpus_coverage_gap'
        ELSE 'OK'
    END AS status
FROM last_two
WHERE rn <= 2;
