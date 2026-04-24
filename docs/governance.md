# Governance Reference Architecture — Finance AI on Databricks + Azure

**Version:** 1.0
**Scope:** Controllership-ready governance design for the O&M Finance AI Control Tower, deployed on Databricks on Azure. Covers model, prompt, data-source, reviewer, and audit-trail lineage; HIPAA adjacency; SOX-aligned change control; and drift / rollback procedures.
**Last updated:** 2026-04-24

---

## 1. What this document answers

A Lead Finance AI TPM must be able to answer these questions on demand, with lineage, before a CFO or internal auditor asks:

1. _What model generated this decision, trained on what data, at what version?_
2. _What prompt was used, what was retrieved, and what evidence was cited?_
3. _Who reviewed it, what did they decide, and why?_
4. _When did calibration last pass? When will the model next be re-trained?_
5. _If this AI-assisted entry were challenged in audit, how would we reconstruct it?_

The design below uses Databricks + Azure primitives so these questions have a deterministic answer at any point in time.

---

## 2. Stack alignment

| Concern                            | Primitive                                                              | Why                                                                                         |
| ---------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Table lineage + row-level security | Unity Catalog schemas + column tags                                    | Native table-level lineage; practice-scoped RBAC via row filters                            |
| Model registry + model cards       | MLflow Model Registry (Unity Catalog-backed)                           | Governance follows the model across stages (`None` → `Staging` → `Production` → `Archived`) |
| Prompt registry                    | MLflow Prompt Registry (or a `prompts` Delta table if older workspace) | Every prompt version is durable and cross-referenced from scored rows                       |
| Retrieval artifacts                | Delta table of corpus chunks + embeddings, SHA-hashed source version   | Any cited chunk is reproducible from its `(doc_id, section_title, doc_version)`             |
| Serving                            | Databricks Model Serving (real-time) or Mosaic AI Batch                | Authenticated, logged, rate-limited                                                         |
| Data ingest                        | Databricks Asset Bundles                                               | Infrastructure-as-code; PRs + reviews on every change                                       |
| Reviewer action                    | Databricks App or embedded workstation panel                           | UI writes append-only to `override_log`                                                     |
| Monitoring                         | Lakehouse Monitoring + Databricks SQL alerts                           | Drift / calibration / abstention / override alarms                                          |
| Audit export                       | SQL Warehouse + scheduled query to encrypted blob                      | 7-year retention; encrypted at rest with customer-managed keys                              |

---

## 3. Medallion layout with governance metadata

```
rev_integrity.bronze.*          raw ingests, including claim feeds, policy docs
rev_integrity.silver.*          normalized entities (drug_economics, claim_lines)
rev_integrity.gold.*            scored_exceptions, explained_exceptions, override_log
rev_integrity.governance.*      model_registry, prompt_registry, source_doc_versions, audit_trail
```

Each scored row carries the full provenance:

```
scored_exceptions columns (governance subset):
  claim_id
  model_name             = "rev_integrity.risk_scorer"
  model_run_id           = MLflow run id
  model_version          = registered version number
  scored_at              = timestamp
  risk_score             = uncalibrated
  risk_score_calibrated  = isotonic output
  calibration_fold_id    = reference to the held-out calibration run
```

Each explained row adds:

```
explained_exceptions columns (governance subset):
  citation_doc_id
  citation_section
  citation_score
  citation_doc_version   = SHA of the source document at retrieval time
  prompt_version
  retrieved_top_k        = full set of candidates considered (auditable)
  abstained              = bool
```

Override log:

```
override_log columns:
  override_id, exception_id, reviewer_id, original_*, decision,
  agreed_with_model, was_abstention, rationale_category,
  rationale_text (free-text, PII-reviewed), decided_at, model_run_id
```

The append-only contract is enforced by Unity Catalog table properties (`delta.enableChangeDataFeed=true`, table owner-only `DELETE`).

---

## 4. PHI / HIPAA overlay

No production deployment should process PHI until the following are in place. This document specifies the design; the acceptance checkpoint is a BAA + DUA + privacy-office sign-off.

1. **Azure BAA** in force for the hosting subscription.
2. **Customer-managed keys** (CMK) for all Delta table encryption at rest.
3. **Private networking** — Databricks workspace in VNet injection; no public IP endpoints; egress only via controlled NAT.
4. **Row-level security** in Unity Catalog scoped to `practice_id`, enforced on `claim_lines` and downstream gold tables.
5. **PHI minimization** — no free-text narrative fields committed to bronze without redaction; synthetic attributes only in dev.
6. **DLP on prompts** — any LLM layer (v2) runs with a DLP proxy that strips PHI patterns before outbound calls; Azure OpenAI with `data_residency=us` and content-filter configured.
7. **Access logs** — Unity Catalog access events streamed to a SIEM; queries against PHI-adjacent tables require a break-glass justification field.
8. **Retention** — PHI-adjacent tables follow a practice-specified retention schedule, with cold tiering after 90 days.
9. **Incident runbook** — standard HIPAA breach-notification runbook mapped to Databricks audit logs.

