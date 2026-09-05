// FILE: frontend/src/services/forensicService.ts
// PHOENIX PROTOCOL - FORENSIC & COMPREHENSIVE CASE ANALYSIS MICRO-SERVICE V1.1 (CLEAN ZERO-COLLISION TYPING)

import { apiClient } from './apiClient';
import type {
  CaseAnalysisResult,
  DeepAnalysisResult
} from '../data/types';

import type {
  ForensicSpreadsheetAnalysisResult,
  ForensicInterrogationResponse
} from './caseService';

export class ForensicService {
  // =========================================================================
  // 🏛️ 1. ANALIZA E PLOTË E LËNDËS (COMPREHENSIVE CASE ANALYSIS)
  // =========================================================================

  public async analyzeCase(
    caseId: string, 
    clientPosition?: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL', 
    force?: boolean
  ): Promise<CaseAnalysisResult & { cached?: boolean; message?: string; latest_deep_analysis?: DeepAnalysisResult }> {
    const params: any = {};
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
}

export const forensicService = new ForensicService();