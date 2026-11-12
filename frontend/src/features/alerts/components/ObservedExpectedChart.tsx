import React, { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertEvidence } from "../../../lib/api/types";

interface ChartProps {
  evidence: AlertEvidence;
  title: string;
}

export const ObservedExpectedChart: React.FC<ChartProps> = ({ evidence, title }) => {
  const obs = Number(evidence.observed_value) || 0;
  const exp = Number(evidence.expected_value) || obs * 0.4;
  const lower = Number(evidence.prediction_interval_lower) || Math.max(0, exp * 0.7);
  const upper = Number(evidence.prediction_interval_upper) || exp * 1.3;
  const band = Math.max(0, upper - lower);

  const timeline = useMemo(() => {
    // Illustrative 7-day context reconstructed from the single observation point.
    const ramp = [0.95, 1.05, 0.98, 1.15, 1.45, 1.95, 1];
    return ramp.map((factor, index) => {
      const isEvent = index === ramp.length - 1;
      const observed = isEvent ? obs : Math.round(exp * factor);
      return {
        day: isEvent ? "Event day" : `D-${ramp.length - 1 - index}`,
        observed,
        expected: Math.round(exp * 10) / 10,
        lower,
        band,
      };
    });
  }, [obs, exp, lower, band]);

  if (evidence.is_suppressed) {
    return (
      <div className="flex h-64 flex-col items-center justify-center rounded-lg border border-dashed bg-muted/20 p-6 text-center">
        <span className="text-sm font-semibold text-muted-foreground">Chart suppressed for privacy</span>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          Observed counts or contributor cohorts fall below the privacy threshold. Exact time-series rendering is masked.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-semibold">{title}</span>
        <span className="text-muted-foreground">
          Obs: <strong className="font-mono text-foreground">{obs}</strong> · Exp:{" "}
          <strong className="font-mono text-foreground">{Math.round(exp * 10) / 10}</strong> · Res:{" "}
          <strong className="font-mono text-foreground">+{evidence.standardised_residual || 0}σ</strong>
        </span>
      </div>
      <p className="text-[10px] text-amber-700 dark:text-amber-400">
        Illustrative trajectory reconstructed from the event-day observation and baseline — not a stored multi-day series.
      </p>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={timeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis dataKey="day" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                borderColor: "hsl(var(--border))",
                fontSize: "12px",
                borderRadius: "6px",
              }}
            />
            <Area type="monotone" dataKey="lower" stackId="band" stroke="none" fill="transparent" name="PI lower" />
            <Area
              type="monotone"
              dataKey="band"
              stackId="band"
              stroke="none"
              fill="hsl(var(--primary))"
              fillOpacity={0.15}
              name="Prediction interval"
            />
            <Line
              type="monotone"
              dataKey="expected"
              stroke="#64748b"
              strokeDasharray="4 4"
              strokeWidth={2}
              dot={false}
              name="Expected baseline"
            />
            <Line
              type="monotone"
              dataKey="observed"
              stroke="hsl(var(--primary))"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "hsl(var(--primary))" }}
              activeDot={{ r: 6 }}
              name="Observed"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
