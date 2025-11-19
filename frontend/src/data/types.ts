// FILE: frontend/src/data/types.ts
// PHOENIX PROTOCOL - LEGACY COMPATIBILITY RESTORED
// 1. Restored 'Finding', 'client', 'notes', 'is_all_day', 'result_summary'.
// 2. Expanded ChatMessage to support old 'text' property and 'AI' sender.

export type ConnectionStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'ERROR';

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'USER' | 'ADMIN';
  subscription_status: 'ACTIVE' | 'INACTIVE' | 'TRIAL' | 'EXPIRED';
}

export interface Case {
  id: string;
  owner_id: string;
  case_name: string;
  status: 'OPEN' | 'PENDING' | 'CLOSED' | 'ARCHIVED';
  created_at: string;
  // FIXED: Restored client object for CaseViewPage
  client?: {
    name: string | null;
    email?: string | null;
    phone?: string | null;
  };
}

export interface Document {
  id: string;
  case_id: string;
  file_name: string;
  mime_type: string;
  created_at: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'READY';
  summary?: string;
  error_message?: string; // Phoenix field
}

// FIXED: Restored Finding interface for CaseViewPage
export interface Finding {
  id: string;
  case_id: string;
  finding_text: string;
  source_text?: string;
  document_name?: string;
  page_number?: number;
  confidence_score?: number;
  created_at?: string;
}

export interface ChatMessage {
  // FIXED: Allow 'AI' (uppercase) and 'text' property for legacy UI compatibility
  sender: 'user' | 'ai' | 'AI'; 
  content: string;
  text?: string; 
  timestamp: string;
  isPartial?: boolean;
}

export interface CalendarEvent {
  id: string;
  title: string;
  start_date: string;
  end_date?: string;
  // FIXED: Restored fields for CalendarPage
  notes?: string;
  is_all_day?: boolean;
  location?: string;
  attendees?: string[];
}

export interface CalendarEventCreateRequest {
  title: string;
  start_date: string;
  end_date?: string;
  notes?: string;
  is_all_day?: boolean;
  location?: string;
  attendees?: string[];
}

export interface CreateDraftingJobRequest {
  context: string;
}

export interface DraftingJobStatus {
  job_id: string;
  status: string;
  // FIXED: Restored result_summary for DraftingPage
  result_summary?: string;
}

export interface DraftingJobResult {
  result_text: string;
}

export interface ApiKey {
  id: string;
  key_name: string;
}

export interface ApiKeyCreateRequest {
  key_name: string;
  api_key: string;
}

export interface ChangePasswordRequest {
  old_password: string;
}

export interface LoginRequest { username: string; }
export interface RegisterRequest { username: string; }
export interface CreateCaseRequest { case_name: string; }
export interface UpdateUserRequest { email?: string; }

export interface DeletedDocumentResponse { 
    documentId: string;
    // FIXED: Restored deletedFindingIds for CaseViewPage
    deletedFindingIds?: string[]; 
}