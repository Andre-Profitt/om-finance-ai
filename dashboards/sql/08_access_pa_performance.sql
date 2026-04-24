-- Access / Prior-Auth performance — per-payer view of PA gaps, access-delay
-- cost, and denial-on-PA volume. Drives the Access module's operational KPI
-- panel and ties PA hygiene to finance outcomes.

SELECT
    s.payer,
    COUNT(*)                                                       AS n_pa_gap_exceptions,
    SUM(s.dollars_at_risk)                                         AS pa_gap_dollars_at_risk,
    AVG(s.risk_score_calibrated)                                   AS mean_calibrated_score,
    SUM(s.dollars_at_risk * s.risk_score_calibrated)               AS expected_recovery,
    AVG(c.access_delay_cost)                                       AS mean_delay_cost_per_claim,
    SUM(c.access_delay_cost)                                       AS total_delay_cost
FROM rev_integrity.gold.scored_exceptions s
LEFT JOIN rev_integrity.bronze.claims_raw c
    ON c.claim_id = s.claim_id
WHERE s.exception_type = 'access_pa_gap'
GROUP BY s.payer
ORDER BY expected_recovery DESC;
