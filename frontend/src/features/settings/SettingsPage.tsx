import React from "react";
import { Sliders, Bell, FileCode2, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";

export const SettingsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">System Settings & Threshold Policies</h2>
        <p className="text-muted-foreground text-sm">
          Authorised detection limits, versioned playbooks, and notification routing configurations.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Sliders className="h-4 w-4 text-primary" /> Active Surveillance Thresholds
            </CardTitle>
            <CardDescription className="text-xs">
              Configured in config/demo-policies.yaml. Requires safety officer approval to change.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-1.5 border-b">
              <span>Heat Watch Screening Threshold</span>
              <span className="font-mono font-bold">Apparent Temp ≥ 40.0°C</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b">
              <span>Air Quality Watch Threshold</span>
              <span className="font-mono font-bold">PM2.5 24h Mean ≥ 35.5 µg/m³</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b">
              <span>Standardised Residual Anomaly Cutoff</span>
              <span className="font-mono font-bold">Z-score &gt; +2.0σ</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span>One-sided EWMA Smoothing Factor ($\lambda$)</span>
              <span className="font-mono font-bold">0.30 ($L=2.5\sigma$)</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Bell className="h-4 w-4 text-primary" /> Notification Routes & On-Call Dispatch
            </CardTitle>
            <CardDescription className="text-xs">
              Delivery channel routing for early warnings and overdue mitigation tasks.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between py-1.5 border-b">
              <span>Workplace Safety Manager</span>
              <span className="font-mono text-muted-foreground">In-App + Mailpit (safety@demo.local)</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b">
              <span>Occupational Health Analyst</span>
              <span className="font-mono text-muted-foreground">In-App + Mailpit (ohanalyst@demo.local)</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span>Notification Flapping Cooldown</span>
              <span className="font-mono font-bold">240 minutes</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

