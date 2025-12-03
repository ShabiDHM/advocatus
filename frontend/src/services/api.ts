// FILE: src/services/api.ts
// PHOENIX PROTOCOL - API CLIENT V2 (FOLDERS)
// 1. UPDATE: 'getArchiveItems' now accepts 'parentId' for navigation.
// 2. UPDATE: 'uploadArchiveItem' now accepts 'parentId' for uploading to folders.
// 3. FEATURE: Added 'createArchiveFolder' method.

import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from 'axios';
import type {
    LoginRequest, RegisterRequest, Case, CreateCaseRequest, Document, User, UpdateUserRequest,
    DeletedDocumentResponse, CalendarEvent, CalendarEventCreateRequest, CreateDraftingJobRequest,
    DraftingJobStatus, DraftingJobResult, ChangePasswordRequest, Finding, CaseAnalysisResult,
    BusinessProfile, BusinessProfileUpdate, Invoice, InvoiceCreateRequest,
    GraphData, ArchiveItemOut
} from '../data/types';

interface LoginResponse { access_token: string; }
interface DocumentContentResponse { text: string; }

// --- URL SETUP ---
const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';
let normalizedUrl = rawBaseUrl.replace(/\/$/, '');
if (typeof window !== 'undefined' && window.location.protocol === 'https:' && normalizedUrl.startsWith('http:')) {
    normalizedUrl = normalizedUrl.replace('http:', 'https:');
}

export const API_BASE_URL = normalizedUrl;
export const API_V1_URL = `${API_BASE_URL}/api/v1`;
export const API_V2_URL = `${API_BASE_URL}/api/v2`;

// --- PHOENIX FIX: Singleton token manager for in-memory access token ---
class TokenManager {
    private accessToken: string | null = null;
    
    get(): string | null {
        return this.accessToken;
    }

    set(token: string | null): void {
        this.accessToken = token;
    }
}
const tokenManager = new TokenManager();


class ApiService {
    public axiosInstance: AxiosInstance;
    public onUnauthorized: (() => void) | null = null;
    private isRefreshing = false;
    private failedQueue: { resolve: (value: any) => void; reject: (reason?: any) => void; }[] = [];

    constructor() {
        this.axiosInstance = axios.create({ 
            baseURL: API_V1_URL, 
            withCredentials: true, // Crucial for sending cookies
            headers: { 'Content-Type': 'application/json' } 
        });
        this.setupInterceptors();
    }

    public setLogoutHandler(handler: () => void) { this.onUnauthorized = handler; }

    private processQueue(error: Error | null) {
        this.failedQueue.forEach(prom => {
            if (error) {
                prom.reject(error);
            } else {
                prom.resolve(tokenManager.get());
            }
        });
        this.failedQueue = [];
    }

