# LLM Paraphrase A/B Evaluation — V2 Model Selection (Track C1)

**Status:** harness shipped (`oaifinance.eval.paraphrase_eval`); A/B run executed against three models when `OAI_ENABLE_LLM_PARAPHRASE=1` and the candidate models are reachable.

The V1 explainer is deterministic + template-based with strict citation enforcement (DL-0010). The V2 paraphrase layer (shipped feature-flagged in `oaifinance.rag.paraphraser`) re-renders the top-20 explained items via an LLM under a post-generation citation verifier. Before V2 enables paraphrase by default in production, this A/B selects one model based on a four-dimension rubric.

## Rubric

Each paraphrase is scored on four dimensions; each scored `yes / partial / no` (1.0 / 0.5 / 0.0):

1. **Numerical accuracy** — every dollar amount and numerical claim from the upstream template is preserved verbatim; no invented numbers
2. **Citation fidelity** — the `[doc_id §section]` marker is present AND a 40-char+ verbatim fragment of the retrieved clause is quoted (this is the V2 verifier contract)
3. **Tone appropriateness** — no first-person pronouns, no marketing copy, no emoji; reviewer-ready clinical/finance register
4. **Abstention compliance** — `paraphrase_status="failed_call"` or `failed_verify` ⇒ `paraphrase_text` MUST be `None`. Any text output under a fail status is a CONTRACT VIOLATION and scores `no`

Composite score is the simple mean. **Acceptance threshold: composite ≥ 0.85 with abstention_compliance = 1.00 across all 50 items.** A model that violates the abstention contract on even one item is rejected regardless of its mean.

## Models evaluated

| Model                     | Endpoint            | Latency budget |
| ------------------------- | ------------------- | -------------- |
| qwen2.5:7b-instruct       | local Ollama        | ≤ 8s/item      |
| qwen2.5:72b-instruct      | local Ollama        | ≤ 30s/item     |
| Azure OpenAI gpt-4o-class | enterprise endpoint | ≤ 6s/item      |

## Test set

50 explained exception rows drawn from the seed-20260424 pipeline run, stratified by `exception_type` so every type appears at least 4 times. Each row carries:

- the V1 template text (the verifier ground truth for citation fidelity)
- the retrieved clause + (doc_id, section_title)
- expected dollar amounts (dollars_at_risk, allowed_total, billed_total)

## Running the A/B

```bash
# 1. Ensure Ollama is reachable and pulls have completed
ollama pull qwen2.5:7b-instruct
ollama pull qwen2.5:72b-instruct

# 2. Run the pipeline so explained_exceptions.parquet is fresh
make demo

# 3. Run the A/B against each model (the harness writes per-model
#    parquet outputs under artifacts/paraphrase_eval/)
OAI_ENABLE_LLM_PARAPHRASE=1 OLLAMA_MODEL=qwen2.5:7b-instruct \
    uv run python -m oaifinance.eval.paraphrase_eval --label qwen-7b
OAI_ENABLE_LLM_PARAPHRASE=1 OLLAMA_MODEL=qwen2.5:72b-instruct \
    uv run python -m oaifinance.eval.paraphrase_eval --label qwen-72b
# Azure: set AZURE_OPENAI_* and run with --backend azure
```

## Results template (fill in after running the A/B)

| Model                | n   | Composite | Numerical | Citation | Tone | Abstention |
| -------------------- | --- | --------- | --------- | -------- | ---- | ---------- |
| qwen2.5:7b-instruct  | 50  | \_        | \_        | \_       | \_   | \_         |
| qwen2.5:72b-instruct | 50  | \_        | \_        | \_       | \_   | \_         |
| gpt-4o-class         | 50  | \_        | \_        | \_       | \_   | \_         |

## Decision rationale (fill in after running the A/B)

- **Selected model:** \_
- **Why:** [composite ≥ 0.85 AND abstention compliance 1.0 AND latency budget honored]
- **Cost note:** \_
- **Operational risk:** \_
- **Fallback model:** \_
- **Re-evaluation cadence:** quarterly + on any retriever / corpus change

## Risks the A/B doesn't measure

- Drift over time once the chosen model is in production — covered by the override-rate alarm in `dashboards/sql/alerts/04`
- Non-English content — out of scope for V2; English-only guardrail
- Cost variance — operational concern; tracked in finance separately
- Privacy / data residency — covered by `docs/governance.md` §4

## Why this matters for V2

The auditability-critical mechanism is citation enforcement + abstention. The deterministic template (V1) honors that contract by construction. Adding an LLM step is a real improvement (better natural-language fluency for reviewers) but ONLY if the post-generation verifier preserves the contract. This A/B exists to prove a chosen model honors it on a non-trivial sample before promotion to default-on.
