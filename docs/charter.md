# Project Charter — O&M Finance AI Control Tower

**Version:** 1.0 (Week 4)
**Owner:** Andre Profitt (TPM)
**Status:** Shipped — V1 working prototype live at `github.com/Andre-Profitt/om-finance-ai`
**Last updated:** 2026-04-24

---

## Problem statement

McKesson's Oncology & Multispecialty (O&M) segment is a connected specialty-care ecosystem: US Oncology Network practices, Ontada, Biologics, CoverMyMeds, Onmark GPO, iKnowMed, Glide Health, and multispecialty providers in retinal, rheumatology, gastroenterology, and neurology care. Each capability produces financial and operational signal; each is instrumented locally; none today produces a single prioritized, governed, evidence-grounded reviewer queue that tells an O&M Finance leader which AI-assisted exceptions to work first, why they were flagged, what the ROI looks like, and how the model is performing against controllership expectations.

Specialty-care practices lose **2–5% of revenue annually** to preventable leakage across revenue cycle (denials, underpayments, coding), access (prior-auth gaps), specialty drug economics (ASP variance, chargeback validity, biosimilar conversion, 340B eligibility), and practice-level inefficiency. A finance-AI product that treats these as separate workflows misses the operating reality: one reviewer, one Monday morning, one queue.

The **O&M Finance AI Control Tower** is the finance-side operating layer above existing O&M capabilities. It does not replace Glide Health, CoverMyMeds, or Onmark — it governs, prioritizes, and sizes AI use cases across them.

## Users & primary personas

| Persona                          | Role                                                            | Jobs-to-be-done                                                                                        |
| -------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Revenue cycle analyst**        | Works the reviewer queue, drafts appeals, validates chargebacks | Highest-$ items first; cited reason for every flag; override with rationale; no confident miscitations |
| **Access operations lead**       | Tracks PA gaps, documentation SLAs, access-delay cost           | Per-practice / per-payer PA performance; delay-cost-in-dollars at the network level                    |
| **Finance operations lead**      | Close cycle, leakage reporting, rebate accruals, ASP variance   | Traceable AI-assisted entries; model/prompt lineage; controllership sign-off path                      |
| **Controller / FP&A**            | KPIs, ROI justification, SOX readiness                          | Defensible business-outcome metrics; change control, override log, drift alarms                        |
| **Practice CFO (network level)** | Benchmark practices, inform acquisition / integration roadmap   | Practice-level exposure + initiative projection; multispecialty mix visibility                         |

## Value hypothesis

> If O&M Finance receives a calibrated, evidence-grounded work queue of revenue-cycle + access + contract-economics exceptions with controllership-ready audit trails, then for a mid-size specialty-care practice preventable leakage recovery rises materially at equivalent reviewer cost, close-cycle reporting confidence improves, and the capability scales across the network because governance, adoption, and ROI are measured continuously.

## Success metrics (business-outcome)

| Metric                                         | Target                                                                  | Status in V1                                |
| ---------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------- |
| Calibrated precision@top-100 on reviewer queue | ≥ 0.85                                                                  | **0.93 achieved**                           |
| Dollars-at-risk captured per reviewer hour     | ≥ 3× unassisted baseline                                                | $249K/h vs. ~$77K/h uniform baseline — 3.2× |
| Citation precision on RAG explanations         | ≥ 0.90                                                                  | **0.997 achieved**                          |
| Abstention rate                                | reported, within [10%, 40%]                                             | **26.8%** — within band                     |
| Override-with-rationale rate                   | 100% of decisions carry a rationale                                     | Shipped on override_log schema              |
| Payback period (modeled)                       | ≤ 9 months on mid-size practice                                         | **4.5 months** modeled                      |
| Model lineage completeness                     | 100% of scored items traceable to model + prompt + source-doc version   | Shipped on scored/explained schema          |
| Drift alarm coverage                           | Calibration, citation precision, abstention, override rate each alarmed | Shipped in `docs/governance.md` §6          |

**Explicitly NOT success metrics:** AUC on synthetic labels, MAPE on synthetic forecasts, model accuracy absent business context, "confidence score" without calibration.

## Scope — five capability modules (V1 shipped)

1. **Revenue Integrity Queue** — denials, underpayments, J-code/NDC coding, ASP drift
2. **Access & Prior-Auth Intelligence** — PA documentation gaps, CO-197 exposure, access-delay cost
3. **Specialty Drug Contract Economics** — ASP variance, chargeback validity, biosimilar conversion, 340B scenario (compliance-first)
4. **Practice Performance & Acquisition Model** — per-practice exposure, 100-day integration projection, network mix
5. **Governance & Audit Log** — Unity Catalog + MLflow, append-only override log, HIPAA + SOX reference architecture

All five shipped on one Databricks-native pipeline; multispecialty-aware (oncology + retinal + rheumatology + GI + neurology).

**Out of scope (V1):**

- Any PHI or production claims data
- Automated appeal submission, prior-auth auto-submission, or chargeback filing
- Real-time payer API adjudication
- Clinical decision support
- Production HIPAA compliance claim (design documented; claim not asserted)

## Assumptions

1. Leakage is concentrated enough that a top-k reviewer queue captures a meaningful majority of recoverable dollars in the top 10–20% of items — **validated in V1 calibration and capture curves**
2. Evidence-grounded explanations reduce reviewer override-without-action rate — to be validated with live reviewers in V2
3. Finance leaders accept AI-assisted recommendations only with full lineage — drives the Unity Catalog + MLflow + override-log design
4. Multispecialty generalizes from oncology primitives because the underlying mechanics (payer, drug, rebate, access) repeat — **validated in V1 by running the same pipeline across 5 specialties with 99.7% citation precision**

