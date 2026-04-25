# Refinement Plan — V1 → V2 → V3

**Owner:** TPM (Andre)
**Status:** living document — update item status as work ships
**Last updated:** 2026-04-24
**Current state:** V1 shipped (commits `f4d3de1` through `0953622`). Pipeline runs end-to-end on synthetic data anchored to real CMS ASP. Eight exception types across revenue cycle + access + contract economics + multispecialty.

---

## How to use this doc

Six tracks, mostly parallel. Each item has:

- **ID** — stable handle (track-letter + number)
- **Type** — `code` / `doc` / `manual` / `decision`
- **Effort** — order-of-magnitude session count
- **Acceptance bar** — what "done" looks like, measurable
- **Status** — `todo` / `in-progress` / `blocked` / `done` / `dropped`
- **Depends on** — IDs that must ship first

Update status inline. When a track has nothing left in `todo`, archive it.

Stop and re-baseline after every ship. The portfolio must stay demoable at all times — `make demo && make test` green is the invariant.

---

## Track A — V1 Polish (this week)

Tighten the current portfolio. Highest signal-per-hour. All in-session except Loom.

| ID     | Item                                               | Type   | Effort   | Status                                                                 |
| ------ | -------------------------------------------------- | ------ | -------- | ---------------------------------------------------------------------- |
| **A1** | Calibration slope into [0.85, 1.15]                | code   | 1 sess   | **done** (`e4f3287`/`df05368`) — 0.99 calibrated                       |
| **A2** | Per-specialty top-N-per-specialty fairness slice   | code   | 0.5 sess | **done** (`b1592e8`) — equal-effort table in eval report               |
| **A3** | Unit tests for paraphraser citation contract       | code   | 0.5 sess | **done** (`b1592e8`) — 6 tests, citation contract enforced             |
| **A4** | Unit tests for practice performance module         | code   | 0.5 sess | **done** (`b1592e8`) — 6 tests across analyze + initiatives + override |
| **A5** | Streamlit UI: cache + governance page              | code   | 1 sess   | **done** (`00e80d0` W5 multi-page Model Ops + cache)                   |
| **A6** | Live CMS ASP + crosswalk fetch (quarterly scraper) | code   | 1 sess   | **done** — `--live` flag wired with sample fallback on any failure     |
| **A7** | Loom recording                                     | manual | 1 hr     | todo                                                                   |
| **A8** | Resume + LinkedIn rewrite                          | manual | 1 hr     | todo                                                                   |
| **A9** | Repo public visibility flip + apply                | manual | 30 min   | todo                                                                   |

### A1 — Calibration slope into target band ✓

**Shipped 2026-04-25** (commits `e4f3287` + `df05368`). Root cause was the slope _measurement_, not the calibrator: unweighted polyfit through 10 bin centers was dominated by sparse middle bins on the bimodal post-isotonic score distribution. Fix is sample-count-weighted polyfit (sqrt(n)) — one numpy kwarg. Calibrated slope: 1.22 → **0.99**, in the standard reliability-diagram band [0.85, 1.15]. Smoke test invariant tightened from [0.70, 2.00] to [0.80, 1.20]. See DL-0015 for rationale.

### A2 — Per-specialty top-N-per-specialty

Top-100 is 100% oncology because drug magnitudes dominate. Add a second slicing: top-N items per specialty where N = top-100 / number_of_specialties_present. Reports per-specialty precision and dollars on equal-effort slices. Acceptance: eval report shows each specialty represented; per-specialty precision within ±10pp of overall.

### A3 — Paraphraser citation contract tests

The verifier is load-bearing. Tests: (1) valid paraphrase passes; (2) missing citation marker fails; (3) marker present but no clause fragment fails; (4) Ollama unreachable returns `failed_call`; (5) flag off returns `skipped` for all rows. Acceptance: 5+ unit tests for `oaifinance.rag.paraphraser`; CI green.

### A4 — Practice performance module tests

Tests: (1) auto-selection returns the highest-expected-recovery practice; (2) initiative projections are non-negative; (3) addressable dollars match the exception-mix calculation; (4) explicit-target override works; (5) cold-start (`<50` exceptions) practices are excluded from auto-selection. Acceptance: 5+ unit tests for `oaifinance.practice.performance`.

### A5 — Streamlit UI cache + governance page

Add a second page (`pages/02_governance.py`) showing calibration health, override-rate distribution, abstention by exception type, citation-precision-by-type. Cache the per-frame loads with `@st.cache_data(ttl=60)` to avoid re-reads on every interaction. Acceptance: two pages; cache hit visible; runs locally with no errors.

