import { useSyncExternalStore } from "react";
import { api } from "./api";
import {
  clearSession,
  getCurrentUser,
  setSession,
  subscribeSession,
  type SessionUser,
} from "./auth";

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: SessionUser;
}

export function useAuth() {
  const user = useSyncExternalStore(subscribeSession, getCurrentUser, getCurrentUser);

  async function login(email: string, password: string): Promise<SessionUser> {
    const response = await api.post<LoginResponse>("/api/v1/auth/login", { email, password });
    setSession(response);
    return response.user;
  }

  function logout() {
    clearSession();
  }

  return { user, isAuthenticated: user !== null, login, logout };
}
