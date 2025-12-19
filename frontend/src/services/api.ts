// FILE: src/services/api.ts
import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError, AxiosHeaders } from 'axios';
import type {
    LoginRequest, RegisterRequest, Case, CreateCaseRequest, Document, User, UpdateUserRequest,
    DeletedDocumentResponse, CalendarEvent, CalendarEventCreateRequest, CreateDraftingJobRequest,
    DraftingJobStatus, DraftingJobResult, ChangePasswordRequest, CaseAnalysisResult,
    BusinessProfile, BusinessProfileUpdate, Invoice, InvoiceCreateRequest, InvoiceItem,
    GraphData, ArchiveItemOut
} from '../data/types';

// --- LOCAL INTERFACES ---
export interface AuditIssue { id: string; severity: 'CRITICAL' | 'WARNING'; message: string; related_item_id?: string; item_type?: 'INVOICE' | 'EXPENSE'; }
export interface TaxCalculation { period_month: number; period_year: number; total_sales_gross: number; total_purchases_gross: number; vat_collected: number; vat_deductible: number; net_obligation: number; currency: string; status: string; regime: string; tax_rate_applied: string; description: string; }
export interface WizardState { calculation: TaxCalculation; issues: AuditIssue[]; ready_to_close: boolean; }
export interface InvoiceUpdate { client_name?: string; client_email?: string; client_address?: string; items?: InvoiceItem[]; tax_rate?: number; due_date?: string; status?: string; notes?: string; }

// --- INTEGRATION HUB INTERFACES ---
export interface ImportBatchOut { 
    id: string; 
    filename: string; 
    status: string; 
    row_count: number; 
    total_volume: number; 
    created_at: string; 
    mapping_required?: false;
}

export interface ImportMappingResponse {
    mapping_required: true;
    upload_id: string;
    detected_headers: string[];
    system_fields: string[];
}

export type PosImportResponse = ImportBatchOut | ImportMappingResponse;

export interface TransactionOut {
    id: string;
    transaction_ref?: string;
    date_time: string;
    product_name: string;
    quantity: number;
    unit_price: number;
    total_amount: number;
}

// --- ANALYTICS INTERFACES ---
export interface SalesTrendPoint { date: string; amount: number; }
export interface TopProductItem { product_name: string; total_quantity: number; total_revenue: number; }
export interface AnalyticsDashboardData {
    total_revenue_period: number;
    total_transactions_period: number;
    sales_trend: SalesTrendPoint[];
    top_products: TopProductItem[];
}

// Restored Local Expense Interfaces
export interface Expense { id: string; category: string; amount: number; description?: string; date: string; currency: string; receipt_url?: string; }
export interface ExpenseCreateRequest { category: string; amount: number; description?: string; date?: string; }
export interface ExpenseUpdate { category?: string; amount?: number; description?: string; date?: string; }

interface LoginResponse { access_token: string; }
interface DocumentContentResponse { text: string; }

const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';
let normalizedUrl = rawBaseUrl.replace(/\/$/, '');
if (typeof window !== 'undefined' && window.location.protocol === 'https:' && normalizedUrl.startsWith('http:')) { normalizedUrl = normalizedUrl.replace('http:', 'https:'); }
export const API_BASE_URL = normalizedUrl;
export const API_V1_URL = `${API_BASE_URL}/api/v1`;
export const API_V2_URL = `${API_BASE_URL}/api/v2`;

class TokenManager {
    private accessToken: string | null = null;
    get(): string | null { return this.accessToken; }
    set(token: string | null): void { this.accessToken = token; }
}
const tokenManager = new TokenManager();

class ApiService {
    public axiosInstance: AxiosInstance;
    public onUnauthorized: (() => void) | null = null;
    private isRefreshing = false;
    private failedQueue: { resolve: (value: any) => void; reject: (reason?: any) => void; }[] = [];

    constructor() {
        this.axiosInstance = axios.create({ baseURL: API_V1_URL, withCredentials: true });
        this.setupInterceptors();
    }

    public setLogoutHandler(handler: () => void) { this.onUnauthorized = handler; }
    private processQueue(error: Error | null) { this.failedQueue.forEach(prom => { if (error) prom.reject(error); else prom.resolve(tokenManager.get()); }); this.failedQueue = []; }

