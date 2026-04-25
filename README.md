# O&M Finance AI Control Tower

**Finance AI operating layer for McKesson's Oncology & Multispecialty ecosystem — revenue integrity, access/prior-auth intelligence, specialty drug economics, and practice performance across oncology, retinal, rheumatology, gastroenterology, and neurology care.**

> The finance-side operating layer above O&M's existing practice-facing capabilities (Glide Health claims acceptance, CoverMyMeds access automation, Onmark GPO savings, Regimen Profiler / Practice Insights analytics, iKnowMed EHR, Ontada data). Focused on ROI sizing, exception prioritization, evidence-grounded explanation, controllership audit trail, and adoption metrics — so practices can reduce administrative burden, accelerate access, and keep providers focused on patients.

**Status:** V1 shipped (Weeks 0–4 + polish). Working end-to-end pipeline: eight exception types across revenue-cycle + access + contract economics; multispecialty coverage across five specialties; cross-validated isotonic calibration; evidence-grounded RAG with honest abstention; flag-gated LLM paraphrase layer with strict citation contract; simulated override log; per-practice performance + acquisition model; governance reference architecture; eight Databricks SQL dashboard queries; Streamlit reviewer-queue mock; CI green on every push; refinement plan covering V1 → V4 in [docs/refinement-plan.md](docs/refinement-plan.md).

