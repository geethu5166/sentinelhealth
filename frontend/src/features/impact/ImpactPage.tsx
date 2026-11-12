import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Clock3, ListChecks, ShieldAlert } from "lucide-react";
import { useAlerts, useOverview, useTasks } from "../../lib/api/hooks";
import { PageHeader } from "../../components/ui/page-header";
import { ErrorState } from "../../components/ui/error-state";
import { Skeleton } from "../../components/ui/skeleton";
import { formatTimestamp, humanizeKey } from "../../lib/utils";

export const ImpactPage: React.FC = () => {
  const overview = useOverview();
  const tasks = useTasks();
  const alerts = useAlerts({ status: "new" });

  const stats = useMemo(() => {
    const taskList = tasks.data || [];
    const completed = taskList.filter((t) => t.status === "completed" || t.status === "verified").length;
    const pending = taskList.filter((t) => t.status === "pending" || t.status === "in_progress").length;
    const active = overview.data?.active_alert_count ?? 0;
    return { completed, pending, active };
  }, [tasks.data, overview.data]);

  if (overview.isLoading || tasks.isLoading) {
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <Skeleton className="h-14 w-80" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (overview.error) {
    return (
      <div className="mx-auto max-w-5xl">
        <ErrorState title="Impact metrics unavailable" description="Could not load operational tallies." onRetry={() => overview.refetch()} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl animate-fade-in space-y-10">
      <PageHeader
        title="Operational impact"
        description="Live tallies from alerts and mitigation tasks. Causal health claims require prospective evaluation design."
      />

      <section className="grid grid-cols-1 gap-8 border-y border-border/80 py-8 sm:grid-cols-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Active episodes</p>
          <p className="mt-2 font-display text-4xl font-semibold tabular-nums">{stats.active}</p>
          <p className="mt-1 text-xs text-muted-foreground">Open surveillance episodes</p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Mitigations pending</p>
          <p className="mt-2 font-display text-4xl font-semibold tabular-nums">{stats.pending}</p>
          <p className="mt-1 text-xs text-muted-foreground">Assigned playbook actions</p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">Completed actions</p>
          <p className="mt-2 font-display text-4xl font-semibold tabular-nums">{stats.completed}</p>
          <p className="mt-1 text-xs text-muted-foreground">Verified or closed tasks</p>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold">Queue needing attention</h2>
            <p className="text-xs text-muted-foreground">Newest open alerts awaiting review.</p>
          </div>
          <Link to="/alerts" className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline">
            All alerts <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {(alerts.data || []).length === 0 ? (
          <div className="flex items-start gap-3 rounded-xl border border-dashed px-4 py-8 text-sm text-muted-foreground">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            No new episodes in queue. Impact tallies update as alerts and tasks change.
          </div>
        ) : (
          <ul className="divide-y border-t border-border/70">
            {(alerts.data || []).slice(0, 5).map((alert) => (
              <li key={alert.id} className="flex flex-col gap-2 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold capitalize">
                    {humanizeKey(alert.hazard)} · {alert.geography_name || "Unscoped geography"}
                  </p>
                  <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <Clock3 className="h-3 w-3" />
                    First detected {formatTimestamp(alert.first_detected_at)} · {humanizeKey(alert.severity)}
                  </p>
                </div>
                <Link
                  to={`/alerts/${alert.id}`}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                >
                  Investigate <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="flex items-start gap-2 text-[11px] leading-relaxed text-muted-foreground">
        <ListChecks className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        Before/after absence or clinic reductions are not attributed to SentinelHealth without a pre-specified evaluation protocol.
      </p>
    </div>
  );
};
