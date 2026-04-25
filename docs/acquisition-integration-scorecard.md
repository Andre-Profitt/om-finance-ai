# Practice Acquisition Integration Scorecard

**Use:** evaluate a target practice (acquisition, de novo, or in-network underperformer) for Control Tower onboarding readiness. Score each row as **Green / Amber / Red** with a one-line rationale. Only practices that score Green on Data + Workflow + Governance can begin V2 pilot.

This scorecard directly supports McKesson O&M's Q3 FY26 growth thesis (provider solutions + specialty distribution + acquisitions, +37% revenue / +57% segment operating profit) — the question this artifact answers is _which acquired practices are ready to operationalize Finance AI on day one, vs. which need 90 days of foundation work first_.

---

## 1. Data readiness

| Row                          | Question                                    | Green                           | Amber                         | Red                       |
| ---------------------------- | ------------------------------------------- | ------------------------------- | ----------------------------- | ------------------------- |
| Claims feed                  | Where does the claim line data come from?   | Real-time API to billing system | Daily batch export            | Manual CSV / no feed      |
| Remittance feed              | 835/EOB ingest path                         | API + CARC/RARC parsed          | Batch + manual reconciliation | None                      |
| Payer contract corpus        | Are contracts digitized + searchable?       | Yes, all top-10 payers          | Top-3 payers only             | Paper / scanned PDFs only |
| GPO roster + chargeback feed | Onmark or equivalent integration            | Live feed + reconciled          | Periodic exports              | None                      |
| Drug purchasing + inventory  | Buy-and-bill data flowing                   | API to specialty distributor    | Periodic                      | Manual                    |
| EHR / PM connection          | iKnowMed / Epic / Cerner / Meditech         | API in place                    | Manual export                 | Air-gapped                |
| 340B status                  | Documented eligibility + ceiling-price feed | Yes                             | Partially                     | Unknown / disputed        |

## 2. Workflow readiness

| Row              | Question                                     | Green                                 | Amber                   | Red                   |
| ---------------- | -------------------------------------------- | ------------------------------------- | ----------------------- | --------------------- |
| Reviewer pool    | Who works the queue?                         | Dedicated AR analyst(s)               | Shared with billing ops | No-one designated     |
| Queue location   | Where does the reviewer log in?              | Embedded panel in current workstation | Standalone dashboard    | "We'll figure it out" |
| Disposition SLA  | Time from flag to action                     | Documented < 48h SLA                  | Informal 1-week target  | No SLA                |
| Appeals workflow | First-level appeal process                   | Documented + training                 | Informal                | No process            |
| PA workflow      | CoverMyMeds / equivalent in use              | Yes, integrated                       | Yes, separate           | Manual phone/fax      |
| Coding team      | Coder available for NDC / J-code corrections | Yes, dedicated                        | Shared                  | None                  |
| Contracts team   | Reconsideration filing capacity              | Yes                                   | Sometimes               | No                    |

## 3. Finance readiness

| Row                                       | Question                                 | Green                  | Amber          | Red         |
| ----------------------------------------- | ---------------------------------------- | ---------------------- | -------------- | ----------- |
| Baseline leakage measurement              | Do they know their current leakage rate? | Yes, by exception type | Aggregate only | No          |
| AR aging                                  | Trended monthly                          | Yes                    | Quarterly      | Annual      |
| Chargeback lag                            | Tracked                                  | Yes                    | Sometimes      | No          |
| Working-capital reporting                 | Days to cash by drug class               | Yes                    | Aggregate      | No          |
| Reserve treatment for AI-assisted entries | Documented accounting policy             | Yes                    | In process     | No          |
| Practice CFO sponsor                      | Named, engaged, committed to pilot       | Yes                    | Aware          | Not engaged |

## 4. Governance readiness

| Row                      | Question                                                | Green               | Amber                | Red         |
| ------------------------ | ------------------------------------------------------- | ------------------- | -------------------- | ----------- |
| HIPAA BAA in force       | Practice → McKesson + downstream sub-processors         | Yes                 | In process           | No          |
| DUA scope                | Permitted use covers AI scoring                         | Yes                 | Renegotiation needed | No          |
| Privacy office           | Engaged + signed off                                    | Yes                 | Aware                | Not engaged |
| Override-log retention   | 7-year append-only configured                           | Yes                 | In process           | No          |
| Reviewer access controls | Practice-scoped RLS in place                            | Yes (Unity Catalog) | Coarse-grained       | None        |
| SOX scoping              | AI-assisted finance entries scoped + control documented | Yes                 | In process           | No          |
| Internal audit           | Aware of AI-assisted entries                            | Yes                 | Aware                | Not engaged |

## 5. Value-capture readiness

What's possible in the first 100 days vs. what waits until post-integration.

### Days 1–30 (high-confidence; depends on data + workflow Green)

- Revenue Integrity Queue (V1) on retrospective claims for the practice
- Top-100 review cycle established
- Override log + reviewer agreement KPIs measurable
- Citation-grounded explanations live for the practice's payer mix

### Days 31–60 (depends on contract / GPO data)

- Specialty Drug Contract Economics module against this practice's GPO roster
- Chargeback validation reconciliation
- 340B scenario review (if eligible)

### Days 61–100 (depends on inventory feed)

- JW drug-waste exception type
- Biosimilar conversion program tracking
- Site-of-care optimization scenarios

### Post-integration (months 4+; needs full workflow integration)

- Pre-bill PA propensity scoring
- Appeal-letter draft assistance
- Multi-practice benchmarking against this practice's peer set
- Acquisition financial-impact model fed back into M&A diligence

## 6. Composite score

Sum the rows: count Green = 2pt, Amber = 1pt, Red = 0pt.

| Range          | Recommendation                                                                                                 |
| -------------- | -------------------------------------------------------------------------------------------------------------- |
| 38–50 (max 50) | Greenlight V2 pilot. Begin within 2 weeks.                                                                     |
| 25–37          | Conditional. Identify the 3 lowest rows; remediate; re-score in 4 weeks.                                       |
| 0–24           | Not ready. Defer V2; spend 60 days on foundation work (data feeds, workflow, governance) before re-evaluating. |

## 7. How this scorecard saves money

- **Avoids stalled pilots.** Practices in the 0–24 band that try to pilot Control Tower will fail not because the model is bad but because the data feeds aren't there. Better to spend 60 days laying foundation than 90 days wondering why nothing recovered.
- **Sequences the rollout right.** A 250-practice network can't onboard everyone at once. The scorecard becomes the prioritization signal.
- **Surfaces foundation gaps as M&A diligence findings.** A practice scoring Red on "claims feed" or "DUA scope" is identifying capital expenditure that needs to happen post-acquisition. That's a real input to deal economics.
- **Connects to FCS-style integration playbook.** McKesson's $2.49B FCS acquisition (US Oncology Q3 FY26 release) is the template; this scorecard is the row-level checklist.

## 8. What to do with the result

The completed scorecard becomes:

- A row in `data/gold/practice_performance.parquet` (V2 — adds `acquisition_readiness_score` to the per-practice frame)
- An exhibit in the practice-onboarding memo
- A trigger for the V2 ingest gate — failed scorecard → no DUA paper signed → no V2 ingest

Filed under `docs/private/practice-onboarding/<practice_id>-scorecard-<YYYY-MM>.md` (gitignored — practice-specific data).
