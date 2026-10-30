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
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user?.current_role && !allowedRoles.includes(user.current_role)) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-xl font-bold text-destructive">Access Restricted</h2>
        <p className="mt-2 text-muted-foreground">
          Your role ({user.current_role}) does not have permission to view this resource.
        </p>
      </div>
    );
  }

  return <>{children}</>;
};

