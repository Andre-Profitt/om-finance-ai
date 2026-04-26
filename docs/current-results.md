# Current Results — single source of truth

**This file is authoritative.** Every other doc that quotes a metric should defer to this run. If you see a different number elsewhere in the repo, that doc is stale; this file wins.

**Run:** `make demo` end-to-end · **Seed:** `20260424` · **Refreshed:** 2026-04-25

## Pipeline scope

| Surface                      | Count                                                            |
| ---------------------------- | ---------------------------------------------------------------- |
| Total claims processed       | 5,000                                                            |
| Exception candidates flagged | 2,722                                                            |
| **Exception types**          | **10**                                                           |
| HCPCS codes                  | 18                                                               |
| Specialties                  | 5 (oncology, retinal, rheumatology, gastroenterology, neurology) |
| Payer policies in corpus     | 10                                                               |
| GPO contracts in corpus      | 6                                                                |
| SQL query files              | 9 (8 V1 dashboard panels + 1 V2 working-capital / DSO query)     |

**Exception types (priority order):**
`access_pa_gap` · `jw_drug_waste` · `gpo_340b_rebate_excluded` · `chargeback_validity_fail` · `biosimilar_conversion_miss` · `site_of_care_underpayment` · `ndc_hcpcs_mismatch` · `asp_drift` · `underpayment` · `denial`

## Headline metrics

| Metric                           | Value          | Notes                                         |
| -------------------------------- | -------------- | --------------------------------------------- |
| Calibrated precision @ top-100   | **96.0%**      | ranked by expected recovery                   |
| Dollars captured @ top-100       | **$2,323,674** | calibrated ranking                            |
| Citation precision (overall)     | **100.0%**     | golden-map backed                             |
| Abstention rate                  | **15.1%**      | retrieval similarity < 0.64                   |
| Calibration slope — uncalibrated | 1.194          | sample-weighted reliability fit               |
| Calibration slope — isotonic     | **0.985**      | 5-fold CV; target band [0.85, 1.15] · in band |

## Internal model-debug only (not headline)

| Metric             | Value |
| ------------------ | ----- |
| LightGBM valid AUC | 0.934 |

## Limitations of this run

- **Synthetic claims** with drug prices anchored to public CMS ASP. Production pilot replaces synthetic labels with retrospective appeal-outcome / re-adjudication / chargeback-resolution labels via `oaifinance.governance.labels` (V2 schema).
- **Citation precision** is measured against a hand-curated golden map of (doc, section) pairs in `oaifinance.eval.citation`. Production requires multi-rater rubric validation.
- **Reviewer override rate** is simulated; real rate measurable only with reviewers in the loop.
- **Reviewer cost** modeled at 5–7 minutes per item; production throughput must be measured.

## Where the numbers come from

- `artifacts/eval_report.json` — machine-readable
- `artifacts/eval_report.md` — human-readable
- `artifacts/calibration.png` — uncalibrated vs. isotonic reliability diagram
- `artifacts/capture_curves.png` — three-ranking capture curves vs. rules-only baseline

To refresh this file, run `make demo` and copy the headline numbers from `artifacts/eval_report.json`.

## Historical context (pre-polish runs)

Earlier docs reference older runs from before the calibration slope tightening (DL-0015) and before C2/C3/C4/C5 expansion. If you see calibrated slope 1.22, AUC 0.907, or precision@100 of 81% / 93% in any doc, that's a pre-polish snapshot — refer to this file for the current run.
