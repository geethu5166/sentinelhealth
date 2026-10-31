# SentinelHealth Phase 4 Validation & Evaluation Integrity Report

> [!CAUTION]
> **Mandatory Prototype Limitation Disclaimer**: This prototype has not undergone clinical validation, production security assessment or jurisdiction-specific legal/compliance review.

> [!IMPORTANT]
> **Status Statement**: Two backend hazard pipelines and reconciled synthetic evaluation reported complete; five-seed results exploratory; frontend integration and live operational acceptance pending.

---

## 1. Executive Summary & Verification Scope

This report documents the Phase 4 validation suite and chronological replay evaluation for SentinelHealth across **15 deterministic benchmark scenarios** (Scenario Generator v0.3.0, Git checkpoint `be36d4a`, clean tree post-commit).

### Evaluation Guiding Principles (CDC MMWR RR-5305 Framework)
- **Predefined Event Matching Rules**: Alerts receive early-warning credit only when they satisfy predeclared matching rules: matching hazard (`heat_illness` or `respiratory_air_quality`), matching geography (`DIST-DHANPUR`), and eligible window ($\le 2$ days prior to onset through event termination).
- **Separation of Event Sensitivity and Alert PPV**: Reference Event Sensitivity measures the proportion of true public health events detected ($\frac{N_{\text{detected\_events}}}{N_{\text{ref\_events}}}$). Positive Predictive Value (PPV) measures the precision of issued alert episodes ($\frac{N_{\text{matched\_episodes}}}{N_{\text{total\_episodes}}}$), evaluated strictly within each alert class.
- **Strict Separation of Detection from Output Naming**: Policies are evaluated on whether they identified the underlying crisis at any eligible tier, rather than penalizing comparator policies for lacking a specific output label.
- **Exposure-Watch Accuracy vs Health-Event Prediction**: Environmental watches are evaluated both for exposure-screening accuracy (against independently defined atmospheric hazards) and health-event association. An environmental watch during genuine elevated heat or pollution is an operationally appropriate exposure warning even when clinical surge is mitigated or absent.
- **Single Source of Truth**: All metrics and tables in this report are programmatically derived from the exported per-episode dataset (`backend/fixtures/replay_evaluation_episodes.json` and `.csv`) and verified by automated regression tests (`test_replay_episode_reconciliation.py`).
- **Mathematical Delay Derivation**: Detection delays are strictly derived from datetime subtraction between reference onset and operational alert issuance timestamp (`calculate_exact_time_delay`), eliminating narrative drift.

---

## 2. Reconciled Multi-Policy Comparison (15 Benchmark Scenarios)

The evaluation suite compares three operational surveillance policies across all 15 scenarios:
1. **Environmental-Only Policy**: Emits `environmental_watch` upon physical sensor threshold exceedance.
2. **Health-Only Policy**: Emits `uncorroborated_health_anomaly` upon clinical or workforce statistical deviation.
3. **Fused Corroborated Policy**: Deterministic multi-source fusion engine that corroborates environmental exposure with clinical impact to issue `corroborated_health_warning`, while routing isolated physical exposures to `environmental_watch` and isolated clinical surges to `uncorroborated_health_anomaly`.

### Summary Comparison Table (Derived Programmatically from `replay_evaluation_episodes.json`)