    private setupInterceptors() {
        this.axiosInstance.interceptors.request.use(
            (config) => {
                const token = tokenManager.get();
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        this.axiosInstance.interceptors.response.use(
            (response) => response,
            async (error: AxiosError) => {
                const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

                if (error.response?.status === 401 && !originalRequest._retry) {
                    if (this.isRefreshing) {
                        return new Promise((resolve, reject) => {
                            this.failedQueue.push({ resolve, reject });
                        }).then(() => {
                            originalRequest.headers.Authorization = `Bearer ${tokenManager.get()}`;
                            return this.axiosInstance(originalRequest);
                        });
                    }

                    originalRequest._retry = true;
                    this.isRefreshing = true;

                    try {
                        const { data } = await this.axiosInstance.post<LoginResponse>('/auth/refresh');
                        tokenManager.set(data.access_token);
                        
                        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
                        this.processQueue(null);
                        
                        return this.axiosInstance(originalRequest);
                    } catch (refreshError) {
                        tokenManager.set(null);
                        this.processQueue(refreshError as Error);
                        if (this.onUnauthorized) {
                            this.onUnauthorized();
                        }
                        return Promise.reject(refreshError);
                    } finally {
                        this.isRefreshing = false;
                    }
                }
                return Promise.reject(error);
            }
        );
    }
    
    public getToken(): string | null { return tokenManager.get(); }
    public async login(data: LoginRequest): Promise<LoginResponse> {
        const response = await this.axiosInstance.post<LoginResponse>('/auth/login', data);
        if (response.data.access_token) {
            tokenManager.set(response.data.access_token);
        }
        return response.data;
    }
    
    // Call this from your AuthContext/logout function
    public logout() {
        tokenManager.set(null);
    }

    public async fetchImageBlob(url: string): Promise<Blob> { const response = await this.axiosInstance.get(url, { responseType: 'blob' }); return response.data; }

    // --- CHAT (AI) ---
    public async sendChatMessage(caseId: string, message: string, documentId?: string, jurisdiction?: string): Promise<string> { const response = await this.axiosInstance.post<{ response: string }>(`/chat/case/${caseId}`, { message, document_id: documentId || null, jurisdiction: jurisdiction || 'ks' }); return response.data.response; }
    public async clearChatHistory(caseId: string): Promise<void> { await this.axiosInstance.delete(`/chat/case/${caseId}/history`); }

    // --- Business Profile ---
    public async getBusinessProfile(): Promise<BusinessProfile> { const response = await this.axiosInstance.get<BusinessProfile>('/business/profile'); return response.data; }
    public async updateBusinessProfile(data: BusinessProfileUpdate): Promise<BusinessProfile> { const response = await this.axiosInstance.put<BusinessProfile>('/business/profile', data); return response.data; }
    public async uploadBusinessLogo(file: File): Promise<BusinessProfile> { const formData = new FormData(); formData.append('file', file); const response = await this.axiosInstance.put<BusinessProfile>('/business/logo', formData, { headers: { 'Content-Type': 'multipart/form-data' } }); return response.data; }

    // --- Finance ---
    public async getInvoices(): Promise<Invoice[]> { const response = await this.axiosInstance.get<Invoice[]>('/finance/invoices'); return response.data; }
    public async createInvoice(data: InvoiceCreateRequest): Promise<Invoice> { const response = await this.axiosInstance.post<Invoice>('/finance/invoices', data); return response.data; }
    public async updateInvoiceStatus(invoiceId: string, status: string): Promise<Invoice> { const response = await this.axiosInstance.put<Invoice>(`/finance/invoices/${invoiceId}/status`, { status }); return response.data; }
    public async deleteInvoice(invoiceId: string): Promise<void> { await this.axiosInstance.delete(`/finance/invoices/${invoiceId}`); }
    public async downloadInvoicePdf(invoiceId: string, lang: string = 'sq'): Promise<void> { const response = await this.axiosInstance.get(`/finance/invoices/${invoiceId}/pdf`, { params: { lang }, responseType: 'blob' }); const url = window.URL.createObjectURL(new Blob([response.data])); const link = document.createElement('a'); link.href = url; link.setAttribute('download', `Invoice_${invoiceId}.pdf`); document.body.appendChild(link); link.click(); link.parentNode?.removeChild(link); }
    public async getInvoicePdfBlob(invoiceId: string, lang: string = 'sq'): Promise<Blob> { const response = await this.axiosInstance.get(`/finance/invoices/${invoiceId}/pdf`, { params: { lang }, responseType: 'blob' }); return response.data; }
    public async archiveInvoice(invoiceId: string, caseId?: string): Promise<ArchiveItemOut> { const params = caseId ? { case_id: caseId } : {}; const response = await this.axiosInstance.post<ArchiveItemOut>(`/finance/invoices/${invoiceId}/archive`, null, { params }); return response.data; }

    // --- ARCHIVE (File Storage) ---
    // PHOENIX: Updated to support parentId for folders
    public async getArchiveItems(category?: string, caseId?: string, parentId?: string): Promise<ArchiveItemOut[]> { 
        const params: any = {}; 
        if (category) params.category = category; 
        if (caseId) params.case_id = caseId;
        if (parentId) params.parent_id = parentId; // Pass folder ID
        
        const response = await this.axiosInstance.get<ArchiveItemOut[]>('/archive/items', { params }); 
        return response.data; 
    }

    public async createArchiveFolder(title: string, parentId?: string, caseId?: string): Promise<ArchiveItemOut> {
        const formData = new FormData();
        formData.append('title', title);
        if (parentId) formData.append('parent_id', parentId);
        if (caseId) formData.append('case_id', caseId);
        
        const response = await this.axiosInstance.post<ArchiveItemOut>('/archive/folder', formData);
        return response.data;
    }

    public async uploadArchiveItem(file: File, title: string, category: string, caseId?: string, parentId?: string): Promise<ArchiveItemOut> { 
        const formData = new FormData(); 
        formData.append('file', file); 
        formData.append('title', title); 
        formData.append('category', category); 
        if (caseId) formData.append('case_id', caseId); 
        if (parentId) formData.append('parent_id', parentId); // Pass folder ID
        
        const response = await this.axiosInstance.post<ArchiveItemOut>('/archive/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }); 
        return response.data; 
    }
    
    public async deleteArchiveItem(itemId: string): Promise<void> { await this.axiosInstance.delete(`/archive/items/${itemId}`); }
    public async downloadArchiveItem(itemId: string, title: string): Promise<void> { const response = await this.axiosInstance.get(`/archive/items/${itemId}/download`, { responseType: 'blob' }); const url = window.URL.createObjectURL(new Blob([response.data])); const link = document.createElement('a'); link.href = url; link.setAttribute('download', title); document.body.appendChild(link); link.click(); link.parentNode?.removeChild(link); }
    public async getArchiveFileBlob(itemId: string): Promise<Blob> { const response = await this.axiosInstance.get(`/archive/items/${itemId}/download`, { params: { preview: true }, responseType: 'blob' }); return response.data; }

    // --- DOCUMENTS (Case Files) ---
    public async getDocuments(caseId: string): Promise<Document[]> { const response = await this.axiosInstance.get<Document[]>(`/cases/${caseId}/documents`); return response.data; }
    public async uploadDocument(caseId: string, file: File): Promise<Document> { const formData = new FormData(); formData.append('file', file); const response = await this.axiosInstance.post<Document>(`/cases/${caseId}/documents/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }); return response.data; }
    public async getDocument(caseId: string, documentId: string): Promise<Document> { const response = await this.axiosInstance.get<Document>(`/cases/${caseId}/documents/${documentId}`); return response.data; }
    public async deleteDocument(caseId: string, documentId: string): Promise<DeletedDocumentResponse> { const response = await this.axiosInstance.delete<DeletedDocumentResponse>(`/cases/${caseId}/documents/${documentId}`); return response.data; }
    public async deepScanDocument(caseId: string, documentId: string): Promise<void> { await this.axiosInstance.post(`/cases/${caseId}/documents/${documentId}/deep-scan`); }
    public async getDocumentContent(caseId: string, documentId: string): Promise<DocumentContentResponse> { const response = await this.axiosInstance.get<DocumentContentResponse>(`/cases/${caseId}/documents/${documentId}/content`); return response.data; }
    public async getOriginalDocument(caseId: string, documentId: string): Promise<Blob> { const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/original`, { responseType: 'blob' }); return response.data; }
    public async getPreviewDocument(caseId: string, documentId: string): Promise<Blob> { const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/preview`, { responseType: 'blob' }); return response.data; }
    public async downloadDocumentReport(caseId: string, documentId: string): Promise<Blob> { const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/report`, { responseType: 'blob' }); return response.data; }
    public async archiveCaseDocument(caseId: string, documentId: string): Promise<ArchiveItemOut> { const response = await this.axiosInstance.post<ArchiveItemOut>(`/cases/${caseId}/documents/${documentId}/archive`); return response.data; }

    // --- Graph ---
    public async getCaseGraph(caseId: string): Promise<GraphData> { const response = await this.axiosInstance.get<GraphData>(`/graph/graph/${caseId}`); return response.data; }

    // --- Calendar & Alerts ---
    public async getCalendarEvents(): Promise<CalendarEvent[]> { const response = await this.axiosInstance.get<CalendarEvent[]>('/calendar/events'); return response.data; }
    public async createCalendarEvent(data: CalendarEventCreateRequest): Promise<CalendarEvent> { const response = await this.axiosInstance.post<CalendarEvent>('/calendar/events', data); return response.data; }
    public async deleteCalendarEvent(eventId: string): Promise<void> { await this.axiosInstance.delete(`/calendar/events/${eventId}`); }
    public async getAlertsCount(): Promise<{ count: number }> { const response = await this.axiosInstance.get<{ count: number }>('/calendar/alerts'); return response.data; }

    // --- Standard Services ---
    public async sendContactForm(data: { firstName: string; lastName: string; email: string; phone: string; message: string }): Promise<void> { await this.axiosInstance.post('/support/contact', { first_name: data.firstName, last_name: data.lastName, email: data.email, phone: data.phone, message: data.message }); }
    public async getCases(): Promise<Case[]> { const response = await this.axiosInstance.get<Case[]>('/cases'); return response.data; }
    public async createCase(data: CreateCaseRequest): Promise<Case> { const response = await this.axiosInstance.post<Case>('/cases', data); return response.data; }
    public async getCaseDetails(caseId: string): Promise<Case> { const response = await this.axiosInstance.get<Case>(`/cases/${caseId}`); return response.data; }
    public async deleteCase(caseId: string): Promise<void> { await this.axiosInstance.delete(`/cases/${caseId}`); }
    public async getFindings(caseId: string): Promise<Finding[]> { const response = await this.axiosInstance.get<{ findings: Finding[] }>(`/cases/${caseId}/findings`); return response.data.findings || []; }
    public async analyzeCase(caseId: string): Promise<CaseAnalysisResult> { const response = await this.axiosInstance.post<CaseAnalysisResult>(`/cases/${caseId}/analyze`); return response.data; }
    public async register(data: RegisterRequest): Promise<void> { await this.axiosInstance.post('/auth/register', data); }
    public async fetchUserProfile(): Promise<User> { const response = await this.axiosInstance.get<User>('/users/me'); return response.data; }
    public async changePassword(data: ChangePasswordRequest): Promise<void> { await this.axiosInstance.post('/auth/change-password', data); }
    public async deleteAccount(): Promise<void> { await this.axiosInstance.delete('/users/me'); }
    public async getWebSocketUrl(_caseId: string): Promise<string> { return ""; }
    public async getAllUsers(): Promise<User[]> { const response = await this.axiosInstance.get<User[]>('/admin/users'); return response.data; }
    public async updateUser(userId: string, data: UpdateUserRequest): Promise<User> { const response = await this.axiosInstance.put<User>(`/admin/users/${userId}`, data); return response.data; }
    public async deleteUser(userId: string): Promise<void> { await this.axiosInstance.delete(`/admin/users/${userId}`); }

    // --- V2 API Calls ---
    public async initiateDraftingJob(data: CreateDraftingJobRequest): Promise<DraftingJobStatus> { const response = await this.axiosInstance.post<DraftingJobStatus>(`${API_V2_URL}/drafting/jobs`, data); return response.data; }
    public async getDraftingJobStatus(jobId: string): Promise<DraftingJobStatus> { const response = await this.axiosInstance.get<DraftingJobStatus>(`${API_V2_URL}/drafting/jobs/${jobId}/status`); return response.data; }
    public async getDraftingJobResult(jobId: string): Promise<DraftingJobResult> { const response = await this.axiosInstance.get<DraftingJobResult>(`${API_V2_URL}/drafting/jobs/${jobId}/result`); return response.data; }
}

export const apiService = new ApiService();