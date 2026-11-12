import React from "react";
import { Ban, Lock, UserCheck } from "lucide-react";
import { useUser } from "../../auth/useUser";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { PageHeader } from "../../components/ui/page-header";
import { humanizeKey } from "../../lib/utils";

export const GovernancePage: React.FC = () => {
  const { user } = useUser();

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Governance & privacy"
        description="Authorisation boundaries, prohibited uses, small-cell disclosure controls, and export review."
      />

      <Card className="border-destructive/40 bg-destructive/5 shadow-panel">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm font-bold text-destructive">
            <Ban className="h-4 w-4" aria-hidden /> Prohibited operational & employment uses
          </CardTitle>
          <CardDescription className="text-xs">
            Mandatory policy condition for deploying SentinelHealth in population and workforce health settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-xs text-foreground/90">
          <p>
            SentinelHealth early warnings are population-level statistical risk indicators. The platform{" "}
            <strong>must never</strong> be used for:
          </p>
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            <li>Employee productivity scoring, individual performance ranking, or appraisal weighting.</li>
            <li>Individual sickness monitoring, attendance surveillance, or automated disciplinary action.</li>
            <li>Determining clinical fitness for work or employment termination.</li>
            <li>Health insurance eligibility discrimination or premium adjustments.</li>
            <li>Re-identification attempts against anonymized or suppressed aggregate data cells.</li>
          </ul>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <UserCheck className="h-4 w-4 text-primary" aria-hidden /> Active operator credentials
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div>
              <span className="text-muted-foreground">Authenticated identity</span>
              <p className="mt-0.5 text-sm font-semibold">
                {user?.display_name} ({user?.email})
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Active role</span>
              <p className="mt-0.5 font-mono text-sm font-bold uppercase text-primary">
                {humanizeKey(user?.current_role)}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Tenant isolation scope</span>
              <p className="mt-0.5 font-semibold">
                {user?.memberships?.[0]?.tenant_name || "District Health Authority"} (PostgreSQL RLS)
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Lock className="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden /> Disclosure controls
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex items-center justify-between border-b py-1">
              <span>Minimum upstream contributors</span>
              <span className="font-mono font-bold">≥ 10 individuals</span>
            </div>
            <div className="flex items-center justify-between border-b py-1">
              <span>Small-cell event masking</span>
              <span className="font-mono font-bold">1 – 4 counts suppressed</span>
            </div>
            <div className="flex items-center justify-between border-b py-1">
              <span>Complementary marginal suppression</span>
              <span className="font-bold text-emerald-700 dark:text-emerald-400">Enforced</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span>Export CSV formula sanitization</span>
              <span className="font-bold text-emerald-700 dark:text-emerald-400">Active</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
