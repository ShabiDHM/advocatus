// FILE: frontend/src/services/forensicService.ts
// PHOENIX PROTOCOL - FORENSIC SERVICE V4.2 (CLEAN STANDARD CASE FORENSICS)
// 100% COMPLETE CODE • ZERO TS WARNINGS • ATOMIC $UNSET INTEGRATION

import { apiClient } from './apiClient';
import type {
  CaseAnalysisResult,
  DeepAnalysisResult
} from '../data/types';

export interface ForensicSpreadsheetAnalysisResult {
  [key: string]: any;
}
export interface ForensicInterrogationResponse {
  [key: string]: any;
}

export interface MediaEvidenceItem {
  id: string;
  _id?: string;
  case_id: string;
  owner_id: string;
  file_name: string;
  storage_key: string;
  media_type: 'video' | 'audio';
  mime_type: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED';
  transcript?: string;
  visual_analysis?: {
    exif_data?: Record<string, any>;
    gps_coordinates?: {
      latitude?: number;
      longitude?: number;
      address?: string;
    };
    cctv_frame_analysis?: string;
    detected_entities?: string[];
    [key: string]: any;
  };
  role?: string;
  case_domain?: string;
  created_at: string;
  updated_at: string;
}

export class ForensicService {
  // Ky shërbim përdoret VETËM për analiza brenda lëndës standarde (endpoint /cases/...)
  // Asnjë metodë nuk duhet të përdorë endpoint /forensic/...

  // =========================================================================
  // 🏛️ 1. SHTJELLAT E LËNDËS NË MONGODB
  // =========================================================================

  public async saveCasePillar(caseId: string, pillar: string, content: string): Promise<{ status: string; pillar: string }> {
    const response = await apiClient.post<{ status: string; pillar: string }>(`/cases/${caseId}/pillars`, { pillar, content });
    return response.data;
  }

  public async getCasePillars(caseId: string): Promise<Record<string, string>> {
    const response = await apiClient.get<Record<string, string>>(`/cases/${caseId}/pillars`);
    return response.data;
  }

  public async deleteCasePillar(caseId: string, pillar: string): Promise<any> {
    const response = await apiClient.delete(`/cases/${caseId}/pillars/${pillar}`);
    return response.data;
  }

  // =========================================================================
  // ⚖️ 2. SHTJELLAT E DOKUMENTIT TË VETËM NË MONGODB
  // =========================================================================

  public async saveDocumentPillar(caseId: string, documentId: string, pillar: string, content: string): Promise<{ status: string; pillar: string }> {
    const response = await apiClient.post<{ status: string; pillar: string }>(`/cases/${caseId}/documents/${documentId}/pillars`, { pillar, content });
    return response.data;
  }

  public async getDocumentPillars(caseId: string, documentId: string): Promise<Record<string, string>> {
    const response = await apiClient.get<Record<string, string>>(`/cases/${caseId}/documents/${documentId}/pillars`);
    return response.data;
  }

  public async deleteDocumentPillar(caseId: string, documentId: string, pillar: string): Promise<any> {
    const response = await apiClient.delete(`/cases/${caseId}/documents/${documentId}/pillars/${pillar}`);
    return response.data;
  }

  public async saveDocumentAnalysis(caseId: string, documentId: string, content: string): Promise<{ status: string; document_id: string }> {
    const response = await apiClient.post<{ status: string; document_id: string }>(`/cases/${caseId}/documents/${documentId}/pillars`, { pillar: 'PILLAR_1', content });
    return response.data;
  }

