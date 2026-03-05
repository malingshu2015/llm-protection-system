import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  username: string;
  email?: string;
  avatar?: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  serverUrl: string | null;

  // Actions
  login: (token: string, user: User, serverUrl: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  initAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: true, // DEV_MODE: mock login
      user: { id: "dev_1", username: "admin" },
      token: "mock-token-for-dev",
      serverUrl: "http://localhost:8082",

      login: (token: string, user: User, serverUrl: string) => {
        set({
          isAuthenticated: true,
          token,
          user,
          serverUrl,
        });
      },

      logout: () => {
        set({
          isAuthenticated: false,
          token: null,
          user: null,
        });
      },

      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user;
        if (currentUser) {
          set({
            user: { ...currentUser, ...userData },
          });
        }
      },

      initAuth: () => {
        // DEV_MODE: Force login bypass regardless of local storage
        set({
          isAuthenticated: true,
          user: { id: "dev_1", username: "admin" },
          token: "mock-token-for-dev",
          serverUrl: "http://localhost:8082",
        });
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
