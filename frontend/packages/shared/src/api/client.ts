import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

declare const __API_BASE__: string | undefined;
const API_BASE = typeof __API_BASE__ !== 'undefined' ? __API_BASE__ : 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const stored = localStorage.getItem('songhut-auth');
  if (stored) {
    try {
      const { state } = JSON.parse(stored);
      const token = state?.accessToken;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch { /* ignore */ }
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !originalRequest?._retry) {
      const stored = localStorage.getItem('songhut-auth');
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          const refreshToken = parsed.state?.refreshToken;
          if (refreshToken) {
            originalRequest._retry = true;
            const resp = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: refreshToken });
            if (resp.data?.ok) {
              const { access_token, refresh_token } = resp.data.data;
              parsed.state.accessToken = access_token;
              parsed.state.refreshToken = refresh_token;
              localStorage.setItem('songhut-auth', JSON.stringify(parsed));
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
              return apiClient(originalRequest);
            }
          }
        } catch { /* ignore */ }
      }
      localStorage.removeItem('songhut-auth');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
