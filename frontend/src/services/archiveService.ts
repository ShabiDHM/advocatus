// FILE: src/services/archiveService.ts
// PHOENIX PROTOCOL - ARCHIVE & DOCUMENT MANAGEMENT SERVICE MODULE

import { apiClient } from './apiClient';
import type { ArchiveItemOut, Document } from '../data/types';

export class ArchiveService {
  public async getArchiveItems(category?: string, caseId?: string, parentId?: string): Promise<ArchiveItemOut[]> {
    const params: any = {};
    if (category) params.category = category;
    if (caseId) params.case_id = caseId;
    if (parentId) params.parent_id = parentId;
    const response = await apiClient.get<ArchiveItemOut[]>('/archive/items', { params });
    return Array.isArray(response.data) ? response.data : ((response.data as any).items || []);
  }

  public async createArchiveFolder(title: string, parentId?: string, caseId?: string, category?: string): Promise<ArchiveItemOut> {
    const formData = new FormData();
    formData.append('title', title);
    if (parentId) formData.append('parent_id', parentId);
    if (caseId) formData.append('case_id', caseId);
    if (category) formData.append('category', category);
    const response = await apiClient.post<ArchiveItemOut>('/archive/folder', formData);
    return response.data;
  }

  public async uploadArchiveItem(file: File, title: string, category: string, caseId?: string, parentId?: string): Promise<ArchiveItemOut> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('category', category);
    if (caseId) formData.append('case_id', caseId);
    if (parentId) formData.append('parent_id', parentId);
    const response = await apiClient.post<ArchiveItemOut>('/archive/upload', formData);
    return response.data;
  }

  public async deleteArchiveItem(itemId: string): Promise<void> {
    await apiClient.delete(`/archive/items/${itemId}`);
  }

  public async renameArchiveItem(itemId: string, newTitle: string): Promise<void> {
    await apiClient.put(`/archive/items/${itemId}/rename`, { new_title: newTitle });
  }

  public async shareDocument(caseId: string, docId: string, isShared: boolean): Promise<Document> {
    const response = await apiClient.put<Document>(`/cases/${caseId}/documents/${docId}/share`, { is_shared: isShared });
    return response.data;
  }

  public async shareArchiveItem(itemId: string, isShared: boolean): Promise<ArchiveItemOut> {
    const response = await apiClient.put<ArchiveItemOut>(`/archive/items/${itemId}/share`, { is_shared: isShared });
    return response.data;
  }

  public async shareArchiveCase(caseId: string, isShared: boolean): Promise<void> {
    await apiClient.put('/archive/case/share', { case_id: caseId, is_shared: isShared });
  }

  public async downloadArchiveItem(itemId: string, title: string): Promise<void> {
    const response = await apiClient.get(`/archive/items/${itemId}/download`, { responseType: 'blob' });
    let filename = (title || 'Dokument').trim();
    if (!filename.toLowerCase().endsWith('.pdf')) {
      filename = `${filename}.pdf`;
    }
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  public async getArchiveFileBlob(itemId: string): Promise<Blob> {
    const response = await apiClient.get(`/archive/items/${itemId}/download`, { params: { preview: true }, responseType: 'blob' });
    return response.data;
  }
}

export const archiveService = new ArchiveService();