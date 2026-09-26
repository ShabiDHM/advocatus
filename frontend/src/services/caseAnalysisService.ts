// FILE: src/services/caseAnalysisService.ts
// PHOENIX PROTOCOL - CASE ANALYSIS SSE CLIENT V1.11
// V1.11: REWRITE REMOVED + TOKEN URL FIX —
//        - Hequr dead code Rewrite:
//          streamDraftRewrite(), getSavedRewrite(),
//          ValidationIssue, RewriteValidation, StructureStats,
//          DraftRewriteResult, SavedRewriteResponse, REWRITE_TIMEOUT_MS.
//        - Hequr token nga query string në streamDraftVerification.
//          fetch() mban headers, prandaj token-i në URL ishte i
//          panevojshëm dhe rrezik sigurie (server logs, referer).
//        - Pastruar AnalysisPhase: hequr 'cross_reference' dhe 'synthesis'
//          (nuk emitohen më nga orchestratori V1.9).
// V1.10: CLEANUP — hequr streamDraftAiImprove() + tipet AiImprove* +
//        AI_IMPROVE_TIMEOUT_MS (funksionaliteti u hoq për të shmangur
//        rrezikun e halucinacioneve semantike).
// V1.9: AI IMPROVE (u hoq).
// V1.8: MULTI-DEVICE — getSavedRewrite() (u hoq në V1.11).
// V1.7: REWRITE VALIDATION (u hoq në V1.11).

import { tokenManager, API_V1_URL, apiClient } from './apiClient';

// ────────────────────────────────────────────────────────────────────────────
// TYPES
// ────────────────────────────────────────────────────────────────────────────

export type AnalysisScope = 'case' | 'document';

export type AnalysisPhase =
  | 'extraction'
  | 'document_review';

export interface AnalysisEvent {
  event: string;
  phase?: AnalysisPhase;
  scope?: AnalysisScope;
  case_id?: string;
  case_title?: string;
  force_reprocess?: boolean;
  document_ids?: string[] | null;
  document_id?: string;
  document_type?: string;
  is_single_document?: boolean;
  file_name?: string;
  index?: number;
  total_documents?: number;
  stats?: Record<string, any>;
  section_stats?: Record<string, any>;
  summary?: Record<string, any>;
  section_key?: string;
  section_title?: string;
  content_length?: number;
  content?: string;
  from_cache?: boolean;
  chunk?: string;
  chunk_index?: number;
  total_chunks?: number;
  reason?: string;
  message?: string;
  error?: string;
  result?: any;
  [key: string]: any;
}

export type VerifyDocType =
  | 'padi_civile'
  | 'pergjigje_padi'
  | 'kallzim_penal'
  | 'kontrate'
  | 'kerkese_propozim'
  | 'ankese_kundershtim'
  | 'tjeter';

export interface ScoreBreakdown {
  formal: number;
  legal: number;
  readiness: number;
}

export interface DraftVerificationResult {
  case_id: string;
  document_id: string;
  doc_type: string;
  doc_type_label: string;
  file_name: string;
  built_at: string;
  sections: Record<string, { title: string; content: string; error?: string }>;
  stats: Record<string, any>;
  readiness: 'READY' | 'NEEDS WORK' | 'INCOMPLETE' | 'UNKNOWN';
  score: number;
  score_breakdown: ScoreBreakdown;
  full_report: string;
  section_stats: Record<string, any>;
  status: 'completed' | 'error' | 'empty';
  error_message?: string;
  persisted?: boolean;
}

export interface DraftVerificationCached {
  doc_type: string;
  doc_type_label: string;
  file_name: string;
  built_at: string;
  readiness: string;
  score?: number;
  score_breakdown?: ScoreBreakdown;
  full_report: string;
  stats?: Record<string, any>;
  status: string;
}

export interface DraftVerificationResponse {
  has_verification: boolean;
  verification?: DraftVerificationCached;
}

const ANALYSIS_TIMEOUT_MS = 45 * 60 * 1000;
const VERIFY_TIMEOUT_MS = 15 * 60 * 1000;

