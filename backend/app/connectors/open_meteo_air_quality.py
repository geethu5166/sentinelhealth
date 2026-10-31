"""Open-Meteo Air Quality API Connector.

Connects to the Open-Meteo Air Quality REST endpoint.
Preserves:
- Explicit domain provenance: allows selecting 'cams_global' (default for India / non-European domains) or 'cams_europe'.
- Distinct AQI standards: European AQI (0-100+) and US EPA AQI (0-500). Neither is silently relabelled as Indian AQI.
- Averaging period distinction:
    * Hourly values represent 1-hour screening observations.
    * 24-hour average requires >= 75% valid hourly data coverage (>= 18 hours).
    * Incomplete daily windows are explicitly marked incomplete and not treated as regulatory daily means.
- Missing model-run metadata is retained as None (unavailable), not invented.
- Clear attribution: model forecast data is explicitly labelled as regional model output, NEVER as an on-site monitor measurement.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import httpx


class OpenMeteoAirQualityConnector:
    """Retrieves air quality indicators from Open-Meteo with explicit domain and averaging rules."""

    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client

    def parse_api_response(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        domain: str = "cams_global",
        geography_id: str = "geo_live_station",
        retrieval_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Parses raw Open-Meteo hourly response into standardized SentinelHealth signal records.
        Preserves AQI system distinction (European AQI vs US AQI vs Indian AQI).
        Labels model domain accurately (e.g. cams_global vs cams_europe).
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
            period_end = period_start + timedelta(hours=1)

            # 1. PM2.5 1-Hour Screening Concentration
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
                        "model_domain": domain,
                        "model_run_at": None,  # Not provided in Open-Meteo payload; explicitly unavailable
                        "is_regional_model_output": True,
                        "is_on_site_measurement": False,
                        "is_regulatory_compliance_finding": False,
                        "averaging_window_hours": 1,
                        "screening_interpretation": "1-hour acute exposure screening signal; 60 ug/m3 NAAQS applies to 24-hour mean.",
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
                        "model_domain": domain,
                        "model_run_at": None,
                        "is_regional_model_output": True,
                        "is_on_site_measurement": False,
                        "averaging_window_hours": 1,
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
                        "model_domain": domain,
                        "model_run_at": None,
                        "is_regional_model_output": True,
                        "is_on_site_measurement": False,
                        "averaging_window_hours": 1,
                        "latitude": latitude,
                        "longitude": longitude,
                        "retrieved_at": retrieval_time.isoformat(),
                        "aqi_system": "aqi_us",
                        "standard_description": "US EPA Air Quality Index (40 CFR Part 58)",
                        "quality_flag": "nominal_forecast",
                    },
                })

        return records

    @staticmethod
    def compute_24h_rolling_mean(
        hourly_records: List[Dict[str, Any]],
        min_coverage_pct: float = 75.0,
    ) -> List[Dict[str, Any]]:
        """
        Computes 24-hour averages from 1-hour records subject to data coverage rules.
        Requires >= 18 valid hourly observations out of 24 (>= 75% coverage).
        If coverage is below 75%, marks window incomplete and does NOT emit a compliant 24-hour mean.
        """
        daily_records: List[Dict[str, Any]] = []
        pm_records = [r for r in hourly_records if r["metric_code"] == "pm25_concentration"]
        if not pm_records:
            return daily_records

        # Group by UTC date
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        for r in pm_records:
            dt = datetime.fromisoformat(r["period_start"]).strftime("%Y-%m-%d")
            by_date.setdefault(dt, []).append(r)

        for dt_str, day_items in by_date.items():
            valid_values = [item["value"] for item in day_items if item.get("value") is not None]
            hour_count = len(valid_values)
            coverage_pct = round((hour_count / 24.0) * 100.0, 1)

            if coverage_pct >= min_coverage_pct:
                mean_val = round(sum(valid_values) / len(valid_values), 2)
                p_start = datetime.fromisoformat(f"{dt_str}T00:00:00+00:00")
                p_end = p_start + timedelta(hours=24)
                first_meta = day_items[0].get("metadata", {})

                daily_records.append({
                    "metric_code": "pm25_24h_mean",
                    "signal_family": "environmental",
                    "value": mean_val,
                    "unit": "ug/m3",
                    "period_start": p_start.isoformat(),
                    "period_end": p_end.isoformat(),
                    "geography_id": day_items[0]["geography_id"],
                    "metadata": {
                        "source": first_meta.get("source", "open_meteo_air_quality"),
                        "model_domain": first_meta.get("model_domain", "cams_global"),
                        "averaging_window_hours": 24,
                        "valid_hour_count": hour_count,
                        "coverage_pct": coverage_pct,
                        "coverage_status": "complete",
                        "threshold_reference": "NAAQS_2009_24h_standard_60_ug_m3",
                        "threshold_policy_version": "0.2.0",
                        "is_model_derived": True,
                        "is_regulatory_compliance_finding": False,
                    },
                })
            else:
                # Mark incomplete daily window
                daily_records.append({
                    "metric_code": "pm25_24h_mean",
                    "signal_family": "environmental",
                    "value": None,
                    "unit": "ug/m3",
                    "period_start": f"{dt_str}T00:00:00+00:00",
                    "period_end": f"{dt_str}T23:59:59+00:00",
                    "geography_id": day_items[0]["geography_id"],
                    "metadata": {
                        "averaging_window_hours": 24,
                        "valid_hour_count": hour_count,
                        "coverage_pct": coverage_pct,
                        "coverage_status": "incomplete",
                        "warning": f"Insufficient data coverage ({hour_count}/24 hours, {coverage_pct}% < 75%). Daily mean not estimable.",
                        "is_regulatory_compliance_finding": False,
                    },
                })

        return daily_records

    async def fetch_air_quality(
        self,
        latitude: float,
        longitude: float,
        domain: str = "cams_global",
        geography_id: str = "geo_live_station",
    ) -> List[Dict[str, Any]]:
        """Fetches live air quality forecast using explicit domain."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "pm2_5,european_aqi,us_aqi",
            "domains": domain,
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
            domain=domain,
            geography_id=geography_id,
            retrieval_time=retrieval_time,
        )
