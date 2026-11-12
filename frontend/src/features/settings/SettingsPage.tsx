import React from "react";
import { Bell, Sliders } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { PageHeader } from "../../components/ui/page-header";

export const SettingsPage: React.FC = () => {
  return (
    <div className="mx-auto max-w-7xl animate-fade-in space-y-6">
      <PageHeader
        title="Settings & thresholds"
        description="Authorised detection limits, versioned playbooks, and notification routing. Read-only in this demo."
      />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Sliders className="h-4 w-4 text-primary" aria-hidden /> Active surveillance thresholds
            </CardTitle>
            <CardDescription className="text-xs">
              Configured in config/demo-policies.yaml. Requires safety officer approval to change.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between border-b py-1.5">
              <span>Heat watch screening threshold</span>
              <span className="font-mono font-bold">Apparent temp ≥ 40.0°C</span>
            </div>
            <div className="flex items-center justify-between border-b py-1.5">
              <span>Air quality watch threshold</span>
              <span className="font-mono font-bold">PM2.5 24h mean ≥ 35.5 µg/m³</span>
            </div>
            <div className="flex items-center justify-between border-b py-1.5">
              <span>Standardised residual anomaly cutoff</span>
              <span className="font-mono font-bold">Z-score &gt; +2.0σ</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span>One-sided EWMA smoothing (λ)</span>
              <span className="font-mono font-bold">0.30 (L = 2.5σ)</span>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Bell className="h-4 w-4 text-primary" aria-hidden /> Notification routes
            </CardTitle>
            <CardDescription className="text-xs">
              Delivery channel routing for early warnings and overdue mitigation tasks.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between border-b py-1.5">
              <span>Workplace safety manager</span>
              <span className="font-mono text-muted-foreground">In-app + Mailpit</span>
            </div>
            <div className="flex items-center justify-between border-b py-1.5">
              <span>Occupational health analyst</span>
              <span className="font-mono text-muted-foreground">In-app + Mailpit</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span>Notification flapping cooldown</span>
              <span className="font-mono font-bold">240 minutes</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
