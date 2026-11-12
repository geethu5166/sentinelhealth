import React from "react";
import { AlertTriangle, Loader2, Play } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api/client";
import { Button } from "../../components/ui/button";
import { PageHeader } from "../../components/ui/page-header";
import { ErrorState } from "../../components/ui/error-state";

interface ReplayResult {
  id: string;
  scenario: string;
  status: string;
  data_label: string;
  metrics: {
    event_sensitivity: number;
    alert_ppv: number;
    false_alarm_burden_per_week: number;
    useful_action_lead_days: number;
  };
  limitations: string[];
}

export const ValidationPage: React.FC = () => {
  const queryClient = useQueryClient();
  const runs = useQuery({
    queryKey: ["validation-runs"],
    queryFn: () => apiFetch<any[]>("/validation/runs"),
  });

  const replay = useMutation({
    mutationFn: () =>
      apiFetch<ReplayResult>("/validation/runs", {
        method: "POST",
        body: JSON.stringify({ scenario_name: "heat-gradual" }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["validation-runs"] }),
  });

  const latest = replay.data;
  const prior = !latest && Array.isArray(runs.data) && runs.data[0]
    ? {
        scenario: runs.data[0].scenario?.name || "heat-gradual",
        data_label: runs.data[0].scenario?.data_label || "benchmark",
        metrics: runs.data[0].results_summary?.metrics,
        limitations: runs.data[0].results_summary?.limitations || [],
      }
    : null;
  const results = latest || (prior?.metrics ? prior : null);

  return (
    <div className="mx-auto max-w-5xl animate-fade-in space-y-8">
      <PageHeader
        title="Replay validation"
        description="Chronological holdout replay with withheld labels. Metrics certify pipeline wiring, not clinical effectiveness."
        actions={
          <Button size="sm" onClick={() => replay.mutate()} disabled={replay.isPending}>
            {replay.isPending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Play className="mr-1.5 h-4 w-4" />}
            {replay.isPending ? "Running…" : "Run heat-gradual replay"}
          </Button>
        }
      />

      {runs.isError ? (
        <ErrorState title="Validation API unavailable" description="Could not list prior replay runs." onRetry={() => runs.refetch()} />
      ) : null}

      {replay.isError ? (
        <p className="text-xs text-destructive">Replay failed. Confirm API auth and replay routes are available.</p>
      ) : null}

      {!results ? (
        <div className="rounded-xl border border-dashed px-6 py-14 text-center">
          <p className="text-sm text-muted-foreground">
            No replay result yet. Run the heat-gradual benchmark to load sensitivity, PPV, and lead-time metrics.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-6 border-y border-border/80 py-8 sm:grid-cols-4">
            <div>
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Sensitivity</p>
              <p className="mt-2 font-display text-3xl font-semibold text-emerald-700 dark:text-emerald-400">
                {(Number(results.metrics.event_sensitivity) * 100).toFixed(0)}%
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Alert PPV</p>
              <p className="mt-2 font-display text-3xl font-semibold">
                {(Number(results.metrics.alert_ppv) * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">False alarms / week</p>
              <p className="mt-2 font-display text-3xl font-semibold">
                {Number(results.metrics.false_alarm_burden_per_week)}
              </p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Action lead</p>
              <p className="mt-2 font-display text-3xl font-semibold">
                +{Number(results.metrics.useful_action_lead_days) * 24}h
              </p>
            </div>
          </div>

          <section className="space-y-3">
            <h2 className="flex items-center gap-2 font-display text-base font-semibold">
              <AlertTriangle className="h-4 w-4 text-primary" /> Limitations
            </h2>
            <ul className="list-disc space-y-1.5 pl-5 text-xs text-muted-foreground">
              {(results.limitations || []).map((lim: string) => (
                <li key={lim}>{lim}</li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
};
