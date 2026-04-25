# DUA + IRB Privacy Office Checklist — V2 retrospective-label readiness

**Use:** before moving the Control Tower from synthetic data (V1) to real retrospective billing-system labels (V2 pilot per `docs/refinement-plan.md` track B). Walk through the rows in order; do not start V2 ingest until every status is `done`.

**Owner:** TPM. **Required collaborators:** Privacy Office, Legal, Internal Audit, Practice CFO, Compliance.

---

## 1. Data Use Agreement (DUA)

| Item                                                | Status | Owner          | Notes                                                                               |
| --------------------------------------------------- | ------ | -------------- | ----------------------------------------------------------------------------------- |
| Counterparty identified (practice + parent network) | ☐      | TPM + Legal    | One DUA per pilot practice; FCS or comparable                                       |
| Permitted use scope (revenue integrity AI scoring)  | ☐      | Legal          | Out: clinical decision support, marketing, secondary research                       |
| PHI vs. de-identified data                          | ☐      | Privacy Office | V2 prefers de-identified per HIPAA Safe Harbor; PHI requires Limited Data Set + DUA |
| Data minimization clause                            | ☐      | Privacy Office | Only fields required by the model are received                                      |
| Re-identification prohibition                       | ☐      | Legal          | Standard contract clause                                                            |
| Retention schedule                                  | ☐      | Privacy Office | Aligns with `docs/governance.md` §4 (90-day cold tier, 7-year audit retention)      |
| Breach notification path                            | ☐      | Privacy Office | 24-hour notification per HIPAA Breach Notification Rule                             |
| Data return / destruction at termination            | ☐      | Legal          | Standard term                                                                       |
| Indemnification                                     | ☐      | Legal          | Standard term                                                                       |
| Subcontractor / vendor flow-down                    | ☐      | Legal          | Cover Databricks, Azure OpenAI / Mosaic AI as sub-processors                        |
| Effective date + term + renewal                     | ☐      | Legal          | Default: 1 year + auto-renew with 90-day opt-out                                    |

## 2. Business Associate Agreement (BAA)

| Item                             | Status | Owner          | Notes                                             |
| -------------------------------- | ------ | -------------- | ------------------------------------------------- |
| Microsoft Azure BAA in force     | ☐      | Privacy Office | Standard Microsoft BAA covers Azure subscription  |
| Databricks-on-Azure BAA addendum | ☐      | Privacy Office | Confirm Databricks workspace is BAA-eligible tier |
| Azure OpenAI BAA flow-down       | ☐      | Privacy Office | Required if V2 LLM layer hits Azure OpenAI        |
| Sub-processor list current       | ☐      | Privacy Office | Reviewed quarterly                                |

## 3. IRB / institutional review

V2 retrospective billing labels for finance-AI scoring is generally a **quality improvement** activity rather than human-subjects research, but the institutional path varies by site. Confirm with each pilot practice's research office.

| Item                                          | Status | Owner                    | Notes                                                             |
| --------------------------------------------- | ------ | ------------------------ | ----------------------------------------------------------------- |
| QI vs. research determination                 | ☐      | Practice IRB liaison     | Document the rationale                                            |
| If research: IRB protocol submitted           | ☐      | TPM + IRB                | May be exempt under 45 CFR 46.104(d)(4) for retrospective records |
| If QI: QI protocol filed with research office | ☐      | Practice quality officer | Standard QI registration                                          |
| Patient consent / waiver determination        | ☐      | IRB                      | Typically waiver of consent for retrospective claims data         |
| Risk / benefit summary                        | ☐      | TPM                      | Modeled on docs/charter.md                                        |

## 4. Privacy Office checklist

| Item                                              | Status | Owner             | Notes                                                                   |
| ------------------------------------------------- | ------ | ----------------- | ----------------------------------------------------------------------- |
| Data flow diagram                                 | ☐      | TPM               | Map: practice billing → DUA-compliant transfer → bronze → silver → gold |
| Privacy impact assessment (PIA)                   | ☐      | Privacy Office    | One PIA per pilot                                                       |
| HIPAA Safe Harbor de-identification verified      | ☐      | Privacy Office    | If de-identified path chosen                                            |
| Limited Data Set criteria documented              | ☐      | Privacy Office    | If LDS path chosen                                                      |
| Encryption at rest (CMK)                          | ☐      | Cloud Platform    | Customer-managed keys per docs/governance.md §4                         |
| Encryption in transit (TLS)                       | ☐      | Cloud Platform    | Standard                                                                |
| VNet injection / no public endpoints              | ☐      | Cloud Platform    | docs/governance.md §4                                                   |
| Row-level security per docs/governance.md §4 + §7 | ☐      | Staff ML Engineer | See dashboards/sql/governance/01_unity_catalog_rls.sql                  |
| DLP on outbound prompts                           | ☐      | Staff ML Engineer | If V2 LLM layer hits external endpoint                                  |
| Access logging to SIEM                            | ☐      | SecOps            | Standard pattern                                                        |
| Break-glass justification field                   | ☐      | SecOps            | Required for PHI-adjacent table reads                                   |

## 5. Compliance / SOX

| Item                                      | Status | Owner          | Notes                                                                         |
| ----------------------------------------- | ------ | -------------- | ----------------------------------------------------------------------------- |
| Model risk management framework alignment | ☐      | Internal Audit | Map to existing finance MRM                                                   |
| SOX scoping decision                      | ☐      | Controllership | Are AI-assisted finance entries SOX-relevant? Default: yes for any entry > $X |
| Change-control process documented         | ☐      | TPM            | docs/governance.md §5                                                         |
| Two-person integrity attested             | ☐      | TPM            | Promotion approver ≠ PR author; logged                                        |
| Override log retention 7 years            | ☐      | Controllership | docs/governance.md §7                                                         |
| Drift / alarm runbook                     | ☐      | TPM            | dashboards/sql/alerts/                                                        |

## 6. Operational

| Item                             | Status | Owner              | Notes                                     |
| -------------------------------- | ------ | ------------------ | ----------------------------------------- |
| Data ingest cadence agreed       | ☐      | TPM + Practice IT  | Daily? Weekly? Manual until automated     |
| Pilot success metrics signed off | ☐      | Practice CFO       | Aligns to docs/charter.md success metrics |
| Reviewer training plan           | ☐      | TPM + RCM Ops      | Onboarding for the queue UI               |
| Escalation contacts published    | ☐      | TPM                | Slack / email / on-call                   |
| Pilot exit criteria documented   | ☐      | TPM + Practice CFO | Must be explicit before start             |

## 7. Sign-off

This checklist is reviewed and signed by:

- TPM (product) — ************\_************ Date: ****\_\_****
- Privacy Office — ************\_************ Date: ****\_\_****
- Legal — ************\_************ Date: ****\_\_****
- Internal Audit — ************\_************ Date: ****\_\_****
- Practice CFO — ************\_************ Date: ****\_\_****

V2 ingest begins **only after** all signatures are in place.
