import { useAuth } from "./AuthProvider";

export function useUser() {
  const { user, isAuthenticated, isLoading, loginAsDemoUser, logout } = useAuth();
  return {
    user,
    isAuthenticated,
    isLoading,
    loginAsDemoUser,
    logout,
    role: user?.current_role,
    tenantId: user?.current_tenant_id,
  };
}

