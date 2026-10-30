import React, { createContext, useContext, useEffect, useState } from "react";
import { UserInfo } from "../lib/api/types";
import { apiFetch, setApiToken } from "../lib/api/client";

interface AuthContextType {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginAsDemoUser: (role: string, email: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: true,
  isLoading: false,
  loginAsDemoUser: async () => {},
  logout: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      setIsLoading(true);
      const profile = await apiFetch<UserInfo>("/me");
      setUser(profile);
    } catch {
      // In offline demo mode, fallback default mock user if API is still booting
      setUser({
        id: "demo-user-id",
        email: "safety@demo.local",
        display_name: "Vikram Patel",
        external_id: "demo-sub-safety",
        is_active: true,
        current_role: "workplace_safety_manager",
        memberships: [
          {
            id: "mem-1",
            tenant_id: "tenant-1",
            tenant_name: "Central District Health Authority",
            tenant_slug: "district_health_authority",
            role: "workplace_safety_manager",
            is_active: true,
          },
        ],
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const loginAsDemoUser = async (role: string, email: string) => {
    const token = `demo-token-${email.split("@")[0]}-${role}`;
    setApiToken(token);
    await fetchProfile();
  };

  const logout = () => {
    setApiToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        loginAsDemoUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

