# SentinelHealth Demonstration Script (5–7 Minutes)

## Setup & Demo Mode
- **Synthetic Data Disclaimer**: Emphasize that all demonstration records are fictional and calibrated for testing decision support workflows.
- **Audience**: Public Health Directors, Occupational Health Leads, and Workplace Safety Managers.

---

## Step-by-Step Walkthrough

### Step 1: Login & Identity Scoping (`/login`)
- Show Keycloak OIDC login with PKCE.
- Log in as **Vikram Patel (Workplace Safety Manager)**.
- Note the persistent banner: *"⚠️ DEMONSTRATION MODE — All data is synthetic and fictional."*

### Step 2: Overview & Normal Baseline (`/overview`)
- Review active episodes, system health, and source freshness.
- Point out that data sources show green freshness dots (< 60 min).
- Explain that surveillance combines environmental screening with workforce and clinical signals.

### Step 3: Map & Aggregate Geographic Uncertainty (`/map`)
- View approved aggregate polygons: **Dhanpur District** and **Lakshmi Industrial Corridor**.
- Explain that coordinates reflect district administrative boundaries, not individual homes or workers.
- Show the opacity-coded risk overlay.

### Step 4: Investigating a Corroborated Warning (`/alerts/1`)
- Open the active **Heat Illness Warning**.
- **Evidence Tab**: Show the **Observed vs Expected chart**. Show the solid observed line exceeding the dashed baseline and prediction area.
- Explain the **Evidence Fusion**:
  - Apparent Temperature: 42.5°C (> 40.0°C screening threshold).
  - Sickness Absence: 82 worker-days (expected 24.2, z=4.1).
  - Emergency Contacts: 38 contacts (expected 13.5, z=3.8).
- Review non-causal phrasing: *"Signals coincided in time and geography; requires operational investigation."*
- Review alternate explanations (reporting batching, shift re-allocation).

### Step 5: Preventive Action & Decision Support (`/tasks`)
- Open the linked **Preventive Task**: *"Execute Heat Protocol: Work-Rest Cycles & Hydration Stations"*.
- Show the assigned role (**Workplace Safety Manager**) and required approval role (**Occupational Health Analyst**).
- Transition the task to **Completed**, entering site inspection notes.

### Step 6: Privacy & Small-Cell Suppression (`/signals`)
- Navigate to the **Surya Nagar Ward** signal view.
- Point out that counts between 1 and 4 show **"Suppressed for privacy"** rather than revealing specific worker numbers.
- Show that rates and denominators that could reveal the cell are also masked.

### Step 7: Graceful Degradation on Missing Data (`/sources`)
- Simulate disabling the clinical service connector.
- Refresh Overview: The system transitions to an amber **"Environmental Watch / Degraded Evidence"** state.
- Emphasize that the platform **never displays a false green "Safe" status** when required feeds are missing.

### Step 8: Replay Validation & Limitations (`/validation`)
- View the Chronological Replay evaluation of the `heat-gradual` scenario.
- Review true Event Sensitivity (100%), Alert PPV (85.7%), and False Alarm Burden (0.2 / week).
- Review explicit limitations: synthetic benchmarks, unvalidated clinical efficacy.

