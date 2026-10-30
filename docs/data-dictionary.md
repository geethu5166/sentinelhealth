# SentinelHealth Data Dictionary

## Overview
SentinelHealth enforces strict, versioned schemas across all aggregate ingestion contracts and internal database tables. All timestamps are persisted in **UTC** with timezone awareness (`timestamptz`). Local displays use IANA identifiers (default: `Asia/Kolkata`).

All data ingested and processed by SentinelHealth represents strictly aggregate surveillance indicators. No Personally Identifiable Information (PII) or individual clinical records are ingested, stored, or processed. Fictional test fixtures and benchmarks are explicitly marked with `data_label="synthetic"`.

---

## 1. Relational Entities

### `tenants`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | Primary Key | Unique tenant identifier. |
| `name` | VARCHAR(255) | NOT NULL | Official tenant organization name. |
| `slug` | VARCHAR(100) | UNIQUE, NOT NULL | URL-safe machine identifier (e.g. `district_health_authority`). |
| `display_name` | VARCHAR(255) | NULLABLE | Human-friendly name displayed in UI. |
| `is_active` | BOOLEAN | DEFAULT TRUE | Status flag. |
| `settings` | JSON | DEFAULT `{}` | Tenant-specific configuration (threshold overrides, timezone). |

### `signal_records`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | Primary Key | Unique signal record identifier. |
| `tenant_id` | UUID | FK `tenants.id`, RLS | Tenant boundary. |
| `source_id` | UUID | FK `data_sources.id` | Originating data source connector. |
| `source_record_id` | VARCHAR(255) | NOT NULL | External provenance identifier. |
| `record_version` | INTEGER | DEFAULT 1 | Increments upon upstream source revisions. |
| `schema_version` | VARCHAR(50) | NOT NULL | Contract schema specification version. |
| `signal_family` | ENUM | NOT NULL | `environmental`, `clinical_service`, `workforce`, `workplace_safety`, `laboratory`. |
| `metric_code` | VARCHAR(100) | NOT NULL | Standardized metric code (e.g. `apparent_temperature`, `shift_peak_apparent_temperature`). |
| `value` | NUMERIC(14,4) | NOT NULL | Reported aggregate numeric measure. |
| `unit` | VARCHAR(50) | NOT NULL | Standard measurement unit (e.g. `celsius`, `hours`, `encounters`, `worker_days`). |
| `numerator` | NUMERIC(14,4) | NULLABLE | Raw count of occurrences. |
| `denominator` | NUMERIC(14,4) | NULLABLE | Exposure denominator (e.g. total scheduled shifts). |
| `denominator_unit` | VARCHAR(50) | NULLABLE | Denominator measurement unit. |
| `contributor_count` | INTEGER | NULLABLE | Upstream-attested distinct human contributors. |
| `contributor_definition` | VARCHAR(255) | NULLABLE | e.g. `unique_patients`, `distinct_absent_workers`. |
| `period_start` | TIMESTAMPTZ | NOT NULL | Beginning of observation time window. |
| `period_end` | TIMESTAMPTZ | NOT NULL | End of observation time window. |
| `observed_at` | TIMESTAMPTZ | NOT NULL | Time the phenomenon was observed/measured. |
| `source_available_at`| TIMESTAMPTZ | NOT NULL | Time the upstream feed made the data available. |
| `ingested_at` | TIMESTAMPTZ | DEFAULT NOW() | System ingestion time. |
| `geography_id` | UUID | FK `geographies.id` | Aggregate district/zone mapping. |
| `workplace_id` | UUID | FK `workplaces.id` | Specific workplace site mapping (optional). |
| `location_basis` | ENUM | NOT NULL | `residence`, `workplace`, `exposure_site`, `facility`, `catchment`, `model_grid`, `unknown`. |
| `location_confidence`| ENUM | NOT NULL | `exact`, `mapped`, `estimated`, `unknown`. |
| `data_label` | ENUM | NOT NULL | `real`, `synthetic`, `modelled`, `observed`. |
| `is_current` | BOOLEAN | DEFAULT TRUE | False if superseded by a revised version. |

