"""Shared feed freshness helpers for overview and source health."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple


def classify_freshness(
    last_seen: Optional[datetime],
    threshold_minutes: Optional[int],
    *,
    now: Optional[datetime] = None,
) -> Tuple[str, int]:
    """
    Returns (status, age_minutes).

    status: fresh | stale | critical | unknown
    """
    clock = now or datetime.now(timezone.utc)
    if last_seen is None:
        return "unknown", 0
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    age_minutes = max(0, int((clock - last_seen).total_seconds() // 60))
    threshold = max(1, int(threshold_minutes or 180))
    if age_minutes <= threshold:
        return "fresh", age_minutes
    if age_minutes <= threshold * 2:
        return "stale", age_minutes
    return "critical", age_minutes
