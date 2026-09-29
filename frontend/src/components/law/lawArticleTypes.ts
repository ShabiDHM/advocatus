// FILE: src/components/law/lawArticleTypes.ts
// PHOENIX PROTOCOL - LAW ARTICLE TYPES V2.1
//
// V2.1: Shtuar fushat për burime eksterne (KEDNJ/OKB/Hagë).
//   - `is_external`, `external_source_id`, `external_category`,
//     `external_short_name` — vijnë nga backend V208.6 kur citimi
//     është traktat ndërkombëtar.
//
// V2.0: ALIGNED ME BACKEND V208.2.

// ═══════════════════════════════════════════════════════════════════════════
// CONFIDENCE
// ═══════════════════════════════════════════════════════════════════════════

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';

export interface ConfidenceInfo {
  level: ConfidenceLevel;
  label: string;
  icon: string;
  color: string;
  description: string;
  score: number;
}

// ═══════════════════════════════════════════════════════════════════════════
// REPEALED INFO (V208.2)
// ═══════════════════════════════════════════════════════════════════════════

export interface RepealedInfo {
  id?: string;
  is_repealed: boolean;
  repealed_by: string;
  repealed_date: string;
  source: string;
  reason: string;
  warning_message: string;
  successor_patterns?: string[];
}

// ═══════════════════════════════════════════════════════════════════════════
// SOURCE INFO — ALIGNED ME BACKEND V23.0/V208.2/V208.6
// ═══════════════════════════════════════════════════════════════════════════

export interface SourceInfo {
  confidence: ConfidenceInfo;
  matched_law: string;
  matched_article: string;
  source_file: string;
  was_mapped: boolean;
  verification_hint: string;
  match_count: number;

  // V23.0 backend fields
  page?: number | null;
  page_available?: boolean;
  is_official_statute?: boolean;
  title_match_type?: 'exact' | 'code' | 'substring' | 'word' | 'unknown';

  // V208.6: external source flag
  is_external?: boolean;
}

// ═══════════════════════════════════════════════════════════════════════════
// ARTICLE DATA
// ═══════════════════════════════════════════════════════════════════════════

export interface ArticleData {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id?: string;
  source_info?: SourceInfo;

  // V208.2 repeals
  is_repealed?: boolean;
  repealed_info?: RepealedInfo;
  warning?: string;

  // Page info (nullable)
  page?: number | null;
  page_number?: number | null;

  // Kërkesa origjinale e userit (jo nga backend)
  requested_law_title?: string;

  // V208.6: External sources (KEDNJ, OKB, Hagë)
  is_external?: boolean;
  external_source_id?: string;
  external_category?: string;
  external_short_name?: string;
}

// ═══════════════════════════════════════════════════════════════════════════
// CHAT
// ═══════════════════════════════════════════════════════════════════════════

export interface ChatMessage {
  id: string;
  role: 'user' | 'auditor';
  content: string;
  timestamp: Date;
}

// ═══════════════════════════════════════════════════════════════════════════
// SUGGESTED QUESTIONS
// ═══════════════════════════════════════════════════════════════════════════

export const SUGGESTED_QUESTIONS: string[] = [];