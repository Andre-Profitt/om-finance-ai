# Practice Performance & Acquisition Finance Model

**Executive memo**
**Prepared by:** O&M Finance AI Control Tower — practice-analytics module
**Date:** 2026-04-24
**For:** VP, O&M Finance Transformation / US Oncology Network CFO
**All numbers below are produced by `oaifinance.practice.performance` on synthetic data anchored to public CMS ASP; figures illustrate the model, not live practice economics.**

---

## 1. Executive summary

McKesson's O&M segment — US Oncology Network, community oncology practices, Ontada, Biologics, CoverMyMeds, and multispecialty providers across retinal, rheumatology, gastroenterology, and neurology — is the fastest-growing revenue + operating-profit unit on the portfolio. The Q3 FY26 release reported O&M revenue up 37% and segment operating profit up 57%, driven by provider solutions, specialty distribution, and acquisitions including the ~$2.49B controlling-interest buy of the Core Ventures business services organization supporting Florida Cancer Specialists (FCS).

Acquiring or onboarding a practice is not a one-time event — it is a 100-day integration sprint followed by ongoing performance management across revenue integrity, access, specialty drug economics, and multispecialty mix. This memo proposes a **Finance AI Control Tower** as the operating layer for that sprint, demonstrated here on a simulated 20-practice network spanning oncology + multispecialty.

**Network state (simulated 20 practices, 5,000 claims, Q1 2026):**

- Total dollars at risk surfaced: **$7.17M** across 1,573 exception candidates
- Expected recovery (model-calibrated): **$5.84M**
- Access delay operational cost (prior-auth gaps): **$31.1K**
- Specialty mix by $ exposure: oncology 68%, gastroenterology 19%, neurology 7%, retinal 4%, rheumatology 2%

**Target practice for integration focus (model-selected by highest expected recovery):**

- Practice `PR-012` — oncology — non-340B
- 250 claims / 53 exceptions / 21% exception rate
- $626.9K at risk, $543.2K expected recovery
- Top exception types: access PA gap (46%), chargeback validity (23%), denial (19%)

**Projected 100-day integration (`PR-012`):**

- Total recovery: **$322.2K** across five sequenced initiatives
- Reviewer cost: **$292** (7 min × ~40 items × $42/hr effective)
- Net value: **$321.9K**
- Modeled payback on $120K platform cost: **4.5 months**

---

## 2. Why "Specialty Care Operations," not "Oncology Finance"

The O&M business is a connected specialty-care ecosystem: practice management, clinical trials, specialty drug distribution, GPO services, access automation via CoverMyMeds, real-world data via Ontada, and multispecialty care across retina, rheumatology, GI, and neurology. A finance-AI product that reads as "oncology denial classifier" would misrepresent the role. The artifacts in this portfolio — control tower, revenue integrity queue, access intelligence, specialty drug economics, practice performance, governance — generalize across the O&M portfolio because the underlying mechanics (J-code / NDC coding, payer adjudication, contract rebates, site-of-care, prior auth, biosimilar economics) repeat with specialty-specific detail.

The simulated network above confirms it. 32% of the network's dollar exposure sits outside oncology, concentrated in GI (ustekinumab) and neurology (ocrelizumab), where per-administration drug margin is highest. A control tower that only covered oncology would leave that third of exposure unmonitored.

---

## 3. The 100-day integration framework

For any incoming practice (acquisition, de novo, or underperforming in-network), the Control Tower sequences five initiatives in the first 100 days:

### Initiative 1 — Revenue Integrity top-100 quick wins (weeks 1–4)

Target: address addressable denials, underpayments, coding mismatches, and immediate PA gaps on the highest-$ exceptions.
For `PR-012`: $484.5K addressable → $174.4K projected recovery at 80% confidence.

### Initiative 2 — Access / Prior-Auth documentation intake (weeks 2–6)

Target: close the PA documentation loop with CoverMyMeds-style workflow; reduce CO-197 denial re-work.
For `PR-012`: $285.7K addressable (46% of exposure is PA) → $117.8K projected at 75% confidence.

### Initiative 3 — Specialty Drug Contract Economics reconciliation (weeks 5–10)

Target: ASP-variance audit + chargeback validation true-up.
For `PR-012`: $142.4K addressable → $29.9K projected at 60% confidence (lower because ASP variance requires contract-specific remediation).

### Initiative 4 — Biosimilar conversion program (weeks 6–12)

