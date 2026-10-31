"""Open-Meteo Air Quality API Connector.

Connects to the Open-Meteo Air Quality REST endpoint.
Preserves:
- Distinct AQI standards: European AQI (0-100+) and US AQI (0-500). Neither is silently relabelled as Indian AQI.
- Provenance metadata: source URL, regional forecast model, retrieval timestamp, coordinates, and quality flags.
- Clear attribution: model forecast data is explicitly labelled as regional model output, NEVER as an on-site monitor measurement.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx


class OpenMeteoAirQualityConnector:
    """Retrieves air quality indicators from Open-Meteo with explicit AQI system handling."""

    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client

    def parse_api_response(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        geography_id: str = "DIST-DHANPUR",
        retrieval_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parses raw Open-Meteo hourly response into standardized SentinelHealth signal records.
        Preserves AQI system distinction (European AQI vs US AQI vs Indian AQI).
        """
        if retrieval_time is None:
            retrieval_time = datetime.now(timezone.utc)

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        pm25_vals = hourly.get("pm2_5", [])
        eu_aqi_vals = hourly.get("european_aqi", [])
        us_aqi_vals = hourly.get("us_aqi", [])

        records: List[Dict[str, Any]] = []

        for i, t_str in enumerate(times):
            period_start = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
            period_end = period_start

            # 1. PM2.5 Concentration
            if i < len(pm25_vals) and pm25_vals[i] is not None:
                records.append({
                    "metric_code": "pm25_concentration",
                    "signal_family": "environmental",
                    "value": float(pm25_vals[i]),
                    "unit": "ug/m3",
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "geography_id": geography_id,
                    "metadata": {
                        "source": "open_meteo_air_quality",
                        "model": "cams_europe_regional_forecast",
                        "is_regional_model_output": True,
                        "is_on_site_measurement": False,
                        "latitude": latitude,
                        "longitude": longitude,
                        "retrieved_at": retrieval_time.isoformat(),
                        "aqi_system": None,
                        "quality_flag": "nominal_forecast",
                    },
                })

            # 2. European AQI (Scale: 0-100+, Good to Extremely Poor)
            if i < len(eu_aqi_vals) and eu_aqi_vals[i] is not None:
                records.append({
                    "metric_code": "aqi_eu",
                    "signal_family": "environmental",
                    "value": float(eu_aqi_vals[i]),
                    "unit": "index_points",
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "geography_id": geography_id,
                    "metadata": {
                        "source": "open_meteo_air_quality",
                        "model": "cams_europe_regional_forecast",
                        "is_regional_model_output": True,
                        "is_on_site_measurement": False,
                        "latitude": latitude,
                        "longitude": longitude,
                        "retrieved_at": retrieval_time.isoformat(),
                        "aqi_system": "aqi_eu",
                        "standard_description": "European Air Quality Index (Directive 2008/50/EC)",
                        "quality_flag": "nominal_forecast",
                    },
                })

            # 3. US AQI (Scale: 0-500, EPA standard)
            if i < len(us_aqi_vals) and us_aqi_vals[i] is not None:
                records.append({
                    "metric_code": "aqi_us",
                    "signal_family": "environmental",
                    "value": float(us_aqi_vals[i]),
                    "unit": "index_points",
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "geography_id": geography_id,
                    "metadata": {
                        "source": "open_meteo_air_quality",
                        "model": "cams_europe_regional_forecast",
                        "is_regional_model_output": True,
                        "is_on_site_measurement": False,
                        "latitude": latitude,
                        "longitude": longitude,
                        "retrieved_at": retrieval_time.isoformat(),
                        "aqi_system": "aqi_us",
                        "standard_description": "US EPA Air Quality Index (40 CFR Part 58)",
                        "quality_flag": "nominal_forecast",
                    },
                })

        return records

    async def fetch_air_quality(
        self,
        latitude: float,
        longitude: float,
        geography_id: str = "DIST-DHANPUR",
    ) -> List[Dict[str, Any]]:
        """Fetches live forecast data asynchronously if client is available."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "pm2_5,european_aqi,us_aqi",
            "timezone": "UTC",
        }
        retrieval_time = datetime.now(timezone.utc)

        if self.client:
            resp = await self.client.get(self.BASE_URL, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.BASE_URL, params=params, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()

        return self.parse_api_response(
            data=data,
            latitude=latitude,
            longitude=longitude,
            geography_id=geography_id,
            retrieval_time=retrieval_time,
        )
