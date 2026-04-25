# Value Realization Runbook

**Owner:** TPM + Controllership (joint)
**Status:** V2 design — schema and process defined; ingest from billing system pending DUA. The V1 pipeline ships everything left of "claim_resubmitted_at"; everything right of it requires real practice integration.

This runbook closes the loop from "we flagged an exception" to "we recovered cash." V1 surfaces signals; V2 measures realized value. Without this, V1's ROI numbers are projections — defensible as scenario modeling, but not as forecasts.

---

## 1. The loop

```
flag → reviewer action → corrected claim / appeal / chargeback true-up
      → payer response → cash received OR denial upheld
      → accounting treatment → KPI update
```

Each transition is a logged event with a timestamp, an actor, and a reason code. The full chain is auditable per `docs/governance.md` §7.

## 2. Required event timestamps

The override log already captures `decided_at`. V2 extends it with the downstream events:

| Field                        | Type      | When written                                   | Source                   |
| ---------------------------- | --------- | ---------------------------------------------- | ------------------------ |
| `flagged_at`                 | timestamp | when the rule layer flags the exception        | pipeline (V1)            |
| `scored_at`                  | timestamp | when the model scores it                       | pipeline (V1)            |
| `reviewed_at`                | timestamp | when the reviewer takes a disposition action   | reviewer UI (V2)         |
| `action_taken`               | enum      | approve / resubmit / escalate / reject / defer | reviewer UI (V2)         |
| `claim_resubmitted_at`       | timestamp | when the corrected claim is sent to the payer  | billing system feed (V2) |
| `payer_response_at`          | timestamp | when the payer adjudicates the resubmission    | billing system feed (V2) |
| `cash_received`              | $         | actual cash received vs. original allowed      | billing system feed (V2) |
| `writeoff_avoided`           | $         | original denial recovered minus new write-off  | billing system feed (V2) |
| `chargeback_trueup_received` | $         | chargeback dollars settled                     | GPO portal feed (V2)     |
| `revenue_recognition_status` | enum      | recognized / pending / reversed / N/A          | finance close pipeline   |
| `controller_review_status`   | enum      | approved / pending / rejected / N/A            | controller workflow      |

## 3. Per-exception lifecycle

For each exception_type, the path is slightly different. Document the common cases so reviewers and finance ops know what's expected.

### `access_pa_gap`

flag → reviewer files PA → PA approved or denied → if approved, claim resubmitted → payer adjudicates → cash received as if no PA gap had occurred. Realized value = (originally-denied dollars) − (PA processing time-cost).

### `ndc_hcpcs_mismatch`

flag → reviewer corrects NDC → claim resubmitted → payer adjudicates → cash received. Realized value = (originally-denied dollars) − (correction time-cost).

### `chargeback_validity_fail`

flag → reviewer reconciles billed amount with acquisition cost → chargeback adjusted → GPO settles → cash received. Realized value = (delta between billed and acquisition cost) − (reconciliation time-cost). Some flags are NOT recoverable — they were correct submissions; the model should learn to deprioritize over time.

### `gpo_340b_rebate_excluded`

flag → compliance review → if confirmed double-dip, rebate accrual is reversed BEFORE the next quarterly settlement (no clawback). Realized value = clawback prevented. This one is risk reduction, not cash recovery.

### `biosimilar_conversion_miss`

flag → formulary team reviews → if not medical-exception, conversion plan opened with the prescriber → next admin uses biosimilar → incremental rebate accrued in next quarter. Realized value = (incremental rebate) on FUTURE volume; this lifecycle is months long, not days.

### `site_of_care_underpayment`

flag → contracts team reviews → reconsideration filed OR contract renegotiation queued → cash recovered or renegotiated rate captured for future. Realized value = case-by-case.

### `jw_drug_waste`

flag → biller appends JW or JZ modifier → claim resubmitted with documented discarded amount → payer reimburses waste line. Realized value = waste-line reimbursement, typically 5–15% of vial cost.

### `denial` (generic)

flag → appeals team reviews → file first-level appeal → payer adjudicates → cash recovered or denial sustained. Realized value = appeal recovery rate × original allowed.

### `asp_drift`, `underpayment` — handled like denial / chargeback respectively

## 4. Aggregate KPIs

These are the metrics finance leadership cares about. All are computed off the V2-extended override log.

| KPI                    | Formula                                                                               | Cadence   |
| ---------------------- | ------------------------------------------------------------------------------------- | --------- |
| Realized recovery rate | `sum(cash_received) / sum(dollars_at_risk)` over closed exceptions                    | weekly    |
| Cycle time             | `payer_response_at − flagged_at` median by exception_type                             | weekly    |
| Working-capital impact | `sum(cash_received) − sum(reviewer_loaded_cost) − sum(implementation_cost_amortized)` | monthly   |
| Forecast variance      | `realized_recovery / projected_recovery` from `practice.performance`                  | monthly   |
| Exception type ROI     | per-type realized recovery rate × annual exception volume × avg dollars-at-risk       | quarterly |

## 5. Accounting treatment

Where each recovery type lands in the practice's books. Confirm with the controller for the specific GAAP/IFRS posture.

| Source                                   | Likely treatment                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------- |
| Re-adjudicated cash from corrected claim | Increase in net patient revenue; reverse the prior contractual adjustment |
| Successful appeal                        | Same as above                                                             |
| Chargeback true-up                       | Reduction in COGS for the affected period                                 |
| Avoided 340B clawback                    | No journal entry; flagged as a control event in compliance log            |
| Biosimilar conversion incremental rebate | Reduction in COGS in the period the rebate is recognized                  |
| Avoided JW write-off                     | Increase in net patient revenue                                           |
| Site-of-care reconsideration             | Increase in net patient revenue                                           |

## 6. Reviewer disposition rules

Reviewers should NOT mark an exception "resolved" just because they took an action. The exception stays open until the **financial outcome** is observed. This avoids a class of reporting fraud where review activity inflates without recovery following.

A reviewer can:

- **Approve** — sets `action_taken=approve`, leaves the exception open until `cash_received` posts
- **Resubmit corrected** — same; open until adjudication
- **Escalate** — same; assigns to coding team or contracts team; open until they take a downstream action
- **Reject** — closes the exception with `action_taken=reject` and a rationale; counts as zero realized value

The override log records the disposition action. The financial outcome closes the exception.

## 7. What V1 does NOT do (and why this runbook matters)

V1 measures **modeled** value (calibrated risk × dollars at risk). V2 measures **realized** value. The two will diverge — it's the gap that tells the TPM whether the model is well-calibrated to the actual practice's recovery behavior. Closing this gap is the core V2 product question.

If at week 12 of pilot, modeled recovery is $322K but realized recovery is $80K, that's the signal that:

- The model over-ranks easy-looking flags
- The reviewer pool can't actually work the volume
- The payer behavior we modeled doesn't match the real payer
- The accounting treatment is killing the upside

All four are addressable, but only if they're measured. This runbook is what makes them measurable.
