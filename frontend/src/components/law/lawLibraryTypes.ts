// FILE: src/components/law/lawLibraryTypes.ts
// PHOENIX PROTOCOL - LAW LIBRARY TYPES V2.0
//
// V2.0: ALIGNED ME BACKEND V208.2.
//   - DEFAULT_LAWS: HEQUR (hardcoding; vjen nga /laws/titles)
//   - LawResult: shtuar is_repealed/warning/page/page_number/source_info
//   - LawResult: chunk_id bërë optional (backend mund të mos e dërgojë)
//   - Shtuar RepealedStatuteItem dhe TitlesResponse interfaces
//
// V1.0: Versioni i vjetër me DEFAULT_LAWS hardcoded.

import type { SourceInfo, RepealedInfo } from './lawArticleTypes';

// ═══════════════════════════════════════════════════════════════════════════
// LAW RESULT (nga /laws/search)
// ═══════════════════════════════════════════════════════════════════════════

export interface LawResult {
  law_title: string;
  article_number?: string;
  chunk_id?: string;            // optional — mund të mungojë
  source?: string;
  text?: string;

  // V208.2 repeals
  is_repealed?: boolean;
  warning?: string;
  repealed_info?: RepealedInfo;

  // Page info
  page?: number | null;
  page_number?: number | null;

  // Confidence (nëse vjen)
  source_info?: SourceInfo;
}

// ═══════════════════════════════════════════════════════════════════════════
// TITLES RESPONSE (nga /laws/titles) — V208.2
// ═══════════════════════════════════════════════════════════════════════════

export interface RepealedStatuteItem {
  law_title: string;
  repealed_by: string;
  repealed_date: string;
  source: string;
  reason: string;
  warning: string;
}

export interface TitlesResponse {
  statutes: string[];
  case_law: string[];
  all_titles: string[];
  repealed_statutes?: RepealedStatuteItem[];
}

// ═══════════════════════════════════════════════════════════════════════════
// BY-TITLE RESPONSE (nga /laws/by-title)
// ═══════════════════════════════════════════════════════════════════════════

export interface LawOverviewData {
  law_title: string;
  source: string;
  article_count: number;
  articles: string[];
  is_official_statute?: boolean;

  // V208.2 repeals
  is_repealed?: boolean;
  repealed_info?: RepealedInfo;
  warning?: string;

  // Page info
  page?: number | null;
  page_number?: number | null;
}

// ═══════════════════════════════════════════════════════════════════════════
// KONFIRMIM: NUK ka DEFAULT_LAWS — ato vijnë vetëm nga backend /laws/titles
// ═══════════════════════════════════════════════════════════════════════════