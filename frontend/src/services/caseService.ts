// FILE: src/services/caseService.ts
// PHOENIX PROTOCOL - CASE & FORENSIC ANALYSIS SERVICE MODULE

import { apiClient, API_V1_URL } from './apiClient';
import axios from 'axios';
import type {
  Case,
  CreateCaseRequest,
  Document,
  DeletedDocumentResponse,
  CaseAnalysisResult,
  DeepAnalysisResult,
  SpreadsheetAnalysisResult
} from '../data/types';

export interface ForensicMetadata {
  evidence_hash: string;
  analysis_timestamp: string;
  record_count: number;
}

export interface EnhancedAnomaly {
  date: string;
  amount: number;
  description: string;
  risk_level: 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';
  explanation: string;
  forensic_type?: string;
  legal_reference?: string;
  confidence?: number;
}

export interface ForensicSpreadsheetAnalysisResult {
  executive_summary: string;
  anomalies: EnhancedAnomaly[];
  trends: Array<{ category: string; trend: 'UP' | 'DOWN' | 'STABLE'; percentage: string; comment: string }>;
  recommendations: string[];
  forensic_metadata?: ForensicMetadata;
}

export interface ForensicInterrogationResponse {
  answer: string;
  referenced_rows_count?: number;
  supporting_evidence_count?: number;
  evidence_references?: string[];
  chain_of_custody?: any[];
  forensic_warning?: string;
  legal_disclaimer?: string;
}

interface DocumentContentResponse { text: string; }
interface ReprocessConfirmation { documentId: string; message: string; }
interface BulkReprocessResponse { count: number; message: string; }
interface MobileSessionResponse { upload_url: string; }
interface MobileUploadStatus { status: 'pending' | 'complete' | 'error'; data?: SpreadsheetAnalysisResult; message?: string; }
interface FinanceInterrogationResponse { answer: string; referenced_rows_count: number; }

export class CaseService {
  public async getCases(): Promise<Case[]> {
    const response = await apiClient.get<any>('/cases');
    return Array.isArray(response.data) ? response.data : (response.data.cases || []);
  }

  public async createCase(data: CreateCaseRequest): Promise<Case> {
    const response = await apiClient.post<Case>('/cases', data);
    return response.data;
  }

  public async getCaseDetails(caseId: string): Promise<Case> {
    const response = await apiClient.get<Case>(`/cases/${caseId}`);
    return response.data;
  }

  public async deleteCase(caseId: string): Promise<void> {
    await apiClient.delete(`/cases/${caseId}`);
  }

  public async updateCasePosition(caseId: string, position: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL'): Promise<void> {
    await apiClient.put(`/cases/${caseId}/position`, { client_position: position });
  }

  // ========== DOCUMENTS CRUD ==========
  public async getDocuments(caseId: string): Promise<Document[]> {
    const response = await apiClient.get<any>(`/cases/${caseId}/documents`);
    return Array.isArray(response.data) ? response.data : (response.data.documents || []);
  }

