"""
Open-Meteo Regional Modelled Weather and Air Quality Screening Connector.

Scientific Framework & Operational Caveats:
------------------------------------------
1. Regional Modelled Screening Context Only:
   Outputs from this connector represent numerical weather prediction (NWP) model simulations
   (e.g., GFS, ICON, ECMWF, CAMS), spatially interpolated to geographic grid coordinates.
   They are MACRO-SCALE SCREENING ESTIMATES, NOT in-situ workplace or microclimate sensor
   dosimetry. They do not account for radiant heat trapped in indoor structures, uninsulated
   metal roofing, radiant heat near heavy industrial machinery or furnaces, or lack of ventilation.

2. Wet-Bulb Temperature (Tw) != Wet-Bulb Globe Temperature (WBGT):
   - Psychrometric / Natural Wet-Bulb Temperature (Tw) reflects the thermodynamic evaporative
     cooling limit based strictly on dry-bulb temperature and relative humidity.
   - Wet-Bulb Globe Temperature (WBGT) [ISO 7243 / OSHA / ACGIH / NIOSH]:
       Outdoor with direct sun: WBGT = 0.7 * Tnw + 0.2 * Tg + 0.1 * Ta
       Indoor / Shaded:         WBGT = 0.7 * Tnw + 0.3 * Tg
   - CRITICAL LIMITATION: WBGT CANNOT be calculated from ambient dry-bulb temperature (Ta) and
     relative humidity (RH) alone. It physically requires a black-globe thermometer (Tg) measuring
     radiant solar/thermal load and air velocity (v) for natural convection. Any proxy derived
     purely from Ta and RH is strictly a simplified screening approximation under shaded/light-wind
     assumptions. True workplace heat strain in unshaded or radiant industrial areas can be
     drastically higher.

3. Heat Index / Apparent Temperature Assumptions:
   - Heat Index (Rothfusz equation) assumes a human walking in the SHADE with LIGHT WIND (~5 knots / 2.5 m/s)
     and light summer attire.
   - Direct exposure to full radiant sunlight can increase effective heat index by up to 8°C (15°F).
   - Impermeable PPE, heavy coveralls, or respiratory equipment severely impair sweat evaporation,
     lowering safe exposure limits below standard ambient thresholds.

4. Multi-Tiered Exposure Screening Features:
   - Hourly Granularity: Retained to capture diurnal peaks and rapid daytime shifts.
   - Shift-Level Maximums: Extracts peak heat index and WBGT screening proxy during active operational
     shifts (Morning 06:00-14:00, Afternoon 14:00-22:00, Night 22:00-06:00 UTC), along with shift duration
     (hours) above threshold. Shift-peak exposure metrics drive rapid workplace administrative controls.
   - Daily Summary Metrics: Evaluates daily maximums, total daily exposure hours, and crucially
     consecutive hours >= threshold (e.g., >= 38°C or >= 40°C), capturing continuous thermoregulatory strain.
   - Rolling 7-Day Trend: Computed strictly for multi-day background context (tracking cumulative
     acclimatization deficit, prolonged heatwaves, and sustained community fatigue). Rolling 7-day
     averages MUST NOT be used as the primary triggering mechanism for acute heat stress warnings,
     which demand rapid shift-level responsiveness to prevent acute exertional heat illness.

5. Privacy & Surveillance Ethics:
   Ingests and provides aggregate environmental screening data only. Contains zero PII or
   individual diagnostic determinations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from app.connectors.base import BaseConnector, NormalizedRecord
from app.connectors.heat_screening import (
    DEFAULT_HEAT_INDEX_WARNING,
    DEFAULT_WBGT_SCREENING_THRESHOLD,
    calculate_heat_index,
    calculate_wbgt_screening_proxy,
    calculate_wet_bulb_temperature,
    extract_all_heat_screening_features,
    extract_daily_heat_metrics,
    extract_rolling_7d_context,
    extract_shift_exposure_metrics,
)


class OpenMeteoConnector(BaseConnector):
    """
    Connects to Open-Meteo Free Weather and Air Quality APIs.

    NOTE: Open-Meteo outputs are regional numerical weather prediction (NWP) model simulations,
    strictly functioning as environmental screening context, NOT on-site workplace sensor dosimetry.
    """

    BASE_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    BASE_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    async def test_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(
                    self.BASE_WEATHER_URL,
                    params={"latitude": 21.1458, "longitude": 79.0882, "current": "temperature_2m"},
                )
                return res.status_code == 200
        except Exception:
            return False

    async def fetch(self, start_time: datetime, end_time: datetime) -> List[NormalizedRecord]:
        lat = self.configuration.get("latitude", 21.1458)  # Default Central India
        lon = self.configuration.get("longitude", 79.0882)
        endpoint_type = self.configuration.get("type", "weather")
        extract_screening_features = self.configuration.get("extract_features", True)
        heat_threshold = float(self.configuration.get("heat_threshold", DEFAULT_HEAT_INDEX_WARNING))
        wbgt_threshold = float(self.configuration.get("wbgt_threshold", DEFAULT_WBGT_SCREENING_THRESHOLD))
        geography_id = self.configuration.get("geography_id")
        workplace_id = self.configuration.get("workplace_id")

        records: List[NormalizedRecord] = []
        now = datetime.now(timezone.utc)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if endpoint_type == "weather":
                    params = {
                        "latitude": lat,
                        "longitude": lon,
                        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,wind_speed_10m",
                        "timezone": "UTC",
                    }
                    res = await client.get(self.BASE_WEATHER_URL, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        hourly = data.get("hourly", {})
                        times = hourly.get("time", [])
                        temps = hourly.get("temperature_2m", [])
                        rhs = hourly.get("relative_humidity_2m", [])
                        app_temps = hourly.get("apparent_temperature", [])
                        wind_speeds = hourly.get("wind_speed_10m", [])

                        hourly_weather_records: List[NormalizedRecord] = []

                        for idx, t_str in enumerate(times):
                            p_start = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                            if start_time and p_start < start_time:
                                continue
                            if end_time and p_start > end_time:
                                continue

                            temp = float(temps[idx]) if idx < len(temps) and temps[idx] is not None else None
                            rh = float(rhs[idx]) if idx < len(rhs) and rhs[idx] is not None else None
                            app_temp = float(app_temps[idx]) if idx < len(app_temps) and app_temps[idx] is not None else None
                            wind_speed = float(wind_speeds[idx]) if idx < len(wind_speeds) and wind_speeds[idx] is not None else None

                            if temp is None:
                                continue

                            # 1. Hourly Ambient Dry-Bulb Temperature
                            rec_temp = NormalizedRecord(
                                source_record_id=f"openmeteo_temp_{t_str}",
                                metric_code="ambient_temperature",
                                signal_family="environmental",
                                value=temp,
                                unit="celsius",
                                period_start=p_start,
                                period_end=p_start,
                                observed_at=p_start,
                                source_available_at=now,
                                geography_id=geography_id,
                                workplace_id=workplace_id,
                                location_basis="model_grid",
                                location_confidence="estimated",
                                data_label="modelled",
                                provenance="Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
                                quality_flags={
                                    "provider": "open-meteo",
                                    "model": "numerical_weather_prediction",
                                    "screening_context_only": True,
                                },
                            )
                            hourly_weather_records.append(rec_temp)

                            # 2. Hourly Relative Humidity (if available)
                            if rh is not None:
                                rec_rh = NormalizedRecord(
                                    source_record_id=f"openmeteo_rh_{t_str}",
                                    metric_code="relative_humidity",
                                    signal_family="environmental",
                                    value=rh,
                                    unit="percent",
                                    period_start=p_start,
                                    period_end=p_start,
                                    observed_at=p_start,
                                    source_available_at=now,
                                    geography_id=geography_id,
                                    workplace_id=workplace_id,
                                    location_basis="model_grid",
                                    location_confidence="estimated",
                                    data_label="modelled",
                                    provenance="Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
                                    quality_flags={
                                        "provider": "open-meteo",
                                        "model": "numerical_weather_prediction",
                                        "screening_context_only": True,
                                    },
                                )
                                hourly_weather_records.append(rec_rh)

                            # 3. Hourly Apparent Temperature / Heat Index
                            effective_app_temp = app_temp
                            if effective_app_temp is None and rh is not None:
                                effective_app_temp = calculate_heat_index(temp, rh)

                            if effective_app_temp is not None:
                                rec_app = NormalizedRecord(
                                    source_record_id=f"openmeteo_apptemp_{t_str}",
                                    metric_code="apparent_temperature",
                                    signal_family="environmental",
                                    value=effective_app_temp,
                                    unit="celsius",
                                    period_start=p_start,
                                    period_end=p_start,
                                    observed_at=p_start,
                                    source_available_at=now,
                                    geography_id=geography_id,
                                    workplace_id=workplace_id,
                                    location_basis="model_grid",
                                    location_confidence="estimated",
                                    data_label="modelled",
                                    provenance="Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
                                    quality_flags={
                                        "provider": "open-meteo",
                                        "screening_context_only": True,
                                        "assumptions": "shade_and_light_wind_2.5ms; direct_sun_adds_up_to_8C",
                                    },
                                )
                                hourly_weather_records.append(rec_app)

                            # 4. Hourly Psychrometric Wet-Bulb Temperature (Tw)
                            if rh is not None:
                                tw_val = calculate_wet_bulb_temperature(temp, rh)
                                rec_tw = NormalizedRecord(
                                    source_record_id=f"openmeteo_tw_{t_str}",
                                    metric_code="wet_bulb_temperature",
                                    signal_family="environmental",
                                    value=tw_val,
                                    unit="celsius",
                                    period_start=p_start,
                                    period_end=p_start,
                                    observed_at=p_start,
                                    source_available_at=now,
                                    geography_id=geography_id,
                                    workplace_id=workplace_id,
                                    location_basis="model_grid",
                                    location_confidence="estimated",
                                    data_label="modelled",
                                    provenance="Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
                                    quality_flags={
                                        "provider": "open-meteo",
                                        "formula": "stull_2011",
                                        "scientific_caveat": "Psychrometric Tw != WBGT. Does not measure radiant black-globe heat.",
                                        "screening_context_only": True,
                                    },
                                )
                                hourly_weather_records.append(rec_tw)

                                # 5. Hourly Simplified WBGT Screening Proxy
                                swbgt_val = calculate_wbgt_screening_proxy(temp, rh)
                                rec_swbgt = NormalizedRecord(
                                    source_record_id=f"openmeteo_swbgt_{t_str}",
                                    metric_code="wbgt_screening_proxy",
                                    signal_family="environmental",
                                    value=swbgt_val,
                                    unit="celsius",
                                    period_start=p_start,
                                    period_end=p_start,
                                    observed_at=p_start,
                                    source_available_at=now,
                                    geography_id=geography_id,
                                    workplace_id=workplace_id,
                                    location_basis="model_grid",
                                    location_confidence="estimated",
                                    data_label="modelled",
                                    provenance="Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
                                    quality_flags={
                                        "provider": "open-meteo",
                                        "formula": "australian_bom_simplified",
                                        "is_screening_proxy": True,
                                        "scientific_caveat": "Simplified indoor/shaded proxy. True ISO 7243 WBGT requires in-situ black-globe radiant sensor and air velocity.",
                                        "screening_context_only": True,
                                    },
                                )
                                hourly_weather_records.append(rec_swbgt)

                            # 6. Hourly Wind Speed (if available)
                            if wind_speed is not None:
                                rec_ws = NormalizedRecord(
                                    source_record_id=f"openmeteo_ws_{t_str}",
                                    metric_code="wind_speed",
                                    signal_family="environmental",
                                    value=wind_speed,
                                    unit="km/h",
                                    period_start=p_start,
                                    period_end=p_start,
                                    observed_at=p_start,
                                    source_available_at=now,
                                    geography_id=geography_id,
                                    workplace_id=workplace_id,
                                    location_basis="model_grid",
                                    location_confidence="estimated",
                                    data_label="modelled",
                                    provenance="Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
                                    quality_flags={
                                        "provider": "open-meteo",
                                        "model": "numerical_weather_prediction",
                                        "screening_context_only": True,
                                    },
                                )
                                hourly_weather_records.append(rec_ws)

                        records.extend(hourly_weather_records)

                        # Extract shift-level, daily, and rolling 7-day screening features
                        if extract_screening_features and hourly_weather_records:
                            screening_features = extract_all_heat_screening_features(
                                hourly_records=hourly_weather_records,
                                heat_threshold=heat_threshold,
                                wbgt_threshold=wbgt_threshold,
                                geography_id=geography_id,
                                workplace_id=workplace_id,
                                data_label="modelled",
                                provenance="Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
                            )
                            records.extend(screening_features)

                elif endpoint_type == "air_quality":
                    params = {
                        "latitude": lat,
                        "longitude": lon,
                        "hourly": "pm2_5,pm10",
                        "timezone": "UTC",
                    }
                    res = await client.get(self.BASE_AIR_QUALITY_URL, params=params)
                    if res.status_code == 200:
                        data = res.json()
                        hourly = data.get("hourly", {})
                        times = hourly.get("time", [])
                        pm25 = hourly.get("pm2_5", [])

                        for t_str, p25 in zip(times, pm25):
                            p_start = datetime.fromisoformat(t_str).replace(tzinfo=timezone.utc)
                            if start_time and p_start < start_time:
                                continue
                            if end_time and p_start > end_time:
                                continue

                            records.append(
                                NormalizedRecord(
                                    source_record_id=f"openmeteo_pm25_{t_str}",
                                    metric_code="pm25_concentration",
                                    signal_family="environmental",
                                    value=float(p25),
                                    unit="ug/m3",
                                    period_start=p_start,
                                    period_end=p_start,
                                    observed_at=p_start,
                                    source_available_at=now,
                                    geography_id=geography_id,
                                    workplace_id=workplace_id,
                                    location_basis="model_grid",
                                    location_confidence="estimated",
                                    data_label="modelled",
                                    provenance="Open-Meteo CAMS Global Atmospheric Model (Screening Context Only)",
                                    quality_flags={
                                        "provider": "open-meteo",
                                        "model": "CAMS",
                                        "screening_context_only": True,
                                    },
                                )
                            )
        except Exception:
            # Safe degraded handling on network failure
            pass

        return records
