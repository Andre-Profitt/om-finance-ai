# Discovery Plan — V2 Pilot Validation

**Status:** plan; runs concurrently with the V2 pilot DUA / privacy approvals (`docs/dua-irb-checklist.md`)
**Owner:** TPM
**Output:** validated hypotheses + a 1-page "what we changed in the roadmap because of this" memo

The V1 artifact ships fast. Before V2 commits engineering capacity, this plan validates that the actual O&M Finance / Practice operations teams agree with the value hypothesis, the persona model, and the disposition workflow assumed in `docs/charter.md`. It is the customer-discovery + usability layer the JD specifically asks for ("ideation, discovery, continuous-improvement workshops" and "incorporate customer & user feedback into the prioritization of current product feature expansion").

---

## 1. Hypotheses to validate

Each hypothesis maps to a docs/charter.md success metric or a docs/roi-model.md assumption. Validate or kill — don't half-keep.

| ID  | Hypothesis                                                                                                              | If invalidated, what changes                                                                  |
| --- | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| H1  | Reviewers will trust a calibrated model + cited explanation enough to dispose 80%+ of top-100 items per shift.          | Re-design the queue UI; possibly add tier-1/tier-2 reviewer roles; reduce default queue size. |
| H2  | The 25% prevention-lift assumption in `docs/roi-model.md` is achievable on a real practice's payer mix.                 | Replace the headline ROI scenario with a measured base case; remove the upside scenario.      |
| H3  | The 7-minute-per-item reviewer throughput planning assumption is realistic.                                             | Re-tune `oaifinance.config.REVIEWER_REVIEW_MINUTES`; recompute the practice performance memo. |
| H4  | Citation-grounded explanations materially reduce override-without-action rate.                                          | Adjust the citation contract; possibly require LLM paraphrase as default-on.                  |
| H5  | The 10 V1 exception types cover the >80% of recoverable leakage at a typical O&M practice.                              | Add or remove exception types; re-prioritize the Track C/D backlog.                           |
| H6  | Practices want a per-practice CFO dashboard alongside the reviewer queue, not just a queue.                             | Bring the Network View KPI strip closer to the Reviewer Queue (or vice versa).                |
| H7  | The Glide Health / CoverMyMeds / Onmark integrations leave gaps that a Control Tower fills, vs. duplicating capability. | Re-position the product against actual gaps; update the README thesis.                        |

## 2. Stakeholder interviews — five required, two optional

Five 45-minute sessions, scheduled in week 1 of pilot prep. Each interview produces ≤ 1 page of notes filed under `docs/private/discovery-interviews/<role>-<date>.md` (gitignored).

### Required

1. **Revenue cycle analyst** — at the pilot practice. Watch them work the existing denial / appeal / chargeback queue for 30 minutes; ask about pain points; show V1 reviewer-queue mock for 15 minutes.
2. **Access operations lead** — same practice. Ask about the PA workflow gap; show V1 access_pa_gap exception type; ask whether pre-bill PA propensity (Track C4) would change their day.
3. **Practice CFO** — same practice. Show the practice performance memo; ask which numbers they'd defend to their network CFO; ask which they'd kill.
4. **Controller** — at the network level. Show `docs/governance.md` § SOX change control; ask what's missing for AI-assisted entries to clear quarterly close.
5. **Network analytics lead** — at McKesson O&M (Ontada or equivalent). Ask how the Control Tower would consume Ontada signals; ask what they'd need from us in return.

### Optional (if access)

6. **GPO contracts lead** — at Onmark or equivalent. Show the contract economics module; ask whether the chargeback validation logic matches their actual workflow.
7. **Internal Audit** — show the override log + retention model; ask what they'd need to clear the AI-assisted entries SOX scope.

## 3. Interview structure (45-min template)

```
0:00–0:05   Intro + their role + what they own
0:05–0:15   Watch them work / draw their current workflow on a whiteboard
0:15–0:25   Show the V1 artifact relevant to their role
0:25–0:35   Ask the discovery questions for their persona
0:35–0:42   "If you could change ONE thing about today's workflow, what?"
0:42–0:45   Wrap; what would they want to see in 30 days
```

