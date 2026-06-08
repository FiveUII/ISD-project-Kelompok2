/**
 * Zustand auth store persisted to localStorage.
 * Holds the JWT access_token and the current user profile.
 *
 * Context decision (D — JWT in localStorage, 24h TTL):
 *   - Access token stored in localStorage under key "lms-auth"
 *   - Persists across browser sessions/restarts
 *   - No refresh token in v1 (24h TTL)
 *
 * Usage:
 *   const { token, user, setAuth, logout } = useAuthStore();
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: "student" | "librarian";
  is_email_verified: boolean;
}

interface AuthState {
  token: string | null;
  user: AuthUser | null;
  setAuth: (token: string, user: AuthUser) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,

      setAuth: (token: string, user: AuthUser) => {
        set({ token, user });
      },

      logout: () => {
        set({ token: null, user: null });
      },
    }),
    {
      name: "lms-auth", // localStorage key
    }
  )
);
