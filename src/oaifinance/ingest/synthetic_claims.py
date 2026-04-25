"""Synthetic specialty-care claims generator.

Covers oncology + multispecialty (retinal, rheumatology, gastroenterology,
neurology) practices. Generative model has a latent `is_true_error` state
per claim that rules observe *noisily*, so rules miss cases (low recall) and
fire on some clean claims (false positives). The ML scorer must combine weak
signals (rule flags + billed ratios + payer + magnitude + specialty) to rank
candidates better than any single rule.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from oaifinance.config import (
    BRONZE_DIR,
    PAYER_ARCHETYPES,
    PRACTICE_SPECIALTY_DISTRIBUTION,
    RANDOM_SEED,
    SPECIALTIES,
    SYNTHETIC_CLAIMS_N,
    SYNTHETIC_DIR,
)

PAYER_BASE_ERROR = {
    "medicare_ffs": 0.025,
    "commercial_national": 0.055,
    "commercial_regional": 0.085,
    "medicaid_managed": 0.13,
}

CLEAN_DENIAL_RATE = {
    "medicare_ffs": 0.010,
    "commercial_national": 0.025,
    "commercial_regional": 0.040,
    "medicaid_managed": 0.060,
}

ERROR_OBS_PROB = {
    "asp_drift_true": 0.45,
    "asp_drift_false": 0.02,
    "ndc_mismatch_true": 0.35,
    "ndc_mismatch_false": 0.015,
    "denied_given_error": 0.55,
    "denied_given_error_drift": 0.20,
    "denied_given_error_mismatch": 0.25,
}

# Access / prior-auth dynamics — PA is payer-side and specialty-sensitive.
PA_REQUIRED_RATE = {
    "medicare_ffs": 0.05,
    "commercial_national": 0.85,
    "commercial_regional": 0.90,
    "medicaid_managed": 0.70,
}
PA_ON_FILE_GIVEN_REQUIRED = 0.88  # practice remembers to submit PA 88% of the time
PA_GAP_DENIAL_PROB = 0.75  # when PA required and not on file → claim denied with CO-197

CARC_CODES = {
    "prior_auth": "CO-197",
    "medical_necessity": "CO-50",
    "coding": "CO-16",
    "coverage": "PR-204",
    "duplicate": "CO-18",
    "bundled": "CO-97",
    "timely": "CO-29",
}

LEAKAGE_DOLLAR_THRESHOLD = 200.0
PA_DELAY_COST_PER_CLAIM = 85.0  # modeled per-claim operational impact when PA delay occurs

PRACTICE_340B_SHARE = 0.25
CLAIM_340B_PURCHASE_GIVEN_ELIGIBLE = 0.55
GPO_REBATE_CLAIMED_RATE = 0.88

COMMERCIAL_PAYERS = ("commercial_national", "commercial_regional")
BIOSIMILAR_CONVERSION_MISS_BUMP = 0.05
BIOSIMILAR_MISSED_REBATE_RATE = 0.025
GPO_REBATE_CLAWBACK_RATE = 0.020
GPO_CLAWBACK_REALIZED_RATE = 0.55
BIOSIMILAR_MISS_REALIZED_RATE = 0.48

# Clinically plausible total-mg target per admin by HCPCS — covers oncology
# and multispecialty.
HCPCS_TARGET_MG = {
    # Oncology
    "J9035": 400,
    "J9299": 480,
    "J9312": 700,
    "J9228": 240,
    "J9145": 1600,
    "J9173": 1500,
    "J9271": 200,
    "J9317": 400,
    "J9144": 1800,
    "J9042": 180,
    # Retinal (aflibercept 2mg per injection; dosed per-eye)
    "J0178": 4,
    # Rheumatology (golimumab IV 100mg)
    "J1602": 100,
    # Gastroenterology (ustekinumab IV ~260mg then SC ~90mg maintenance)
    "J3357": 130,
    # Neurology (ocrelizumab 600mg every 6 months)
    "J1559": 300,
    # Oncology second-line + multispecialty additions (C2 expansion)
    "J9023": 1200,  # atezolizumab Tecentriq 1200mg q3w
    "J1745": 375,  # infliximab 5 mg/kg ~75kg
    "J3380": 300,  # vedolizumab Entyvio 300mg q8w
    "J2323": 300,  # natalizumab Tysabri 300mg q4w
}


def _sample_units(rng: np.random.Generator, hcpcs: str, dosage_per_unit_mg: int) -> int:
    jitter = rng.normal(1.0, 0.08)
    target = max(1, int(HCPCS_TARGET_MG.get(hcpcs, 100) * jitter))
    return max(1, target // max(1, dosage_per_unit_mg))


def _assign_specialties(practice_ids: list[str], rng: np.random.Generator) -> dict[str, str]:
    specialties = list(PRACTICE_SPECIALTY_DISTRIBUTION.keys())
    probs = np.array([PRACTICE_SPECIALTY_DISTRIBUTION[s] for s in specialties])
    probs = probs / probs.sum()
    return {pid: str(rng.choice(specialties, p=probs)) for pid in practice_ids}


def generate(
    asp: pl.DataFrame,
    crosswalk: pl.DataFrame,
    n_claims: int = SYNTHETIC_CLAIMS_N,
    seed: int = RANDOM_SEED,
) -> pl.DataFrame:
    rng = np.random.default_rng(seed)

    hcpcs_by_specialty: dict[str, list[str]] = {s: [] for s in SPECIALTIES}
    asp_map: dict[str, tuple[int, float, bool, str]] = {}
    for row in asp.iter_rows(named=True):
        specialty = str(row.get("specialty") or "oncology")
        hcpcs_by_specialty.setdefault(specialty, []).append(row["hcpcs_code"])
        asp_map[row["hcpcs_code"]] = (
            int(row["dosage_per_unit_mg"]),
            float(row["payment_limit_per_unit"]),
            bool(row["biosimilar_reference"]),
            specialty,
        )

    ndc_by_hcpcs: dict[str, list[str]] = {}
    for row in crosswalk.iter_rows(named=True):
        ndc_by_hcpcs.setdefault(row["hcpcs_code"], []).append(str(row["ndc_code"]))
    all_ndcs = np.array(crosswalk["ndc_code"].to_list())
    payers = np.array(PAYER_ARCHETYPES)

    practice_ids = [f"PR-{i:03d}" for i in range(1, 21)]
    practice_specialty = _assign_specialties(practice_ids, rng)
    practice_340b = {pid: rng.random() < PRACTICE_340B_SHARE for pid in practice_ids}

    rows = []
    for i in range(n_claims):
        practice_id = str(practice_ids[rng.integers(0, len(practice_ids))])
        specialty = practice_specialty[practice_id]
        hcpcs_pool = hcpcs_by_specialty.get(specialty) or hcpcs_by_specialty["oncology"]
        hcpcs = str(hcpcs_pool[rng.integers(0, len(hcpcs_pool))])

        dosage_per_unit, asp_rate, is_bios_ref, drug_specialty = asp_map[hcpcs]
        payer = str(payers[rng.integers(0, len(payers))])
        is_340b_practice = bool(practice_340b[practice_id])
        is_340b_purchased = is_340b_practice and rng.random() < CLAIM_340B_PURCHASE_GIVEN_ELIGIBLE
        gpo_rebate_claimed = rng.random() < GPO_REBATE_CLAIMED_RATE
        gpo_340b_double_dip = is_340b_purchased and gpo_rebate_claimed

        pa_required = rng.random() < PA_REQUIRED_RATE[payer]
        pa_on_file = (not pa_required) or (rng.random() < PA_ON_FILE_GIVEN_REQUIRED)
        pa_gap = pa_required and not pa_on_file

        units = _sample_units(rng, hcpcs, dosage_per_unit)

        base_error = PAYER_BASE_ERROR[payer] + (0.04 if is_bios_ref else 0.0)
        if is_bios_ref and payer in COMMERCIAL_PAYERS:
            base_error += BIOSIMILAR_CONVERSION_MISS_BUMP
        is_true_error = rng.random() < base_error
        biosimilar_conversion_miss = is_true_error and is_bios_ref and payer in COMMERCIAL_PAYERS

        billed_jitter = rng.normal(1.18, 0.06)
        billed_per_unit = asp_rate * max(1.0, billed_jitter)

        asp_drift_obs = False
        if is_true_error and rng.random() < ERROR_OBS_PROB["asp_drift_true"]:
            billed_per_unit *= rng.uniform(1.6, 2.4)
            asp_drift_obs = True
        elif (not is_true_error) and rng.random() < ERROR_OBS_PROB["asp_drift_false"]:
            billed_per_unit *= rng.uniform(1.55, 2.0)
            asp_drift_obs = True

        valid_ndcs = ndc_by_hcpcs.get(hcpcs, list(all_ndcs))
        wrong_pool = [n for n in all_ndcs.tolist() if n not in valid_ndcs]
        ndc_mismatch_obs = False
        if is_true_error and rng.random() < ERROR_OBS_PROB["ndc_mismatch_true"] and wrong_pool:
            ndc = str(wrong_pool[rng.integers(0, len(wrong_pool))])
            ndc_mismatch_obs = True
        elif (
            (not is_true_error)
            and rng.random() < ERROR_OBS_PROB["ndc_mismatch_false"]
            and wrong_pool
        ):
            ndc = str(wrong_pool[rng.integers(0, len(wrong_pool))])
            ndc_mismatch_obs = True
        else:
            ndc = str(valid_ndcs[rng.integers(0, len(valid_ndcs))])

        allowed_per_unit = asp_rate * rng.uniform(1.04, 1.08)
        billed_total = round(billed_per_unit * units, 2)
        allowed_total = round(allowed_per_unit * units, 2)

        if pa_gap and rng.random() < PA_GAP_DENIAL_PROB:
            denied = True
            denial_reason_pa = True
        else:
            if is_true_error:
                p = ERROR_OBS_PROB["denied_given_error"]
                if asp_drift_obs:
                    p += ERROR_OBS_PROB["denied_given_error_drift"]
                if ndc_mismatch_obs:
                    p += ERROR_OBS_PROB["denied_given_error_mismatch"]
                denial_prob = min(0.95, p)
            else:
                denial_prob = CLEAN_DENIAL_RATE[payer]
            denied = rng.random() < denial_prob
            denial_reason_pa = False

        if denied:
            paid_total = 0.0
            status = "denied"
            if denial_reason_pa:
                carc = CARC_CODES["prior_auth"]
            elif ndc_mismatch_obs:
                carc = CARC_CODES["coding"]
            elif asp_drift_obs:
                carc_pool = ["prior_auth", "medical_necessity"]
                carc = CARC_CODES[str(carc_pool[rng.integers(0, len(carc_pool))])]
            else:
                carc_pool = list(CARC_CODES.keys())
                carc = CARC_CODES[str(carc_pool[rng.integers(0, len(carc_pool))])]
        else:
            if is_true_error:
                paid_total = round(allowed_total * rng.uniform(0.55, 0.92), 2)
            else:
                paid_total = round(allowed_total * rng.uniform(0.98, 1.005), 2)
            status = "paid"
            carc = None

        if is_true_error or denial_reason_pa:
            leakage_amount = max(0.0, allowed_total - paid_total)
        else:
            leakage_amount = 0.0

        if biosimilar_conversion_miss and rng.random() < BIOSIMILAR_MISS_REALIZED_RATE:
            leakage_amount += allowed_total * BIOSIMILAR_MISSED_REBATE_RATE
        if gpo_340b_double_dip and rng.random() < GPO_CLAWBACK_REALIZED_RATE:
            leakage_amount += allowed_total * GPO_REBATE_CLAWBACK_RATE

        access_delay_cost = PA_DELAY_COST_PER_CLAIM if pa_gap else 0.0

        true_leakage = leakage_amount > LEAKAGE_DOLLAR_THRESHOLD

        service_date = np.datetime64("2026-01-01") + np.timedelta64(int(rng.integers(0, 90)), "D")

        rows.append(
            {
                "claim_id": f"CLM-{i:06d}",
                "service_date": str(service_date),
                "practice_id": practice_id,
                "practice_specialty": specialty,
                "drug_specialty": drug_specialty,
                "hcpcs_code": hcpcs,
                "ndc_code": ndc,
                "payer": payer,
                "units": int(units),
                "billed_per_unit": round(float(billed_per_unit), 4),
                "billed_total": float(billed_total),
                "allowed_total": float(allowed_total),
                "paid_total": float(paid_total),
                "adjudication_status": status,
                "carc_code": carc,
                "asp_rate_at_service": float(asp_rate),
                "is_biosimilar_reference": bool(is_bios_ref),
                "is_340b_practice": bool(is_340b_practice),
                "is_340b_purchased": bool(is_340b_purchased),
                "gpo_rebate_claimed": bool(gpo_rebate_claimed),
                "gpo_340b_double_dip": bool(gpo_340b_double_dip),
                "biosimilar_conversion_miss": bool(biosimilar_conversion_miss),
                "pa_required": bool(pa_required),
                "pa_on_file": bool(pa_on_file),
                "pa_gap": bool(pa_gap),
                "denial_reason_pa": bool(denial_reason_pa),
                "access_delay_cost": float(access_delay_cost),
                "_true_leakage_amount": round(float(leakage_amount), 2),
                "_true_leakage": bool(true_leakage),
            }
        )

    df = pl.DataFrame(rows).with_columns(
        pl.col("service_date").str.strptime(pl.Date, "%Y-%m-%d"),
    )
    return df


def ingest(
    asp: pl.DataFrame | None = None,
    crosswalk: pl.DataFrame | None = None,
    n_claims: int = SYNTHETIC_CLAIMS_N,
    seed: int = RANDOM_SEED,
) -> pl.DataFrame:
    if asp is None:
        asp = pl.read_parquet(BRONZE_DIR / "asp_raw.parquet")
    if crosswalk is None:
        crosswalk = pl.read_parquet(BRONZE_DIR / "ndc_hcpcs_raw.parquet")

    df = generate(asp, crosswalk, n_claims=n_claims, seed=seed)

    SYNTHETIC_DIR.mkdir(parents=True, exist_ok=True)
    BRONZE_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(SYNTHETIC_DIR / "claims.parquet")
    df.write_parquet(BRONZE_DIR / "claims_raw.parquet")
    return df


if __name__ == "__main__":
    from oaifinance.ingest.cms_asp import ingest as ingest_asp
    from oaifinance.ingest.ndc_hcpcs import ingest as ingest_crosswalk

    a = ingest_asp()
    c = ingest_crosswalk()
    df = ingest(a, c)
    print(f"generated {len(df)} claims")
    print(df.group_by("practice_specialty").len().sort("len", descending=True))
    print(f"pa_gap rate: {df['pa_gap'].mean():.1%}")
    print(f"denial_reason_pa: {df['denial_reason_pa'].sum()}")
