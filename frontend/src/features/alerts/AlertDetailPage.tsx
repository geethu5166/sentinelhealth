import React, { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, FileText, History, ShieldAlert } from "lucide-react";
import { useAlert, useTransitionAlert } from "../../lib/api/hooks";
import { ObservedExpectedChart } from "./components/ObservedExpectedChart";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Skeleton } from "../../components/ui/skeleton";
import { ErrorState } from "../../components/ui/error-state";
import { formatSuppressed, formatTimestamp, humanizeKey, severityBadgeClass } from "../../lib/utils";

const TABS = [
  { id: "evidence", label: "Evidence & analytics" },
  { id: "playbook", label: "Playbook" },
  { id: "timeline", label: "Audit timeline" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export const AlertDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { data: alert, isLoading, error, refetch } = useAlert(id);
  const transitionMutation = useTransitionAlert();

  const [activeTab, setActiveTab] = useState<TabId>("evidence");
  const [transitionStatus, setTransitionStatus] = useState("");
  const [transitionReason, setTransitionReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div className="mx-auto max-w-xl">
        <ErrorState
          title="Alert not found"
          description={
            error instanceof Error
              ? error.message
              : "This episode may have been removed or the API is unreachable."
          }
          onRetry={() => refetch()}
        />
        <div className="mt-4 text-center">
          <Link to="/alerts" className="text-sm text-primary underline">
            Return to alerts
          </Link>
        </div>
      </div>
    );
  }

  const runTransition = async (toStatus: string, reason: string) => {
    if (!id) return;
    setActionError(null);
    setActionSuccess(null);
    try {
      await transitionMutation.mutateAsync({
        alertId: id,
        to_status: toStatus,
        reason,
      });
      setActionSuccess(`Status updated to ${humanizeKey(toStatus)}.`);
      setTransitionReason("");
      setTransitionStatus("");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to record transition.");
    }
  };

  const handleTransition = async () => {
    if (!transitionStatus || !transitionReason) return;
    await runTransition(transitionStatus, transitionReason);
  };

  return (
    <div className="mx-auto max-w-6xl animate-fade-in space-y-6">
      <Link
        to="/alerts"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back to alerts
      </Link>

      <div className="flex flex-col justify-between gap-4 rounded-xl border bg-card p-5 shadow-panel md:flex-row md:items-center">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded border px-2.5 py-0.5 text-xs font-bold capitalize ${severityBadgeClass(alert.severity)}`}>
              {alert.severity}
            </span>
            <span className="rounded border bg-muted/60 px-2.5 py-0.5 text-xs font-medium capitalize">
              {humanizeKey(alert.evidence_class)}
            </span>
            <span className="rounded border bg-primary/10 px-2 py-0.5 text-xs font-semibold capitalize text-primary">
              {humanizeKey(alert.status)}
            </span>
          </div>
          <h1 className="font-display text-2xl font-semibold capitalize tracking-tight">
            {humanizeKey(alert.hazard)} early warning
          </h1>
          <p className="text-xs text-muted-foreground">
            Target: <strong>{alert.geography_name}</strong>
            {alert.workplace_name ? ` (${alert.workplace_name})` : ""} · First detected:{" "}
            {formatTimestamp(alert.first_detected_at)}
          </p>
        </div>

        {alert.status === "new" ? (
          <Button
            size="sm"
            onClick={() => runTransition("acknowledged", "Operator initial acknowledgment")}
            disabled={transitionMutation.isPending}
          >
            <CheckCircle2 className="mr-1.5 h-4 w-4" /> Acknowledge
          </Button>
        ) : null}
      </div>

      {(actionError || actionSuccess) && (
        <div
          role="status"
          className={`rounded-lg border px-3 py-2 text-xs ${
            actionError
              ? "border-destructive/30 bg-destructive/5 text-destructive"
              : "border-emerald-500/30 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300"
          }`}
        >
          {actionError || actionSuccess}
        </div>
      )}

      <div role="tablist" aria-label="Alert detail sections" className="flex gap-6 overflow-x-auto border-b text-sm font-medium">
        {TABS.map((tab) => {
          const selected = activeTab === tab.id;
          const label =
            tab.id === "timeline" ? `${tab.label} (${alert.state_events.length})` : tab.label;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={selected}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap pb-2.5 transition-colors ${
                selected
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {label}
            </button>
          );
        })}
      </div>

      {activeTab === "evidence" && (
        <div role="tabpanel" aria-labelledby="tab-evidence" className="space-y-6">
          <Card className="border-primary/30 bg-primary/5 shadow-panel">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldAlert className="h-4 w-4 text-primary" aria-hidden /> Multi-signal corroboration
              </CardTitle>
              <CardDescription>
                Statistical co-occurrence indicates elevated population vulnerability — not a confirmed clinical diagnosis.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <ul className="list-disc space-y-1 pl-5">
                {(alert.evidence_score_components?.reasons || ["No fusion narrative provided for this episode."]).map(
                  (r: string, idx: number) => (
                    <li key={idx}>{r}</li>
                  )
                )}
              </ul>
              <div className="border-t border-primary/20 pt-2 text-[11px] text-muted-foreground">
                Evidence score: <strong>{alert.evidence_score ?? "—"} / 100</strong>
              </div>
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {alert.evidences.map((ev) => (
              <Card key={ev.id} className="shadow-panel">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-sm font-semibold capitalize">
                      {humanizeKey(ev.metric_code)}
                    </CardTitle>
                    <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase">
                      {ev.signal_family}
                    </span>
                  </div>
                  <CardDescription className="text-xs">
                    Model: {ev.model_type || "Poisson GLM"} · Freshness: {ev.source_freshness_minutes || 30}m
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ObservedExpectedChart evidence={ev} title={ev.metric_code} />
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="shadow-panel">
            <CardHeader>
              <CardTitle className="text-sm">Evidence data points</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto p-0">
              <table className="w-full text-xs">
                <thead className="border-b bg-muted/50">
                  <tr>
                    <th className="p-2.5 text-left font-medium">Family</th>
                    <th className="p-2.5 text-left font-medium">Metric</th>
                    <th className="p-2.5 text-right font-medium">Observed</th>
                    <th className="p-2.5 text-right font-medium">Expected</th>
                    <th className="p-2.5 text-right font-medium">Excess</th>
                    <th className="p-2.5 text-right font-medium">Z-score</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {alert.evidences.map((ev) => (
                    <tr key={ev.id}>
                      <td className="p-2.5 capitalize">{humanizeKey(ev.signal_family)}</td>
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

      {activeTab === "playbook" && (
        <Card role="tabpanel" aria-labelledby="tab-playbook" className="shadow-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-primary" aria-hidden /> Prevention playbook
            </CardTitle>
            <CardDescription>
              Proportionate measures from the pre-approved operational safety protocol.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2 rounded-lg border bg-muted/30 p-4">
              <h4 className="text-sm font-bold">Recommended preventive action</h4>
              <p className="text-sm text-foreground/90">
                {alert.recommended_action ||
                  "Implement mandatory shaded rest cycles and continuous hydration points. Review high physical workload shifts."}
              </p>
            </div>
            <div className="grid grid-cols-1 gap-4 text-xs sm:grid-cols-2">
              <div className="rounded-md border p-3">
                <span className="text-muted-foreground">Accountable role</span>
                <p className="mt-0.5 font-semibold capitalize">
                  {humanizeKey(alert.responsible_role) || "Workplace safety manager"}
                </p>
              </div>
              <div className="rounded-md border p-3">
                <span className="text-muted-foreground">Required approval</span>
                <p className="mt-0.5 font-semibold capitalize">Occupational health analyst</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
              <span className="text-xs text-muted-foreground">
                Playbook: workplace environmental safety standard v1.0.0
              </span>
              <Link
                to="/tasks"
                className="inline-flex items-center rounded bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground shadow hover:bg-primary/90"
              >
                View assigned tasks →
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === "timeline" && (
        <Card role="tabpanel" aria-labelledby="tab-timeline" className="shadow-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <History className="h-4 w-4 text-primary" aria-hidden /> Audit trail
            </CardTitle>
            <CardDescription>
              Chronological log of system and operator transitions with mandatory reasons.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {alert.state_events.length === 0 ? (
                <p className="text-xs text-muted-foreground">No state events recorded yet.</p>
              ) : (
                alert.state_events.map((evt) => (
                  <div key={evt.id} className="flex items-start gap-3 border-l-2 border-primary/40 py-1 pl-4">
                    <div className="space-y-1">
                      <p className="text-xs font-semibold">
                        Transitioned to <span className="uppercase text-primary">{evt.to_status}</span>
                      </p>
                      <p className="text-xs text-foreground/80">{evt.reason}</p>
                      <span className="text-[10px] text-muted-foreground">{formatTimestamp(evt.created_at)}</span>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="mt-8 space-y-3 border-t pt-6">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Advance workflow state
              </h4>
              <div className="flex flex-col gap-3 sm:flex-row">
                <label className="sr-only" htmlFor="transition-status">
                  Target status
                </label>
                <select
                  id="transition-status"
                  value={transitionStatus}
                  onChange={(e) => setTransitionStatus(e.target.value)}
                  className="rounded border bg-background px-3 py-2 text-xs sm:w-48"
                >
                  <option value="">Select target status…</option>
                  <option value="investigating">Investigating</option>
                  <option value="action_planned">Action planned</option>
                  <option value="monitoring">Monitoring</option>
                  <option value="resolved">Resolved</option>
                  <option value="dismissed_not_actionable">Dismissed (not actionable)</option>
                </select>

                <label className="sr-only" htmlFor="transition-reason">
                  Audit reason
                </label>
                <input
                  id="transition-reason"
                  type="text"
                  placeholder="Mandatory audit justification…"
                  value={transitionReason}
                  onChange={(e) => setTransitionReason(e.target.value)}
                  className="flex-1 rounded border bg-background px-3 py-2 text-xs"
                />

                <Button
                  size="sm"
                  onClick={handleTransition}
                  disabled={!transitionStatus || !transitionReason || transitionMutation.isPending}
                >
                  Record transition
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
