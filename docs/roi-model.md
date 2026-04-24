# ROI Model — Revenue Integrity Control Tower

**Version:** 0 (input assumptions, methodology, and sensitivity table — pre-build calibration)
**Last updated:** 2026-04-24

---

## Purpose

Provide a defensible, inspectable ROI model for the Control Tower before a single line of production code runs. This is the artifact that answers *"what would we measure if this were live, and what's the break-even?"* — the question a controllership or FP&A leader will ask on page one.

## Unit of analysis

A single mid-size community oncology practice, annualized. Results scale linearly to network level with modest efficiency bonuses (shared reviewer pool, shared model).

## Input assumptions (v0, all modifiable)

| Input | Base value | Source / reasoning |
|---|---|---|
| Annual claim volume (practice) | 120,000 lines | Mid-size practice: ~6–8 medical oncologists × ~20 claim lines per encounter per week × 48 weeks |
| Average claim-line billed amount | $2,800 | Weighted blend of J-code buy-and-bill ($3,500 avg) + E&M ($150) + ancillary + imaging |
| Preventable leakage rate (denials + underpayments + chargeback + ASP variance) | 3.0% of billed | Industry range 2–5%; use 3% as conservative midpoint |
| Gross annual preventable leakage | **$10.08M** | 120,000 × $2,800 × 3.0% |
| Tool prevention lift on addressable leakage | 25% | Conservative; denial-prevention literature cites 30–50% with assisted appeals; scale down for synthetic-data prudence |
| Addressable share of leakage (reachable by the work queue vs. inherent denials) | 60% | Not everything flagged is recoverable; 60% is the design target for top-k coverage |
| Reviewer capacity | 1 FTE @ 1,800 productive hours | One dedicated analyst |
| Reviewer review throughput | 12 items / hour | 5 min per item average; calibration-dependent |
| Reviewer fully loaded cost | $75K / year | Community oncology billing analyst range |
| Reviewer cost per item | $3.47 | $75K / (1,800 × 12) |
| Tool annual cost (modeled) | $120K | Platform + model serving + maintenance; conservative |

## Outputs (base case)

| Output | Value | Formula |
|---|---|---|
| Reachable preventable leakage $ | $6.05M | $10.08M × 60% |
| Prevented leakage (value captured) | **$1.51M** | $6.05M × 25% |
| Reviewer cost at full capacity | $75K | reviewer FTE |
| Tool cost | $120K | modeled |
| Net annual value | **$1.31M** | $1.51M − $75K − $120K |
| Payback period | **1.5 months** | (tool + reviewer) / (prevented leakage / 12) |
| ROI Year 1 | **6.7×** | Net / (tool + reviewer) |

## Sensitivity table

Two-dimensional sensitivity on the two largest-impact drivers: prevention lift and addressable-share-of-leakage. Cell values = net annual value ($M).

| Prevention lift ↓ \\ Addressable % → | 40% | 50% | 60% | 70% | 80% |
|---|---|---|---|---|---|
| 15% | 0.41 | 0.56 | 0.71 | 0.86 | 1.01 |
| 20% | 0.61 | 0.81 | 1.01 | 1.21 | 1.41 |
| **25%** | **0.81** | **1.06** | **1.31** | **1.56** | **1.81** |
| 30% | 1.01 | 1.31 | 1.61 | 1.91 | 2.21 |
| 35% | 1.21 | 1.56 | 1.91 | 2.26 | 2.61 |

*Even at worst-case (15% lift × 40% addressable), the tool is net positive at $0.41M/year. The break-even floor on prevention lift is ~5% at base assumptions.*

## Sensitivity on reviewer capacity

Adding reviewers scales captured value linearly until the top-k queue is exhausted. At the base case, top-k queue saturation occurs around 2.2 FTE reviewers. Beyond that, marginal return drops sharply — the TPM call is *do not over-staff; invest the second-FTE dollars in expanding the model's addressable surface (more exception types, better RAG evidence coverage) instead*.

| Reviewer FTE | Gross captured | Reviewer cost | Net value | Marginal $ per added FTE |
|---|---|---|---|---|
| 0.5 | $0.76M | $37.5K | $0.60M | — |
| 1.0 | $1.51M | $75K | $1.31M | +$0.71M |
| 1.5 | $2.11M | $112.5K | $1.88M | +$0.57M |
| 2.0 | $2.42M | $150K | $2.15M | +$0.27M |
| 2.5 | $2.52M | $187.5K | $2.21M | +$0.06M |

## What this model deliberately does NOT claim

- It does **not** claim the 25% prevention lift is empirically validated on production data; this is a modeled design target for the v1 eval harness to test.
- It does **not** claim the 3% preventable-leakage rate holds uniformly across practices; the range is 2–5% and a production deployment would calibrate per-practice.
- It does **not** include second-order benefits (faster close, reduced rework on rebate accruals, M&A diligence acceleration) that are real but harder to size.
- It does **not** model risk-adjusted net value for override-rate miscalibration or false-positive reviewer burn; that is a v1 eval output feeding a v2 model refresh.

## What the v1 eval harness will replace in this model

| v0 assumption | v1 eval-harness replacement |
|---|---|
| 25% prevention lift (modeled) | Measured lift vs. unassisted baseline on held-out synthetic |
| 60% addressable share | Measured from top-k coverage curve |
| $3.47/item reviewer cost | Measured from review-time simulation + item-complexity features |
| 1.5-month payback | Recomputed from measured lift and cost |

## Using this for a practice-network ROI roll-up (Week 4 memo)

At network scale (modeled: 250-practice equivalent), the base-case net annual value ≈ $300M+ before efficiency bonuses from shared reviewer capacity and shared model maintenance. This is the number that goes into the Practice Acquisition & Performance Model executive memo, with appropriate caveats for practice heterogeneity, payer mix, and regional variation.

## References

- CMS ASP Part B pricing files (drug economics anchor)
- Industry literature on oncology revenue cycle leakage rates (2–5% range)
- Healthcare Financial Management Association (HFMA) revenue cycle benchmarks
- Note: all figures in this document are modeled illustrations; not audited actuals