Don't pitch. Watch and ask.

## 4. Persona-specific questions

### Revenue cycle analyst

- Walk me through your last 5 denials. Which ones did you appeal? Why or why not?
- When you see a denial, how do you decide if it's worth working?
- What's the one thing in your workflow that breaks most often?
- If a tool said "this denial is 85% likely to be recoverable, here's the cited policy clause," would you trust it on first use? On 100th use? What changes between?

### Access operations lead

- For prior-auth denials (CO-197), what's the median time from claim submission to PA approval to corrected resubmission?
- Where does CoverMyMeds end and your work begin?
- If we could flag a claim BEFORE submission as 70%+ likely to be denied for PA reasons, what would you do with that signal?

### Practice CFO

- Of the dollars in the practice performance memo, which would you defend in a board meeting? Which would you cut in half?
- What's your practice's current annual leakage estimate? How was it computed?
- If we report "$322K projected recovery, $292 reviewer cost," what's wrong with that number? (Listening for the "implementation cost / SME time / change management" answer.)

### Controller

- What's the SOX scope on AI-assisted entries today? What threshold dollar amount triggers documentation?
- How would AI-assisted finance entries land in your annual SOX walkthrough?
- What's missing from `docs/governance.md` §5 for you to sign off on a single-practice pilot?

### Network analytics lead

- What signals does Ontada produce that this Control Tower could consume?
- What would you need this Control Tower to produce that you'd consume?
- Is the connected-specialty-care framing right? What would you say differently?

## 5. Usability test (week 2 of pilot prep)

A 30-minute moderated session at the reviewer's actual workstation:

1. **Setup** (3 min): explain we're testing the tool, not them; recordings are for our notes only.
2. **Cold-open task** (10 min): "You have 30 minutes of review time. Here are 50 flagged exceptions. Work them." Watch silently.
3. **Think-aloud task** (10 min): "Now narrate as you work. Tell me what you're doing and why." Take notes on every "huh" or "wait, what?"
4. **Specific probes** (5 min): "What does the abstention pill mean?" "What would you do if the citation didn't make sense?" "When would you escalate vs reject?"
5. **Wrap** (2 min): "What would change your workflow tomorrow?"

Score against 6 rubric items: queue scan time per item, drill-in comprehension, citation usability, disposition confidence, abstention interpretation, override rationale clarity. Each scored Yes / Partial / No.

## 6. Pilot entry / exit criteria

Pilot starts when:

- Discovery interviews 1–5 complete
- Usability test produces 4-of-6 Green
- All `docs/dua-irb-checklist.md` rows in §1–§4 are ☑
- Practice CFO and Controller signed the pilot intent letter

Pilot exits when (any of):

- 12 weeks elapsed AND realized recovery / projected recovery (per `docs/value-realization-runbook.md` §4) ≥ 0.50 → success → V3
- 12 weeks elapsed AND ratio < 0.30 → product reset; re-baseline V1 against the data we learned
- Critical incident (PHI exposure, SOX deficiency, calibration drift > 2 cycles unresolved) → immediate exit

## 7. What changes in the roadmap

Whatever the discovery output is, document it as DL-0016+ in `docs/decision-log.md`. Specifically, after pilot:

- Update `docs/charter.md` value hypothesis with measured prevention lift
- Update `docs/roi-model.md` headline scenario to a measured base case (drop the +100% upside if not validated)
- Update `docs/refinement-plan.md` Track D priorities based on what the practice actually asked for
- Update `docs/raci.md` if the matrixed-team conversations revealed a different decision-rights model than we assumed

## 8. What this is NOT

- A reason to delay V1 shipping. V1 ships now.
- A research project — pilot is QI, not human-subjects research (see roadmap clarification on IRB).
- A blank check for backlog reshuffling — every change to the roadmap from discovery output requires a documented rationale.
