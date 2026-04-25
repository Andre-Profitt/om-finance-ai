"""Unity-Catalog-equivalent RLS pattern tests."""

from __future__ import annotations

import polars as pl

from oaifinance.governance.rls import (
    NETWORK_CFO_GROUP,
    Principal,
    authorized_practices,
    enforce_practice_scope,
)


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "claim_id": ["A1", "A2", "B1", "B2", "C1"],
            "practice_id": ["PR-001", "PR-001", "PR-002", "PR-002", "PR-003"],
            "dollars_at_risk": [100, 200, 50, 75, 1000],
        }
    )


def test_principal_sees_only_their_practice():
    df = _frame()
    p = Principal(email="alice@om.example", practice_ids=frozenset({"PR-001"}))
    out = enforce_practice_scope(df, p)
    assert set(out["practice_id"].unique().to_list()) == {"PR-001"}
    assert out["claim_id"].to_list() == ["A1", "A2"]


def test_principal_with_no_grants_sees_nothing():
    df = _frame()
    p = Principal(email="newhire@om.example", practice_ids=frozenset())
    out = enforce_practice_scope(df, p)
    assert len(out) == 0


def test_network_cfo_group_sees_all():
    df = _frame()
    p = Principal(
        email="cfo@om.example",
        practice_ids=frozenset(),
        groups=frozenset({NETWORK_CFO_GROUP}),
    )
    out = enforce_practice_scope(df, p)
    assert len(out) == len(df)


def test_principal_cannot_read_other_practice():
    """The load-bearing invariant: practice-A principal must NOT see
    practice-B rows."""
    df = _frame()
    a = Principal(email="alice@om.example", practice_ids=frozenset({"PR-001"}))
    out = enforce_practice_scope(df, a)
    assert "PR-002" not in set(out["practice_id"].unique().to_list())
    assert "PR-003" not in set(out["practice_id"].unique().to_list())


def test_authorized_practices_diagnostic():
    a = Principal(email="alice@om.example", practice_ids=frozenset({"PR-001"}))
    b = Principal(email="bob@om.example", practice_ids=frozenset({"PR-002"}))
    cfo = Principal(
        email="cfo@om.example",
        practice_ids=frozenset(),
        groups=frozenset({NETWORK_CFO_GROUP}),
    )
    assert authorized_practices([a, b]) == {"PR-001", "PR-002"}
    assert authorized_practices([a, cfo]) == {"*"}


def test_table_without_practice_id_passes_through():
    """Tables without a practice_id column rely on table-level grants;
    the helper should not error or filter to empty."""
    df = pl.DataFrame({"id": [1, 2, 3]})
    p = Principal(email="alice@om.example", practice_ids=frozenset({"PR-001"}))
    out = enforce_practice_scope(df, p)
    assert len(out) == 3
