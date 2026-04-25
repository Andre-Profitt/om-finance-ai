"""Evidence-grounded exception explainer with citation enforcement and abstention.

For each scored exception, builds a retrieval query keyed on exception_type +
payer + hcpcs, runs the retriever, and produces a template-based explanation
that quotes the top chunk only if its similarity clears the threshold.
Otherwise the system ABSTAINS — a first-class product outcome that a
controllership-ready AI must support.

No LLM is invoked. Natural-language paraphrasing via Ollama or Azure OpenAI is
a v3 concern; the citation mechanism (retrieve → threshold → quote or abstain)
is the auditability-critical part and is demonstrated here deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from oaifinance.config import GOLD_DIR
from oaifinance.rag.retriever import Retriever, RetrievalHit

SIMILARITY_THRESHOLD = 0.64
MAX_QUOTE_CHARS = 420

QUERY_TEMPLATES = {
    "ndc_hcpcs_mismatch": (
        "NDC does not match the HCPCS J-code in the CMS NDC-HCPCS crosswalk; "
        "coding error on claim billed to {payer} for {hcpcs}"
    ),
    "asp_drift": (
        "billed amount per unit materially exceeds the Medicare Part B ASP payment "
        "limit for HCPCS {hcpcs} on claim to {payer}"
    ),
    "denial": (
        "claim denied by {payer} for HCPCS {hcpcs}; appeal process, medical "
        "necessity, prior authorization requirements"
    ),
    "underpayment": (
        "Contract underpayment: {payer} paid less than the contract-allowed amount "
        "on HCPCS {hcpcs}; site-of-care reduced reimbursement, preferred-site "
        "allowable, contractual payment methodology"
    ),
    "gpo_340b_rebate_excluded": (
        "GPO rebate accrued on a 340B-purchased drug; duplicate discount between "
        "340B ceiling price and GPO rebate; exclusion from rebate eligibility for "
        "covered entity claims"
    ),
    "biosimilar_conversion_miss": (
        "Reference biologic billed when biosimilar is payer-preferred; biosimilar "
        "substitution required under formulary and conversion addendum; "
        "reference-product utilization audit"
    ),
    "chargeback_validity_fail": (
        "Chargeback submission with billed-per-unit variance above ASP threshold; "
        "validation rejection under variance reason code; audit of submission "
        "requirements"
    ),
    "access_pa_gap": (
        "Prior authorization required for specialty drug {hcpcs} on {payer}; "
        "PA documentation missing or not on file; claim denied with CO-197 "
        "pending authorization; access delay and expected determination "
        "timeline"
    ),
    "jw_drug_waste": (
        "JW modifier required for single-dose container drug {hcpcs}; "
        "waste reporting; CMS Medicare Claims Processing Manual; vial-size "
        "optimization; audit exposure on missing JW or JZ modifier"
    ),
}

EXPLANATION_TEMPLATES = {
    "ndc_hcpcs_mismatch": (
        "Claim {claim_id} billed HCPCS {hcpcs} with NDC {ndc}, which is not in the "
        "CMS NDC-HCPCS crosswalk for {hcpcs}. Per {doc_title} §{section_title}: "
        '"{quote}" Expected outcome: {payer} will deny with CO-16. Action: '
        "resubmit corrected claim with a crosswalk-valid NDC or escalate to coding."
    ),
    "asp_drift": (
        "Claim {claim_id} billed {hcpcs} at ${billed_per_unit:.2f}/unit, "
        "approximately {ratio:.2f}× the Medicare ASP payment limit of "
        '${asp_rate:.2f}. Per {doc_title} §{section_title}: "{quote}" Dollars '
        "at risk on this line: ${dollars_at_risk:,.0f}. Action: confirm billed "
        "amount against acquisition cost and ASP for the service quarter."
    ),
    "denial": (
        "Claim {claim_id} for HCPCS {hcpcs} billed to {payer} was denied with "
        'CARC {carc}. Per {doc_title} §{section_title}: "{quote}" Dollars at '
        "risk if not appealed: ${dollars_at_risk:,.0f}. Action: route to "
        "appeals queue with medical-necessity documentation."
    ),
    "underpayment": (
        "Claim {claim_id} for {hcpcs} billed to {payer} was paid at "
        "{paid_ratio:.1%} of allowed amount. Per {doc_title} §{section_title}: "
        '"{quote}" Variance: ${dollars_at_risk:,.0f}. Action: request '
        "reconsideration citing contract reimbursement methodology."
    ),
    "jw_drug_waste": (
        "Claim {claim_id} for HCPCS {hcpcs} ({payer}) is for a single-dose "
        "container drug but the JW (or JZ) modifier is not on file. Per "
        '{doc_title} §{section_title}: "{quote}" Audit-recovery exposure: '
        "${dollars_at_risk:,.0f}. Action: append JW with documented discarded "
        "amount, or JZ if no waste, then resubmit."
    ),
}

ABSTENTION_REASON = (
    "No policy or contract clause in the current corpus exceeded the similarity "
    "threshold ({threshold:.2f}); best candidate was {best_doc_id} §{best_section} "
    "at similarity {best_score:.2f}. Routing to human reviewer without a "
    "model-generated explanation."
)


@dataclass
class Explanation:
    exception_id: str
    explained: bool
    abstained: bool
    citation_doc_id: str | None
    citation_section: str | None
    citation_score: float
    retrieved_top_k: list[str]
    explanation_text: str


def _clip(text: str, n: int = MAX_QUOTE_CHARS) -> str:
    t = " ".join(text.split())
    return t if len(t) <= n else t[: n - 1] + "…"


def explain_one(row: dict, retriever: Retriever) -> Explanation:
    exc_type = row["exception_type"]
    query_tmpl = QUERY_TEMPLATES.get(exc_type, "{hcpcs} {payer} exception")
    query = query_tmpl.format(
        payer=row["payer"],
        hcpcs=row["hcpcs_code"],
    )
    hits = retriever.search(query, top_k=5)
    top_k_ids = [h.chunk_id for h in hits]

    best: RetrievalHit | None = hits[0] if hits else None
    if best is None or best.score < SIMILARITY_THRESHOLD:
        reason = ABSTENTION_REASON.format(
            threshold=SIMILARITY_THRESHOLD,
            best_doc_id=best.doc_id if best else "none",
            best_section=best.section_title if best else "none",
            best_score=best.score if best else 0.0,
        )
        return Explanation(
            exception_id=row["claim_id"],
            explained=False,
            abstained=True,
            citation_doc_id=best.doc_id if best else None,
            citation_section=best.section_title if best else None,
            citation_score=best.score if best else 0.0,
            retrieved_top_k=top_k_ids,
            explanation_text=reason,
        )

    tmpl = EXPLANATION_TEMPLATES.get(exc_type)
    if tmpl is None:
        text = (
            f"Exception flagged ({exc_type}) on claim {row['claim_id']}. "
            f"Supporting evidence from {best.doc_title} §{best.section_title}: "
            f'"{_clip(best.text)}"'
        )
    else:
        allowed = float(row.get("allowed_total") or 0.0)
        paid = float(row.get("paid_total") or 0.0)
        paid_ratio = paid / allowed if allowed > 0 else 0.0
        billed_per_unit = float(row.get("billed_per_unit") or 0.0)
        asp_rate = float(row.get("asp_rate_at_service") or 0.0)
        ratio = billed_per_unit / asp_rate if asp_rate > 0 else 0.0

        text = tmpl.format(
            claim_id=row["claim_id"],
            hcpcs=row["hcpcs_code"],
            ndc=row.get("ndc_code", "unknown"),
            payer=row["payer"],
            carc=row.get("carc_code") or "unspecified",
            doc_title=best.doc_title,
            section_title=best.section_title,
            quote=_clip(best.text),
            billed_per_unit=billed_per_unit,
            asp_rate=asp_rate,
            ratio=ratio,
            paid_ratio=paid_ratio,
            dollars_at_risk=float(row.get("dollars_at_risk") or 0.0),
        )

    return Explanation(
        exception_id=row["claim_id"],
        explained=True,
        abstained=False,
        citation_doc_id=best.doc_id,
        citation_section=best.section_title,
        citation_score=best.score,
        retrieved_top_k=top_k_ids,
        explanation_text=text,
    )


def explain_all(
    scored: pl.DataFrame | None = None,
    retriever: Retriever | None = None,
) -> pl.DataFrame:
    if scored is None:
        scored = pl.read_parquet(GOLD_DIR / "scored_exceptions.parquet")
    if retriever is None:
        from oaifinance.rag.retriever import build as build_retriever

        retriever = build_retriever()

    out_rows = []
    for row in scored.iter_rows(named=True):
        exp = explain_one(row, retriever)
        out_rows.append(
            {
                "claim_id": exp.exception_id,
                "explained": exp.explained,
                "abstained": exp.abstained,
                "citation_doc_id": exp.citation_doc_id,
                "citation_section": exp.citation_section,
                "citation_score": exp.citation_score,
                "retrieved_top_k": ",".join(exp.retrieved_top_k),
                "explanation_text": exp.explanation_text,
            }
        )

    expl = pl.DataFrame(out_rows)
    enriched = scored.join(expl, on="claim_id", how="left")

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    enriched.write_parquet(GOLD_DIR / "explained_exceptions.parquet")
    return enriched


if __name__ == "__main__":
    df = explain_all()
    print(f"explained: {df['explained'].sum()}  abstained: {df['abstained'].sum()}")
    shown = df.filter(pl.col("explained")).sort("risk_score", descending=True).head(3)
    for row in shown.iter_rows(named=True):
        print(f"\n[{row['exception_type']}] {row['claim_id']}")
        print(row["explanation_text"])
