# om-finance-ai

**Purpose:** O&M Finance AI Control Tower — finance operating layer for McKesson's Oncology & Multispecialty ecosystem. Five capability modules (revenue integrity queue, access/PA intelligence, specialty drug economics, practice performance, governance + audit) on one Databricks-native pipeline. Portfolio artifact for Lead TPM Finance AI (McKesson JR0143772).

## Stack

- **Language:** Python 3.11+
- **Package manager:** uv (pyproject.toml)
- **Data:** polars + pyarrow; Parquet locally, Delta-compatible
- **ML:** LightGBM (risk scorer) + sklearn IsotonicRegression (5-fold CV calibration) + MLflow (tracking, registry)
- **RAG:** sentence-transformers + sklearn cosine; template-based explainer with strict citation enforcement and abstention; optional Ollama paraphrase layer (flag-gated, post-generation citation verifier)
- **Governance:** append-only Parquet override log; Unity Catalog + MLflow lineage in production
- **Eval:** business-outcome harness (precision@k, $/reviewer-hour, calibration, citation precision, abstention, override distribution)
- **UI:** Streamlit reviewer-queue mock (`make reviewer-ui`)
- **CLI:** click
- **Target runtime:** Databricks on Azure (Unity Catalog + Delta + MLflow + Mosaic AI / Azure OpenAI for the V2 LLM layer); runs locally for dev

## Setup

```bash
make install        # uv sync --all-extras (arm64 venv on Apple Silicon)
make demo           # end-to-end pipeline, ~12s after first model download
uv run oai-finance practice-analysis  # per-practice + 100-day initiative model
make reviewer-ui    # Streamlit reviewer queue
make mlflow-ui      # browse model runs at http://127.0.0.1:5000
make test           # smoke test
make clean          # wipe data/ artifacts/ mlruns/
```

## Conventions

- **All data under `data/`** is reproducible: bronze/silver/gold rebuild from samples or live fetch. Never commit `data/bronze`, `data/silver`, `data/gold`, `data/synthetic` — `make clean` wipes them.
- **Sample data in `data/samples/`** is committed — hand-curated representative snippets of CMS ASP + NDC-HCPCS, plus 5 payer policies and 3 GPO contracts.
- **Real CMS data is public** but fetched on demand. The `--live` flag in ingest is currently a stub (refinement plan A6); samples are the demo default.
- **No PHI. No proprietary contracts. No real patient-level claims.** Synthetic claims anchored to real ASP prices.
- **Business-outcome eval only** in public artifacts. AUC is logged internally to MLflow for debugging but is never the headline metric.
- **"Controllership-ready"** not "auditor-defensible" in any copy facing reviewers (decision DL-0006).
- **340B is a scenario module, never a headline.** Policy-volatile framing enforced in charter (decision DL-0002).
- **LLM paraphrase is feature-flagged off by default** with a strict post-generation citation verifier; the deterministic template explainer remains the auditability-critical path.

## Pipeline stages

1. **Bronze** — CMS ASP + NDC-HCPCS crosswalk + 5 payer policies + 3 GPO contracts + commercial PA workflow doc → Parquet
2. **Bronze** — synthetic oncology + multispecialty claims generator with latent `is_true_error` state observed noisily by rules
3. **Silver** — `drug_economics` + `claim_lines` with ASP ratios, NDC validity, specialty + 340B + PA flags
4. **Gold** — exception candidates across 10 priority-ordered types (`access_pa_gap`, `jw_drug_waste`, `gpo_340b_rebate_excluded`, `chargeback_validity_fail`, `biosimilar_conversion_miss`, `site_of_care_underpayment`, `ndc_hcpcs_mismatch`, `asp_drift`, `underpayment`, `denial`)
5. **Gold** — LightGBM risk scorer + MLflow run + gain-based feature importance
6. **Gold** — 5-fold cross-validated isotonic calibration → `risk_score_calibrated` and `expected_recovery_calibrated`
7. **RAG** — retrieval + citation-enforced template explainer with abstention at similarity < 0.64
   7b. **RAG (optional)** — Ollama paraphrase with post-generation citation verification; falls back to template on verifier failure or unreachable endpoint
8. **Governance** — append-only override log over the top-100 queue
9. **Eval** — three rankings + rules-only baseline + citation precision + abstention rate + per-specialty slicing + calibration overlay

Outputs: `artifacts/eval_report.md`, `eval_report.json`, `calibration.png`, `capture_curves.png`, `practice_performance.json`; `data/gold/{exception_candidates,scored_exceptions,explained_exceptions,override_log,practice_performance}.parquet`; MLflow runs at `mlruns/`.

## Doc surfaces

- `docs/charter.md` — V1 product charter with JD crosswalk
- `docs/architecture.md` — medallion + governance reference architecture (Mermaid)
- `docs/roi-model.md` — ROI base case + 2D sensitivity
- `docs/prd.md` — V1 PRD with JD crosswalk
- `docs/governance.md` — HIPAA + SOX reference architecture
- `docs/practice-performance-memo.md` — executive memo with real computed numbers
- `docs/decision-log.md` — DL-0001..0014 design decisions
- `docs/roadmap.md` — V1 / V2 / V3 / V4 phased plan
- `docs/refinement-plan.md` — living plan with Tracks A–F, owner-driven
- `docs/model-card.md` — `rev_integrity.risk_scorer` model card
- `docs/demo-script.md` — 2-minute Loom storyboard + 5-minute extended cut

## Non-goals

- PHI handling (synthetic only)
- Automated appeal submission, prior-auth submission, or chargeback filing
- Real-time payer adjudication integration
- Clinical decision support
- Production HIPAA compliance claim (design documented; claim is not made)
- Standalone chatbot UX (reviewer UI embeds where reviewers work)

## Credentials

No credentials required for the sample-data pipeline. Optional Ollama paraphrase layer reads `OAI_ENABLE_LLM_PARAPHRASE`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` from env — see `.env.example`. `.env` is gitignored.
