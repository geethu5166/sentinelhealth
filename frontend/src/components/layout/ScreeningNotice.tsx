import React from "react";
import { ShieldCheck } from "lucide-react";

/** Compact honesty strip — screening decision support, not clinical diagnosis. */
export const ScreeningNotice: React.FC = () => {
  return (
    <div
      role="status"
      className="flex items-start justify-center gap-2 border-b border-primary/15 bg-primary/5 px-4 py-1.5 text-[11px] font-medium text-foreground/80 sm:items-center"
    >
      <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary sm:mt-0" aria-hidden />
      <span className="text-balance leading-relaxed">
        Screening decision support · aggregate signals only · not for individual diagnosis or employment actions
      </span>
    </div>
  );
};
