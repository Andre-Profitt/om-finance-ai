# O&M Finance AI — Revenue Integrity Control Tower

**A Databricks-native, controllership-ready AI product prototype for oncology-practice revenue integrity: claims leakage prioritization, evidence-grounded exception explanation, contract/chargeback economics, and practice-acquisition finance.**

> The finance-side operating layer above existing O&M practice-facing tools (claims acceptance, GPO savings, regimen and practice analytics, oncology EHR) — focused on ROI sizing, exception prioritization, model evaluation, auditability, and adoption metrics.

**Status:** Week 0 — portfolio in progress. Architecture, charter, and ROI model drafted. Hero build in Week 1.

**Author:** Andre Profitt · [LinkedIn](https://www.linkedin.com/in/andreprofitt) · built as a public Lead-TPM-Finance-AI portfolio artifact.

**Not affiliated with any healthcare distributor, GPO, or EHR vendor. No PHI. All claims data is synthetic; drug prices anchored to public CMS ASP Part B files.**

---

## Why this exists

Community-oncology practice economics hinge on revenue-cycle precision: buy-and-bill margins, J-code/NDC coding, prior authorization, GPO rebate and chargeback validity, ASP drift, specialty-drug waste (JW modifier), biosimilar conversion, and payer-policy exceptions. Finance teams need an AI layer that does not just predict denials — it surfaces *which exceptions to work first, why they were flagged, and what the ROI looks like*, with every decision traceable for controllership and SOX review.

This repo is the governed work-queue that sits above existing revenue-cycle and practice-analytics tooling. It is built for one Lead TPM question: *"Can this AI capability be scaled across an oncology network with known risk, known cost, and defensible adoption metrics?"*

## What's in here

| Surface | Artifact | Status |
|---|---|---|
| Product thesis | [docs/charter.md](docs/charter.md) | v0.1 drafted |
| System design | [docs/architecture.md](docs/architecture.md) | v0.1 drafted |
| Business case | [docs/roi-model.md](docs/roi-model.md) | v0 drafted with sensitivity |
| Product requirements | docs/prd.md | Week 2 |
| Evaluation plan | docs/eval-plan.md | Week 2 |
| Decision log | docs/decision-log.md | Running |
| Governance design | docs/governance.md | Week 4 |
| Roadmap V1/V2/V3 | docs/roadmap.md | Week 3 |

## Build plan (4 weeks)

| Week | Focus | Deliverable |
|---|---|---|
| 0 (now) | Apply + scaffold | Landing page, charter, architecture, ROI model |
| 1 | Hero skeleton | CMS ASP + NDC-HCPCS ingest, Delta schema, LightGBM baseline, MLflow, ROI v1 |
| 2 | Evidence + eval | RAG citation layer, abstention logic, override logging, PRD, decision log |
| 3 | Contract economics | GPO/chargeback/ASP variance module (340B as scenario), leakage dashboard, roadmap |
| 4 | Executive artifact | Practice Acquisition & Performance Model memo, governance reference architecture, polish |

## Stack

- **Databricks on Azure** — Unity Catalog (governance + lineage), Delta Lake (bronze/silver/gold), MLflow (experiments + registered models), Mosaic AI / Azure OpenAI (RAG), Databricks Asset Bundles (IaC), SQL Warehouse (dashboards)
- **Python** — LightGBM + SHAP for risk scoring; LangChain-style RAG with citation enforcement and abstention
- **Data sources (public, real)** — CMS ASP Part B quarterly pricing files; CMS NDC-HCPCS crosswalk; HRSA OPAIS (340B scenario only); SEC EDGAR exhibits (for contract-term patterns)
- **Synthetic layer** — 2–5k oncology claims across top-10 J-codes and four payer archetypes, anchored to real ASP prices

## Evaluation philosophy

Business-outcome metrics, not vanity model metrics:

- **Precision@top-k** on the reviewer work queue (not AUC)
- **Dollars-at-risk captured per reviewer hour** (not just recall)
- **Calibration** (actual vs. predicted leakage by decile)
- **Citation precision** on RAG explanations (wrong citation = unusable)
- **Abstention rate** (model refuses to score when evidence is weak)
- **Override rate + rationale distribution** (does finance ever trust this?)
- **Payback-period sensitivity** (±20% on prevention lift × ±20% on reviewer capacity)

See [docs/roi-model.md](docs/roi-model.md) for worked numbers.

## Scope boundaries

**In scope:** oncology-practice revenue-cycle leakage prioritization, evidence-grounded exception explanation, GPO / chargeback / ASP-variance exception module, 340B scenario module (governance-first framing), practice-acquisition finance memo.

**Out of scope:** PHI handling (synthetic only), clinical decision support, prior-auth submission automation, appeal letter auto-send, production HIPAA compliance, payer-specific API integrations, real-time claim adjudication.

## License

MIT. Use freely. Attribution appreciated.
