import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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

/** Event-day observed vs expected comparison — no fabricated multi-day trajectory. */
export const ObservedExpectedChart: React.FC<ChartProps> = ({ evidence, title }) => {
  const obs = Number(evidence.observed_value) || 0;
  const exp = Number(evidence.expected_value) || 0;
  const lower = Number(evidence.prediction_interval_lower);
  const upper = Number(evidence.prediction_interval_upper);
  const residual = Number(evidence.standardised_residual) || 0;

  const bars = [
    { label: "Expected", value: Math.round(exp * 100) / 100, kind: "expected" },
    { label: "Observed", value: Math.round(obs * 100) / 100, kind: "observed" },
  ];

  if (evidence.is_suppressed) {
    return (
      <div className="flex h-56 flex-col items-center justify-center rounded-lg border border-dashed bg-muted/20 p-6 text-center">
        <span className="text-sm font-semibold text-muted-foreground">Chart suppressed for privacy</span>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          Observed counts or contributor cohorts fall below the privacy threshold.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="font-semibold">{title}</span>
        <span className="font-mono text-muted-foreground">
          residual <strong className="text-foreground">+{residual.toFixed(2)}σ</strong>
          {Number.isFinite(lower) && Number.isFinite(upper) ? (
            <>
              {" "}
              · PI [{lower.toFixed(1)}, {upper.toFixed(1)}]
            </>
          ) : null}
        </span>
      </div>
      <div className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bars} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barCategoryGap="28%">
            <CartesianGrid strokeDasharray="3 3" opacity={0.25} vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                borderColor: "hsl(var(--border))",
                fontSize: "12px",
                borderRadius: "6px",
              }}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={72}>
              {bars.map((entry) => (
                <Cell
                  key={entry.kind}
                  fill={entry.kind === "observed" ? "hsl(var(--primary))" : "hsl(var(--muted-foreground) / 0.45)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-muted-foreground">
        Event-day screening comparison from stored evidence values — not a reconstructed multi-day series.
      </p>
    </div>
  );
};