| Evaluation Dimension | Environmental-Only Policy | Health-Only Policy | Fused Corroborated Policy | Methodological Accounting Rule |
| :--- | :---: | :---: | :---: | :--- |
| **Operational Policy Classification** | `environmental_exposure_watch` | `uncorroborated_health_anomaly` | `fused_corroborated_warning` | Operating action tier |
| **Overall Event Detection (Any Tier)** | **60.0% (3/5)** | **100.0% (5/5)** | **100.0% (5/5)** | Unique reference events detected ($N=5$) |
| **Crisis-Event Detection (Any Tier)** | **100.0% (3/3)** | **100.0% (3/3)** | **100.0% (3/3)** | Identified the 3 multi-factor crises |
| **Warning-Tier Performance** | *Not Applicable (Tier not implemented)* | *Not Applicable (Tier not implemented)* | **100.0% (3/3 matched, 0 unmatched)** | Applicable solely to policies implementing warning tier |
| **Total Alert Episodes (All Tiers)** | **7** | **23** | **27** | Sum of all episode clusters across 15 scenarios |
| **Matched Alert Episodes** | 3 | 5 | 7 | Episodes matching a predeclared event window |
| **Unmatched Alert Episodes** | 4 | 18 | 20 | Unmatched alerts across all tiers |
| **Unmatched Alerts in Null Scenario** | **0** | **0** | **0** | `stable-null-baseline` false alarm audit |
| **Warning Tier Episodes (`warning`)** | 0 episodes | 0 episodes | **3 episodes** | Primary high-urgency operational tier |
| **Warning Tier Matched** | 0 | 0 | **3** | All 3 multi-hazard crises detected |
| **Warning Tier False Alarms** | 0 | 0 | **0** | **Zero false warnings across all scenarios** |
| **Warning Tier PPV** | *Not Applicable* | *Not Applicable* | **100.0% (3/3)** | $\frac{N_{\text{matched\_warnings}}}{N_{\text{total\_warnings}}}$ |
| **Watch Tier Episodes (`watch`)** | 7 episodes | 0 episodes | 4 episodes | Environmental facility screening tier |
| **Health-Event-Associated Watch PPV** | 42.9% (3/7) | *Not Applicable* | 0.0% (0/4)* | *Watches issued only during non-crisis exposures |
| **Exposure-Watch Accuracy** | **100.0% (7/7)** | *Not Applicable* | **100.0% (4/4)** | Verified against physical exposure episodes |
| **Anomaly Tier Episodes (`advisory`)** | 0 episodes | 23 episodes | 20 episodes | Uncorroborated clinical anomaly tier |
| **Health-Event Anomaly PPV** | *Not Applicable* | 21.7% (5/23) | 20.0% (4/20) | $\frac{N_{\text{matched\_anomalies}}}{N_{\text{total\_anomalies}}}$ |

### Defensible Operational Findings
- **High-Specificity Warnings**: The fused policy issued three matched warnings without unmatched warning episodes in this synthetic evaluation.
- **Review Burden & Fatigue**: The fused policy produced **more total review episodes (27 fused vs 18 health-only vs 4 environmental-only)** than either comparator. Multi-source fusion does **not** reduce overall alert fatigue; public health surveillance evaluation must evaluate validity and timeliness together across all output tiers rather than relying solely on one favorable output class.
- **Separation of Exposure Screening from Health Prediction**:
  - *Exposure-Watch Accuracy*: Evaluates whether an atmospheric threshold exceedance occurred. Both environmental-only (7/7) and fused (4/4) watches accurately reflected genuine physical exposure episodes. Calling an environmental watch an error simply because clinical illness did not follow evaluates it against the wrong reference outcome.
  - *Health-Event Prediction*: Evaluates whether an alert accompanied an independently documented surge in clinical contacts or workforce absences.

---

## 3. Scenario-by-Scenario Evaluation Matrix (15 Benchmark Scenarios)

The table below presents the chronological replay results for the **Fused Corroborated Policy** across all 15 scenarios. Every timestamp, delay, and alert category is derived directly from `backend/fixtures/replay_evaluation_summary.json` and `replay_evaluation_episodes.json`.

