// FILE: /home/user/advocatus-frontend/src/data/types.ts
// PHOENIX PROTOCOL MODIFICATION 11.0 (ARCHITECTURAL DATA CONTRACT REFACTOR):
// 1. CRITICAL FIX: The 'Document' interface has been completely refactored to serve as a
//    definitive, single source of truth, perfectly mirroring the backend's data model.
// 2. DATA MODEL CORRECTION: Added the missing `mime_type: string;` property, which will
//    resolve the TypeScript error in `DocumentViewPage.tsx`.
// 3. ARCHITECTURAL CLEANUP: Removed all redundant, legacy, and incorrectly cased fields
//    (e.g., 'name', 'type', 'caseId', 'file_type') and standardized all property names to
//    match the backend's snake_case convention (e.g., 'case_id', 'created_at').
//
// PHOENIX PROTOCOL MODIFICATION 10.0 (FRONTEND STATE MACHINE ALIGNMENT)
// ...

export interface User {
  id: string;
  username: string;
  token: string;
  role?: 'LAWYER' | 'ADMIN' | 'STANDARD';
  email?: string;
}

export interface Case {
  id: string;
  name: string;
  client: { name: string | null; email: string | null; phone: string | null; } | null;
  status: 'OPEN' | 'PENDING' | 'Open' | 'Closed' | 'Archived' | 'active';
  created_at: string;
  document_count: number;
  alert_count: number;
  event_count: number;
}

export interface Finding {
    id: string;
    document_id: string;
    summary: string;
    case_id: string;
    created_at: string;
    status: 'DRAFT' | 'REVIEW' | 'FINAL' | 'PENDING';
}


export interface CalendarEvent {
  id: string;
  case_id: string;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  is_all_day: boolean;
  event_type: 'DEADLINE' | 'HEARING' | 'MEETING' | 'FILING' | 'COURT_DATE' | 'CONSULTATION' | 'OTHER';
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'PENDING' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED';
  location?: string;
  attendees?: string[];
  notes?: string;
  case?: { title: string; case_number: string; };
}

export interface CalendarEventCreateRequest {
  case_id: string;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  event_type: CalendarEvent['event_type'];
  priority: CalendarEvent['priority'];
  location?: string;
  attendees?: string[];
  is_all_day: boolean;
  notes?: string;
}

// --- PHOENIX PROTOCOL: Definitive, architecturally sound Document interface ---
export interface Document {
  id: string;
  _id?: string;
  case_id: string;
  file_name: string;
  mime_type: string; // The newly added, correct field
  created_at: string; // Standardized field name
  status: 'PENDING' | 'READY' | 'FAILED';
  summary?: string;
  processed_timestamp?: string;
}

export interface ChatMessage { sender: 'user' | 'AI'; text: string; timestamp: string; }
export interface WebSocketMessage { type: string; payload: any; }
export interface LoginRequest { username: string; password: string; }
export interface RegisterRequest extends LoginRequest { email: string; }

export interface CreateCaseRequest {
  case_name: string;
  case_number?: string;
  clientName: string;
  clientEmail?: string;
  clientPhone?: string;
}

export interface CreateDraftingJobRequest { caseId?: string; documentIds?: string[]; prompt?: string; context: string; }
export interface DraftingJobStatus { id: string; jobId: string; status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'SUCCESS' | 'FAILURE'; error?: string; }
export interface ChangePasswordRequest { old_password: string; new_password: string; }

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: 'LAWYER' | 'ADMIN' | 'STANDARD';
  created_at: string;
  last_login?: string;
  subscription_status: 'ACTIVE' | 'INACTIVE' | 'TRIAL' | 'expired';
  case_count?: number;
  document_count?: number;
}

export interface UpdateUserRequest {
  email?: string;
  role?: 'LAWYER' | 'ADMIN' | 'STANDARD';
  subscription_status?: 'ACTIVE' | 'INACTIVE' | 'TRIAL' | 'expired';
}

export interface ApiKey {
    id: string;
    provider: 'openai' | 'anthropic' | 'google';
    key_name: string;
    is_active: boolean;
    last_used: string | null;
    usage_count: number;
}

export interface ApiKeyCreateRequest {
    provider: 'openai' | 'anthropic' | 'google';
    key_name: string;
    api_key: string;
}