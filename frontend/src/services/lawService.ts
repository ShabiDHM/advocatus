// FILE: src/services/lawService.ts
// PHOENIX PROTOCOL - DEDICATED LAW SERVICE MODULE (100% ISOLATED)

import { apiClient, API_V1_URL, tokenManager } from './apiClient';

export interface SourceInfo {
  confidence: {
    level: 'HIGH' | 'MEDIUM' | 'LOW' | 'LOWEST' | 'UNKNOWN' | 'NONE';
    label: string;
    icon: string;
    color: string;
    description: string;
    score: number;
  };
  matched_law: string;
  matched_article: string;
  source_file: string;
  was_mapped: boolean;
  mapped_from: string | null;
  multiple_matches: boolean;
  matching_laws: string[];
  strategy_used: string;
  verification_hint: string;
  match_count: number;
}

export interface LawArticle {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id?: string;
  source_info?: SourceInfo;
  page?: number;
  page_number?: number;
}

export class LawService {
  /**
   * Ngarkon nenin e plotë nga baza e të dhënave.
   */
  public async getLawArticle(lawTitle: string, articleNumber: string): Promise<LawArticle> {
    const response = await apiClient.get<LawArticle>('/laws/article', {
      params: { law_title: lawTitle, article_number: articleNumber },
    });
    return response.data;
  }

  /**
   * Kontrollon menjëherë nëse ekziston analizë e ruajtur në MongoDB (Multi-Device Cache).
   */
  public async getCachedLawAnalysis(lawTitle: string, articleNumber: string): Promise<string | null> {
    try {
      const response = await apiClient.get<{ cached: boolean; content: string | null }>('/laws/explain/cached', {
        params: { law_title: lawTitle, article_number: articleNumber },
      });
      if (response.data && response.data.cached && response.data.content) {
        return response.data.content;
      }
      return null;
    } catch {
      return null;
    }
  }

  /**
   * Fshin analizën e ruajtur në MongoDB (Purge Cache).
   */
  public async clearLawCache(lawTitle: string, articleNumber: string): Promise<void> {
    await apiClient.delete('/laws/explain/cache', {
      params: { law_title: lawTitle, article_number: articleNumber },
    });
  }

  /**
   * Ngarkon listën e neneve për një ligj të caktuar.
   */
  public async getLawArticlesByTitle(lawTitle: string): Promise<any> {
    const response = await apiClient.get('/laws/by-title', { params: { law_title: lawTitle } });
    return response.data;
  }

  /**
   * Ngarkon të gjithë titujt e ligjeve, manualeve dhe praktikës gjyqësore.
   */
  public async getLawTitles(): Promise<any> {
    const response = await apiClient.get('/laws/titles');
    return response.data;
  }

  /**
   * Kërkim global në bazën ligjore.
   */
  public async searchLaws(query: string, jurisdiction?: string, limit: number = 50): Promise<any> {
    const response = await apiClient.get('/laws/search', { params: { q: query, jurisdiction, limit } });
    return response.data;
  }

  /**
   * Ngarkon pjesën e ligjit me Chunk ID.
   */
  public async getLawByChunkId(chunkId: string): Promise<LawArticle> {
    const response = await apiClient.get<LawArticle>(`/laws/${chunkId}`);
    return response.data;
  }

  /**
   * Gjeneron analizën e thellë ligjore me DeepSeek (Streaming në kohë reale).
   */
  public async *explainLawStream(
    lawTitle: string,
    articleNumber: string,
    articleText: string
  ): AsyncGenerator<string, void, unknown> {
    let token = tokenManager.get();
    if (!token) {
      try {
        const { data } = await apiClient.post<{ access_token: string }>('/auth/refresh');
        tokenManager.set(data.access_token);
        token = data.access_token;
      } catch {}
    }

    const prompt = `Ligji: "${lawTitle}"\nNeni: ${articleNumber}\n\nPërmbajtja e Nenit:\n${articleText}`;
    const url = `${API_V1_URL}/laws/explain`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ prompt, law_title: lawTitle, article_number: articleNumber }),
    });

    if (!response.ok) {
      let errorMsg = 'Sqarimi i ligjit dështoi.';
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

  /**
   * Bisedë interaktive me Auditorin Ligjor (DeepSeek Streaming).
   */
  public async *askLawAuditor(
    articleId: string,
    query: string,
    lawTitle?: string,
    articleNumber?: string
  ): AsyncGenerator<string, void, unknown> {
    let token = tokenManager.get();
    if (!token) {
      try {
        const { data } = await apiClient.post<{ access_token: string }>('/auth/refresh');
        tokenManager.set(data.access_token);
        token = data.access_token;
      } catch {}
    }

    const url = `${API_V1_URL}/laws/audit-chat`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        article_id: articleId,
        law_title: lawTitle || '',
        article_number: articleNumber || '',
        query,
      }),
    });

    if (!response.ok) throw new Error(`Biseda dështoi: ${response.status}`);
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

export const lawService = new LawService();