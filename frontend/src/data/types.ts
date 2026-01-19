// FILE: src/data/types.ts
// PHOENIX PROTOCOL - TYPES V8.0 (SUBSCRIPTION DATA)
// 1. ADDED: 'subscription_expiry' and 'plan_tier' to User.
// 2. ADDED: Request interfaces for SubscriptionUpdate and PromoteRequest.

export type ConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';

// --- USER & AUTH ---
export interface User { 
    id: string; 
    email: string; 
    username: string; 
    role: 'ADMIN' | 'LAWYER' | 'CLIENT' | 'STANDARD'; 
    status: 'active' | 'inactive'; 
    created_at: string; 
    token?: string; 
    
    // SaaS Fields
    subscription_status?: string; 
    subscription_expiry?: string; // ISO Date String
    plan_tier?: 'SOLO' | 'STARTUP' | 'GROWTH' | 'ENTERPRISE';
    
    business_profile?: BusinessProfile; 
}

export type AdminUser = User;

export interface LoginRequest { username: string; password: string; }
export interface RegisterRequest { email: string; password: string; username: string; }
export interface ChangePasswordRequest { current_password: string; new_password: string; }
export interface UpdateUserRequest { username?: string; email?: string; role?: string; subscription_status?: string; status?: 'active' | 'inactive'; }
export interface AcceptInviteRequest { token: string; username: string; password: string; }

// --- ADMIN MANAGEMENT REQUESTS ---
export interface SubscriptionUpdate {
    status: string;
    expiry_date?: string; // ISO Date
    plan_tier?: string;
}

export interface PromoteRequest {
    firm_name: string;
    plan_tier: string;
}

// --- BUSINESS PROFILE ---
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
    vat_rate?: number; 
    target_margin?: number; 
    currency?: string; 
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
    vat_rate?: number; 
    target_margin?: number; 
    currency?: string; 
}

// --- CHAT & AGENTS ---
export type AgentType = 'business' | 'legal';
export type Jurisdiction = 'ks' | 'al';
export type ChatMode = 'general' | 'document';
export interface ChatMessage { role: 'user' | 'ai'; content: string; timestamp: string; }

// --- CASE MANAGEMENT ---
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
    is_shared?: boolean; 
}

export interface CreateCaseRequest { case_number: string; title: string; case_name?: string; description?: string; clientName?: string; clientEmail?: string; clientPhone?: string; status?: string; }

export interface Document { 
    id: string; 
    file_name: string; 
    file_type: string; 
    mime_type?: string; 
    storage_key: string; 
    uploaded_by: string; 
    created_at: string; 
    status: 'UPLOADING' | 'PENDING' | 'PROCESSING' | 'READY' | 'COMPLETED' | 'FAILED'; 
    summary?: string; 
    risk_score?: number; 
    ocr_status?: string; 
    processed_text_storage_key?: string; 
    preview_storage_key?: string; 
    error_message?: string; 
    progress_percent?: number; 
    progress_message?: string; 
    is_shared?: boolean; 
}

export interface DeletedDocumentResponse { documentId: string; deletedFindingIds: string[]; }

// --- CALENDAR ---
export interface CalendarEvent { 
    id: string; 
    title: string; 
    description?: string; 
    start_date: string; 
    end_date: string; 
    is_all_day: boolean; 
    event_type: 'APPOINTMENT' | 'TASK' | 'PAYMENT_DUE' | 'TAX_DEADLINE' | 'PERSONAL' | 'OTHER'; 
    status: 'PENDING' | 'COMPLETED' | 'CANCELLED' | 'OVERDUE' | 'ARCHIVED'; 
    case_id?: string; 
    document_id?: string; 
    location?: string; 
    notes?: string; 
    priority?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'; 
    attendees?: string[]; 
    is_public?: boolean; 
}

export interface CalendarEventCreateRequest { title: string; description?: string; start_date: string; end_date?: string; is_all_day?: boolean; event_type: string; case_id?: string; location?: string; notes?: string; priority?: string; attendees?: string[]; }

