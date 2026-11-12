import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./button";
import { cn } from "../../lib/utils";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Unable to load data",
  description = "The surveillance API did not respond. Check connectivity and try again.",
  onRetry,
  className,
}) => {
  return (
    <div
      role="alert"
      className={cn(
        "rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-10 text-center",
        className
      )}
    >
      <AlertTriangle className="mx-auto h-8 w-8 text-destructive" aria-hidden />
      <h2 className="mt-3 text-sm font-semibold text-destructive">{title}</h2>
      <p className="mt-1 text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
        {description}
      </p>
      {onRetry ? (
        <Button size="sm" variant="outline" className="mt-4" onClick={onRetry}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Retry
        </Button>
      ) : null}
    </div>
  );
};
