import { create } from 'zustand';
import { setUnauthorizedHandler } from '../api/client';

const TOKEN_KEY = 'surge_jwt_token';

interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  role: string | null;
  /**
   * True when the session ended on its own rather than because the operator signed out.
   *
   * <p>Both used to look identical: the app simply became the sign-in screen. Someone mid-way
   * through configuring a run had no way to tell whether they had been logged out, whether the
   * server was down, or whether they had misclicked — so the sign-in screen has to say which.
   */
  sessionExpired: boolean;
  login: (username: string, role: string) => void;
  logout: () => void;
  expireSession: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
  username: null,
  role: null,
  sessionExpired: false,
  login: (username, role) => set({ isAuthenticated: true, username, role, sessionExpired: false }),
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ isAuthenticated: false, username: null, role: null, sessionExpired: false });
  },
  expireSession: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ isAuthenticated: false, username: null, role: null, sessionExpired: true });
  }
}));

// A rejected token means the session is over, whatever localStorage still claims. Dropping straight
// back to the sign-in screen beats leaving the operator in an app where every request quietly fails
// — but it is recorded as an expiry, so the screen can explain itself rather than just appearing.
setUnauthorizedHandler(() => useAuthStore.getState().expireSession());
