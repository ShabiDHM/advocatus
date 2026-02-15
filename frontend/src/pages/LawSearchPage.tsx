// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - ENHANCED SEARCH WITH LAW DROPDOWN
// FINAL: Removed subtitle paragraph as requested.

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, BookOpen, AlertCircle, ChevronRight, FileText, ChevronDown, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';

interface LawResult {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id: string;
}

interface ArticleGroup {
  law_title: string;
  article_number: string;
  source: string;
  preview: string;
  chunkCount: number;
  chunkIds: string[];
}

// Hardcoded mapping for known malformed titles.
const KNOWN_JUNK_MAP: Record<string, string> = {
  'kodi lid': 'LIGJI NR. 06/L-082 – PËR MBROJTJEN E TË DHËNAVE PERSONALE'
};

// Normalize a title for display: trim and replace any whitespace sequences with a single space.
function normalizeForDisplay(title: string): string {
  return title.trim().replace(/\s+/g, ' ');
}

// Extract the descriptive part from the source filename and prepend "PËR".
// Example: "LIGJI_NR._04_L-077_PËR_MARRËDHËNIET_E_DETYRIMEVE.pdf" -> "PËR MARRËDHËNIET E DETYRIMEVE"
function extractDescriptiveFromSource(source: string): string | null {
  const match = source.match(/_PËR_(.+)\.pdf$/i);
  if (match && match[1]) {
    const descriptive = match[1].replace(/_/g, ' ').trim();
    return `PËR ${descriptive}`;
  }
  return null;
}

// Heuristic: a title is "bare" if it starts with "LIGJ" and contains a slash,
// but does NOT contain a long dash or common Albanian words (heuristic).
function isBareLawNumber(title: string): boolean {
  const trimmed = title.trim();
  if (!/^LIGJ/i.test(trimmed)) return false;
  if (!/\//.test(trimmed)) return false;
  // If it contains a dash or words like PËR, it's probably already descriptive
  if (/[—–-]/.test(trimmed) && !/^LIGJI?\s+NR\.?\s*\d+(?:\/[A-Za-z0-9-]+)*$/.test(trimmed)) {
    return false;
  }
  const wordCount = trimmed.split(/\s+/).length;
  if (wordCount > 4) return false;
  return true;
}

function useDebounce<T extends (...args: any[]) => any>(callback: T, delay: number) {
  const timeoutRef = useRef<NodeJS.Timeout>();
  const debouncedCallback = useCallback((...args: Parameters<T>) => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => callback(...args), delay);
  }, [callback, delay]);
  useEffect(() => () => timeoutRef.current && clearTimeout(timeoutRef.current), []);
  return debouncedCallback;
}

