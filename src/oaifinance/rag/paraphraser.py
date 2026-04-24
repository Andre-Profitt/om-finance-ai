"""Optional LLM paraphrase layer over the template explainer.

Off by default. Enable with `OAI_ENABLE_LLM_PARAPHRASE=1` and a reachable
Ollama endpoint (`OLLAMA_BASE_URL`, default http://localhost:11434) running
the model named in `OLLAMA_MODEL` (default `qwen2.5:7b-instruct` — a small
model is sufficient since the retrieved clause already constrains the task).

Citation contract (never weakened):
  1. LLM sees the template text + the retrieved chunk + the citation tuple.
  2. LLM output is post-verified: the cited (doc_id, section_title) must
     appear in the paraphrase, AND at least one 40-character fragment from
     the retrieved chunk must appear verbatim.
  3. On verification failure or unreachable endpoint: the template text is
     kept and `paraphrase_status` is recorded as `failed` or `skipped`.
     The system never publishes an unverified paraphrase.

Only the top-20 queue items are paraphrased (configurable); the rest retain
the deterministic template. This keeps the mechanism auditable while showing
the LLM layer exists in code, not only in docs.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import polars as pl
import requests

from oaifinance.config import GOLD_DIR

OLLAMA_BASE_URL_DEFAULT = "http://localhost:11434"
OLLAMA_MODEL_DEFAULT = "qwen2.5:7b-instruct"
DEFAULT_TOP_K = 20
FRAGMENT_CHARS = 40

PARAPHRASE_PROMPT = """You are a finance-AI assistant writing a one-paragraph
reviewer-ready explanation for a flagged revenue-cycle exception.

RULES (inviolable):
1. Use ONLY information from the retrieved clause and the structured facts.
2. Include the citation marker exactly once, in the form: [{doc_id} §{section_title}].
3. Quote at least one phrase (8+ words) verbatim from the retrieved clause, in double quotes.
4. Do not invent dollar amounts, payer rules, or policy text not present below.
5. Return a single paragraph of 2-4 sentences. No lists.

STRUCTURED FACTS:
claim_id: {claim_id}
exception_type: {exception_type}
hcpcs_code: {hcpcs}
payer: {payer}
dollars_at_risk: ${dollars_at_risk:,.0f}
calibrated_risk_score: {risk_score:.3f}

RETRIEVED CLAUSE ({doc_id} §{section_title}):
{clause}

TEMPLATE OUTPUT (for tone reference; rewrite in your own words but preserve all facts):
{template}

Return ONLY the paraphrase paragraph."""


@dataclass
class ParaphraseResult:
    claim_id: str
    status: str  # "ok" | "skipped" | "failed_verify" | "failed_call"
    paraphrase_text: str | None


def _ollama_available(base_url: str, timeout: float = 2.0) -> bool:
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=timeout)
        return r.status_code == 200
    except requests.RequestException:
        return False


def _ollama_generate(base_url: str, model: str, prompt: str, timeout: float = 60.0) -> str | None:
    try:
        r = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
        return str(data.get("response", "")).strip() or None
    except requests.RequestException:
        return None
    except (ValueError, json.JSONDecodeError):
        return None


def _verify(paraphrase: str, doc_id: str, section_title: str, clause: str) -> bool:
    if not paraphrase:
        return False
    marker = f"[{doc_id} §{section_title}]"
    if marker not in paraphrase:
        return False
    # Require one 40-char+ fragment from the clause to appear verbatim.
    clause_compact = " ".join(clause.split())
    # Split clause into overlapping 40-char windows and look for any match.
    step = 20
    n = len(clause_compact)
    if n < FRAGMENT_CHARS:
        return clause_compact in paraphrase
    for start in range(0, n - FRAGMENT_CHARS + 1, step):
        window = clause_compact[start : start + FRAGMENT_CHARS]
        if window in paraphrase:
            return True
    return False


def paraphrase_queue(
    explained: pl.DataFrame | None = None,
    top_k: int = DEFAULT_TOP_K,
    rank_col: str = "expected_recovery_calibrated",
) -> pl.DataFrame:
    if explained is None:
        explained = pl.read_parquet(GOLD_DIR / "explained_exceptions.parquet")

    enabled = os.environ.get("OAI_ENABLE_LLM_PARAPHRASE", "0") == "1"
    base_url = os.environ.get("OLLAMA_BASE_URL", OLLAMA_BASE_URL_DEFAULT)
    model = os.environ.get("OLLAMA_MODEL", OLLAMA_MODEL_DEFAULT)

    if not enabled:
        out = explained.with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("paraphrase_text"),
            pl.lit("skipped").alias("paraphrase_status"),
        )
        out.write_parquet(GOLD_DIR / "explained_exceptions.parquet")
        return out

    if not _ollama_available(base_url):
        out = explained.with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("paraphrase_text"),
            pl.lit("failed_call").alias("paraphrase_status"),
        )
        out.write_parquet(GOLD_DIR / "explained_exceptions.parquet")
        return out

    rank = rank_col if rank_col in explained.columns else "expected_recovery"
    queue = explained.filter(pl.col("explained")).sort(rank, descending=True).head(top_k)

    results: dict[str, ParaphraseResult] = {}
    for row in queue.iter_rows(named=True):
        doc_id = row.get("citation_doc_id") or ""
        section_title = row.get("citation_section") or ""
        clause = row.get("explanation_text") or ""
        # The template already contains the quoted clause; we pull the
        # retrieved chunk text from the explainer's template output.
        prompt = PARAPHRASE_PROMPT.format(
            claim_id=row["claim_id"],
            exception_type=row.get("exception_type", "unknown"),
            hcpcs=row.get("hcpcs_code", ""),
            payer=row.get("payer", ""),
            dollars_at_risk=float(row.get("dollars_at_risk") or 0.0),
            risk_score=float(row.get("risk_score_calibrated") or row.get("risk_score") or 0.0),
            doc_id=doc_id,
            section_title=section_title,
            clause=clause,
            template=clause,
        )
        response = _ollama_generate(base_url, model, prompt)
        if response is None:
            results[row["claim_id"]] = ParaphraseResult(
                claim_id=row["claim_id"],
                status="failed_call",
                paraphrase_text=None,
            )
            continue
        if _verify(response, doc_id, section_title, clause):
            results[row["claim_id"]] = ParaphraseResult(
                claim_id=row["claim_id"],
                status="ok",
                paraphrase_text=response,
            )
        else:
            results[row["claim_id"]] = ParaphraseResult(
                claim_id=row["claim_id"],
                status="failed_verify",
                paraphrase_text=None,
            )

    paraphrase_rows = []
    for cid in explained["claim_id"].to_list():
        r = results.get(cid)
        if r is None:
            paraphrase_rows.append(
                {
                    "claim_id": cid,
                    "paraphrase_text": None,
                    "paraphrase_status": "skipped",
                }
            )
        else:
            paraphrase_rows.append(
                {
                    "claim_id": cid,
                    "paraphrase_text": r.paraphrase_text,
                    "paraphrase_status": r.status,
                }
            )

    paraphrase_df = pl.DataFrame(paraphrase_rows)
    out = explained.join(paraphrase_df, on="claim_id", how="left")
    out.write_parquet(GOLD_DIR / "explained_exceptions.parquet")
    return out


if __name__ == "__main__":
    df = paraphrase_queue()
    status_counts = df.group_by("paraphrase_status").len().sort("len", descending=True)
    print(status_counts)