// --- FINANCE (BILLING) ---
export interface InvoiceItem { description: string; quantity: number; unit_price: number; total: number; }

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
    status: 'DRAFT' | 'SENT' | 'PAID' | 'PENDING' | 'OVERDUE' | 'CANCELLED'; 
    notes?: string; 
    related_case_id?: string; 
}

export interface InvoiceCreateRequest { client_name: string; client_email?: string; client_address?: string; items: InvoiceItem[]; tax_rate: number; due_date?: string; notes?: string; related_case_id?: string; status?: string; }

export interface Expense { 
    id: string; 
    category: string; 
    amount: number; 
    description?: string; 
    date: string; 
    currency: string; 
    receipt_url?: string; 
    related_case_id?: string; 
}

export interface ExpenseCreateRequest { category: string; amount: number; description?: string; date?: string; related_case_id?: string; }
export interface ExpenseUpdate { category?: string; amount?: number; description?: string; date?: string; related_case_id?: string; }

export interface CaseFinancialSummary { case_id: string; case_title: string; case_number: string; total_billed: number; total_expenses: number; net_balance: number; }
export interface SalesTrendPoint { date: string; amount: number; }
export interface TopProductItem { product_name: string; total_quantity: number; total_revenue: number; }
export interface AnalyticsDashboardData { total_revenue_period: number; total_transactions_period: number; sales_trend: SalesTrendPoint[]; top_products: TopProductItem[]; total_profit_period?: number; }
export interface PosTransaction { id: string; product_name: string; quantity: number; total_price: number; transaction_date: string; payment_method: string; }

// --- ARCHIVE & SHARING ---
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
    is_shared?: boolean; 
    indexing_status?: 'PENDING' | 'PROCESSING' | 'READY' | 'FAILED'; 
}

// --- DRAFTING ---
export interface CreateDraftingJobRequest { user_prompt: string; template_id?: string; case_id?: string; context?: string; draft_type?: string; document_type?: string; use_library?: boolean; }
export type DraftingJobStatus = { job_id: string; status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'; error?: string; result_summary?: string; };
export type DraftingJobResult = { document_text: string; document_html?: string; result_text?: string; job_id?: string; status?: string; };

// --- ANALYSIS ---
export interface GraphNode { id: string; name: string; group: string; val: number; }
export interface GraphLink { source: string; target: string; label: string; }
export interface GraphData { nodes: GraphNode[]; links: GraphLink[]; }

export interface ChronologyEvent { date: string; event: string; source_doc?: string; source?: string; }

export interface AdversarialSimulation {
    opponent_strategy: string;
    weakness_attacks: string[];
    counter_claims: string[];
    predicted_outcome: string;
}

export interface Contradiction {
    claim: string;
    evidence: string;
    severity: 'HIGH' | 'MEDIUM' | 'LOW';
    impact: string;
}

export interface DeepAnalysisResult {
    adversarial_simulation: AdversarialSimulation;
    chronology: ChronologyEvent[];
    contradictions: Contradiction[];
    error?: string;
}

export interface CaseAnalysisResult {
    summary?: string;
    key_issues?: string[];
    legal_basis?: string[];
    strategic_analysis?: string;
    weaknesses?: string[];
    action_plan?: string[];
    risk_level?: string;
    red_flags?: string[];
    contradictions?: string[]; 
    chronology?: ChronologyEvent[];
    judicial_observation?: string;
    strategic_summary?: string;
    error?: string;
}

export interface SpreadsheetAnalysisResult { 
    file_id?: string; 
    filename: string; 
    record_count: number; 
    columns: string[]; 
    narrative_report: string; 
    charts: any[]; 
    anomalies: any[]; 
    key_statistics: Record<string, string | number>; 
    preview_rows?: Record<string, any>[]; 
    processed_at: string; 
}

// --- ORGANIZATION ---
export interface Organization {
    id: string;
    name: string;
    owner_id: string;
    tier: 'TIER_1' | 'TIER_2';
    plan: string; // STARTUP, GROWTH, etc.
    status: string;
    expiry?: string;
    seat_limit: number;
    seat_count: number;
    created_at: string;
    owner_email?: string;
}