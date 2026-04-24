"""Paths, constants, and deterministic seeds."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_ROOT = REPO_ROOT / "data"
SAMPLES_DIR = DATA_ROOT / "samples"
BRONZE_DIR = DATA_ROOT / "bronze"
SILVER_DIR = DATA_ROOT / "silver"
GOLD_DIR = DATA_ROOT / "gold"
SYNTHETIC_DIR = DATA_ROOT / "synthetic"

ARTIFACTS_DIR = REPO_ROOT / "artifacts"
MLRUNS_DIR = REPO_ROOT / "mlruns"

RANDOM_SEED = 20260424
SYNTHETIC_CLAIMS_N = 5000

ONCOLOGY_HCPCS = [
    "J9035",  # bevacizumab
    "J9299",  # nivolumab
    "J9312",  # rituximab
    "J9228",  # ipilimumab
    "J9145",  # daratumumab
    "J9173",  # durvalumab
    "J9271",  # pembrolizumab
    "J9317",  # trastuzumab deruxtecan
    "J9144",  # daratumumab-hyaluronidase
    "J9042",  # brentuximab vedotin
]

PAYER_ARCHETYPES = [
    "medicare_ffs",
    "commercial_national",
    "commercial_regional",
    "medicaid_managed",
]

REVIEWER_REVIEW_MINUTES = 5.0
REVIEWER_LOADED_HOURLY = 75_000 / 1_800

MODEL_NAME = "rev_integrity.risk_scorer"
MLFLOW_EXPERIMENT = "om_finance_revenue_integrity"


def ensure_dirs() -> None:
    for d in (BRONZE_DIR, SILVER_DIR, GOLD_DIR, SYNTHETIC_DIR, ARTIFACTS_DIR, MLRUNS_DIR):
        d.mkdir(parents=True, exist_ok=True)
