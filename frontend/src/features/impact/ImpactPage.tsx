import React from "react";
import { AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { PageHeader } from "../../components/ui/page-header";

export const ImpactPage: React.FC = () => {
  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Operational impact"
        description="Track response timing, completed mitigations, and prospective evaluation plans."
      />

      <Card className="border-amber-500/30 bg-amber-500/5 shadow-panel">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 dark:text-amber-400">
            <AlertCircle className="h-4 w-4" aria-hidden /> Prospective evaluation principles
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground leading-relaxed">
          Observational before/after changes alone must not be described as caused by the system. Genuine health and
          absence reductions require a pre-specified stepped-wedge or interrupted time-series rollout with
          epidemiological oversight. Metrics below are <strong>illustrative placeholders</strong> for the MVP shell —
          not measured outcomes from this deployment.
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <Card className="shadow-panel">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground">Mean time to acknowledgment</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold text-primary">—</div>
            <p className="mt-1 text-[11px] text-muted-foreground">Instrument after pilot logging is enabled</p>
          </CardContent>
        </Card>
        <Card className="shadow-panel">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground">Completed mitigations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold">—</div>
            <p className="mt-1 text-[11px] text-muted-foreground">Derived from verified task completions</p>
          </CardContent>
        </Card>
        <Card className="shadow-panel">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground">Lead over conventional reporting</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-display text-3xl font-semibold">—</div>
            <p className="mt-1 text-[11px] text-muted-foreground">Requires paired clinic report baselines</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
