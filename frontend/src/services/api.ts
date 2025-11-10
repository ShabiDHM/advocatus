// FILE: frontend/src/services/api.ts
// DEFINITIVE VERSION (PROACTIVE AUTHENTICATION CURE):
// 1. ADDED: A new private helper function, 'decodeJwtPayload', to safely inspect the
//    token's expiration time without external libraries.
// 2. ADDED: A new public method, 'ensureValidToken'. This is the core of the cure. It
//    proactively checks if the current token is expired (or close to it) and, if so,
//    forces a token refresh. It returns a promise that resolves only when a valid
//    token is guaranteed to be in storage.
// 3. This transforms our authentication service from purely reactive (for HTTP) to also
//    proactive, providing the robust mechanism the WebSocket subsystem requires.

import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type { LoginRequest, RegisterRequest, Case, CreateCaseRequest, Document, CreateDraftingJobRequest, DraftingJobStatus, ChangePasswordRequest, AdminUser, UpdateUserRequest, ApiKey, ApiKeyCreateRequest, CalendarEvent, CalendarEventCreateRequest, Finding, DraftingJobResult } from '../data/types';

interface LoginResponse { access_token: string; }
interface DocumentContentResponse { text: string; }

const API_BASE_URL = 'https://advocatus-prod-api.duckdns.org';
const API_V1_URL = `${API_BASE_URL}/api/v1`;

// --- PHOENIX PROTOCOL CURE: Helper to decode JWT payload to check expiration ---
function decodeJwtPayload(token: string): { exp: number } | null {
  try {
    const base64Url = token.split('.')[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error("Failed to decode JWT payload:", error);
    return null;
  }
}

export class ApiService {
    private axiosInstance: AxiosInstance;
    private onUnauthorized: (() => void) | null = null;
    private refreshTokenPromise: Promise<LoginResponse> | null = null;

    constructor() {
        this.axiosInstance = axios.create({
            baseURL: API_V1_URL,
            headers: { 'Content-Type': 'application/json' },
            withCredentials: true,
            timeout: 10000,
        });
        this.setupInterceptors();
    }

    public setLogoutHandler(handler: () => void) { this.onUnauthorized = handler; }
    
    // --- PHOENIX PROTOCOL CURE: New proactive method to guarantee a fresh token ---
    public async ensureValidToken(): Promise<void> {
        const token = localStorage.getItem('jwtToken');
        if (!token) {
            if (this.onUnauthorized) this.onUnauthorized();
            throw new Error("Authentication token not found.");
        }

        const payload = decodeJwtPayload(token);
        // Check if token is expired or will expire in the next 20 seconds for safety.
        const isExpired = !payload || payload.exp * 1000 < Date.now() + 20000;

        if (isExpired) {
            console.log("Token is expired or expiring soon. Proactively refreshing...");
            try {
                await this.refreshAccessToken();
            } catch (error) {
                console.error("Failed to refresh token proactively:", error);
                throw error; // Propagate error to stop connection attempts
            }
        }
    }


    public async refreshAccessToken(): Promise<LoginResponse> {
        if (this.refreshTokenPromise) {
            return this.refreshTokenPromise;
        }

        this.refreshTokenPromise = axios.post<LoginResponse>(`${API_V1_URL}/auth/refresh`, {}, { withCredentials: true, timeout: 5000 })
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
            .finally(() => { this.refreshTokenPromise = null; });

        return this.refreshTokenPromise;
    }

    private setupInterceptors() {
        this.axiosInstance.interceptors.request.use(
            (config: InternalAxiosRequestConfig) => {
                const token = localStorage.getItem('jwtToken');
                if (token && !config.headers.Authorization) { 
                    config.headers.Authorization = `Bearer ${token}`; 
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        this.axiosInstance.interceptors.response.use(
            (response: AxiosResponse) => response,
            async (error) => {
                const originalRequest = error.config;
                if (error.response?.status === 401 && !originalRequest?.url?.includes('/auth/refresh') && originalRequest) {
                    try {
                        const { access_token } = await this.refreshAccessToken();
                        originalRequest.headers['Authorization'] = `Bearer ${access_token}`;
                        return this.axiosInstance(originalRequest);
                    } catch (refreshError) {
                        if (this.onUnauthorized) this.onUnauthorized();
                        return Promise.reject(refreshError);
                    }
                }
                return Promise.reject(error);
            }
        );
    }

    public getWebSocketUrl(caseId: string): string {
        const token = localStorage.getItem('jwtToken');
        if (!token) throw new Error('Authentication required for WebSocket connection');
        return `wss://advocatus-prod-api.duckdns.org/ws/case/${caseId}?token=${encodeURIComponent(token)}`;
    }

    // --- All other methods remain unchanged ---
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
    public async downloadDocumentReport(caseId: string, documentId: string): Promise<Blob> { return (await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/report`, { responseType: 'blob' })).data; }
    public async uploadDocument(caseId: string, file: File): Promise<Document> { 
        const formData = new FormData(); 
        formData.append('file', file); 
        return (await this.axiosInstance.post(`/cases/${caseId}/documents/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })).data; 
    }
    public async deleteDocument(caseId: string, documentId: string): Promise<void> { await this.axiosInstance.delete(`/cases/${caseId}/documents/${documentId}`); }
    public async getFindings(caseId: string): Promise<Finding[]> { return (await this.axiosInstance.get(`/cases/${caseId}/findings`)).data; }
    public async getCalendarEvents(): Promise<CalendarEvent[]> { return (await this.axiosInstance.get('/calendar/events')).data; }
    public async createCalendarEvent(data: CalendarEventCreateRequest): Promise<CalendarEvent> { return (await this.axiosInstance.post('/calendar/events', data)).data; }
    public async deleteCalendarEvent(eventId: string): Promise<void> { await this.axiosInstance.delete(`/calendar/events/${eventId}`); }
    public async getAllUsers(): Promise<AdminUser[]> { return (await this.axiosInstance.get(`/admin/users`)).data; }
    public async updateUser(userId: string, data: UpdateUserRequest): Promise<AdminUser> { return (await this.axiosInstance.put(`/admin/users/${userId}`, data)).data; }
    public async deleteUser(userId: string): Promise<void> { await this.axiosInstance.delete(`/admin/users/${userId}`); }
    public async initiateDraftingJob(data: CreateDraftingJobRequest): Promise<DraftingJobStatus> { return (await this.axiosInstance.post(`${API_BASE_URL}/api/v2/drafting/jobs`, data)).data; }
    public async getDraftingJobStatus(jobId: string): Promise<DraftingJobStatus> { return (await this.axiosInstance.get(`${API_BASE_URL}/api/v2/drafting/jobs/${jobId}/status`)).data; }
    public async getDraftingJobResult(jobId: string): Promise<DraftingJobResult> { return (await this.axiosInstance.get(`${API_BASE_URL}/api/v2/drafting/jobs/${jobId}/result`)).data; }
    public async getUserApiKeys(): Promise<ApiKey[]> { return (await this.axiosInstance.get<ApiKey[]>('/keys')).data; }
    public async addApiKey(data: ApiKeyCreateRequest): Promise<ApiKey> { return (await this.axiosInstance.post<ApiKey>('/keys', data)).data; }
    public async deleteApiKey(keyId: string): Promise<void> { await this.axiosInstance.delete(`/keys/${keyId}`); }
}

export const apiService = new ApiService();