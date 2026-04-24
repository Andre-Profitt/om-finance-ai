# GPO Chargeback Validation Protocol

Protocol: CB-VAL-2026 · Effective 2026-01-01

## §1 Scope

Defines validation logic applied to chargeback submissions from covered-entity dispensers seeking the contracted acquisition price on eligible products. Applies to all products under the Master Agreement Exhibit A.

## §2 Submission Requirements

Each chargeback line item must include: NDC, HCPCS J-code, date of service, units dispensed, payer of record, eligibility class (commercial / Medicare / Medicaid / 340B), and the contract reference ID. Missing fields result in a Tier 1 rejection returned to the dispenser within 72 hours.

## §3 Validation Logic

Validation executes the following checks in order:

1. NDC-HCPCS crosswalk match for the date-of-service quarter. Mismatches are rejected under Reason CB-C-01 (coding).
2. ASP variance: billed-per-unit within 1.5× published ASP. Claims above threshold are routed for manual review under Reason CB-V-02 (variance).
3. Payer eligibility class consistent with the contract-qualified dispenser status. Duplicate-discount risk (340B + Medicaid rebate) under Reason CB-E-03 (eligibility).
4. Biosimilar-conversion consistency with the Biosimilar Conversion addendum; reference-product chargebacks where biosimilar is payer-preferred are flagged under Reason CB-B-04 (biosimilar).

## §4 Dispute and Resolution

Dispensers may dispute a rejection within 30 days by submitting supporting documentation through the contract-manager portal. Disputes missing the contract reference ID or the original claim payer EOB cannot be processed.

## §5 Audit Rights

The GPO retains audit rights over a rolling 24-month period. Auditable records include NDC-HCPCS reconciliations, payer adjudication records, and 340B eligibility determinations.
