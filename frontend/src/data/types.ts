// FILE: src/data/types.ts
// PHOENIX PROTOCOL - DATA TYPES
// Includes: User, Case, Document, and BusinessProfile definitions.

export type ConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';

export interface User {
    id: string;
    email: string;
    full_name: string;
    role: 'ADMIN' | 'LAWYER' | 'CLIENT';
    is_active: boolean;
    created_at: string;
}

export interface Case {
    id: string;
    case_number: string;
    case_name: string;
    title: string; // Legacy support
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
}

export interface Document {
    id: string;
    file_name: string;
    file_type: string;
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
    // UI Progress Props
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
    event_type: 'HEARING' | 'DEADLINE' | 'MEETING' | 'OTHER';
    status: 'PENDING' | 'COMPLETED' | 'CANCELLED';
    case_id?: string;
    document_id?: string;
}

// --- BUSINESS MODULE TYPES ---
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

// --- AUTH REQUEST TYPES ---
export interface LoginRequest {
    username: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
    full_name: string;
}

export interface ChangePasswordRequest {
    current_password: string;
    new_password: string;
}

export interface UpdateUserRequest {
    full_name?: string;
    email?: string;
}

export interface CreateCaseRequest {
    case_number: string;
    title: string;
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
}

export type DraftingJobStatus = {
    job_id: string;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
    error?: string;
};

export type DraftingJobResult = {
    document_text: string;
    document_html: string;
};

export interface CreateDraftingJobRequest {
    template_id?: string;
    user_prompt: string;
    case_id?: string;
}

export interface CaseAnalysisResult {
    summary_analysis: string;
    contradictions: string[];
    risks: string[];
    missing_info: string[];
    error?: string;
}