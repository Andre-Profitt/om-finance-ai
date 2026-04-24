# PRD — Revenue Integrity Control Tower

**Version:** 1.0
**Status:** Draft (v1 implementation shipped; v2 in planning)
**Owner:** Andre Profitt (TPM)
**Last updated:** 2026-04-24

---

## 1. Problem

Community-oncology practices operated within the O&M network lose 2–5% of revenue per year to preventable leakage across a small number of surfaces (claim denials, underpayments, J-code/NDC coding errors, GPO chargeback validity, and ASP drift). Existing practice-facing tooling — claims acceptance, GPO savings analytics, practice analytics, oncology EHR — already produce signal on the individual surfaces. What is missing is a **governed, controllership-ready work queue** that prioritizes flagged exceptions by dollars at risk, explains each flag with auditable citation to the underlying policy or contract clause, and reports ROI and adoption the O&M finance leadership can defend.

## 2. Users

| Persona                | Job-to-be-done                                                                              | Primary v1 deliverable                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Revenue cycle analyst  | Work the highest-$ exceptions first; trust the flag reason; submit overrides with rationale | Calibrated reviewer queue + cited explanation per exception               |
| Finance ops lead       | Monthly leakage reporting; rebate accruals; ASP variance analysis                           | ROI aggregates + calibration + override distribution                      |
| Controller / FP&A      | Defensible metrics; model + prompt + source lineage; audit trail                            | MLflow registered model + append-only override log + citation enforcement |
| Practice / network CFO | Benchmark practices; inform acquisition integration roadmap                                 | Per-practice leakage heatmap (v3) + 100-day integration model (v4)        |

## 3. Value hypothesis

If finance receives a calibrated, evidence-grounded work queue of revenue-cycle exceptions, then for a mid-size oncology practice:

- Preventable leakage recovery rises materially at equivalent reviewer cost
- Close-cycle leakage reporting confidence improves because every AI-assisted entry traces to a cited clause and a registered model version
- The capability scales across the network because governance, adoption, and ROI are measured continuously

Quantified target (from the ROI model): 25% prevention lift on addressable leakage → $1.31M net annual value per mid-size practice @ 1.5-month payback, with sensitivity tables documented.

## 4. v1 scope — what shipped

### 4.1 Risk scoring

- LightGBM binary classifier on 16 features (claim magnitude, billed-to-ASP ratio, rule indicators, payer one-hots, HCPCS ordinal, biosimilar flag)
- Trained on 75/25 split of synthetic exception candidates, early-stopping on validation AUC
- MLflow experiment + registered model `rev_integrity.risk_scorer`
- Gain-based feature importance as the v1 explainer
- **Acceptance:** valid AUC ≥ 0.85, precision@top-100 ≥ 80% on both P(leakage) and calibrated expected-recovery rankings
- **Shipped:** valid AUC 0.907; calibrated precision@100 93.0%

### 4.2 Isotonic calibration

- Sklearn `IsotonicRegression` fit on candidate scores → `risk_score_calibrated`
- Reviewer queue defaults to `expected_recovery_calibrated = risk_score_calibrated × dollars_at_risk`
- **Acceptance:** calibration slope in [0.9, 1.1] post-calibration
- **Shipped:** slope 1.78 → 1.00

### 4.3 RAG explainer with citation enforcement and abstention

- Corpus: four payer policies + three GPO contracts, chunked by `##` sections
- Retriever: `all-MiniLM-L6-v2` embeddings + cosine similarity (swap for Databricks Vector Search at scale — same interface)
- Query templates keyed on `exception_type`
- Template-based explanation that quotes the top retrieved chunk _only if_ its similarity ≥ 0.64; otherwise **abstains** with a structured reason
- **Acceptance:** citation precision ≥ 0.90 on explained exceptions; abstention rate ≥ 10% (forces honest abstention rather than confident mis-citation)
- **Shipped:** citation precision 100% on explained; abstention rate 25.5%

### 4.4 Governance / override log

- Append-only Parquet at `data/gold/override_log.parquet`
- Schema includes override_id, exception_id, reviewer_id, original score (uncalibrated + calibrated), dollars at risk, decision, agreed-with-model flag, was-abstention flag, rationale category, rationale text, decided_at, model_run_id
- Simulated reviewer decisions on top-100 queue with a realistic agree-more-with-explained-than-abstained bias
- **Acceptance:** 100% of scored items traceable to model run + prompt version + source doc version
- **Shipped:** override rows carry model_run_id; abstention path preserves best-candidate citation for audit

### 4.5 Business-outcome eval harness

Metrics in public artifacts:

- Precision@20/50/100 (two rankings)
- Dollars captured @ top-k (three rankings incl. calibrated)
- Dollars per reviewer-hour
- Rules-only uniform baseline
- Citation precision (overall + by exception_type)
- Abstention rate
- Calibration slope uncalibrated vs. calibrated

AUC is logged in MLflow for model debugging but is not a public headline metric.

### 4.6 Pipeline + CLI + tests

