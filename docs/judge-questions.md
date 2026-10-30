# Anticipated Judge & Reviewer Questions

### Q1: Why is this earlier than existing public health reporting?
**A:** Traditional public health reporting depends on laboratory-confirmed clinical diagnoses or death registrations, which suffer from a 1 to 3 week reporting lag. SentinelHealth monitors leading and real-time aggregate indicators: environmental forecasts (48h lead), syndromic clinic triage contacts (same-day), and workforce sickness absence reports (daily). By correlating an environmental screening exceedance with early service anomalies, decision-makers gain a 24–72 hour preventive action window.

### Q2: What data is actually accessible in reality versus simulated?
**A:** In the prototype, all data is explicitly synthetic. In an actual pilot deployment, public weather/air-quality forecasts (Open-Meteo, IMD) are openly accessible. Workplace sickness absence registers exist within corporate EHS portals. Aggregate syndromic triage counts can be integrated from participating regional health clinics via secure aggregate CSV/API contracts. Personal health records, EHRs, and individual diagnoses are neither required nor requested.

### Q3: What changes when geolocation is poor?
**A:** SentinelHealth explicitly tags each record with its `location_basis` and `location_confidence`. Coarse regional model grids (e.g. 10km atmospheric grids) are never downscaled to fake street coordinates. When workplace coordinates are unavailable, records remain in an explicit "unlocated" cohort; they contribute to district-wide statistical sums but cannot create false spatial hotspots on the map.

### Q4: What causes false alarms and how are they managed?
**A:** False alarms can arise from reporting batch delays (weekend catch-up), shift rescheduling, or non-occupational community gatherings. SentinelHealth mitigates false alarms through:
1. Day-of-week matched baselines to account for routine Monday spikes.
2. One-sided EWMA filtering requiring sustained deviation rather than isolated single-day spikes.
3. Multi-signal corroboration gates: an alert requires both an environmental hazard exceedance and a health anomaly in a shared window.
4. Episode grouping with a 72-hour window and 48-hour resolution hysteresis to prevent alarm flapping.

### Q5: Why transparent statistical models (Poisson/EWMA) rather than deep learning?
**A:** Public health and workplace safety decisions carry legal liability and human impact. Black-box neural networks (LSTMs, Transformers) lack interpretability, can hallucinate correlations, and fail under concept drift when real data is scarce. Transparent GLMs with log exposure offsets and EWMA control limits provide exact statistical residuals, clear prediction intervals, and transparent auditability required by safety officers and regulators.

### Q6: Can a manager identify an individual absent worker using this tool?
**A:** No. Privacy-by-design guarantees that any cell with fewer than 10 contributors or a count between 1 and 4 is completely suppressed at the API layer. Complementary suppression prevents subtraction attacks. The platform contains an explicit prohibited-use policy forbidding individual attendance scoring or disciplinary use.

