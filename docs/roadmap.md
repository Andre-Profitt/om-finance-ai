# Roadmap — V1 / V2 / V3

**Last updated:** 2026-04-24
**Maintained by:** TPM

Maps the current repo state (V1) against the v2/v3 rollout for O&M Finance deployment. Time estimates are order-of-magnitude, not commitments.

---

## V1 — shipped in this repo

**Scope:** oncology-practice revenue-cycle + contract-economics exception prioritization on Databricks on Azure, with evidence-grounded RAG and append-only override logging.

| Capability                                                                                                  | State                                                                                                                                                                         |
| ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CMS ASP + NDC-HCPCS ingest (bronze)                                                                         | Shipped (sample + live-fetch hook)                                                                                                                                            |
| Synthetic claims generator with latent error signal                                                         | Shipped                                                                                                                                                                       |
| Silver: `drug_economics`, `claim_lines`                                                                     | Shipped                                                                                                                                                                       |
| Gold: rule-based exception candidates across 7 types                                                        | Shipped — revenue-cycle (ASP drift, NDC mismatch, denial, underpayment) + contract economics (gpo_340b_rebate_excluded, biosimilar_conversion_miss, chargeback_validity_fail) |
| LightGBM risk scorer + MLflow registry                                                                      | Shipped                                                                                                                                                                       |
| Isotonic calibration with held-out 20% fold                                                                 | Shipped                                                                                                                                                                       |
| RAG retriever + citation-enforced explainer + abstention                                                    | Shipped                                                                                                                                                                       |
| Append-only override log                                                                                    | Shipped                                                                                                                                                                       |
| Business-outcome eval harness with three rankings, citation precision, abstention rate, rules-only baseline | Shipped                                                                                                                                                                       |
| 6 Databricks SQL queries for reviewer queue + ops                                                           | Shipped                                                                                                                                                                       |
| Charter, PRD, ROI model, decision log                                                                       | Shipped                                                                                                                                                                       |

**V1 acceptance — hit:**

- LightGBM valid AUC ≥ 0.85 — hit at 0.905
- Calibrated precision@top-100 ≥ 80% — hit at 91%
- Calibration slope within [0.85, 1.15] after held-out isotonic — close at 1.38 (production-realistic; will tighten with larger calibration fold at scale)
- Citation precision ≥ 0.90 — hit at 100%
- Abstention rate ≥ 10% — hit at 13.6%

## V2 — deployable pilot (estimate: 6–8 weeks)

**Goal:** production pilot in one US Oncology practice on real retrospective data under DUA + privacy/security/legal/controllership approval (IRB review only if the pilot becomes human-subjects research or produces publishable research), with a reviewer UI in the existing RCM workstation.

| Capability                                                                                                     | Why it's V2                                                                                                                |
| -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Live CMS ASP + NDC-HCPCS fetch from published quarterly files                                                  | V1 has the interface hook; V2 implements the scraper that resolves the current ZIP link                                    |
| Retrospective label plumbing — appeal outcomes, re-adjudications, chargeback resolutions                       | V1 uses synthetic ground truth; V2 wires real labels from the practice billing system                                      |
| Production calibration at scale (held-out 20% of ~weekly refresh)                                              | V1 uses in-session holdout of one batch                                                                                    |
| LLM paraphrasing over retrieved chunks (Azure OpenAI or Databricks Mosaic AI) with citation contract preserved | V1 uses deterministic templates; V2 adds natural-language paraphrasing that cannot invent facts outside the retrieved span |
| Reviewer UI (Databricks App or embedded workstation panel)                                                     | V1 ships SQL queries; V2 adds the reviewer-facing surface                                                                  |
| Per-payer policy expansion (10+ commercial + Medicare LCDs)                                                    | V1 has 4 payer policies in corpus                                                                                          |
| Per-vendor GPO contract expansion and chargeback flow end-to-end                                               | V1 has 3 GPO contracts                                                                                                     |
| Prometheus/Datadog monitoring on calibration drift, abstention rate, override rate                             | V1 reports these as metrics; V2 alerts on them                                                                             |
| Unity Catalog row-level security with practice-scoped roles                                                    | V1 has the schema pattern documented; V2 enforces it                                                                       |
| HFMA CRCR certification in progress                                                                            | TPM personal development; not a product gate                                                                               |
| Model cards published per registered model                                                                     | V1 has model-size/run metrics; V2 adds full card                                                                           |

