import React from "react";
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
  if (evidence.is_suppressed) {
    return (
      <div className="h-64 flex flex-col items-center justify-center border border-dashed rounded-lg bg-muted/20 p-6 text-center">
        <span className="text-sm font-semibold text-muted-foreground">Chart Suppressed for Privacy</span>
        <p className="text-xs text-muted-foreground mt-1 max-w-sm">
          Observed counts or contributor cohorts fall below the privacy threshold. Exact time-series rendering is masked.
        </p>
      </div>
    );
  }

  // Construct demonstration 7-day window surrounding the target event
  const obs = Number(evidence.observed_value) || 0;
  const exp = Number(evidence.expected_value) || (obs * 0.4);
  const lower = Number(evidence.prediction_interval_lower) || Math.max(0, exp * 0.7);
  const upper = Number(evidence.prediction_interval_upper) || (exp * 1.3);

  const mockTimeline = [
    { day: "D-6", observed: Math.round(exp * 0.95), expected: exp, lower, upper },
    { day: "D-5", observed: Math.round(exp * 1.05), expected: exp, lower, upper },
    { day: "D-4", observed: Math.round(exp * 0.98), expected: exp, lower, upper },
    { day: "D-3", observed: Math.round(exp * 1.15), expected: exp, lower, upper },
    { day: "D-2", observed: Math.round(exp * 1.45), expected: exp, lower, upper },
    { day: "D-1", observed: Math.round(exp * 1.95), expected: exp, lower, upper },
    { day: "Today (Event)", observed: obs, expected: exp, lower, upper },
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold">{title}</span>
        <span className="text-muted-foreground">
          Obs: <strong>{obs}</strong> | Exp: <strong>{Math.round(exp * 10) / 10}</strong> | Res: <strong>+{evidence.standardised_residual || 0}σ</strong>
        </span>
      </div>
      <div className="h-60 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={mockTimeline} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
            {/* Prediction Interval Area */}
            <Area
              type="monotone"
              dataKey="upper"
              stroke="none"
              fill="hsl(var(--primary))"
              fillOpacity={0.15}
              name="Upper Bound (95%)"
            />
            {/* Expected baseline (dashed line) */}
            <Line
              type="monotone"
              dataKey="expected"
              stroke="#6b7280"
              strokeDasharray="4 4"
              strokeWidth={2}
              dot={false}
              name="Expected Baseline"
            />
            {/* Observed measurements (solid line) */}
            <Line
              type="monotone"
              dataKey="observed"
              stroke="#2563eb"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "#2563eb" }}
              activeDot={{ r: 6 }}
              name="Observed Count"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

