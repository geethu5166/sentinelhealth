import React from "react";
import { AlertCircle, Clock, HeartPulse, TrendingUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";

export const ImpactPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Health & Resilience Operational Impact</h2>
        <p className="text-muted-foreground text-sm">
          Track response timing, completed mitigations, and prospective evaluation plans.
        </p>
      </div>

      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-semibold text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
            <AlertCircle className="h-4 w-4" /> Prospective Evaluation Principles
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          Observational before/after changes alone must not be described as caused by the system.
          Genuine health and absence reductions must be demonstrated through a pre-specified stepped-wedge or interrupted time-series rollout with epidemiological oversight.
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground">Mean Time to Acknowledgment</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-primary">24 min</div>
            <p className="text-[11px] text-muted-foreground mt-1">From initial multi-signal detection to human review</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground">Completed Mitigations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">92%</div>
            <p className="text-[11px] text-muted-foreground mt-1">Preventive tasks verified with on-site inspection</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground">Lead Over Conventional Reporting</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-purple-600 dark:text-purple-400">+48 hours</div>
            <p className="text-[11px] text-muted-foreground mt-1">Earlier than retrospective monthly clinic reports</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

