from datetime import datetime, timezone, timedelta
from app.replay.scenarios import ScenarioGenerator
from app.analytics.baselines.models import RecentHistoryBaseline, PoissonCountBaseline
from app.analytics.detectors.ewma import OneSidedEWMADetector
from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem

start_date = datetime(2026, 6, 1, tzinfo=timezone.utc)
df, ref = ScenarioGenerator.generate_heat_gradual_scenario(start_date, days=45, seed=42)
recent_baseline = RecentHistoryBaseline(lookback_days=28, weekday_matching=True)
poisson_baseline = PoissonCountBaseline(min_samples=14)
detector = OneSidedEWMADetector(0.3, 2.5)
fusion = EvidenceFusionEngine("0.1.0")

print(f"Reference event: {ref['onset_at']} to {ref['end_at']}")

alerts = []
for d in range(14, 45):
    sim = start_date + timedelta(days=d)
    av = df[df["timestamp"] <= sim]
    w = av[av["metric_code"] == "apparent_temperature"]
    h = av[av["metric_code"] == "heat_exhaustion_contacts"]
    s = av[av["metric_code"] == "sickness_absence_worker_days"]
    evs = []
    if not w.empty:
        p = recent_baseline.fit_predict(w, sim)
        sc = detector.compute_anomaly(float(w.iloc[-1]["value"]), p.expected_value, p.standard_error)
        evs.append(EvidenceItem("environmental", "apparent_temperature", float(w.iloc[-1]["value"]), p.expected_value, sc.excess, sc.standardised_residual, sc.ewma_value, sc.is_anomaly, 15, True, False, "synthetic", "DIST-1", sim))
    if not h.empty:
        p = poisson_baseline.fit_predict(h, sim, 1500)
        sc = detector.compute_anomaly(float(h.iloc[-1]["value"]), p.expected_value, p.standard_error)
        evs.append(EvidenceItem("clinical_service", "heat_exhaustion_contacts", float(h.iloc[-1]["value"]), p.expected_value, sc.excess, sc.standardised_residual, sc.ewma_value, sc.is_anomaly, 60, True, False, "synthetic", "DIST-1", sim))
    if not s.empty:
        p = poisson_baseline.fit_predict(s, sim, 3400)
        sc = detector.compute_anomaly(float(s.iloc[-1]["value"]), p.expected_value, p.standard_error)
        evs.append(EvidenceItem("workforce", "sickness_absence_worker_days", float(s.iloc[-1]["value"]), p.expected_value, sc.excess, sc.standardised_residual, sc.ewma_value, sc.is_anomaly, 120, True, False, "synthetic", "DIST-1", sim))
    dec = fusion.evaluate("heat_illness", evs, {"apparent_temperature": 39.0})
    if dec.should_alert:
        print(f"Day {d} ({sim.strftime('%Y-%m-%d')}): class={dec.evidence_class}, score={dec.evidence_score}, severity={dec.severity}")
        alerts.append({"day": d, "sim": sim, "class": dec.evidence_class, "score": dec.evidence_score})

# Cluster into episodes
episodes = []
for a in alerts:
    if not episodes or (a["day"] - episodes[-1][-1]["day"]) > 2:
        episodes.append([a])
    else:
        episodes[-1].append(a)

print(f"\nTotal episodes: {len(episodes)}")
for idx, ep in enumerate(episodes, 1):
    first = ep[0]
    last = ep[-1]
    classes = set(x["class"] for x in ep)
    print(f"Episode {idx}: Days {first['day']}-{last['day']} ({first['sim'].strftime('%Y-%m-%d')} to {last['sim'].strftime('%Y-%m-%d')}) | Classes: {classes} | Alerts in ep: {len(ep)}")

