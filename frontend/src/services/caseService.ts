// FILE: frontend/src/services/caseService.ts
// PHOENIX PROTOCOL - CASE SERVICE MODULE V60.0
// V60.0: Hequr mobile flow (i vdekur): createMobileUploadSession, analyzeScannedImage,
//        checkMobileUploadStatus, getMobileSessionFile, publicMobileUpload.
// V59.0: Hequr archiveForensicReport + downloadForensicReport.
// V58.0: Removed dead spreadsheet/forensic-interrogation feature.

import { apiClient } from './apiClient';
import type {
  Case,
  CreateCaseRequest,
  Document,
  DeletedDocumentResponse,
  CaseAnalysisResult,
  DeepAnalysisResult
} from '../data/types';

interface DocumentContentResponse { text: string; }
interface ReprocessConfirmation { documentId: string; message: string; }
interface BulkReprocessResponse { count: number; message: string; }

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

  public async fetchImageBlob(url: string): Promise<Blob> {
    if (url.startsWith('blob:')) {
      const response = await window.fetch(url);
      return await response.blob();
    }
    const response = await apiClient.get(url, { responseType: 'blob' });
    return response.data;
  }
}

export const caseService = new CaseService();