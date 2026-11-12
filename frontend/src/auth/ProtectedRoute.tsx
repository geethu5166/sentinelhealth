import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthProvider";

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-background">
        <div
          className="h-9 w-9 animate-spin rounded-full border-4 border-primary border-t-transparent"
          aria-label="Loading session"
        />
        <p className="text-xs text-muted-foreground">Restoring session…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user?.current_role && !allowedRoles.includes(user.current_role)) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-xl font-bold text-destructive">Access restricted</h2>
        <p className="mt-2 text-muted-foreground">
          Your role ({user.current_role}) does not have permission to view this resource.
        </p>
      </div>
    );
  }

  return <>{children}</>;
};
