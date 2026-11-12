import React from "react";
import { Database, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api/client";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Skeleton } from "../../components/ui/skeleton";
import { PageHeader } from "../../components/ui/page-header";
import { EmptyState } from "../../components/ui/empty-state";
import { ErrorState } from "../../components/ui/error-state";
import { StatusDot } from "../../components/ui/status-dot";
import { formatTimestamp, humanizeKey } from "../../lib/utils";

interface SourceRow {
  id: string;
  code: string;
  name: string;
  signal_family: string;
  source_type: string;
  provider?: string;
  expected_cadence_minutes?: number;
  freshness_status?: string;
  status?: string;
  updated_at?: string;
}

export const SourcesPage: React.FC = () => {
  const { data: sources, isLoading, error, refetch, isFetching } = useQuery<SourceRow[]>({
    queryKey: ["sources"],
    queryFn: () => apiFetch<SourceRow[]>("/sources"),
  });

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Signal sources"
        description="Connector health, expected cadences, and ingestion freshness for upstream feeds."
        actions={
          <Button size="sm" variant="outline" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      />

      <Card className="shadow-panel overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-3 p-6">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="p-4">
              <ErrorState
                title="Sources unavailable"
                description="Could not load connector health from the API."
                onRetry={() => refetch()}
              />
            </div>
          ) : !sources || sources.length === 0 ? (
            <EmptyState
              icon={Database}
              title="No sources registered"
              description="Register Open-Meteo, clinic, or EHS connectors to populate this view."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Family</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Provider</TableHead>
                    <TableHead>Cadence</TableHead>
                    <TableHead>Last transmission</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sources.map((s) => {
                    const status = s.freshness_status || s.status || "unknown";
                    return (
                      <TableRow key={s.id}>
                        <TableCell>
                          <StatusDot status={status} pulse={status === "fresh" || status === "online"} />
                        </TableCell>
                        <TableCell>
                          <div className="text-xs font-semibold">{s.name}</div>
                          <div className="font-mono text-[10px] text-muted-foreground">{s.code}</div>
                        </TableCell>
                        <TableCell>
                          <span className="rounded border bg-muted px-2 py-0.5 font-mono text-[10px] uppercase">
                            {s.signal_family}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs capitalize">{humanizeKey(s.source_type)}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{s.provider || "—"}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {s.expected_cadence_minutes != null ? `${s.expected_cadence_minutes} min` : "—"}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {s.updated_at ? formatTimestamp(s.updated_at) : "—"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
