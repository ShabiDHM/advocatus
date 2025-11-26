// FILE: src/services/api.ts
// PHOENIX PROTOCOL - API SERVICE
// Includes: Auth, Cases, Documents, Business, Support, Calendar.

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
    ChangePasswordRequest,
    Finding,
    CaseAnalysisResult,
    BusinessProfile,
    BusinessProfileUpdate
} from '../data/types';

interface LoginResponse {
    access_token: string;
}

interface DocumentContentResponse {
    text: string;
}

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';
let normalizedUrl = rawBaseUrl.replace(/\/$/, '');

if (typeof window !== 'undefined' && window.location.protocol === 'https:' && normalizedUrl.startsWith('http:')) {
    normalizedUrl = normalizedUrl.replace('http:', 'https:');
}

export const API_BASE_URL = normalizedUrl;
export const API_V1_URL = `${API_BASE_URL}/api/v1`;

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

    public setLogoutHandler(handler: () => void) {
        this.onUnauthorized = handler;
    }

    private setupInterceptors() {
        this.axiosInstance.interceptors.request.use(
            (config) => {
                if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
                    if (config.baseURL?.startsWith('http:')) config.baseURL = config.baseURL.replace('http:', 'https:');
                    if (config.url?.startsWith('http:')) config.url = config.url.replace('http:', 'https:');
                }
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
                const isRefreshRequest = originalRequest?.url?.includes('/auth/refresh');

                if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !isRefreshRequest) {
                    originalRequest._retry = true;
                    try {
                        if (!this.refreshTokenPromise) this.refreshTokenPromise = this.refreshAccessToken();
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

    // --- BUSINESS MODULE ---
    public async getBusinessProfile(): Promise<BusinessProfile> {
        const response = await this.axiosInstance.get<BusinessProfile>('/business/profile');
        return response.data;
    }

    public async updateBusinessProfile(data: BusinessProfileUpdate): Promise<BusinessProfile> {
        const response = await this.axiosInstance.put<BusinessProfile>('/business/profile', data);
        return response.data;
    }

    public async uploadBusinessLogo(file: File): Promise<BusinessProfile> {
        const formData = new FormData();
        formData.append('file', file);
        const response = await this.axiosInstance.post<BusinessProfile>('/business/logo', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    }

    // --- SUPPORT ---
    public async sendContactForm(data: { firstName: string; lastName: string; email: string; phone: string; message: string }): Promise<void> {
        await this.axiosInstance.post('/support/contact', {
            first_name: data.firstName,
            last_name: data.lastName,
            email: data.email,
            phone: data.phone,
            message: data.message
        });
    }

    // --- CASES ---
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

    public async getFindings(caseId: string): Promise<Finding[]> {
        const response = await this.axiosInstance.get<{ findings: Finding[] }>(`/cases/${caseId}/findings`);
        return response.data.findings || [];
    }

    public async analyzeCase(caseId: string): Promise<CaseAnalysisResult> {
        const response = await this.axiosInstance.post<CaseAnalysisResult>(`/cases/${caseId}/analyze`);
        return response.data;
    }
    
    // --- AUTH ---
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

    // --- DOCUMENTS ---
    public async getDocuments(caseId: string): Promise<Document[]> {
        const response = await this.axiosInstance.get<Document[]>(`/cases/${caseId}/documents`);
        return response.data;
    }

    public async uploadDocument(caseId: string, file: File): Promise<Document> {
        const formData = new FormData();
        formData.append('file', file);
        const response = await this.axiosInstance.post<Document>(`/cases/${caseId}/documents/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data;
    }
    
    public async getDocument(caseId: string, documentId: string): Promise<Document> {
        const response = await this.axiosInstance.get<Document>(`/cases/${caseId}/documents/${documentId}`);
        return response.data;
    }

    public async deleteDocument(caseId: string, documentId: string): Promise<DeletedDocumentResponse> {
        const response = await this.axiosInstance.delete<DeletedDocumentResponse>(`/cases/${caseId}/documents/${documentId}`);
        return response.data;
    }

    public async deepScanDocument(caseId: string, documentId: string): Promise<void> {
        await this.axiosInstance.post(`/cases/${caseId}/documents/${documentId}/deep-scan`);
    }

    public async getDocumentContent(caseId: string, documentId: string): Promise<DocumentContentResponse> {
        const response = await this.axiosInstance.get<DocumentContentResponse>(`/cases/${caseId}/documents/${documentId}/content`);
        return response.data;
    }

    public async getOriginalDocument(caseId: string, documentId: string): Promise<Blob> {
        const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/original`, { responseType: 'blob' });
        return response.data;
    }

    public async getPreviewDocument(caseId: string, documentId: string): Promise<Blob> {
        const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/preview`, { responseType: 'blob' });
        return response.data;
    }
    
    public async downloadDocumentReport(caseId: string, documentId: string): Promise<Blob> {
        const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/report`, { responseType: 'blob' });
        return response.data;
    }

    public async getWebSocketUrl(_caseId: string): Promise<string> {
        return "";
    }

    // --- CHAT ---
    public async clearChatHistory(caseId: string): Promise<void> {
        await this.axiosInstance.delete(`/chat/case/${caseId}/history`);
    }

    // --- ADMIN ---
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

    // --- CALENDAR ---
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

    // --- DRAFTING ---
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