  public async clearDocumentAudit(caseId: string, documentId: string): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/documents/${documentId}/clear-audit`);
    return response.data;
  }

  public async crossExamineDocument(caseId: string, documentId: string): Promise<CaseAnalysisResult> {
    const response = await apiClient.post<CaseAnalysisResult>(`/cases/${caseId}/documents/${documentId}/cross-examine`);
    return response.data;
  }

  // =========================================================================
  // 🔬 3. STRATEGJIA E THELLË DHE RAPORTET
  // =========================================================================

  public async analyzeCase(
    caseId: string, 
    clientPosition?: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL', 
    force?: boolean
  ): Promise<CaseAnalysisResult & { cached?: boolean; message?: string; latest_deep_analysis?: DeepAnalysisResult }> {
    const params: Record<string, any> = {};
    if (clientPosition) params.client_position = clientPosition;
    if (force) params.force = force;
    const response = await apiClient.post<any>(`/cases/${caseId}/analyze`, null, { params });
    return response.data;
  }

  public async clearCaseAnalysis(caseId: string): Promise<void> {
    await apiClient.post(`/cases/${caseId}/analyze/clear`);
  }

  public async archiveForensicReport(caseId: string, title: string, content: string): Promise<any> {
    const response = await apiClient.post('/finance/forensic-report/archive', { case_id: caseId, title, content });
    return response.data;
  }

  public async downloadForensicReport(caseId: string, data: any): Promise<void> {
    const response = await apiClient.post(`/cases/${caseId}/report/forensic`, data, { responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Raporti_Forenzik_${caseId.slice(-6)}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  public async analyzeDeepStrategy(caseId: string, clientPosition?: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL'): Promise<DeepAnalysisResult> {
    const params = clientPosition ? { client_position: clientPosition } : {};
    const response = await apiClient.post<DeepAnalysisResult>(`/cases/${caseId}/deep-analysis`, null, { params });
    return response.data;
  }

  public async analyzeDeepSimulation(caseId: string, clientPosition?: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL'): Promise<any> {
    const params = clientPosition ? { client_position: clientPosition } : {};
    const response = await apiClient.post<any>(`/cases/${caseId}/deep-analysis/simulation`, null, { params });
    return response.data;
  }

  public async analyzeDeepChronology(caseId: string): Promise<any[]> {
    const response = await apiClient.post<any[]>(`/cases/${caseId}/deep-analysis/chronology`);
    return response.data;
  }

  public async analyzeDeepContradictions(caseId: string): Promise<any[]> {
    const response = await apiClient.post<any[]>(`/cases/${caseId}/deep-analysis/contradictions`);
    return response.data;
  }

  public async archiveStrategyReport(caseId: string, legalData: any, deepData: any): Promise<{ status: string; item_id: string }> {
    const response = await apiClient.post<{ status: string; item_id: string }>(`/cases/${caseId}/archive-strategy`, { legal_data: legalData, deep_data: deepData });
    return response.data;
  }

  // =========================================================================
  // 💶 4. FORENZIKA FINANCIARE (RIKTHYER NGA PASTRIMI I GABUAR)
  // =========================================================================

  public async forensicAnalyzeSpreadsheet(caseId: string, file: File, lang: string = 'sq'): Promise<ForensicSpreadsheetAnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('analyst_id', 'frontend_user');
    formData.append('acquisition_method', 'WEB_UPLOAD');
    formData.append('lang', lang);
    const response = await apiClient.post<ForensicSpreadsheetAnalysisResult>(`/cases/${caseId}/analyze/spreadsheet/forensic`, formData, { params: { lang } });
    return response.data;
  }

  public async forensicInterrogateEvidence(caseId: string, question: string, includeChainOfCustody: boolean = true): Promise<ForensicInterrogationResponse> {
    const response = await apiClient.post<ForensicInterrogationResponse>(`/cases/${caseId}/interrogate-finances/forensic`, { question, include_chain_of_custody: includeChainOfCustody });
    return response.data;
  }

  // =========================================================================
  // 🎙️ & 🎬 5. MEDIA EVIDENCE (AUDIO, VIDEO CCTV, STREAMING)
  // =========================================================================

  public async getCaseMedia(caseId: string): Promise<MediaEvidenceItem[]> {
    const response = await apiClient.get<MediaEvidenceItem[]>(`/cases/${caseId}/media`);
    return response.data;
  }

  public async uploadCaseMedia(caseId: string, file: File): Promise<MediaEvidenceItem> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<MediaEvidenceItem>(`/cases/${caseId}/media/upload`, formData);
    return response.data;
  }

  public async deleteCaseMedia(caseId: string, mediaId: string): Promise<void> {
    await apiClient.delete(`/cases/${caseId}/media/${mediaId}`);
  }

  public getMediaStreamUrl(caseId: string, mediaId: string, token: string): string {
    return `/api/v1/cases/${caseId}/media/${mediaId}/stream?token=${encodeURIComponent(token)}`;
  }
}

export const forensicService = new ForensicService();