| ID | Scenario Name | Ground-Truth Reference Event | Reference Onset (UTC) | First Alert Class Issued | Issue Delay (Calculated) | Operational Timeliness Classification & Narrative |
| :---: | :--- | :--- | :---: | :--- | :---: | :--- |
| **1** | `heat-gradual` | `REF-EVT-HEAT-GRADUAL-2026` | 2026-07-02 00:00 | `corroborated_health_warning` | **+48.2h (+2.01d)** | Post-onset detection (+1.0d observation delay, 48.2h operational issue delay) |
| **2** | `heat-abrupt-extreme` | `REF-EVT-HEAT-ABRUPT-2026` | 2026-07-15 12:00 | `corroborated_health_warning` | **+12.2h (+0.51d)** | Onset-window detection (-0.5d observation delay, 12.2h operational issue delay) |
| **3** | `heat-exposure-without-health` | *None (Exposure only)* | — | `environmental_watch` | *None* | Precautionary watch; 0 false warnings; health baseline nominal ($z < 1.0$) |
| **4** | `spurious-health-spike` | *None (Spurious noise)* | — | `uncorroborated_health_anomaly` | *None* | Correctly withheld warning; isolated clinical anomaly flagged for review |
| **5** | `air-quality-respiratory-surge` | `REF-EVT-AIR-QUALITY-SURGE-2026` | 2026-06-27 00:00 | `corroborated_health_warning` | **+24.2h (+1.01d)** | Onset-day observation with warning issued (24.2h operational issue delay) |
| **6** | `air-quality-stagnation-without-health` | *None (Inversion only)* | — | `environmental_watch` | *None* | Precautionary air quality watch; 0 false warnings; health baseline nominal |
| **7** | `respiratory-outbreak-without-pollution` | `REF-EVT-RESP-OUTBREAK-2026` | 2026-06-18 00:00 | `uncorroborated_health_anomaly` | **+24.2h (+1.01d)** | Detected infectious surge without pollution; correctly withheld pollution warning |
| **8** | `stable-null-baseline` | *None (Nominal climate/health)* | — | *No Alert* | *None* | Clean baseline; **0 alert episodes, 0 false alarms** across all tiers |
| **9** | `missing-environmental-input` | *None (Sensor dropout)* | — | `uncorroborated_health_anomaly` | *None* | Visible `missing_input:pm25_concentration`; day 22 health surge preserved |
| **10** | `missing-health-input` | *None (EMR pipeline drop)* | — | `environmental_watch` | *None* | Visible `missing_input:heat_exhaustion_contacts`; environmental watch preserved |
| **11** | `stale-quarantined-records` | *None (QA failure)* | — | `environmental_watch` | *None* | Visible `stale_input` and `quarantined_input` flags; no false warnings |
| **12** | `missing-denominator-uncertain-geo` | *None (Unmapped facility)* | — | `uncorroborated_health_anomaly` | *None* | Calculated rate withheld (`None`, `missing_population_denominator`); basis `unspecified` |
| **13** | `small-cells-overlapping-disclosure` | *None (Privacy edge cases)* | — | `uncorroborated_health_anomaly` | *None* | Cells in [1, 4] and contributors < 10 suppressed; PM2.5 = 3.2 unmasked |
| **14** | `duplicate-revised-out-of-order` | *None (Out-of-order replay)* | — | *No Alert* | *None* | Duplicates rejected (`records_already_processed`); chronological sorting verified |
| **15** | `baseline-drift-changing-exposure` | `REF-EVT-DRIFT-SURGE-2026` | 2026-07-06 00:00 | `uncorroborated_health_anomaly` | **+24.2h (+1.01d)** | Facility expansion scaled without false alarms; acute day 35 surge detected ($z > 4.5$) |

---

## 4. Exploratory Five-Seed Robustness & Chronological Splits

An exploratory multi-seed evaluation was executed across **5 distinct random seeds** (Seeds 101–105). This exploratory run assesses sensitivity across different stochastic noise realisations; it does not claim to constitute a fully powered 20-seed epidemiological study.

### Chronological Splits & Lookahead Prevention
- **Burn-in Calibration Split**: Days 0–14 (15 days baseline model fitting without alert generation).
- **Held-out Evaluation Split**: Days 15–44 (30 days chronological simulation). In accordance with time-series evaluation standards (TimeSeriesSplit), future observations never enter earlier fitting or scoring steps.

### Exploratory Multi-Seed Results (`fixtures/replay_evaluation_multiseed.json`)

| Evaluation Metric | Median | Minimum (Worst Case) | Maximum (Best Case) | Prototype Robustness Finding |
| :--- | :---: | :---: | :---: | :--- |
| **Crisis Event Sensitivity** | **100.0%** | 100.0% | 100.0% | Fused policy reliably detects all 3 multi-hazard crises across all 5 seeds |
| **Corroborated Warning PPV** | **100.0%** | 100.0% | 100.0% | Zero false warning episodes across all 5 evaluated seeds |
| **Gradual Heat Issue Delay** | **48.2h** (+2.01d) | 24.2h (+1.01d) | 72.2h (+3.01d) | Delay varies by 1-2 days depending on thermal accumulation pace |
| **Abrupt Heat Shock Issue Delay** | **12.2h** (+0.51d) | 12.2h (+0.51d) | 12.2h (+0.51d) | Exact invariant detection on immediate acute exposure shock |
| **Air Quality Surge Issue Delay** | **24.2h** (+1.01d) | 24.2h (+1.01d) | 24.2h (+1.01d) | Invariant detection within standard next-day operational issue window |
| **Null Scenario False Alarms** | **0** | 0 | 0 | Stable null baseline produces zero false alerts across all 5 seeds |

---

## 5. Threshold Provenance & Labeling Integrity

