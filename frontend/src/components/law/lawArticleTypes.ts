// FILE: src/components/law/lawArticleTypes.ts

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
  is_official_statute?: boolean;
}

export interface ArticleData {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id: string;
  source_info?: SourceInfo;
  requested_law_title?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'auditor';
  content: string;
  timestamp: Date;
}

export const SUGGESTED_QUESTIONS: string[] = [
  'Cilat janë detyrimet kryesore sipas këtij neni?',
  'Çfarë ndodh nëse shkelet ky nen?',
  'A ka ndonjë afat kohor që duhet respektuar?',
  'Si mund ta zbatoj këtë nen në praktikë?',
];