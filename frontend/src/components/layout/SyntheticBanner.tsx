import React from "react";
import { AlertTriangle } from "lucide-react";

export const SyntheticBanner: React.FC = () => {
  return (
    <div
      role="status"
      className="flex items-start justify-center gap-2 border-b border-amber-500/25 bg-amber-500/10 px-4 py-2 text-xs font-medium text-amber-800 dark:text-amber-300 sm:items-center"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 sm:mt-0" aria-hidden />
      <span className="text-balance leading-relaxed">
        <strong>Demonstration prototype:</strong> all health and workforce signals are synthetic.
        Not clinically validated or intended for diagnosis, employment decisions, or real health data.
      </span>
    </div>
  );
};
