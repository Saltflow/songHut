import { useCallback } from 'react';
import { useAuthStore } from '../stores/auth.store';
import { RegisterRequest } from '../api/auth';

export function useAuth() {
  const user = useAuthStore(s => s.user);
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const isLoading = useAuthStore(s => s.isLoading);
  const error = useAuthStore(s => s.error);

  const login = useCallback(
    async (phone: string, password: string) => useAuthStore.getState().login(phone, password),
    [],
  );

  const register = useCallback(
    async (data: RegisterRequest) => useAuthStore.getState().register(data),
    [],
  );

  const logout = useCallback(
    () => useAuthStore.getState().logout(),
    [],
  );

  const clearError = useCallback(
    () => useAuthStore.getState().clearError(),
    [],
  );

  return { user, isAuthenticated, isLoading, error, login, register, logout, clearError };
}