  public async uploadDocument(caseId: string, file: File, onProgress?: (percent: number) => void): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<Document>(`/cases/${caseId}/documents/upload`, formData, {
      onUploadProgress: (progressEvent: any) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      }
    });
    return response.data;
  }

  public async getDocument(caseId: string, documentId: string): Promise<Document> {
    const response = await apiClient.get<Document>(`/cases/${caseId}/documents/${documentId}`);
    return response.data;
  }

  public async deleteDocument(caseId: string, documentId: string): Promise<DeletedDocumentResponse> {
    const response = await apiClient.delete<DeletedDocumentResponse>(`/cases/${caseId}/documents/${documentId}`);
    return response.data;
  }

  public async bulkDeleteDocuments(caseId: string, documentIds: string[]): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/documents/bulk-delete`, { document_ids: documentIds });
    return response.data;
  }

  public async importArchiveDocuments(caseId: string, archiveItemIds: string[]): Promise<Document[]> {
    const response = await apiClient.post<Document[]>(`/cases/${caseId}/documents/import-archive`, { archive_item_ids: archiveItemIds });
    return response.data;
  }

  public async getDocumentContent(caseId: string, documentId: string): Promise<DocumentContentResponse> {
    const response = await apiClient.get<DocumentContentResponse>(`/cases/${caseId}/documents/${documentId}/content`);
    return response.data;
  }

  public async getOriginalDocument(caseId: string, documentId: string): Promise<Blob> {
    const response = await apiClient.get(`/cases/${caseId}/documents/${documentId}/original`, { responseType: 'blob' });
    return response.data;
  }

  public async getPreviewDocument(caseId: string, documentId: string): Promise<Blob> {
    const response = await apiClient.get(`/cases/${caseId}/documents/${documentId}/preview`, { responseType: 'blob' });
    return response.data;
  }

  public async downloadDocumentReport(caseId: string, documentId: string): Promise<Blob> {
    const response = await apiClient.get(`/cases/${caseId}/documents/${documentId}/report`, { responseType: 'blob' });
    return response.data;
  }

  public async downloadObjection(caseId: string, docId: string): Promise<void> {
    const response = await apiClient.get(`/cases/${caseId}/documents/${docId}/generate-objection`, { responseType: 'blob' });
    let filename = 'Kundërshtim.docx';
    const disposition = response.headers['content-disposition'];
    if (disposition && disposition.indexOf('filename=') !== -1) {
      const matches = /filename="?([^"]+)"?/.exec(disposition);
      if (matches && matches[1]) filename = matches[1];
    }
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  public async archiveCaseDocument(caseId: string, documentId: string): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/documents/${documentId}/archive`);
    return response.data;
  }

  public async renameDocument(caseId: string, docId: string, newName: string): Promise<void> {
    await apiClient.put(`/cases/${caseId}/documents/${docId}/rename`, { new_name: newName });
  }

  public async reprocessDocument(caseId: string, documentId: string): Promise<ReprocessConfirmation> {
    const response = await apiClient.post<ReprocessConfirmation>(`/cases/${caseId}/documents/${documentId}/reprocess`);
    return response.data;
  }

  public async reprocessCaseDocuments(caseId: string): Promise<BulkReprocessResponse> {
    const response = await apiClient.post<BulkReprocessResponse>(`/cases/${caseId}/documents/reprocess-all`);
    return response.data;
  }

  // ========== ANALYSIS & STRATEGY ==========
  public async analyzeCase(caseId: string, clientPosition?: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL', force?: boolean): Promise<CaseAnalysisResult & { cached?: boolean; message?: string; latest_deep_analysis?: DeepAnalysisResult }> {
    const params: any = {};
    if (clientPosition) params.client_position = clientPosition;
    if (force) params.force = force;
    const response = await apiClient.post<any>(`/cases/${caseId}/analyze`, null, { params });
    return response.data;
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

  public async crossExamineDocument(caseId: string, documentId: string): Promise<CaseAnalysisResult> {
    const response = await apiClient.post<CaseAnalysisResult>(`/cases/${caseId}/documents/${documentId}/cross-examine`);
    return response.data;
  }

  public async clearCaseAnalysis(caseId: string): Promise<void> {
    await apiClient.post(`/cases/${caseId}/analyze/clear`);
  }

  // ========== GRAPH ONTOLOGY ==========
  public async getCaseGraph(caseId: string): Promise<any> {
    const response = await apiClient.get(`/cases/${caseId}/graph`);
    return response.data;
  }

  public async rebuildCaseGraph(caseId: string): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/graph/rebuild`);
    return response.data;
  }

  public async searchFirmGraph(query: string): Promise<any[]> {
    const response = await apiClient.get('/cases/firm/graph/search', { params: { query } });
    return response.data;
  }

  public async mergeGraphNodes(caseId: string, primaryId: string, secondaryId: string): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/graph/nodes/merge`, { primary_id: primaryId, secondary_id: secondaryId });
    return response.data;
  }

  public async createCustomGraphEdge(caseId: string, edgeData: { source: string; target: string; relation: string; evidence_text?: string; amount_eur?: number }): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/graph/edges`, edgeData);
    return response.data;
  }

  public async downloadCourtGraphReport(caseId: string): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/graph/export`);
    return response.data;
  }

  // ========== MOBILE SESSIONS & FORENSICS ==========
  public async createMobileUploadSession(caseId?: string): Promise<MobileSessionResponse> {
    const url = caseId ? `/cases/${caseId}/mobile-upload-session` : `/finance/mobile-upload-session`;
    const response = await apiClient.post<MobileSessionResponse>(url);
    return response.data;
  }

  public async analyzeScannedImage(caseId: string, file: File): Promise<SpreadsheetAnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<SpreadsheetAnalysisResult>(`/cases/${caseId}/analyze/scanned-image`, formData);
    return response.data;
  }

  public async checkMobileUploadStatus(token: string): Promise<MobileUploadStatus> {
    const url = token.startsWith('GEN-') ? `/finance/mobile-upload-status/${token}` : `/cases/mobile-upload-status/${token}`;
    const response = await apiClient.get<MobileUploadStatus>(url);
    return response.data;
  }

  public async getMobileSessionFile(token: string): Promise<{ blob: Blob; filename: string }> {
    const url = token.startsWith('GEN-') ? `/finance/mobile-upload-file/${token}` : `/cases/mobile-upload-file/${token}`;
    const response = await apiClient.get(url, { responseType: 'blob' });
    const disposition = response.headers['content-disposition'];
    let filename = 'mobile-upload.jpg';
    if (disposition && disposition.indexOf('filename=') !== -1) {
      const matches = /filename="([^"]*)"/.exec(disposition);
      if (matches != null && matches[1]) filename = matches[1];
    }
    return { blob: response.data, filename };
  }

  public async publicMobileUpload(token: string, file: File): Promise<{ status: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const url = token.startsWith('GEN-') ? `${API_V1_URL}/finance/mobile-upload/${token}` : `${API_V1_URL}/cases/mobile-upload/${token}`;
    const response = await axios.post(url, formData);
    return response.data;
  }

  public async fetchImageBlob(url: string): Promise<Blob> {
    if (url.startsWith('blob:')) {
      const response = await window.fetch(url);
      return await response.blob();
    }
    const response = await apiClient.get(url, { responseType: 'blob' });
    return response.data;
  }

  public async analyzeSpreadsheet(caseId: string, file: File): Promise<SpreadsheetAnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<SpreadsheetAnalysisResult>(`/cases/${caseId}/analyze/spreadsheet`, formData);
    return response.data;
  }

  public async forensicAnalyzeSpreadsheet(caseId: string, file: File, lang: string = 'sq'): Promise<ForensicSpreadsheetAnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('analyst_id', 'frontend_user');
    formData.append('acquisition_method', 'WEB_UPLOAD');
    formData.append('lang', lang);
    const response = await apiClient.post<ForensicSpreadsheetAnalysisResult>(`/cases/${caseId}/analyze/spreadsheet/forensic`, formData, { params: { lang } });
    return response.data;
  }

  public async analyzeExistingSpreadsheet(caseId: string, documentId: string): Promise<SpreadsheetAnalysisResult> {
    const response = await apiClient.post<SpreadsheetAnalysisResult>(`/cases/${caseId}/analyze/spreadsheet-existing/${documentId}`);
    return response.data;
  }

  public async interrogateFinancialRecords(caseId: string, question: string): Promise<FinanceInterrogationResponse> {
    const response = await apiClient.post<FinanceInterrogationResponse>(`/cases/${caseId}/interrogate-finances`, { question });
    return response.data;
  }

  public async forensicInterrogateEvidence(caseId: string, question: string, includeChainOfCustody: boolean = true): Promise<ForensicInterrogationResponse> {
    const response = await apiClient.post<ForensicInterrogationResponse>(`/cases/${caseId}/interrogate-finances/forensic`, { question, include_chain_of_custody: includeChainOfCustody });
    return response.data;
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
}

export const caseService = new CaseService();