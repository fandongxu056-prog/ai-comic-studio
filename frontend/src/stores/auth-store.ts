/** Authentication store — token management, user profile, login/logout. */

import { create } from "zustand";

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
  created_at: string | null;
}

interface AuthState {
  user: UserProfile | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
  refreshAccessToken: () => Promise<boolean>;
  clearError: () => void;
}

const API_BASE = "/api/v1/auth";

function getStoredTokens(): { access: string | null; refresh: string | null } {
  try {
    return {
      access: localStorage.getItem("access_token"),
      refresh: localStorage.getItem("refresh_token"),
    };
  } catch {
    return { access: null, refresh: null };
  }
}

function storeTokens(access: string, refresh: string) {
  try {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
  } catch {}
}

function clearStoredTokens() {
  try {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  } catch {}
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: getStoredTokens().access,
  refreshToken: getStoredTokens().refresh,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "登录失败");
      }
      const data = await resp.json();
      storeTokens(data.access_token, data.refresh_token);
      set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });
      await get().fetchMe();
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
    }
  },

  register: async (email, username, password, displayName) => {
    set({ isLoading: true, error: null });
    try {
      const resp = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, username, password, display_name: displayName }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "注册失败");
      }
      const data = await resp.json();
      storeTokens(data.access_token, data.refresh_token);
      set({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        isAuthenticated: true,
        isLoading: false,
      });
      await get().fetchMe();
    } catch (e: any) {
      set({ error: e.message, isLoading: false });
    }
  },

  logout: () => {
    clearStoredTokens();
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      error: null,
    });
  },

  fetchMe: async () => {
    const token = get().accessToken;
    if (!token) return;
    try {
      const resp = await fetch(`${API_BASE}/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (resp.ok) {
        const user = await resp.json();
        set({ user, isAuthenticated: true });
      } else if (resp.status === 401) {
        const refreshed = await get().refreshAccessToken();
        if (refreshed) await get().fetchMe();
        else get().logout();
      }
    } catch {
      // Network error — keep current state
    }
  },

  refreshAccessToken: async () => {
    const refresh = get().refreshToken;
    if (!refresh) return false;
    try {
      const resp = await fetch(`${API_BASE}/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (resp.ok) {
        const data = await resp.json();
        storeTokens(data.access_token, data.refresh_token);
        set({ accessToken: data.access_token, refreshToken: data.refresh_token });
        return true;
      }
    } catch {}
    return false;
  },

  clearError: () => set({ error: null }),
}));
