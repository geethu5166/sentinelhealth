import React, { useState } from "react";
import { Activity, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { useSignals } from "../../lib/api/hooks";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../components/ui/table";
import { Skeleton } from "../../components/ui/skeleton";
import { formatSuppressed, formatTimestamp } from "../../lib/utils";

export const SignalsPage: React.FC = () => {
  const [familyFilter, setFamilyFilter] = useState<string>("");
  const { data: signals, isLoading } = useSignals();

  const filteredSignals = signals
    ? signals.filter((s) => (familyFilter ? s.signal_family === familyFilter : true))
    : [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Surveillance Signals & Time-Series</h2>
        <p className="text-muted-foreground text-sm">
          Privacy-preserving aggregate metrics with automated contributor thresholds and small-cell masking.
        </p>
      </div>

      {/* Filter and Privacy Notice */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
          <select
            value={familyFilter}
            onChange={(e) => setFamilyFilter(e.target.value)}
            className="text-xs border rounded px-2.5 py-1.5 bg-background"
          >
            <option value="">All Signal Families</option>
            <option value="environmental">Environmental</option>
            <option value="clinical_service">Clinical / Service</option>
            <option value="workforce">Workforce</option>
            <option value="workplace_safety">Workplace Safety</option>
          </select>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/40 px-3 py-1.5 rounded border">
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
          <span>Active Privacy Rule: Counts 1–4 and cohorts &lt; 10 contributors suppressed.</span>
        </div>
      </div>

      {/* Signals Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : filteredSignals.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <Activity className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p>No signal records found for the selected family.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Family</TableHead>
                  <TableHead>Metric</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Unit</TableHead>
                  <TableHead>Location Basis</TableHead>
                  <TableHead>Provenance / Label</TableHead>
                  <TableHead>Observation Period</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSignals.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell>
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-muted border">
                        {s.signal_family}
                      </span>
                    </TableCell>
                    <TableCell className="font-mono text-xs font-semibold">{s.metric_code}</TableCell>
                    <TableCell>
                      {s.is_suppressed ? (
                        <span className="text-xs italic text-amber-600 dark:text-amber-400 font-medium">
                          Suppressed for privacy
                        </span>
                      ) : (
                        <span className="font-bold text-sm">{s.value?.toLocaleString()}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{s.unit}</TableCell>
                    <TableCell className="text-xs capitalize">{s.location_basis.replace(/_/g, " ")}</TableCell>
                    <TableCell>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-200 uppercase font-mono">
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
          )}
        </CardContent>
      </Card>
    </div>
  );
};