### A6 — Live CMS fetch

Resolve the current-quarter CMS ASP ZIP URL from the CMS landing page; download; parse Excel; write to bronze. Implement in `oaifinance.ingest.cms_asp` behind the existing `--live` flag (currently raises `NotImplementedError`). Acceptance: `oai-finance build --live` succeeds and produces an ASP table with the published-quarter effective date.

### A7 — Loom recording

Use `docs/demo-script.md`. 2-min cut for the cover letter; 5-min cut for the interview loop. Acceptance: two Loom URLs in the README and on LinkedIn.

### A8 — Resume + LinkedIn

Resume headline + 3 bullets per `docs/practice-performance-memo.md`. LinkedIn featured section linked to the repo + Loom. Acceptance: both updated; resume PDF in `docs/private/` (gitignored) for application use.

### A9 — Public + apply

`gh repo edit Andre-Profitt/om-finance-ai --visibility public`; submit via careers.mckesson.com with cover-letter thesis paragraph from the README opening. Acceptance: application reference number captured in personal notes.

---

## Track B — V2 Production Readiness (4–6 weeks, post-application)

Moves from V1 demo to V2 deployable pilot. Sequenced for a single-practice DUA.

| ID     | Item                                          | Type       | Effort | Depends | Status                         |
| ------ | --------------------------------------------- | ---------- | ------ | ------- | ------------------------------ |
| **B1** | Per-payer policy corpus expansion             | doc + code | 1 sess | —       | **done** (`305ea3a`) — 10 docs |
| **B2** | Per-vendor GPO contract expansion             | doc + code | 1 sess | —       | **done** (`305ea3a`) — 6 docs  |
| **B3** | Retrospective label plumbing schema + adapter | code       | 2 sess | —       | todo                           |
| **B4** | Scheduled calibration refresh job             | code       | 1 sess | A1      | todo                           |
| **B5** | Drift / alarm wiring                          | code       | 1 sess | B4      | todo                           |
| **B6** | Unity Catalog RLS pattern + test              | code       | 1 sess | —       | todo                           |
| **B7** | Reviewer UI production deployment path        | code       | 2 sess | A5      | todo                           |
| **B8** | CI hardening (matrix + lint + security scan)  | code       | 1 sess | —       | todo                           |
| **B9** | DUA + IRB language + privacy-office checklist | doc        | 1 sess | —       | todo                           |

### B1 — Per-payer policy corpus expansion

Today: 5 payer policies (Medicare LCD, commercial-national NCCN, commercial-national PA workflow, commercial-regional PA, Medicaid managed). Target: 10+ covering top payer specialties (UHC, Aetna, BCBS plans, Medicare Advantage, state Medicaid programs). Acceptance: corpus has ≥10 documents; citation precision per type does not regress below 0.90.

### B2 — Per-vendor GPO contract expansion

Today: 3 GPO contracts (master rebate, biosimilar conversion, chargeback validation). Target: 5–7 covering specialty distribution, infusion contracts, biosimilar-specific tier addenda. Acceptance: corpus has ≥6 contracts; chargeback / biosimilar exception precision unchanged or better.

### B3 — Retrospective label plumbing

Schema for ingesting real appeal-outcome / re-adjudication / chargeback-resolution labels under DUA. Adapter that maps an Epic / Cerner / Meditech billing-system feed onto our `_true_leakage_amount` ground truth. Acceptance: synthetic adapter tested; documentation of fields + transformation rules; production version requires DUA (B9 blocks).

### B4 — Scheduled calibration refresh

Databricks Asset Bundle job that refits isotonic on a rolling 30-day window of held-out labels and promotes the new calibration only if calibration slope improves vs. current. Acceptance: bundle YAML committed; job runs on demand locally; promotion gate enforced.

### B5 — Drift / alarm wiring

Per `docs/governance.md` §6 thresholds. SQL queries → alert rules → channels. Acceptance: 6 alarm rules wired (calibration, citation precision, abstention, override, coverage, dollar-capture); test fires on a deliberately-broken run.

### B6 — Unity Catalog RLS

Practice-scoped RLS pattern for `claim_lines` and downstream gold tables. Acceptance: documented row filter + practice-scoped service principal; test that a practice-A principal cannot read practice-B rows.

### B7 — Reviewer UI production path

Pick: Databricks App vs. embedded workstation panel. Decide based on stakeholder interview output (gate). Build the chosen path. Acceptance: production-shaped UI deployed in a dev workspace, reading from gold tables.

### B8 — CI hardening

- Python version matrix (3.11 + 3.12)
- Ruff + mypy as gates (currently advisory)
- Bandit / pip-audit security scan
- Coverage report uploaded to artifacts

