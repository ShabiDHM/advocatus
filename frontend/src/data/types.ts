// FILE: src/data/types.ts
// PHOENIX PROTOCOL - TOTAL SYSTEM SYNCHRONIZATION V28.4
// 1. RESTORED: All 15+ missing interfaces required by api.ts and pages.
// 2. INTEGRATED: Dual-Persona AI fields (burden_of_proof, missing_evidence).
// 3. FIX: CreateCaseRequest and CreateDraftingJobRequest property alignment.
// 4. STATUS: Unabridged replacement.

import { AccountType, SubscriptionTier, ProductPlan } from './enums';

export type ConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';

// --- 1. USER & AUTHENTICATION ---
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
    last_login?: string;
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

// --- 2. THE GUARDIAN (RISK RADAR) ---
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

// --- 3. BUSINESS & PROFILE ---
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

// --- 4. CASE MANAGEMENT & LEGAL ANALYSIS ---
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
    status?: string; // FIXED: Added back for DashboardPage compatibility
}

export interface CaseAnalysisResult { 
    summary?: string; 
    key_issues?: string[]; 
    legal_basis?: (string | { law?: string; article?: string; relevance?: string; title?: string; argument?: string })[]; 
    strategic_analysis?: string; 
    weaknesses?: string[]; 
    action_plan?: string[]; 
    risk_level?: string; 
    success_probability?: string;
    burden_of_proof?: string; // NEW DUAL-PERSONA FIELD
    missing_evidence?: string[]; // NEW DUAL-PERSONA FIELD
    red_flags?: string[]; 
    contradictions?: string[]; 
    chronology?: ChronologyEvent[]; 
    error?: string; 
}

// --- 5. DOCUMENTS & ARCHIVE ---
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
    progress_percent?: number; 
    is_shared?: boolean; 
}

export interface DeletedDocumentResponse { 
    documentId: string; 
    deletedFindingIds: string[]; 
}

export interface ArchiveItemOut { 
    id: string; 
    title: string; 
    file_type: string; 
    category: string; 
    storage_key: string; 
    file_size: number; 
    created_at: string; 
    item_type?: 'FILE' | 'FOLDER'; 
    is_shared?: boolean; 
}

// --- 6. CALENDAR & DEADLINES ---
export interface CalendarEvent { 
    id: string; 
    title: string; 
    description?: string; 
    start_date: string; 
    end_date: string; 
    is_all_day: boolean; 
    event_type: 'APPOINTMENT' | 'TASK' | 'PAYMENT_DUE' | 'TAX_DEADLINE' | 'PERSONAL' | 'OTHER'; 
    category: 'AGENDA' | 'FACT'; 
    status: 'PENDING' | 'COMPLETED' | 'CANCELLED' | 'OVERDUE' | 'ARCHIVED'; 
    case_id?: string; 
    priority?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'; 
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

// --- 7. FINANCE & ANALYTICS ---
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
    total_amount: number; 
    status: 'DRAFT' | 'SENT' | 'PAID' | 'PENDING' | 'OVERDUE' | 'CANCELLED'; 
    issue_date: string; 
    due_date: string; 
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
}

export interface ExpenseCreateRequest { 
    category: string; 
    amount: number; 
    description?: string; 
    date?: string; 
    related_case_id?: string; 
}

export interface ExpenseUpdate { 
    category?: string; 
    amount?: number; 
    description?: string; 
    date?: string; 
    related_case_id?: string; 
}

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
    top_products: any[]; 
    total_profit_period?: number; 
}

// --- 8. FORENSIC ANALYSIS ---
export interface EnhancedAnomaly {
    date: string; 
    amount: number; 
    description: string;
    risk_level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL'; 
    explanation: string;
}

export interface SpreadsheetAnalysisResult { 
    filename: string; 
    record_count: number; 
    narrative_report: string; 
    anomalies: EnhancedAnomaly[]; 
    processed_at: string; 
}

// --- 9. LEGAL STRATEGY (WAR ROOM) ---
export interface ChronologyEvent { date: string; event: string; source?: string; }
export interface AdversarialSimulation { opponent_strategy: string; weakness_attacks: string[]; counter_claims: string[]; }
export interface Contradiction { claim: string; evidence: string; severity: 'HIGH' | 'MEDIUM' | 'LOW'; impact: string; }

export interface DeepAnalysisResult { 
    adversarial_simulation: AdversarialSimulation; 
    chronology: ChronologyEvent[]; 
    contradictions: Contradiction[]; 
    error?: string; 
}

// --- 10. ORGANIZATIONS & SaaS ---
export interface Organization { 
    id: string; 
    name: string; 
    owner_id: string; 
    tier: 'TIER_1' | 'TIER_2'; 
    seat_limit: number; 
    seat_count: number; 
    created_at: string; 
}

export interface SubscriptionUpdate { status: string; expiry_date?: string; plan_tier?: string; }
export interface PromoteRequest { firm_name: string; plan_tier: string; }

// --- 11. CHAT & DRAFTING ---
export interface ChatMessage { role: 'user' | 'ai'; content: string; timestamp: string; }

export interface CreateDraftingJobRequest { 
    user_prompt: string; 
    case_id?: string; 
    draft_type?: string; 
    document_type?: string; // FIXED: Added back for DraftingPage compatibility
    use_library?: boolean; 
}

export interface DraftingJobStatus { 
    job_id: string; 
    status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'; 
    error?: string; 
}

export interface DraftingJobResult { 
    document_text: string; 
    job_id?: string; 
    status?: string; 
}

// --- 12. KNOWLEDGE GRAPH ---
export interface GraphNode { id: string; name: string; group: string; val: number; }
export interface GraphLink { source: string; target: string; label: string; }
export interface GraphData { nodes: GraphNode[]; links: GraphLink[]; }