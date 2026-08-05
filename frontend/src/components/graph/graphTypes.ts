// FILE: src/components/graph/graphTypes.ts
import { User, Building2, CreditCard, MapPin, Calendar, FileText, LucideIcon } from 'lucide-react';

export type EntityType = 'PERSON' | 'ORGANIZATION' | 'ACCOUNT' | 'LOCATION' | 'EVENT' | 'DOCUMENT';

export interface OntologyNode {
  id: string;
  label: string;
  type: EntityType;
  description?: string;
  source_doc_ids?: string[];
  metadata?: Record<string, any>;
}

export interface OntologyEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  amount_eur?: number | null;
  date_iso?: string;
  evidence_text?: string;
  source_doc_ids?: string[];
}

export interface CaseGraphData {
  case_id: string;
  nodes: OntologyNode[];
  edges: OntologyEdge[];
  updated_at?: string | null;
}

export interface ChatMsg {
  id: string;
  role: 'user' | 'ai';
  content: string;
}

export interface EvidenceGraphTabProps {
  caseId: string;
  caseTitle?: string;
}

export const ENTITY_CONFIG: Record<EntityType, { albanianLabel: string; bg: string; border: string; icon: LucideIcon }> = {
  PERSON: { albanianLabel: 'Persona', bg: '#2563eb', border: '#60a5fa', icon: User },
  ORGANIZATION: { albanianLabel: 'Institucione', bg: '#7c3aed', border: '#a78bfa', icon: Building2 },
  ACCOUNT: { albanianLabel: 'Llogari Bankare', bg: '#059669', border: '#34d399', icon: CreditCard },
  DOCUMENT: { albanianLabel: 'Dokumente & Provat', bg: '#4b5563', border: '#9ca3af', icon: FileText },
  LOCATION: { albanianLabel: 'Lokacione', bg: '#d97706', border: '#fbbf24', icon: MapPin },
  EVENT: { albanianLabel: 'Ngjarje / Seanca', bg: '#dc2626', border: '#f87171', icon: Calendar },
};