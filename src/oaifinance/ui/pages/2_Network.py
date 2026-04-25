"""Network View — per-practice exposure, mix, and acquisition target."""

from __future__ import annotations

import polars as pl
import streamlit as st

from oaifinance import __version__
from oaifinance.ui import components as ui
from oaifinance.ui import data as ud
from oaifinance.ui import styles

st.set_page_config(
    page_title="Network · Control Tower",
    layout="wide",
    initial_sidebar_state="expanded",
)
styles.inject()

frames = ud.load_all()
if frames.practice is None or frames.scored is None:
    ui.page_header("Network view", "Pipeline outputs not found.")
    ui.empty_state("Run `make demo` and `oai-finance practice-analysis` to populate.")
    st.stop()

practice = frames.practice
scored = frames.scored

n_practices = len(practice)
total_at_risk = float(practice["total_at_risk"].sum())
total_recovery = float(practice["expected_recovery_calibrated"].sum())
total_access_delay = float(practice["access_delay_cost"].sum())

ui.page_header(
    "Network — practice exposure",
    f"{n_practices} practices across oncology and multispecialty.",
    n_rows=n_practices,
)

ui.kpi_grid(
    [
        ("Practices", f"{n_practices}", "synthetic network"),
        ("Total exposure", ui.fmt_dollars(total_at_risk), None),
        ("Expected recovery", ui.fmt_dollars(total_recovery), "calibrated"),
        ("Access delay cost", ui.fmt_dollars(total_access_delay), "PA gap operational impact"),
    ]
)

ui.section("Specialty mix")
spec = (
    practice.group_by("practice_specialty")
    .agg(
        pl.len().alias("n_practices"),
        pl.col("n_exceptions").sum().alias("n_exceptions"),
        pl.col("total_at_risk").sum().alias("dollars_at_risk"),
        pl.col("expected_recovery_calibrated").sum().alias("expected_recovery"),
    )
    .sort("expected_recovery", descending=True)
)
st.dataframe(
    spec,
    hide_index=True,
    use_container_width=True,
    column_config={
        "practice_specialty": st.column_config.TextColumn("Specialty"),
        "n_practices": st.column_config.NumberColumn("Practices", format="%d"),
        "n_exceptions": st.column_config.NumberColumn("Exceptions", format="%d"),
        "dollars_at_risk": st.column_config.NumberColumn("$ at risk", format="$%.0f"),
        "expected_recovery": st.column_config.NumberColumn("Expected recovery", format="$%.0f"),
    },
)

ui.section("Practices ranked by expected recovery")
st.dataframe(
    practice.sort("expected_recovery_calibrated", descending=True),
    hide_index=True,
    use_container_width=True,
    height=420,
    column_config={
        "practice_id": st.column_config.TextColumn("Practice", width="small"),
        "practice_specialty": st.column_config.TextColumn("Specialty", width="small"),
        "is_340b": st.column_config.CheckboxColumn("340B", width="small"),
        "n_claims": st.column_config.NumberColumn("Claims", format="%d"),
        "n_exceptions": st.column_config.NumberColumn("Exceptions", format="%d"),
        "exception_rate": st.column_config.NumberColumn("Exception rate", format="%.1%%"),
        "total_at_risk": st.column_config.NumberColumn("$ at risk", format="$%.0f"),
        "expected_recovery_calibrated": st.column_config.NumberColumn(
            "Expected recovery", format="$%.0f"
        ),
        "access_delay_cost": st.column_config.NumberColumn("Access delay cost", format="$%.0f"),
    },
)

ui.section("Drill-in: a single practice")
selected_practice = st.selectbox(
    "Practice",
    practice.sort("expected_recovery_calibrated", descending=True)["practice_id"].to_list(),
    index=0,
    label_visibility="collapsed",
)

p_row = practice.filter(pl.col("practice_id") == selected_practice).row(0, named=True)
p_scored = scored.filter(pl.col("practice_id") == selected_practice)

ui.kpi_grid(
    [
        ("Specialty", str(p_row["practice_specialty"]).capitalize(), None),
        ("340B", "yes" if p_row["is_340b"] else "no", None),
        ("Claims", f"{p_row['n_claims']:,}", None),
        ("Exceptions", f"{p_row['n_exceptions']:,}", f"{p_row['exception_rate']:.1%} rate"),
        ("$ at risk", ui.fmt_dollars(float(p_row["total_at_risk"])), None),
        (
            "Expected recovery",
            ui.fmt_dollars(float(p_row["expected_recovery_calibrated"])),
            "calibrated",
        ),
    ],
    accent_first=False,
)

if len(p_scored) > 0:
    ui.section("Exception mix")
    mix = (
        p_scored.group_by("exception_type")
        .agg(
            pl.len().alias("n"),
            pl.col("dollars_at_risk").sum().alias("dollars_at_risk"),
        )
        .sort("dollars_at_risk", descending=True)
    )
    st.dataframe(
        mix,
        hide_index=True,
        use_container_width=True,
        column_config={
            "exception_type": st.column_config.TextColumn("Exception type"),
            "n": st.column_config.NumberColumn("Count", format="%d"),
            "dollars_at_risk": st.column_config.NumberColumn("$ at risk", format="$%.0f"),
        },
    )

    ui.section("Top HCPCS by dollars at risk")
    hcpcs_mix = (
        p_scored.group_by("hcpcs_code")
        .agg(
            pl.len().alias("n"),
            pl.col("dollars_at_risk").sum().alias("dollars_at_risk"),
        )
        .sort("dollars_at_risk", descending=True)
        .head(5)
    )
    st.dataframe(
        hcpcs_mix,
        hide_index=True,
        use_container_width=True,
        column_config={
            "hcpcs_code": st.column_config.TextColumn("HCPCS"),
            "n": st.column_config.NumberColumn("Count", format="%d"),
            "dollars_at_risk": st.column_config.NumberColumn("$ at risk", format="$%.0f"),
        },
    )

ui.app_footer(version=__version__)
