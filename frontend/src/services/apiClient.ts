// FILE: src/services/apiClient.ts
// PHOENIX PROTOCOL - CORE API CLIENT & TOKEN MANAGER

import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError, AxiosHeaders } from 'axios';

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';
let normalizedUrl = rawBaseUrl.replace(/\/$/, '');
if (typeof window !== 'undefined' && window.location.protocol === 'https:' && normalizedUrl.startsWith('http:')) {
  normalizedUrl = normalizedUrl.replace('http:', 'https:');
}

export const API_BASE_URL = normalizedUrl;
export const API_V1_URL = `${API_BASE_URL}/api/v1`;
export const API_V2_URL = `${API_BASE_URL}/api/v2`;

export class TokenManager {
  private accessToken: string | null = null;
  get(): string | null { return this.accessToken; }
  set(token: string | null): void { this.accessToken = token; }
}

export const tokenManager = new TokenManager();

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_V1_URL,
  withCredentials: true,
});

let isRefreshing = false;
let failedQueue: { resolve: (value: any) => void; reject: (reason?: any) => void }[] = [];
let onUnauthorizedHandler: (() => void) | null = null;

export function setGlobalLogoutHandler(handler: () => void) {
  onUnauthorizedHandler = handler;
}

function processQueue(error: Error | null) {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(tokenManager.get());
  });
  failedQueue = [];
}

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenManager.get();
    if (!config.headers) config.headers = new AxiosHeaders();
    if (token) {
      if (config.headers instanceof AxiosHeaders) config.headers.set('Authorization', `Bearer ${token}`);
      else (config.headers as any).Authorization = `Bearer ${token}`;
    }
    if (config.url && config.url.startsWith('blob:')) {
      config.baseURL = '';
    }
    return config;
  },
  (error: any) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response: any) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 402) {
      const detail = (error.response.data as any)?.detail || 'Abonimi juaj ka skaduar.';
      console.warn('[Gatekeeper 402]:', detail);
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/auth/refresh') {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          if (originalRequest.headers instanceof AxiosHeaders) {
            originalRequest.headers.set('Authorization', `Bearer ${token}`);
          } else {
            (originalRequest.headers as any).Authorization = `Bearer ${token}`;
          }
          return apiClient(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await apiClient.post<{ access_token: string }>('/auth/refresh');
        tokenManager.set(data.access_token);
        if (originalRequest.headers instanceof AxiosHeaders) {
          originalRequest.headers.set('Authorization', `Bearer ${data.access_token}`);
        } else {
          (originalRequest.headers as any).Authorization = `Bearer ${data.access_token}`;
        }
        processQueue(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        tokenManager.set(null);
        processQueue(refreshError as Error);
        if (onUnauthorizedHandler) onUnauthorizedHandler();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);