export default function LawSearchPage() {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [rawResults, setRawResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [lawTitles, setLawTitles] = useState<string[]>([]);
  const [loadingTitles, setLoadingTitles] = useState(true);
  const [selectedLaw, setSelectedLaw] = useState<string>('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [enrichedTitles, setEnrichedTitles] = useState<Map<string, string>>(new Map());
  const [enrichingTitles, setEnrichingTitles] = useState<Set<string>>(new Set());

  useEffect(() => {
    console.log('[LawSearch] Fetching law titles...');
    apiService.getLawTitles()
      .then(async (titles) => {
        console.log('[LawSearch] Raw titles from API:', titles);
        
        // Only filter out truly empty or very short strings (length < 2)
        const filteredTitles = titles.filter(title => {
          const normalized = normalizeForDisplay(title);
          return normalized.length >= 2;
        });
        
        console.log('[LawSearch] Filtered titles:', filteredTitles);
        setLawTitles(filteredTitles);
        
        // Pre‑populate enriched titles with known junk mappings
        const initialEnriched = new Map<string, string>();
        const remainingTitles: string[] = [];
        
        filteredTitles.forEach(title => {
          const lower = title.toLowerCase().trim();
          if (KNOWN_JUNK_MAP[lower]) {
            initialEnriched.set(title, KNOWN_JUNK_MAP[lower]);
          } else {
            remainingTitles.push(title);
          }
        });
        
        setEnrichedTitles(initialEnriched);
        
        const bareTitles = remainingTitles.filter(title => {
          const isBare = isBareLawNumber(title);
          console.log(`[LawSearch] "${title}" -> isBare: ${isBare}`);
          return isBare;
        });
        
        if (bareTitles.length === 0) {
          console.log('[LawSearch] No bare titles to enrich.');
          return;
        }

        console.log('[LawSearch] Enriching bare titles:', bareTitles);
        setEnrichingTitles(new Set(bareTitles));
        
        const enrichmentPromises = bareTitles.map(async (bareTitle) => {
          try {
            console.log(`[LawSearch] Fetching details for: "${bareTitle}"`);
            const lawData = await apiService.getLawArticlesByTitle(bareTitle);
            console.log(`[LawSearch] Full response for "${bareTitle}":`, JSON.stringify(lawData, null, 2));
            
            // Try to get descriptive part from source field
            if (lawData?.source) {
              const descriptive = extractDescriptiveFromSource(lawData.source);
              if (descriptive) {
                const fullTitle = `${bareTitle} – ${descriptive}`;
                console.log(`[LawSearch] Enriched via source: "${bareTitle}" -> "${fullTitle}"`);
                return { bare: bareTitle, full: fullTitle };
              }
            }
            
            // Fallback: if law_title is different from bare, use it
            if (lawData?.law_title && lawData.law_title !== bareTitle) {
              console.log(`[LawSearch] Enriched via law_title: "${bareTitle}" -> "${lawData.law_title}"`);
              return { bare: bareTitle, full: lawData.law_title };
            }
            
            console.warn(`[LawSearch] No usable enrichment data for "${bareTitle}". Response:`, lawData);
            return { bare: bareTitle, full: bareTitle };
          } catch (err) {
            console.error(`[LawSearch] Failed to enrich title "${bareTitle}":`, err);
            return { bare: bareTitle, full: bareTitle };
          }
        });

        const results = await Promise.all(enrichmentPromises);
        const newMap = new Map(initialEnriched);
        results.forEach(({ bare, full }) => newMap.set(bare, full));
        setEnrichedTitles(newMap);
        console.log('[LawSearch] Enriched titles map:', Object.fromEntries(newMap));
        setEnrichingTitles(new Set());
      })
      .catch(err => {
        console.error('[LawSearch] Failed to load law titles:', err);
        setLoadingTitles(false);
      })
      .finally(() => setLoadingTitles(false));
  }, []);

  const groupedResults = useMemo(() => {
    const groups = new Map<string, ArticleGroup>();
    rawResults.forEach(item => {
      const articleNum = item.article_number || '0';
      const key = `${item.law_title}|${articleNum}`;
      if (!groups.has(key)) {
        groups.set(key, {
          law_title: item.law_title,
          article_number: articleNum,
          source: item.source,
          preview: item.text,
          chunkCount: 1,
          chunkIds: [item.chunk_id]
        });
      } else {
        const group = groups.get(key)!;
        group.chunkCount++;
        group.chunkIds.push(item.chunk_id);
      }
    });
    return Array.from(groups.values());
  }, [rawResults]);

  const performSearch = useCallback(async (searchTerm: string) => {
    if (!searchTerm.trim()) {
      setRawResults([]);
      setHasSearched(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiService.searchLaws(searchTerm, undefined, 100);
      setRawResults(data);
      setHasSearched(true);
    } catch (err: any) {
      setError(err.message || t('lawSearch.error', 'Kërkimi dështoi.'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const debouncedSearch = useDebounce(performSearch, 300);

  useEffect(() => {
    debouncedSearch(query);
  }, [query, debouncedSearch]);

  const handleClear = () => {
    setQuery('');
    setRawResults([]);
    setHasSearched(false);
    setError('');
  };

  const handleLawSelect = (lawTitle: string) => {
    setSelectedLaw(lawTitle);
    setDropdownOpen(false);
    window.location.href = `/laws/overview?lawTitle=${encodeURIComponent(lawTitle)}`;
  };

  const getDisplayTitle = (original: string): string => {
    if (enrichedTitles.has(original)) {
      return enrichedTitles.get(original)!;
    }
    return original;
  };

  return (
    <div className="max-w-5xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-black text-text-primary tracking-tight">
          {t('lawSearch.title', 'Biblioteka Ligjore')}
        </h1>
        {/* Subtitle paragraph removed as requested */}
      </div>

      <div className="relative mb-6">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="glass-button w-full flex items-center justify-between px-4 py-3 rounded-xl text-left"
          disabled={loadingTitles || enrichingTitles.size > 0}
        >
          <span className="text-text-secondary">
            {selectedLaw ? normalizeForDisplay(selectedLaw) : t('lawSearch.selectLaw', 'Zgjidh një ligj')}
          </span>
          {loadingTitles || enrichingTitles.size > 0 ? (
            <Loader2 className="h-4 w-4 animate-spin text-text-secondary" />
          ) : (
            <ChevronDown size={18} className={`transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
          )}
        </button>
        {dropdownOpen && (
          <div className="absolute z-10 mt-1 w-full bg-background-dark/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl max-h-60 overflow-y-auto custom-scrollbar">
            {loadingTitles ? (
              <div className="p-4 text-center text-text-secondary">{t('general.loading', 'Duke ngarkuar...')}</div>
            ) : (
              lawTitles.map(title => (
                <button
                  key={title}
                  onClick={() => handleLawSelect(title)}
                  className="w-full text-left px-4 py-2 hover:bg-white/5 text-text-secondary hover:text-white transition-colors"
                >
                  {normalizeForDisplay(getDisplayTitle(title))}
                  {enrichingTitles.has(title) && (
                    <Loader2 className="inline-block ml-2 h-3 w-3 animate-spin" />
                  )}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div className="relative mb-8">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-text-secondary" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('lawSearch.placeholder', 'Kërko ligje, nene, koncepte juridike...')}
          className="glass-input w-full pl-12 pr-12 py-3 text-base rounded-xl transition-all"
          autoFocus
        />
        {query && (
          <button
            onClick={handleClear}
            className="absolute inset-y-0 right-0 pr-4 flex items-center text-text-secondary hover:text-white transition-colors"
            aria-label={t('general.clear', 'Pastro')}
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {loading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-panel p-6 rounded-2xl animate-pulse">
              <div className="h-6 bg-white/10 rounded w-3/4 mb-3"></div>
              <div className="h-4 bg-white/5 rounded w-full mb-2"></div>
              <div className="h-4 bg-white/5 rounded w-5/6 mb-4"></div>
              <div className="h-4 bg-white/5 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="glass-panel border border-red-500/30 bg-red-500/10 p-6 rounded-2xl flex items-start gap-4">
          <AlertCircle className="h-6 w-6 text-red-500 shrink-0" />
          <p className="text-red-200 text-sm">{error}</p>
        </div>
      )}

      {!loading && hasSearched && groupedResults.length === 0 && query.trim() !== '' && (
        <div className="glass-panel p-12 rounded-2xl text-center">
          <BookOpen className="h-12 w-12 mx-auto text-text-secondary mb-4" />
          <p className="text-text-secondary text-lg font-medium">
            {t('lawSearch.noResults', 'Nuk u gjet asnjë ligj për këtë kërkim.')}
          </p>
          <p className="text-sm text-text-secondary/60 mt-2">
            {t('lawSearch.tryDifferent', 'Provo fjalë të ndryshme ose shkruaj një pyetje më të plotë.')}
          </p>
        </div>
      )}

      {!loading && groupedResults.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-text-secondary font-medium">
            {groupedResults.length} {groupedResults.length === 1 ? 'nen' : 'nene'} të gjetur
          </p>
          {groupedResults.map((article, idx) => (
            <div
              key={idx}
              className="glass-panel p-6 rounded-2xl hover:shadow-xl transition-all cursor-pointer group block"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center flex-wrap gap-2 mb-2">
                    <Link
                      to={`/laws/overview?lawTitle=${encodeURIComponent(article.law_title)}`}
                      className="text-xl font-bold text-text-primary hover:text-primary-start transition-colors"
                      title={t('lawSearch.viewAllArticles', 'Shiko të gjitha nenet')}
                    >
                      {article.law_title}
                    </Link>
                    <span className="text-text-secondary font-normal">
                      – Neni {article.article_number}
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary mb-3 line-clamp-3">
                    {article.preview}
                  </p>
                  <div className="flex items-center gap-3 text-xs flex-wrap">
                    <span className="px-2 py-1 bg-white/5 rounded-full text-text-secondary">
                      {article.source}
                    </span>
                    {article.chunkCount > 1 && (
                      <span className="px-2 py-1 bg-primary-start/10 text-primary-start rounded-full border border-primary-start/20">
                        {article.chunkCount} pjesë
                      </span>
                    )}
                    <Link
                      to={`/laws/article?lawTitle=${encodeURIComponent(article.law_title)}&articleNumber=${encodeURIComponent(article.article_number)}`}
                      className="text-primary-start group-hover:text-primary-end transition-colors font-medium flex items-center gap-1"
                    >
                      {t('lawSearch.viewDetails', 'Shiko detajet')}
                      <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
                    </Link>
                    <Link
                      to={`/laws/overview?lawTitle=${encodeURIComponent(article.law_title)}`}
                      className="text-text-secondary hover:text-primary-start transition-colors font-medium flex items-center gap-1 ml-auto"
                      title={t('lawSearch.viewAllArticles', 'Të gjitha nenet e këtij ligji')}
                    >
                      <FileText size={14} />
                      {t('lawSearch.viewAll', 'Të gjitha')}
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && !error && rawResults.length === 0 && query.trim() === '' && (
        <div className="text-center text-text-secondary/40 text-sm mt-12">
          <Search className="h-8 w-8 mx-auto mb-3 opacity-30" />
          <p>{t('lawSearch.startTyping', 'Fillo të shkruash për të kërkuar...')}</p>
        </div>
      )}
    </div>
  );
}