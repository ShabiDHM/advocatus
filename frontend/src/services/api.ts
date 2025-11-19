// FILE: frontend/src/services/api.ts
// PHOENIX PROTOCOL - API RESTORATION
// 1. Added missing 'getFindings' method (Critical Fix).
// 2. Configured 'getPreviewDocument' to use /preview endpoint.
// 3. Includes SSE helpers (getToken).

import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from 'axios';
import type {
    LoginRequest,
    RegisterRequest,
    Case,
    CreateCaseRequest,
    Document,
    User,
    UpdateUserRequest,
    DeletedDocumentResponse,
    CalendarEvent,
    CalendarEventCreateRequest,
    CreateDraftingJobRequest,
    DraftingJobStatus,
    DraftingJobResult,
    ApiKey,
    ApiKeyCreateRequest,
    ChangePasswordRequest,
    Finding // Imported Finding
} from '../data/types';

interface LoginResponse {
    access_token: string;
}

interface DocumentContentResponse {
    text: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';
const API_V1_URL = `${API_BASE_URL}/api/v1`;

class ApiService {
    public axiosInstance: AxiosInstance;
    public onUnauthorized: (() => void) | null = null;
    private refreshTokenPromise: Promise<LoginResponse> | null = null;

    constructor() {
        this.axiosInstance = axios.create({
            baseURL: API_V1_URL,
            withCredentials: true,
            headers: { 'Content-Type': 'application/json' },
        });
        this.setupInterceptors();
    }

    private normalizeDocument(doc: any): Document {
        if (doc && doc._id && !doc.id) {
            doc.id = doc._id;
        }
        return doc as Document;
    }

    private setupInterceptors() {
        this.axiosInstance.interceptors.request.use(
            (config: InternalAxiosRequestConfig) => {
                const token = localStorage.getItem('jwtToken');
                if (token) config.headers.Authorization = `Bearer ${token}`;
                return config;
            },
            (error) => Promise.reject(error)
        );

        this.axiosInstance.interceptors.response.use(
            (response) => response,
            async (error: AxiosError) => {
                const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
                if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
                    originalRequest._retry = true;
                    try {
                        if (!this.refreshTokenPromise) {
                            this.refreshTokenPromise = this.refreshAccessToken();
                        }
                        await this.refreshTokenPromise;
                        this.refreshTokenPromise = null;
                        const newToken = localStorage.getItem('jwtToken');
                        if (newToken) originalRequest.headers.Authorization = `Bearer ${newToken}`;
                        return this.axiosInstance(originalRequest);
                    } catch (refreshError) {
                        this.refreshTokenPromise = null;
                        localStorage.removeItem('jwtToken');
                        if (this.onUnauthorized) this.onUnauthorized();
                        return Promise.reject(refreshError);
                    }
                }
                return Promise.reject(error);
            }
        );
    }

    // --- SSE Helpers ---
    public getToken(): string | null {
        return localStorage.getItem('jwtToken');
    }

    public async post<T>(url: string, data: any): Promise<T> {
        const response = await this.axiosInstance.post<T>(url, data);
        return response.data;
    }

    public async refreshAccessToken(): Promise<LoginResponse> {
        const response = await this.axiosInstance.post<LoginResponse>('/auth/refresh');
        if (response.data.access_token) localStorage.setItem('jwtToken', response.data.access_token);
        return response.data;
    }

    // --- Auth & User ---
    public async login(data: LoginRequest): Promise<LoginResponse> {
        const response = await this.axiosInstance.post<LoginResponse>('/auth/login', data);
        return response.data;
    }

    public async register(data: RegisterRequest): Promise<void> {
        await this.axiosInstance.post('/auth/register', data);
    }

    public async fetchUserProfile(): Promise<User> {
        const response = await this.axiosInstance.get<User>('/users/me');
        return response.data;
    }

    public async changePassword(data: ChangePasswordRequest): Promise<void> {
        await this.axiosInstance.post('/auth/change-password', data);
    }

    public async deleteAccount(): Promise<void> {
        await this.axiosInstance.delete('/users/me');
    }

    // --- Cases ---
    public async getCases(): Promise<Case[]> {
        const response = await this.axiosInstance.get<Case[]>('/cases');
        return response.data;
    }

    public async createCase(data: CreateCaseRequest): Promise<Case> {
        const response = await this.axiosInstance.post<Case>('/cases', data);
        return response.data;
    }

    public async getCaseDetails(caseId: string): Promise<Case> {
        const response = await this.axiosInstance.get<Case>(`/cases/${caseId}`);
        return response.data;
    }

    public async deleteCase(caseId: string): Promise<void> {
        await this.axiosInstance.delete(`/cases/${caseId}`);
    }

