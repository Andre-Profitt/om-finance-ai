-- ALARM: scoring coverage below 99% (claims with a model risk score / total
-- claims processed). Indicates an ingest or feature pipeline incident.

WITH coverage AS (
    SELECT
        DATE_TRUNC('day', service_date) AS day,
        COUNT(*) AS n_claims,
        SUM(CASE WHEN risk_score IS NOT NULL THEN 1 ELSE 0 END) AS n_scored
    FROM rev_integrity.silver.claim_lines cl
    LEFT JOIN rev_integrity.gold.scored_exceptions s
        ON s.claim_id = cl.claim_id
    WHERE service_date >= CURRENT_DATE - INTERVAL 7 DAYS
    GROUP BY DATE_TRUNC('day', service_date)
)
SELECT
    day,
    n_claims,
    n_scored,
    n_scored * 1.0 / NULLIF(n_claims, 0) AS coverage,
    CASE
        WHEN n_scored * 1.0 / NULLIF(n_claims, 0) < 0.99 THEN 'COVERAGE_GAP'
        ELSE 'OK'
    END AS status
FROM coverage
ORDER BY day DESC;
