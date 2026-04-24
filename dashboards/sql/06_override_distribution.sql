-- Override distribution — reviewer behavior on the top-100 queue.
-- Feeds the KPI: reviewer agreement rate, rationale mix, abstention-routed vs
-- explained dispositions. Abstention-routed rejections should NOT equal model
-- mistakes — they are by-design human-first decisions.

SELECT
    decision,
    was_abstention,
    rationale_category,
    COUNT(*)                       AS n,
    AVG(CAST(agreed_with_model AS DOUBLE)) AS pct_agreed,
    SUM(dollars_at_risk)           AS dollars_reviewed,
    AVG(original_calibrated_score) AS mean_calibrated_score
FROM rev_integrity.gold.override_log
GROUP BY decision, was_abstention, rationale_category
ORDER BY n DESC;
