-- ALARM: citation precision below 0.90 for two consecutive runs.
-- Per docs/governance.md §6, this opens a prompt / retriever ticket and
-- triggers a per-exception-type review.

WITH last_two AS (
    SELECT
        run_id,
        scored_at,
        citation_precision,
        ROW_NUMBER() OVER (ORDER BY scored_at DESC) AS rn
    FROM rev_integrity.governance.eval_metrics
)
SELECT
    MAX(scored_at) AS latest_run,
    AVG(citation_precision) AS avg_precision_last_two,
    CASE
        WHEN MIN(citation_precision) < 0.90 THEN 'BELOW_THRESHOLD'
        ELSE 'OK'
    END AS status
FROM last_two
WHERE rn <= 2;
