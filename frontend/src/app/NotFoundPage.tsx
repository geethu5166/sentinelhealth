import React from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-6">
      <h1 className="text-4xl font-extrabold tracking-tight text-primary">404</h1>
      <p className="mt-2 text-base text-muted-foreground">The requested surveillance view does not exist.</p>
      <Link to="/overview" className="mt-6">
        <Button size="sm">Return to Overview Dashboard</Button>
      </Link>
    </div>
  );
};

