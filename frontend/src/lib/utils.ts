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

export function severityBadgeClass(severity: string): string {
  const map: Record<string, string> = {
    advisory: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 border-blue-300",
    watch: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200 border-amber-300",
    warning: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200 border-orange-300",
    critical: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200 border-red-300",
    emergency: "bg-red-200 text-red-950 dark:bg-red-950 dark:text-red-100 border-red-500 font-bold",
  };
  return map[severity] || "bg-gray-100 text-gray-800 border-gray-300";
}

