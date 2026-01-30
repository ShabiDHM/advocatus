// FILE: src/data/types.ts
// PHOENIX PROTOCOL - TOTAL SYSTEM SYNCHRONIZATION V23.1
// 1. INTEGRATED: Risk Radar (LEVEL_1_PREKLUZIV) logic for Malpractice prevention.
// 2. RESTORED: All Forensic, Financial, and Deep Case Analysis interfaces.
// 3. HARDENED: Unified identity fields with 'full_name' and 'RiskAlert' arrays.

import { AccountType, SubscriptionTier, ProductPlan } from './enums';

export type ConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';

// --- USER & AUTHENTICATION ---
export interface User { 
    id: string; 
    email: string; 
    username: string; 
    full_name?: string; 
    role: 'ADMIN' | 'LAWYER' | 'CLIENT' | 'STANDARD'; 
    organization_role?: 'OWNER' | 'MEMBER';
    status: 'active' | 'inactive'; 
    created_at: string; 
    token?: string; 
    
    // SaaS Matrix
    account_type: AccountType;
    subscription_tier: SubscriptionTier;
    product_plan: ProductPlan;
    subscription_status?: string; 
    subscription_expiry?: string; 
    
    business_profile?: BusinessProfile; 
}

export interface LoginRequest { username: string; password: string; }
export interface RegisterRequest { email: string; password: string; username: string; }
export interface ChangePasswordRequest { current_password: string; new_password: string; }

export interface UpdateUserRequest { 
    username?: string; 
    email?: string; 
    full_name?: string; 
    role?: string; 
    status?: 'active' | 'inactive';
    account_type?: AccountType;
    subscription_tier?: SubscriptionTier;
    product_plan?: ProductPlan;
}

export interface AcceptInviteRequest { token: string; username: string; password: string; }

// --- THE GUARDIAN: RISK RADAR ---
export interface RiskAlert {
    id: string;
    title: string;
    level: 'LEVEL_1_PREKLUZIV' | 'LEVEL_2_GJYQESOR' | 'LEVEL_3_PROCEDURAL';
    seconds_remaining: number;
    effective_deadline: string;
}

export interface BriefingResponse {
    count: number;
    greeting_key: string; 
    message_key: string;  
    status: 'OPTIMAL' | 'HOLIDAY' | 'WEEKEND' | 'WARNING' | 'CRITICAL';
    data: Record<string, any>;
    risk_radar: RiskAlert[];
}

// --- CASE MANAGEMENT & ANALYSIS ---
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

export interface CreateCaseRequest { 
    case_number: string; 
    title: string; 
    case_name?: string; 
    description?: string; 
    clientName?: string; 
    clientEmail?: string; 
    clientPhone?: string; 
    status?: string; 
}

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

export interface DeletedDocumentResponse { 
    documentId: string; 
    deletedFindingIds: string[]; 
}

// --- CALENDAR & LEGAL TRIAGE ---
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
    // Intelligence injection
    working_days_remaining?: number;
    risk_level?: string;
    effective_deadline?: string;
    is_extended?: boolean;
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

// --- FINANCE & FORENSIC MODULES ---
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

export interface InvoiceCreateRequest { 
    client_name: string; 
    client_email?: string; 
    client_address?: string; 
    items: InvoiceItem[]; 
    tax_rate: number; 
    due_date?: string; 
    notes?: string; 
    related_case_id?: string; 
    status?: string; 
}

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

export interface CaseFinancialSummary { 
    case_id: string; 
    case_title: string; 
    case_number: string; 
    total_billed: number; 
    total_expenses: number; 
    net_balance: number; 
}

export interface AnalyticsDashboardData { 
    total_revenue_period: number; 
    total_transactions_period: number; 
    sales_trend: Array<{ date: string; amount: number }>; 
    top_products: Array<{ product_name: string; total_quantity: number; total_revenue: number }>; 
    total_profit_period?: number; 
}

// --- FORENSIC ANALYSIS ---
export interface EnhancedAnomaly {
    date: string;
    amount: number;
    description: string;
    risk_level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
    explanation: string;
    forensic_type?: string;
    confidence?: number;
}

export interface ForensicMetadata {
    evidence_hash: string;
    analysis_timestamp: string;
    record_count: number;
}

export interface SpreadsheetAnalysisResult { 
    file_id?: string; 
    filename: string; 
    record_count: number; 
    columns: string[]; 
    narrative_report: string; 
    charts: any[]; 
    anomalies: EnhancedAnomaly[]; 
    key_statistics: Record<string, string | number>; 
    processed_at: string; 
    forensic_metadata?: ForensicMetadata;
}

// --- LEGAL STRATEGY & WAR ROOM ---
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
}

// --- ORGANIZATION & SaaS ---
export interface Organization { 
    id: string; 
    name: string; 
    owner_id: string; 
    tier: 'TIER_1' | 'TIER_2'; 
    plan: string; 
    status: string; 
    expiry?: string; 
    seat_limit: number; 
    seat_count: number; 
    created_at: string; 
}

export interface SubscriptionUpdate { status: string; expiry_date?: string; plan_tier?: string; }
export interface PromoteRequest { firm_name: string; plan_tier: string; }

// --- CHAT & DRAFTING ---
export interface ChatMessage { role: 'user' | 'ai'; content: string; timestamp: string; }
export interface CreateDraftingJobRequest { user_prompt: string; template_id?: string; case_id?: string; context?: string; draft_type?: string; }
export type DraftingJobStatus = { job_id: string; status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'; error?: string; };
export type DraftingJobResult = { document_text: string; document_html?: string; result_text?: string; job_id?: string; };

export interface BusinessProfile { 
    id: string; 
    firm_name: string; 
    address?: string; 
    branding_color: string; 
    logo_url?: string; 
    is_complete: boolean; 
}

export interface BusinessProfileUpdate { firm_name?: string; branding_color?: string; }