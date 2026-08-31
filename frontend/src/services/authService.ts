// FILE: src/services/authService.ts
// PHOENIX PROTOCOL - AUTHENTICATION & USER PROFILE SERVICE MODULE

import { apiClient, tokenManager } from './apiClient';
import type {
  LoginRequest,
  RegisterRequest,
  User,
  UpdateUserRequest,
  ChangePasswordRequest
} from '../data/types';

interface LoginResponse {
  access_token: string;
}

export class AuthService {
  public setToken(token: string | null): void {
    tokenManager.set(token);
  }

  public getToken(): string | null {
    return tokenManager.get();
  }

  public async refreshToken(): Promise<boolean> {
    try {
      const response = await apiClient.post<LoginResponse>('/auth/refresh');
      if (response.data.access_token) {
        tokenManager.set(response.data.access_token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  public async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', data);
    if (response.data.access_token) {
      tokenManager.set(response.data.access_token);
    }
    return response.data;
  }

  public logout(): void {
    tokenManager.set(null);
  }

  public async register(data: RegisterRequest): Promise<void> {
    await apiClient.post('/auth/register', data);
  }

  public async fetchUserProfile(): Promise<User> {
    const response = await apiClient.get<User>('/users/me');
    return response.data;
  }

  public async updateUser(userId: string, data: UpdateUserRequest): Promise<User> {
    const response = await apiClient.put<User>(`/admin/users/${userId}`, data);
    return response.data;
  }

  public async changePassword(data: ChangePasswordRequest): Promise<void> {
    await apiClient.post('/auth/change-password', data);
  }

  public async deleteAccount(): Promise<void> {
    await apiClient.delete('/users/me');
  }

  public async forgotPassword(email: string): Promise<{ message: string }> {
    const response = await apiClient.post('/auth/forgot-password', { email });
    return response.data;
  }

  public async resetPassword(token: string, password: string): Promise<{ message: string }> {
    const response = await apiClient.post('/auth/reset-password', { token, password });
    return response.data;
  }
}

export const authService = new AuthService();