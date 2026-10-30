# Validation Methodology & Replay Evaluation

## 1. Principles of Honest Surveillance Evaluation

Surveillance and early-warning systems cannot be validated using conventional random cross-validation or unconstrained train-test splits. Random temporal sampling introduces catastrophic lookahead leakage, leading to artificially inflated accuracy metrics and undetected operational failure during actual deployment.

SentinelHealth implements a strict **chronological replay engine** grounded in three core principles:
1. **Temporal Splitting**: Statistical baselines, moving averages, and anomaly detectors are calibrated exclusively on data preceding each simulated decision timestamp ($t \le \tau_{\text{decision}}$).
2. **Upstream Availability Gating**: Every observation is evaluated using only the data that was genuinely published and available upstream at that specific point in time (`source_available_at <= sim_time`). Ingestion delays, batch reporting lags, and weekend reporting pauses are preserved with temporal fidelity.
3. **Ground Truth Isolation**: Reference scenario labels and ground-truth event markers are isolated in an evaluation-only data store. Detection, fusion, and alerting algorithms have zero programmatic access to future observations or hidden scenario markers.

---

## 2. Standardized Surveillance Performance Metrics

| Metric | Code Definition | Interpretation & Operational Purpose |
|---|---|---|
| **Event Sensitivity** | `Matched Reference Events / Total Reference Events` | Proportion of true/synthetic hazard episodes successfully detected by the system within the permissible warning window. |
| **Alert PPV (Precision)** | `Matched Alert Episodes / Total Alert Episodes` | Proportion of generated alert episodes corresponding to genuine ground-truth hazards (deduplicated across active 72h episode windows). |
| **False-Alarm Burden** | `Unmatched Alert Episodes / Eligible Observation Weeks` | Operational workload imposed on occupational health and safety analysts (target: $< 0.5$ uncorroborated alerts per district-week). |
| **Detection Delay** | `Alert Time - Reference Event Onset Time` | Timeliness metric. Negative values represent pre-emptive early warning prior to clinical surge or widespread heat collapse. |
| **Useful-Action Lead Time** | `Latest Feasible Action Deadline - Alert Time` | Time margin available for preventive intervention (e.g. issuing hydration advisories, deploying cooling shelters, pausing heavy work). Positive only if sufficient time remains to avert harm. |
| **Compute Latency** | `Scoring Completion Time - Ingestion Time` | Real-time processing speed (benchmarked at $< 20\text{ ms}$). Distinct from epidemiological lead time. |

---

## 3. Heat Exposure Screening Validation

Phase 1B and Phase 2 establish specialized biometeorological exposure screening features within the surveillance engine. Replay evaluations benchmark these features against calibrated physical scenarios:

### 3.1 Multi-Tiered Exposure Architecture Evaluation
1. **Hourly Granularity Preservation**:
   - The replay engine validates that hourly diurnal thermal trajectories are preserved intact without lossy premature aggregation.
   - Sudden midday temperature spikes or rapid convective cooling are captured within 1 hour of upstream availability.
2. **Shift-Level Maximum Exposure Metrics**:
   - Evaluated across operational working shifts (Morning: 06:00–14:00, Afternoon: 14:00–22:00, Night: 22:00–06:00 UTC).
   - Validates that `shift_peak_apparent_temperature` and `shift_peak_wbgt_screening` correctly identify the maximum thermal burden experienced by the working shift, driving immediate preventive recommendations (mandatory rest cycles, cooling station access).
   - Validates that `shift_hours_above_threshold` accurately aggregates cumulative exposure duration within the shift boundary.
3. **Daily Summary Metrics & Consecutive Hours**:
   - Evaluates `daily_max_apparent_temperature`, `daily_max_temperature`, and `daily_hours_above_threshold`.
   - **Validation of `consecutive_hours_above_threshold`**: Physiological thermoregulation fails non-linearly under sustained unbroken heat exposure. 4 consecutive hours at $\ge 40^\circ\text{C}$ poses significantly higher exertional heat stroke risk than 4 non-consecutive hours interspersed with thermal respite. Replay tests verify that longest-streak algorithms correctly distinguish sustained heat crises from intermittent heat spikes.
4. **Validation of Rolling 7-Day Trend as Background Context**:
   - **Crucial Scientific Rule**: The rolling 7-day trend (`rolling_7d_mean_apparent_temperature`, `rolling_7d_peak_apparent_temperature`) must serve **STRICTLY as multi-day background context** (assessing cumulative fatigue, population dehydration debt, and acclimatization deficits).
   - **Detection Delay Avoidance**: If an early warning system triggers acute alerts based on a trailing 7-day moving average, a sudden-onset acute heat wave will not trigger an alert until day 3 or 4 of the event—by which time severe exertional heat stroke and occupational fatalities will have already occurred. The replay evaluation enforces that acute alerts trigger rapidly on shift-peak and consecutive daytime hours, while the 7-day trend is verified to modulate background risk without delaying acute warnings.

