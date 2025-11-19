// FILE: src/data/types.ts
export type ConnectionStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'ERROR';

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'USER' | 'ADMIN' | 'LAWYER' | 'STANDARD';
  subscription_status: 'ACTIVE' | 'INACTIVE' | 'TRIAL' | 'EXPIRED' | 'expired';
}

// Inherit from User but ensure it has the fields expected by AdminDashboard
export interface AdminUser extends User {
  case_count?: number;
  document_count?: number;
  last_login?: string;
  created_at?: string;
}

export interface Case {
  id: string;
  owner_id: string;
  case_name: string;
  status: 'OPEN' | 'PENDING' | 'CLOSED' | 'ARCHIVED';
  created_at: string;
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
  error_message?: string;
}

export interface Finding {
  id: string;
  case_id: string;
  document_id?: string | number;
  finding_text: string;
  source_text?: string;
  document_name?: string;
  page_number?: number;
  confidence_score?: number;
  created_at?: string;
}

export interface ChatMessage {
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
  notes?: string;
  is_all_day?: boolean;
  location?: string;
  attendees?: string[];
  priority?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | string;
  description?: string;
  event_type?: 'DEADLINE' | 'HEARING' | 'MEETING' | 'FILING' | 'COURT_DATE' | 'CONSULTATION' | string;
  case_id?: string;
}

export interface CalendarEventCreateRequest {
  title: string;
  start_date: string;
  end_date?: string;
  notes?: string;
  is_all_day?: boolean;
  location?: string;
  attendees?: string[];
  priority?: string;
  description?: string;
  event_type?: string;
  case_id?: string;
}

export interface CreateDraftingJobRequest {
  context: string;
}

export interface DraftingJobStatus {
  job_id: string;
  status: string;
  result_summary?: string;
}

export interface DraftingJobResult {
  result_text: string;
}

export interface ApiKey {
  id: string;
  key_name: string;
  provider?: string;     // Added for AccountPage
  usage_count?: number;  // Added for AccountPage
}

export interface ApiKeyCreateRequest {
  key_name: string;
  api_key: string;
  provider?: 'openai' | 'anthropic'; // Added for AccountPage
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password?: string; // Added for AccountPage
}

export interface LoginRequest { 
  username: string; 
  password?: string; // Added to fix AuthPage error
}

export interface RegisterRequest { 
  username: string;
  password?: string; // Added to fix AuthPage error
  email?: string;
}

export interface CreateCaseRequest { case_name: string; }

export interface UpdateUserRequest { 
  email?: string;
  role?: User['role']; // Added for AdminDashboard
  subscription_status?: User['subscription_status']; // Added for AdminDashboard
}

export interface DeletedDocumentResponse { 
    documentId: string;
    deletedFindingIds?: string[]; 
}