// ────────────────────────────────────────────────────────────────────────────
// SERVICE
// ────────────────────────────────────────────────────────────────────────────

export class CaseAnalysisService {
  public async *streamCaseAnalysis(
    caseId: string,
    forceReprocess: boolean = true,
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
          else if (response.status === 404) errorMsg = 'Lënda ose dokumenti nuk u gjet.';
        }
        throw new Error(errorMsg);
      }

      if (!response.body) {
        throw new Error('Përgjigjja SSE është e zbrazët.');
      }

      yield* this._readSSEStream(response.body);

    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err?.name === 'AbortError') {
        throw new Error(
          `Koha e analizës skadoi pas ${Math.round(ANALYSIS_TIMEOUT_MS / 60000)} minutash.`
        );
      }
      throw err;
    }
  }

  public async *streamDraftVerification(
    caseId: string,
    documentId: string,
    docType: VerifyDocType,
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

    const url = `${API_V1_URL}/cases/${caseId}/documents/${documentId}/verify`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), VERIFY_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Accept': 'text/event-stream',
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ doc_type: docType }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMsg = 'Verifikimi i draftit dështoi.';
        try {
          const errJson = await response.json();
          if (errJson?.detail) errorMsg = errJson.detail;
        } catch {
          if (response.status === 400) errorMsg = 'Lloj dokumenti i pavlefshëm.';
          else if (response.status === 401) errorMsg = 'Sesioni ka skaduar. Rifreskoni faqen.';
          else if (response.status === 403) errorMsg = 'Nuk keni akses në këtë lëndë.';
          else if (response.status === 404) errorMsg = 'Lënda ose dokumenti nuk u gjet.';
        }
        throw new Error(errorMsg);
      }

      if (!response.body) {
        throw new Error('Përgjigjja SSE është e zbrazët.');
      }

      yield* this._readSSEStream(response.body);

    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err?.name === 'AbortError') {
        throw new Error(
          `Koha e verifikimit skadoi pas ${Math.round(VERIFY_TIMEOUT_MS / 60000)} minutash.`
        );
      }
      throw err;
    }
  }

  public async getDraftVerification(
    caseId: string,
    documentId: string,
    docType?: VerifyDocType,
  ): Promise<DraftVerificationResponse> {
    try {
      const params: Record<string, string> = {};
      if (docType) params.doc_type = docType;

      const { data } = await apiClient.get<DraftVerificationResponse>(
        `/cases/${caseId}/documents/${documentId}/verify`,
        { params },
      );
      return data;
    } catch (err: any) {
      if (err?.response?.status === 404) {
        return { has_verification: false };
      }
      console.warn('[CaseAnalysisService V1.11] getDraftVerification failed:', err);
      throw err;
    }
  }

  public async clearDraftVerification(
    caseId: string,
    documentId: string,
  ): Promise<{ deleted: boolean; modified_count: number }> {
    try {
      const { data } = await apiClient.delete<{ deleted: boolean; modified_count: number }>(
        `/cases/${caseId}/documents/${documentId}/verify`,
      );
      return data;
    } catch (err: any) {
      console.error('[CaseAnalysisService V1.11] clearDraftVerification failed:', err);
      throw err;
    }
  }

  // ────────────────────────────────────────────────────────────────────────
  // INTERNAL
  // ────────────────────────────────────────────────────────────────────────

  private async *_readSSEStream(
    body: ReadableStream<Uint8Array>,
  ): AsyncGenerator<AnalysisEvent, void, unknown> {
    const reader = body.getReader();
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
    if (dataLine === '[DONE]') return null;

    try {
      const parsed = JSON.parse(dataLine);
      if (parsed && typeof parsed === 'object') {
        return parsed as AnalysisEvent;
      }
      return null;
    } catch (e) {
      console.warn(
        '[CaseAnalysisService] Failed to parse SSE data line:',
        dataLine.slice(0, 100)
      );
      return null;
    }
  }
}

export const caseAnalysisService = new CaseAnalysisService();