### `alerts`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | Primary Key | Unique alert identifier. |
| `tenant_id` | UUID | FK `tenants.id`, RLS | Tenant boundary. |
| `hazard` | ENUM | NOT NULL | `heat_illness`, `respiratory_air_quality`, `infectious_disease`, `workplace_safety`, `data_quality`. |
| `evidence_class` | ENUM | NOT NULL | `environmental_watch`, `corroborated_health_warning`, `uncorroborated_health_anomaly`, `safety_escalation`, `insufficient_data`. |
| `severity` | ENUM | NOT NULL | `advisory`, `watch`, `warning`, `critical`, `emergency`. |
| `status` | ENUM | NOT NULL | `new`, `acknowledged`, `investigating`, `action_planned`, `monitoring`, `resolved`, `dismissed_data_issue`, `dismissed_not_actionable`, `reopened`. |
| `geography_id` | UUID | FK `geographies.id` | District/zone where warning applies. |
| `responsible_role` | VARCHAR(100) | NOT NULL | Designated operational role accountable for review. |
| `evidence_score` | NUMERIC(10,4) | NOT NULL | 0–100 operational ranking score (not disease probability). |
| `episode_key` | VARCHAR(255) | NOT NULL | Deduplication key across time window. |

---

## 2. Privacy & Disclosure Control Rules

1. **Strictly Non-PII**: SentinelHealth exclusively ingests and processes anonymized, aggregate surveillance counts and model grid forecasts. No names, national IDs, addresses, patient record numbers, or precise geo-coordinates of individuals are ever collected.
2. **Contributor Count Rule**: If `contributor_count` is known and `< 10`, the metric is masked (`value = null`, `is_suppressed = true`).
3. **Small-Cell Suppression**: Counts between `1` and `4` inclusive are masked for sensitive health metrics.
4. **True Zero Handling**: Zero is preserved when it does not disclose an individual condition; unknown and suppressed values are never coerced to zero.
5. **Complementary Suppression**: In tabular rollups with one suppressed cell, the smallest non-zero cell is also suppressed to prevent marginal derivation.
6. **Synthetic Isolation**: Deterministic benchmark fixtures are strictly tagged `data_label="synthetic"` and stored in isolated fixture repositories.

---

## 3. Environmental Metric Definitions & Exposure Screening Features

SentinelHealth establishes a multi-tiered heat exposure screening architecture designed to provide timely operational awareness while respecting physical biometeorological boundaries.

### 3.1 Metric Code Registry

| Metric Code | Signal Family | Unit | Temporal Granularity | Description | Scientific & Operational Purpose |
|---|---|---|---|---|---|
| `ambient_temperature` | `environmental` | `celsius` | Hourly | Dry-bulb air temperature ($T_a$) measured at 2m above ground. | Baseline meteorological variable from regional NWP models (Open-Meteo GFS/ICON). Macro screening context only. |
| `relative_humidity` | `environmental` | `percent` | Hourly | Ambient relative humidity ($RH$) at 2m. | Required for psychrometric wet-bulb, apparent temperature, and vapor pressure calculations. |
| `apparent_temperature` | `environmental` | `celsius` | Hourly | Perceived temperature / Heat Index combining $T_a$, $RH$, and wind. | Standard screening index for human thermoregulatory load under shaded conditions. |
| `wet_bulb_temperature` | `environmental` | `celsius` | Hourly | Psychrometric wet-bulb temperature ($T_w$) calculated via Stull (2011). | Thermodynamic limit of evaporative cooling. **NOTE: $T_w \neq WBGT$**. |
| `wbgt_screening_proxy` | `environmental` | `celsius` | Hourly | Simplified Wet-Bulb Globe Temperature proxy (Australian BOM formula). | Shaded/indoor screening estimate based on $T_a$ and vapor pressure $e$. **Lacks radiant globe sensor**. |
| `wind_speed` | `environmental` | `km/h` | Hourly | Surface wind velocity at 10m. | Convective cooling context for regional screening. |
| `shift_peak_apparent_temperature` | `environmental` | `celsius` | Shift (8-hour) | Maximum hourly apparent temperature observed during an operational shift. | Primary trigger for workplace heat illness prevention (hydration pauses, cooling breaks). |
| `shift_peak_wbgt_screening` | `environmental` | `celsius` | Shift (8-hour) | Maximum hourly WBGT screening proxy observed during an operational shift. | Occupational screening action level for moderate-to-heavy physical work. |
| `shift_hours_above_threshold` | `environmental` | `hours` | Shift (8-hour) | Total hours during the shift exceeding safety threshold (e.g. $\ge 38^\circ\text{C}$). | Quantifies shift-level heat exposure duration for administrative work-rest cycling. |
| `daily_max_apparent_temperature` | `environmental` | `celsius` | Daily | Peak apparent temperature across the 24-hour UTC calendar day. | Evaluates diurnal peak thermal severity across the surveillance district. |
| `daily_max_temperature` | `environmental` | `celsius` | Daily | Peak ambient dry-bulb temperature across the 24-hour UTC day. | Tracks meteorological heat wave classification. |
| `daily_hours_above_threshold` | `environmental` | `hours` | Daily | Total cumulative hours in the day exceeding safety threshold ($\ge 38^\circ\text{C}$). | Cumulative daytime thermal load measure. |
| `consecutive_hours_above_threshold` | `environmental` | `hours` | Daily | Longest unbroken sequence of hours where apparent temperature $\ge$ threshold. | **Critical physiological metric**: Unremitting heat without recovery breaks induces severe thermoregulatory failure. |
| `rolling_7d_mean_apparent_temperature` | `environmental` | `celsius` | 7-Day Rolling | 7-day trailing moving average of daily maximum apparent temperatures. | **Contextual background only**: Tracks cumulative community heat debt and acclimatization deficit. |
| `rolling_7d_peak_apparent_temperature` | `environmental` | `celsius` | 7-Day Rolling | Highest daily maximum apparent temperature recorded in the past 7 days. | Identifies multi-day heatwave persistence. Never used as sole acute trigger. |
| `heat_exhaustion_contacts` | `clinical_service` | `encounters` | Daily / Shift | Aggregate clinical encounters matching syndromic heat exhaustion / heat stress. | Health outcome corroboration. Upstream aggregated; small cells masked. |
| `sickness_absence_worker_days` | `workforce` | `worker_days` | Daily / Shift | Total unscheduled sickness absence across scheduled worker shifts. | Workplace impact corroboration. Population aggregate measure; no individual diagnostic attribution. |

