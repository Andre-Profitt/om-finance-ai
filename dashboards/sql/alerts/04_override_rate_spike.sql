-- ALARM: reviewer disagree-with-model rate > 25% sustained over 30 days.
-- Indicates the top-of-queue is no longer trustworthy; could mean drift,
-- corpus staleness, or an upstream rule misfire. Per docs/governance.md §6.

SELECT
    DATE_TRUNC('day', CAST(decided_at AS TIMESTAMP)) AS day,
    COUNT(*) AS n_decisions,
    1.0 - AVG(CAST(agreed_with_model AS DOUBLE)) AS disagree_rate,
    SUM(CASE WHEN NOT agreed_with_model THEN dollars_at_risk ELSE 0 END) AS disagree_dollars,
    CASE
        WHEN 1.0 - AVG(CAST(agreed_with_model AS DOUBLE)) > 0.25 THEN 'ALARM'
        ELSE 'OK'
    END AS status
FROM rev_integrity.gold.override_log
WHERE CAST(decided_at AS TIMESTAMP) >= CURRENT_TIMESTAMP - INTERVAL 30 DAYS
GROUP BY DATE_TRUNC('day', CAST(decided_at AS TIMESTAMP))
ORDER BY day DESC;
