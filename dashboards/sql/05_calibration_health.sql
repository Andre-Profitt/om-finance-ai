-- Calibration health — binned observed vs. predicted leakage rate.
-- Drift alarm: slope outside [0.85, 1.15] for two consecutive eval cycles
-- triggers a model-refresh SLA review.

SELECT
    width_bucket(risk_score_calibrated, 0, 1, 10) AS score_decile,
    COUNT(*)                                      AS n,
    AVG(risk_score_calibrated)                    AS mean_predicted,
    AVG(CAST(_true_leakage AS DOUBLE))            AS empirical_rate,
    SUM(dollars_at_risk)                          AS bucket_exposure
FROM rev_integrity.gold.scored_exceptions
GROUP BY score_decile
ORDER BY score_decile;