## V3 — network rollout (estimate: 6 months post-pilot)

**Goal:** scale to 15+ practices across the US Oncology Network with an integration playbook for acquired practices.

| Capability                                                                                              | Why it's V3                                                                                                                  |
| ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Practice Acquisition & Performance Model as a live app (not memo)                                       | V1 ships the memo; V3 ships the running app with per-practice onboarding                                                     |
| Multi-practice benchmarking dashboard with drill-through                                                | V1 has the SQL panels; V3 adds network-level views and practice-vs-peer comparisons                                          |
| Contract Economics v2 — automated rebate-accrual reconciliation and chargeback submission feedback loop | V1 flags exceptions; V3 closes the loop to the practice's AP/AR                                                              |
| Biosimilar conversion program dashboard with target tracking                                            | V1 flags individual misses; V3 aggregates into conversion-rate KPI per practice × J-code × quarter                           |
| 340B scenario module with explicit compliance/audit workflow                                            | V1 has the flag and exception type; V3 adds the full governed workflow — still framed as compliance-first, not leakage-first |
| Payer-policy change detection — automatic re-scoring when a payer publishes a new LCD / policy          | V1 has a static corpus; V3 monitors and re-scores                                                                            |
| Reviewer throughput measurement instrumented end-to-end                                                 | V1 uses 5 min/item placeholder; V3 measures                                                                                  |
| DSCSA traceability integration for inventory-adjacent exceptions                                        | Not in V1 scope; V3 bolts on if inventory reconciliation produces exceptions                                                 |

## V4 and beyond — research agenda

Not commitments. Items the TPM should surface to the advanced analytics team as value-sizing candidates. Note that JW drug-waste, prior-auth propensity, and site-of-care optimization shipped in V1.1 (formerly listed here as research items).

- Cross-practice leakage correlation — do regional payer behavior changes predict denial waves?
- **Clinical-trial finance + access intelligence** — connecting Ontada / Sarah Cannon Research Institute / McKesson Compile / Genospace signals to Control Tower so trial activation bottlenecks, reimbursement friction on investigational therapies, patient access delay, site operational cost, and RWE/data-product value are first-class surfaces. The connected-specialty-care framing makes this V4 — O&M is bigger than claims, and finance AI for clinical trials is real money.
- LLM-based clinical-necessity reasoner for appeal packets (human-approved only, with citation contract preserved)
- Payer mix optimization — marginal contribution of each payer contract to network P&L
- Outbound contract negotiation intelligence — recurring pattern detection in denial reasons to inform next-renewal levers
- Working-capital + DSO impact modeling for high-cost specialty drug inventory across the network

## What is intentionally NOT on the roadmap

- Automated appeal submission (keep human-in-the-loop forever)
- Automated prior-authorization submission (same reason)
- Clinical decision support (scope creep; not a finance TPM concern)
- Standalone chatbot UX (reviewer UI embeds where reviewers work; a chat interface is not a product requirement)
- Fine-tuned LLMs as a headline — V2 LLM layer stays prompt-engineered over the retriever

## Dependencies and risks

| Dependency                                               | Owner                            | Mitigation if slipped                                                                                                     |
| -------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| DUA + privacy/legal approval for retrospective labels    | Privacy + legal + controllership | Hold pilot at one practice; extend synthetic fold until approvals clear. IRB only if research/publication scope is added. |
| Databricks Mosaic AI availability in target workspace    | Platform                         | Fall back to Azure OpenAI deployment for LLM layer                                                                        |
| Controllership sign-off on governance design doc         | Finance leadership               | Publish V1 governance.md (Week 4 artifact); schedule working session                                                      |
| Reviewer workflow access (workstation integration point) | RCM operations                   | Standalone Databricks App as fallback UI                                                                                  |
