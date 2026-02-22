"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { User, AuthResponse } from "@/types";
import { api, ApiRequestError } from "@/lib/api-client";
import {
  getAuthToken,
  setAuthToken,
  setStoredUser,
  getStoredUser,
  clearAuth,
} from "@/lib/auth";

interface UseAuthReturn {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
}

interface RegisterData {
  email: string;
  password: string;
  display_name: string;
  account_type: "family" | "school" | "club";
}

export function useAuth(): UseAuthReturn {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      const storedUser = getStoredUser();
      if (storedUser) {
        setUser(storedUser as unknown as User);
        setIsLoading(false);
      } else {
        api
          .get<User>("/api/v1/auth/me")
          .then((userData) => {
            setUser(userData);
            setStoredUser(userData as unknown as Record<string, unknown>);
          })
          .catch(() => {
            clearAuth();
            setUser(null);
          })
          .finally(() => setIsLoading(false));
      }
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.post<AuthResponse>(
          "/api/v1/auth/login",
          { email, password }
        );
        setAuthToken(response.access_token);
        setStoredUser(response.user as unknown as Record<string, unknown>);
        setUser(response.user);
        router.push("/dashboard");
      } catch (err) {
        const message =
          err instanceof ApiRequestError
            ? err.detail
            : "Login failed. Please try again.";
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/api/v1/auth/logout");
    } catch {
      // Continue with local logout even if server logout fails
    }
    clearAuth();
    setUser(null);
    router.push("/");
  }, [router]);

  const register = useCallback(
    async (data: RegisterData) => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.post<AuthResponse>(
          "/api/v1/auth/register",
          data
        );
        setAuthToken(response.access_token);
        setStoredUser(response.user as unknown as Record<string, unknown>);
        setUser(response.user);
        router.push("/dashboard");
      } catch (err) {
        const message =
          err instanceof ApiRequestError
            ? err.detail
            : "Registration failed. Please try again.";
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [router]
  );

  return {
    user,
    isLoading,
    isAuthenticated: user !== null,
    error,
    login,
    logout,
    register,
  };
}
