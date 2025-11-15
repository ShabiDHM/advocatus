// FILE: /home/user/advocatus-frontend/src/services/api.ts
// PHOENIX PROTOCOL - FINAL DEFINITIVE VERSION (CODE CLEANUP)
// CORRECTION: Removed the unused 'decodeJwtPayload' function and the now-uncalled
// 'ensureValidToken' method. This resolves the "'decodeJwtPayload' is declared
// but its value is never read" compiler warning and removes dead code.

import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type { LoginRequest, RegisterRequest, Case, CreateCaseRequest, Document, CreateDraftingJobRequest, DraftingJobStatus, ChangePasswordRequest, AdminUser, UpdateUserRequest, ApiKey, ApiKeyCreateRequest, CalendarEvent, CalendarEventCreateRequest, Finding, DraftingJobResult } from '../data/types';

interface LoginResponse { access_token: string; }
interface RegisterResponse { message: string; }
interface DocumentContentResponse { text: string; }
interface WebSocketInfo { url: string; token: string; }
interface FindingsResponse { findings: Finding[]; count: number; }

const API_BASE_URL = 'https://advocatus-prod-api.duckdns.org';
const API_V1_URL = `${API_BASE_URL}/api/v1`;

// The 'decodeJwtPayload' function has been removed as it is no longer used.

export class ApiService {
    private axiosInstance: AxiosInstance;
    private onUnauthorized: (() => void) | null = null;
    private refreshTokenPromise: Promise<LoginResponse> | null = null;

    constructor() {
        this.axiosInstance = axios.create({
            baseURL: API_V1_URL,
            withCredentials: true,
            timeout: 10000,
        });
        this.setupInterceptors();
    }

    public setLogoutHandler(handler: () => void) { this.onUnauthorized = handler; }

    // The 'ensureValidToken' method has been removed as it is no longer used.

    public async refreshAccessToken(): Promise<LoginResponse> {
        if (this.refreshTokenPromise) { 
            return this.refreshTokenPromise; 
        }
        
        this.refreshTokenPromise = this.axiosInstance.post<LoginResponse>('/auth/refresh', undefined, {
            withCredentials: true,
            timeout: 5000,
        })
        .then(response => {
            const { access_token } = response.data;
            localStorage.setItem('jwtToken', access_token);
            this.axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
            return response.data;
        })
        .catch(error => {
            console.error('Refresh token request failed:', error);
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
    
    public getWebSocketInfo(caseId: string): WebSocketInfo {
        const token = localStorage.getItem('jwtToken');
        if (!token) {
            if (this.onUnauthorized) this.onUnauthorized();
            throw new Error('Cannot establish WebSocket connection: No token found.');
        }
        return {
            url: `wss://advocatus-prod-api.duckdns.org/api/v1/comms/case/${caseId}`,
            token: token
        };
    }

    public getAxiosInstance(): AxiosInstance { return this.axiosInstance; }
    public async login(data: LoginRequest): Promise<LoginResponse> { return (await this.axiosInstance.post('/auth/login', data)).data; }
    
    public async register(data: RegisterRequest): Promise<RegisterResponse> {
        try {
            const response = await this.axiosInstance.post<RegisterResponse>('/auth/register', data);
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error) && error.response) {
                if (error.response.status === 409) {
                    const detail = error.response.data?.detail || 'A user with this email or username already exists.';
                    throw new Error(detail);
                }
            }
            throw new Error('An unexpected error occurred during registration.');
        }
    }

    public async changePassword(data: ChangePasswordRequest): Promise<void> { await this.axiosInstance.post('/users/change-password', data); }
    public async fetchUserProfile(): Promise<AdminUser> { return (await this.axiosInstance.get('/users/me')).data; }
    public async deleteAccount(): Promise<void> { await this.axiosInstance.delete('/users/me'); }
    public async getCases(): Promise<Case[]> { return (await this.axiosInstance.get('/cases/')).data; }
    public async createCase(data: CreateCaseRequest): Promise<Case> { return (await this.axiosInstance.post('/cases/', data)).data; }
    public async getCaseDetails(caseId: string): Promise<Case> { return (await this.axiosInstance.get(`/cases/${caseId}`)).data; }
    public async deleteCase(caseId: string): Promise<void> { await this.axiosInstance.delete(`/cases/${caseId}`); }
    public async getDocuments(caseId: string): Promise<Document[]> { return (await this.axiosInstance.get(`/cases/${caseId}/documents`)).data; }
    
    public async getPreviewDocument(caseId: string, documentId: string): Promise<Blob> {
        return (await this.axiosInstance.get(
            `/cases/${caseId}/documents/${documentId}/preview`,
            { responseType: 'blob', timeout: 30000 }
        )).data;
    }

    public async getOriginalDocument(caseId: string, documentId: string): Promise<Blob> {
        return (await this.axiosInstance.get(
            `/cases/${caseId}/documents/${documentId}/original`,
            { responseType: 'blob', timeout: 30000 }
        )).data;
    }

    public async getDocument(caseId: string, documentId: string): Promise<Document> { return (await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}`)).data; }
    public async getDocumentContent(caseId: string, documentId: string): Promise<DocumentContentResponse> { return (await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/content`)).data; }
    public async downloadDocumentReport(caseId: string, documentId: string): Promise<Blob> { return (await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/report`, { responseType: 'blob' })).data; }
    public async uploadDocument(caseId: string, file: File): Promise<Document> { 
        const formData = new FormData(); 
        formData.append('file', file); 
        return (await this.axiosInstance.post(`/cases/${caseId}/documents/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })).data;
    }
    public async deleteDocument(caseId: string, documentId: string): Promise<void> { await this.axiosInstance.delete(`/cases/${caseId}/documents/${documentId}`); }
    
    public async getFindings(caseId: string): Promise<Finding[]> {
        const response = await this.axiosInstance.get<FindingsResponse>(`/cases/${caseId}/findings`);
        return response.data.findings || [];
    }
    
    public async getCalendarEvents(): Promise<CalendarEvent[]> { 
        return (await this.axiosInstance.get('/calendar/events')).data; 
    }
    public async createCalendarEvent(data: CalendarEventCreateRequest): Promise<CalendarEvent> { 
        return (await this.axiosInstance.post('/calendar/events', data)).data; 
    }
    public async deleteCalendarEvent(eventId: string): Promise<void> { 
        await this.axiosInstance.delete(`/calendar/events/${eventId}`); 
    }

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