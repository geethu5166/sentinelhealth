"""Unit tests for feed freshness classification."""

from datetime import datetime, timedelta, timezone

from app.services.freshness import classify_freshness


def test_freshness_bands():
    now = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)
    assert classify_freshness(now - timedelta(minutes=5), 60, now=now) == ("fresh", 5)
    assert classify_freshness(now - timedelta(minutes=90), 60, now=now) == ("stale", 90)
    assert classify_freshness(now - timedelta(minutes=200), 60, now=now) == ("critical", 200)
    assert classify_freshness(None, 60, now=now) == ("unknown", 0)
