import React from "react";
import { Bell, Loader2, Radio, Sliders } from "lucide-react";
import { useDetectors, useTrainRealtimeBaselines } from "../../lib/api/hooks";
import { Button } from "../../components/ui/button";
import { PageHeader } from "../../components/ui/page-header";
import { Badge } from "../../components/ui/badge";
import { formatTimestamp, humanizeKey } from "../../lib/utils";

export const SettingsPage: React.FC = () => {
  const detectors = useDetectors();
  const train = useTrainRealtimeBaselines();

  return (
    <div className="mx-auto max-w-5xl animate-fade-in space-y-10">
      <PageHeader
        title="Detection & routing"
        description="Active screening stack, thresholds, and notification routes. Threshold edits require dual control."
        actions={
          <Button
            size="sm"
            variant="outline"
            disabled={train.isPending}
            onClick={() => train.mutate({ latitude: 21.1458, longitude: 79.0882, lookback_days: 60 })}
          >
            {train.isPending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Radio className="mr-1.5 h-4 w-4" />}
            Retrain live baselines
          </Button>
        }
      />

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Sliders className="h-4 w-4 text-primary" />
          <h2 className="font-display text-lg font-semibold">Surveillance thresholds</h2>
        </div>
        <dl className="divide-y border-y border-border/80 text-sm">
          <div className="flex items-center justify-between gap-4 py-3">
            <dt className="text-muted-foreground">Heat watch screening</dt>
            <dd className="font-mono text-xs font-semibold">Apparent temp ≥ 40.0°C</dd>
          </div>
          <div className="flex items-center justify-between gap-4 py-3">
            <dt className="text-muted-foreground">Air quality watch</dt>
            <dd className="font-mono text-xs font-semibold">PM2.5 24h mean ≥ 35.5 µg/m³</dd>
          </div>
          <div className="flex items-center justify-between gap-4 py-3">
            <dt className="text-muted-foreground">Residual anomaly cutoff</dt>
            <dd className="font-mono text-xs font-semibold">Z &gt; +2.0σ</dd>
          </div>
          <div className="flex items-center justify-between gap-4 py-3">
            <dt className="text-muted-foreground">EWMA (λ / L)</dt>
            <dd className="font-mono text-xs font-semibold">0.25 / 2.5σ</dd>
          </div>
          <div className="flex items-center justify-between gap-4 py-3">
            <dt className="text-muted-foreground">CUSUM (k / h)</dt>
            <dd className="font-mono text-xs font-semibold">0.5 / 4.0</dd>
          </div>
        </dl>
      </section>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-primary" />
          <h2 className="font-display text-lg font-semibold">Active detector catalog</h2>
        </div>
        {detectors.isLoading ? (
          <p className="text-xs text-muted-foreground">Loading detector catalog…</p>
        ) : detectors.data ? (
          <div className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Source: {detectors.data.realtime_source} · evidence {detectors.data.evidence_label}
            </p>
            <div className="flex flex-wrap gap-2">
              {detectors.data.baselines.map((b) => (
                <Badge key={b} variant="outline" className="font-mono text-[10px]">
                  {humanizeKey(b)}
                </Badge>
              ))}
            </div>
            <ul className="space-y-2 text-xs text-muted-foreground">
              {detectors.data.detectors.map((d) => (
                <li key={d.name}>
                  <span className="font-semibold text-foreground">{d.name}</span> — {d.role}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">Detector catalog unavailable.</p>
        )}
        {train.data ? (
          <p className="text-[11px] text-muted-foreground">
            Last train: {humanizeKey(train.data.selected_model)} · HI {train.data.expected_value.toFixed(1)}°C ·{" "}
            {formatTimestamp(train.data.trained_at)}
          </p>
        ) : null}
      </section>

      <section className="space-y-4">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-primary" />
          <h2 className="font-display text-lg font-semibold">Notification routes</h2>
        </div>
        <dl className="divide-y border-y border-border/80 text-sm">
          <div className="flex items-center justify-between gap-4 py-3">
            <dt className="text-muted-foreground">Workplace safety manager</dt>
            <dd className="text-xs font-medium">In-app · SMTP</dd>
          </div>
          <div className="flex items-center justify-between gap-4 py-3">
            <dt className="text-muted-foreground">Occupational health analyst</dt>
            <dd className="text-xs font-medium">In-app · SMTP</dd>
          </div>
          <div className="flex items-center justify-between gap-4 py-3">
            <dt className="text-muted-foreground">Flapping cooldown</dt>
            <dd className="font-mono text-xs font-semibold">240 minutes</dd>
          </div>
        </dl>
      </section>
    </div>
  );
};
