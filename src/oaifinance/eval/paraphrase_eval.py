"""LLM paraphrase A/B evaluation harness (Track C1).

The V1 explainer is template-based and the V2 paraphrase layer is gated
behind `OAI_ENABLE_LLM_PARAPHRASE`. This harness scores each model's
paraphrased output against a four-dimension rubric so the V2 model
selection is documented and auditable.

The rubric is intentionally rigid (no free-form judgment) — every score
is yes/no/partial against an explicit checklist. This is the V1 design
decision (see DL-0010); paraphrase quality is downstream of the
auditability contract.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape as html_escape
from typing import Iterable, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

ScoreLevel = Literal["yes", "partial", "no"]


class RubricItem(BaseModel):
    """One scored rubric line on one paraphrase."""

    model_config = ConfigDict(extra="forbid")

    dimension: Literal[
        "numerical_accuracy",
        "citation_fidelity",
        "tone_appropriateness",
        "abstention_compliance",
    ]
    score: ScoreLevel
    rationale: str = Field(min_length=1)


class ParaphraseEvalRow(BaseModel):
    """Per-paraphrase eval record. One per (model, claim_id) cell."""

    model_config = ConfigDict(extra="forbid")

    model_name: str
    claim_id: str
    template_text: str
    paraphrase_text: str | None
    paraphrase_status: str
    citation_doc_id: str | None
    citation_section: str | None
    items: list[RubricItem] = Field(min_length=4, max_length=4)
    composite_score: float = Field(ge=0.0, le=1.0)


@dataclass
class ModelScorecard:
    model_name: str
    n_evaluated: int
    n_explained: int
    n_abstained: int
    composite_mean: float
    by_dimension: dict[str, float]


def _level_to_score(level: ScoreLevel) -> float:
    return {"yes": 1.0, "partial": 0.5, "no": 0.0}[level]


def _score_numerical_accuracy(text: str, expected_numbers: Iterable[float | int]) -> RubricItem:
    """Are dollar amounts and numerical claims correctly preserved?

    Heuristic: every expected number must appear (with thousands separator
    insensitive) in the paraphrase. Missing → partial; multiple missing → no;
    extra invented numbers → no.
    """
    if not text:
        return RubricItem(dimension="numerical_accuracy", score="no", rationale="empty paraphrase")
    normalized = text.replace(",", "")
    expected = list(expected_numbers)
    missing = [n for n in expected if str(int(n)) not in normalized]
    invented = re.findall(r"\$[\d,]+", text)
    invented_clean = [
        s.lstrip("$").replace(",", "")
        for s in invented
        if s.lstrip("$").replace(",", "") not in {str(int(n)) for n in expected}
    ]
    if not missing and not invented_clean:
        return RubricItem(
            dimension="numerical_accuracy",
            score="yes",
            rationale="all expected numbers present, none invented",
        )
    if missing and not invented_clean:
        return RubricItem(
            dimension="numerical_accuracy",
            score="partial" if len(missing) == 1 else "no",
            rationale=f"missing: {missing}",
        )
    return RubricItem(
        dimension="numerical_accuracy",
        score="no",
        rationale=f"invented numbers: {invented_clean}",
    )


def _score_citation_fidelity(
    text: str, doc_id: str | None, section_title: str | None, clause: str
) -> RubricItem:
    """Is the cited (doc, section) referenced AND a clause fragment quoted?"""
    if not text:
        return RubricItem(dimension="citation_fidelity", score="no", rationale="empty paraphrase")
    if not doc_id or not section_title:
        return RubricItem(
            dimension="citation_fidelity",
            score="no",
            rationale="no upstream citation available",
        )
    has_marker = f"[{doc_id}" in text and section_title in text
    clause_compact = " ".join(clause.split())
    fragment_present = False
    for n in range(40, min(len(clause_compact), 80) + 1, 20):
        if clause_compact[:n] in text:
            fragment_present = True
            break
    if has_marker and fragment_present:
        return RubricItem(
            dimension="citation_fidelity",
            score="yes",
            rationale="marker + verbatim fragment present",
        )
    if has_marker or fragment_present:
        return RubricItem(
            dimension="citation_fidelity",
            score="partial",
            rationale="one of marker / fragment present",
        )
    return RubricItem(
        dimension="citation_fidelity",
        score="no",
        rationale="neither marker nor fragment present",
    )


def _score_tone(text: str) -> RubricItem:
    """Reviewer-ready tone: no first-person, no marketing copy, no emoji."""
    if not text:
        return RubricItem(dimension="tone_appropriateness", score="no", rationale="empty")
    bad_signals = []
    if re.search(r"\b(I|we|our|us)\b", text):
        bad_signals.append("first-person pronoun")
    if re.search(r"[!]{2,}|amazing|wonderful|delighted", text, re.I):
        bad_signals.append("marketing tone")
    if re.search(r"[\U0001F300-\U0001FAFF☀-⛿]", text):
        bad_signals.append("emoji")
    if not bad_signals:
        return RubricItem(
            dimension="tone_appropriateness",
            score="yes",
            rationale="reviewer-ready tone",
        )
    if len(bad_signals) == 1:
        return RubricItem(
            dimension="tone_appropriateness",
            score="partial",
            rationale=", ".join(bad_signals),
        )
    return RubricItem(
        dimension="tone_appropriateness", score="no", rationale=", ".join(bad_signals)
    )


def _score_abstention_compliance(status: str, has_text: bool) -> RubricItem:
    """If status is `failed_call` or `failed_verify`, paraphrase_text MUST be None."""
    if status == "ok" and has_text:
        return RubricItem(
            dimension="abstention_compliance",
            score="yes",
            rationale="ok status, paraphrase published",
        )
    if status == "skipped" and not has_text:
        return RubricItem(
            dimension="abstention_compliance",
            score="yes",
            rationale="skipped — flag off, no text published (correct)",
        )
    if status in {"failed_call", "failed_verify"} and not has_text:
        return RubricItem(
            dimension="abstention_compliance",
            score="yes",
            rationale=f"{status} — fell back to template (correct)",
        )
    if status in {"failed_call", "failed_verify"} and has_text:
        return RubricItem(
            dimension="abstention_compliance",
            score="no",
            rationale=f"{status} but paraphrase_text was published — CONTRACT VIOLATION",
        )
    return RubricItem(
        dimension="abstention_compliance",
        score="partial",
        rationale=f"unexpected status={status} text={'present' if has_text else 'absent'}",
    )


def evaluate_row(
    *,
    model_name: str,
    claim_id: str,
    template_text: str,
    paraphrase_text: str | None,
    paraphrase_status: str,
    citation_doc_id: str | None,
    citation_section: str | None,
    citation_clause: str,
    expected_numbers: Iterable[float | int],
) -> ParaphraseEvalRow:
    text = paraphrase_text or ""
    items = [
        _score_numerical_accuracy(text, expected_numbers),
        _score_citation_fidelity(text, citation_doc_id, citation_section, citation_clause),
        _score_tone(text),
        _score_abstention_compliance(paraphrase_status, bool(paraphrase_text)),
    ]
    composite = sum(_level_to_score(i.score) for i in items) / len(items)
    return ParaphraseEvalRow(
        model_name=model_name,
        claim_id=claim_id,
        template_text=template_text,
        paraphrase_text=paraphrase_text,
        paraphrase_status=paraphrase_status,
        citation_doc_id=citation_doc_id,
        citation_section=citation_section,
        items=items,
        composite_score=composite,
    )


def scorecard(rows: list[ParaphraseEvalRow]) -> ModelScorecard:
    if not rows:
        return ModelScorecard("(empty)", 0, 0, 0, 0.0, {})
    model_names = {r.model_name for r in rows}
    if len(model_names) > 1:
        raise ValueError(f"scorecard takes one model at a time; saw {model_names}")
    name = next(iter(model_names))
    by_dim: dict[str, list[float]] = {}
    for r in rows:
        for it in r.items:
            by_dim.setdefault(it.dimension, []).append(_level_to_score(it.score))
    return ModelScorecard(
        model_name=name,
        n_evaluated=len(rows),
        n_explained=sum(1 for r in rows if r.paraphrase_text),
        n_abstained=sum(1 for r in rows if not r.paraphrase_text),
        composite_mean=sum(r.composite_score for r in rows) / len(rows),
        by_dimension={k: sum(v) / len(v) for k, v in by_dim.items()},
    )


def render_scorecards_html(scorecards: list[ModelScorecard]) -> str:
    """Tiny HTML renderer for the writeup. No CSS dep — just a clean table."""
    head = (
        "<table style='border-collapse:collapse;font-family:sans-serif;font-size:0.9em;'>"
        "<thead><tr style='border-bottom:1px solid #ccc;'>"
        "<th style='padding:0.4em 0.7em;text-align:left;'>Model</th>"
        "<th style='padding:0.4em 0.7em;'>n</th>"
        "<th style='padding:0.4em 0.7em;'>Composite</th>"
        "<th style='padding:0.4em 0.7em;'>Numerical</th>"
        "<th style='padding:0.4em 0.7em;'>Citation</th>"
        "<th style='padding:0.4em 0.7em;'>Tone</th>"
        "<th style='padding:0.4em 0.7em;'>Abstention</th>"
        "</tr></thead><tbody>"
    )
    body = []
    for s in scorecards:
        body.append(
            "<tr>"
            f"<td style='padding:0.4em 0.7em;'>{html_escape(s.model_name)}</td>"
            f"<td style='padding:0.4em 0.7em;text-align:right;'>{s.n_evaluated}</td>"
            f"<td style='padding:0.4em 0.7em;text-align:right;'>{s.composite_mean:.2f}</td>"
            f"<td style='padding:0.4em 0.7em;text-align:right;'>{s.by_dimension.get('numerical_accuracy', 0):.2f}</td>"
            f"<td style='padding:0.4em 0.7em;text-align:right;'>{s.by_dimension.get('citation_fidelity', 0):.2f}</td>"
            f"<td style='padding:0.4em 0.7em;text-align:right;'>{s.by_dimension.get('tone_appropriateness', 0):.2f}</td>"
            f"<td style='padding:0.4em 0.7em;text-align:right;'>{s.by_dimension.get('abstention_compliance', 0):.2f}</td>"
            "</tr>"
        )
    return head + "".join(body) + "</tbody></table>"


def to_dataframe(rows: list[ParaphraseEvalRow]) -> pl.DataFrame:
    flat = []
    for r in rows:
        scores = {f"{i.dimension}_score": _level_to_score(i.score) for i in r.items}
        flat.append(
            {
                "model_name": r.model_name,
                "claim_id": r.claim_id,
                "paraphrase_status": r.paraphrase_status,
                "composite_score": r.composite_score,
                **scores,
            }
        )
    return pl.DataFrame(flat)