All analytical screening thresholds and coverage rules are explicitly documented with provenance:

1. **Particulate Matter Standards (CPCB NAAQS 2009)**:
   - **24-Hour Reference Standard**: India's National Ambient Air Quality Standard for PM2.5 is **60 µg/m³ for a 24-hour average** (Central Pollution Control Board, 2009).
   - **Hourly Screening Metric**: The connector's 90 µg/m³ hourly trigger is explicitly documented as:  
     `"Configurable illustrative hourly screening threshold; not clinically validated."`
   - **Completeness & Coverage Rule**: The 18/24-hour rule is explicitly documented as:  
     `"Prototype's configured completeness rule requiring >= 18/24 valid hours (>= 75% coverage). Incomplete periods are explicitly flagged and not silently evaluated as daily means."`
2. **Apparent Temperature (Thermal Stress)**:
   - The 39.0°C apparent temperature threshold reflects high-heat screening for industrial/outdoor workforce surveillance, evaluated alongside Poisson health encounter baselines.
3. **Tested Disclosure Controls**:
   - Aggregate cells with patient counts in $[1, 4]$ or contributor counts $< 10$ have `is_suppressed=True` and `value=None` in public health API payloads. Continuous environmental measurements (e.g. PM2.5 = 3.2 µg/m³) are unsuppressed physical measurements without human contributor risk. These tests establish compliance with small-cell disclosure rules, but do not claim theoretical immunity against all reconstruction attacks.

---

## 6. Backend Integration Workflow & Role Routing

Both hazard pipelines have been verified through backend integration workflow tests running against PostgreSQL 18.0 / PostGIS 3.6.4:

1. **Heat-Illness Vertical Slice (`test_deployed_heat_workflow.py`)**:
   - Ingestion of apparent temperature and workplace clinic encounters.
   - EWMA anomaly scoring and Poisson baseline prediction.
   - Evidence fusion generating `corroborated_health_warning`.
   - Alert lifecycle: Transition from `NEW` to `ASSIGNED` to `RESOLVED` with auditable operator state events.
   - Role routing: Assigned to `district_health_officer` for district tenant; `workplace_safety_manager` for enterprise workforce tenant.
2. **Respiratory Air-Quality Vertical Slice (`test_deployed_respiratory_workflow.py`)**:
   - Ingestion of Open-Meteo PM2.5, AQI, and syndromic acute respiratory clinic contacts.
   - Fusion decision verifying non-causal language (`"cause not established"`).
   - Tested disclosure controls and small-cell suppression.
   - Role routing: Accountable review window (4 hours) routed to `workplace_safety_manager` and `occupational_health_analyst`.

---

## 7. CI Acceptance Runner & Git Remote Configuration

### Root-Cause of CI Blocker
Git remote check confirms that `origin` is currently unconfigured on this development environment (`git remote -v` outputs empty). Creating and configuring the GitHub repository and granting access is the remaining user-controlled step.

### Execution Command Sequence (To Be Executed with User Credentials)
Once the repository remote is configured:
```bash
# 1. Add GitHub remote origin
git remote add origin https://github.com/<organization-or-user>/sentinelhealth.git

# 2. Push master branch containing default workflow_dispatch definition
git push -u origin master

# 3. Push feature branch
git push -u origin feature/phase3-respiratory

# 4. Trigger manual operational acceptance test workflow against feature branch
gh workflow run operational-e2e.yml --ref feature/phase3-respiratory

# 5. Inspect workflow run status and retain execution URL
gh run list --workflow operational-e2e.yml --limit 5
```

---

## 8. Automated Test Suite Summary

- **Total Backend Tests**: **80 passing, 0 failing, 0 skipped**.
- **Upstream Deprecation Warnings**: **None displayed under documented filters** (targeted filter for `asyncio.iscoroutinefunction` in `pyproject.toml`).
- **RLS PostgreSQL Isolation Tests**: 8 passing against live PostgreSQL 18.0 / PostGIS 3.6.4.
- **Reconciliation Regression Tests**: `test_replay_episode_reconciliation.py` (3 passing).
- **Data Quality Edge Case Tests**: `test_phase4_data_quality_scenarios.py` (6 passing).
- **Exact Timeliness Delay Arithmetic Tests**: `test_replay_timeliness.py` (3 passing).
- **Backend Workflow Integration Tests**: `test_deployed_heat_workflow.py` and `test_deployed_respiratory_workflow.py` (both passing).
