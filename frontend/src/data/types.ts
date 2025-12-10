// FILE: src/data/types.ts
// PHOENIX PROTOCOL - TYPES REFACTOR V5.5 (INTELLIGENCE UPDATE)
// 1. FIX: Added 'ConflictingParty' interface.
// 2. FIX: Updated 'CaseAnalysisResult' to include 'conflicting_parties' and 'key_evidence'.
// 3. COMPATIBILITY: Marked 'risks' as optional to support legacy data without breaking strict typing.

export type ConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';

export interface User {
    id: string;
    email: string;
    username: string;
    role: 'ADMIN' | 'LAWYER' | 'CLIENT';
    status: 'active' | 'inactive';
    created_at: string;
    token?: string;
    subscription_status?: string;
}

export type AdminUser = User;

export interface Case {
    id: string;
    case_number: string;
    case_name: string;
    title: string;
    status: 'open' | 'closed' | 'pending' | 'archived';
    client?: { name: string; phone: string; email: string; };
    opposing_party?: { name: string; lawyer: string; };
    court_info?: { name: string; judge: string; };
    description: string;
    created_at: string;
    updated_at: string;
    tags: string[];
    chat_history?: ChatMessage[];
    document_count?: number;
    alert_count?: number;
    event_count?: number;
    finding_count?: number;
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
    category?: string;
    page_number?: number;
    confidence_score: number;
    created_at: string;
}

export interface ChatMessage {
    role: 'user' | 'ai'; 
    content: string;
    timestamp: string;
}

export interface CalendarEvent {
    id: string;
    title: string;
    description?: string;
    start_date: string;
    end_date: string;
    is_all_day: boolean;
    event_type: 'HEARING' | 'DEADLINE' | 'MEETING' | 'OTHER' | 'FILING' | 'COURT_DATE' | 'CONSULTATION';
    status: 'PENDING' | 'COMPLETED' | 'CANCELLED' | 'OVERDUE' | 'ARCHIVED';
    case_id?: string;
    document_id?: string;
    location?: string;
    notes?: string;
    priority?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
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

// --- FINANCE ---
export interface InvoiceItem {
    description: string;
    quantity: number;
    unit_price: number;
    total: number;
}

export interface Invoice {
    id: string;
    invoice_number: string;
    client_name: string;
    client_email?: string;
    client_address?: string;
    issue_date: string;
    due_date: string;
    items: InvoiceItem[];
    subtotal: number;
    tax_rate: number;
    tax_amount: number;
    total_amount: number;
    currency: string;
    status: 'DRAFT' | 'SENT' | 'PAID' | 'OVERDUE' | 'CANCELLED';
    notes?: string;
}

export interface InvoiceCreateRequest {
    client_name: string;
    client_email?: string;
    client_address?: string;
    items: InvoiceItem[];
    tax_rate: number;
    due_date?: string;
    notes?: string;
}

export interface ArchiveItemOut {
    id: string;
    title: string;
    file_type: string;
    category: string;
    storage_key: string;
    file_size: number;
    created_at: string;
    case_id?: string;
    parent_id?: string; 
    item_type?: 'FILE' | 'FOLDER'; 
}

// --- SHARED ---
export interface LoginRequest { username: string; password: string; }
export interface RegisterRequest { email: string; password: string; username: string; }
export interface ChangePasswordRequest { current_password: string; new_password: string; }
export interface UpdateUserRequest { username?: string; email?: string; role?: string; subscription_status?: string; status?: 'active' | 'inactive'; }
export interface CreateCaseRequest { case_number: string; title: string; case_name?: string; description?: string; clientName?: string; clientEmail?: string; clientPhone?: string; status?: string; }
export interface DeletedDocumentResponse { documentId: string; deletedFindingIds: string[]; }
export interface CalendarEventCreateRequest { title: string; description?: string; start_date: string; end_date?: string; is_all_day?: boolean; event_type: string; case_id?: string; location?: string; notes?: string; priority?: string; attendees?: string[]; }

// --- DRAFTING ---
export interface CreateDraftingJobRequest { 
    user_prompt: string; 
    template_id?: string; 
    case_id?: string; 
    context?: string;
    draft_type?: string;
    use_library?: boolean; 
}

export type DraftingJobStatus = { 
    job_id: string; 
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'; 
    error?: string; 
    result_summary?: string; 
};

export type DraftingJobResult = { 
    document_text: string; 
    document_html?: string; 
    result_text?: string; 
    job_id?: string;
    status?: string;
};

// --- INTELLIGENCE & ANALYSIS (UPDATED) ---

// New Interface for the Debate Judge
export interface ConflictingParty {
    party_name: string;
    core_claim: string;
}

export interface CaseAnalysisResult { 
    summary_analysis: string; 
    contradictions: string[]; 
    missing_info: string[]; 
    
    // New Fields for V5.2 Intelligence
    conflicting_parties?: ConflictingParty[];
    key_evidence?: string[];
    
    // Legacy support (optional)
    risks?: string[]; 
    error?: string; 
}

export interface GraphNode { id: string; name: string; group: string; val: number; }
export interface GraphLink { source: string; target: string; label: string; }
export interface GraphData { nodes: GraphNode[]; links: GraphLink[]; }