## Risks & mitigations

| Risk                                                | Likelihood | Impact | Mitigation                                                                                                                            |
| --------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Synthetic data not credible to the audience         | Medium     | Medium | Drug prices anchored to real CMS ASP; limitations explicit in every artifact; V2 introduces retrospective labels                      |
| Confident RAG mis-citation                          | Medium     | High   | Similarity threshold + abstention path; citation precision is a first-class eval metric; V2 LLM layer adds a second citation verifier |
| Scope creep into clinical / auto-submission         | High       | Medium | Explicit non-goals in this charter and PRD; roadmap enforces                                                                          |
| 340B framed as leakage-first                        | Low        | High   | Governance-first scenario module; policy-volatile language; no advocacy                                                               |
| Databricks Free Edition limits                      | Medium     | Low    | Local-execution compatible; architecture Databricks-native; serving-path deferred to V2                                               |
| Reviewer override-rate untestable without reviewers | High       | Low    | Simulated distribution documented as a placeholder; measured override-rate is a V2 deliverable                                        |
| Multispecialty policy corpus incomplete             | Medium     | Medium | V1 ships commercial-national PA workflow covering specialty-drug infusions broadly; V2 expands per-payer                              |

## Stakeholders (modeled for illustration)

- **Sponsor:** VP, O&M Finance Transformation
- **Product owner:** Lead TPM, Finance AI
- **Engineering partner:** Staff Data/ML Engineer (Databricks + Azure)
- **Access / RCM partner:** Director, Revenue Cycle Operations
- **Analytics partner:** Senior Finance Analyst / FP&A
- **Consumer:** Revenue cycle analysts + access operations
- **Governance:** Controllership, Internal Audit, SOX PMO, Privacy
- **Advisory:** Practice CFOs across oncology + multispecialty, Pharmacy Operations, Contracts Office

## Decision rights

- **Product direction + prioritization:** TPM
- **Architecture standards:** Staff ML Engineer + Enterprise Architecture
- **Governance + audit requirements:** Controllership + SOX PMO (hard gates)
- **PHI handling readiness:** Privacy Office + Legal (hard gate)
- **Go-live by practice:** Practice CFO (adoption criteria)
- **Deprecation / model retirement:** TPM + Staff ML Engineer (jointly, logged)

## Phased delivery

| Phase                              | Timebox   | Definition of done                                                                  | Status   |
| ---------------------------------- | --------- | ----------------------------------------------------------------------------------- | -------- |
| 0 — Scaffold + apply               | Weekend 0 | Landing page + charter + architecture + ROI                                         | **Done** |
| 1 — Hero skeleton                  | Week 1    | Ingest + silver + rules + LightGBM + MLflow + ROI v1                                | **Done** |
| 2 — Evidence + eval                | Week 2    | RAG + abstention + calibration + override log + PRD                                 | **Done** |
| 3 — Contract economics             | Week 3    | 340B + biosimilar + chargeback + SQL dashboards + roadmap + held-out calibration    | **Done** |
| 4 — Specialty + access + executive | Week 4    | Multispecialty + access/PA module + practice performance memo + governance ref arch | **Done** |

## Open questions (living)

1. **Target reviewer UI surface.** Databricks App, embedded workstation panel, or both? → decide in V2 after stakeholder interviews.
2. **LLM paraphrasing model selection.** Azure OpenAI, Databricks Mosaic AI, or local via Ollama? → V2 evaluates all three against the citation contract; whichever wins enters production.
3. **Multispecialty payer-policy coverage.** How far beyond commercial-national PA to expand in V2? Proposed: top-10 payers by $ volume across the network.
4. **Calibration refresh cadence.** Weekly held-out refresh is the default; should high-variance practices trigger more frequently?
5. **340B scenario enablement.** Which practices enable the 340B module vs. leave it off? Governance should default to _off_ unless compliance signs off.

## Appendix — crosswalk to JR0143772

This charter responds directly to the job posting's responsibilities.

| JD phrase                                                                          | Charter section                                                        |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| "Own and evolve the AI roadmap"                                                    | Phased delivery + `docs/roadmap.md`                                    |
| "Convert ambiguous business problems into charters, success metrics, user stories" | Problem statement, users, value hypothesis, success metrics            |
| "Clear scope boundaries, defined value hypotheses"                                 | Scope, assumptions                                                     |
| "Prioritization balancing business value, feasibility, effort, and risk"           | Risks table + `docs/roadmap.md` V2/V3 ranking                          |
| "Feasibility, scalability, alignment with architectural standards"                 | `docs/architecture.md` + `docs/governance.md`                          |
| "Build financial business cases and justify product investments"                   | Success metrics + `docs/roi-model.md` + practice performance memo      |
| "Own financials including budget adherence and ROI analysis"                       | ROI model + practice performance memo + modeled payback                |
| "Monitor KPIs, risks, resource allocation"                                         | Success metrics + risks + `docs/governance.md` §6                      |
| "Technical specs, release notes, user guides"                                      | This charter + PRD + architecture + roadmap                            |
| "Decision logs and technical rationale"                                            | `docs/decision-log.md`                                                 |
| "Highly matrixed teams"                                                            | Stakeholders + decision rights                                         |
| "Regulated environment / healthcare"                                               | `docs/governance.md` HIPAA + SOX sections                              |
| "Oncology or healthcare revenue cycle management"                                  | Revenue Integrity + Access modules; oncology + multispecialty coverage |
