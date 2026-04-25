"""Rubric-scoring tests for the LLM paraphrase A/B harness (Track C1)."""

from __future__ import annotations

from oaifinance.eval.paraphrase_eval import (
    evaluate_row,
    scorecard,
    to_dataframe,
)


CLAUSE = (
    "Every claim for a drug billed under an HCPCS J-code MUST include a "
    "corresponding National Drug Code (NDC) from the CMS NDC-HCPCS crosswalk."
)
DOC = "medicare_lcd_oncology_iv_biologics"
SEC = "NDC-HCPCS Mapping Requirements"


def _good_paraphrase() -> str:
    fragment = " ".join(CLAUSE.split())[:60]
    return (
        "Claim CLM-1 billed at $4,500 was denied with CO-16 because the NDC "
        "is not in the CMS crosswalk. "
        f'"{fragment}" '
        f"[{DOC} §{SEC}]"
    )


def test_good_paraphrase_scores_high():
    row = evaluate_row(
        model_name="qwen-7b",
        claim_id="CLM-1",
        template_text="(template)",
        paraphrase_text=_good_paraphrase(),
        paraphrase_status="ok",
        citation_doc_id=DOC,
        citation_section=SEC,
        citation_clause=CLAUSE,
        expected_numbers=[4500],
    )
    assert row.composite_score >= 0.75
    dims = {it.dimension: it.score for it in row.items}
    assert dims["citation_fidelity"] == "yes"
    assert dims["abstention_compliance"] == "yes"


def test_invented_dollar_fails_numerical():
    bad = (
        "Claim CLM-1 billed at $4,500 plus an unrelated $99,999 charge. "
        f'"{CLAUSE[:50]}" [{DOC} §{SEC}]'
    )
    row = evaluate_row(
        model_name="qwen-7b",
        claim_id="CLM-1",
        template_text="(template)",
        paraphrase_text=bad,
        paraphrase_status="ok",
        citation_doc_id=DOC,
        citation_section=SEC,
        citation_clause=CLAUSE,
        expected_numbers=[4500],
    )
    nums = next(it for it in row.items if it.dimension == "numerical_accuracy")
    assert nums.score == "no"


def test_missing_marker_fails_citation():
    no_marker = f'"{CLAUSE[:50]}" — but no citation marker is present.'
    row = evaluate_row(
        model_name="qwen-7b",
        claim_id="CLM-1",
        template_text="(template)",
        paraphrase_text=no_marker,
        paraphrase_status="ok",
        citation_doc_id=DOC,
        citation_section=SEC,
        citation_clause=CLAUSE,
        expected_numbers=[],
    )
    cit = next(it for it in row.items if it.dimension == "citation_fidelity")
    assert cit.score in {"no", "partial"}


def test_failed_verify_with_text_is_contract_violation():
    """The load-bearing invariant: failed_verify must NOT publish text."""
    row = evaluate_row(
        model_name="bad-model",
        claim_id="CLM-1",
        template_text="(template)",
        paraphrase_text=_good_paraphrase(),  # text present
        paraphrase_status="failed_verify",  # but status says fail
        citation_doc_id=DOC,
        citation_section=SEC,
        citation_clause=CLAUSE,
        expected_numbers=[4500],
    )
    abst = next(it for it in row.items if it.dimension == "abstention_compliance")
    assert abst.score == "no"
    assert "CONTRACT VIOLATION" in abst.rationale


def test_skipped_status_compliant_when_no_text():
    row = evaluate_row(
        model_name="(flag-off)",
        claim_id="CLM-1",
        template_text="(template)",
        paraphrase_text=None,
        paraphrase_status="skipped",
        citation_doc_id=DOC,
        citation_section=SEC,
        citation_clause=CLAUSE,
        expected_numbers=[],
    )
    abst = next(it for it in row.items if it.dimension == "abstention_compliance")
    assert abst.score == "yes"


def test_emoji_in_paraphrase_dings_tone():
    out = f'Claim flagged 🎯 — billed $4,500. "{CLAUSE[:50]}" [{DOC} §{SEC}]'
    row = evaluate_row(
        model_name="emoji-model",
        claim_id="CLM-1",
        template_text="(template)",
        paraphrase_text=out,
        paraphrase_status="ok",
        citation_doc_id=DOC,
        citation_section=SEC,
        citation_clause=CLAUSE,
        expected_numbers=[4500],
    )
    tone = next(it for it in row.items if it.dimension == "tone_appropriateness")
    assert tone.score in {"partial", "no"}


def test_scorecard_aggregates_correctly():
    rows = [
        evaluate_row(
            model_name="qwen-7b",
            claim_id=f"CLM-{i}",
            template_text="(template)",
            paraphrase_text=_good_paraphrase(),
            paraphrase_status="ok",
            citation_doc_id=DOC,
            citation_section=SEC,
            citation_clause=CLAUSE,
            expected_numbers=[4500],
        )
        for i in range(5)
    ]
    sc = scorecard(rows)
    assert sc.model_name == "qwen-7b"
    assert sc.n_evaluated == 5
    assert sc.n_explained == 5
    assert sc.composite_mean >= 0.75
    df = to_dataframe(rows)
    assert len(df) == 5
    assert "composite_score" in df.columns
