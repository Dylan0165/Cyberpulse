"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { authApi, usersApi } from "@/lib/api";
import { setToken, clearToken } from "@/lib/auth";

// Loosely typed plan info returned by GET /users/me/plan.
export type PlanInfo = {
  plan: string;
  plan_interval?: string;
  plan_expires_at?: string | null;
  max_targets?: number;
  max_scans_per_month?: number;
  scans_this_month?: number;
  scans_remaining?: number; // -1 = unlimited
  unlimited_scans?: boolean;
  custom_modules?: boolean;
  scheduled_scans?: boolean;
  role?: string;
  features?: Record<string, any>;
  [key: string]: any;
} | null;

export interface AuthUser {
  id: string;
  email: string;
  name?: string;
  company_name?: string;
  api_key?: string;
  terms_accepted?: boolean;
  terms_accepted_at?: string | null;
  onboarding_completed?: boolean;
  notify_on_complete?: boolean;
  notification_email?: string | null;
  plan?: string;
  role?: string;
  created_at?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (data: {
    email: string;
    password: string;
    name: string;
    company_name: string;
  }) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  planInfo: PlanInfo;
  refreshPlan: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [planInfo, setPlanInfo] = useState<PlanInfo>(null);

  const loadPlan = useCallback(async () => {
    try {
      const res: any = await usersApi.plan();
      setPlanInfo(res?.data ?? null);
    } catch {
      // best-effort — never crash the app if the plan endpoint fails
      setPlanInfo(null);
    }
  }, []);

  const loadMe = useCallback(async () => {
    try {
      const res: any = await authApi.me();
      const u: AuthUser | null = res.data ?? null;
      setUser(u);
      if (u) {
        await loadPlan();
      } else {
        setPlanInfo(null);
      }
    } catch {
      // best-effort — 401 / network errors leave user null, no toast
      setUser(null);
      setPlanInfo(null);
    }
  }, [loadPlan]);

  useEffect(() => {
    let active = true;
    (async () => {
      await loadMe();
      if (active) setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [loadMe]);

  const refreshPlan = useCallback(async () => {
    await loadPlan();
  }, [loadPlan]);

  const login = useCallback(async (email: string, password: string) => {
    const res: any = await authApi.login({ email, password });
    const token = res?.data?.token;
    if (token) setToken(token);
    const u: AuthUser | null = res?.data?.user ?? null;
    setUser(u);
    if (u) loadPlan();
    return u as AuthUser;
  }, [loadPlan]);

  const register = useCallback(
    async (data: {
      email: string;
      password: string;
      name: string;
      company_name: string;
    }) => {
      const res: any = await authApi.register(data);
      const token = res?.data?.token;
      if (token) setToken(token);
      const u: AuthUser | null = res?.data?.user ?? null;
      setUser(u);
      if (u) loadPlan();
      return u as AuthUser;
    },
    [loadPlan]
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // best-effort — ignore network failure
    }
    clearToken();
    setUser(null);
    setPlanInfo(null);
  }, []);

  const refresh = useCallback(async () => {
    await loadMe();
  }, [loadMe]);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refresh,
        planInfo,
        refreshPlan,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
