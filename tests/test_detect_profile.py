"""Tests for the country-to-profile detection used by apply.py."""
from apply import _detect_profile


LOCATIONS = {
    "Malaysia":    ["malaysia", "kuala lumpur", "kl", "selangor"],
    "Singapore":   ["singapore", "sg"],
    "Netherlands": ["netherlands", "amsterdam", "rotterdam"],
    "United States": ["united states", "usa", "us", "new york"],
}


def test_match_by_country_name():
    assert _detect_profile("Malaysia", LOCATIONS) == "Malaysia"


def test_match_by_city():
    assert _detect_profile("Amsterdam", LOCATIONS) == "Netherlands"


def test_match_by_abbreviation():
    assert _detect_profile("SG", LOCATIONS) == "Singapore"


def test_match_case_insensitive():
    assert _detect_profile("KUALA LUMPUR", LOCATIONS) == "Malaysia"


def test_word_boundary_prevents_false_match():
    # "us" must NOT match inside "netherlands" — the original bug we fixed.
    # (Note: "netherlands" does not actually contain "us", but the principle
    # is that short tokens like "us" or "sg" only match whole words.)
    assert _detect_profile("Netherlands", LOCATIONS) == "Netherlands"


def test_short_abbrev_not_matched_in_word():
    # "us" should not match inside "discusses" or similar word-embedded use
    assert _detect_profile("Job discusses something", LOCATIONS) is None


def test_no_match_returns_none():
    assert _detect_profile("Antarctica", LOCATIONS) is None


def test_none_country_returns_none():
    assert _detect_profile(None, LOCATIONS) is None


def test_empty_country_returns_none():
    assert _detect_profile("", LOCATIONS) is None


def test_multi_word_location():
    assert _detect_profile("Job posting in New York", LOCATIONS) == "United States"
