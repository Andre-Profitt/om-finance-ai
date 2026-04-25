-- Unity Catalog row-level security for practice-scoped reviewer access.
-- Per docs/governance.md §4, claim_lines and gold tables are filtered on
-- practice_id so a practice-A reviewer principal cannot read practice-B
-- rows. Pattern uses Unity Catalog row filters and column masks.

-- 1. Service principal mapped to practice_id via a mapping table.
CREATE TABLE IF NOT EXISTS rev_integrity.governance.practice_principal_map (
    principal_email STRING NOT NULL,
    practice_id     STRING NOT NULL,
    granted_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    granted_by      STRING NOT NULL,
    revoked_at      TIMESTAMP
);

-- 2. Row filter function: returns TRUE when the current user has a row in
--    the mapping table for the row's practice_id, or is a member of the
--    network-CFO group (network-wide read).
CREATE OR REPLACE FUNCTION rev_integrity.governance.practice_row_filter(practice_id STRING)
RETURNS BOOLEAN
RETURN
    is_account_group_member('network_cfo')
    OR EXISTS (
        SELECT 1 FROM rev_integrity.governance.practice_principal_map
        WHERE principal_email = current_user()
          AND practice_id = practice_id
          AND revoked_at IS NULL
    );

-- 3. Apply the filter to silver + gold tables.
ALTER TABLE rev_integrity.silver.claim_lines
    SET ROW FILTER rev_integrity.governance.practice_row_filter ON (practice_id);
ALTER TABLE rev_integrity.gold.scored_exceptions
    SET ROW FILTER rev_integrity.governance.practice_row_filter ON (practice_id);
ALTER TABLE rev_integrity.gold.explained_exceptions
    SET ROW FILTER rev_integrity.governance.practice_row_filter ON (practice_id);

-- 4. PHI-adjacent column mask example: reviewer-rationale free-text is
--    redacted unless the principal is in the privacy-cleared group.
CREATE OR REPLACE FUNCTION rev_integrity.governance.rationale_mask(rationale STRING)
RETURNS STRING
RETURN CASE
    WHEN is_account_group_member('privacy_cleared') THEN rationale
    ELSE '[REDACTED]'
END;

ALTER TABLE rev_integrity.gold.override_log
    ALTER COLUMN rationale_text
    SET MASK rev_integrity.governance.rationale_mask;
