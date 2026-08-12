import { create } from 'zustand';

const TOKEN_KEY = 'surge_jwt_token';

interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  role: string | null;
  login: (username: string, role: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
  username: null,
  role: null,
  login: (username, role) => set({ isAuthenticated: true, username, role }),
  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ isAuthenticated: false, username: null, role: null });
  }
}));
