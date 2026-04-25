-- Working-capital exposure — specialty distribution + cash conversion view.
-- Connects the Control Tower to McKesson O&M's Q3 FY26 growth thesis (provider
-- solutions + specialty distribution + acquisitions, +37% revenue / +57%
-- segment operating profit). Surfaces inventory days, buy-and-bill cash lag,
-- chargeback settlement lag, drug margin at risk, GPO rebate accrual variance,
-- and DSO impact from PA / denial delays.

WITH per_drug AS (
    SELECT
        s.hcpcs_code,
        s.short_description,
        s.specialty,
        s.payment_limit_per_unit                                     AS asp_per_unit,
        s.dosage_per_unit_mg,
        s.biosimilar_reference,

        -- Inventory days (proxy: vial throughput per practice quarter)
        COUNT(DISTINCT cl.claim_id)                                   AS n_admins,
        SUM(cl.units * s.dosage_per_unit_mg)                          AS mg_administered,

        -- Buy-and-bill cash conversion lag (days from service to payer pay)
        AVG(DATE_DIFF('day', cl.service_date, e.payer_response_at))   AS buyandbill_cash_days,

        -- Drug margin at risk: ASP delta × volume on flagged exceptions
        SUM(CASE WHEN sx.dollars_at_risk IS NOT NULL THEN sx.dollars_at_risk ELSE 0 END) AS dollars_at_risk_total,

        -- High-cost-drug exposure flag
        s.payment_limit_per_unit / NULLIF(s.dosage_per_unit_mg, 0)    AS asp_per_mg
    FROM rev_integrity.silver.drug_economics s
    LEFT JOIN rev_integrity.silver.claim_lines cl
        ON cl.hcpcs_code = s.hcpcs_code
    LEFT JOIN rev_integrity.gold.scored_exceptions sx
        ON sx.claim_id = cl.claim_id
    LEFT JOIN rev_integrity.gold.realized_outcomes e   -- V2 — populated by docs/value-realization-runbook
        ON e.claim_id = cl.claim_id
    GROUP BY 1, 2, 3, 4, 5, 6, 12
),
per_payer_lag AS (
    SELECT
        cl.hcpcs_code,
        cl.payer,
        AVG(DATE_DIFF('day', cl.service_date, e.payer_response_at))   AS payer_response_days,
        AVG(CASE WHEN cl.adjudication_status = 'denied' THEN
            DATE_DIFF('day', cl.service_date, e.payer_response_at)
        END)                                                          AS denial_response_days,
        AVG(CASE WHEN cl.pa_required AND NOT cl.pa_on_file THEN
            DATE_DIFF('day', cl.service_date, e.payer_response_at)
        END)                                                          AS pa_gap_response_days
    FROM rev_integrity.silver.claim_lines cl
    LEFT JOIN rev_integrity.gold.realized_outcomes e
        ON e.claim_id = cl.claim_id
    GROUP BY 1, 2
),
gpo_rebate AS (
    SELECT
        gpo.hcpcs_code,
        gpo.quarter,
        gpo.expected_rebate_accrual,
        gpo.actual_rebate_settled,
        gpo.actual_rebate_settled - gpo.expected_rebate_accrual       AS rebate_variance,
        AVG(DATE_DIFF('day', gpo.quarter_end_date, gpo.settled_at))   AS settlement_lag_days
    FROM rev_integrity.gold.gpo_rebate_accrual gpo                    -- V2 — populated by GPO portal feed
    GROUP BY 1, 2, 3, 4, 5
)
SELECT
    pd.hcpcs_code,
    pd.short_description,
    pd.specialty,
    pd.asp_per_mg,

    -- Volume + margin
    pd.n_admins,
    pd.mg_administered,
    pd.dollars_at_risk_total,

    -- Cash conversion (lower = better for working capital)
    pd.buyandbill_cash_days,
    AVG(pl.payer_response_days)                                       AS avg_payer_response_days,
    AVG(pl.denial_response_days)                                      AS avg_denial_response_days,
    AVG(pl.pa_gap_response_days)                                      AS avg_pa_gap_response_days,

    -- Rebate accrual health
    AVG(gr.rebate_variance)                                           AS rebate_accrual_variance,
    AVG(gr.settlement_lag_days)                                       AS rebate_settlement_lag_days,

    -- DSO impact attributable to PA / denial delays
    AVG(pl.pa_gap_response_days - pl.payer_response_days)             AS pa_gap_dso_impact,
    AVG(pl.denial_response_days - pl.payer_response_days)             AS denial_dso_impact,

    -- High-cost flag (>$100/mg)
    CASE WHEN pd.asp_per_mg > 100 THEN 'HIGH_COST' ELSE 'STANDARD' END AS cost_band,

    -- Biosimilar conversion opportunity
    pd.biosimilar_reference                                           AS has_biosimilar
FROM per_drug pd
LEFT JOIN per_payer_lag pl USING (hcpcs_code)
LEFT JOIN gpo_rebate gr USING (hcpcs_code)
GROUP BY
    pd.hcpcs_code, pd.short_description, pd.specialty, pd.asp_per_mg,
    pd.n_admins, pd.mg_administered, pd.dollars_at_risk_total,
    pd.buyandbill_cash_days, pd.biosimilar_reference
ORDER BY pd.dollars_at_risk_total DESC, pd.asp_per_mg DESC;

-- Notes:
-- * realized_outcomes and gpo_rebate_accrual are V2 tables populated by the
--   billing-system + GPO-portal feeds (see docs/value-realization-runbook.md).
--   In V1 dev, those tables are empty and the cash-conversion / rebate-variance
--   columns return NULL. The query is the production-shape; the data flow
--   lights up at V2 pilot start.
-- * Deliberately leaves out cost-of-capital so finance can apply their own rate
--   when computing $ impact of DSO; this is just the days, not the dollars.
