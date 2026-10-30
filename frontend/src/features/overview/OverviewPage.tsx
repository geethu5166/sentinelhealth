import React from "react";
import { Link } from "react-router-dom";
import { Activity, AlertTriangle, CheckSquare, Clock, Database, ShieldAlert } from "lucide-react";
import { useOverview } from "../../lib/api/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Skeleton } from "../../components/ui/skeleton";
import { formatTimestamp, severityBadgeClass } from "../../lib/utils";

export const OverviewPage: React.FC = () => {
  const { data, isLoading, error } = useOverview();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="text-destructive">Overview Data Unavailable</CardTitle>
          <CardDescription>Could not connect to the SentinelHealth analytics engine.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Population & Workforce Health Surveillance</h2>
        <p className="text-muted-foreground text-sm">
          Near-real-time multi-signal screening, anomaly detection, and accountable preventive decision support.
        </p>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Episodes</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{data.active_alert_count}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {data.severity_breakdown.find((s) => s.severity === "warning")?.count || 0} warnings,{" "}
              {data.severity_breakdown.find((s) => s.severity === "watch")?.count || 0} watches
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Action Tasks</CardTitle>
            <CheckSquare className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{data.pending_task_count}</div>
            <p className="text-xs text-muted-foreground mt-1">Pending assigned mitigations</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Signal Sources</CardTitle>
            <Database className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {data.sources_online_count} <span className="text-sm font-normal text-muted-foreground">/ {data.total_sources_count}</span>
            </div>
            <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">All core feeds transmitting</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Engine Status</CardTitle>
            <Clock className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold truncate">EWMA Residual Monitor</div>
            <p className="text-xs text-muted-foreground mt-1">
              Updated: {data.last_update_at ? formatTimestamp(data.last_update_at) : "Just now"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Active Episodes List */}
      <Card>
        <CardHeader>
          <CardTitle>Active Surveillance Episodes</CardTitle>
          <CardDescription>
            Time-aligned warnings requiring accountable review under approved site playbooks.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {data.active_episodes.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              <ShieldAlert className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>No active anomalies or watches detected. All monitored areas within baseline limits.</p>
            </div>
          ) : (
            <div className="divide-y">
              {data.active_episodes.map((ep) => (
                <div key={ep.id} className="py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded border capitalize ${severityBadgeClass(ep.severity)}`}>
                        {ep.severity}
                      </span>
                      <span className="text-sm font-bold tracking-tight capitalize">
                        {ep.hazard.replace(/_/g, " ")} — {ep.geography_name}
                      </span>
                      <Badge variant="outline" className="text-[10px]">
                        {ep.evidence_class.replace(/_/g, " ")}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      First detected: {formatTimestamp(ep.first_detected_at)} • Corroborated signals: {ep.contributing_signal_count}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/alerts/${ep.id}`}
                      className="inline-flex items-center justify-center rounded-md text-xs font-medium bg-primary text-primary-foreground px-3 py-1.5 shadow hover:bg-primary/90"
                    >
                      Investigate Evidence
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Source Freshness Health Matrix */}
      <Card>
        <CardHeader>
          <CardTitle>Feed Health & Freshness Matrix</CardTitle>
          <CardDescription>
            Monitors upstream delays, missing indicators, and reporting cadence. Stale feeds trigger degraded state warnings.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {data.sources.map((s) => (
              <div key={s.id} className="p-3 border rounded-lg flex items-center justify-between">
                <div>
                  <p className="font-semibold text-xs">{s.name}</p>
                  <p className="text-[11px] text-muted-foreground capitalize">{s.signal_family.replace(/_/g, " ")}</p>
                </div>
                <div className="text-right">
                  <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                    <span className="h-2 w-2 rounded-full bg-emerald-500" />
                    Fresh ({s.freshness_minutes}m)
                  </span>
                  <p className="text-[10px] text-muted-foreground">Cadence: {s.threshold_minutes}m</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

