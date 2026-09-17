// FILE: src/services/caseAnalysisService.ts
// PHOENIX PROTOCOL - CASE ANALYSIS SSE CLIENT V1.1
// V1.1: documentIds param — scope analysis to specific documents.

import { tokenManager, API_V1_URL, apiClient } from './apiClient';

// ────────────────────────────────────────────────────────────────────────────
// TYPES
// ────────────────────────────────────────────────────────────────────────────

export type AnalysisPhase = 'extraction' | 'cross_reference' | 'synthesis';

export interface AnalysisEvent {
  event: string;
  phase?: AnalysisPhase;
  case_id?: string;
  case_title?: string;
  force_reprocess?: boolean;
  document_ids?: string[] | null;
  is_single_document?: boolean;
  file_name?: string;
  document_id?: string;
  index?: number;
  total_documents?: number;
  stats?: Record<string, any>;
  summary?: Record<string, any>;
  section_key?: string;
  section_title?: string;
  content_length?: number;
  content?: string;
  from_cache?: boolean;
  chunk?: string;
  reason?: string;
  message?: string;
  error?: string;
  [key: string]: any;
}

const ANALYSIS_TIMEOUT_MS = 45 * 60 * 1000;

// ────────────────────────────────────────────────────────────────────────────
// SERVICE
// ────────────────────────────────────────────────────────────────────────────

export class CaseAnalysisService {
  /**
   * Stream analizën e plotë të një lënde.
   *
   * @param caseId - ID e lëndës
   * @param forceReprocess - Nëse true, ri-ekstrakton edhe nëse ekziston cache
   * @param documentIds - Nëse jepet, analiza skopohet VETËM në këto dokumente
   */
  public async *streamCaseAnalysis(
    caseId: string,
    forceReprocess: boolean = false,
    documentIds?: string[],
  ): AsyncGenerator<AnalysisEvent, void, unknown> {
    let token = tokenManager.get();
    if (!token) {
      try {
        const { data } = await apiClient.post<{ access_token: string }>('/auth/refresh');
        tokenManager.set(data.access_token);
        token = data.access_token;
      } catch {
        // vazhdo pa token
      }
    }

    const url = `${API_V1_URL}/cases/${caseId}/analyze`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), ANALYSIS_TIMEOUT_MS);

    // V1.1: Body me document_ids
    const body: Record<string, any> = {
      force_reprocess: forceReprocess,
    };
    if (documentIds && documentIds.length > 0) {
      body.document_ids = documentIds;
    }

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Accept': 'text/event-stream',
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMsg = 'Analiza e lëndës dështoi.';
        try {
          const errJson = await response.json();
          if (errJson?.detail) errorMsg = errJson.detail;
        } catch {
          if (response.status === 402) errorMsg = 'Abonimi juaj ka skaduar.';
          else if (response.status === 401) errorMsg = 'Sesioni ka skaduar. Rifreskoni faqen.';
          else if (response.status === 403) errorMsg = 'Nuk keni akses në këtë lëndë.';
          else if (response.status === 404) errorMsg = 'Lënda nuk u gjet.';
        }
        throw new Error(errorMsg);
      }

      if (!response.body) {
        throw new Error('Përgjigjja SSE është e zbrazët.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          let separatorIndex: number;
          while ((separatorIndex = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.slice(0, separatorIndex);
            buffer = buffer.slice(separatorIndex + 2);

            const parsed = this._parseSSEBlock(rawEvent);
            if (parsed) {
              yield parsed;
            }
          }
        }

        if (buffer.trim()) {
          const parsed = this._parseSSEBlock(buffer);
          if (parsed) {
            yield parsed;
          }
        }

      } finally {
        reader.releaseLock();
      }

    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err?.name === 'AbortError') {
        throw new Error(
          `Koha e analizës skadoi pas ${Math.round(ANALYSIS_TIMEOUT_MS / 60000)} minutash. ` +
          `Provoni përsëri me më pak dokumente ose kontaktoni mbështetjen.`
        );
      }
      throw err;
    }
  }

  private _parseSSEBlock(block: string): AnalysisEvent | null {
    const lines = block.split('\n');
    let dataLine: string | null = null;

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      if (trimmed.startsWith('data:')) {
        dataLine = trimmed.slice(5).trim();
        break;
      }
    }

    if (!dataLine) return null;

    if (dataLine === '[DONE]') {
      return null;
    }

    try {
      const parsed = JSON.parse(dataLine);
      if (parsed && typeof parsed === 'object') {
        return parsed as AnalysisEvent;
      }
      return null;
    } catch (e) {
      console.warn('[CaseAnalysisService] Failed to parse SSE data line:', dataLine.slice(0, 100));
      return null;
    }
  }
}

export const caseAnalysisService = new CaseAnalysisService();