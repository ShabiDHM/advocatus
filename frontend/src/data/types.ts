// FILE: frontend/src/data/types.ts
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
}

export interface Document {
  id: string;
  case_id: string;
  file_name: string;
  mime_type: string;
  created_at: string;
  status: 'PENDING' | 'COMPLETED' | 'FAILED' | 'READY';
  summary?: string;
  error_message?: string; // Added for Phoenix Protocol
}

export interface ChatMessage {
  sender: 'user' | 'ai';
  content: string;
  timestamp: string;
  isPartial?: boolean;
}

// --- Basic placeholders for other types to prevent errors ---
export interface CalendarEvent { id: string; title: string; start_date: string; }
export interface CalendarEventCreateRequest { title: string; start_date: string; }
export interface CreateDraftingJobRequest { context: string; }
export interface DraftingJobStatus { job_id: string; status: string; }
export interface DraftingJobResult { result_text: string; }
export interface ApiKey { id: string; key_name: string; }
export interface ApiKeyCreateRequest { key_name: string; api_key: string; }
export interface ChangePasswordRequest { old_password: string; }
export interface LoginRequest { username: string; }
export interface RegisterRequest { username: string; }
export interface CreateCaseRequest { case_name: string; }
export interface UpdateUserRequest { email?: string; }
export interface DeletedDocumentResponse { documentId: string; }