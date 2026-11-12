import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { UserInfo } from "../lib/api/types";
import { ApiError, apiFetch, getApiToken, setApiToken } from "../lib/api/client";

interface AuthContextType {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginAsDemoUser: (role: string, email: string, displayName?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  loginAsDemoUser: async () => {},
  logout: () => {},
});

const DEMO_PROFILES: Record<string, UserInfo> = {
  "safety@demo.local": {
    id: "demo-user-safety",
    email: "safety@demo.local",
    display_name: "Vikram Patel",
    external_id: "demo-sub-safety",
    is_active: true,
    current_role: "workplace_safety_manager",
    memberships: [
      {
        id: "mem-safety",
        tenant_id: "tenant-1",
        tenant_name: "Central District Health Authority",
        tenant_slug: "district_health_authority",
        role: "workplace_safety_manager",
        is_active: true,
      },
    ],
  },
  "analyst@demo.local": {
    id: "demo-user-analyst",
    email: "analyst@demo.local",
    display_name: "Dr. Ananya Sharma",
    external_id: "demo-sub-analyst",
    is_active: true,
    current_role: "public_health_analyst",
    memberships: [
      {
        id: "mem-analyst",
        tenant_id: "tenant-1",
        tenant_name: "Central District Health Authority",
        tenant_slug: "district_health_authority",
        role: "public_health_analyst",
        is_active: true,
      },
    ],
  },
  "ohanalyst@demo.local": {
    id: "demo-user-oh",
    email: "ohanalyst@demo.local",
    display_name: "Rajesh Kumar",
    external_id: "demo-sub-oh",
    is_active: true,
    current_role: "occupational_health_analyst",
    memberships: [
      {
        id: "mem-oh",
        tenant_id: "tenant-1",
        tenant_name: "Central District Health Authority",
        tenant_slug: "district_health_authority",
        role: "occupational_health_analyst",
        is_active: true,
      },
    ],
  },
  "privacy@demo.local": {
    id: "demo-user-privacy",
    email: "privacy@demo.local",
    display_name: "Meera Iyer",
    external_id: "demo-sub-privacy",
    is_active: true,
    current_role: "privacy_officer",
    memberships: [
      {
        id: "mem-privacy",
        tenant_id: "tenant-1",
        tenant_name: "Central District Health Authority",
        tenant_slug: "district_health_authority",
        role: "privacy_officer",
        is_active: true,
      },
    ],
  },
};

function demoProfileFromToken(token: string | null): UserInfo | null {
  if (!token?.startsWith("demo-token-")) return null;
  const parts = token.replace("demo-token-", "").split("-");
  const emailKey = `${parts[0]}@demo.local`;
  return DEMO_PROFILES[emailKey] || null;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchProfile = useCallback(async () => {
    const token = getApiToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      const profile = await apiFetch<UserInfo>("/me");
      setUser(profile);
    } catch (err) {
      // Demo tokens may run before the API is ready — keep the local demo identity and token.
      const demoUser = demoProfileFromToken(token);
      if (demoUser) {
        setUser(demoUser);
      } else {
        setApiToken(null);
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const loginAsDemoUser = async (role: string, email: string) => {
    const token = `demo-token-${email.split("@")[0]}-${role}`;
    setApiToken(token);
    const known = DEMO_PROFILES[email];
    if (known) {
      setUser({ ...known, current_role: role });
      setIsLoading(false);
    }
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
