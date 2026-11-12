import React from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-6 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">Error 404</p>
      <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight">View not found</h1>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        The requested surveillance view does not exist or is outside your current session scope.
      </p>
      <Link to="/overview" className="mt-6">
        <Button size="sm">Return to overview</Button>
      </Link>
    </div>
  );
};
