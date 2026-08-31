// FILE: src/services/chatService.ts
// PHOENIX PROTOCOL - AI CHAT & LEGAL DRAFTING SERVICE MODULE

import { apiClient, tokenManager, API_V1_URL, API_V2_URL } from './apiClient';
import type {
  CreateDraftingJobRequest,
  DraftingJobStatus,
  DraftingJobResult,
  ChatMessage
} from '../data/types';

export class ChatService {
  public async submitChatFeedback(caseId: string, messageIndex: number, feedback: 'up' | 'down'): Promise<void> {
    await apiClient.post(`/chat/case/${caseId}/feedback`, { message_index: messageIndex, feedback });
  }

  public async clearChatHistory(caseId: string): Promise<void> {
    await apiClient.delete(`/chat/case/${caseId}/history`);
  }

  public async updateChatHistory(caseId: string, chatHistory: ChatMessage[]): Promise<void> {
    await apiClient.put(`/cases/${caseId}/chat`, { chat_history: chatHistory });
  }

  public async getWebSocketUrl(_caseId: string): Promise<string> {
    return '';
  }

  public async initiateDraftingJob(data: CreateDraftingJobRequest): Promise<DraftingJobStatus> {
    const response = await apiClient.post<DraftingJobStatus>(`${API_V2_URL}/drafting/jobs`, data);
    return response.data;
  }

  public async getDraftingJobStatus(jobId: string): Promise<DraftingJobStatus> {
    const response = await apiClient.get<DraftingJobStatus>(`${API_V2_URL}/drafting/jobs/${jobId}/status`);
    return response.data;
  }

  public async getDraftingJobResult(jobId: string): Promise<DraftingJobResult> {
    const response = await apiClient.get<DraftingJobResult>(`${API_V2_URL}/drafting/jobs/${jobId}/result`);
    return response.data;
  }

  public async *sendChatMessageStream(
    caseId: string,
    message: string,
    documentIds?: string[],
    jurisdiction?: string,
    mode: 'FAST' | 'DEEP' = 'DEEP',
    domain?: string
  ): AsyncGenerator<string, void, unknown> {
    let token = tokenManager.get();
    if (!token) {
      try {
        const { data } = await apiClient.post<{ access_token: string }>('/auth/refresh');
        tokenManager.set(data.access_token);
        token = data.access_token;
      } catch {}
    }

    const url = `${API_V1_URL}/chat/case/${caseId}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 25000);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message,
          document_ids: documentIds || null,
          jurisdiction: jurisdiction || 'ks',
          mode: mode || 'DEEP',
          domain: domain || 'automatic',
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMsg = 'Biseda dështoi.';
        try {
          const errJson = await response.json();
          if (errJson?.detail) errorMsg = errJson.detail;
        } catch {
          if (response.status === 402) errorMsg = 'Abonimi juaj ka skaduar.';
        }
        throw new Error(errorMsg);
      }

      if (!response.body) throw new Error('Përgjigjja është e zbrazët.');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          yield decoder.decode(value, { stream: true });
        }
      } finally {
        reader.releaseLock();
      }
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new Error('Koha e përgjigjes skadoi. Ju lutem riprovoni.');
      }
      throw err;
    }
  }

  public async *draftLegalDocumentStream(data: CreateDraftingJobRequest): AsyncGenerator<string, void, unknown> {
    let token = tokenManager.get();
    if (!token) {
      try {
        const { data } = await apiClient.post<{ access_token: string }>('/auth/refresh');
        tokenManager.set(data.access_token);
        token = data.access_token;
      } catch {}
    }

    const url = `${API_V2_URL}/drafting/stream`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      let errorMsg = 'Hartimi i dokumentit dështoi.';
      try {
        const errJson = await response.json();
        if (errJson?.detail) errorMsg = errJson.detail;
      } catch {}
      throw new Error(errorMsg);
    }

    if (!response.body) return;
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        yield decoder.decode(value, { stream: true });
      }
    } finally {
      reader.releaseLock();
    }
  }
}

export const chatService = new ChatService();