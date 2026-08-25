// FILE: src/drafting/types.ts
// ARCHITECTURE: CORE TYPE DEFINITIONS FOR HAVERI AI / ADVOKATUS

import { TFunction } from 'i18next';
import { Case } from '../data/types';

export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

// Closed union type: Template definitions across civil, corporate, and criminal law
export type TemplateType =
  | 'generic' 
  | 'padi' | 'pergjigje' | 'kunderpadi' | 'ankese' | 'prapësim'
  | 'kallezim_penal'
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
  structureInstructions: string;   // The internal prompt matrix
  placeholder: string;             // UI Hint for the user
  label: string;                   // UI Display name
}

export interface ConfigPanelProps {
  t: TFunction;
  isPro: boolean;
  cases: Case[];
  selectedCaseId: string | undefined; // Allowed to be undefined when no case is selected
  selectedTemplate: TemplateType;
  context: string;
  isSubmitting: boolean;
  onSelectCase: (id: string | undefined) => void;
  onSelectTemplate: (val: TemplateType) => void;
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
  selectedCaseId: string | undefined;
  saveModalOpen: boolean;
  setSaveModalOpen: (open: boolean) => void;
}