---

## 4. Scientific Foundations & Biometeorological Caveats

### 4.1 Regional Modelled Screening vs. In-Situ Workplace Dosimetry
Open-Meteo feeds and numerical weather prediction (NWP) model grids represent macro-scale atmospheric estimates interpolated over grid cells (typically 1–10 km resolution). 
- **Macro Screening Context**: These data points provide critical early warnings of broad environmental hazards across geographic districts.
- **Physical Boundary**: They do **NOT** measure microclimates inside industrial facilities, under uninsulated metal roofs, inside vehicle cabs, deep in underground quarries, or adjacent to high-temperature industrial equipment (furnaces, asphalt pavers, steam pipes).
- **Surveillance Designation**: All records derived from Open-Meteo are strictly labeled with `location_basis="model_grid"`, `location_confidence="estimated"`, and `data_label="modelled"`. They serve as screening triggers for preventive administrative controls, not as legal replacements for in-situ industrial hygiene dosimetry.

### 4.2 Wet-Bulb Temperature ($T_w$) vs. Wet-Bulb Globe Temperature (WBGT)
A widespread error in environmental health systems is treating psychrometric wet-bulb temperature as equivalent to Wet-Bulb Globe Temperature. SentinelHealth explicitly distinguishes these quantities:

1. **Psychrometric Wet-Bulb Temperature ($T_w$)**:
   - Represents the lowest temperature air can reach through evaporative water cooling under current thermodynamic conditions.
   - Calculated using dry-bulb temperature ($T_a$) and relative humidity ($RH$) (e.g. via Stull's 2011 formulation).
   - Reflects the thermodynamic barrier to sweat evaporation.

2. **Wet-Bulb Globe Temperature (WBGT)** (ISO 7243 / OSHA / ACGIH / NIOSH standard):
   - Outdoors with direct solar radiation:
     $$WBGT_{\text{outdoor}} = 0.7\,T_{nw} + 0.2\,T_g + 0.1\,T_a$$
   - Indoors or shaded environments:
     $$WBGT_{\text{indoor}} = 0.7\,T_{nw} + 0.3\,T_g$$
     where $T_{nw}$ is the *natural* wet-bulb temperature (measured with natural air movement), $T_g$ is the *black-globe temperature* (measured inside a 150mm matte-black copper sphere capturing mean radiant solar and thermal radiation), and $T_a$ is dry-bulb air temperature.

3. **Fundamental Limitation**:
   > [!WARNING]
   > **WBGT cannot be calculated from ambient dry-bulb temperature and relative humidity alone.**
   > Radiant heat flux ($T_g$) and natural air velocity ($v$) are physical prerequisites. Formulations derived purely from $T_a$ and $RH$ (such as the Australian BOM formula) are strictly simplified screening proxies under assumed shaded conditions with light air movement. In direct radiant sunlight or near industrial furnaces, true workplace WBGT can exceed the proxy by several degrees Celsius.

### 4.3 Heat Index Assumptions & Radiant Adjustments
- The NOAA Heat Index (Rothfusz polynomial regression) is calibrated to Steadman's biometeorological model, which explicitly assumes:
  - Human walking in full shade.
  - Light wind velocity of 5 knots (~2.5 m/s or 9 km/h).
  - Light clothing (shorts and light shirt).
- **Direct Sunlight Exposure**: Unshaded exposure in direct radiant sunlight can add up to **8°C (15°F)** to effective perceived heat strain.
- **Protective Clothing & PPE**: Workers wearing impermeable chemical suits, flame-resistant coveralls, heavy vests, or respirators experience severe restriction of evaporative sweat dissipation. Safe thermal action levels must be adjusted downwards by 2–5°C when heavy PPE is required.

### 4.4 Operational Role of Rolling 7-Day Trend vs. Acute Triggers
> [!IMPORTANT]
> **Rolling 7-day trend metrics are designated STRICTLY for multi-day background context.**
> They must **NEVER** serve as the primary triggering mechanism for acute workplace heat stress warnings.
> 
> **Scientific Rationale**:
> Exertional heat illness and heat stroke are acute physiological events governed by immediate shift-level peak thermal load and unbroken consecutive hours of exposure. A worker engaged in heavy manual labor can succumb to heat stroke within 2 hours of a sudden extreme heat spike. If an alert system waits for a 7-day trailing moving average to exceed threshold, the warning will arrive days too late.
> 
> Therefore, in SentinelHealth:
> - **Acute Alerts (Watches & Warnings)** trigger immediately on **shift-peak apparent temperature / WBGT screening proxy** and **consecutive daytime hours $\ge$ threshold**.
> - **Rolling 7-Day Trends** provide secondary context for assessing cumulative population fatigue, chronic hydration deficits, and community acclimatization status.
---

## 3. Environmental Metric Definitions & Exposure Screening Features

### 3.1 Metric Code Registry
| Metric Code | Signal Family | Unit | Description | Scientific / Operational Limitations |
|---|---|---|---|---|
| `ambient_temperature` | `environmental` | `celsius` | Dry-bulb ambient air temperature ($T_a$) at 2 meters. | Regional numerical weather model (Open-Meteo NWP grid). Not an on-site workplace sensor. |
| `apparent_temperature` | `environmental` | `celsius` | Modelled heat index combining dry-bulb temperature, humidity, and wind. | Assumes shady conditions and light wind (approx. 5 knots). Direct solar radiation increases effective thermal stress by up to 8°C (15°F). |
| `plant_wbgt_sensor` | `environmental` | `celsius` | On-site Wet-Bulb Globe Temperature (fictional plant IoT sensor). | Combines natural wet-bulb ($T_{nw}$), black-globe ($T_g$), and dry-bulb ($T_a$). Used strictly for Tenant B workplace screening. |
| `pm25_concentration` | `environmental` | `ug/m3` | Fine particulate matter ($PM_{2.5}$) mass concentration. | Modelled atmospheric CAMS reanalysis. Screening context only. |
| `heat_exhaustion_contacts` | `clinical_service` | `encounters` | Aggregate clinic/ED consultations matching heat-illness ICD/syndromic codes. | Upstream aggregate numerator with strictly protected small cells ($<5$ masked). |
| `sickness_absence_worker_days` | `workforce` | `worker_days` | Aggregate unscheduled sickness absence across workforce shifts. | Non-specific health indicator. Does NOT establish individual causation or specific medical diagnosis. |

### 3.2 Scientific Constraints on Heat Modeling
> [!IMPORTANT]
> 1. **Wet-Bulb Temperature $\neq$ WBGT**: Natural Wet-Bulb Globe Temperature requires physical radiant heat measurement via black-globe thermometer and air movement. WBGT cannot be computed from temperature and relative humidity alone.
> 2. **Regional Screening vs On-Site Sensor**: Open-Meteo feeds provide regional atmospheric screening context. They are never conflated with on-site workplace sensors.
> 3. **Screening Granularity**:
>    - **Hourly Granularity**: Preserved for fine-grained temporal alignment.
>    - **Shift-Level Peak Exposure**: Peak temperature/apparent temperature during operational working shifts (e.g. 08:00–16:00).
>    - **Daily Exposure Duration**: Continuous hours exceeding thermal safety threshold (e.g. $\ge 38^\circ\text{C}$ for $\ge 3$ consecutive hours).
>    - **7-Day Rolling Trend**: Retained strictly as background context; never used as the sole trigger for acute workplace warnings.


