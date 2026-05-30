"""Tests for the job classifier in generator.py.

The classifier reads template subfolders from disk and keyword config from
keywords.json. Both are patched in these tests.
"""
import pytest
from unittest.mock import patch


@pytest.fixture
def stub_categories(monkeypatch):
    """Stub out filesystem + keyword loading for classify_job."""
    folders = ["Finance", "Accounting", "Investment", "Fund Accounting", "M&A"]
    keywords = {
        "finance":          ["finance", "fp&a", "budget"],
        "accounting":       ["accounting", "ledger", "reconciliation"],
        "investment":       ["investment", "portfolio", "equities"],
        "fund accounting":  ["fund accounting", "nav", "fund admin"],
        "m&a":              ["m&a", "mergers", "acquisitions"],
    }
    broad = {"finance", "accounting"}

    monkeypatch.setattr("os.listdir", lambda path: folders)
    monkeypatch.setattr("os.path.isdir", lambda path: True)
    monkeypatch.setattr("generator._load_keywords", lambda: (keywords, broad))
    monkeypatch.setattr("generator.config", type("C", (), {"TEMPLATE_BASE": "/fake"}))


def test_title_signal_wins_over_description(stub_categories):
    from generator import classify_job
    # Title says investment, description mentions accounting once.
    # Title-weighted scoring should pick investment.
    assert classify_job("Investment Analyst", "some accounting context") == "Investment"


def test_specialist_overrides_broad_when_specialist_has_title_evidence(stub_categories):
    from generator import classify_job
    # Title "Fund Accounting" matches both Accounting (broad) and Fund Accounting (specialist).
    # Specialist should win because its name appears literally in the title.
    assert classify_job("Fund Accounting Senior Analyst", "reconciliation and nav prep") == "Fund Accounting"


def test_specialist_name_in_title_forces_override(stub_categories):
    from generator import classify_job
    # Even when the broad category's description signal is strong, a specialist
    # whose name appears in the title should win.
    desc = "accounting reconciliation ledger reconciliation accounting"  # broad-heavy
    assert classify_job("M&A Associate", desc) == "M&A"


def test_no_title_evidence_falls_back_to_description(stub_categories):
    from generator import classify_job
    # Generic title with no category match → description signal decides
    result = classify_job("Senior Analyst", "fp&a budget forecasting work")
    assert result == "Finance"


def test_empty_description_with_title_match(stub_categories):
    from generator import classify_job
    assert classify_job("Portfolio Investment Manager", "") == "Investment"
