-- Specialty mix view — slice the network's exposure by practice specialty.
-- Shows the multispecialty story: oncology share vs. retinal vs. rheum vs. GI
-- vs. neuro. Feeds the Week-4 Practice Performance memo and the network CFO
-- benchmarking view.

SELECT
    practice_specialty,
    COUNT(DISTINCT practice_id)                                    AS n_practices,
    COUNT(*)                                                       AS n_exceptions,
    SUM(dollars_at_risk)                                           AS total_dollars_at_risk,
    AVG(dollars_at_risk)                                           AS mean_dollars_at_risk,
    AVG(risk_score_calibrated)                                     AS mean_calibrated_score,
    SUM(dollars_at_risk * risk_score_calibrated)                   AS expected_recovery,
    SUM(CASE WHEN exception_type IN (
        'gpo_340b_rebate_excluded',
        'biosimilar_conversion_miss',
        'chargeback_validity_fail'
    ) THEN dollars_at_risk ELSE 0 END)                             AS contract_economics_exposure,
    SUM(CASE WHEN exception_type = 'access_pa_gap'
        THEN dollars_at_risk ELSE 0 END)                           AS access_pa_exposure
FROM rev_integrity.gold.scored_exceptions
GROUP BY practice_specialty
ORDER BY expected_recovery DESC;
