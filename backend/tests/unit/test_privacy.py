"""Unit tests for privacy and disclosure control."""

from app.privacy.suppression import DisclosureChecker


def test_small_cell_suppression():
    checker = DisclosureChecker(min_contributors=10, suppress_range=(1, 4))

    # Counts 1 through 4 MUST be suppressed
    for count in [1, 2, 3, 4]:
        suppress, reason = checker.should_suppress_cell(value=count, is_sensitive_health_event=True)
        assert suppress is True
        assert "protected small-cell range" in reason

    # Count 0 is preserved (not an individual disclosure)
    suppress_zero, _ = checker.should_suppress_cell(value=0, is_sensitive_health_event=True)
    assert suppress_zero is False

    # Count >= 5 is preserved if contributors >= 10
    suppress_normal, _ = checker.should_suppress_cell(value=15, contributor_count=15, is_sensitive_health_event=True)
    assert suppress_normal is False


def test_contributor_count_suppression():
    checker = DisclosureChecker(min_contributors=10)

    # Even if value is large (e.g. 20 events), if contributor count is only 5 unique people -> suppress
    suppress, reason = checker.should_suppress_cell(value=20, contributor_count=5)
    assert suppress is True
    assert "below privacy threshold" in reason


def test_complementary_suppression():
    checker = DisclosureChecker()
    rows = [
        {"name": "Site A", "value": 2, "is_suppressed": True},  # Suppressed (1-4)
        {"name": "Site B", "value": 15, "is_suppressed": False},
        {"name": "Site C", "value": 30, "is_suppressed": False},
    ]
    # Complementary suppression should mask Site B to prevent calculating Site A from total
    protected = checker.apply_complementary_suppression(rows)
    suppressed_count = sum(1 for r in protected if r["is_suppressed"])
    assert suppressed_count == 2
    assert protected[1]["is_suppressed"] is True
    assert protected[1]["value"] is None