    private setupInterceptors() {
        this.axiosInstance.interceptors.request.use((config) => {
                const token = tokenManager.get();
                if (!config.headers) config.headers = new AxiosHeaders();
                if (token) {
                    if (config.headers instanceof AxiosHeaders) config.headers.set('Authorization', `Bearer ${token}`);
                    else (config.headers as any).Authorization = `Bearer ${token}`;
                }
                return config;
            }, (error) => Promise.reject(error));

        this.axiosInstance.interceptors.response.use((response) => response, async (error: AxiosError) => {
                const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
                if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/auth/refresh') {
                    if (this.isRefreshing) { return new Promise((resolve, reject) => { this.failedQueue.push({ resolve, reject }); }).then((token) => { if (originalRequest.headers instanceof AxiosHeaders) { originalRequest.headers.set('Authorization', `Bearer ${token}`); } else { (originalRequest.headers as any).Authorization = `Bearer ${token}`; } return this.axiosInstance(originalRequest); }); }
                    originalRequest._retry = true;
                    this.isRefreshing = true;
                    try {
                        const { data } = await this.axiosInstance.post<LoginResponse>('/auth/refresh');
                        tokenManager.set(data.access_token);
                        if (originalRequest.headers instanceof AxiosHeaders) { originalRequest.headers.set('Authorization', `Bearer ${data.access_token}`); } else { (originalRequest.headers as any).Authorization = `Bearer ${data.access_token}`; }
                        this.processQueue(null);
                        return this.axiosInstance(originalRequest);
                    } catch (refreshError) { tokenManager.set(null); this.processQueue(refreshError as Error); if (this.onUnauthorized) this.onUnauthorized(); return Promise.reject(refreshError); } finally { this.isRefreshing = false; }
                }
                return Promise.reject(error);
            });
    }
    
    public getToken(): string | null { return tokenManager.get(); }
    public async refreshToken(): Promise<boolean> { try { const response = await this.axiosInstance.post<LoginResponse>('/auth/refresh'); if (response.data.access_token) { tokenManager.set(response.data.access_token); return true; } return false; } catch (error) { console.warn("[API] Session Refresh Failed (Normal if logged out):", error); return false; } }
    public async login(data: LoginRequest): Promise<LoginResponse> { const response = await this.axiosInstance.post<LoginResponse>('/auth/login', data); if (response.data.access_token) tokenManager.set(response.data.access_token); return response.data; }
    public logout() { tokenManager.set(null); }

    public async fetchImageBlob(url: string): Promise<Blob> { const response = await this.axiosInstance.get(url, { responseType: 'blob' }); return response.data; }
    public async getExpenseReceiptBlob(expenseId: string): Promise<{ blob: Blob, filename: string }> { const response = await this.axiosInstance.get(`/finance/expenses/${expenseId}/receipt`, { responseType: 'blob' }); const disposition = response.headers['content-disposition']; let filename = `receipt-${expenseId}.pdf`; if (disposition && disposition.indexOf('filename=') !== -1) { const matches = /filename="([^"]*)"/.exec(disposition); if (matches != null && matches[1]) filename = matches[1]; } return { blob: response.data, filename }; }
    public async getWizardState(month: number, year: number): Promise<WizardState> { const response = await this.axiosInstance.get<WizardState>('/finance/wizard/state', { params: { month, year } }); return response.data; }
    public async downloadMonthlyReport(month: number, year: number): Promise<void> { const response = await this.axiosInstance.get('/finance/wizard/report/pdf', { params: { month, year }, responseType: 'blob' }); const url = window.URL.createObjectURL(new Blob([response.data])); const link = document.createElement('a'); link.href = url; link.setAttribute('download', `Raporti_${month}_${year}.pdf`); document.body.appendChild(link); link.click(); link.parentNode?.removeChild(link); window.URL.revokeObjectURL(url); }

    // --- POS IMPORT & ANALYTICS ---
    
    public async uploadPosFile(file: File): Promise<PosImportResponse> {
        const formData = new FormData();
        formData.append('file', file);
        const response = await this.axiosInstance.post<PosImportResponse>('/finance/import-pos', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    }

    public async finalizePosImport(uploadId: string, mappings: Record<string, string>): Promise<ImportBatchOut> {
        const response = await this.axiosInstance.post<ImportBatchOut>(`/finance/import-pos/${uploadId}/map`, { mappings });
        return response.data;
    }

    public async getImportHistory(): Promise<ImportBatchOut[]> {
        const response = await this.axiosInstance.get<ImportBatchOut[]>('/finance/import-batches');
        return response.data;
    }

    public async getBatchTransactions(batchId: string): Promise<TransactionOut[]> {
        const response = await this.axiosInstance.get<TransactionOut[]>(`/finance/import-batches/${batchId}/transactions`);
        return response.data;
    }

    public async getAnalyticsDashboard(days: number = 30): Promise<AnalyticsDashboardData> {
        const response = await this.axiosInstance.get<AnalyticsDashboardData>(`/finance/analytics/dashboard`, { params: { days } });
        return response.data;
    }

    public async getInvoices(): Promise<Invoice[]> { const response = await this.axiosInstance.get<any>('/finance/invoices'); return Array.isArray(response.data) ? response.data : (response.data.invoices || []); }
    public async createInvoice(data: InvoiceCreateRequest): Promise<Invoice> { const response = await this.axiosInstance.post<Invoice>('/finance/invoices', data); return response.data; }
    public async updateInvoice(invoiceId: string, data: InvoiceUpdate): Promise<Invoice> { const response = await this.axiosInstance.put<Invoice>(`/finance/invoices/${invoiceId}`, data); return response.data; }
    public async updateInvoiceStatus(invoiceId: string, status: string): Promise<Invoice> { const response = await this.axiosInstance.put<Invoice>(`/finance/invoices/${invoiceId}/status`, { status }); return response.data; }
    public async deleteInvoice(invoiceId: string): Promise<void> { await this.axiosInstance.delete(`/finance/invoices/${invoiceId}`); }
    public async downloadInvoicePdf(invoiceId: string, lang: string = 'sq'): Promise<void> { const response = await this.axiosInstance.get(`/finance/invoices/${invoiceId}/pdf`, { params: { lang }, responseType: 'blob' }); const url = window.URL.createObjectURL(new Blob([response.data])); const link = document.createElement('a'); link.href = url; link.setAttribute('download', `Invoice_${invoiceId}.pdf`); document.body.appendChild(link); link.click(); link.parentNode?.removeChild(link); }
    public async getInvoicePdfBlob(invoiceId: string, lang: string = 'sq'): Promise<Blob> { const response = await this.axiosInstance.get(`/finance/invoices/${invoiceId}/pdf`, { params: { lang }, responseType: 'blob' }); return response.data; }
    public async archiveInvoice(invoiceId: string, caseId?: string): Promise<ArchiveItemOut> { const params = caseId ? { case_id: caseId } : {}; const response = await this.axiosInstance.post<ArchiveItemOut>(`/finance/invoices/${invoiceId}/archive`, null, { params }); return response.data; }

    public async getExpenses(): Promise<Expense[]> { const response = await this.axiosInstance.get<any>('/finance/expenses'); return Array.isArray(response.data) ? response.data : (response.data.expenses || []); }
    public async createExpense(data: ExpenseCreateRequest): Promise<Expense> { const response = await this.axiosInstance.post<Expense>('/finance/expenses', data); return response.data; }
    public async updateExpense(expenseId: string, data: ExpenseUpdate): Promise<Expense> { const response = await this.axiosInstance.put<Expense>(`/finance/expenses/${expenseId}`, data); return response.data; }
    public async deleteExpense(expenseId: string): Promise<void> { await this.axiosInstance.delete(`/finance/expenses/${expenseId}`); }
    public async uploadExpenseReceipt(expenseId: string, file: File): Promise<void> { const formData = new FormData(); formData.append('file', file); await this.axiosInstance.put(`/finance/expenses/${expenseId}/receipt`, formData); }

    public async getBusinessProfile(): Promise<BusinessProfile> { const response = await this.axiosInstance.get<BusinessProfile>('/business/profile'); return response.data; }
    public async updateBusinessProfile(data: BusinessProfileUpdate): Promise<BusinessProfile> { const response = await this.axiosInstance.put<BusinessProfile>('/business/profile', data); return response.data; }
    public async uploadBusinessLogo(file: File): Promise<BusinessProfile> { const formData = new FormData(); formData.append('file', file); const response = await this.axiosInstance.put<BusinessProfile>('/business/logo', formData); return response.data; }

    public async getArchiveItems(category?: string, caseId?: string, parentId?: string): Promise<ArchiveItemOut[]> { const params: any = {}; if (category) params.category = category; if (caseId) params.case_id = caseId; if (parentId) params.parent_id = parentId; const response = await this.axiosInstance.get<ArchiveItemOut[]>('/archive/items', { params }); return Array.isArray(response.data) ? response.data : ((response.data as any).items || []); }
    public async createArchiveFolder(title: string, parentId?: string, caseId?: string, category?: string): Promise<ArchiveItemOut> { const formData = new FormData(); formData.append('title', title); if (parentId) formData.append('parent_id', parentId); if (caseId) formData.append('case_id', caseId); if (category) formData.append('category', category); const response = await this.axiosInstance.post<ArchiveItemOut>('/archive/folder', formData); return response.data; }
    public async uploadArchiveItem(file: File, title: string, category: string, caseId?: string, parentId?: string): Promise<ArchiveItemOut> { const formData = new FormData(); formData.append('file', file); formData.append('title', title); formData.append('category', category); if (caseId) formData.append('case_id', caseId); if (parentId) formData.append('parent_id', parentId); const response = await this.axiosInstance.post<ArchiveItemOut>('/archive/upload', formData); return response.data; }
    public async deleteArchiveItem(itemId: string): Promise<void> { await this.axiosInstance.delete(`/archive/items/${itemId}`); }
    public async renameArchiveItem(itemId: string, newTitle: string): Promise<void> { await this.axiosInstance.put(`/archive/items/${itemId}/rename`, { new_title: newTitle }); }
    public async downloadArchiveItem(itemId: string, title: string): Promise<void> { const response = await this.axiosInstance.get(`/archive/items/${itemId}/download`, { responseType: 'blob' }); const url = window.URL.createObjectURL(new Blob([response.data])); const link = document.createElement('a'); link.href = url; link.setAttribute('download', title); document.body.appendChild(link); link.click(); link.parentNode?.removeChild(link); }
    public async getArchiveFileBlob(itemId: string): Promise<Blob> { const response = await this.axiosInstance.get(`/archive/items/${itemId}/download`, { params: { preview: true }, responseType: 'blob' }); return response.data; }

    public async getCases(): Promise<Case[]> { const response = await this.axiosInstance.get<any>('/cases'); return Array.isArray(response.data) ? response.data : (response.data.cases || []); }
    public async createCase(data: CreateCaseRequest): Promise<Case> { const response = await this.axiosInstance.post<Case>('/cases', data); return response.data; }
    public async getCaseDetails(caseId: string): Promise<Case> { const response = await this.axiosInstance.get<Case>(`/cases/${caseId}`); return response.data; }
    public async deleteCase(caseId: string): Promise<void> { await this.axiosInstance.delete(`/cases/${caseId}`); }
    public async getDocuments(caseId: string): Promise<Document[]> { const response = await this.axiosInstance.get<any>(`/cases/${caseId}/documents`); return Array.isArray(response.data) ? response.data : (response.data.documents || []); }
    public async uploadDocument(caseId: string, file: File, onProgress?: (percent: number) => void): Promise<Document> { const formData = new FormData(); formData.append('file', file); const response = await this.axiosInstance.post<Document>(`/cases/${caseId}/documents/upload`, formData, { onUploadProgress: (progressEvent) => { if (onProgress && progressEvent.total) { const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total); onProgress(percent); } } }); return response.data; }
    public async getDocument(caseId: string, documentId: string): Promise<Document> { const response = await this.axiosInstance.get<Document>(`/cases/${caseId}/documents/${documentId}`); return response.data; }
    public async deleteDocument(caseId: string, documentId: string): Promise<DeletedDocumentResponse> { const response = await this.axiosInstance.delete<DeletedDocumentResponse>(`/cases/${caseId}/documents/${documentId}`); return response.data; }
    public async bulkDeleteDocuments(caseId: string, documentIds: string[]): Promise<any> { const response = await this.axiosInstance.post(`/cases/${caseId}/documents/bulk-delete`, { document_ids: documentIds }); return response.data; }
    public async importArchiveDocuments(caseId: string, archiveItemIds: string[]): Promise<Document[]> { const response = await this.axiosInstance.post<Document[]>(`/cases/${caseId}/documents/import-archive`, { archive_item_ids: archiveItemIds }); return response.data; }

    public async getDocumentContent(caseId: string, documentId: string): Promise<DocumentContentResponse> { const response = await this.axiosInstance.get<DocumentContentResponse>(`/cases/${caseId}/documents/${documentId}/content`); return response.data; }
    public async getOriginalDocument(caseId: string, documentId: string): Promise<Blob> { const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/original`, { responseType: 'blob' }); return response.data; }
    public async getPreviewDocument(caseId: string, documentId: string): Promise<Blob> { const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/preview`, { responseType: 'blob' }); return response.data; }
    public async downloadDocumentReport(caseId: string, documentId: string): Promise<Blob> { const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${documentId}/report`, { responseType: 'blob' }); return response.data; }
    public async downloadObjection(caseId: string, docId: string): Promise<void> { const response = await this.axiosInstance.get(`/cases/${caseId}/documents/${docId}/generate-objection`, { responseType: 'blob' }); let filename = 'Kundërshtim.docx'; const disposition = response.headers['content-disposition']; if (disposition && disposition.indexOf('filename=') !== -1) { const matches = /filename="?([^"]+)"?/.exec(disposition); if (matches && matches[1]) filename = matches[1]; } const url = window.URL.createObjectURL(new Blob([response.data])); const link = document.createElement('a'); link.href = url; link.setAttribute('download', filename); document.body.appendChild(link); link.click(); link.parentNode?.removeChild(link); window.URL.revokeObjectURL(url); }
    public async archiveCaseDocument(caseId: string, documentId: string): Promise<ArchiveItemOut> { const response = await this.axiosInstance.post<ArchiveItemOut>(`/cases/${caseId}/documents/${documentId}/archive`); return response.data; }
    public async renameDocument(caseId: string, docId: string, newName: string): Promise<void> { await this.axiosInstance.put(`/cases/${caseId}/documents/${docId}/rename`, { new_name: newName }); }
    
    public async getCaseGraph(caseId: string): Promise<GraphData> { const response = await this.axiosInstance.get<GraphData>(`/graph/graph/${caseId}`); return response.data; }
    public async analyzeCase(caseId: string): Promise<CaseAnalysisResult> { const response = await this.axiosInstance.post<CaseAnalysisResult>(`/cases/${caseId}/analyze`); return response.data; }
    public async crossExamineDocument(caseId: string, documentId: string): Promise<CaseAnalysisResult> { const response = await this.axiosInstance.post<CaseAnalysisResult>(`/cases/${caseId}/documents/${documentId}/cross-examine`); return response.data; }
    public async sendChatMessage(caseId: string, message: string, documentId?: string, jurisdiction?: string): Promise<string> { const response = await this.axiosInstance.post<{ response: string }>(`/chat/case/${caseId}`, { message, document_id: documentId || null, jurisdiction: jurisdiction || 'ks' }); return response.data.response; }
    public async clearChatHistory(caseId: string): Promise<void> { await this.axiosInstance.delete(`/chat/case/${caseId}/history`); }
    
    public async getCalendarEvents(): Promise<CalendarEvent[]> { const response = await this.axiosInstance.get<any>('/calendar/events'); return Array.isArray(response.data) ? response.data : (response.data.events || []); }
    public async createCalendarEvent(data: CalendarEventCreateRequest): Promise<CalendarEvent> { const response = await this.axiosInstance.post<CalendarEvent>('/calendar/events', data); return response.data; }
    public async deleteCalendarEvent(eventId: string): Promise<void> { await this.axiosInstance.delete(`/calendar/events/${eventId}`); }
    public async getAlertsCount(): Promise<{ count: number }> { const response = await this.axiosInstance.get<{ count: number }>('/calendar/alerts'); return response.data; }
    public async sendContactForm(data: { firstName: string; lastName: string; email: string; phone: string; message: string }): Promise<void> { await this.axiosInstance.post('/support/contact', { first_name: data.firstName, last_name: data.lastName, email: data.email, phone: data.phone, message: data.message }); }
    public async getWebSocketUrl(_caseId: string): Promise<string> { return ""; }

    public async register(data: RegisterRequest): Promise<void> { await this.axiosInstance.post('/auth/register', data); }
    public async fetchUserProfile(): Promise<User> { const response = await this.axiosInstance.get<User>('/users/me'); return response.data; }
    public async changePassword(data: ChangePasswordRequest): Promise<void> { await this.axiosInstance.post('/auth/change-password', data); }
    public async deleteAccount(): Promise<void> { await this.axiosInstance.delete('/users/me'); }
    public async getAllUsers(): Promise<User[]> { const response = await this.axiosInstance.get<any>('/admin/users'); return Array.isArray(response.data) ? response.data : (response.data.users || []); }
    public async updateUser(userId: string, data: UpdateUserRequest): Promise<User> { const response = await this.axiosInstance.put<User>(`/admin/users/${userId}`, data); return response.data; }
    public async deleteUser(userId: string): Promise<void> { await this.axiosInstance.delete(`/admin/users/${userId}`); }

    public async initiateDraftingJob(data: CreateDraftingJobRequest): Promise<DraftingJobStatus> { const response = await this.axiosInstance.post<DraftingJobStatus>(`${API_V2_URL}/drafting/jobs`, data); return response.data; }
    public async getDraftingJobStatus(jobId: string): Promise<DraftingJobStatus> { const response = await this.axiosInstance.get<DraftingJobStatus>(`${API_V2_URL}/drafting/jobs/${jobId}/status`); return response.data; }
    public async getDraftingJobResult(jobId: string): Promise<DraftingJobResult> { const response = await this.axiosInstance.get<DraftingJobResult>(`${API_V2_URL}/drafting/jobs/${jobId}/result`); return response.data; }
}

export const apiService = new ApiService();