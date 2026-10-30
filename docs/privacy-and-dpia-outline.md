# Privacy by Design & DPIA Outline

## 1. Principles & Lawful Basis
SentinelHealth operates on **privacy-by-design** and **data minimization**:
- **No Direct Identifiers**: No names, employee badges, national IDs, precise residential coordinates, or clinical diagnoses are collected or stored.
- **Aggregate-First Ingestion**: Data sources submit only aggregate counts with exposure denominators over specified time intervals.
- **Purpose Limitation**: Exclusively dedicated to early warning, preventive workforce protection, and public health readiness. Prohibited for employee evaluation, disciplinary monitoring, attendance scoring, or insurance eligibility.

---

## 2. Technical Safeguards Implemented

### 2.1 The 10-Contributor Minimum Rule
Aggregates representing fewer than 10 upstream contributors (e.g. fewer than 10 workers or patients in the catchment group) are masked at the API and database levels. This prevents singling out individuals in sparse cohorts.

### 2.2 Small-Cell Masking (Range [1, 4])
To prevent identification in small facilities, counts between 1 and 4 are replaced with `null` (`is_suppressed = true`). Rates and derived metrics based on these counts are also suppressed.

### 2.3 Complementary (Secondary) Suppression
When an aggregate table displays a total and one cell is suppressed, an attacker could calculate the hidden value by subtracting visible cells from the total. SentinelHealth suppresses a secondary cell (the smallest non-zero cell) to ensure algebraic reconstruction is impossible.

### 2.4 Prevention of Differencing Attacks
The API blocks arbitrary sliding-window queries and ad-hoc micro-filtering across intersecting demographics (e.g. site + shift + age group) that could isolate single individuals.

---

## 3. Data Protection Impact Assessment (DPIA) Framework

For operational deployment in any jurisdiction, the data controller must complete:
1. **Lawful Basis Verification**: Assess legal basis for processing aggregate workplace health signals (e.g. employer duty of care, public interest in public health).
2. **Worker Representative Consultation**: Engage trade union or occupational health representatives on surveillance parameters and playbook tier actions.
3. **Redress & Complaint Mechanism**: Establish clear channels for employees to contest improper surveillance use.
4. **Third-Party Review**: Independent audit of small-cell suppression rules against local privacy guidelines (e.g. UK ICO Anonymisation Code, Indian DPDP Act).

