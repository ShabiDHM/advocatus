// FILE: frontend/src/services/forensicService.ts
// PHOENIX PROTOCOL - FORENSIC SERVICE V5.0 (STREAMLINED CASE EVIDENCE & MEDIA CLIENT)
// 100% COMPLETE CODE • ZERO TS WARNINGS • LEGACY PILLARS & DEEP SIMULATIONS FULLY PURGED

import { apiClient } from './apiClient';

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
  // Ky shërbim përdoret për administrimin e provave mediare dhe shkarkimin e raporteve brenda lëndës standarde (/cases/...)

  // =========================================================================
  // 📄 1. DOKUMENTET DHE RAPORTET E LËNDËS
  // =========================================================================

  public async clearDocumentAudit(caseId: string, documentId: string): Promise<any> {
    const response = await apiClient.post(`/cases/${caseId}/documents/${documentId}/clear-audit`);
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
    link.setAttribute('download', `Raporti_Juridik_${caseId.slice(-6)}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  // =========================================================================
  // 🎙️ & 🎬 2. MEDIA EVIDENCE (AUDIO & VIDEO CCTV E LËNDËS)
  // =========================================================================

  public async getCaseMedia(caseId: string): Promise<MediaEvidenceItem[]> {
    const response = await apiClient.get<MediaEvidenceItem[]>(`/cases/${caseId}/media`);
    return response.data || [];
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