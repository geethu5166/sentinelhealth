# SentinelHealth Threat Model

## 1. Scope & System Boundaries
SentinelHealth operates as a modular monolith API with asynchronous background workers. It ingests aggregate surveillance signals, computes baseline residuals, evaluates multi-signal corroboration, and produces actionable decision support.

The system intentionally excludes:
- Individual medical records, EHR feeds, or personal identifiable information (PII).
- Individual employee timecards, disciplinary metrics, or performance scoring.
- Automated workplace closures or legal non-compliance declarations.

---

## 2. Threat Analysis & Mitigations

| Threat ID | Threat Description | Likelihood | Impact | Mitigations Implemented | Residual Risk |
|---|---|---|---|---|---|
| **TH-01: Cross-Tenant Data Access** | Malicious tenant user attempts to read or mutate alerts belonging to another tenant via ID tampering. | Medium | Critical | • Server-side JWT tenant validation.<br>• Non-bypassable PostgreSQL Row-Level Security (RLS) on all sensitive tables (`signal_records`, `alerts`, `preventive_tasks`, `audit_events`).<br>• Request context set per transaction (`app.current_tenant_id`). | Connection pooling misconfiguration leaking context; mitigated by session cleanup reset in SQLAlchemy engine listener. |
| **TH-02: Small-Cell Re-identification** | An insider queries aggregate absence counts for a small shift to determine if a specific employee was ill. | High | High | • Enforced suppression of cells with value 1–4.<br>• Contributor minimum of 10 distinct individuals before publishing.<br>• Complementary suppression applied to table margins.<br>• Fixed reporting windows (no custom micro-filtering). | Out-of-band external knowledge combined with true zero observations. Documented in DPIA. |
| **TH-03: Formula Injection in Exports** | Malicious data steward injects `=CMD()` or `@SUM()` formulas into metric labels or error logs to execute commands on analyst spreadsheets. | Medium | High | • Mandatory CSV cell sanitization: prepending apostrophe `'` to any cell starting with `=`, `+`, `-`, `@`, `\t`, `\r`.<br>• Formal disclosure review before export approval. | User manually stripping apostrophes after export. |
| **TH-04: Token Theft & Replay** | Malicious script steals access tokens from browser storage. | Low | Critical | • PKCE Authorization Code flow with short-lived tokens (5 min).<br>• In-memory token storage (never `localStorage` or `sessionStorage`).<br>• Strict Content Security Policy (CSP) blocking external scripts. | Compromised developer workstation. |
| **TH-05: Data Poisoning & Feed Forgery** | An adversary submits fabricated extreme weather or absence spikes to trigger false emergency procedures. | Medium | High | • Strict schema and unit validation at ingestion.<br>• Multi-signal corroboration gate: single-signal spikes cannot generate a Corroborated Health Warning without compatible secondary signals.<br>• Human-in-the-loop review required before enacting operational interventions. | Sophisticated coordinated poisoning across environmental and workforce feeds. |
| **TH-06: Alert Manipulation** | An insider dismisses an alert to hide severe workplace safety violations. | Medium | High | • Immutable append-only `alert_state_events` and `audit_events`.<br>• Mandatory recorded reason and authenticated actor ID on all state transitions.<br>• Periodic audit trail reviews by Privacy Officer and Regulators. | Superuser direct database manipulation; mitigated in AWS pilot via KMS encrypted audit trails. |
| **TH-07: SSRF via External Connectors** | User-controlled URLs in connector configuration causing the server to probe internal infrastructure. | Low | High | • Strict connector allowlist (Open-Meteo API domain only).<br>• No arbitrary user-defined HTTP endpoints permitted. | Future extension plugins; mitigated by connector validation sandbox. |

