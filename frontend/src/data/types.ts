// FILE: frontend/src/data/types.ts
// PHOENIX PROTOCOL - TYPE DEFINITION FIX (CHAT PERSISTENCE)
// 1. Added 'chat_history' to Case interface to support persistent chat.
// 2. Maintained 'AdminUser' alias and all other strict types.

export type ConnectionStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'ERROR';

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'USER' | 'ADMIN';
  subscription_status: 'ACTIVE' | 'INACTIVE' | 'TRIAL' | 'EXPIRED';
  created_at: string;
  last_login?: string;
  token?: string;
  case_count?: number;
  document_count?: number;
}

// PHOENIX FIX: Alias AdminUser to User to satisfy legacy imports
export type AdminUser = User;

export interface ChatMessage {
  sender: 'user' | 'ai';
  content: string;
  // PHOENIX FIX: Added optional 'text' to prevent ChatPanel build errors.
  text?: string; 
  timestamp: string;
  isPartial?: boolean;
}

export interface Case {
  id: string;
  owner_id: string;
  case_name: string;
  client: { name: string | null; email: string | null; phone: string | null; } | null;
  status: 'OPEN' | 'PENDING' | 'CLOSED' | 'ARCHIVED';
  created_at: string;
  document_count: number;
  alert_count: number;
  event_count: number;
  finding_count: number;
  // PHOENIX FIX: Added chat_history for persistence
  chat_history?: ChatMessage[];
}

export interface Document {
  id: string;
  case_id: string;
  file_name: string;
  mime_type: string;
  created_at: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'READY';
  summary?: string;
  error_message?: string;
}

export interface Finding {
  id: string;
  case_id: string;
  document_id: string; 
  finding_text: string;
  source_text: string;
  page_number?: number;
  document_name?: string;
  confidence_score?: number;
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
}

export interface CalendarEventCreateRequest {
  case_id: string;
  title: string;
  start_date: string;
  event_type: CalendarEvent['event_type'];
  priority: CalendarEvent['priority'];
  description?: string;
  end_date?: string;
  is_all_day?: boolean;
  location?: string;
  attendees?: string[];
  notes?: string;
}

export interface CreateDraftingJobRequest {
  caseId?: string;
  documentIds?: string[];
  prompt?: string;
  context: string;
}

export interface DraftingJobStatus {
  job_id: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'SUCCESS' | 'FAILURE';
  result_summary?: string;
}

export interface DraftingJobResult {
    result_text: string;
}

export interface WebSocketMessage {
  event: string;
  data: any;
}

export interface DeletedDocumentResponse {
  documentId: string;
  deletedFindingIds: string[];
}

// --- API Key & Account Management Types ---

export interface ApiKey {
    id: string;
    key_name: string;
    provider: string;
    key_prefix: string;
    created_at: string;
    last_used?: string;
    usage_count: number;
}

export interface ApiKeyCreateRequest {
    key_name: string;
    provider: 'openai' | 'anthropic';
    api_key: string;
}

export interface ChangePasswordRequest {
    old_password: string;
    new_password: string;
}

// --- Auth Types ---

export interface LoginRequest { username: string; password: string; }
export interface RegisterRequest extends LoginRequest { email: string; }
export interface CreateCaseRequest {
  case_name: string;
  clientName: string;
  clientEmail?: string;
  clientPhone?: string;
}

export interface UpdateUserRequest {
  email?: string;
  role?: User['role'];
  subscription_status?: User['subscription_status'];
}