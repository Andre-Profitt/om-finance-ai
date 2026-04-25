"""Unit tests for the LLM paraphrase layer.

Citation contract is the load-bearing invariant: paraphrase must include the
[doc_id §section_title] marker AND a 40-char+ verbatim fragment of the
retrieved clause. Verification failure or unreachable Ollama → fallback to
template with status `failed_verify` or `failed_call`.
"""

from __future__ import annotations

import polars as pl

from oaifinance.rag import paraphraser as p


CLAUSE = (
    "Every claim for a drug billed under an HCPCS J-code MUST include a "
    "corresponding National Drug Code (NDC) from the CMS NDC-HCPCS crosswalk "
    "for that J-code and effective date."
)
DOC_ID = "medicare_lcd_oncology_iv_biologics"
SECTION = "NDC-HCPCS Mapping Requirements"


def _valid_paraphrase() -> str:
    fragment = " ".join(CLAUSE.split())[:60]  # > 40 chars verbatim
    return (
        f"Claim flagged because the NDC is not in the CMS crosswalk. "
        f'"{fragment}" '
        f"[{DOC_ID} §{SECTION}]"
    )


def test_verify_accepts_valid_paraphrase():
    out = _valid_paraphrase()
    assert p._verify(out, DOC_ID, SECTION, CLAUSE) is True


def test_verify_rejects_missing_citation_marker():
    out = (
        f'A reasonable paraphrase that quotes "{CLAUSE[:80]}" but forgets '
        "to include the citation marker."
    )
    assert p._verify(out, DOC_ID, SECTION, CLAUSE) is False


def test_verify_rejects_marker_without_clause_fragment():
    out = (
        f"A reasonable-looking paraphrase that names the policy [{DOC_ID} "
        f"§{SECTION}] but invents details — no verbatim fragment from the "
        "retrieved clause appears here."
    )
    assert p._verify(out, DOC_ID, SECTION, CLAUSE) is False


def test_verify_rejects_empty_paraphrase():
    assert p._verify("", DOC_ID, SECTION, CLAUSE) is False


def test_verify_handles_short_clause():
    short_clause = "Use UD modifier."
    out = f"Per [{DOC_ID} §{SECTION}], the practice should: Use UD modifier."
    assert p._verify(out, DOC_ID, SECTION, short_clause) is True


def test_paraphrase_queue_skipped_when_flag_off(monkeypatch, pipeline_report):
    """Flag off → all rows record status=skipped; explanation_text untouched."""
    monkeypatch.delenv("OAI_ENABLE_LLM_PARAPHRASE", raising=False)
    from oaifinance.config import GOLD_DIR

    explained = pl.read_parquet(GOLD_DIR / "explained_exceptions.parquet")
    out = p.paraphrase_queue(explained.head(5))
    statuses = set(out["paraphrase_status"].unique().to_list())
    assert statuses == {"skipped"}, f"expected only 'skipped', saw {statuses}"
    assert "paraphrase_text" in out.columns


def test_paraphrase_queue_failed_call_when_ollama_unreachable(monkeypatch, pipeline_report):
    """Flag on but Ollama unreachable → status=failed_call, no exceptions raised."""
    monkeypatch.setenv("OAI_ENABLE_LLM_PARAPHRASE", "1")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:1")  # nothing on this port
    from oaifinance.config import GOLD_DIR

    explained = pl.read_parquet(GOLD_DIR / "explained_exceptions.parquet")
    out = p.paraphrase_queue(explained.head(5))
    statuses = set(out["paraphrase_status"].unique().to_list())
    assert statuses == {"failed_call"}, (
        f"expected 'failed_call' when Ollama unreachable, saw {statuses}"
    )
