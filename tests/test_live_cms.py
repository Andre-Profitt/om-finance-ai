"""Live CMS fetch smoke test — opt-in.

Hits the actual CMS landing page and downloads the current quarter's
payment-limit ZIP. CI does NOT run this by default. Set
`OAI_TEST_LIVE_CMS=1` to enable.
"""

from __future__ import annotations

import os

import pytest

LIVE = os.environ.get("OAI_TEST_LIVE_CMS") == "1"


@pytest.mark.skipif(not LIVE, reason="set OAI_TEST_LIVE_CMS=1 to enable live network test")
def test_live_asp_url_resolves():
    from oaifinance.ingest.cms_asp import _resolve_latest_asp_zip

    url = _resolve_latest_asp_zip()
    assert url.startswith("https://www.cms.gov/files/zip/")
    assert url.endswith(".zip")
    assert "crosswalk" not in url.lower()
    assert "noc" not in url.lower()


@pytest.mark.skipif(not LIVE, reason="set OAI_TEST_LIVE_CMS=1 to enable live network test")
def test_live_crosswalk_url_resolves():
    from oaifinance.ingest.ndc_hcpcs import _resolve_latest_crosswalk_zip

    url = _resolve_latest_crosswalk_zip()
    assert url.startswith("https://www.cms.gov/files/zip/")
    assert "ndc-hcpcs-crosswalk" in url.lower()


@pytest.mark.skipif(not LIVE, reason="set OAI_TEST_LIVE_CMS=1 to enable live network test")
def test_live_asp_ingest_returns_target_hcpcs():
    from oaifinance.ingest import cms_asp

    df = cms_asp.ingest(live=True)
    assert len(df) >= 5, "live ingest should produce at least 5 oncology + multispecialty HCPCS"
    assert "payment_limit_per_unit" in df.columns
    assert df["payment_limit_per_unit"].min() > 0


@pytest.mark.skipif(not LIVE, reason="set OAI_TEST_LIVE_CMS=1 to enable live network test")
def test_live_crosswalk_ingest_covers_target_hcpcs():
    from oaifinance.ingest import ndc_hcpcs

    df = ndc_hcpcs.ingest(live=True)
    assert len(df) >= 10
    assert "ndc_code" in df.columns


def test_offline_default_does_not_raise():
    """The default path (live=False) must not raise NotImplementedError anymore."""
    from oaifinance.ingest import cms_asp, ndc_hcpcs

    asp = cms_asp.ingest(live=False)
    assert len(asp) > 0
    cross = ndc_hcpcs.ingest(live=False)
    assert len(cross) > 0


def test_live_falls_back_to_sample_on_dns_failure(monkeypatch):
    """If the live fetch raises (network down, DNS fail, etc.) the ingest
    must fall back to the sample rather than crash the pipeline."""
    import requests

    from oaifinance.ingest import cms_asp

    def _boom(*args, **kwargs):
        raise requests.exceptions.ConnectionError("simulated DNS failure")

    monkeypatch.setattr(cms_asp.requests, "get", _boom)
    df = cms_asp.ingest(live=True)
    assert len(df) > 0, "should fall back to sample when network fails"
