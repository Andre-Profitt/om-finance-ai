-- Reviewer queue — top 100 items, ranked by calibrated expected recovery.
-- Each row carries the citation path the RAG explainer produced, so the
-- reviewer UI can render "why flagged" without another call.

SELECT
    s.claim_id,
    s.practice_id,
    s.payer,
    s.hcpcs_code,
    s.exception_type,
    s.dollars_at_risk,
    s.risk_score_calibrated,
    (s.risk_score_calibrated * s.dollars_at_risk) AS expected_recovery,
    e.citation_doc_id,
    e.citation_section,
    e.citation_score,
    e.abstained,
    e.explanation_text
FROM rev_integrity.gold.scored_exceptions s
LEFT JOIN rev_integrity.gold.explained_exceptions e
    ON e.claim_id = s.claim_id
ORDER BY expected_recovery DESC
LIMIT 100;