---

## 4. Scientific Caveats & Physical Limitations

### 4.1 Wet-Bulb Temperature ($T_w$) vs. WBGT
- **Psychrometric Wet-Bulb ($T_w$)**: Derived from dry-bulb temperature ($T_a$) and relative humidity ($RH$) using Stull's 2011 equation. It reflects the thermodynamic evaporative limit.
- **Wet-Bulb Globe Temperature (WBGT)** (ISO 7243 / OSHA / ACGIH):
  $$WBGT_{\text{outdoor}} = 0.7\,T_{nw} + 0.2\,T_g + 0.1\,T_a$$
  $$WBGT_{\text{indoor}} = 0.7\,T_{nw} + 0.3\,T_g$$
- **Validation Principle**: Replay evaluation tests confirm that `wbgt_screening_proxy` records are explicitly tagged as simplified modelled proxies. Algorithms must never represent ambient $T_a$ and $RH$ calculations as true in-situ WBGT dosimetry, because radiant solar heat flux (measured via black globe $T_g$) and microclimate air velocity ($v$) cannot be inferred from ambient dry-bulb and humidity alone.

### 4.2 Regional Modelled Screening vs. In-Situ Microclimates
- Open-Meteo NWP forecasts represent regional grid cells (1–10 km).
- Replay tests verify that records generated from regional models carry `location_basis="model_grid"`, `location_confidence="estimated"`, and `data_label="modelled"`.
- The system must not claim regional outdoor screening data reflects enclosed indoor factories, uninsulated metal warehouses, or direct proximity to industrial heat sources.

### 4.3 Heat Index Assumptions
- NOAA Heat Index Rothfusz calculations assume shaded conditions and light air velocity (~5 knots / 2.5 m/s).
- Direct solar radiation can increase effective heat strain by up to 8°C (15°F).
- Protective equipment (PPE) severely restricts evaporative cooling, lowering safe thermal thresholds.

---

## 5. Calibrated Synthetic Benchmark Scenarios

SentinelHealth includes 5 calibrated synthetic scenarios to stress-test detection, fusion, and replay validation without fabricating or exposing real-world patient records:

1. `heat-gradual` (45 days):
   - **Profile**: Multi-day gradual increase in apparent temperature (days 31–38 reaching peak $41^\circ\text{C}$ to $43^\circ\text{C}$), corroborated by rising workforce sickness absence and clinical contacts.
   - **Expected Outcome**: Triggers Corroborated Health Warning with negative Detection Delay (pre-emptive alert $\ge 24\text{ hours}$ before clinical peak).
2. `stable-background` (60 days):
   - **Profile**: 60 days of seasonal temperature fluctuations and normal baseline health contacts without hazardous anomalies.
   - **Expected Outcome**: Zero false-alarm alerts generated (False-Alarm Burden $= 0.0$ alerts/week).
3. `environmental-only` (30 days):
   - **Profile**: Severe heat wave ($> 42^\circ\text{C}$) occurring over an operational facility with resilient indoor climate control and adequate hydration, resulting in zero clinical or workforce anomalies.
   - **Expected Outcome**: Triggers `Environmental Watch` (advisory level), verifying the system does NOT generate false corroborated health warnings when health data remains normal.
4. `clinical-only` (30 days):
   - **Profile**: Abrupt spike in clinic visits during mild seasonal weather ($24^\circ\text{C}$).
   - **Expected Outcome**: Triggers `Uncorroborated Health Anomaly` advisory for operational epidemiologist review, without falsely attributing the surge to heat stress.
5. `missing-data` (30 days):
   - **Profile**: Complete upstream outage of workforce and clinical feeds during an ongoing heat wave.
   - **Expected Outcome**: Graceful degradation to `insufficient_data` and standalone environmental monitoring without system crash or stale data assumptions.

---

## 6. Synthetic Isolation & Privacy Assurance

All validation scenarios and offline test fixtures adhere strictly to surveillance privacy standards:
- **Zero PII**: No names, employee IDs, national identity numbers, patient record IDs, or individual health records exist in benchmark scenarios or test fixtures.
- **Strictly Aggregate**: Health and workforce metrics are represented exclusively as aggregate counts (`encounters`, `worker_days`) with contributor counts $\ge 10$.
- **Synthetic Marking**: All fictional fixture files, scenario datasets, and replay test outputs are explicitly labeled with `data_label="synthetic"` and `provenance="offline_synthetic_fixture"`.
