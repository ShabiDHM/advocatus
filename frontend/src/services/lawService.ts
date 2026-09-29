// FILE: src/services/lawService.ts
// PHOENIX PROTOCOL - LAW SERVICE MODULE V2.0.1
//
// V2.0.1: FIX TS6133 warning për `articleText`.
//   - `articleText` → `_articleText` + JSDoc @deprecated
//   - Backend V3.0 lexon tekstin nga DB (nuk ka nevojë për prompt injection risk)
//   - Parametri do hiqet në klaster 2/6 (bashkë me LawArticlePage refactor)
//
// V2.0: Aligned me backend V208.2 (tipizim i plotë, AbortController).

import { apiClient, API_V1_URL, tokenManager } from './apiClient';
import type {
  ArticleData,
  SourceInfo,
  RepealedInfo,
} from '../components/law/lawArticleTypes';
import type {
  LawResult,
  TitlesResponse,
  LawOverviewData,
} from '../components/law/lawLibraryTypes';

// Re-export types for convenience
export type {
  ArticleData,
  SourceInfo,
  RepealedInfo,
  LawResult,
  TitlesResponse,
  LawOverviewData,
};

// ═══════════════════════════════════════════════════════════════════════════
// SERVICE
// ═══════════════════════════════════════════════════════════════════════════

export class LawService {
  // ═══════════════════════════════════════════════════════════════════════
  // READ
  // ═══════════════════════════════════════════════════════════════════════

  /**
   * Ngarkon nenin e plotë nga DB.
   */
  public async getLawArticle(
    lawTitle: string,
    articleNumber: string,
    signal?: AbortSignal,
  ): Promise<ArticleData> {
    const response = await apiClient.get<ArticleData>('/laws/article', {
      params: { law_title: lawTitle, article_number: articleNumber },
      signal,
    });
    return response.data;
  }

  /**
   * Ngarkon listën e neneve për një ligj (overview).
   * V208.2: përfshin is_repealed/warning.
   */
  public async getLawArticlesByTitle(
    lawTitle: string,
    signal?: AbortSignal,
  ): Promise<LawOverviewData> {
    const response = await apiClient.get<LawOverviewData>('/laws/by-title', {
      params: { law_title: lawTitle },
      signal,
    });
    return response.data;
  }

  /**
   * Liston statute + caselaw + repealed_statutes.
   */
  public async getLawTitles(signal?: AbortSignal): Promise<TitlesResponse> {
    const response = await apiClient.get<TitlesResponse>('/laws/titles', { signal });
    return response.data;
  }

  /**
   * Kërkim global në bazën ligjore (vector search).
   * V2.0: hequr `jurisdiction` (backend nuk e pranon).
   */
  public async searchLaws(
    query: string,
    limit: number = 50,
    signal?: AbortSignal,
  ): Promise<LawResult[]> {
    const response = await apiClient.get<LawResult[]>('/laws/search', {
      params: { q: query, limit },
      signal,
    });
    return response.data;
  }

  /**
   * Ngarkon pjesën e ligjit me Chunk ID.
   */
  public async getLawByChunkId(
    chunkId: string,
    signal?: AbortSignal,
  ): Promise<ArticleData> {
    const response = await apiClient.get<ArticleData>(`/laws/${chunkId}`, { signal });
    return response.data;
  }

  /**
   * Faqja fillestare e një precedenti (për PDF viewer).
   */
  public async getCaseStartingPage(
    lawTitle: string,
    signal?: AbortSignal,
  ): Promise<{ page: number | null; page_number: number | null; law_title: string; found: boolean }> {
    const response = await apiClient.get('/laws/case-page', {
      params: { law_title: lawTitle },
      signal,
    });
    return response.data;
  }

  // ═══════════════════════════════════════════════════════════════════════
  // CACHE — MongoDB multi-device
  // ═══════════════════════════════════════════════════════════════════════

  /**
   * Kthen analizën e ruajtur në MongoDB ose null.
   */
  public async getCachedLawAnalysis(
    lawTitle: string,
    articleNumber: string,
    signal?: AbortSignal,
  ): Promise<string | null> {
    try {
      const response = await apiClient.get<{ cached: boolean; content: string | null }>(
        '/laws/explain/cached',
        {
          params: { law_title: lawTitle, article_number: articleNumber },
          signal,
        },
      );
      if (response.data?.cached && response.data.content) {
        return response.data.content;
      }
      return null;
    } catch {
      // Silent — cache miss nuk është gabim
      return null;
    }
  }

