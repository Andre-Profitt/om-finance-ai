# RACI Matrix — O&M Finance AI Control Tower

**R** = Responsible (does the work) · **A** = Accountable (signs off) · **C** = Consulted (asked) · **I** = Informed (told)

Across nine recurring decisions / events, who plays which role. This is the matrixed-organization layer that the role description specifically flags ("highly matrixed teams … finance, advanced analytics, engineering, finance ops, executive leadership"). One A per row.

| Decision / event                                          | TPM | Staff ML Eng | Finance Ops | Practice RCM | Controller | Privacy / Security | Legal | Compliance | Practice CFO | Exec Sponsor |
| --------------------------------------------------------- | --- | ------------ | ----------- | ------------ | ---------- | ------------------ | ----- | ---------- | ------------ | ------------ |
| **Model promotion** (Staging → Production)                | A   | R            | C           | I            | C          | I                  | I     | I          | I            | I            |
| **New payer policy ingested into corpus**                 | A   | R            | I           | C            | I          | I                  | I     | I          | I            | I            |
| **New exception type launched**                           | A   | R            | C           | C            | C          | I                  | I     | C          | C            | I            |
| **Reviewer override review** (steady-state)               | C   | I            | A           | R            | I          | I                  | I     | I          | I            | I            |
| **ROI sign-off** (per practice, quarterly)                | R   | C            | C           | C            | A          | I                  | I     | I          | C            | I            |
| **Security / privacy approval** (DUA, sub-processor, BAA) | C   | I            | I           | I            | I          | A                  | R     | C          | I            | I            |
| **Practice onboarding** (V2 pilot start)                  | R   | C            | C           | C            | C          | C                  | C     | C          | A            | I            |
| **Dashboard release** (new SQL panel, new alarm)          | A   | R            | C           | C            | C          | I                  | I     | I          | I            | I            |
| **Incident rollback** (model alarmed, retract scoring)    | R   | A            | I           | I            | C          | I                  | I     | I          | I            | I            |

---

## Notes per role

**TPM** — owns prioritization, the roadmap, the charter, the eval rubric, and the disposition language reviewers see. Single point of accountability for the product.

**Staff ML Engineer** — owns the model, the calibration, the MLflow pipeline, the rollback path, and the technical SLA. Two-person integrity with TPM on every promotion (DL governs change control per `docs/governance.md` §5).

**Finance Operations** — owns daily reviewer queue throughput, override quality, and the recovery KPI delivery to controllership.

**Practice RCM** — the actual humans working the queue. Their feedback drives reviewer-UX changes. Their override rate is a first-class signal.

**Controller** — owns the SOX boundary on AI-assisted finance entries. Quarterly ROI sign-off. Owns the override-log retention contract.

**Privacy / Security** — owns BAA, DUA, encryption, RLS enforcement, DLP on prompts. Hard gate on PHI-adjacent surfaces.

**Legal** — owns DUA terms, sub-processor flow-down, indemnification, and any payer-facing communication.

**Compliance** — owns 340B + Stark + AKS exposure on the contract economics module. Hard gate on any compliance-volatile exception type.

**Practice CFO** — accountable for go-live at their practice. Reads the practice performance memo. Approves the V2 pilot kickoff and pilot exit.

**Executive Sponsor** — VP O&M Finance Transformation (modeled). Informed of all material events; consulted only on strategic direction shifts (e.g., scope change, V3 timeline).

## Decision rights conflicts to watch

A few rows have known fault lines. These are explicit so the TPM doesn't end up resolving them in the moment:

- **Model promotion** — TPM is Accountable, but the controllership has effective veto via SOX gates. If the controller blocks promotion, the change does not ship; this is intentional, not a bug.
- **New exception type** — TPM is Accountable, but Compliance is Consulted with effective veto on volatile types (340B, biosimilar conversion when payer/contract policy is fluid).
- **Practice onboarding** — Practice CFO is Accountable, but the readiness scorecard (`docs/acquisition-integration-scorecard.md`) is gating; a Red scorecard score blocks even an enthusiastic Practice CFO.
- **Incident rollback** — TPM is Responsible (initiates) but Staff ML Engineer is Accountable (technical execution + post-mortem); avoids the "TPM goes silent for an hour while ML eng debugs" failure mode.

## Operating cadence

| Cadence   | Forum                              | Required attendees                           |
| --------- | ---------------------------------- | -------------------------------------------- |
| Daily     | Reviewer queue standup             | Practice RCM lead, Finance Ops               |
| Weekly    | Override + drift review            | TPM, Staff ML Eng, Finance Ops, Practice RCM |
| Bi-weekly | Compliance + corpus refresh        | TPM, Compliance, Staff ML Eng                |
| Monthly   | Practice performance review        | TPM, Practice CFO, Controller, Finance Ops   |
| Quarterly | ROI sign-off + roadmap re-baseline | TPM, Controller, Practice CFO, Exec Sponsor  |
