# O&M Finance AI — Revenue Integrity Control Tower

**A Databricks-native, controllership-ready AI product prototype for oncology-practice revenue integrity: claims leakage prioritization, evidence-grounded exception explanation, contract/chargeback economics, and practice-acquisition finance.**

> The finance-side operating layer above existing O&M practice-facing tools (claims acceptance, GPO savings, regimen and practice analytics, oncology EHR) — focused on ROI sizing, exception prioritization, model evaluation, auditability, and adoption metrics.

**Status:** Week 2 complete — working end-to-end pipeline with isotonic-calibrated risk scoring, evidence-grounded RAG explainer with honest abstention, simulated override log, and a business-outcome eval harness.

**Author:** Andre Profitt · [LinkedIn](https://www.linkedin.com/in/andreprofitt) · built as a public Lead-TPM-Finance-AI portfolio artifact.

**Not affiliated with any healthcare distributor, GPO, or EHR vendor. No PHI. All claims data is synthetic; drug prices anchored to public CMS ASP Part B files.**

---

## Run it yourself

```bash
git clone https://github.com/Andre-Profitt/om-finance-ai
cd om-finance-ai
make install      # uv sync --all-extras
make demo         # end-to-end pipeline, ~8s after first model download
make mlflow-ui    # browse model runs
make test         # smoke test
```

The `make demo` command produces `artifacts/eval_report.md`, calibration and capture-curve PNGs, an MLflow-registered LightGBM model, isotonic-calibrated scores, evidence-grounded per-exception explanations, and a simulated override log.

## What the pipeline does

Nine stages, all Databricks-native (Delta tables, Unity Catalog-ready schemas, MLflow tracking). Runs locally on Parquet today; the same code deploys to Databricks on Azure without architectural change.

1. **Bronze — CMS ingest.** Real CMS ASP Part B payment rates + NDC-HCPCS crosswalk (sample snapshot committed; production path fetches live quarterly).
2. **Bronze — synthetic claims.** 5,000 oncology claims across 10 J-codes and four payer archetypes, with a **latent `is_true_error` state** that rules observe _noisily_ (no label leakage).
3. **Silver — drug economics + claim lines.** ASP-per-mg, billed-to-ASP ratio, NDC-HCPCS validity, paid-to-allowed ratio.
4. **Gold — rule-based exception candidates.** Deterministic triggers for ASP drift, NDC mismatch, denial, underpayment.
5. **Gold — LightGBM risk scoring + MLflow.** Gradient-boosted risk model on 16 features, tracked + registered with gain-based feature importance as the v1 explainer.
6. **Gold — isotonic calibration.** Monotonic correction of the raw risk score; the reviewer queue ranks on the calibrated score.
7. **RAG — evidence-grounded explanation.** Dense retrieval (MiniLM) over a corpus of four payer policies and three GPO contracts; every explanation quotes a specific §section with a citation, **or abstains** when no chunk clears the similarity threshold.
8. **Governance — override log.** Simulated reviewer decisions on the top-100 queue, append-only Parquet, reviewer agreement tracked.
9. **Eval — business-outcome report.** Three rankings, rules-only baseline, citation precision, abstention rate, calibration comparison.

## Headline results (5,000 synthetic claims, seed 20260424)

**Ranking strategy matters more than model quality.** Three rankings of the same 695 exception candidates:

| Metric                          | P(leakage) | expected recovery | **expected recovery (calibrated)** |
| ------------------------------- | ---------- | ----------------- | ---------------------------------- |
| Precision@100                   | 100.0%     | 81.0%             | **93.0%**                          |
| Dollars captured @ top-100      | $786,674   | $1,768,531        | **$1,882,249**                     |
| Dollars per reviewer-hour @ 100 | $94,401/h  | $212,224/h        | **$225,870/h**                     |

vs. rules-only baseline of $3.77M captured across 57.9 reviewer-hours, the model + calibrated recovery ranking captures **50% of max leakage at 14% of the reviewer effort**.

**Evidence grounding:**

- Citation precision on explained exceptions: **100%**
- Abstention rate: **25.5%** — the system refuses to cite when retrieval similarity falls below 0.64
- Override agreement (top-100 simulated reviewer decisions): **80%**

**Model diagnostics:**

- LightGBM valid AUC: 0.907
- Calibration slope uncalibrated: 1.78 → isotonic: **1.00** (target 0.9–1.1)

## Sample explanation (auditable output)

```
Claim CLM-002720 billed HCPCS J9228 with NDC 50242-060-01, which is not in
the CMS NDC-HCPCS crosswalk for J9228. Per Medicare LCD L00000 — Oncology
Intravenous Biologic Agents §NDC-HCPCS Mapping Requirements: "Every claim for
a drug billed under an HCPCS J-code MUST include a corresponding National
Drug Code (NDC) from the CMS NDC-HCPCS crosswalk for that J-code and
effective date. Submission of a valid HCPCS code with an NDC that is not
listed in the crosswalk for that HCPCS will result in denial with Claim
Adjustment Reason Code CO-16 …" Expected outcome: medicaid_managed will deny
with CO-16. Action: resubmit corrected claim with a crosswalk-valid NDC or
escalate to coding.
```

Calibrated risk score: 0.957 · Dollars at risk: $46,652 · Citation similarity: 0.735

**Sample abstention (also auditable):**

```
No policy or contract clause in the current corpus exceeded the similarity
threshold (0.64); best candidate was commercial_regional_prior_auth_oncology
§Prior Authorization Required at similarity 0.62. Routing to human reviewer
without a model-generated explanation.
```

## What's in here

| Surface              | Artifact                                     | Status                 |
| -------------------- | -------------------------------------------- | ---------------------- |
| Product thesis       | [docs/charter.md](docs/charter.md)           | v0.1                   |
| System design        | [docs/architecture.md](docs/architecture.md) | v0.1                   |
| Business case        | [docs/roi-model.md](docs/roi-model.md)       | v0 with 2D sensitivity |
| Product requirements | [docs/prd.md](docs/prd.md)                   | v1                     |
| Decision log         | [docs/decision-log.md](docs/decision-log.md) | Running                |
| Governance design    | docs/governance.md                           | Week 4                 |
| Roadmap V1/V2/V3     | docs/roadmap.md                              | Week 3                 |

## Build plan (4 weeks)

| Week | Focus              | Status                                                                                   |
| ---- | ------------------ | ---------------------------------------------------------------------------------------- |
| 0    | Apply + scaffold   | **Done** — landing page, charter, architecture, ROI                                      |
| 1    | Hero skeleton      | **Done** — ingest, silver, rules, LightGBM + MLflow, ROI v1                              |
| 2    | Evidence + eval    | **Done** — RAG + abstention + calibration + overrides + PRD                              |
| 3    | Contract economics | GPO/chargeback/ASP variance module, 340B scenario, leakage dashboard, roadmap            |
| 4    | Executive artifact | Practice Acquisition & Performance Model memo, governance reference architecture, polish |

## Stack

- **Databricks on Azure (target runtime)** — Unity Catalog (governance + lineage), Delta Lake (bronze/silver/gold), MLflow (experiments + registered models), Mosaic AI / Azure OpenAI (RAG), Databricks Asset Bundles (IaC), SQL Warehouse (dashboards)
- **Python 3.11+** — polars + pyarrow; LightGBM + MLflow; sentence-transformers + sklearn cosine similarity for retrieval; scikit-learn IsotonicRegression for calibration; matplotlib for plots; click for the CLI
- **Data sources (public, real)** — CMS ASP Part B quarterly pricing files; CMS NDC-HCPCS crosswalk; HRSA OPAIS (340B scenario only); SEC EDGAR exhibits (for contract-term patterns)
- **Synthetic layer** — 5k oncology claims across top-10 J-codes and four payer archetypes, anchored to real ASP prices

## Evaluation philosophy

Business-outcome metrics, not vanity model metrics:

- **Precision@top-k** on the reviewer work queue (not AUC as the headline)
- **Dollars-at-risk captured per reviewer hour**
- **Calibration** (actual vs. predicted leakage by decile)
- **Citation precision** on RAG explanations
- **Abstention rate** (model refuses to score when evidence is weak)
- **Override rate + rationale distribution** (simulated in v2; wired for reviewers in v3)
- **Payback-period sensitivity** (±20% on prevention lift × ±20% on reviewer capacity)

See [docs/roi-model.md](docs/roi-model.md) for the sensitivity tables.

## Scope boundaries

**In scope:** oncology-practice revenue-cycle leakage prioritization, evidence-grounded exception explanation with citation enforcement and abstention, GPO / chargeback / ASP-variance exception module, 340B scenario module (governance-first framing), practice-acquisition finance memo.

**Out of scope:** PHI handling (synthetic only), clinical decision support, prior-auth submission automation, appeal letter auto-send, production HIPAA compliance, payer-specific API integrations, real-time claim adjudication.

## License

MIT. Use freely. Attribution appreciated.
