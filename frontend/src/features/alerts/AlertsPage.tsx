import React, { useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Filter } from "lucide-react";
import { useAlerts, useGeographies } from "../../lib/api/hooks";
import { Card, CardContent } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Skeleton } from "../../components/ui/skeleton";
import { PageHeader } from "../../components/ui/page-header";
import { EmptyState } from "../../components/ui/empty-state";
import { ErrorState } from "../../components/ui/error-state";
import { formatTimestamp, humanizeKey, severityAccentClass, severityBadgeClass } from "../../lib/utils";

export const AlertsPage: React.FC = () => {
  const [hazardFilter, setHazardFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [geographyFilter, setGeographyFilter] = useState("");

  const { data: alerts, isLoading, error, refetch } = useAlerts({
    hazard: hazardFilter || undefined,
    status: statusFilter || undefined,
    severity: severityFilter || undefined,
    geography_id: geographyFilter || undefined,
  });

  const { data: geographies } = useGeographies();

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Surveillance alerts"
        description="Multi-signal health early warnings requiring review, investigation, and preventive mitigation."
      />

      <Card className="shadow-panel">
        <CardContent className="flex flex-wrap items-end gap-3 p-4">
          <div className="flex items-center gap-2 pb-1.5 text-xs font-semibold text-muted-foreground">
            <Filter className="h-4 w-4" aria-hidden /> Filters
          </div>

          <label className="space-y-1 text-[11px] text-muted-foreground">
            <span className="block">Hazard</span>
            <select
              value={hazardFilter}
              onChange={(e) => setHazardFilter(e.target.value)}
              className="block rounded-md border bg-background px-2.5 py-1.5 text-xs text-foreground"
            >
              <option value="">All hazards</option>
              <option value="heat_illness">Heat illness</option>
              <option value="respiratory_air_quality">Air quality / respiratory</option>
              <option value="workplace_safety">Workplace safety</option>
            </select>
          </label>

          <label className="space-y-1 text-[11px] text-muted-foreground">
            <span className="block">Severity</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="block rounded-md border bg-background px-2.5 py-1.5 text-xs text-foreground"
            >
              <option value="">All severities</option>
              <option value="advisory">Advisory</option>
              <option value="watch">Watch</option>
              <option value="warning">Warning</option>
              <option value="critical">Critical</option>
            </select>
          </label>

          <label className="space-y-1 text-[11px] text-muted-foreground">
            <span className="block">Status</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="block rounded-md border bg-background px-2.5 py-1.5 text-xs text-foreground"
            >
              <option value="">All statuses</option>
              <option value="new">New</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="investigating">Investigating</option>
              <option value="action_planned">Action planned</option>
              <option value="monitoring">Monitoring</option>
              <option value="resolved">Resolved</option>
            </select>
          </label>

          <label className="space-y-1 text-[11px] text-muted-foreground">
            <span className="block">Geography</span>
            <select
              value={geographyFilter}
              onChange={(e) => setGeographyFilter(e.target.value)}
              className="block min-w-[10rem] rounded-md border bg-background px-2.5 py-1.5 text-xs text-foreground"
            >
              <option value="">All geographies</option>
              {(geographies || []).map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
          </label>
        </CardContent>
      </Card>

      <Card className="shadow-panel overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="p-4">
              <ErrorState
                title="Alerts unavailable"
                description="Could not load surveillance episodes from the API."
                onRetry={() => refetch()}
              />
            </div>
          ) : !alerts || alerts.length === 0 ? (
            <EmptyState
              icon={AlertTriangle}
              title="No matching alerts"
              description="No episodes match the selected filters."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Severity</TableHead>
                    <TableHead>Hazard & district</TableHead>
                    <TableHead>Evidence class</TableHead>
                    <TableHead>Score</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>First detected</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {alerts.map((a) => (
                    <TableRow key={a.id} className={`border-l-4 ${severityAccentClass(a.severity)}`}>
                      <TableCell>
                        <span className={`rounded border px-2 py-0.5 text-[11px] font-semibold capitalize ${severityBadgeClass(a.severity)}`}>
                          {a.severity}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm font-semibold capitalize">{humanizeKey(a.hazard)}</div>
                        <div className="text-xs text-muted-foreground">
                          {a.geography_name}
                          {a.workplace_name ? ` · ${a.workplace_name}` : ""}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs capitalize">{humanizeKey(a.evidence_class)}</span>
                      </TableCell>
                      <TableCell>
                        <span className="font-mono text-xs font-bold">{a.evidence_score ?? "—"} / 100</span>
                      </TableCell>
                      <TableCell>
                        <span className="rounded border bg-muted/50 px-2 py-0.5 text-xs capitalize">
                          {humanizeKey(a.status)}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatTimestamp(a.first_detected_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link to={`/alerts/${a.id}`} className="text-xs font-semibold text-primary hover:underline">
                          Review evidence →
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
