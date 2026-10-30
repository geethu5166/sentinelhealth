"""Unit tests for heat screening biometeorological modeling and connectors."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.connectors.heat_screening import (
    DEFAULT_HEAT_INDEX_WARNING,
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
from app.connectors.base import NormalizedRecord


def test_calculate_wet_bulb_temperature():
    """Validates Stull (2011) psychrometric wet-bulb formulation."""
    # At 30°C and 50% RH, psychrometric Tw is approx 22.3°C
    tw = calculate_wet_bulb_temperature(30.0, 50.0)
    assert 22.0 <= tw <= 22.6

    # Wet-bulb should never exceed ambient dry-bulb temperature
    assert calculate_wet_bulb_temperature(40.0, 30.0) < 40.0
    assert calculate_wet_bulb_temperature(25.0, 80.0) < 25.0


def test_calculate_heat_index():
    """Validates NOAA Heat Index Rothfusz polynomial calculation and edge conditions."""
    # Under warm and humid conditions, heat index should be substantially higher than dry-bulb
    hi_hot_humid = calculate_heat_index(35.0, 60.0)
    assert hi_hot_humid > 43.0

    # Under cool conditions (< 80°F / ~26.7°C), simple formula is applied
    hi_cool = calculate_heat_index(22.0, 50.0)
    assert 21.0 <= hi_cool <= 23.0


def test_calculate_wbgt_screening_proxy():
    """Validates simplified Australian BOM WBGT screening proxy."""
    swbgt = calculate_wbgt_screening_proxy(30.0, 50.0)
    # At 30°C, 50% RH: vapor pressure e ~ 21 hPa, sWBGT ~ 29.3°C
    assert 28.5 <= swbgt <= 30.0

    # Increases monotonically with temperature and humidity
    swbgt_high = calculate_wbgt_screening_proxy(38.0, 60.0)
    assert swbgt_high > swbgt


def test_compute_consecutive_hours_above_threshold():
    """Validates longest unbroken streak of hours >= threshold."""
    # Sequence: 30, 39, 41, 40, 35, 39, 39, 42, 41, 30
    # Threshold 38.0:
    # Streak 1: 39, 41, 40 (length 3)
    # Streak 2: 39, 39, 42, 41 (length 4)
    # Max streak should be 4
    vals = [30.0, 39.0, 41.0, 40.0, 35.0, 39.0, 39.0, 42.0, 41.0, 30.0]
    assert compute_consecutive_hours_above_threshold(vals, 38.0) == 4

    # None above threshold
    assert compute_consecutive_hours_above_threshold([25.0, 30.0, 32.0], 38.0) == 0

    # All above threshold
    assert compute_consecutive_hours_above_threshold([39.0, 40.0, 41.0], 38.0) == 3


def test_extract_shift_exposure_metrics():
    """Tests shift-level peak exposure and duration feature extraction."""
    base_time = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    hourly_records = []

    # Generate 24 hours of synthetic hourly records
    for h in range(24):
        t = base_time + timedelta(hours=h)
        # Afternoon heat spike: hours 12-16 reach 41-43°C apparent temp
        if 12 <= h <= 16:
            app_temp = 42.0
            wbgt_proxy = 32.0
        else:
            app_temp = 34.0
            wbgt_proxy = 26.0

        hourly_records.append(
            NormalizedRecord(
                source_record_id=f"rec_app_{h}",
                metric_code="apparent_temperature",
                signal_family="environmental",
                value=app_temp,
                unit="celsius",
                period_start=t,
                period_end=t,
                observed_at=t,
                source_available_at=t,
                data_label="modelled",
            )
        )
        hourly_records.append(
            NormalizedRecord(
                source_record_id=f"rec_wbgt_{h}",
                metric_code="wbgt_screening_proxy",
                signal_family="environmental",
                value=wbgt_proxy,
                unit="celsius",
                period_start=t,
                period_end=t,
                observed_at=t,
                source_available_at=t,
                data_label="modelled",
            )
        )

    shift_metrics = extract_shift_exposure_metrics(hourly_records, heat_threshold=38.0, wbgt_threshold=28.0)

    # We expect metrics for morning (06-14), afternoon (14-22), and night (22-06)
    metric_codes = [m.metric_code for m in shift_metrics]
    assert "shift_peak_apparent_temperature" in metric_codes
    assert "shift_hours_above_threshold" in metric_codes
    assert "shift_peak_wbgt_screening" in metric_codes

    # Morning shift (06:00-14:00) contains hours 12 and 13 (42.0°C)
    morning_peak = next(
        m for m in shift_metrics
        if m.metric_code == "shift_peak_apparent_temperature" and m.quality_flags["shift_name"] == "morning_shift"
    )
    assert morning_peak.value == 42.0

    morning_hours = next(
        m for m in shift_metrics
        if m.metric_code == "shift_hours_above_threshold" and m.quality_flags["shift_name"] == "morning_shift"
    )
    assert morning_hours.value == 2.0  # hours 12 and 13


def test_extract_daily_heat_metrics():
    """Tests daily maximum and consecutive hours above threshold."""
    base_time = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
    hourly_records = []

    for h in range(24):
        t = base_time + timedelta(hours=h)
        # Consecutive heat hours 11, 12, 13, 14, 15 (5 consecutive hours >= 38.0°C)
        app_temp = 41.5 if 11 <= h <= 15 else 32.0
        amb_temp = 38.0 if 11 <= h <= 15 else 29.0

        hourly_records.append(
            NormalizedRecord(
                source_record_id=f"rec_app_{h}",
                metric_code="apparent_temperature",
                signal_family="environmental",
                value=app_temp,
                unit="celsius",
                period_start=t,
                period_end=t,
                observed_at=t,
                source_available_at=t,
                data_label="modelled",
            )
        )
        hourly_records.append(
            NormalizedRecord(
                source_record_id=f"rec_amb_{h}",
                metric_code="ambient_temperature",
                signal_family="environmental",
                value=amb_temp,
                unit="celsius",
                period_start=t,
                period_end=t,
                observed_at=t,
                source_available_at=t,
                data_label="modelled",
            )
        )

    daily_metrics = extract_daily_heat_metrics(hourly_records, heat_threshold=38.0)
    by_code = {m.metric_code: m for m in daily_metrics}

    assert by_code["daily_max_apparent_temperature"].value == 41.5
    assert by_code["daily_max_temperature"].value == 38.0
    assert by_code["daily_hours_above_threshold"].value == 5.0
    assert by_code["consecutive_hours_above_threshold"].value == 5.0


def test_extract_rolling_7d_context_scientific_constraint():
    """
    Verifies that rolling 7-day trend metrics are computed strictly as background context
    and contain explicit flags preventing use as primary acute triggers.
    """
    base_date = datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc)
    daily_records = []

    for d in range(10):
        t_start = base_date + timedelta(days=d)
        t_end = t_start + timedelta(hours=23, minutes=59, seconds=59)
        # Daily peak increases gradually
        daily_records.append(
            NormalizedRecord(
                source_record_id=f"daily_max_{d}",
                metric_code="daily_max_apparent_temperature",
                signal_family="environmental",
                value=35.0 + d * 0.5,
                unit="celsius",
                period_start=t_start,
                period_end=t_end,
                observed_at=t_end,
                source_available_at=t_end,
                data_label="modelled",
            )
        )

    rolling_recs = extract_rolling_7d_context(daily_records)
    assert len(rolling_recs) > 0

    # Verify quality flags enforce background context only
    for rec in rolling_recs:
        assert rec.quality_flags.get("contextual_background_only") is True
        assert rec.quality_flags.get("do_not_use_as_primary_acute_trigger") is True
        assert "multi-day background context" in rec.quality_flags.get("scientific_rationale", "")


@pytest.mark.asyncio
async def test_open_meteo_connector_fetch_and_screening_features():
    """Tests OpenMeteoConnector with mocked API response."""
    connector = OpenMeteoConnector("open_meteo", {"extract_features": True, "heat_threshold": 38.0})

    mock_times = [(datetime(2026, 6, 15, h, 0, tzinfo=timezone.utc)).isoformat() for h in range(24)]
    mock_temps = [30.0 + (10.0 if 12 <= h <= 16 else 2.0) for h in range(24)]
    mock_rhs = [50.0 for _ in range(24)]
    mock_app_temps = [calculate_heat_index(t, 50.0) for t in mock_temps]
    mock_winds = [12.0 for _ in range(24)]

    mock_json_response = {
        "hourly": {
            "time": mock_times,
            "temperature_2m": mock_temps,
            "relative_humidity_2m": mock_rhs,
            "apparent_temperature": mock_app_temps,
            "wind_speed_10m": mock_winds,
        }
    }

    mock_response = httpx.Response(200, json=mock_json_response, request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        start = datetime(2026, 6, 15, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 6, 15, 23, 59, tzinfo=timezone.utc)
        records = await connector.fetch(start, end)

    assert len(records) > 0

    # Hourly metrics must be present
    codes = set(r.metric_code for r in records)
    assert "ambient_temperature" in codes
    assert "relative_humidity" in codes
    assert "apparent_temperature" in codes
    assert "wet_bulb_temperature" in codes
    assert "wbgt_screening_proxy" in codes
    assert "wind_speed" in codes

    # Shift-level and daily metrics must be present
    assert "shift_peak_apparent_temperature" in codes
    assert "shift_hours_above_threshold" in codes
    assert "shift_peak_wbgt_screening" in codes
    assert "daily_max_apparent_temperature" in codes
    assert "consecutive_hours_above_threshold" in codes

    # Check labelling
    for r in records:
        assert r.data_label == "modelled"
        assert r.location_basis == "model_grid"
        assert r.location_confidence == "estimated"
        assert "Screening Context Only" in r.provenance


@pytest.mark.asyncio
async def test_offline_fixture_connector():
    """Tests OfflineFixtureConnector loading synthetic fixture with privacy and synthetic labelling."""
    fixture_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../fixtures/templates/environmental-signals.csv"))
    assert os.path.exists(fixture_path), f"Fixture not found at {fixture_path}"

    connector = OfflineFixtureConnector("offline_fixture", {"file_path": fixture_path, "extract_features": False})
    is_connected = await connector.test_connection()
    assert is_connected is True

    start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc)
    records = await connector.fetch(start, end)

    assert len(records) > 0
    for r in records:
        # Must be explicitly synthetic and aggregate
        assert r.data_label == "synthetic"
        assert r.signal_family == "environmental"
        assert r.contributor_count is None or r.contributor_count >= 10
