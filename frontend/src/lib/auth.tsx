"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { api, clearTokens, getToken, setTokens, usesCookieSession } from "@/lib/api";
import type { TokenPair, User } from "@/lib/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  loggingOut: boolean;
  login: (email: string, password: string, mfaCode?: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (usesCookieSession) clearTokens();
    if (!usesCookieSession && !getToken()) {
      setLoading(false);
      return;
    }
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => { /* unauthenticated or temporarily offline */ })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const expired = () => {
      setUser(null);
      const publicPaths = ["/", "/login", "/register", "/forgot-password", "/reset-password", "/verify-email"];
      if (!publicPaths.includes(window.location.pathname)) router.push("/login");
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, [router]);

  async function login(email: string, password: string, mfaCode?: string) {
    setLoggingOut(false);
    const tokens = await api.post<TokenPair>("/auth/login", {
      email,
      password,
      mfa_code: mfaCode || null,
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    const me = await api.get<User>("/auth/me");
    setUser(me);
    router.push("/dashboard");
  }

  async function register(email: string, password: string, fullName?: string) {
    await api.post("/auth/register", {
      email,
      password,
      full_name: fullName || null,
    });
    await login(email, password);
  }

  async function logout() {
    setLoggingOut(true);
    let failed = false;
    try { await api.post("/auth/logout-all"); } catch { failed = true; }
    if (usesCookieSession && failed) {
      try { await api.post("/auth/browser/clear"); } catch { /* server may be offline */ }
    }
    clearTokens();
    setUser(null);
    router.push(failed ? "/login?logout=unconfirmed" : "/login");
  }

  return (
    <AuthContext.Provider value={{ user, loading, loggingOut, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
