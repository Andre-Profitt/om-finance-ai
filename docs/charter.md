# Project Charter — O&M Finance Revenue Integrity Control Tower

**Version:** 0.1
**Owner:** Andre Profitt (TPM)
**Status:** Draft for stakeholder socialization
**Last updated:** 2026-04-24

---

## Problem statement

Community oncology practices lose 2–5% of revenue annually to preventable leakage across five surfaces: (1) claim denials and underpayments, (2) prior-authorization friction, (3) J-code/NDC pricing variance against CMS ASP, (4) GPO chargeback validity and rebate accrual accuracy, and (5) drug-waste and biosimilar-conversion economics. Existing practice-facing tools (claims-acceptance AI, GPO contracting, practice analytics, EHR) produce signal; what is missing is a **governed finance work queue** that prioritizes exceptions by dollars-at-risk, explains each flag with auditable evidence citations, and reports ROI and adoption metrics the CFO and controllership function can defend.

## Users & primary personas

| Persona | Role | Jobs-to-be-done |
|---|---|---|
| **Revenue Cycle Analyst** | Reviews flagged exceptions, drafts appeals, validates chargebacks | Work the highest-$ items first; trust the reason for the flag; submit overrides with rationale |
| **Finance Operations Lead** | Owns monthly leakage reporting, rebate accruals, ASP variance analysis | Close faster with cleaner numbers; trace every AI-assisted entry to source |
| **Controller / FP&A** | Consumes leakage KPIs, justifies ROI, manages SOX readiness | Defensible metrics; versioned model + prompt + source lineage; override audit trail |
| **O&M Practice CFO (network level)** | Benchmarks practices, informs integration roadmap for acquisitions | Practice-level leakage heatmap; drivers; post-acquisition 100-day plan |

## Value hypothesis

> If oncology-practice finance teams receive a prioritized, evidence-grounded work queue of revenue-cycle exceptions with controllership-ready audit trails, then (a) preventable leakage recovery rises 20–30% vs. unassisted review at equivalent reviewer cost, (b) close-cycle reporting confidence improves, and (c) the AI capability becomes scalable across the network because governance, adoption, and ROI are measured continuously.

## Success metrics (business-outcome)

| Metric | Target | Source |
|---|---|---|
| Precision@top-20 on reviewer queue | ≥ 0.80 | eval harness |
| Dollars-at-risk captured per reviewer hour | Lift ≥ 25% vs. unassisted baseline | modeled + reported |
| Citation precision on RAG explanations | ≥ 0.90 | eval harness |
| Abstention rate | reported (acceptable: 10–25%) | system logs |
| Override rate | < 15% steady-state; rationale categorized | reviewer UI |
| Payback period (modeled) | ≤ 9 months on mid-size practice | ROI model |
| Model-lineage completeness | 100% of scored items traceable to model version + prompt version + source doc version | Unity Catalog + MLflow |

**Explicitly NOT success metrics:** AUC on synthetic labels, MAPE on synthetic forecasts, model accuracy absent business context.

## Scope boundaries

**In scope (v1):**
- Risk scoring on synthetic oncology claims anchored to real CMS ASP + NDC-HCPCS
- Evidence-grounded exception explanation via RAG over mock payer policies + mock GPO contracts + public CMS ASP files + public HRSA OPAIS
- Controllership audit trail (model version, prompt version, source doc version, reviewer override + rationale, timestamp) in Unity Catalog
- Finance ROI dashboard
- Reviewer queue UI mock

**Out of scope (v1):**
- Any PHI or production claims data
- Automated appeal submission, prior-auth submission, or chargeback filing
- Real-time payer adjudication integration
- Clinical decision support
- Full HIPAA compliance (synthetic-data-only; document the compliance *design* without claiming production readiness)

## Value hypothesis assumptions (to be validated)

1. Oncology-practice preventable leakage is concentrated enough that a top-k reviewer queue captures > 60% of dollar value in the top 20% of items — validated by calibration curve in eval harness.
2. Evidence-grounded explanations materially reduce reviewer override-without-action rate — validated by override-rationale distribution post-eval.
3. Finance leaders will accept AI-assisted recommendations if full lineage is available; they will not accept them without lineage — validated via informational interviews during the portfolio-build phase (out-of-scope for code; documented in decision log).

## Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Synthetic data not credible to hiring audience | Medium | Medium | Anchor all drug prices to real CMS ASP files; be explicit in README that claims are synthetic |
| RAG citations wrong but confident | Medium | High | Citation-similarity threshold + abstention logic; eval harness measures citation precision as a first-class metric |
| Scope creep into appeal-letter generation, prior-auth submission, etc. | High | Medium | Explicit non-goals in this charter; PRD enforces |
| 340B module reads as political advocacy | Low | High | Frame exclusively as a governance-first scenario module; policy-volatile language; no leakage advocacy |
| Databricks Free Edition compute limits block the demo | Medium | Low | Architecture is Databricks-native; execution can fall back to local Delta + MLflow for the heaviest notebooks; document the downgrade explicitly |
| Reviewer override-rate untestable without real reviewers | High | Low | Simulate override distribution from held-out labels; document the limitation in the eval report |

## Stakeholders (synthetic, for illustration)

- **Sponsor (modeled):** VP, O&M Finance Transformation
- **Product owner:** Lead TPM, Finance AI (this role)
- **Engineering partner:** Staff Data/ML Engineer (Databricks)
- **Analytics partner:** Senior Finance Analyst / FP&A
- **Consumer:** Revenue Cycle Operations Director
- **Governance:** Controllership, Internal Audit, SOX PMO
- **Advisory:** Oncology Practice CFO, Revenue Cycle SME, GPO contracting lead

## Decision rights

- **Product direction + prioritization:** TPM
- **Architecture standards:** Staff ML Engineer + Enterprise Architecture
- **Governance + audit requirements:** Controllership + SOX PMO (hard gates)
- **Go-live by practice:** O&M Practice CFO (adoption criteria)
- **Deprecation / model retirement:** TPM + Staff ML Engineer (jointly)

## Phased delivery

| Phase | Timebox | Definition of done |
|---|---|---|
| 0 — Scaffold | Weekend 0 | Charter, architecture, ROI drafted; landing page live; application submitted |
| 1 — Hero skeleton | Week 1 | CMS ingest, Delta schema, LightGBM baseline, MLflow tracking, ROI v1 numbers, one Loom demo |
| 2 — Evidence + eval | Week 2 | RAG citation layer, abstention, override log, PRD, eval report, decision log |
| 3 — Contract economics | Week 3 | GPO/chargeback/ASP-variance module, 340B scenario, leakage dashboard, roadmap |
| 4 — Executive artifact | Week 4 | Practice Acquisition memo, governance reference architecture, portfolio polish |

## Open questions

1. Should the hero demo surface a per-practice "integrate next" ranking, or keep that in the Week 4 executive memo only? — leaning memo-only for scope control.
2. Does the RAG layer need a dedicated vector store (Databricks Vector Search) or is file-system retrieval over ~200 documents adequate for v1? — leaning file-system for v1; document the path to production.
3. How to handle PHI-adjacent data patterns in the governance design without handling any PHI? — document a row-level-security pattern in Unity Catalog with synthetic protected attributes; call out in governance doc.
