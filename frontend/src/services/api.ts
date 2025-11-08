// FILE: frontend/src/services/api.ts
// PHOENIX PROTOCOL MODIFICATION 5.0 (URL ALIGNMENT & DUPLICATION FIX):
// 1. CRITICAL FIX: The baseURL for the axios instance is now correctly constructed by
//    combining the VITE_API_BASE_URL (which should be the root domain) with the '/api/v1' prefix.
// 2. REFACTOR: All individual API calls have had the redundant '/api/v1' prefix removed,
//    as they now correctly inherit the full path from the axios instance's baseURL.
// 3. This is the definitive fix for the "404 Not Found" error caused by URL duplication.

import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type {
    LoginRequest, RegisterRequest, Case, CreateCaseRequest, Document,
    CreateDraftingJobRequest, DraftingJobStatus, ChangePasswordRequest, AdminUser,
    UpdateUserRequest, ApiKey, ApiKeyCreateRequest, CalendarEvent, CalendarEventCreateRequest,
    Finding
} from '../data/types';

interface LoginResponse { access_token: string; }
interface DocumentContentResponse { text: string; }

// VITE_API_BASE_URL should be the root domain, e.g., "https://advocatus-prod-api.duckdns.org"
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;
const API_V1_URL = `${API_BASE_URL}/api/v1`;

export class ApiService {
    private axiosInstance: AxiosInstance;
    private onUnauthorized: (() => void) | null = null;
    private refreshTokenPromise: Promise<LoginResponse> | null = null;

    constructor() {
        this.axiosInstance = axios.create({
            baseURL: API_V1_URL, // Use the correctly constructed full base URL
            headers: { 'Content-Type': 'application/json' },
            withCredentials: true
        });
        this.setupInterceptors();
    }

    public setLogoutHandler(handler: () => void) { this.onUnauthorized = handler; }

    public async refreshAccessToken(): Promise<LoginResponse> {
        if (this.refreshTokenPromise) {
            return this.refreshTokenPromise;
        }

        // Use the correctly constructed URL for the refresh endpoint
        this.refreshTokenPromise = axios.post<LoginResponse>(`${API_V1_URL}/auth/refresh`, {}, { withCredentials: true })
            .then(response => {
                const { access_token } = response.data;
                localStorage.setItem('jwtToken', access_token);
                this.axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
                return response.data;
            })
            .catch(error => {
                if (this.onUnauthorized) this.onUnauthorized();
                return Promise.reject(error);
            })
            .finally(() => {
                this.refreshTokenPromise = null;
            });

        return this.refreshTokenPromise;
    }

    private setupInterceptors() {
        this.axiosInstance.interceptors.request.use(
            (config: InternalAxiosRequestConfig) => {
                const token = localStorage.getItem('jwtToken');
                if (token && !config.headers.Authorization) { config.headers.Authorization = `Bearer ${token}`; }
                return config;
            },
            (error) => Promise.reject(error)
        );

        this.axiosInstance.interceptors.response.use(
            (response: AxiosResponse) => response,
            async (error) => {
                const originalRequest = error.config as InternalAxiosRequestConfig;
                const isRefreshEndpoint = originalRequest.url?.includes('/auth/refresh');

                if (error.response?.status === 401 && !isRefreshEndpoint) {
                    try {
                        const { access_token } = await this.refreshAccessToken();
                        originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
                        return this.axiosInstance(originalRequest);
                    } catch (refreshError) {
                        return Promise.reject(refreshError);
                    }
                }
                return Promise.reject(error);
            }
        );
    }

    public getWebSocketUrl(caseId: string): string {
        const token = localStorage.getItem('jwtToken');
        const url = new URL(API_BASE_URL); // Uses the root domain URL
        const domain = url.host;
        const protocol = url.protocol === 'https:' ? 'wss' : 'ws';
        return `${protocol}://${domain}/ws/case/${caseId}?token=${token}`;
    }