Acceptance: all gates fail loudly in CI; main protected by passing gates.

### B9 — DUA + IRB language

Templates and a privacy-office checklist for moving to retrospective real labels. Acceptance: documents in `docs/private/` + cross-link from `docs/governance.md` §4 (HIPAA overlay).

---

## Track C — V2 Hero Features (4–6 weeks, parallel with Track B)

New visible capabilities the demo can highlight.

| ID     | Item                                                | Type       | Effort | Depends | Status                                      |
| ------ | --------------------------------------------------- | ---------- | ------ | ------- | ------------------------------------------- |
| **C1** | LLM paraphrasing eval — A/B vs template             | code + doc | 2 sess | —       | todo                                        |
| **C2** | Multispecialty drug expansion                       | code       | 1 sess | —       | **done** — +4 HCPCS, $2.08M→$2.45M captured |
| **C3** | Inventory / JW modifier / drug-waste exception type | code       | 2 sess | —       | todo                                        |
| **C4** | Prior-auth propensity model (pre-bill PA risk)      | code       | 2 sess | —       | todo                                        |
| **C5** | Site-of-care optimization scenario                  | code       | 1 sess | —       | todo                                        |

### C1 — LLM paraphrasing eval

Currently feature-flagged off. Run with flag on against top-20; build a 50-item rubric scoring paraphrase quality (numerical accuracy, citation fidelity, tone, abstention compliance) across 3 models (qwen2.5:7b, qwen2.5:72b, Azure OpenAI gpt-4-class). Acceptance: blog-post-quality writeup; one model selected for V2 with documented rationale.

### C2 — Multispecialty drug expansion

Add 4–6 more high-$ specialty drugs: oncology second-line agents, retinal anti-VEGF alternatives, rheum IL-17/IL-23, GI vedolizumab, neuro newer MS biologics. Acceptance: pipeline still <15s; AUC ≥ 0.90 retained.

### C3 — Inventory / JW modifier / drug waste

New exception type: claim units billed without JW modifier when partial-vial waste is expected per dose calculation. Requires inventory feed (synthetic in V2). Acceptance: new exception type fires; cited to a Medicare JW modifier policy doc.

### C4 — Prior-auth propensity model

Pre-bill PA risk: predicts P(claim will be denied for PA reasons) at submission time, BEFORE adjudication, so the practice can resubmit with PA reference attached. Different from the V1 `access_pa_gap` which is post-bill. Acceptance: separate model registered; pre-bill recall on the simulated holdout.

### C5 — Site-of-care optimization

Scenario module: for each high-$ administration, the modeled reimbursement difference between HOPD vs. freestanding clinic vs. home-infusion site. Surfaces underpayment patterns tied to site contracting. Acceptance: scenario fires for relevant claims; cited to commercial PA workflow §4 (administration site).

---

## Track D — V3 Network Rollout (6 months post-pilot)

Pilot → scale. Most items are operational, not code.

| ID     | Item                                        | Type       | Effort | Depends | Status |
| ------ | ------------------------------------------- | ---------- | ------ | ------- | ------ |
| **D1** | Practice acquisition workflow as live app   | code       | 4 sess | C, B7   | todo   |
| **D2** | Multi-practice benchmarking + drill-through | code       | 3 sess | B7      | todo   |
| **D3** | Contract economics v2 — AP/AR closure       | code       | 4 sess | B3      | todo   |
| **D4** | Biosimilar conversion program dashboard     | code       | 2 sess | C2      | todo   |
| **D5** | Payer-policy change detection               | code       | 3 sess | B1      | todo   |
| **D6** | Reviewer throughput measurement             | code       | 1 sess | B7      | todo   |
| **D7** | 340B compliance workflow                    | code + doc | 3 sess | B6      | todo   |

### D1 — Practice acquisition app

The Week-4 memo becomes a live tool: select a practice, see initiatives projection, mark them in-progress, track recovery vs. plan over 100 days. Acceptance: end-to-end flow on a pilot practice.

### D2 — Multi-practice benchmarking

Practice-vs-peer views, network-level KPIs, drill-through from network → practice → exception. Acceptance: dashboard live for the pilot network.

### D3 — Contract economics v2

Closes the loop: chargeback-validation flag → automated dispute submission preparation (still human-approved) → resolution tracking. Acceptance: dispute prep generated; finance approves before submission.

### D4 — Biosimilar conversion dashboard

Per-practice × J-code × quarter conversion rate, against the GPO addendum's tier targets. Acceptance: live dashboard; conversion-rate trend per practice.

### D5 — Payer-policy change detection

