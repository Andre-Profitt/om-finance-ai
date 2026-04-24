-- Leakage Summary — top-of-dashboard KPIs
-- Runs against the gold.scored_exceptions Delta table (Unity Catalog path
-- `rev_integrity.gold.scored_exceptions`). Local demo: replace fully-qualified
-- name with `read_parquet('data/gold/scored_exceptions.parquet')`.

SELECT
    COUNT(*)                                                              AS n_exceptions,
    COUNT(DISTINCT practice_id)                                           AS n_practices,
    SUM(dollars_at_risk)                                                  AS total_dollars_at_risk,
    SUM(dollars_at_risk * risk_score_calibrated)                          AS expected_recovery_total,
    AVG(risk_score_calibrated)                                            AS mean_calibrated_score,
    SUM(CASE WHEN adjudication_status = 'denied' THEN 1 ELSE 0 END)       AS n_denied,
    SUM(CASE WHEN is_340b_practice THEN 1 ELSE 0 END)                     AS n_340b_practice_claims,
    SUM(CASE WHEN gpo_340b_double_dip THEN dollars_at_risk ELSE 0 END)    AS double_dip_exposure,
    SUM(CASE WHEN is_biosimilar_reference THEN dollars_at_risk ELSE 0 END) AS biosim_reference_exposure
FROM rev_integrity.gold.scored_exceptions;