---

## 5. SOX-aligned change control

Finance AI changes that affect a scored amount, a reviewer queue rank, a cited clause, or a dashboard ROI number are SOX-relevant. The control below applies to all such changes.

1. **PR-required change control.** Every change to the model, prompt, calibration fold, retriever corpus, citation threshold, or eval rubric goes through a peer-reviewed PR in the Git repo backing the Asset Bundle.
2. **Two-person integrity** (segregation of duties). The PR author and the promotion approver are different humans; both are logged with the change record.
3. **Shadow-production promotion.** New model or prompt versions run in shadow mode against the same data as production for at least one eval cycle; eval artifacts attached to the PR.
4. **Eval gates.** Promotion blocked unless the eval report meets the acceptance bar (citation precision ≥ 0.9, calibrated precision@100 ≥ 0.80, calibration slope in [0.85, 1.15]).
5. **Rollback.** Every production version is reversible by reverting the MLflow alias; scored rows retain both scores (uncalibrated + calibrated) to support point-in-time reconstruction.
6. **Retention.** Model, prompt, and source-doc versions retained 7 years append-only.
7. **Change log.** Every promotion produces a row in `governance.change_log` with PR link, approver, eval artifact pointer, and rationale.

---

## 6. Drift, alarms, and model refresh SLA

Metrics emitted from every pipeline run and monitored:

| Metric                              | Alarm threshold                                | Action                                                                  |
| ----------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------- |
| Calibration slope                   | outside [0.85, 1.15] for two consecutive runs  | Open model-refresh ticket; refit calibration fold                       |
| Citation precision                  | below 0.90 for two consecutive runs            | Open prompt / retriever ticket; review failing exception types          |
| Abstention rate                     | above 40% or below 5% for two consecutive runs | Review corpus coverage (too low) or retrieval threshold (too high)      |
| Override rate (disagree with model) | above 25% sustained over 30 days               | Review top-of-queue quality; consider retraining                        |
| Coverage — claims with a score      | below 99%                                      | Ingest / feature pipeline incident                                      |
| Dollar capture @ top-100 vs. target | below 70% of modeled target over two weeks     | Product review: are exception types miscalibrated to current payer mix? |

Alerts route via Databricks SQL → Slack / email / PagerDuty. Monthly calibration-health dashboard reviewed by the TPM + staff ML engineer.

---

## 7. Reviewer audit trail

The override log is the canonical audit artifact for any AI-assisted finance decision. Every row answers:

- Who reviewed (reviewer_id, practice scope)
- What model version + prompt version + retrieved-doc version produced the recommendation
- What the reviewer decided + why (rationale category + free-text)
- Whether the decision was on an explained or abstained item
- When the decision was made

Export path: `governance.audit_export` — scheduled nightly query writes to an encrypted blob with 7-year retention. Auditor requests are fulfilled by filtering this blob on a date range; no queries against production tables required.

---

## 8. Appeal-assistant governance (v2 LLM layer)

When the LLM paraphrasing layer ships (v2), the citation contract must be preserved:

1. The LLM receives only the retrieved chunks + the structured exception facts as input.
2. The output must quote or cite the retrieved chunk by `(doc_id, section_title)`.
3. A post-generation verifier checks that a fragment of the retrieved span appears in the output. If verification fails, the system abstains and routes to human (never publishes the LLM output).
4. Prompts are versioned in the prompt registry; every response is logged with the prompt version + model version + retrieval set.
5. LLM outputs are never auto-submitted to a payer. The reviewer always approves.
6. DLP on inbound prompts; outbound responses logged for privacy review.

---

## 9. What this does NOT attempt to govern

- Clinical decisions — this is a finance product. Governance for clinical AI belongs to the clinical leadership and is a separate document.
- Automated payer communications — the appeal-assistant always requires human review before any outbound message.
- Contract negotiation — the system surfaces patterns; contract changes go through the contracts office.

---

## 10. Artifacts the TPM maintains

- This document (updated on every material design change)
- `docs/decision-log.md` — running decision log with rationale
- MLflow model cards per registered model
- Prompt registry records per prompt version
- Change-log table in Unity Catalog
- Quarterly calibration + drift report

---

## 11. Crosswalk to McKesson JR0143772

| JD phrase                                                                 | Answer in this doc                           |
| ------------------------------------------------------------------------- | -------------------------------------------- |
| "modern digital architectures, AI/ML product lifecycles, data ecosystems" | §2 Stack alignment                           |
| "feasibility, scalability, alignment with architectural standards"        | §2, §3, §6                                   |
| "regulated environment"                                                   | §4 HIPAA overlay, §5 SOX change control      |
| "highly matrixed teams"                                                   | §5 two-person integrity, §7 reviewer audit   |
| "technical specs, release notes, and user guides"                         | This doc + `docs/prd.md` + `docs/roadmap.md` |
| "KPIs, risks, resource allocation"                                        | §6 drift / alarms / SLA                      |
| "decision logs and technical rationale"                                   | §5 change log, §10 artifacts                 |
