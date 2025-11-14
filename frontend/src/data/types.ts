// FILE: src/data/types.ts
// PHOENIX PROTOCOL MODIFICATION 47.0 (TYPE INTEGRITY CURE)
// 1. CHAT MESSAGE ENHANCEMENT: Added the optional 'isPartial' property to the
//    ChatMessage interface. This makes the data contract explicit for streaming
//    AI responses, resolving the TS2353 build error.

export type ConnectionStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'ERROR';

export interface User {
  id: string;
  username: string;
  token: string;
  role?: 'LAWYER' | 'ADMIN' | 'STANDARD';
  email?: string;
}

export interface Case {
  id: string;
  owner_id: string;
  case_name: string;
  client: { name: string | null; email: string | null; phone: string | null; } | null;
  status: 'OPEN' | 'PENDING' | 'Open' | 'Closed' | 'Archived' | 'active';
  created_at: string;
  document_count: number;
  alert_count: number;
  event_count: number;
  finding_count: number;
}

export interface Finding {
    id: string;
    case_id: string;
    finding_text: string;
    document_id: string;
    document_name?: string;
    source_text?: string;
    page_number?: number | null;
    confidence_score?: number;
    created_at?: string;
    status?: 'DRAFT' | 'REVIEW' | 'FINAL' | 'PENDING';
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

export interface Document {
  id: string;
  _id?: string;
  case_id: string;
  file_name: string;
  mime_type: string;
  created_at: string;
  status: 'PENDING' | 'READY' | 'FAILED';
  summary?: string;
  processed_timestamp?: string;
}

export interface ChatMessage {
  sender: 'user' | 'AI';
  text: string;
  timestamp: string;
  isPartial?: boolean; // This property is now part of the official type
}

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
export interface DraftingJobStatus {
  id?: string;
  job_id: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'SUCCESS' | 'FAILURE';
  error?: string;
  result_summary?: string;
}
export interface DraftingJobResult {
  result_text: string;
}
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
  role?: 'LAWY-ER' | 'ADMIN' | 'STANDARD';
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