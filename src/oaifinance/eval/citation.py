"""Citation-precision eval for the RAG explainer.

Golden map: each exception_type has a set of (doc_id, section_title) pairs
that are acceptable citations. Citation precision = share of explained
exceptions whose cited (doc_id, section_title) is in the acceptable set.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from oaifinance.config import GOLD_DIR

GOLDEN_CITATIONS: dict[str, set[tuple[str, str]]] = {
    "ndc_hcpcs_mismatch": {
        ("medicare_lcd_oncology_iv_biologics", "NDC-HCPCS Mapping Requirements"),
        ("commercial_regional_prior_auth_oncology", "NDC-HCPCS Validation"),
        ("medicaid_managed_specialty_pharmacy", "Claim Submission and NDC-HCPCS"),
        ("gpo_chargeback_validation", "Validation Logic"),
    },
    "asp_drift": {
        ("medicare_lcd_oncology_iv_biologics", "J-code Billing and Units"),
        ("commercial_national_nccn_compendium", "Billed Amount Review"),
        ("gpo_chargeback_validation", "Validation Logic"),
        ("gpo_master_oncology_rebate", "Exclusions and Exceptions"),
    },
    "denial": {
        ("medicare_lcd_oncology_iv_biologics", "Denials and Appeal Process"),
        ("commercial_regional_prior_auth_oncology", "Prior Authorization Required"),
        ("commercial_national_nccn_compendium", "Medical Necessity"),
        (
            "commercial_national_nccn_compendium",
            "Biosimilar Substitution and Reference Product Requirements",
        ),
        ("medicaid_managed_specialty_pharmacy", "Timely Filing and Appeals"),
    },
    "underpayment": {
        ("commercial_regional_prior_auth_oncology", "Administration and Billing Site"),
        ("commercial_national_nccn_compendium", "Site of Care"),
        ("gpo_chargeback_validation", "Validation Logic"),
        ("medicare_lcd_oncology_iv_biologics", "J-code Billing and Units"),
    },
}


@dataclass
class CitationEval:
    n_explained: int
    n_abstained: int
    n_citation_precise: int
    citation_precision: float
    abstention_rate: float
    precision_by_type: dict[str, float]


def evaluate(explained: pl.DataFrame | None = None) -> CitationEval:
    if explained is None:
        explained = pl.read_parquet(GOLD_DIR / "explained_exceptions.parquet")

    n = len(explained)
    n_explained = int(explained["explained"].sum())
    n_abstained = int(explained["abstained"].sum())
    abstention_rate = n_abstained / n if n else 0.0

    explained_rows = explained.filter(pl.col("explained"))
    n_precise = 0
    per_type_correct: dict[str, int] = {}
    per_type_total: dict[str, int] = {}
    for row in explained_rows.iter_rows(named=True):
        et = row["exception_type"]
        golden = GOLDEN_CITATIONS.get(et, set())
        got = (row["citation_doc_id"], row["citation_section"])
        is_correct = got in golden
        per_type_total[et] = per_type_total.get(et, 0) + 1
        if is_correct:
            n_precise += 1
            per_type_correct[et] = per_type_correct.get(et, 0) + 1

    precision_by_type = {
        et: (per_type_correct.get(et, 0) / total) if total else 0.0
        for et, total in per_type_total.items()
    }
    citation_precision = (n_precise / n_explained) if n_explained else 0.0

    return CitationEval(
        n_explained=n_explained,
        n_abstained=n_abstained,
        n_citation_precise=n_precise,
        citation_precision=citation_precision,
        abstention_rate=abstention_rate,
        precision_by_type=precision_by_type,
    )
