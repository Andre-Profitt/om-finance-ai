"""Practice performance & acquisition analytics.

Consumes the upstream scored_exceptions + claims frames to produce per-practice
exposure KPIs and a 100-day integration roadmap projection. The output feeds
the executive Practice Performance & Acquisition memo, so numbers are always
backed by the pipeline's actual output — not prose estimates.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import polars as pl

from oaifinance.config import ARTIFACTS_DIR, BRONZE_DIR, GOLD_DIR

# Initiative projection assumptions. Each initiative maps to the exception
# types whose dollars-at-risk it addresses and the modeled capture rate.
INITIATIVES = [
    {
        "name": "Week 1-4: Revenue Integrity top-100 quick wins",
        "exception_types": [
            "access_pa_gap",
            "ndc_hcpcs_mismatch",
            "asp_drift",
            "underpayment",
            "denial",
        ],
        "capture_rate": 0.45,
        "confidence": 0.80,
    },
    {
        "name": "Week 2-6: Access / Prior-Auth documentation intake",
        "exception_types": ["access_pa_gap"],
        "capture_rate": 0.55,
        "confidence": 0.75,
    },
    {
        "name": "Week 5-10: Specialty Drug Contract Economics reconciliation",
        "exception_types": ["chargeback_validity_fail", "asp_drift"],
        "capture_rate": 0.35,
        "confidence": 0.60,
    },
    {
        "name": "Week 6-12: Biosimilar conversion program",
        "exception_types": ["biosimilar_conversion_miss"],
        "capture_rate": 0.50,
        "confidence": 0.70,
    },
    {
        "name": "Week 8-14: 340B scenario / duplicate-discount governance",
        "exception_types": ["gpo_340b_rebate_excluded"],
        "capture_rate": 0.85,
        "confidence": 0.90,
    },
]

REVIEWER_COST_PER_HOUR = 75_000 / 1_800
AVG_REVIEW_MINUTES = 7.0  # realistic higher than happy-path 5 min


@dataclass
class PracticeSummary:
    practice_id: str
    practice_specialty: str
    is_340b: bool
    n_claims: int
    n_exceptions: int
    exception_rate: float
    total_at_risk: float
    expected_recovery_calibrated: float
    access_delay_cost: float
    exception_mix: dict[str, float]
    payer_mix: dict[str, float]
    top_hcpcs_by_dollars: list[tuple[str, float]]


@dataclass
class InitiativeProjection:
    name: str
    addressable_dollars: float
    projected_recovery: float
    reviewer_hours: float
    reviewer_cost: float
    net_value: float
    confidence: float


@dataclass
class AcquisitionModel:
    target_practice: str
    target_specialty: str
    is_340b_target: bool
    network_summary: dict
    target_summary: dict
    initiatives: list[dict]
    total_projected_recovery_q1: float
    total_projected_reviewer_cost: float
    total_projected_net_value: float
    payback_months_modeled: float = 0.0
    network_specialty_mix: dict[str, float] = field(default_factory=dict)


def _practice_summary(
    practice_id: str, scored: pl.DataFrame, claims: pl.DataFrame
) -> PracticeSummary:
    p_scored = scored.filter(pl.col("practice_id") == practice_id)
    p_claims = claims.filter(pl.col("practice_id") == practice_id)

    n_exceptions = len(p_scored)
    n_claims = len(p_claims)
    exception_rate = n_exceptions / max(n_claims, 1)
    total_at_risk = float(p_scored["dollars_at_risk"].sum()) if n_exceptions else 0.0
    expected_recovery = (
        float(p_scored["expected_recovery_calibrated"].sum()) if n_exceptions else 0.0
    )
    access_delay_cost = float(p_claims["access_delay_cost"].sum()) if n_claims else 0.0

    if n_exceptions:
        mix = p_scored.group_by("exception_type").agg(pl.col("dollars_at_risk").sum().alias("d"))
        exception_mix = {
            row["exception_type"]: float(row["d"]) / max(total_at_risk, 1)
            for row in mix.iter_rows(named=True)
        }
        payer_mix_df = p_scored.group_by("payer").agg(pl.col("dollars_at_risk").sum().alias("d"))
        payer_mix = {
            row["payer"]: float(row["d"]) / max(total_at_risk, 1)
            for row in payer_mix_df.iter_rows(named=True)
        }
        top_hcpcs_df = (
            p_scored.group_by("hcpcs_code")
            .agg(pl.col("dollars_at_risk").sum().alias("d"))
            .sort("d", descending=True)
            .head(3)
        )
        top_hcpcs = [
            (row["hcpcs_code"], float(row["d"])) for row in top_hcpcs_df.iter_rows(named=True)
        ]
    else:
        exception_mix = {}
        payer_mix = {}
        top_hcpcs = []

    specialty = (
        str(p_scored["practice_specialty"][0])
        if n_exceptions
        else str(p_claims["practice_specialty"][0])
        if n_claims
        else "unknown"
    )
    is_340b = (
        bool(p_scored["is_340b_practice"][0])
        if n_exceptions
        else bool(p_claims["is_340b_practice"][0])
        if n_claims
        else False
    )

    return PracticeSummary(
        practice_id=practice_id,
        practice_specialty=specialty,
        is_340b=is_340b,
        n_claims=n_claims,
        n_exceptions=n_exceptions,
        exception_rate=exception_rate,
        total_at_risk=total_at_risk,
        expected_recovery_calibrated=expected_recovery,
        access_delay_cost=access_delay_cost,
        exception_mix=exception_mix,
        payer_mix=payer_mix,
        top_hcpcs_by_dollars=top_hcpcs,
    )


def _project_initiatives(target: PracticeSummary) -> list[InitiativeProjection]:
    projections = []
    for ini in INITIATIVES:
        addressable = sum(
            target.exception_mix.get(et, 0.0) * target.total_at_risk
            for et in ini["exception_types"]
        )
        projected_recovery = addressable * ini["capture_rate"] * ini["confidence"]
        # Reviewer effort scales with addressable dollars / avg claim size.
        # Use a simple proxy: ~40 reviewed items per $1M addressable.
        reviewer_items = max(10, int(addressable / 25_000))
        reviewer_hours = (reviewer_items * AVG_REVIEW_MINUTES) / 60.0
        reviewer_cost = reviewer_hours * REVIEWER_COST_PER_HOUR
        net_value = projected_recovery - reviewer_cost
        projections.append(
            InitiativeProjection(
                name=ini["name"],
                addressable_dollars=addressable,
                projected_recovery=projected_recovery,
                reviewer_hours=reviewer_hours,
                reviewer_cost=reviewer_cost,
                net_value=net_value,
                confidence=ini["confidence"],
            )
        )
    return projections


def analyze(
    scored: pl.DataFrame | None = None,
    claims: pl.DataFrame | None = None,
    target_practice: str | None = None,
) -> AcquisitionModel:
    if scored is None:
        scored = pl.read_parquet(GOLD_DIR / "scored_exceptions.parquet")
    if claims is None:
        claims = pl.read_parquet(BRONZE_DIR / "claims_raw.parquet")

    practice_ids = sorted(claims["practice_id"].unique().to_list())
    summaries = {pid: _practice_summary(pid, scored, claims) for pid in practice_ids}

    network_total_exposure = sum(s.total_at_risk for s in summaries.values())
    network_expected_recovery = sum(s.expected_recovery_calibrated for s in summaries.values())
    network_access_delay = sum(s.access_delay_cost for s in summaries.values())

    specialty_counts: dict[str, int] = {}
    specialty_exposure: dict[str, float] = {}
    for s in summaries.values():
        specialty_counts[s.practice_specialty] = specialty_counts.get(s.practice_specialty, 0) + 1
        specialty_exposure[s.practice_specialty] = (
            specialty_exposure.get(s.practice_specialty, 0.0) + s.total_at_risk
        )

    network_specialty_mix = {
        sp: ex / max(network_total_exposure, 1) for sp, ex in specialty_exposure.items()
    }

    # Pick target: highest expected recovery among practices with >=50 exceptions
    # (avoids cold-start practices with only a handful of noisy flags).
    eligible = [s for s in summaries.values() if s.n_exceptions >= 50]
    if not eligible:
        eligible = list(summaries.values())
    if target_practice is None:
        target = max(eligible, key=lambda s: s.expected_recovery_calibrated)
    else:
        target = summaries[target_practice]

    initiatives = _project_initiatives(target)
    total_recovery = sum(i.projected_recovery for i in initiatives)
    total_cost = sum(i.reviewer_cost for i in initiatives)
    total_net = total_recovery - total_cost
    # Rough payback: assume platform cost $120k/practice/yr; divide total_net by monthly
    monthly_net = total_net / 12.0
    payback = 120_000 / monthly_net if monthly_net > 0 else float("inf")

    result = AcquisitionModel(
        target_practice=target.practice_id,
        target_specialty=target.practice_specialty,
        is_340b_target=target.is_340b,
        network_summary={
            "n_practices": len(summaries),
            "n_claims_total": int(sum(s.n_claims for s in summaries.values())),
            "n_exceptions_total": int(sum(s.n_exceptions for s in summaries.values())),
            "total_at_risk": network_total_exposure,
            "expected_recovery_calibrated": network_expected_recovery,
            "access_delay_cost_total": network_access_delay,
        },
        target_summary=asdict(target),
        initiatives=[asdict(i) for i in initiatives],
        total_projected_recovery_q1=total_recovery,
        total_projected_reviewer_cost=total_cost,
        total_projected_net_value=total_net,
        payback_months_modeled=float(min(payback, 240.0)),
        network_specialty_mix=network_specialty_mix,
    )

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACTS_DIR / "practice_performance.json"
    out_path.write_text(json.dumps(asdict(result), indent=2, default=str))

    # Also write a per-practice Parquet for SQL/dashboard consumption.
    rows = []
    for s in summaries.values():
        rows.append(
            {
                "practice_id": s.practice_id,
                "practice_specialty": s.practice_specialty,
                "is_340b": s.is_340b,
                "n_claims": s.n_claims,
                "n_exceptions": s.n_exceptions,
                "exception_rate": s.exception_rate,
                "total_at_risk": s.total_at_risk,
                "expected_recovery_calibrated": s.expected_recovery_calibrated,
                "access_delay_cost": s.access_delay_cost,
            }
        )
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(GOLD_DIR / "practice_performance.parquet")

    return result


def _fmt_dollars(x: float) -> str:
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:.2f}M"
    if abs(x) >= 1_000:
        return f"${x / 1_000:.1f}K"
    return f"${x:,.0f}"


def print_summary(model: AcquisitionModel) -> None:
    s = model.network_summary
    print(f"\n=== Network ({s['n_practices']} practices, {s['n_claims_total']:,} claims) ===")
    print(f"  specialty mix: {model.network_specialty_mix}")
    print(f"  total exposure: {_fmt_dollars(s['total_at_risk'])}")
    print(f"  expected recovery: {_fmt_dollars(s['expected_recovery_calibrated'])}")
    print(f"  access delay cost: {_fmt_dollars(s['access_delay_cost_total'])}")

    t = model.target_summary
    print(
        f"\n=== Target practice: {model.target_practice} ({model.target_specialty}, 340B={model.is_340b_target}) ==="
    )
    print(f"  n_claims: {t['n_claims']:,}  n_exceptions: {t['n_exceptions']}")
    print(f"  total at risk: {_fmt_dollars(t['total_at_risk'])}")
    print(f"  expected recovery: {_fmt_dollars(t['expected_recovery_calibrated'])}")
    print("  exception mix (top 3):")
    for et, share in sorted(t["exception_mix"].items(), key=lambda kv: -kv[1])[:3]:
        print(f"    {et}: {share:.0%}")

    print("\n=== Initiative projection (100-day) ===")
    for i in model.initiatives:
        print(
            f"  {i['name']}\n"
            f"    addressable {_fmt_dollars(i['addressable_dollars'])}  "
            f"projected recovery {_fmt_dollars(i['projected_recovery'])}  "
            f"conf {i['confidence']:.0%}"
        )
    print(f"\n  total Q1 projected recovery: {_fmt_dollars(model.total_projected_recovery_q1)}")
    print(f"  total reviewer cost: {_fmt_dollars(model.total_projected_reviewer_cost)}")
    print(f"  total net value: {_fmt_dollars(model.total_projected_net_value)}")
    print(f"  modeled payback: {model.payback_months_modeled:.1f} months")


if __name__ == "__main__":
    m = analyze()
    print_summary(m)