Target: move commercial volume onto payer-preferred biosimilars where available.
For `PR-012`: $0 addressable (this practice's drug mix has no reference-biologic exposure this quarter); would be the largest recovery surface on a different practice mix.

### Initiative 5 — 340B scenario / duplicate-discount governance (weeks 8–14)

Target: compliance-first workflow ensuring 340B-purchased claims are excluded from GPO rebate accrual.
For `PR-012`: $0 addressable (non-340B practice); material on 25% of the network that is 340B.

**Total Q1 net value on `PR-012`: $321.9K against $292 reviewer cost.** At 20 practices the modeled network-level Q1 opportunity exceeds $5.8M based on calibrated expected recovery.

---

## 4. What the Control Tower gives an O&M Finance leader

On day one of onboarding a new practice, the operating cadence is:

1. **Monday morning:** open the reviewer queue for the practice; 53 exceptions ranked by calibrated expected recovery, each with a cited policy clause, color-coded by exception type.
2. **By Friday of week one:** the top 20 have been worked; preliminary recovery dollars + per-decision override rationales are logged. (Specific $ figures land once the practice's actual baseline + reviewer throughput are measured in pilot — V1 estimates from `oaifinance.practice.performance` are scenario projections, not forecasts.)
3. **Week four:** review the calibration-health dashboard; if slope has drifted, schedule refresh. Access-delay dashboard shows PA resolution time against the 14-day SLA.
4. **Week ten:** run the specialty-drug economics module against the quarter's GPO and chargeback submissions; 340B scenario verified.
5. **Week fourteen:** generate the practice performance memo (this document, updated with actuals); surface variance-from-plan to network finance.

Every decision in this cycle is traceable to a model version, a retrieved clause, a reviewer, and a dollar outcome — the artifact trail a CFO or internal auditor needs.

---

## 5. Multispecialty readiness

The Control Tower treats practice specialty as a first-class dimension:

- Claims carry `practice_specialty` and `drug_specialty`
- Risk scoring uses specialty one-hots as model features (equal to payer, dollar magnitude, and exception indicators in importance)
- The corpus includes payer policies that span multispecialty (commercial PA workflow is not specialty-specific), and the retriever matches on the payer + drug + exception-type context
- Dashboards can slice by `practice_specialty` to benchmark oncology vs. retinal vs. rheumatology vs. GI vs. neurology practices

For the acquisition use case this matters because O&M's growth thesis is not "more oncology" — it is more multispecialty practices joining a single operating layer. The Control Tower generalizes because the underlying primitives (payer, drug, rebate, access) repeat across specialty.

---

## 6. AI opportunity backlog

Ranked by value × feasibility × risk × stakeholder readiness for an O&M practice post-integration:

| Opportunity                              | Est. $ / mid-size practice / year | Feasibility                         | Risk                     | Readiness                 |
| ---------------------------------------- | --------------------------------- | ----------------------------------- | ------------------------ | ------------------------- |
| Revenue integrity queue + citation       | $500K–$2M                         | High — shipped in V1                | Low                      | High — finance-owned      |
| Access / PA documentation intake         | $200K–$800K                       | High — CoverMyMeds-adjacent         | Low                      | Medium — access-ops owned |
| Specialty drug contract economics        | $100K–$400K                       | Medium — per-contract variance      | Medium — contract office | Medium                    |
| Biosimilar conversion program            | $50K–$1M (practice-mix dependent) | Medium — formulary coordination     | Low                      | Medium — pharmacy ops     |
| 340B duplicate-discount governance       | $20K–$200K                        | High — rule-based                   | Medium — policy-volatile | Low — compliance-first    |
| Practice FP&A forecasting with narrative | $50K–$150K                        | Medium — needs per-practice history | Low                      | Medium — controller-owned |
| Site-of-care optimization                | $100K–$500K                       | Low — requires payer contracts      | High                     | Low — contract team       |
| Inventory / JW drug-waste capture        | $50K–$300K                        | Medium — needs inventory feed       | Low                      | Medium — pharmacy         |

The Control Tower ships the top-three today. Items four through eight are on the V2/V3 roadmap in `docs/roadmap.md`.

---

## 7. Key risks

1. **Synthetic anchors.** These figures are from a synthetic-claims pipeline anchored to real CMS ASP. Production numbers require retrospective labels from the practice's billing system under a DUA.
2. **Specialty concentration drift.** The 68% oncology / 32% multispecialty mix in the simulated network likely over-represents GI (ustekinumab is a very high-$ drug). Real network mix must be measured, not assumed.
3. **PA policy change.** The access module cites commercial PA workflow language; any payer revising PA rules mid-quarter requires corpus refresh.
4. **Reviewer throughput.** 7-minute-per-item assumption is a planning value; production throughput will be measured and fed back into the model.
5. **Acquisition-specific complexity.** Newly acquired practices often carry legacy billing-system quirks the Control Tower has not seen; first-month over-flagging is expected, and the override log captures the correction.

---

## 8. What's next after this memo

1. Wire the Control Tower into one pilot practice under DUA + privacy/security/legal/controllership approval (V2, 6–8 weeks; IRB review only if research/publication scope is added — this is finance-ops AI, default path is QI, not human-subjects research)
2. Productionize calibration with a 20% held-out refresh weekly
3. Publish the model card + governance ref architecture to the controllership team
4. Expand the payer-policy corpus to the practice's actual top-five payers by volume
5. Schedule a 30-day retrospective on override rationale distribution to tune the top-100 queue

The artifact in this repo — running pipeline, eval report, decision log, governance doc, roadmap, per-practice P&L — is the working prototype of the above. A decision to proceed on a single-practice pilot is the next gate.
