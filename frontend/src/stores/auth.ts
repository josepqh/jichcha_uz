import { create } from "zustand";

import type { Me } from "@/lib/api";

export type AuthStatus = "loading" | "anon" | "authed";

interface AuthState {
  status: AuthStatus;
  /** Short-lived JWT, kept in memory only. The refresh token is an httpOnly cookie. */
  accessToken: string | null;
  user: Me | null;
  setSession: (accessToken: string, user: Me) => void;
  setUser: (user: Me) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  status: "loading",
  accessToken: null,
  user: null,
  setSession: (accessToken, user) => set({ status: "authed", accessToken, user }),
  setUser: (user) => set({ user }),
  clear: () => set({ status: "anon", accessToken: null, user: null }),
}));
