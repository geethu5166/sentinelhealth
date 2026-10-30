# Clinical Safety, Operational Boundaries & Limitations

> [!CAUTION]
> **PROTOTYPE NOTICE**: This prototype has not undergone clinical validation, production security assessment or jurisdiction-specific legal/compliance review. SentinelHealth is a population-level and workforce-level decision support prototype and has not been proven to prevent illness or injury.

---

## 1. Operating Boundaries & Prohibited Uses

SentinelHealth must **NEVER** be used to:
1. **Diagnose Individuals**: The system aggregates population counts and environmental context; it cannot determine whether an individual worker or resident is sick.
2. **Determine Fitness for Work**: It must not be used to medically clear, bench, or discipline individual employees.
3. **Automate Disciplinary Action**: Absence signals are population-level operational indicators, not attendance tracking metrics.
4. **Replace Emergency Services**: Urgent clinical incidents or severe workplace accidents must follow statutory emergency reporting protocols; SentinelHealth is an early screening platform, not an emergency dispatch service.

---

## 2. Key Analytical Limitations

### 2.1 Environmental Models vs. On-site Exposure
Open-Meteo feeds provide regional numerical weather predictions and atmospheric transport models (e.g. CAMS). A model grid cell (e.g. 10km × 10km) does not reflect indoor industrial radiant heat, lack of ventilation, or heavy physical exertion. Ambient temperature is an environmental screening filter, not an occupational heat assessment.

### 2.2 Ecological Fallacy
Co-occurrence of high heat and increased absence does not prove that workers were absent due to heat exhaustion. Signals are statistical indicators of shared vulnerability that require on-site investigation.

### 2.3 Data Missingness & Reporting Delays
Clinical feeds are subject to catch-up reporting and holiday delays. Missing data triggers an explicit degraded state ("Unable to Assess"), never a false reassurance of safety.

