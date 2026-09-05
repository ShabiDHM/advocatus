// FILE: frontend/src/services/forensicService.ts
// PHOENIX PROTOCOL - FORENSIC & COMPREHENSIVE CASE ANALYSIS MICRO-SERVICE V3.0
// FULL MULTIMODAL INTEGRATION & 3-PILLAR MONGO ATLAS PERSISTENCE • ZERO TS WARNINGS • 100% COMPLETE

import { apiClient } from './apiClient';
import type {
  CaseAnalysisResult,
  DeepAnalysisResult
} from '../data/types';

import type {
  ForensicSpreadsheetAnalysisResult,
  ForensicInterrogationResponse
} from './caseService';

// =========================================================================
// 🎙️ & 🎬 TIPA PËR PROVAT AUDIO / VIDEO & EXIF FORENZIKE
// =========================================================================

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
  // =========================================================================
  // 🏛️ 1. ANALIZA E PLOTË E LËNDËS & SHTJELLAT PERSISTENTE NË MONGO ATLAS
  // =========================================================================

  public async saveCasePillar(caseId: string, pillarKey: string, content: string): Promise<{ status: string; message: string }> {
    const response = await apiClient.put<{ status: string; message: string }>(`/chat/case/${caseId}/pillars`, {
      pillar_key: pillarKey,
      content
    });
    return response.data;
  }

  public async saveDocumentPillar(caseId: string, documentId: string, pillarKey: string, content: string): Promise<{ status: string; message: string }> {
    const response = await apiClient.put<{ status: string; message: string }>(`/chat/case/${caseId}/documents/${documentId}/pillars`, {
      pillar_key: pillarKey,
      content
    });
    return response.data;
  }

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

  // =========================================================================
  // ⚖️ 2. AUDITIMI I DOKUMENTIT TË VETËM (SINGLE-DOCUMENT FORENSIC AUDIT)
  // =========================================================================

  public async clearDocumentAudit(caseId: string, documentId: string): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/documents/${documentId}/clear-audit`);
    return response.data;
  }

  public async crossExamineDocument(caseId: string, documentId: string): Promise<CaseAnalysisResult> {
    const response = await apiClient.post<CaseAnalysisResult>(`/cases/${caseId}/documents/${documentId}/cross-examine`);
    return response.data;
  }

  // =========================================================================
  // 🔬 3. STRATEGJIA E THELLË & SIMULIMI DOKTRINAR
  // =========================================================================

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
  // 💶 4. FORENZIKA FINANCIARE & INTERROGIMI I PROVAVE
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
  // 🎙️ & 🎬 5. MEDIA FORENSICS (AUDIO WHISPER, VIDEO CCTV, EXIF/GPS)
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