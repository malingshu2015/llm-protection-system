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
      isAuthenticated: false,
      user: null,
      token: null,
      serverUrl: null,

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
        // 从持久化存储中恢复认证状态
        const state = get();
        if (state.token && state.user) {
          set({ isAuthenticated: true });
        }
      },
    }),
    {
      name: 'auth-storage',
    }
  )
);
