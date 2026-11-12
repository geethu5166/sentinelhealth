import React from "react";
import { cn } from "../../lib/utils";

type StatusTone = "online" | "fresh" | "stale" | "offline" | "degraded" | "unknown";

const TONE_CLASS: Record<StatusTone, string> = {
  online: "bg-emerald-500",
  fresh: "bg-emerald-500",
  stale: "bg-amber-500",
  offline: "bg-red-500",
  degraded: "bg-orange-500",
  unknown: "bg-slate-400",
};

const TEXT_CLASS: Record<StatusTone, string> = {
  online: "text-emerald-700 dark:text-emerald-400",
  fresh: "text-emerald-700 dark:text-emerald-400",
  stale: "text-amber-700 dark:text-amber-400",
  offline: "text-red-700 dark:text-red-400",
  degraded: "text-orange-700 dark:text-orange-400",
  unknown: "text-muted-foreground",
};

interface StatusDotProps {
  status?: string | null;
  label?: string;
  pulse?: boolean;
  className?: string;
}

export function resolveStatusTone(status?: string | null): StatusTone {
  const value = (status || "").toLowerCase();
  if (["online", "active", "fresh", "ok", "healthy"].includes(value)) return value === "fresh" ? "fresh" : "online";
  if (["stale", "delayed", "lagging"].includes(value)) return "stale";
  if (["offline", "down", "error", "failed"].includes(value)) return "offline";
  if (["degraded", "partial", "warning"].includes(value)) return "degraded";
  return "unknown";
}

export const StatusDot: React.FC<StatusDotProps> = ({
  status,
  label,
  pulse = false,
  className,
}) => {
  const tone = resolveStatusTone(status);
  const display = label || (status ? status.replace(/_/g, " ") : "Unknown");

  return (
    <span className={cn("inline-flex items-center gap-1.5 text-xs font-semibold capitalize", TEXT_CLASS[tone], className)}>
      <span
        className={cn("h-2 w-2 rounded-full", TONE_CLASS[tone], pulse && tone !== "offline" && tone !== "unknown" && "animate-pulse")}
        aria-hidden
      />
      {display}
    </span>
  );
};
