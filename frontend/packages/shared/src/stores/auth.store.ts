import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, RegisterRequest, AuthTokens } from '../api/auth';
import { UserDto } from '../api/types';

interface AuthState {
  user: UserDto | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (phone: string, password: string) => Promise<boolean>;
  register: (data: RegisterRequest) => Promise<boolean>;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (phone, password) => {
        set({ isLoading: true, error: null });
        const result = await authApi.login({ phone, password });
        if (result.ok) {
          set({
            user: result.data.user,
            accessToken: result.data.access_token,
            refreshToken: result.data.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
          return true;
        }
        set({ isLoading: false, error: result.error.message });
        return false;
      },

      register: async (data) => {
        set({ isLoading: true, error: null });
        const result = await authApi.register(data);
        if (result.ok) {
          set({
            user: result.data.user,
            accessToken: result.data.access_token,
            refreshToken: result.data.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
          return true;
        }
        set({ isLoading: false, error: result.error.message });
        return false;
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
        authApi.logout().catch(() => {});
      },

      clearError: () => set({ error: null }),
    }),
    { name: 'songhut-auth' }
  )
);