    // --- Public API Methods (Prefixes removed) ---
    public getAxiosInstance(): AxiosInstance { return this.axiosInstance; }
    public async login(data: LoginRequest): Promise<LoginResponse> { return (await this.axiosInstance.post('/auth/login', data)).data; }
    public async register(data: RegisterRequest): Promise<any> { return (await this.axiosInstance.post('/auth/register', data)).data; }
    public async changePassword(data: ChangePasswordRequest): Promise<void> { await this.axiosInstance.post('/users/change-password', data); }
    public async fetchUserProfile(): Promise<AdminUser> { return (await this.axiosInstance.get('/users/me')).data; }
    public async deleteAccount(): Promise<void> { await this.axiosInstance.delete('/users/me'); }
    public async getCases(): Promise<Case[]> { return (await this.axiosInstance.get('/cases/')).data; }
    public async createCase(data: CreateCaseRequest): Promise<Case> { return (await this.axiosInstance.post('/cases/', data)).data; }
    public async getCaseDetails(caseId: string): Promise<Case> { return (await this.axiosInstance.get(`/cases/${caseId}`)).data; }
    public async deleteCase(caseId: string): Promise<void> { await this.axiosInstance.delete(`/cases/${caseId}`); }
    public async getDocuments(caseId: string): Promise<Document[]> { return (await this.axiosInstance.get(`/cases/${caseId}/documents`)).data; }
    public async getDocument(caseId: string, documentId: string): Promise<Document> { return (await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}`)).data; }
    public async getDocumentContent(caseId: string, documentId: string): Promise<DocumentContentResponse> { return (await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/content`)).data; }
    public async downloadDocumentReport(caseId: string, documentId: string): Promise<Blob> {
        const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/report`, {
            responseType: 'blob',
        });
        return response.data;
    }
    public async uploadDocument(caseId: string, file: File): Promise<Document> { const formData = new FormData(); formData.append('file', file); return (await this.axiosInstance.post(`/cases/${caseId}/documents/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })).data; }
    public async deleteDocument(caseId: string, documentId: string): Promise<void> { await this.axiosInstance.delete(`/cases/${caseId}/documents/${documentId}`); }
    public async getFindings(caseId: string): Promise<Finding[]> { return (await this.axiosInstance.get(`/cases/${caseId}/findings`)).data; };
    public async getCalendarEvents(): Promise<CalendarEvent[]> { return (await this.axiosInstance.get('/calendar/events')).data; }
    public async createCalendarEvent(data: CalendarEventCreateRequest): Promise<CalendarEvent> { return (await this.axiosInstance.post('/calendar/events', data)).data; }
    public async deleteCalendarEvent(eventId: string): Promise<void> { await this.axiosInstance.delete(`/calendar/events/${eventId}`); }
    public async getAllUsers(): Promise<AdminUser[]> { return (await this.axiosInstance.get(`/admin/users`)).data; }
    public async updateUser(userId: string, data: UpdateUserRequest): Promise<AdminUser> { return (await this.axiosInstance.put(`/admin/users/${userId}`, data)).data; }
    public async deleteUser(userId: string): Promise<void> { await this.axiosInstance.delete(`/admin/users/${userId}`); }
    // NOTE: This service uses /api/v2, so we use the root API_BASE_URL to construct its path
    public async initiateDraftingJob(data: CreateDraftingJobRequest): Promise<DraftingJobStatus> { return (await this.axiosInstance.post(`${API_BASE_URL}/api/v2/drafting/jobs`, data)).data; }
    public async getDraftingJobStatus(jobId: string): Promise<DraftingJobStatus> { return (await this.axiosInstance.get(`${API_BASE_URL}/api/v2/drafting/jobs/${jobId}/status`)).data; }
    public async getDraftingJobResult(jobId: string): Promise<{ resultText: string }> { return (await this.axiosInstance.get(`${API_BASE_URL}/api/v2/drafting/jobs/${jobId}/result`)).data; }
    public async getUserApiKeys(): Promise<ApiKey[]> { return (await this.axiosInstance.get<ApiKey[]>('/keys')).data; }
    public async addApiKey(data: ApiKeyCreateRequest): Promise<ApiKey> { return (await this.axiosInstance.post<ApiKey>('/keys', data)).data; }
    public async deleteApiKey(keyId: string): Promise<void> { await this.axiosInstance.delete(`/keys/${keyId}`); }
}

export const apiService = new ApiService();