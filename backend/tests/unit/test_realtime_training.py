"""Unit tests for realtime Open-Meteo training with mocked HTTP."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.analytics.training.realtime import fetch_open_meteo_hourly, report_to_dict, train_realtime_heat_baselines


def _hourly_payload(days: int = 40):
    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    times, temps, rhs = [], [], []
    for d in range(days):
        for h in range(24):
            ts = start + timedelta(days=d, hours=h)
            times.append(ts.strftime("%Y-%m-%dT%H:00"))
            temps.append(28.0 + (d % 5) + h * 0.15)
            rhs.append(55.0 + (h % 10))
    return {"hourly": {"time": times, "temperature_2m": temps, "relative_humidity_2m": rhs}}


@pytest.mark.asyncio
async def test_fetch_open_meteo_hourly_aggregates_daily_max():
    payload = _hourly_payload(35)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.analytics.training.realtime.httpx.AsyncClient", return_value=mock_client):
        df = await fetch_open_meteo_hourly(21.1, 79.0, lookback_days=35)

    assert len(df) == 35
    assert {"timestamp", "value", "exposure"}.issubset(df.columns)
    assert float(df["value"].min()) > 0


@pytest.mark.asyncio
async def test_train_realtime_heat_baselines_report():
    payload = _hourly_payload(45)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("app.analytics.training.realtime.httpx.AsyncClient", return_value=mock_client):
        report = await train_realtime_heat_baselines(21.1458, 79.0882, lookback_days=45)

    assert report.sample_size >= 30
    assert report.selected_model
    assert report.evidence_label == "screening"
    assert "Open-Meteo" in report.provenance
    payload_dict = report_to_dict(report)
    assert payload_dict["metric_code"] == "heat_index_daily_max"
    assert "candidate_models" in payload_dict