Monitor payer-portal pages and CMS LCD updates; re-score affected claims when policy changes. Acceptance: change detection runs nightly; affected-claim re-score event triggers an alert.

### D6 — Reviewer throughput measurement

Replace the 5-min/item placeholder with measured per-exception-type throughput from the override log. Acceptance: $/reviewer-hour KPI in the dashboard uses measured throughput.

### D7 — 340B compliance workflow

The scenario module becomes a full compliance workflow with attestation, modifier-UD verification, and quarterly self-audit report. Acceptance: compliance officer sign-off on the workflow; first quarterly self-audit produced.

---

## Track E — V4 Research Backlog

Longer horizon. TPM surfaces these to advanced analytics; not necessarily TPM-built.

| ID     | Item                                                               | Type | Status |
| ------ | ------------------------------------------------------------------ | ---- | ------ |
| **E1** | Cross-practice leakage correlation                                 | code | parked |
| **E2** | Buy-and-bill inventory waste detection (advanced)                  | code | parked |
| **E3** | Outbound contract negotiation intelligence                         | code | parked |
| **E4** | LLM-based clinical-necessity reasoner for appeals (human-approved) | code | parked |
| **E5** | Payer mix optimization                                             | code | parked |
| **E6** | DSCSA traceability integration                                     | code | parked |

These are sized in `docs/roadmap.md` Phase V4. No expected delivery; parked unless a stakeholder request promotes one.

---

## Track F — Application Activities (parallel to Tracks A–E)

The portfolio is a means to an end. Don't let polish work crowd out the actual application.

| ID     | Item                                             | Effort      | Status |
| ------ | ------------------------------------------------ | ----------- | ------ |
| **F1** | Repo public + apply via careers.mckesson.com     | 30 min      | todo   |
| **F2** | Cover letter (thesis paragraph + repo link)      | 30 min      | todo   |
| **F3** | Outreach: LinkedIn warm contacts at McKesson O&M | 1 hr        | todo   |
| **F4** | HFMA CRCR enrollment (optional, 14 CPEs, ~$200)  | 1 hr enroll | todo   |
| **F5** | Recruiter follow-ups every 5 days post-apply     | ongoing     | todo   |
| **F6** | Interview prep: technical + behavioral storying  | 4 hr        | todo   |
| **F7** | Pre-interview demo dry-run on the actual machine | 30 min      | todo   |

These are duplicated from Track A's manual items because they're application-critical and need their own status separate from V1 polish.

---

## Operating cadence

- **Per-session:** start with `make test`; end with `make test && git push`. Never push a red main.
- **Per item:** update status in this doc when you start (`in-progress`) and ship (`done`). When blocked, add a one-line note.
- **Per week:** review which Track-B/C items are in flight; if more than two are `in-progress`, finish one before starting another.
- **Per ship:** rerun the demo end-to-end; confirm the README headline numbers haven't regressed; update the README only if numbers materially change.
- **Per recruiter touchpoint:** drop a one-paragraph "what shipped this week" update.

## Decision gates (require a human call before proceeding)

- **GD-1: V2 pilot practice selection** — Track B blocks unless a single pilot practice is identified by O&M. Until then, B-track items run on synthetic data.
- **GD-2: Reviewer UI surface** — B7 blocks until stakeholder interviews land on Databricks App vs. embedded workstation panel.
- **GD-3: LLM model selection** — C1 ships an A/B writeup; the choice between local Ollama, Azure OpenAI, and Mosaic AI is a TPM + Staff ML Engineer decision based on the writeup.
- **GD-4: 340B module enablement** — D7 ships a compliance workflow; whether to enable per-practice is a compliance + practice CFO call.
- **GD-5: Public-facing claims** — when V2 retrospective labels arrive, the README's "synthetic" disclaimer must be updated. Production performance claims require legal sign-off.

## What we are explicitly NOT doing

Same list as `docs/roadmap.md` "What is intentionally NOT on the roadmap":

- Automated appeal submission
- Automated prior-auth submission
- Clinical decision support
- Standalone chatbot UX
- Fine-tuned LLMs as a headline (V2 LLM stays prompt-engineered over the retriever)

If a stakeholder asks for any of these, route to a human-approved override flow instead of automation.

## Stop conditions

This plan ends — not the project — when:

1. Track A is `done` (V1 polish complete; demoable to McKesson)
2. McKesson application returns a yes/no
3. **If yes:** plan re-baselined as the on-the-job V2/V3 backlog with the actual O&M team
4. **If no:** plan re-baselined for the next comparable role; portfolio remains a working artifact

Either way, this document captures the work; nothing in it expires.
