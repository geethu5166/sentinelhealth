"""
Biometeorological Heat Exposure & Surveillance Modeling Module.

Scientific Framework & Operational Caveats:
------------------------------------------
1. Regional Modelled Screening vs. In-situ Dosimetry:
   Open-Meteo and NWP (numerical weather prediction) grid data provide regional, macro-scale
   background screening context (~2 meters above ground in standard open terrain). They do
   NOT reflect microclimate conditions inside buildings, under uninsulated metal roofs, inside
   heavy vehicle cabs, or near radiant industrial heat sources (furnaces, asphalt, heavy machinery).
   Therefore, these metrics serve as screening triggers for preventive administrative controls,
   NOT as replacements for calibrated on-site occupational hygiene dosimetry.

2. Wet-Bulb Temperature (Tw) != Wet-Bulb Globe Temperature (WBGT):
   - Psychrometric / Natural Wet-Bulb Temperature (Tw): The thermodynamic limit of evaporative
     cooling, calculated from ambient dry-bulb temperature (Ta) and relative humidity (RH).
   - Wet-Bulb Globe Temperature (WBGT) [ISO 7243 / OSHA / ACGIH / NIOSH]:
       Outdoor with solar load: WBGT = 0.7 * Tnw + 0.2 * Tg + 0.1 * Ta
       Indoor / shaded:         WBGT = 0.7 * Tnw + 0.3 * Tg
     where Tnw is natural wet-bulb temperature, Tg is black-globe temperature capturing mean
     radiant temperature (MRT) from solar radiation and hot surfaces, and Ta is ambient dry-bulb
     air temperature, influenced by air velocity (v).
   - CRITICAL LIMITATION: WBGT CANNOT be calculated from ambient dry-bulb temperature and relative
     humidity alone. It physically requires radiant heat (black-globe temperature Tg) and air velocity (v).
     Any proxy derived solely from Ta and RH (such as the Australian BOM simplified formula) is strictly
     a modelled screening proxy for shaded conditions with light air movement. In direct unshaded sunlight
     or near radiant industrial surfaces, true WBGT may be several degrees higher than the screening proxy.

3. Heat Index (HI) Assumptions:
   - Heat Index (Rothfusz equation / Steadman model) assumes a human body in full shade and light
     wind speed (~5 knots / 2.5 m/s) wearing light summer clothing.
   - Exposure to direct solar radiation can increase effective heat index by up to 8°C (15°F).
   - Heavy personal protective equipment (PPE), impermeable coveralls, or respirators impair
     sweat evaporation and drastically increase physiological heat strain at lower ambient thresholds.

4. Multi-Tiered Exposure Screening Architecture:
   - Hourly Granularity: Retained to capture diurnal spikes and rapid meteorological transitions.
   - Shift-Level Metrics: Extracts peak heat index / WBGT proxy and duration (hours) above threshold
     during active 8-hour operational work shifts (e.g. Morning 06:00-14:00, Afternoon 14:00-22:00,
     Night 22:00-06:00). Shift-peak metrics drive immediate workplace administrative interventions.
   - Daily Summary Metrics: Computes daily maximums, total exposure hours, and crucially
     consecutive hours >= threshold (e.g. >= 38°C or >= 40°C). Consecutive unremitting heat
     drastically degrades human thermoregulatory homeostatic capacity.
   - Rolling 7-Day Trend: Strictly designated for multi-day background context (tracking cumulative
     fatigue, community vulnerability, and acclimatization deficits). It MUST NOT be used as the
     primary triggering mechanism for acute heat stress warnings, which require rapid shift-level
     responsiveness to prevent exertional heat stroke.

5. Privacy & Surveillance Ethics:
   All metrics represent strictly population-level aggregate or environmental screening indicators.
   Zero individual diagnostic conclusions or PII (Personally Identifiable Information) are ingested
   or outputted.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.connectors.base import NormalizedRecord

# Operational Screening Thresholds (Celsius)
DEFAULT_HEAT_INDEX_ADVISORY = 32.0   # NOAA Caution
DEFAULT_HEAT_INDEX_WARNING = 38.0    # NOAA Extreme Caution / Public Health Screening
DEFAULT_HEAT_INDEX_EMERGENCY = 42.0  # NOAA Danger / Immediate Operational Pause
DEFAULT_WBGT_SCREENING_THRESHOLD = 28.0  # ISO 7243 / ACGIH Screening Action Level for Moderate Work


def calculate_wet_bulb_temperature(temperature_c: float, relative_humidity: float) -> float:
    """
    Computes psychrometric wet-bulb temperature (Tw) in Celsius using Stull's empirical formula (2011).
    Valid for Ta in [-20, 50] °C and RH in [5, 99] %. Mean absolute error < 0.3 °C.

    NOTE: Psychrometric Tw is NOT Wet-Bulb Globe Temperature (WBGT).
    """
    t = float(temperature_c)
    rh = max(1.0, min(100.0, float(relative_humidity)))

    tw = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return round(tw, 2)


def calculate_heat_index(temperature_c: float, relative_humidity: float) -> float:
    """
    Computes NOAA Heat Index in Celsius using Rothfusz regression with low/high humidity adjustments.
    Reflects perceived apparent temperature under shaded conditions with light wind (~2.5 m/s).

    CAVEAT: Direct solar radiation can add up to 8°C (15°F) to perceived heat stress.
    """
    t_c = float(temperature_c)
    rh = max(0.0, min(100.0, float(relative_humidity)))
    tf = t_c * 1.8 + 32.0

    # Steadman simple equation for cool/mild conditions
    hi_simple = 0.5 * (tf + 61.0 + ((tf - 68.0) * 1.2) + (rh * 0.094))
    if hi_simple < 80.0:
        hi_f = hi_simple
    else:
        # Full Rothfusz polynomial regression
        hi_f = (
            -42.379
            + 2.04901523 * tf
            + 10.14333127 * rh
            - 0.22475541 * tf * rh
            - 0.00683783 * (tf ** 2)
            - 0.05481717 * (rh ** 2)
            + 0.00122874 * (tf ** 2) * rh
            + 0.00085282 * tf * (rh ** 2)
            - 0.00000199 * (tf ** 2) * (rh ** 2)
        )
        # Adjustments for dry hot or humid warm extremes
        if rh < 13.0 and 80.0 <= tf <= 112.0:
            adj = ((13.0 - rh) / 4.0) * math.sqrt(max(0.0, (17.0 - abs(tf - 95.0)) / 17.0))
            hi_f -= adj
        elif rh > 85.0 and 80.0 <= tf <= 87.0:
            adj = ((rh - 85.0) / 10.0) * ((87.0 - tf) / 5.0)
            hi_f += adj

    hi_c = (hi_f - 32.0) / 1.8
    return round(hi_c, 2)


def calculate_wbgt_screening_proxy(temperature_c: float, relative_humidity: float) -> float:
    """
    Calculates simplified Wet-Bulb Globe Temperature (sWBGT) screening proxy in Celsius.

    Method Attribution & Scientific Distinction:
    --------------------------------------------
    This function implements the Australian Bureau of Meteorology (BOM) empirical
    temperature/vapour-pressure approximation:
        e = (RH / 100) * 6.105 * exp(17.27 * Ta / (237.7 + Ta))  [Magnus-Tetens vapor pressure in hPa]
        sWBGT = 0.567 * Ta + 0.393 * e + 3.94

    Documented Scientific Limitations & Method Attribution:
    -------------------------------------------------------
    - Implementation: Australian Bureau of Meteorology (BOM) simplified formula (see Lemke &
      Kjellstrom 2012; Budd 2008):
          e = (RH / 100) * 6.105 * exp(17.27 * Ta / (237.7 + Ta))  [Magnus-Tetens vapor pressure in hPa]
          sWBGT = 0.567 * Ta + 0.393 * e + 3.94
    - Non-Interchangeability with Measured WBGT (PMC9941479): The simplified WBGT formula relies
      solely on temperature and vapour pressure, omitting solar radiation flux and wind speed.
      Scientific evaluations (e.g. Grundstein & Cooper 2018; Lemke et al.) demonstrate that sWBGT
      can substantially deviate from true ISO 7243 WBGT depending on solar load, cloud cover, and
      air movement. It does not carry a certified universal validity range.
    - Contrast with Liljegren Physical Modeling (Liljegren et al., 2008): Liljegren's model solves
      coupled energy balances for natural wet bulb (Tnw) and black globe (Tg) using radiation,
      pressure, and wind. SentinelHealth does NOT implement the Liljegren model.
    - Operational Proxy Status: Strictly a regional screening indicator (swbgt_screening_proxy).
      It MUST NOT be used to prescribe specific work-rest schedules or replace certified on-site
      occupational hygiene dosimetry. An approved occupational health playbook and on-site review
      are required before altering operational schedules.
    """
    ta = float(temperature_c)
    rh = max(1.0, min(100.0, float(relative_humidity)))

    # Magnus-Tetens vapor pressure formulation
    e = (rh / 100.0) * 6.105 * math.exp((17.27 * ta) / (237.7 + ta))
    swbgt = 0.567 * ta + 0.393 * e + 3.94
    return round(swbgt, 2)


def compute_consecutive_hours_above_threshold(values: List[float], threshold: float) -> int:
    """
    Computes the maximum run of consecutive hours where metric value >= threshold.
    Crucial for assessing unremitting physiological thermal load without recovery respite.
    """
    max_streak = 0
    current_streak = 0
    for v in values:
        if v >= threshold:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            current_streak = 0
    return max_streak


def extract_shift_exposure_metrics(
    hourly_records: List[NormalizedRecord],
    shifts: Optional[List[Tuple[str, int, int]]] = None,
    heat_threshold: float = DEFAULT_HEAT_INDEX_WARNING,
    wbgt_threshold: float = DEFAULT_WBGT_SCREENING_THRESHOLD,
    geography_id: Optional[str] = None,
    workplace_id: Optional[str] = None,
    data_label: str = "modelled",
    provenance: str = "Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
) -> List[NormalizedRecord]:
    """
    Extracts shift-level maximum exposure metrics from hourly environmental records.
    Default shifts (UTC):
      - morning_shift: 06:00 - 14:00 (hours 6..13)
      - afternoon_shift: 14:00 - 22:00 (hours 14..21)
      - night_shift: 22:00 - 06:00 (hours 22..5 next day)
    """
    if not hourly_records:
        return []

    if shifts is None:
        shifts = [
            ("morning_shift", 6, 14),
            ("afternoon_shift", 14, 22),
            ("night_shift", 22, 6),
        ]

    # Index hourly records by date and hour
    # Target apparent_temperature / heat_index and wbgt_screening_proxy
    hourly_by_time: Dict[str, Dict[datetime, float]] = {
        "apparent_temperature": {},
        "wbgt_screening_proxy": {},
    }

    now = datetime.now(timezone.utc)

    for rec in hourly_records:
        if rec.metric_code in hourly_by_time:
            hourly_by_time[rec.metric_code][rec.period_start] = rec.value

    app_temps = hourly_by_time["apparent_temperature"]
    wbgt_proxies = hourly_by_time["wbgt_screening_proxy"]

    if not app_temps and not wbgt_proxies:
        return []

    # Determine unique days in data
    all_timestamps = sorted(set(list(app_temps.keys()) + list(wbgt_proxies.keys())))
    if not all_timestamps:
        return []

    min_date = all_timestamps[0].date()
    max_date = all_timestamps[-1].date()

    shift_records: List[NormalizedRecord] = []
    current_date = min_date

    while current_date <= max_date:
        for shift_name, start_h, end_h in shifts:
            if start_h < end_h:
                shift_start = datetime(current_date.year, current_date.month, current_date.day, start_h, 0, tzinfo=timezone.utc)
                shift_end = datetime(current_date.year, current_date.month, current_date.day, end_h, 0, tzinfo=timezone.utc)
            else:
                # Overnight shift spanning midnight
                shift_start = datetime(current_date.year, current_date.month, current_date.day, start_h, 0, tzinfo=timezone.utc)
                next_day = current_date + timedelta(days=1)
                shift_end = datetime(next_day.year, next_day.month, next_day.day, end_h, 0, tzinfo=timezone.utc)

            # Collect hours falling within [shift_start, shift_end)
            shift_app_values = [
                val for ts, val in app_temps.items()
                if shift_start <= ts < shift_end
            ]
            shift_wbgt_values = [
                val for ts, val in wbgt_proxies.items()
                if shift_start <= ts < shift_end
            ]

            if not shift_app_values and not shift_wbgt_values:
                continue

            date_str = current_date.isoformat()
            shift_tag = f"{date_str}_{shift_name}"

            # 1. Shift-peak apparent temperature / heat index
            if shift_app_values:
                peak_hi = max(shift_app_values)
                hours_above_thresh = sum(1 for v in shift_app_values if v >= heat_threshold)
                mean_hi = round(sum(shift_app_values) / len(shift_app_values), 2)

                shift_records.append(
                    NormalizedRecord(
                        source_record_id=f"shift_peak_hi_{shift_tag}",
                        metric_code="shift_peak_apparent_temperature",
                        signal_family="environmental",
                        value=float(peak_hi),
                        unit="celsius",
                        period_start=shift_start,
                        period_end=shift_end,
                        observed_at=shift_end,
                        source_available_at=now,
                        geography_id=geography_id,
                        workplace_id=workplace_id,
                        location_basis="model_grid",
                        location_confidence="estimated",
                        data_label=data_label,
                        provenance=provenance,
                        quality_flags={
                            "shift_name": shift_name,
                            "shift_window_hours": len(shift_app_values),
                            "shift_mean_heat_index": mean_hi,
                            "aggregation": "shift_maximum",
                            "screening_context_only": True,
                        },
                    )
                )

                # 2. Shift duration (hours) above threshold
                shift_records.append(
                    NormalizedRecord(
                        source_record_id=f"shift_duration_hi_{shift_tag}",
                        metric_code="shift_hours_above_threshold",
                        signal_family="environmental",
                        value=float(hours_above_thresh),
                        unit="hours",
                        period_start=shift_start,
                        period_end=shift_end,
                        observed_at=shift_end,
                        source_available_at=now,
                        geography_id=geography_id,
                        workplace_id=workplace_id,
                        location_basis="model_grid",
                        location_confidence="estimated",
                        data_label=data_label,
                        provenance=provenance,
                        quality_flags={
                            "shift_name": shift_name,
                            "threshold_celsius": heat_threshold,
                            "aggregation": "shift_duration",
                            "screening_context_only": True,
                        },
                    )
                )

            # 3. Shift-peak WBGT screening proxy
            if shift_wbgt_values:
                peak_wbgt = max(shift_wbgt_values)
                wbgt_hours_above = sum(1 for v in shift_wbgt_values if v >= wbgt_threshold)

                shift_records.append(
                    NormalizedRecord(
                        source_record_id=f"shift_peak_wbgt_{shift_tag}",
                        metric_code="shift_peak_wbgt_screening",
                        signal_family="environmental",
                        value=float(peak_wbgt),
                        unit="celsius",
                        period_start=shift_start,
                        period_end=shift_end,
                        observed_at=shift_end,
                        source_available_at=now,
                        geography_id=geography_id,
                        workplace_id=workplace_id,
                        location_basis="model_grid",
                        location_confidence="estimated",
                        data_label=data_label,
                        provenance=provenance,
                        quality_flags={
                            "shift_name": shift_name,
                            "wbgt_screening_threshold": wbgt_threshold,
                            "wbgt_hours_above": wbgt_hours_above,
                            "scientific_caveat": "Modelled screening proxy only. Lacks black-globe radiant heat sensor and in-situ air velocity.",
                            "screening_context_only": True,
                        },
                    )
                )

        current_date += timedelta(days=1)

    return shift_records


def extract_daily_heat_metrics(
    hourly_records: List[NormalizedRecord],
    heat_threshold: float = DEFAULT_HEAT_INDEX_WARNING,
    geography_id: Optional[str] = None,
    workplace_id: Optional[str] = None,
    data_label: str = "modelled",
    provenance: str = "Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
) -> List[NormalizedRecord]:
    """
    Extracts daily summary heat metrics from hourly records:
      - daily_max_apparent_temperature
      - daily_max_temperature
      - daily_hours_above_threshold
      - consecutive_hours_above_threshold
    """
    if not hourly_records:
        return []

    now = datetime.now(timezone.utc)

    # Group values by metric and calendar day
    daily_values: Dict[str, Dict[str, List[Tuple[datetime, float]]]] = {
        "apparent_temperature": {},
        "ambient_temperature": {},
        "wbgt_screening_proxy": {},
    }

    for rec in hourly_records:
        if rec.metric_code in daily_values:
            d_key = rec.period_start.date().isoformat()
            daily_values[rec.metric_code].setdefault(d_key, []).append((rec.period_start, rec.value))

    daily_records: List[NormalizedRecord] = []
    all_days = sorted(set(
        list(daily_values["apparent_temperature"].keys())
        + list(daily_values["ambient_temperature"].keys())
    ))

    for d_str in all_days:
        day_date = datetime.fromisoformat(d_str).date()
        p_start = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0, tzinfo=timezone.utc)
        p_end = datetime(day_date.year, day_date.month, day_date.day, 23, 59, 59, tzinfo=timezone.utc)

        # 1. Daily Max Apparent Temperature & Consecutive Hours
        app_list = daily_values["apparent_temperature"].get(d_str, [])
        if app_list:
            app_list.sort(key=lambda x: x[0])
            vals = [v for _, v in app_list]
            daily_max_hi = max(vals)
            hours_above = sum(1 for v in vals if v >= heat_threshold)
            consecutive_hours = compute_consecutive_hours_above_threshold(vals, heat_threshold)

            daily_records.append(
                NormalizedRecord(
                    source_record_id=f"daily_max_hi_{d_str}",
                    metric_code="daily_max_apparent_temperature",
                    signal_family="environmental",
                    value=float(daily_max_hi),
                    unit="celsius",
                    period_start=p_start,
                    period_end=p_end,
                    observed_at=p_end,
                    source_available_at=now,
                    geography_id=geography_id,
                    workplace_id=workplace_id,
                    location_basis="model_grid",
                    location_confidence="estimated",
                    data_label=data_label,
                    provenance=provenance,
                    quality_flags={
                        "aggregation": "daily_maximum",
                        "total_hourly_observations": len(vals),
                        "screening_context_only": True,
                    },
                )
            )

            daily_records.append(
                NormalizedRecord(
                    source_record_id=f"consec_hours_hi_{d_str}",
                    metric_code="consecutive_hours_above_threshold",
                    signal_family="environmental",
                    value=float(consecutive_hours),
                    unit="hours",
                    period_start=p_start,
                    period_end=p_end,
                    observed_at=p_end,
                    source_available_at=now,
                    geography_id=geography_id,
                    workplace_id=workplace_id,
                    location_basis="model_grid",
                    location_confidence="estimated",
                    data_label=data_label,
                    provenance=provenance,
                    quality_flags={
                        "threshold_celsius": heat_threshold,
                        "cumulative_hours_above": hours_above,
                        "aggregation": "longest_unbroken_streak",
                        "screening_context_only": True,
                    },
                )
            )

            daily_records.append(
                NormalizedRecord(
                    source_record_id=f"daily_hours_hi_{d_str}",
                    metric_code="daily_hours_above_threshold",
                    signal_family="environmental",
                    value=float(hours_above),
                    unit="hours",
                    period_start=p_start,
                    period_end=p_end,
                    observed_at=p_end,
                    source_available_at=now,
                    geography_id=geography_id,
                    workplace_id=workplace_id,
                    location_basis="model_grid",
                    location_confidence="estimated",
                    data_label=data_label,
                    provenance=provenance,
                    quality_flags={
                        "threshold_celsius": heat_threshold,
                        "aggregation": "cumulative_hours",
                        "screening_context_only": True,
                    },
                )
            )

        # 2. Daily Max Ambient Temperature
        amb_list = daily_values["ambient_temperature"].get(d_str, [])
        if amb_list:
            amb_vals = [v for _, v in amb_list]
            daily_max_amb = max(amb_vals)
            daily_records.append(
                NormalizedRecord(
                    source_record_id=f"daily_max_temp_{d_str}",
                    metric_code="daily_max_temperature",
                    signal_family="environmental",
                    value=float(daily_max_amb),
                    unit="celsius",
                    period_start=p_start,
                    period_end=p_end,
                    observed_at=p_end,
                    source_available_at=now,
                    geography_id=geography_id,
                    workplace_id=workplace_id,
                    location_basis="model_grid",
                    location_confidence="estimated",
                    data_label=data_label,
                    provenance=provenance,
                    quality_flags={
                        "aggregation": "daily_maximum_dry_bulb",
                        "total_hourly_observations": len(amb_vals),
                        "screening_context_only": True,
                    },
                )
            )

    return daily_records


def extract_rolling_7d_context(
    daily_records: List[NormalizedRecord],
    geography_id: Optional[str] = None,
    workplace_id: Optional[str] = None,
    data_label: str = "modelled",
    provenance: str = "Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
) -> List[NormalizedRecord]:
    """
    Computes rolling 7-day multi-day background context from daily maximum records:
      - rolling_7d_mean_apparent_temperature
      - rolling_7d_peak_apparent_temperature

    MANDATORY SCIENTIFIC CONSTRAINT:
    Rolling 7-day trend metrics are designated STRICTLY for multi-day background context
    (tracking cumulative heat debt, community vulnerability, and sustained acclimatization deficit).
    They MUST NOT be used as the primary triggering mechanism for acute heat stress warnings,
    which require shift-peak and consecutive daytime hours for rapid life-safety response.
    """
    max_hi_records = [
        rec for rec in daily_records
        if rec.metric_code == "daily_max_apparent_temperature"
    ]
    if not max_hi_records:
        return []

    # Sort strictly by date
    max_hi_records.sort(key=lambda r: r.period_start)
    now = datetime.now(timezone.utc)
    rolling_records: List[NormalizedRecord] = []

    for i, current_rec in enumerate(max_hi_records):
        # Look back up to 6 preceding days + current day = 7 days
        start_idx = max(0, i - 6)
        window = max_hi_records[start_idx : i + 1]
        vals = [r.value for r in window]

        mean_7d = round(sum(vals) / len(vals), 2)
        peak_7d = max(vals)
        d_str = current_rec.period_start.date().isoformat()

        # Rolling 7-day mean
        rolling_records.append(
            NormalizedRecord(
                source_record_id=f"rolling_7d_mean_hi_{d_str}",
                metric_code="rolling_7d_mean_apparent_temperature",
                signal_family="environmental",
                value=float(mean_7d),
                unit="celsius",
                period_start=window[0].period_start,
                period_end=current_rec.period_end,
                observed_at=current_rec.observed_at,
                source_available_at=now,
                geography_id=geography_id,
                workplace_id=workplace_id,
                location_basis="model_grid",
                location_confidence="estimated",
                data_label=data_label,
                provenance=provenance,
                quality_flags={
                    "window_days": len(window),
                    "contextual_background_only": True,
                    "do_not_use_as_primary_acute_trigger": True,
                    "scientific_rationale": "Rolling 7-day trend serves strictly as multi-day background context. Acute warnings trigger on shift-peak and consecutive hours.",
                    "screening_context_only": True,
                },
            )
        )

        # Rolling 7-day peak
        rolling_records.append(
            NormalizedRecord(
                source_record_id=f"rolling_7d_peak_hi_{d_str}",
                metric_code="rolling_7d_peak_apparent_temperature",
                signal_family="environmental",
                value=float(peak_7d),
                unit="celsius",
                period_start=window[0].period_start,
                period_end=current_rec.period_end,
                observed_at=current_rec.observed_at,
                source_available_at=now,
                geography_id=geography_id,
                workplace_id=workplace_id,
                location_basis="model_grid",
                location_confidence="estimated",
                data_label=data_label,
                provenance=provenance,
                quality_flags={
                    "window_days": len(window),
                    "contextual_background_only": True,
                    "do_not_use_as_primary_acute_trigger": True,
                    "scientific_rationale": "Rolling 7-day trend serves strictly as multi-day background context. Acute warnings trigger on shift-peak and consecutive hours.",
                    "screening_context_only": True,
                },
            )
        )

    return rolling_records


def extract_all_heat_screening_features(
    hourly_records: List[NormalizedRecord],
    heat_threshold: float = DEFAULT_HEAT_INDEX_WARNING,
    wbgt_threshold: float = DEFAULT_WBGT_SCREENING_THRESHOLD,
    shifts: Optional[List[Tuple[str, int, int]]] = None,
    geography_id: Optional[str] = None,
    workplace_id: Optional[str] = None,
    data_label: str = "modelled",
    provenance: str = "Open-Meteo GFS/ICON Weather Model (Screening Context Only)",
) -> List[NormalizedRecord]:
    """
    Extracts complete multi-tier screening feature set (shift-level, daily summaries, rolling 7-day context)
    from hourly environmental records.
    """
    shift_recs = extract_shift_exposure_metrics(
        hourly_records=hourly_records,
        shifts=shifts,
        heat_threshold=heat_threshold,
        wbgt_threshold=wbgt_threshold,
        geography_id=geography_id,
        workplace_id=workplace_id,
        data_label=data_label,
        provenance=provenance,
    )

    daily_recs = extract_daily_heat_metrics(
        hourly_records=hourly_records,
        heat_threshold=heat_threshold,
        geography_id=geography_id,
        workplace_id=workplace_id,
        data_label=data_label,
        provenance=provenance,
    )

    rolling_recs = extract_rolling_7d_context(
        daily_records=daily_recs,
        geography_id=geography_id,
        workplace_id=workplace_id,
        data_label=data_label,
        provenance=provenance,
    )

    return shift_recs + daily_recs + rolling_recs
