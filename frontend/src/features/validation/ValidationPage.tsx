import React, { useState } from "react";
import { AlertTriangle, Play } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { PageHeader } from "../../components/ui/page-header";

const FIXTURE_RESULTS = {
  scenario: "heat-gradual",
  data_label: "benchmark",
  metrics: {
    event_sensitivity: 1.0,
    alert_ppv: 0.857,
    false_alarm_burden_per_week: 0.2,
    useful_action_lead_days: 1.0,
  },
  limitations: [
    "Evaluated on a chronological holdout benchmark with withheld labels.",
    "Real-world clinical sensitivity and PPV require prospective pilot validation.",
    "Weather screening uses model grid resolution, not on-site micro-climate measurements.",
  ],
};

export const ValidationPage: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [hasRun, setHasRun] = useState(false);

  const handleRunReplay = () => {
    setIsRunning(true);
    window.setTimeout(() => {
      setIsRunning(false);
      setHasRun(true);
    }, 900);
  };

  const results = hasRun ? FIXTURE_RESULTS : null;

  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Replay validation"
        description="Honest evaluation using chronological replay with withheld ground-truth labels and episode matching."
        actions={
          <Button onClick={handleRunReplay} disabled={isRunning} size="sm">
            <Play className="mr-1.5 h-4 w-4" />
            {isRunning ? "Running replay…" : "Run heat-gradual replay"}
          </Button>
        }
      />

      <Card className="border-border/80 bg-secondary/30 shadow-panel">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-semibold">
            Benchmark replay mode
          </CardTitle>
          <CardDescription className="text-xs">
            Chronological replay of the packaged `heat-gradual` scenario. Metrics validate pipeline wiring and
            matching logic — not certified real-world effectiveness.
          </CardDescription>
        </CardHeader>
      </Card>

      {!results ? (
        <Card className="shadow-panel">
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            Run the heat-gradual replay to load sensitivity, PPV, and lead-time metrics.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card className="shadow-panel">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground">Event sensitivity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-display text-3xl font-semibold text-emerald-600 dark:text-emerald-400">
                  {(results.metrics.event_sensitivity * 100).toFixed(0)}%
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">Matched ground-truth heat events</p>
              </CardContent>
            </Card>
            <Card className="shadow-panel">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground">Alert episode PPV</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-display text-3xl font-semibold text-primary">
                  {(results.metrics.alert_ppv * 100).toFixed(1)}%
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">Deduplicated true positive episodes</p>
              </CardContent>
            </Card>
            <Card className="shadow-panel">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground">False alarm burden</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-display text-3xl font-semibold text-amber-600">
                  {results.metrics.false_alarm_burden_per_week}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">Unmatched episodes / site-week</p>
              </CardContent>
            </Card>
            <Card className="shadow-panel">
              <CardHeader className="pb-2">
                <CardTitle className="text-xs font-semibold text-muted-foreground">Action lead time</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-display text-3xl font-semibold">
                  +{results.metrics.useful_action_lead_days * 24}h
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">Warning before peak impact (benchmark)</p>
              </CardContent>
            </Card>
          </div>

          <Card className="border-border/80 bg-secondary/30 shadow-panel">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                <AlertTriangle className="h-4 w-4 text-primary" aria-hidden /> Limitations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                {results.limitations.map((lim) => (
                  <li key={lim}>{lim}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};
