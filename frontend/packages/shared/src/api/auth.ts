import { apiClient } from './client';
import { UserDto, ApiResult } from './types';

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterRequest {
  phone: string;
  password: string;
  nickname?: string;
}

export interface LoginRequest {
  phone: string;
  password: string;
}

export const authApi = {
  register: (data: RegisterRequest): Promise<ApiResult<{ user: UserDto } & AuthTokens>> =>
    apiClient.post('/auth/register', data).then(r => r.data),

  login: (data: LoginRequest): Promise<ApiResult<{ user: UserDto } & AuthTokens>> =>
    apiClient.post('/auth/login', data).then(r => r.data),

  refresh: (refreshToken: string): Promise<ApiResult<AuthTokens>> =>
    apiClient.post('/auth/refresh', { refresh_token: refreshToken }).then(r => r.data),

  logout: (): Promise<ApiResult<null>> =>
    apiClient.post('/auth/logout').then(r => r.data),

  getMe: (): Promise<ApiResult<UserDto>> =>
    apiClient.get('/users/me').then(r => r.data),
};