- `oai-finance build` runs all nine stages end-to-end, ~8 s after first sentence-transformer model download
- `tests/test_smoke.py` asserts end-to-end run + the invariant that expected-recovery ranking captures ≥ P(leakage) ranking at top-100

## 5. v1 non-goals (intentionally out of scope)

- PHI handling; synthetic data only
- Clinical decision support
- Prior-authorization submission or appeal-letter auto-send (appeal-packet-draft _assistant_ reachable via template; always human-approved)
- Real-time payer-API adjudication
- Production HIPAA compliance claim (design documented in governance.md; claim is not asserted)
- Fine-tuned LLMs (deferred — template-based explanation with strict citation enforcement beats unconstrained LLM generation on auditor-defensibility at this stage)

## 6. v2 backlog (Week 3)

In priority order:

1. **Contract economics module** — GPO rebate-tier validation, chargeback-validity checking, ASP variance detection, 340B eligibility scenario module
2. **LLM paraphrasing layer** (Azure OpenAI or local Ollama) over the retrieved chunks, with strict citation enforcement preserved from v1 (paraphrase must cite the retrieved span)
3. **Production calibration** — held-out calibration fold rather than in-frame fit
4. **Leakage dashboard** (Databricks SQL) with per-practice rollup
5. **Decision log entries** for each v2 non-trivial call

## 7. v3 backlog (Week 4)

1. Practice Acquisition & Performance Model (memo)
2. Governance reference architecture (Databricks on Azure)
3. Multi-practice rollup, benchmarking
4. Per-payer policy expansion

## 8. Success metrics (post-deployment)

Production-facing KPIs the product owner should report quarterly:

- $ captured / reviewer hour (trend)
- Override rate + override-rationale distribution (is the queue being trusted?)
- Abstention rate (is the system staying honest about evidence?)
- Practice adoption rate
- Cycle-time from flag → resolution
- Calibration drift (does the model need retraining?)
- Cost-per-exception vs. benefit realized

## 9. Risks + mitigations

| Risk                                              | Mitigation                                                                                                                                            |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Confident miscitation (RAG hallucination)         | Threshold-gated citation enforcement + abstention path; citation precision is a first-class eval metric; v2 LLM layer adds a second citation verifier |
| Calibration drift in production                   | Periodic held-out calibration refresh; alert on slope outside [0.9, 1.1] for two consecutive evaluation cycles                                        |
| Reviewer queue ignores dollar magnitude           | Primary ranking is `expected_recovery_calibrated`, not raw P(leakage)                                                                                 |
| Synthetic labels ≠ production behavior            | v2 wires in retrospective appeal-outcome labels from the practice billing system                                                                      |
| 340B module reads as policy advocacy              | Governance-first framing; scenario module, not headline; no leakage advocacy                                                                          |
| Reviewer throughput assumption (5 min/item) wrong | Override log captures reviewer-level timing in production; eval harness recomputes $/hour from measured data once collected                           |

## 10. Open questions

1. Should the reviewer queue UI be a Databricks App, an embedded panel in the existing RCM workstation, or a lightweight standalone? (TPM call in v3 after stakeholder interviews.)
2. What retention period should the override log target for SOX? Proposed: 7 years append-only, but confirm with controllership + legal.
3. How should the model card for `rev_integrity.risk_scorer` surface calibration drift to non-ML finance leaders? Proposed: single "calibration health" badge on the dashboard, with link to the run comparison.

## 11. Appendix — JD language crosswalk

For interview use. Each PRD section maps back to the McKesson JR0143772 language:

| JD phrase                                                                                               | Where in this PRD                                                                |
| ------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| "Convert ambiguous business problems into well-defined project charters, success metrics, user stories" | §1 Problem; §2 Users; §3 Value hypothesis; §8 Success metrics                    |
| "Each use case has clear scope boundaries, defined value hypotheses"                                    | §3, §4, §5                                                                       |
| "Prioritization balancing business value, feasibility, effort, and risk"                                | §6 v2 backlog; §9 Risks                                                          |
| "Feasibility, scalability, and alignment with architectural standards"                                  | See `docs/architecture.md` §Deployment                                           |
| "Build financial business cases and justify product investments"                                        | See `docs/roi-model.md`; §3 here                                                 |
| "Technical specs, release notes, and user guides"                                                       | `docs/architecture.md`, this PRD, `CLAUDE.md`                                    |
| "Decision logs and technical rationale"                                                                 | `docs/decision-log.md`                                                           |
| "Highly matrixed teams"                                                                                 | §2 Users; §10 open questions reflect cross-functional asks                       |
| "AI/ML concepts, data pipelines, APIs, and cloud platforms"                                             | Entire stack; `docs/architecture.md`                                             |
| "Regulated environment"                                                                                 | §4.4 Governance; §9 Risks; governance.md (Week 4)                                |
| "Oncology or healthcare revenue cycle management"                                                       | Entire product — oncology J-codes, NDC crosswalk, GPO chargebacks, 340B scenario |
