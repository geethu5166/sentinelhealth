import React from "react";
import { Ban, CheckCircle2, FileSpreadsheet, Lock, Shield, UserCheck } from "lucide-react";
import { useUser } from "../../auth/useUser";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";

export const GovernancePage: React.FC = () => {
  const { user } = useUser();

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Governance, Roles & Privacy Policies</h2>
        <p className="text-muted-foreground text-sm">
          Authorisation boundaries, strict prohibited uses, small-cell disclosure controls, and export review audit.
        </p>
      </div>

      {/* Prohibited Uses Warning Card */}
      <Card className="border-destructive/40 bg-destructive/5">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-bold text-destructive flex items-center gap-2">
            <Ban className="h-4 w-4" /> Prohibited Operational & Employment Uses
          </CardTitle>
          <CardDescription className="text-xs">
            Mandatory policy condition for deploying SentinelHealth in population and workforce health settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-xs text-foreground/90 space-y-2">
          <p>
            SentinelHealth early warnings are population-level statistical risk indicators. The platform <strong>MUST NEVER</strong> be used for:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
            <li>Employee productivity scoring, individual performance ranking, or appraisal weighting.</li>
            <li>Individual sickness monitoring, attendance surveillance, or automated disciplinary action.</li>
            <li>Determining clinical fitness for work or employment termination.</li>
            <li>Health insurance eligibility discrimination or premium adjustments.</li>
            <li>Re-identification attempts against anonymized or suppressed aggregate data cells.</li>
          </ul>
        </CardContent>
      </Card>

      {/* Current User Scope */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-primary" /> Active Operator Credentials
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div>
              <span className="text-muted-foreground">Authenticated Identity:</span>
              <p className="font-semibold text-sm mt-0.5">{user?.display_name} ({user?.email})</p>
            </div>
            <div>
              <span className="text-muted-foreground">Active Role:</span>
              <p className="font-mono uppercase font-bold text-primary mt-0.5">{user?.current_role?.replace(/_/g, " ")}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Tenant Isolation Scope:</span>
              <p className="font-semibold mt-0.5">District Health Authority (PostgreSQL RLS Active)</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Lock className="h-4 w-4 text-emerald-500" /> Disclosure Control Policies
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex items-center justify-between py-1 border-b">
              <span>Minimum Upstream Contributors</span>
              <span className="font-bold font-mono">≥ 10 individuals</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b">
              <span>Small-Cell Event Masking</span>
              <span className="font-bold font-mono">1 – 4 counts suppressed</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b">
              <span>Complementary Marginal Suppression</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">Enforced</span>
            </div>
            <div className="flex items-center justify-between py-1">
              <span>Export CSV Formula Sanitization</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">Active (OWASP CSV Defenses)</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

