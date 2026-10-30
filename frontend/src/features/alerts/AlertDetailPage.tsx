import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock,
  FileText,
  History,
  ShieldAlert,
} from "lucide-react";
import { useAlert, useTransitionAlert } from "../../lib/api/hooks";
import { ObservedExpectedChart } from "./components/ObservedExpectedChart";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Skeleton } from "../../components/ui/skeleton";
import { formatSuppressed, formatTimestamp, severityBadgeClass } from "../../lib/utils";

export const AlertDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { data: alert, isLoading, error } = useAlert(id);
  const transitionMutation = useTransitionAlert();

  const [activeTab, setActiveTab] = useState<"evidence" | "playbook" | "timeline">("evidence");
  const [transitionStatus, setTransitionStatus] = useState<string>("");
  const [transitionReason, setTransitionReason] = useState<string>("");

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div className="max-w-xl mx-auto text-center py-12">
        <h2 className="text-xl font-bold text-destructive">Alert Not Found</h2>
        <Link to="/alerts" className="text-sm text-primary underline mt-4 inline-block">
          Return to alerts list
        </Link>
      </div>
    );
  }

  const handleTransition = async () => {
    if (!id || !transitionStatus || !transitionReason) return;
    await transitionMutation.mutateAsync({
      alertId: id,
      to_status: transitionStatus,
      reason: transitionReason,
    });
    setTransitionReason("");
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Back button */}
      <Link to="/alerts" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Surveillance Alerts
      </Link>

      {/* Header Banner */}
      <div className="p-6 rounded-xl border bg-card flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2.5 py-0.5 rounded border capitalize font-bold ${severityBadgeClass(alert.severity)}`}>
              {alert.severity}
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded bg-muted/60 border capitalize font-medium">
              {alert.evidence_class.replace(/_/g, " ")}
            </span>
            <span className="text-xs px-2 py-0.5 rounded border capitalize font-semibold bg-primary/10 text-primary">
              Status: {alert.status.replace(/_/g, " ")}
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight capitalize">
            {alert.hazard.replace(/_/g, " ")} Early Warning
          </h1>
          <p className="text-xs text-muted-foreground">
            Target Area: <strong>{alert.geography_name}</strong> {alert.workplace_name ? `(${alert.workplace_name})` : ""} • First Detected: {formatTimestamp(alert.first_detected_at)}
          </p>
        </div>

        {/* Quick Transition controls */}
        <div className="flex items-center gap-2">
          {alert.status === "new" && (
            <Button
              size="sm"
              onClick={() => {
                transitionMutation.mutate({
                  alertId: alert.id,
                  to_status: "acknowledged",
                  reason: "Operator initial acknowledgment",
                });
              }}
              disabled={transitionMutation.isPending}
            >
              <CheckCircle2 className="h-4 w-4 mr-1.5" /> Acknowledge Warning
            </Button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b text-sm font-medium gap-6">
        <button
          onClick={() => setActiveTab("evidence")}
          className={`pb-2.5 transition-colors ${activeTab === "evidence" ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
        >
          Contributing Evidence & Analytics
        </button>
        <button
          onClick={() => setActiveTab("playbook")}
          className={`pb-2.5 transition-colors ${activeTab === "playbook" ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
        >
          Playbook & Action Recommendations
        </button>
        <button
          onClick={() => setActiveTab("timeline")}
          className={`pb-2.5 transition-colors ${activeTab === "timeline" ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
        >
          Audit Timeline ({alert.state_events.length})
        </button>
      </div>

      {/* Tab: Evidence */}
      {activeTab === "evidence" && (
        <div className="space-y-6">
          {/* Fusion Explanation Box */}
          <Card className="border-primary/30 bg-primary/5">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-primary" /> Multi-Signal Corroboration Analysis
              </CardTitle>
              <CardDescription>
                Surveillance signals indicate statistical co-occurrence. This reflects elevated population vulnerability, not a confirmed causal diagnosis.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <ul className="list-disc pl-5 space-y-1">
                {(alert.evidence_score_components?.reasons || []).map((r: string, idx: number) => (
                  <li key={idx}>{r}</li>
                ))}
              </ul>
              <div className="pt-2 text-[11px] text-muted-foreground border-t border-primary/20">
                Operational Evidence Score: <strong>{alert.evidence_score || "—"} / 100</strong> (Bounded transformation of standardized residual deviations).
              </div>
            </CardContent>
          </Card>

          {/* Observed vs Expected Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {alert.evidences.map((ev) => (
              <Card key={ev.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-semibold capitalize">
                      {ev.metric_code.replace(/_/g, " ")}
                    </CardTitle>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-muted">
                      {ev.signal_family}
                    </span>
                  </div>
                  <CardDescription className="text-xs">
                    Model: {ev.model_type || "Poisson GLM"} • Freshness: {ev.source_freshness_minutes || 30}m
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ObservedExpectedChart evidence={ev} title={ev.metric_code} />
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Evidence Table with Suppression Check */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Granular Evidence Data Points</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-xs">
                <thead className="bg-muted/50 border-b">
                  <tr>
                    <th className="p-2.5 text-left font-medium">Family</th>
                    <th className="p-2.5 text-left font-medium">Metric</th>
                    <th className="p-2.5 text-right font-medium">Observed</th>
                    <th className="p-2.5 text-right font-medium">Expected</th>
                    <th className="p-2.5 text-right font-medium">Excess</th>
                    <th className="p-2.5 text-right font-medium">Z-Score (Residual)</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {alert.evidences.map((ev) => (
                    <tr key={ev.id}>
                      <td className="p-2.5 capitalize">{ev.signal_family.replace(/_/g, " ")}</td>
                      <td className="p-2.5 font-mono">{ev.metric_code}</td>
                      <td className="p-2.5 text-right font-bold">
                        {formatSuppressed(ev.observed_value, ev.is_suppressed)}
                      </td>
                      <td className="p-2.5 text-right text-muted-foreground">
                        {formatSuppressed(ev.expected_value, ev.is_suppressed)}
                      </td>
                      <td className="p-2.5 text-right text-destructive">
                        {ev.is_suppressed ? "—" : `+${ev.excess || 0}`}
                      </td>
                      <td className="p-2.5 text-right font-mono font-semibold">
                        +{ev.standardised_residual || 0}σ
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab: Playbook */}
      {activeTab === "playbook" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary" /> Approved Prevention Playbook Recommendation
            </CardTitle>
            <CardDescription>
              Actionable proportionate measures derived from the pre-approved operational safety protocol.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg border bg-muted/30 space-y-2">
              <h4 className="text-sm font-bold text-foreground">Recommended Preventive Action:</h4>
              <p className="text-sm text-foreground/90">
                {alert.recommended_action || "Implement mandatory shaded rest cycles and continuous hydration points. Review high physical workload shifts."}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3 border rounded-md">
                <span className="text-muted-foreground">Accountable Role:</span>
                <p className="font-semibold capitalize mt-0.5">{alert.responsible_role?.replace(/_/g, " ") || "Workplace Safety Manager"}</p>
              </div>
              <div className="p-3 border rounded-md">
                <span className="text-muted-foreground">Required Consequential Approval:</span>
                <p className="font-semibold capitalize mt-0.5">Occupational Health Analyst / Lead</p>
              </div>
            </div>

            <div className="pt-4 border-t flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                Playbook: OSHA / WHO Workplace Environmental Safety Standard v1.0.0
              </span>
              <Link
                to="/tasks"
                className="inline-flex items-center text-xs font-semibold bg-primary text-primary-foreground px-3 py-1.5 rounded shadow hover:bg-primary/90"
              >
                View Assigned Tasks →
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tab: Timeline */}
      {activeTab === "timeline" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <History className="h-4 w-4 text-primary" /> Immutable Audit & State Event Trail
            </CardTitle>
            <CardDescription>
              Chronological log of all system and operator state transitions with mandatory recorded reasons.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {alert.state_events.map((evt) => (
                <div key={evt.id} className="flex items-start gap-3 border-l-2 border-primary/40 pl-4 py-1">
                  <div className="space-y-1">
                    <p className="text-xs font-semibold">
                      Transitioned to <span className="uppercase text-primary">{evt.to_status}</span>
                    </p>
                    <p className="text-xs text-foreground/80">{evt.reason}</p>
                    <span className="text-[10px] text-muted-foreground">{formatTimestamp(evt.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* State Transition Form */}
            <div className="mt-8 pt-6 border-t space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Advance Alert Workflow State</h4>
              <div className="flex flex-col sm:flex-row gap-3">
                <select
                  value={transitionStatus}
                  onChange={(e) => setTransitionStatus(e.target.value)}
                  className="text-xs border rounded px-3 py-2 bg-background sm:w-48"
                >
                  <option value="">Select target status...</option>
                  <option value="investigating">Investigating</option>
                  <option value="action_planned">Action Planned</option>
                  <option value="monitoring">Monitoring</option>
                  <option value="resolved">Resolved</option>
                  <option value="dismissed_not_actionable">Dismissed (Not Actionable)</option>
                </select>

                <input
                  type="text"
                  placeholder="Mandatory audit justification reason..."
                  value={transitionReason}
                  onChange={(e) => setTransitionReason(e.target.value)}
                  className="text-xs border rounded px-3 py-2 bg-background flex-1"
                />

                <Button
                  size="sm"
                  onClick={handleTransition}
                  disabled={!transitionStatus || !transitionReason || transitionMutation.isPending}
                >
                  Record Transition
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

