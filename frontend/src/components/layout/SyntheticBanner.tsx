import React from "react";
import { AlertTriangle } from "lucide-react";

export const SyntheticBanner: React.FC = () => {
  return (
    <div className="bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 text-xs font-medium text-amber-600 dark:text-amber-400 flex items-center justify-center gap-2">
      <AlertTriangle className="h-4 w-4" />
      <span>
        <strong>DEMONSTRATION PROTOTYPE:</strong> All health and workforce signals shown are synthetic and fictional.
        Not clinically validated, legally compliant, or intended for individual diagnosis or employment decisions.
      </span>
    </div>
  );
};

