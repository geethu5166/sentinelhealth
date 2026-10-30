"""Connectors module exports."""

from app.connectors.base import BaseConnector, NormalizedRecord
from app.connectors.heat_screening import (
    calculate_heat_index,
    calculate_wbgt_screening_proxy,
    calculate_wet_bulb_temperature,
    compute_consecutive_hours_above_threshold,
    extract_all_heat_screening_features,
    extract_daily_heat_metrics,
    extract_rolling_7d_context,
    extract_shift_exposure_metrics,
)
from app.connectors.offline_fixture import OfflineFixtureConnector
from app.connectors.open_meteo import OpenMeteoConnector

__all__ = [
    "BaseConnector",
    "NormalizedRecord",
    "OfflineFixtureConnector",
    "OpenMeteoConnector",
    "calculate_wet_bulb_temperature",
    "calculate_heat_index",
    "calculate_wbgt_screening_proxy",
    "compute_consecutive_hours_above_threshold",
    "extract_shift_exposure_metrics",
    "extract_daily_heat_metrics",
    "extract_rolling_7d_context",
    "extract_all_heat_screening_features",
]
