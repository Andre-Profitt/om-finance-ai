"""Shared pytest fixtures.

A session-scope fixture runs the pipeline once; all test modules share it.
This avoids re-running an expensive ~10s pipeline per test module.
"""

from __future__ import annotations

import pytest

from oaifinance import pipeline


@pytest.fixture(scope="session")
def pipeline_report():
    """Run the pipeline once per session and return the EvalReport."""
    return pipeline.run(n_claims=1000)
