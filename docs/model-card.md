# SentinelHealth Model Card: Baseline Estimation & Anomaly Detection

## Model Details
- **Developer**: SentinelHealth Core Engineering Team.
- **Model Date**: October 2026.
- **Model Version**: 1.2.0-nist-signed.
- **Model Types**:
  1. `recent_history_weekday_matched`: Median/mean historical observation matching target weekday within 28–90 days lookback with strict exclusion of look-ahead and exclusion of current evaluation period.
  2. `poisson_glm`: Generalized Linear Model with Poisson family and log exposure offset.
  3. `one_sided_ewma`: Exponentially Weighted Moving Average control chart on standardized residuals ($\lambda=0.3$, $L=2.5\sigma$) with upper-tail alarm evaluation.
  4. `heat_screening_bom`: Australian Bureau of Meteorology empirical temperature/vapour-pressure approximation for screening proxy ($sWBGT$).

---

## Intended Use
- **Primary Use**: Population-level and site-level screening for unusual rises in sickness absence or syndromic clinic contacts coinciding with severe environmental exposures.
- **Out of Scope**: Individual clinical diagnosis, personal sickness tracking, employee fitness evaluation, disciplinary ranking, insurance eligibility, or replacing emergency services.

---

## Biometeorological Screening & Method Attribution

### 1. Australian BOM Empirical Approximation ($sWBGT$) vs. Liljegren Physical Modeling
To prevent methodological misattribution, SentinelHealth explicitly distinguishes empirical screening approximations from physical heat-balance modeling:

- **Implemented Method: Australian Bureau of Meteorology (BOM) Empirical Approximation**:
  - **Inputs**: Ambient dry-bulb temperature ($T_a$ in $^\circ\text{C}$), relative humidity ($\text{RH}$ in $\%$, $[0, 100]$).
  - **Equations**:
    $$e = \frac{\text{RH}}{100} \cdot 6.105 \cdot \exp\left(\frac{17.27 \cdot T_a}{237.7 + T_a}\right) \quad [\text{vapour pressure } e \text{ in hPa}]$$
    $$\text{sWBGT} = 0.567 \cdot T_a + 0.393 \cdot e + 3.94 \quad [^\circ\text{C}]$$
  - **Non-Interchangeability with Measured WBGT (PMC9941479)**: The simplified WBGT formula relies solely on temperature and vapour pressure, omitting solar radiation flux and wind speed. Evaluations show that $sWBGT$ substantially diverges from measured ISO 7243 WBGT under varying solar and wind conditions; it does not have a proven universal validity range and cannot be assumed to represent shaded conditions under low ventilation.
  - **Proxy Classification**: This metric is strictly an empirical regional screening proxy (`swbgt_screening_proxy`), not in-situ dosimetry. It cannot automatically prescribe workplace work–rest schedules.

- **Contrast: Liljegren et al. (2008) Physical Heat-Balance Modeling**:
  - **Inputs Required**: $T_a$, $\text{RH}$, barometric pressure ($P$), 10-meter wind speed ($v$), direct normal solar irradiance, diffuse horizontal solar irradiance, and solar zenith angle ($\theta_z$).
  - **Physical Mechanism**: Numerically solves coupled non-linear heat-exchange equations (convective, radiative, evaporative, and sensible heat balances) separately for the natural wet-bulb ($T_{nw}$) and black globe ($T_g$).
  - **Status in SentinelHealth**: SentinelHealth does **not** implement the Liljegren physical simulation model. Relying on regional weather grids lacking accurate local irradiance and wind profiles makes physical heat-balance models ungrounded; SentinelHealth restricts its environmental screening to the BOM empirical proxy, explicitly disclaiming ISO 7243 workplace dosimetry.

### 2. NOAA Heat Index ($HI$)
- **Formulation**: Rothfusz polynomial regression with high/low humidity adjustments, approximating the Steadman apparent temperature model for shaded conditions with light wind ($2.5\text{ m/s}$).
- **Caveat**: Direct solar exposure increases effective thermal strain by up to $+8^\circ\text{C}$ ($+15^\circ\text{F}$). Heavy PPE and impermeable garments severely impair sweat evaporation, lowering safe threshold margins.

---

## Anomaly Detection: Standard Signed-Residual EWMA

### Reference Formulation
Adheres to NIST/SEMATECH e-Handbook of Statistical Methods §6.3.2.4 (EWMA Control Charts):
https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm

### Mathematical Definition
1. **Standardised Residual**:
   $$r_t = \frac{y_t - \hat{\mu}_t}{\sqrt{\hat{V}_t}}$$
   where $y_t$ is the observed count/rate, $\hat{\mu}_t$ is the baseline estimated value, and $\hat{V}_t$ is the baseline variance estimate (e.g. $\hat{V}_t = \max(\hat{\mu}_t, 0.25)$ for Poisson models).

2. **EWMA Statistic**:
   $$E_t = \lambda r_t + (1 - \lambda) E_{t-1}$$
   with in-control initialisation $E_0 = 0.0$ and smoothing parameter $\lambda \in (0, 1]$ (default $\lambda = 0.3$).
   *Important distinction*: In standard NIST EWMA, signed residuals are smoothed directly without negative pre-clipping. Negative residuals appropriately reduce the EWMA value, reflecting periods of below-average incidence.

3. **Time-Varying Upper Control Limit (UCL)**:
   $$\sigma_{E, t} = \sqrt{\frac{\lambda}{2 - \lambda} \left[1 - (1 - \lambda)^{2t}\right]}$$
   $$\text{UCL}_t = L \cdot \sigma_{E, t}$$
   where $L = 2.5$ standard errors and $t$ is the observation sequence index.

4. **Nominal Analytical Limits vs. Empirical Calibration**:
   > [!IMPORTANT]
   > The analytical control limit $\text{UCL}_t = L \cdot \sigma_{E,t}$ represents a **nominal analytical limit** derived under the theoretical assumption that standardized residuals $r_t$ are independent and identically distributed ($i.i.d.$) standard normal variables ($\mathbb{E}[r_t] = 0$, $\text{Var}(r_t) = 1$) with zero auto-covariance:
   > $$\text{Cov}(r_t, r_{t-k}) = 0 \quad \forall k \ge 1$$
   > In real-world epidemiological and workforce surveillance, time series exhibit temporal auto-correlation, weekly reporting rhythms, and environmental clustering ($\text{Cov}(r_t, r_{t-k}) > 0$). Auto-correlation increases the variance of the EWMA statistic and inflates empirical false-alarm rates relative to nominal Gaussian theory.
   > 
   > Therefore, analytical limits must be regarded as baseline statistical indicators, not empirical calibration. Operational deployment requires local historical replay calibration to adjust $L$ and $\lambda$ to match desired operational Average Run Lengths (ARL) and false-positive budgets.

### Missing Period & Out-of-Order Handling
- Missing periods do not increment observation step count $t$.
- Missing observations are treated as gaps; EWMA state remains held until the next eligible observation.
- Revised records trigger recomputation of the sequence from the revised timestamp to maintain sequential integrity.

---

## Calibration Status & Caveats
> [!WARNING]
> Default control limits ($L = 2.5$, $\lambda = 0.3$) are starting heuristic baselines. They have not been clinically validated or calibrated against specific jurisdiction-specific distributions. Performance must be verified using the historical replay framework before operational deployment.

---

## Prototype Disclaimer
*This prototype has not undergone clinical validation, production security assessment or jurisdiction-specific legal/compliance review.*
