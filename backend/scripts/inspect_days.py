from datetime import datetime, timezone, timedelta
from app.replay.scenarios import ScenarioGenerator
from app.analytics.baselines.models import PoissonCountBaseline, RecentHistoryBaseline
from app.analytics.detectors.ewma import OneSidedEWMADetector
from app.analytics.fusion.policy import EvidenceFusionEngine, EvidenceItem

df, ref = ScenarioGenerator.generate_heat_gradual_scenario(datetime(2026, 6, 1, tzinfo=timezone.utc), days=45, seed=42)
recent_baseline = RecentHistoryBaseline(lookback_days=28, weekday_matching=True)
poisson_baseline = PoissonCountBaseline(min_samples=14)
detector_w = OneSidedEWMADetector(0.3, 2.5)
detector_h = OneSidedEWMADetector(0.3, 2.5)
detector_a = OneSidedEWMADetector(0.3, 2.5)
fusion_engine = EvidenceFusionEngine("0.1.0")

for d in range(14, 45):
    sim_time = datetime(2026, 6, 1, tzinfo=timezone.utc) + timedelta(days=d)
    avail = df[df["timestamp"] <= sim_time]
    
    w = float(avail[avail["metric_code"] == "apparent_temperature"].iloc[-1]["value"])
    h = float(avail[avail["metric_code"] == "heat_exhaustion_contacts"].iloc[-1]["value"])
    a = float(avail[avail["metric_code"] == "sickness_absence_worker_days"].iloc[-1]["value"])
    
    w_pred = recent_baseline.fit_predict(avail[avail["metric_code"] == "apparent_temperature"], sim_time)
    w_score = detector_w.compute_anomaly(w, w_pred.expected_value, w_pred.standard_error)
    
    h_pred = poisson_baseline.fit_predict(avail[avail["metric_code"] == "heat_exhaustion_contacts"], sim_time, 1500)
    h_score = detector_h.compute_anomaly(h, h_pred.expected_value, h_pred.standard_error)
    
    a_pred = poisson_baseline.fit_predict(avail[avail["metric_code"] == "sickness_absence_worker_days"], sim_time, 3400)
    a_score = detector_a.compute_anomaly(a, a_pred.expected_value, a_pred.standard_error)
    
    evidences = [
        EvidenceItem("environmental", "apparent_temperature", w, w_pred.expected_value, w_score.excess, w_score.standardised_residual, w_score.ewma_value, w_score.is_anomaly, 15, True, False, "synthetic", "GEO-1", sim_time),
        EvidenceItem("clinical_service", "heat_exhaustion_contacts", h, h_pred.expected_value, h_score.excess, h_score.standardised_residual, h_score.is_anomaly, h_score.is_anomaly, 60, True, False, "synthetic", "GEO-1", sim_time),
        EvidenceItem("workforce", "sickness_absence_worker_days", a, a_pred.expected_value, a_score.excess, a_score.standardised_residual, a_score.ewma_value, a_score.is_anomaly, 120, True, False, "synthetic", "GEO-1", sim_time),
    ]
    
    dec = fusion_engine.evaluate("heat_illness", evidences, {"apparent_temperature": 39.0})
    if dec.should_alert or d in [30, 31, 32]:
        print(f"Day {d} ({sim_time.strftime('%Y-%m-%d')}): Temp={w:.2f} (thresh=39.0), Health={h:.0f} (z={h_score.standardised_residual:.2f}), Abs={a:.0f} (z={a_score.standardised_residual:.2f}) -> Alert={dec.should_alert}, Class={dec.evidence_class}, Sev={dec.severity}")
