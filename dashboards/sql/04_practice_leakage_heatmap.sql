-- Practice leakage heatmap — per-practice exposure and concentration.
-- Feeds the network CFO benchmarking view and the Week-4 practice-acquisition
-- performance model.

WITH practice_totals AS (
    SELECT
        practice_id,
        MAX(is_340b_practice)                 AS is_340b_practice,
        COUNT(*)                              AS n_exceptions,
        SUM(dollars_at_risk)                  AS dollars_at_risk_total,
        SUM(dollars_at_risk * risk_score_calibrated) AS expected_recovery,
        SUM(CASE WHEN exception_type IN (
            'gpo_340b_rebate_excluded',
            'biosimilar_conversion_miss',
            'chargeback_validity_fail'
        ) THEN dollars_at_risk ELSE 0 END)    AS contract_economics_exposure
    FROM rev_integrity.gold.scored_exceptions
    GROUP BY practice_id
)
SELECT
    practice_id,
    is_340b_practice,
    n_exceptions,
    dollars_at_risk_total,
    expected_recovery,
    contract_economics_exposure,
    (contract_economics_exposure / NULLIF(dollars_at_risk_total, 0)) AS contract_share
FROM practice_totals
ORDER BY expected_recovery DESC;
