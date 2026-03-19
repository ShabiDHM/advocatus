// src/drafting/types.ts
import { TFunction } from 'i18next';
import { Case } from '../data/types';

export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export type TemplateType =
  | 'generic' | 'padi' | 'pergjigje' | 'kunderpadi' | 'ankese' | 'prapësim'
  | 'nda' | 'mou' | 'shareholders' | 'sla'
  | 'employment_contract' | 'termination_notice' | 'warning_letter'
  | 'terms_conditions' | 'privacy_policy'
  | 'lease_agreement' | 'sales_purchase'
  | 'power_of_attorney';

export interface DraftingJobState {
  status: JobStatus | null;
  result: string | null;
  error: string | null;
}

export interface NotificationState {
  msg: string;
  type: 'success' | 'error';
}

export interface TemplateConfig {
  structureInstructions: string;   // the format guidelines for the AI
  placeholder: string;             // example prompt for the user
  label: string;                   // display name (may be translated later)
}

// Props for subcomponents
export interface ConfigPanelProps {
  t: TFunction;
  isPro: boolean;
  cases: Case[];
  selectedCaseId: string;
  selectedTemplate: TemplateType;
  context: string;
  isSubmitting: boolean;
  onSelectCase: (id: string) => void;
  onSelectTemplate: (val: string) => void;
  onChangeContext: (val: string) => void;
  onSubmit: () => void;
}

export interface ResultPanelProps {
  t: TFunction;
  currentJob: DraftingJobState;
  saving: boolean;
  notification: NotificationState | null;
  onSave: () => void;
  onSaveToCase: (title: string) => Promise<void>;
  onRetry: () => void;
  onClear: () => void;
  selectedCaseId: string;
  saveModalOpen: boolean;
  setSaveModalOpen: (open: boolean) => void;
}