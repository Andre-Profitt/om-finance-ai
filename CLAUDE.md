# om-finance-ai

**Purpose:** O&M Finance Revenue Integrity Control Tower — Databricks-native governed AI for oncology-practice revenue leakage prioritization. Portfolio artifact for Lead TPM Finance AI (McKesson JR0143772).

## Stack

- **Language:** Python 3.11+
- **Package manager:** uv (pyproject.toml)
- **Data:** polars + pyarrow; Parquet locally, Delta-compatible
- **ML:** LightGBM (risk scorer) + MLflow (tracking, registry)
- **Eval:** custom harness (precision@k, $-at-risk/reviewer-hour, calibration)
- **RAG (Week 2):** sentence-transformers + faiss-cpu (optional extra)
- **CLI:** click
- **Target runtime:** Databricks on Azure (Unity Catalog + Delta + MLflow); runs locally for dev

## Setup

```bash
make install    # uv sync
make demo       # end-to-end pipeline
make mlflow-ui  # browse runs at http://127.0.0.1:5000
make test       # smoke test
make clean      # wipe data/ artifacts/ mlruns/
```

## Conventions

- **All data under `data/`** is reproducible: bronze/silver/gold rebuild from samples or live fetch. Never commit `data/bronze`, `data/silver`, `data/gold`, `data/synthetic` — `make clean` wipes them.
- **Sample data in `data/samples/`** is committed — hand-curated representative snippets of CMS ASP + NDC-HCPCS.
- **Real CMS data is public** but fetched on demand (`--live` flag in ingest, not implemented in v0; samples are the demo default).
- **No PHI. No proprietary contracts. No real patient-level claims.** Synthetic claims anchored to real ASP prices.
- **Business-outcome eval only** in public artifacts. AUC is logged internally to MLflow for debugging but is never the headline metric.
- **"Controllership-ready"** not "auditor-defensible" in any copy facing reviewers.
- **340B is a scenario module, never a headline.** Policy-volatile framing enforced in charter.

## Pipeline stages

1. **Bronze** — CMS ASP + NDC-HCPCS crosswalk ingest to Parquet
2. **Bronze** — synthetic oncology claims generator (anchors to real ASP)
3. **Silver** — `drug_economics` + `claim_lines` with ASP ratios, NDC validity
4. **Gold** — `exception_candidates` (deterministic rules: ASP drift, NDC mismatch, denial, underpayment)
5. **Gold** — `scored_exceptions` (LightGBM risk score + MLflow run + feature importance)
6. **Eval** — `artifacts/eval_report.{md,json}`, `calibration.png`, `top_k_curve.png`

## Non-goals

- PHI handling (synthetic only)
- Automated appeal submission or prior-auth submission
- Real-time adjudication integration
- Clinical decision support
- Production HIPAA compliance claim (design documented; claim is not made)

## v1 → v2 roadmap

- v1 (this repo, Week 1–2): rule-based triggers + LightGBM scoring + native feature importance + eval harness
- v2 (Week 2): RAG citation layer over payer policies + mock GPO contracts; abstention on weak evidence
- v3 (Week 3): Contract Economics module — GPO/chargeback/ASP variance; 340B scenario; leakage dashboard
- v4 (Week 4): Practice Acquisition & Performance Model memo; governance reference architecture

## Credentials

No credentials required for the sample-data pipeline. If/when RAG uses Azure OpenAI, add keys to `.env` (see `.env.example`); `.env` is gitignored.
