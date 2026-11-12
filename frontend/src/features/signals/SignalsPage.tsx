import React, { useState } from "react";
import { Activity, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { useSignals } from "../../lib/api/hooks";
import { Card, CardContent } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Skeleton } from "../../components/ui/skeleton";
import { PageHeader } from "../../components/ui/page-header";
import { EmptyState } from "../../components/ui/empty-state";
import { ErrorState } from "../../components/ui/error-state";
import { formatTimestamp, humanizeKey } from "../../lib/utils";

export const SignalsPage: React.FC = () => {
  const [familyFilter, setFamilyFilter] = useState("");
  const { data: signals, isLoading, error, refetch } = useSignals();

  const filteredSignals = signals
    ? signals.filter((s) => (familyFilter ? s.signal_family === familyFilter : true))
    : [];

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Surveillance signals"
        description="Privacy-preserving aggregate metrics with automated contributor thresholds and small-cell masking."
      />

      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <SlidersHorizontal className="h-4 w-4" aria-hidden />
          <span className="sr-only">Signal family</span>
          <select
            value={familyFilter}
            onChange={(e) => setFamilyFilter(e.target.value)}
            className="rounded-md border bg-background px-2.5 py-1.5 text-xs text-foreground"
          >
            <option value="">All signal families</option>
            <option value="environmental">Environmental</option>
            <option value="clinical_service">Clinical / service</option>
            <option value="workforce">Workforce</option>
            <option value="workplace_safety">Workplace safety</option>
          </select>
        </label>

        <div className="flex items-center gap-2 rounded border bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground">
          <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden />
          <span>Counts 1–4 and cohorts &lt; 10 contributors are suppressed.</span>
        </div>
      </div>

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
                title="Signals unavailable"
                description="Could not load time-series metrics from the API."
                onRetry={() => refetch()}
              />
            </div>
          ) : filteredSignals.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="No signal records"
              description="No records found for the selected family."
            />
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Family</TableHead>
                    <TableHead>Metric</TableHead>
                    <TableHead>Value</TableHead>
                    <TableHead>Unit</TableHead>
                    <TableHead>Location basis</TableHead>
                    <TableHead>Provenance</TableHead>
                    <TableHead>Observation period</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSignals.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell>
                        <span className="rounded border bg-muted px-2 py-0.5 font-mono text-[10px] uppercase">
                          {s.signal_family}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-xs font-semibold">{s.metric_code}</TableCell>
                      <TableCell>
                        {s.is_suppressed ? (
                          <span className="text-xs font-medium italic text-amber-700 dark:text-amber-400">
                            Suppressed for privacy
                          </span>
                        ) : (
                          <span className="text-sm font-bold tabular-nums">{s.value?.toLocaleString()}</span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">{s.unit}</TableCell>
                      <TableCell className="text-xs capitalize">{humanizeKey(s.location_basis)}</TableCell>
                      <TableCell>
                        <span className="rounded border border-primary/20 bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] uppercase text-primary">
                          {s.data_label}
                        </span>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatTimestamp(s.period_start)}
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
