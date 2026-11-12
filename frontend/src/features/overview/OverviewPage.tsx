import React from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckSquare, Clock, Database, ShieldAlert } from "lucide-react";
import { useOverview } from "../../lib/api/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Skeleton } from "../../components/ui/skeleton";
import { PageHeader } from "../../components/ui/page-header";
import { EmptyState } from "../../components/ui/empty-state";
import { ErrorState } from "../../components/ui/error-state";
import { StatusDot } from "../../components/ui/status-dot";
import { formatTimestamp, humanizeKey, severityAccentClass, severityBadgeClass } from "../../lib/utils";

export const OverviewPage: React.FC = () => {
  const { data, isLoading, error, refetch } = useOverview();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl space-y-6">
        <Skeleton className="h-16 w-full max-w-xl" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-80" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-7xl">
        <ErrorState
          title="Overview data unavailable"
          description="Could not reach the SentinelHealth analytics API."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const warningCount = data.severity_breakdown.find((s) => s.severity === "warning")?.count || 0;
  const watchCount = data.severity_breakdown.find((s) => s.severity === "watch")?.count || 0;

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Surveillance overview"
        description="Near-real-time multi-signal screening, anomaly detection, and accountable preventive decision support."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="border-l-4 border-l-[hsl(var(--severity-warning))] shadow-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active episodes</CardTitle>
            <AlertTriangle className="h-4 w-4 text-[hsl(var(--severity-warning))]" aria-hidden />
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold tabular-nums">{data.active_alert_count}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              {warningCount} warnings · {watchCount} watches
            </p>
          </CardContent>
        </Card>

        <Card className="shadow-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Action tasks</CardTitle>
            <CheckSquare className="h-4 w-4 text-primary" aria-hidden />
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold tabular-nums">{data.pending_task_count}</div>
            <p className="mt-1 text-xs text-muted-foreground">Pending assigned mitigations</p>
          </CardContent>
        </Card>

        <Card className="shadow-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Signal sources</CardTitle>
            <Database className="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden />
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold tabular-nums">
              {data.sources_online_count}{" "}
              <span className="text-sm font-normal text-muted-foreground">/ {data.total_sources_count}</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">Sources reporting within cadence</p>
          </CardContent>
        </Card>

        <Card className="shadow-panel">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Engine status</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" aria-hidden />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold">EWMA residual monitor</div>
            <p className="mt-1 text-xs text-muted-foreground">
              Updated: {data.last_update_at ? formatTimestamp(data.last_update_at) : "Awaiting first cycle"}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-panel">
        <CardHeader>
          <CardTitle>Active surveillance episodes</CardTitle>
          <CardDescription>
            Time-aligned warnings requiring accountable review under approved site playbooks.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.active_episodes.length === 0 ? (
            <EmptyState
              icon={ShieldAlert}
              title="No active anomalies"
              description="All monitored areas are within baseline limits."
            />
          ) : (
            <div className="divide-y">
              {data.active_episodes.map((ep) => (
                <div
                  key={ep.id}
                  className={`flex flex-col justify-between gap-4 border-l-4 py-4 pl-4 sm:flex-row sm:items-center ${severityAccentClass(ep.severity)}`}
                >
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded border px-2 py-0.5 text-xs font-semibold capitalize ${severityBadgeClass(ep.severity)}`}>
                        {ep.severity}
                      </span>
                      <span className="text-sm font-semibold capitalize tracking-tight">
                        {humanizeKey(ep.hazard)} — {ep.geography_name}
                      </span>
                      <Badge variant="outline" className="text-[10px] capitalize">
                        {humanizeKey(ep.evidence_class)}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      First detected: {formatTimestamp(ep.first_detected_at)} · Corroborated signals:{" "}
                      {ep.contributing_signal_count}
                    </p>
                  </div>
                  <Link
                    to={`/alerts/${ep.id}`}
                    className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground shadow hover:bg-primary/90"
                  >
                    Investigate evidence
                  </Link>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="shadow-panel">
        <CardHeader>
          <CardTitle>Feed health & freshness</CardTitle>
          <CardDescription>
            Upstream delays, missing indicators, and reporting cadence. Stale feeds degrade confidence.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.sources.length === 0 ? (
            <EmptyState title="No sources registered" description="Connect feeds to monitor freshness." />
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {data.sources.map((s) => (
                <div key={s.id} className="flex items-center justify-between rounded-lg border bg-card/60 p-3">
                  <div className="min-w-0 pr-2">
                    <p className="truncate text-xs font-semibold">{s.name}</p>
                    <p className="text-[11px] capitalize text-muted-foreground">{humanizeKey(s.signal_family)}</p>
                  </div>
                  <div className="text-right">
                    <StatusDot status={s.status || "fresh"} label={`${s.status || "fresh"} (${s.freshness_minutes}m)`} pulse />
                    <p className="mt-0.5 text-[10px] text-muted-foreground">Cadence: {s.threshold_minutes}m</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
