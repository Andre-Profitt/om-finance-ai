-- Exposure breakdown by exception type.
-- Contract-economics types (gpo_340b_rebate_excluded, biosimilar_conversion_miss,
-- chargeback_validity_fail) are reported alongside revenue-cycle types so
-- finance can see the relative dollar magnitude.

SELECT
    exception_type,
    COUNT(*)                              AS n_exceptions,
    SUM(dollars_at_risk)                  AS dollars_at_risk_total,
    AVG(dollars_at_risk)                  AS dollars_at_risk_mean,
    AVG(risk_score_calibrated)            AS mean_calibrated_score,
    SUM(dollars_at_risk * risk_score_calibrated) AS expected_recovery
FROM rev_integrity.gold.scored_exceptions
GROUP BY exception_type
ORDER BY expected_recovery DESC;