  /**
   * Fshin analizën e ruajtur në MongoDB.
   */
  public async clearLawCache(lawTitle: string, articleNumber: string): Promise<void> {
    await apiClient.delete('/laws/explain/cache', {
      params: { law_title: lawTitle, article_number: articleNumber },
    });
  }

  // ═══════════════════════════════════════════════════════════════════════
  // STREAMING
  // ═══════════════════════════════════════════════════════════════════════

  /**
   * Gjeneron analizën e thellë ligjore (streaming).
   *
   * @param lawTitle - Titulli i ligjit
   * @param articleNumber - Numri i nenit
   * @param _articleText - DEPRECATED. Backend V3.0 lexon tekstin nga DB.
   *                       Mbahet për backward compat; do hiqet në klaster 2/6.
   * @param signal - AbortController signal (opsional)
   */
  public async *explainLawStream(
    lawTitle: string,
    articleNumber: string,
    _articleText: string,
    signal?: AbortSignal,
  ): AsyncGenerator<string, void, unknown> {
    const token = await this._ensureToken();
    const url = `${API_V1_URL}/laws/explain`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        prompt: `Analizo nenin ${articleNumber} sipas tekstit të dhënë.`,
        law_title: lawTitle,
        article_number: articleNumber,
      }),
      signal,
    });

    if (!response.ok) {
      const errMsg = await this._extractErrorMessage(response, 'Sqarimi i ligjit dështoi.');
      throw new Error(errMsg);
    }

    yield* this._readStream(response, signal);
  }

  /**
   * Bisedë interaktive me Auditorin Ligjor (streaming).
   * V2.0: pranon signal për cancel.
   */
  public async *askLawAuditor(
    articleId: string,
    query: string,
    lawTitle: string,
    articleNumber: string,
    signal?: AbortSignal,
  ): AsyncGenerator<string, void, unknown> {
    const token = await this._ensureToken();
    const url = `${API_V1_URL}/laws/audit-chat`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        article_id: articleId || '',
        law_title: lawTitle || '',
        article_number: articleNumber || '',
        query,
      }),
      signal,
    });

    if (!response.ok) {
      const errMsg = await this._extractErrorMessage(
        response,
        `Biseda dështoi: ${response.status}`,
      );
      throw new Error(errMsg);
    }

    yield* this._readStream(response, signal);
  }

  // ═══════════════════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════════════════

  /**
   * Merret token-in aktual ose provon refresh.
   * V2.0: nëse refresh dështon → kthen null (jo throw).
   */
  private async _ensureToken(): Promise<string | null> {
    let token = tokenManager.get();
    if (token) return token;

    try {
      const { data } = await apiClient.post<{ access_token: string }>('/auth/refresh');
      if (data?.access_token) {
        tokenManager.set(data.access_token);
        return data.access_token;
      }
    } catch (e) {
      console.warn('[lawService] Token refresh failed:', e);
    }
    return null;
  }

  /**
   * Nxjerr mesazhin e gabimit nga response (JSON detail ose fallback).
   */
  private async _extractErrorMessage(response: Response, fallback: string): Promise<string> {
    try {
      const errJson = await response.json();
      if (errJson?.detail && typeof errJson.detail === 'string') {
        return errJson.detail;
      }
    } catch {
      // Nuk është JSON — vazhdo me fallback
    }
    return fallback;
  }

  /**
   * Lexon një ReadableStream si AsyncGenerator.
   * V2.0: ndan kodin e përbashkët mes explainLawStream/askLawAuditor.
   */
  private async *_readStream(
    response: Response,
    signal?: AbortSignal,
  ): AsyncGenerator<string, void, unknown> {
    if (!response.body) return;

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        if (signal?.aborted) {
          await reader.cancel();
          break;
        }
        const { done, value } = await reader.read();
        if (done) break;
        yield decoder.decode(value, { stream: true });
      }
    } finally {
      try {
        reader.releaseLock();
      } catch {
        // Ignore — mund të ketë stream të mbyllur
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXPORT SINGLETON
// ═══════════════════════════════════════════════════════════════════════════

export const lawService = new LawService();