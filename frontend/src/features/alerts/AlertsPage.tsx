import React, { useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, Filter, Search } from "lucide-react";
import { useAlerts, useGeographies } from "../../lib/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Skeleton } from "../../components/ui/skeleton";
import { formatTimestamp, severityBadgeClass } from "../../lib/utils";

export const AlertsPage: React.FC = () => {
  const [hazardFilter, setHazardFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("");

  const { data: alerts, isLoading } = useAlerts({
    hazard: hazardFilter || undefined,
    status: statusFilter || undefined,
    severity: severityFilter || undefined,
  });

  const { data: geographies } = useGeographies();

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Surveillance Alerts & Episodes</h2>
        <p className="text-muted-foreground text-sm">
          Multi-signal health early warnings requiring review, investigation, and preventive mitigation.
        </p>
      </div>

      {/* Filter Bar */}
      <Card>
        <CardContent className="p-4 flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
            <Filter className="h-4 w-4" /> Filters:
          </div>

          <select
            value={hazardFilter}
            onChange={(e) => setHazardFilter(e.target.value)}
            className="text-xs border rounded px-2.5 py-1.5 bg-background"
          >
            <option value="">All Hazards</option>
            <option value="heat_illness">Heat Illness</option>
            <option value="respiratory_air_quality">Air Quality / Respiratory</option>
            <option value="workplace_safety">Workplace Safety</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="text-xs border rounded px-2.5 py-1.5 bg-background"
          >
            <option value="">All Severities</option>
            <option value="advisory">Advisory</option>
            <option value="watch">Watch</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border rounded px-2.5 py-1.5 bg-background"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="investigating">Investigating</option>
            <option value="action_planned">Action Planned</option>
            <option value="monitoring">Monitoring</option>
            <option value="resolved">Resolved</option>
          </select>
        </CardContent>
      </Card>

      {/* Alerts Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !alerts || alerts.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p>No alerts matching the selected criteria.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severity</TableHead>
                  <TableHead>Hazard & District</TableHead>
                  <TableHead>Evidence Class</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>First Detected</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>
                      <span className={`text-[11px] px-2 py-0.5 rounded border capitalize font-semibold ${severityBadgeClass(a.severity)}`}>
                        {a.severity}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="font-semibold capitalize text-sm">{a.hazard.replace(/_/g, " ")}</div>
                      <div className="text-xs text-muted-foreground">
                        {a.geography_name} {a.workplace_name ? `• ${a.workplace_name}` : ""}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs capitalize">{a.evidence_class.replace(/_/g, " ")}</span>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs font-bold">{a.evidence_score || "—"} / 100</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs capitalize border px-2 py-0.5 rounded bg-muted/50">
                        {a.status.replace(/_/g, " ")}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatTimestamp(a.first_detected_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link
                        to={`/alerts/${a.id}`}
                        className="text-xs font-semibold text-primary hover:underline"
                      >
                        Review Evidence →
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

