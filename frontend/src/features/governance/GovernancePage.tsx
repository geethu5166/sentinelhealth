import React from "react";
import { Ban, Lock, ScrollText, UserCheck } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useUser } from "../../auth/useUser";
import { apiFetch } from "../../lib/api/client";
import { PageHeader } from "../../components/ui/page-header";
import { formatTimestamp, humanizeKey } from "../../lib/utils";

interface AuditEventRow {
  id: string;
  action?: string;
  event_type?: string;
  resource_type?: string;
  actor_email?: string;
  created_at: string;
  details?: Record<string, unknown>;
}

export const GovernancePage: React.FC = () => {
  const { user } = useUser();
  const tenantName = user?.memberships?.find((m) => m.tenant_id === user.current_tenant_id)?.tenant_name
    || user?.memberships?.[0]?.tenant_name
    || "Current tenant";

  const audit = useQuery({
    queryKey: ["audit-events"],
    queryFn: () => apiFetch<AuditEventRow[]>("/audit-events?limit=20"),
    retry: false,
  });

  return (
    <div className="mx-auto max-w-5xl animate-fade-in space-y-10">
      <PageHeader
        title="Governance & privacy"
        description="Authorisation boundaries, small-cell disclosure controls, and append-only audit review."
      />

      <section className="rounded-xl border border-destructive/30 bg-destructive/5 px-5 py-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-destructive">
          <Ban className="h-4 w-4" /> Prohibited uses
        </h2>
        <ul className="mt-3 list-disc space-y-1.5 pl-5 text-xs text-muted-foreground">
          <li>Employee productivity scoring, individual performance ranking, or appraisal weighting.</li>
          <li>Individual sickness monitoring, attendance surveillance, or automated disciplinary action.</li>
          <li>Clinical fitness-for-work determinations or employment termination.</li>
          <li>Insurance eligibility discrimination or premium adjustments.</li>
          <li>Re-identification attempts against suppressed aggregate cells.</li>
        </ul>
      </section>

      <section className="grid gap-8 border-y border-border/80 py-8 sm:grid-cols-2">
        <div className="space-y-3">
          <h2 className="flex items-center gap-2 font-display text-base font-semibold">
            <UserCheck className="h-4 w-4 text-primary" /> Active credentials
          </h2>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Identity</dt>
              <dd className="mt-0.5 font-semibold">
                {user?.display_name} · {user?.email}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Role</dt>
              <dd className="mt-0.5 font-mono text-xs font-semibold uppercase text-primary">
                {humanizeKey(user?.current_role)}
              </dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">Tenant isolation</dt>
              <dd className="mt-0.5 text-sm font-medium">{tenantName} · PostgreSQL RLS</dd>
            </div>
          </dl>
        </div>

        <div className="space-y-3">
          <h2 className="flex items-center gap-2 font-display text-base font-semibold">
            <Lock className="h-4 w-4 text-primary" /> Disclosure controls
          </h2>
          <dl className="divide-y border-y border-border/70 text-sm">
            <div className="flex justify-between gap-3 py-2.5">
              <dt className="text-muted-foreground">Minimum contributors</dt>
              <dd className="font-mono text-xs font-semibold">≥ 10</dd>
            </div>
            <div className="flex justify-between gap-3 py-2.5">
              <dt className="text-muted-foreground">Small-cell masking</dt>
              <dd className="font-mono text-xs font-semibold">1–4 suppressed</dd>
            </div>
            <div className="flex justify-between gap-3 py-2.5">
              <dt className="text-muted-foreground">Complementary suppression</dt>
              <dd className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">Enforced</dd>
            </div>
            <div className="flex justify-between gap-3 py-2.5">
              <dt className="text-muted-foreground">Export formula sanitization</dt>
              <dd className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">Active</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="flex items-center gap-2 font-display text-base font-semibold">
          <ScrollText className="h-4 w-4 text-primary" /> Recent audit events
        </h2>
        {audit.isError ? (
          <p className="text-xs text-muted-foreground">
            Audit feed requires privacy officer or platform admin scope. Sign in with that role to review the append-only log.
          </p>
        ) : audit.isLoading ? (
          <p className="text-xs text-muted-foreground">Loading audit events…</p>
        ) : !audit.data?.length ? (
          <p className="text-xs text-muted-foreground">No audit events recorded for this tenant yet.</p>
        ) : (
          <ul className="divide-y border-t border-border/70">
            {audit.data.slice(0, 12).map((event) => (
              <li key={event.id} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium">
                    {humanizeKey(event.action || event.event_type || "event")}
                    {event.resource_type ? ` · ${humanizeKey(event.resource_type)}` : ""}
                  </p>
                  <p className="text-[11px] text-muted-foreground">{event.actor_email || "system"}</p>
                </div>
                <p className="text-[11px] text-muted-foreground">{formatTimestamp(event.created_at)}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};
