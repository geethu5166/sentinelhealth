import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatSuppressed(value: number | null | undefined, isSuppressed: boolean): string {
  if (isSuppressed) return "Suppressed for privacy";
  if (value === null || value === undefined) return "—";
  return value.toLocaleString();
}

export function formatTimestamp(iso: string, timezone: string = "Asia/Kolkata"): string {
  try {
    return new Date(iso).toLocaleString("en-IN", { timeZone: timezone });
  } catch {
    return iso;
  }
}

export function humanizeKey(value?: string | null): string {
  if (!value) return "—";
  return value.replace(/_/g, " ");
}

export function severityBadgeClass(severity: string): string {
  const map: Record<string, string> = {
    advisory:
      "bg-[hsl(var(--severity-advisory)/0.12)] text-[hsl(var(--severity-advisory))] border-[hsl(var(--severity-advisory)/0.35)]",
    watch:
      "bg-[hsl(var(--severity-watch)/0.14)] text-[hsl(var(--severity-watch))] border-[hsl(var(--severity-watch)/0.4)]",
    warning:
      "bg-[hsl(var(--severity-warning)/0.14)] text-[hsl(var(--severity-warning))] border-[hsl(var(--severity-warning)/0.4)]",
    critical:
      "bg-[hsl(var(--severity-critical)/0.14)] text-[hsl(var(--severity-critical))] border-[hsl(var(--severity-critical)/0.45)]",
    emergency:
      "bg-[hsl(var(--severity-emergency)/0.18)] text-[hsl(var(--severity-emergency))] border-[hsl(var(--severity-emergency)/0.55)] font-bold",
  };
  return map[severity] || "bg-muted text-muted-foreground border-border";
}

export function severityAccentClass(severity: string): string {
  const map: Record<string, string> = {
    advisory: "border-l-[hsl(var(--severity-advisory))]",
    watch: "border-l-[hsl(var(--severity-watch))]",
    warning: "border-l-[hsl(var(--severity-warning))]",
    critical: "border-l-[hsl(var(--severity-critical))]",
    emergency: "border-l-[hsl(var(--severity-emergency))]",
  };
  return map[severity] || "border-l-border";
}
