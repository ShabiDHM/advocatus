// FILE: src/data/types.ts
// PHOENIX PROTOCOL - TYPES FINALIZATION
// 1. UPDATED: User, RegisterRequest, UpdateUserRequest to match Backend 'username' field.
// 2. REMOVED: 'full_name' field (not supported by backend).

export type ConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';

export interface User {
    id: string;
    email: string;
    username: string; // MATCHES BACKEND
    role: 'ADMIN' | 'LAWYER' | 'CLIENT';
    is_active: boolean;
    created_at: string;
    token?: string;
    subscription_status?: string;
}

// Alias AdminUser to User to fix legacy imports
export type AdminUser = User; 

export interface Case {
    id: string;
    case_number: string;
    case_name: string;
    title: string;
    status: 'open' | 'closed' | 'pending' | 'archived';
    client?: {
        name: string;
        phone: string;
        email: string;
    };
    opposing_party?: {
        name: string;
        lawyer: string;
    };
    court_info?: {
        name: string;
        judge: string;
    };
    description: string;
    created_at: string;
    updated_at: string;
    tags: string[];
    chat_history?: ChatMessage[];
    
    // Aggregated Counts for Dashboard Cards
    document_count?: number;
    alert_count?: number;
    event_count?: number;
}

export interface Document {
    id: string;
    file_name: string;
    file_type: string;
    mime_type?: string;
    storage_key: string;
    uploaded_by: string;
    created_at: string;
    status: 'PENDING' | 'PROCESSING' | 'READY' | 'COMPLETED' | 'FAILED';
    summary?: string;
    risk_score?: number;
    ocr_status?: string;
    processed_text_storage_key?: string;
    preview_storage_key?: string;
    error_message?: string;
    progress_percent?: number;
    progress_message?: string;
}

export interface Finding {
    id: string;
    case_id: string;
    document_id?: string;
    document_name?: string;
    finding_text: string;
    source_text: string;
    page_number?: number;
    confidence_score: number;
    created_at: string;
}

export interface ChatMessage {
    sender: 'user' | 'ai';
    content: string;
    timestamp: string;
    text?: string;
}

export interface CalendarEvent {
    id: string;
    title: string;
    description?: string;
    start_date: string;
    end_date: string;
    is_all_day: boolean;
    event_type: 'HEARING' | 'DEADLINE' | 'MEETING' | 'OTHER' | 'FILING' | 'COURT_DATE' | 'CONSULTATION';
    status: 'PENDING' | 'COMPLETED' | 'CANCELLED';
    case_id?: string;
    document_id?: string;
    location?: string;
    notes?: string;
    priority?: string;
    attendees?: string[]; 
}

export interface BusinessProfile {
    id: string;
    firm_name: string;
    address?: string;
    city?: string;
    phone?: string;
    email_public?: string;
    website?: string;
    tax_id?: string;
    branding_color: string;
    logo_url?: string;
    is_complete: boolean;
}

export interface BusinessProfileUpdate {
    firm_name?: string;
    address?: string;
    city?: string;
    phone?: string;
    email_public?: string;
    website?: string;
    tax_id?: string;
    branding_color?: string;
}

export interface LoginRequest {
    username: string; // NOTE: Backend Auth uses OAuth2 form data (username=email), handled in API/AuthContext
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
    username: string; // REPLACES full_name
}

export interface ChangePasswordRequest {
    current_password: string;
    new_password: string;
}

export interface UpdateUserRequest {
    username?: string; // REPLACES full_name
    email?: string;
    role?: string; 
    subscription_status?: string;
    is_active?: boolean;
}

export interface CreateCaseRequest {
    case_number: string;
    title: string;
    case_name?: string;
    description?: string;
    client_name?: string;
    client_email?: string;
    client_phone?: string;
    status?: string;
}

export interface DeletedDocumentResponse {
    documentId: string;
    deletedFindingIds: string[];
}

export interface CalendarEventCreateRequest {
    title: string;
    description?: string;
    start_date: string;
    end_date?: string;
    is_all_day?: boolean;
    event_type: string;
    case_id?: string;
    location?: string;
    notes?: string;
    priority?: string;
    attendees?: string[];
}

export type DraftingJobStatus = {
    job_id: string;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    error?: string;
    result_summary?: string;
};

export type DraftingJobResult = {
    document_text: string;
    document_html: string;
    result_text?: string;
};

export interface CreateDraftingJobRequest {
    template_id?: string;
    user_prompt: string;
    case_id?: string;
    context?: string;
}

export interface CaseAnalysisResult {
    summary_analysis: string;
    contradictions: string[];
    risks: string[];
    missing_info: string[];
    error?: string;
}