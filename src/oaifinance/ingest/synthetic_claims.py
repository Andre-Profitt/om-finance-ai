"""Synthetic oncology claims generator.

Generative model has a latent `is_true_error` state per claim that rules
observe *noisily*. Rules therefore miss cases (low recall) and fire on some
clean claims (false positives). The label `_true_leakage` is defined in
dollars-recoverable terms, so the ML scorer must combine weak signals
(rule flags + billed ratios + payer + biosimilar + magnitude) to rank
candidates better than any single rule.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from oaifinance.config import (
    BRONZE_DIR,
    PAYER_ARCHETYPES,
    RANDOM_SEED,
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

PRACTICE_340B_SHARE = 0.25  # share of practices that are 340B covered entities
CLAIM_340B_PURCHASE_GIVEN_ELIGIBLE = 0.55  # share of eligible practice's claims purchased via 340B
GPO_REBATE_CLAIMED_RATE = 0.88  # share of claims that flow into GPO rebate accrual

COMMERCIAL_PAYERS = ("commercial_national", "commercial_regional")
BIOSIMILAR_CONVERSION_MISS_BUMP = 0.05  # extra error prob on bios-reference commercial claims
BIOSIMILAR_MISSED_REBATE_RATE = (
    0.025  # 2.5% incremental rebate lost on reference when biosim preferred
)
GPO_REBATE_CLAWBACK_RATE = 0.020  # ~2% clawback when 340B + rebate double-dip caught
GPO_CLAWBACK_REALIZED_RATE = (
    0.55  # share of double-dip events that actually result in clawback (noise)
)
BIOSIMILAR_MISS_REALIZED_RATE = (
    0.48  # share of conversion misses that realize recoverable leakage (noise)
)


def _sample_units(rng: np.random.Generator, hcpcs: str, dosage_per_unit_mg: int) -> int:
    """Clinically plausible total-unit count for a single administration."""
    target_mg = {
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
    }
    jitter = rng.normal(1.0, 0.08)
    target = max(1, int(target_mg.get(hcpcs, 100) * jitter))
    return max(1, target // dosage_per_unit_mg)


def generate(
    asp: pl.DataFrame,
    crosswalk: pl.DataFrame,
    n_claims: int = SYNTHETIC_CLAIMS_N,
    seed: int = RANDOM_SEED,
) -> pl.DataFrame:
    rng = np.random.default_rng(seed)

    hcpcs_list = np.array(asp["hcpcs_code"].to_list())
    asp_map = {
        row["hcpcs_code"]: (
            int(row["dosage_per_unit_mg"]),
            float(row["payment_limit_per_unit"]),
            bool(row["biosimilar_reference"]),
        )
        for row in asp.iter_rows(named=True)
    }

    ndc_by_hcpcs: dict[str, list[str]] = {}
    for row in crosswalk.iter_rows(named=True):
        ndc_by_hcpcs.setdefault(row["hcpcs_code"], []).append(str(row["ndc_code"]))
    all_ndcs = np.array(crosswalk["ndc_code"].to_list())
    payers = np.array(PAYER_ARCHETYPES)

    practice_ids = [f"PR-{i:03d}" for i in range(1, 21)]
    practice_340b = {pid: (rng.random() < PRACTICE_340B_SHARE) for pid in practice_ids}

    rows = []
    for i in range(n_claims):
        hcpcs = str(hcpcs_list[rng.integers(0, len(hcpcs_list))])
        dosage_per_unit, asp_rate, is_bios_ref = asp_map[hcpcs]
        payer = str(payers[rng.integers(0, len(payers))])
        practice_id = str(practice_ids[rng.integers(0, len(practice_ids))])
        is_340b_practice = bool(practice_340b[practice_id])
        is_340b_purchased = is_340b_practice and rng.random() < CLAIM_340B_PURCHASE_GIVEN_ELIGIBLE
        gpo_rebate_claimed = rng.random() < GPO_REBATE_CLAIMED_RATE
        gpo_340b_double_dip = is_340b_purchased and gpo_rebate_claimed

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
        ndc: str
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

        if denied:
            paid_total = 0.0
            status = "denied"
            if ndc_mismatch_obs:
                carc_pool = ["coding"]
            elif asp_drift_obs:
                carc_pool = ["prior_auth", "medical_necessity"]
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

        if is_true_error:
            leakage_amount = max(0.0, allowed_total - paid_total)
        else:
            leakage_amount = 0.0

        if biosimilar_conversion_miss and rng.random() < BIOSIMILAR_MISS_REALIZED_RATE:
            leakage_amount += allowed_total * BIOSIMILAR_MISSED_REBATE_RATE
        if gpo_340b_double_dip and rng.random() < GPO_CLAWBACK_REALIZED_RATE:
            leakage_amount += allowed_total * GPO_REBATE_CLAWBACK_RATE

        true_leakage = leakage_amount > LEAKAGE_DOLLAR_THRESHOLD

        service_date = np.datetime64("2026-01-01") + np.timedelta64(int(rng.integers(0, 90)), "D")

        rows.append(
            {
                "claim_id": f"CLM-{i:06d}",
                "service_date": str(service_date),
                "practice_id": practice_id,
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
    print(f"true_leakage rate: {df['_true_leakage'].mean():.1%}")
    print(f"denial rate: {(df['adjudication_status'] == 'denied').mean():.1%}")