**Author:** Andre Profitt · [LinkedIn](https://www.linkedin.com/in/andreprofitt) · built as a public Lead-TPM-Finance-AI portfolio artifact.

**Not affiliated with McKesson, US Oncology Network, Ontada, CoverMyMeds, Glide Health, or any other named entity. No PHI. All claims data is synthetic; drug prices anchored to public CMS ASP Part B files.**

---

## Run it yourself

```bash
git clone https://github.com/Andre-Profitt/om-finance-ai
cd om-finance-ai
make install                          # uv sync --all-extras
make demo                             # end-to-end pipeline
uv run oai-finance practice-analysis  # per-practice + acquisition model
make mlflow-ui                        # browse model runs
make test                             # smoke test
```

The `make demo` command runs a nine-stage Databricks-native pipeline and produces `artifacts/eval_report.md`, calibration and capture-curve plots, an MLflow-registered LightGBM model, isotonic-calibrated scores, evidence-grounded per-exception explanations, and a simulated override log. The `practice-analysis` CLI produces a network + target-practice + 100-day integration projection feeding the executive memo at `docs/practice-performance-memo.md`.

## What the Control Tower does

Five capability modules, all built on one Databricks-native pipeline. All metrics below are produced by the running code on synthetic data with drug prices anchored to real CMS ASP.

### 1. Revenue Integrity Queue

Claims at risk of denial, underpayment, or coding mismatch — prioritized by calibrated expected recovery, cited to specific policy or contract clause, or routed to human when evidence is weak.

### 2. Access & Prior-Authorization Intelligence

Claims with PA gaps, CO-197 denials, and expected access-delay operational cost. Cites payer PA workflow documentation for every flag. Complements existing access tooling (e.g., CoverMyMeds) by scoring pre-bill risk and quantifying delay cost at the network level.

### 3. Specialty Drug Contract Economics

ASP / J-code / NDC variance, chargeback validation, biosimilar conversion, 340B scenario as a compliance-first module (not a headline). Cites GPO and payer contract clauses.

### 4. Practice Performance & Acquisition Model

Per-practice exposure, exception mix, payer mix, and a 100-day integration projection with five sequenced initiatives. Feeds the executive memo with real computed numbers, not prose estimates.

### 5. Governance & Audit Log

Append-only override log with model version, prompt version, retrieved-doc version, reviewer rationale. Full reference architecture for Databricks + Azure deployment (Unity Catalog RBAC, PHI/HIPAA overlay, SOX-aligned change control, drift alarms) in `docs/governance.md`.

## Pipeline architecture

Nine stages, Databricks-native (Delta, Unity Catalog-ready schemas, MLflow tracking). Runs locally on Parquet today; the same code deploys to Databricks on Azure without architectural change.

1. **Bronze — CMS ingest.** Real CMS ASP + NDC-HCPCS crosswalk (sample snapshot committed; live-fetch hook ready).
2. **Bronze — synthetic claims.** 5,000 claims across 14 HCPCS codes spanning oncology + retinal + rheumatology + GI + neurology; 4 payer archetypes; latent error state observed noisily by rules.
3. **Silver — drug economics + claim lines.** ASP ratios, NDC validity, paid/allowed ratios, specialty dimensions, 340B flags.
4. **Gold — rule-based exception candidates.** Eight exception types in priority order: `access_pa_gap`, `gpo_340b_rebate_excluded`, `chargeback_validity_fail`, `biosimilar_conversion_miss`, `ndc_hcpcs_mismatch`, `asp_drift`, `underpayment`, `denial`.
5. **Gold — LightGBM risk scoring + MLflow.** 30 features including specialty + PA + 340B flags; registered model with gain-based feature importance.
6. **Gold — isotonic calibration (5-fold CV).** Out-of-fold isotonic; sample-weighted reliability slope **0.99** (target band 0.85–1.15).
7. **RAG — evidence-grounded explanation.** Dense retrieval over 5 payer policies + 3 GPO contracts. Quote-or-abstain citation enforcement.
8. **Governance — override log.** Append-only, simulated top-100 reviewer decisions.
9. **Eval — business-outcome report.** Three rankings, rules-only baseline, citation precision, abstention rate, per-type precision.

## Headline results (5,000 synthetic claims, seed 20260424)

**Reviewer-queue rankings on 1,573 exception candidates across 8 types:**

| Metric                        | P(leakage) | expected recovery | **expected recovery (calibrated)** |
| ----------------------------- | ---------- | ----------------- | ---------------------------------- |
| Precision@100                 | 100.0%     | 93.0%             | **93.0%**                          |
| Dollars captured @ top-100    | $1,042,224 | $2,077,531        | **$2,077,531**                     |
| Dollars / reviewer-hour @ 100 | $125,067/h | $249,304/h        | **$249,304/h**                     |

**Network view (20 practices, synthesized from the same run):**

- Total dollars at risk: **$7.17M**
- Expected recovery: **$5.84M**
- Access delay cost: **$31.1K**
- Specialty $ mix: oncology 68% · gastroenterology 19% · neurology 7% · retinal 4% · rheumatology 2%

**Target-practice integration model (`PR-012`, oncology, non-340B, auto-selected):**

- 250 claims, 53 exceptions, 21% exception rate
- $626.9K at risk, $543.2K expected recovery
- 100-day plan: five initiatives → $322.2K projected recovery, $292 reviewer cost, **4.5-month modeled payback**

**Evidence grounding (8 exception types, 8 policy / contract documents):**

- Citation precision on explained exceptions: **99.7%**
- Abstention rate: **26.8%** — refuses to cite when retrieval < 0.64 similarity
- Override agreement (simulated top-100): **65%**

**Model diagnostics:**

- LightGBM valid AUC: 0.925
- Calibration slope: 1.12 uncalibrated → **0.99 after 5-fold CV isotonic** (within the reliability target band of 0.85–1.15)

## Sample output (auditable)

```
Claim CLM-000076 billed HCPCS J9228 with NDC 57894-071-01, which is not in
the CMS NDC-HCPCS crosswalk for J9228. Per Medicare LCD L00000 — Oncology
Intravenous Biologic Agents §NDC-HCPCS Mapping Requirements: "Every claim
for a drug billed under an HCPCS J-code MUST include a corresponding National
Drug Code (NDC) from the CMS NDC-HCPCS crosswalk for that J-code and
effective date. …" Expected outcome: commercial_regional will deny with
CO-16. Action: resubmit corrected claim with a crosswalk-valid NDC or
escalate to coding.
```

Calibrated risk score: 1.00 · Dollars at risk: $41,429 · Citation similarity: 0.756

And when retrieval is too weak to cite confidently:

```
No policy or contract clause in the current corpus exceeded the similarity
threshold (0.64); best candidate was commercial_regional_prior_auth_oncology
§Prior Authorization Required at similarity 0.59. Routing to human reviewer
without a model-generated explanation.
```

## Docs

| Surface                               | Artifact                                                               | Status                 |
| ------------------------------------- | ---------------------------------------------------------------------- | ---------------------- |
| Product thesis                        | [docs/charter.md](docs/charter.md)                                     | v0.1                   |
| System design                         | [docs/architecture.md](docs/architecture.md)                           | v0.1                   |
| Business case                         | [docs/roi-model.md](docs/roi-model.md)                                 | v0 with 2D sensitivity |
| Product requirements                  | [docs/prd.md](docs/prd.md)                                             | v1                     |
| **Practice performance memo**         | [docs/practice-performance-memo.md](docs/practice-performance-memo.md) | **Week 4 shipped**     |
| **Governance reference architecture** | [docs/governance.md](docs/governance.md)                               | **Week 4 shipped**     |
| Decision log                          | [docs/decision-log.md](docs/decision-log.md)                           | Running                |
| Roadmap V1/V2/V3                      | [docs/roadmap.md](docs/roadmap.md)                                     | v1                     |
| Refinement plan (V1→V4)               | [docs/refinement-plan.md](docs/refinement-plan.md)                     | living — Tracks A–F    |
| Dashboards (SQL)                      | [dashboards/](dashboards/)                                             | 8 queries              |
| Demo script                           | [docs/demo-script.md](docs/demo-script.md)                             | 2-min + 5-min cuts     |
| Model card                            | [docs/model-card.md](docs/model-card.md)                               | v1                     |

## Build plan (4 weeks)

| Week | Focus                          | Status                                                                                                                                                                                                 |
| ---- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0    | Scaffold + apply               | **Done**                                                                                                                                                                                               |
| 1    | Hero skeleton                  | **Done** — ingest, silver, rules, LightGBM, ROI                                                                                                                                                        |
| 2    | Evidence + eval                | **Done** — RAG + abstention + calibration + overrides + PRD                                                                                                                                            |
| 3    | Contract economics             | **Done** — 340B/biosimilar/chargeback types, SQL dashboards, roadmap, held-out calibration                                                                                                             |
| 4    | Specialty + access + executive | **Done** — multispecialty coverage, access/PA module, practice performance memo, governance reference architecture                                                                                     |
| 5    | Polish + refinement plan       | **Done** — charter v1, decision log catch-up, model card, LLM paraphrase layer (flag-gated), CI, per-specialty eval slicing, CV calibration, Streamlit reviewer UI, demo script, V1→V4 refinement plan |

## Stack

- **Databricks on Azure (target runtime)** — Unity Catalog, Delta, MLflow, Mosaic AI / Azure OpenAI (v2 LLM layer), Databricks Asset Bundles, SQL Warehouse
- **Python 3.11+** — polars, LightGBM, MLflow, sentence-transformers, scikit-learn (IsotonicRegression), matplotlib, click
- **Data sources (public, real)** — CMS ASP Part B, CMS NDC-HCPCS crosswalk, HRSA OPAIS (340B scenario), SEC EDGAR exhibits (contract patterns); payer PA workflow patterned on commercial specialty policy
- **Synthetic layer** — 5k claims across 14 HCPCS, 5 specialties, 4 payer archetypes, 20 practices; drug prices anchored to real ASP

## Evaluation philosophy

Business-outcome metrics, not vanity model metrics. See [docs/prd.md](docs/prd.md) for the full rubric. Headline: **precision@top-k**, **dollars-at-risk per reviewer hour**, **calibration**, **citation precision**, **abstention rate**, **override rate + rationale distribution**, **payback sensitivity**.

## Scope boundaries

**In scope:** specialty-care revenue integrity, access / PA exception intelligence, contract economics (GPO / chargeback / ASP / biosimilar / 340B scenario), per-practice performance analysis, controllership-ready governance.

**Out of scope:** PHI handling (synthetic only), clinical decision support, prior-auth auto-submission, appeal-letter auto-send, production HIPAA compliance claim, real-time payer integration.

## License

MIT. Use freely. Attribution appreciated.
