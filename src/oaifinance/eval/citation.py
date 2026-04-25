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
    "gpo_340b_rebate_excluded": {
        ("gpo_master_oncology_rebate", "Exclusions and Exceptions"),
        ("gpo_master_oncology_rebate", "Rebate Percentages"),
        ("medicaid_managed_specialty_pharmacy", "340B Interaction"),
    },
    "biosimilar_conversion_miss": {
        (
            "commercial_national_nccn_compendium",
            "Biosimilar Substitution and Reference Product Requirements",
        ),
        ("gpo_biosimilar_conversion", "Purpose"),
        ("gpo_biosimilar_conversion", "Conversion Targets and Incentives"),
        ("gpo_biosimilar_conversion", "Reference-Product Audit"),
        ("gpo_biosimilar_conversion", "Data Reporting"),
        (
            "commercial_regional_prior_auth_oncology",
            "Formulary Tier and Step Therapy",
        ),
    },
    "chargeback_validity_fail": {
        ("gpo_chargeback_validation", "Validation Logic"),
        ("gpo_chargeback_validation", "Submission Requirements"),
        ("gpo_chargeback_validation", "Scope"),
        ("gpo_master_oncology_rebate", "Exclusions and Exceptions"),
        ("commercial_national_nccn_compendium", "Billed Amount Review"),
    },
    "access_pa_gap": {
        ("commercial_national_prior_auth_workflow", "Prior Authorization Requirement"),
        ("commercial_national_prior_auth_workflow", "Required Documentation"),
        ("commercial_national_prior_auth_workflow", "Expected Determination Timeline"),
        ("commercial_national_prior_auth_workflow", "Access Delay Financial Impact"),
        ("commercial_national_prior_auth_workflow", "Appeal Path for PA Denials"),
        ("commercial_regional_prior_auth_oncology", "Prior Authorization Required"),
        ("medicare_lcd_oncology_iv_biologics", "Prior Authorization"),
        ("medicaid_managed_specialty_pharmacy", "Timely Filing and Appeals"),
        ("uhc_oncology_specialty_drug_policy", "Prior Authorization"),
        ("bcbs_state_oncology_pa_workflow", "Prior Authorization Required"),
        ("bcbs_state_oncology_pa_workflow", "Required Documentation"),
        ("bcbs_state_oncology_pa_workflow", "Access-Delay Tracking"),
        ("medicare_advantage_oncology_coverage", "Prior Authorization"),
        ("medicare_advantage_oncology_coverage", "Step Therapy Under Part B"),
    },
}

# V2 corpus expansion (B1 + B2): newly admissible citations for existing types.
# Added inline to keep the golden map authoritative as one structure.
GOLDEN_CITATIONS["biosimilar_conversion_miss"] |= {
    ("uhc_oncology_specialty_drug_policy", "Biosimilar Tier and Step Therapy"),
    ("aetna_oncology_step_therapy", "Step Therapy Sequence"),
    ("aetna_oncology_step_therapy", "Conversion Reporting"),
    ("aetna_oncology_step_therapy", "Reference-Product Audit"),
}
GOLDEN_CITATIONS["chargeback_validity_fail"] |= {
    ("gpo_specialty_distribution_addendum", "Substitution Rules"),
    ("gpo_payer_class_pricing", "Validation Logic"),
    ("gpo_payer_class_pricing", "Differential Pricing"),
}
GOLDEN_CITATIONS["ndc_hcpcs_mismatch"] |= {
    ("uhc_oncology_specialty_drug_policy", "Coding and NDC Validation"),
    ("bcbs_state_oncology_pa_workflow", "NDC-HCPCS Coding Validation"),
    ("medicare_advantage_oncology_coverage", "NDC-HCPCS Validation"),
}
GOLDEN_CITATIONS["denial"] |= {
    ("medicare_advantage_oncology_coverage", "Determinations and Appeals"),
    ("aetna_oncology_step_therapy", "Appeal Path"),
}
GOLDEN_CITATIONS["underpayment"] |= {
    ("bcbs_state_oncology_pa_workflow", "Site of Care"),
    ("uhc_oncology_specialty_drug_policy", "Coverage and Site of Service"),
}
GOLDEN_CITATIONS["gpo_340b_rebate_excluded"] |= {
    ("gpo_payer_class_pricing", "Payer Class Definitions"),
}
GOLDEN_CITATIONS["jw_drug_waste"] = {
    ("medicare_jw_drug_waste_policy", "JW Modifier Requirement"),
    ("medicare_jw_drug_waste_policy", "Documentation"),
    ("medicare_jw_drug_waste_policy", "Audit Exposure"),
    ("medicare_jw_drug_waste_policy", "JZ Modifier (No Waste)"),
    ("medicare_jw_drug_waste_policy", "Practice-Level Optimization"),
    ("gpo_inventory_management_addendum", "JW Modifier Compliance"),
    ("gpo_inventory_management_addendum", "Vial-Size Optimization"),
    ("gpo_inventory_management_addendum", "Waste Cost Allocation"),
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