    // --- Findings (FIXED: Added missing method) ---
    public async getFindings(caseId: string): Promise<Finding[]> {
        const response = await this.axiosInstance.get<{ findings: Finding[] }>(`/cases/${caseId}/findings`);
        return response.data.findings || [];
    }

    // --- Documents ---
    public async getDocuments(caseId: string): Promise<Document[]> {
        const response = await this.axiosInstance.get<Document[]>(`/cases/${caseId}/documents`);
        return response.data.map(d => this.normalizeDocument(d));
    }

    public async uploadDocument(caseId: string, file: File): Promise<Document> {
        const formData = new FormData();
        formData.append('file', file);
        const response = await this.axiosInstance.post<Document>(`/cases/${caseId}/documents/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return this.normalizeDocument(response.data);
    }

    public async getDocument(caseId: string, documentId: string): Promise<Document> {
        const response = await this.axiosInstance.get<Document>(`/cases/${caseId}/documents/${documentId}`);
        return this.normalizeDocument(response.data);
    }

    public async deleteDocument(caseId: string, documentId: string): Promise<DeletedDocumentResponse> {
        const response = await this.axiosInstance.delete<DeletedDocumentResponse>(`/cases/${caseId}/documents/${documentId}`);
        return response.data;
    }

    public async getDocumentContent(caseId: string, documentId: string): Promise<DocumentContentResponse> {
        const response = await this.axiosInstance.get<DocumentContentResponse>(`/cases/${caseId}/documents/${documentId}/content`);
        return response.data;
    }

    public async getOriginalDocument(caseId: string, documentId: string): Promise<Blob> {
        const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/download`, { responseType: 'blob' });
        return response.data;
    }

    // FIXED: Points to /preview for generated PDFs
    public async getPreviewDocument(caseId: string, documentId: string): Promise<Blob> {
        const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/preview`, { responseType: 'blob' });
        return response.data;
    }

    public async downloadDocumentReport(caseId: string, documentId: string): Promise<Blob> {
        const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/report`, { responseType: 'blob' });
        return response.data;
    }

    // --- WebSocket Legacy (Empty Stub) ---
    public async getWebSocketUrl(_caseId: string): Promise<string> {
        return ""; 
    }

    // --- Admin Functions ---
    public async getAllUsers(): Promise<User[]> {
        const response = await this.axiosInstance.get<User[]>('/admin/users');
        return response.data;
    }

    public async updateUser(userId: string, data: UpdateUserRequest): Promise<User> {
        const response = await this.axiosInstance.put<User>(`/admin/users/${userId}`, data);
        return response.data;
    }

    public async deleteUser(userId: string): Promise<void> {
        await this.axiosInstance.delete(`/admin/users/${userId}`);
    }

    // --- API Keys ---
    public async getUserApiKeys(): Promise<ApiKey[]> {
        const response = await this.axiosInstance.get<ApiKey[]>('/api-keys');
        return response.data;
    }

    public async addApiKey(data: ApiKeyCreateRequest): Promise<ApiKey> {
        const response = await this.axiosInstance.post<ApiKey>('/api-keys', data);
        return response.data;
    }

    public async deleteApiKey(keyId: string): Promise<void> {
        await this.axiosInstance.delete(`/api-keys/${keyId}`);
    }

    // --- Calendar ---
    public async getCalendarEvents(): Promise<CalendarEvent[]> {
        const response = await this.axiosInstance.get<CalendarEvent[]>('/calendar/events');
        return response.data;
    }

    public async createCalendarEvent(data: CalendarEventCreateRequest): Promise<CalendarEvent> {
        const response = await this.axiosInstance.post<CalendarEvent>('/calendar/events', data);
        return response.data;
    }

    public async deleteCalendarEvent(eventId: string): Promise<void> {
        await this.axiosInstance.delete(`/calendar/events/${eventId}`);
    }

    // --- Drafting V2 ---
    public async initiateDraftingJob(data: CreateDraftingJobRequest): Promise<DraftingJobStatus> {
        const response = await this.axiosInstance.post<DraftingJobStatus>(`${API_BASE_URL}/api/v2/drafting/jobs`, data);
        return response.data;
    }

    public async getDraftingJobStatus(jobId: string): Promise<DraftingJobStatus> {
        const response = await this.axiosInstance.get<DraftingJobStatus>(`${API_BASE_URL}/api/v2/drafting/jobs/${jobId}/status`);
        return response.data;
    }

    public async getDraftingJobResult(jobId: string): Promise<DraftingJobResult> {
        const response = await this.axiosInstance.get<DraftingJobResult>(`${API_BASE_URL}/api/v2/drafting/jobs/${jobId}/result`);
        return response.data;
    }
}

export const apiService = new ApiService();