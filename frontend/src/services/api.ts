import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type { LoginRequest, RegisterRequest, Case, CreateCaseRequest, Document, CreateDraftingJobRequest, DraftingJobStatus, ChangePasswordRequest, AdminUser, UpdateUserRequest, ApiKey, ApiKeyCreateRequest, CalendarEvent, CalendarEventCreateRequest, Finding, DraftingJobResult } from '../data/types';

interface LoginResponse { access_token: string; }
interface RegisterResponse { message: string; }
interface DocumentContentResponse { text: string; }
interface WebSocketInfo { url: string; token: string; }

const API_BASE_URL = 'https://advocatus-prod-api.duckdns.org';
const API_V1_URL = `${API_BASE_URL}/api/v1`;

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
    
    public async ensureValidToken(): Promise<void> {
        const token = localStorage.getItem('jwtToken');
        if (!token) {
            if (this.onUnauthorized) this.onUnauthorized();
            throw new Error("Authentication token not found.");
        }
        const payload = decodeJwtPayload(token);
        const isExpired = !payload || payload.exp * 1000 < Date.now() + 20000;
        if (isExpired) {
            try {
                await this.refreshAccessToken();
            } catch (error) {
                console.error("Failed to refresh token proactively:", error);
                throw error;
            }
        }
    }

    public async refreshAccessToken(): Promise<LoginResponse> {
        if (this.refreshTokenPromise) { 
            return this.refreshTokenPromise; 
        }
        
        // PHOENIX PROTOCOL CURE: The POST request for refresh must not contain a body or a Content-Type header.
        // We pass `undefined` as the data argument to ensure Axios sends a request with an empty body.
        this.refreshTokenPromise = this.axiosInstance.post<LoginResponse>('/auth/refresh', undefined, {
            withCredentials: true,
            timeout: 5000,
            headers: {
                // By not specifying a Content-Type, we allow Axios to omit it, which is correct for a bodyless request.
                'Content-Type': null
            }
        })
        .then(response => {
            const { access_token } = response.data;
            localStorage.setItem('jwtToken', access_token);
            this.axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
            return response.data;
        })
        .catch(error => {
            console.error('Refresh token request failed:', error);
            console.error('Refresh error details:', {
                status: error.response?.status,
                data: error.response?.data,
                headers: error.response?.headers
            });
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

    public async getWebSocketInfo(caseId: string): Promise<WebSocketInfo> {
        await this.ensureValidToken();
        const token = localStorage.getItem('jwtToken');
        if (!token) {
            if (this.onUnauthorized) this.onUnauthorized();
            throw new Error('Fatal: Token disappeared after validation.');
        }
        return {
            url: `wss://advocatus-prod-api.duckdns.org/ws/case/${caseId}`,
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
    public async getFindings(caseId: string): Promise<Finding[]> { return (await this.axiosInstance.get(`/cases/${caseId}/findings`)).data; }
    
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