"""Privacy, disclosure control, and cell suppression logic."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.config import settings


class DisclosureChecker:
    """Evaluates disclosure risk and applies small-cell and contributor suppression."""

    def __init__(
        self,
        min_contributors: int = settings.PRIVACY_MIN_CONTRIBUTORS,
        suppress_range: Tuple[int, int] = (
            settings.PRIVACY_SUPPRESS_RANGE_MIN,
            settings.PRIVACY_SUPPRESS_RANGE_MAX,
        ),
    ):
        self.min_contributors = min_contributors
        self.suppress_range = suppress_range

    def should_suppress_cell(
        self,
        value: Optional[Union[int, float, Decimal]],
        contributor_count: Optional[int] = None,
        is_sensitive_health_event: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines if an aggregate cell must be suppressed.

        Rules:
        1. If contributor_count is known and < min_contributors (default 10) -> suppress.
        2. If sensitive count is within [1, 4] -> suppress.
        3. Zero is preserved if non-sensitive, but unknown/suppressed is NOT zero.
        """
        # Contributor count check
        if contributor_count is not None and contributor_count < self.min_contributors:
            return True, f"Contributor count ({contributor_count}) below privacy threshold ({self.min_contributors})"

        # Small cell suppression for counts
        if is_sensitive_health_event and value is not None:
            val_float = float(value)
            # If value is integer-like and in range [1, 4]
            if self.suppress_range[0] <= val_float <= self.suppress_range[1]:
                return True, f"Count ({val_float}) falls within protected small-cell range [{self.suppress_range[0]}-{self.suppress_range[1]}]"

        return False, None

    def protect_record(
        self,
        record: Dict[str, Any],
        is_sensitive_health_metric: bool = True,
    ) -> Dict[str, Any]:
        """Returns a copy of the record with suppressed fields masked."""
        result = dict(record)
        val = result.get("value")
        contrib = result.get("contributor_count")

        suppress, reason = self.should_suppress_cell(
            value=val,
            contributor_count=contrib,
            is_sensitive_health_event=is_sensitive_health_metric,
        )

        if suppress:
            result["value"] = None
            result["numerator"] = None
            result["denominator"] = None  # Prevent derivation of numerator
            result["is_suppressed"] = True
            result["suppression_reason"] = reason or "Suppressed for privacy"
        else:
            result["is_suppressed"] = False

        return result

    def apply_complementary_suppression(
        self,
        table_rows: List[Dict[str, Any]],
        value_key: str = "value",
    ) -> List[Dict[str, Any]]:
        """
        If exactly one cell in a marginal row/column is suppressed and the total is visible,
        the suppressed cell could be reconstructed by subtraction.
        Complementary suppression suppresses a second cell (e.g. the lowest non-zero).
        """
        suppressed_count = sum(1 for r in table_rows if r.get("is_suppressed", False))
        if suppressed_count == 1 and len(table_rows) > 1:
            # Find the non-suppressed row with smallest positive value to suppress
            candidates = [
                (i, r[value_key])
                for i, r in enumerate(table_rows)
                if not r.get("is_suppressed", False) and r.get(value_key) is not None
            ]
            if candidates:
                candidates.sort(key=lambda x: x[1])
                idx_to_suppress = candidates[0][0]
                table_rows[idx_to_suppress]["is_suppressed"] = True
                table_rows[idx_to_suppress][value_key] = None
                table_rows[idx_to_suppress]["suppression_reason"] = "Complementary suppression to prevent marginal reconstruction"

        return table_rows


default_disclosure_checker = DisclosureChecker()


def should_suppress(
    value: Optional[Union[int, float, Decimal]],
    contributor_count: Optional[int] = None,
    min_contributors: int = settings.PRIVACY_MIN_CONTRIBUTORS,
    suppress_range: Tuple[int, int] = (
        settings.PRIVACY_SUPPRESS_RANGE_MIN,
        settings.PRIVACY_SUPPRESS_RANGE_MAX,
    ),
) -> bool:
    checker = DisclosureChecker(min_contributors=min_contributors, suppress_range=suppress_range)
    suppress, _ = checker.should_suppress_cell(value, contributor_count)
    return suppress


def apply_suppression(
    record_dict: Dict[str, Any],
    is_sensitive: bool = True,
) -> Dict[str, Any]:
    return default_disclosure_checker.protect_record(record_dict, is_sensitive_health_metric=is_sensitive)

