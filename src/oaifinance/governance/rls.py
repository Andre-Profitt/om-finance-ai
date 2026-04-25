"""Local-equivalent row-level security helper.

In production, Unity Catalog row filters enforce practice-scoped reads
(see `dashboards/sql/governance/01_unity_catalog_rls.sql`). For local dev
and tests, this module provides the same contract via Python — call
`enforce_practice_scope(df, principal)` and get back only the rows the
principal is authorized to see.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import polars as pl

NETWORK_CFO_GROUP = "network_cfo"


@dataclass(frozen=True)
class Principal:
    email: str
    practice_ids: frozenset[str]
    groups: frozenset[str] = frozenset()


def enforce_practice_scope(
    df: pl.DataFrame,
    principal: Principal,
    practice_id_col: str = "practice_id",
) -> pl.DataFrame:
    """Return only rows the principal is authorized to read.

    Network-CFO group members see all rows. Other principals see only
    rows whose `practice_id` is in their authorized set.
    """
    if NETWORK_CFO_GROUP in principal.groups:
        return df
    if practice_id_col not in df.columns:
        # Tables without a practice_id column are not practice-scoped;
        # access is governed by table-level grants instead.
        return df
    return df.filter(pl.col(practice_id_col).is_in(list(principal.practice_ids)))


def authorized_practices(principals: Iterable[Principal]) -> set[str]:
    """Diagnostic: union of practice_ids any of the supplied principals can read."""
    out: set[str] = set()
    for p in principals:
        if NETWORK_CFO_GROUP in p.groups:
            return {"*"}
        out.update(p.practice_ids)
    return out
