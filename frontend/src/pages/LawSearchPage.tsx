// FILE: src/pages/LawSearchPage.tsx
import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, BookOpen, AlertCircle, ChevronRight, FileText, ChevronDown, Loader2, Scale, Filter } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

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

const KNOWN_JUNK_MAP: Record<string, string> = {
  'kodi lid': 'LIGJI NR. 06/L-082 – PËR MBROJTJEN E TË DHËNAVE PERSONALE'
};

function normalizeForDisplay(title: string): string {
  return title.trim().replace(/\s+/g, ' ');
}

function extractDescriptiveFromSource(source: string): string | null {
  const match = source.match(/_PËR_(.+)\.pdf$/i);
  if (match && match[1]) {
    const descriptive = match[1].replace(/_/g, ' ').trim();
    return `PËR ${descriptive}`;
  }
  return null;
}

function isBareLawNumber(title: string): boolean {
  const trimmed = title.trim();
  if (!/^LIGJ/i.test(trimmed)) return false;
  if (!/\//.test(trimmed)) return false;
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
    apiService.getLawTitles()
      .then(async (titles) => {
        const filteredTitles = titles.filter(title => normalizeForDisplay(title).length >= 2);
        setLawTitles(filteredTitles);
        
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
        
        const bareTitles = remainingTitles.filter(isBareLawNumber);
        if (bareTitles.length === 0) return;

        setEnrichingTitles(new Set(bareTitles));
        
        const enrichmentPromises = bareTitles.map(async (bareTitle) => {
          try {
            const lawData = await apiService.getLawArticlesByTitle(bareTitle);
            if (lawData?.source) {
              const descriptive = extractDescriptiveFromSource(lawData.source);
              if (descriptive) return { bare: bareTitle, full: `${bareTitle} – ${descriptive}` };
            }
            if (lawData?.law_title && lawData.law_title !== bareTitle) {
              return { bare: bareTitle, full: lawData.law_title };
            }
            return { bare: bareTitle, full: bareTitle };
          } catch (err) {
            return { bare: bareTitle, full: bareTitle };
          }
        });

        const results = await Promise.all(enrichmentPromises);
        const newMap = new Map(initialEnriched);
        results.forEach(({ bare, full }) => newMap.set(bare, full));
        setEnrichedTitles(newMap);
        setEnrichingTitles(new Set());
      })
      .catch(() => setLoadingTitles(false))
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
          source: item.source || '',
          preview: item.text || '',
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
    return enrichedTitles.has(original) ? enrichedTitles.get(original)! : original;
  };

  return (
    <motion.div className="w-full min-h-screen pb-16" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {/* Dynamic Theme-Aware Scrollbar Injection */}
      <style>{`
        .custom-dropdown-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-dropdown-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-dropdown-scrollbar::-webkit-scrollbar-thumb { 
            background: var(--border-main); 
            border-radius: 10px; 
        }
        .custom-dropdown-scrollbar::-webkit-scrollbar-thumb:hover { 
            background: var(--accent-primary); 
        }
      `}</style>

      <div className="max-w-5xl mx-auto px-6 sm:px-8 pt-32">
        
        {/* Executive Header */}
        <header className="mb-10 flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-accent-subtle flex items-center justify-center text-accent-primary shadow-sm">
              <BookOpen size={24} />
            </div>
            <h1 className="text-4xl font-black text-text-primary tracking-tighter leading-none">
              {t('lawSearch.title', 'Hulumtim Ligjor')}
            </h1>
          </div>
        </header>

        {/* The Executive Search Console */}
        <div className="glass-panel p-6 sm:p-8 mb-12 shadow-lg border-border-main flex flex-col gap-4 relative z-40">
            
            {/* 1. Dropdown Filter Area */}
            <div className="relative z-50">
                <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="w-full flex items-center justify-between px-5 py-4 rounded-xl border border-border-main bg-card text-left transition-all hover:border-accent-primary/50 group shadow-sm"
                disabled={loadingTitles || enrichingTitles.size > 0}
                >
                <div className="flex items-center gap-3">
                    <Filter size={16} className="text-accent-primary" />
                    <span className="text-sm font-bold text-text-primary">
                        {selectedLaw ? normalizeForDisplay(selectedLaw) : t('lawSearch.selectLaw', 'Shfleto ligje specifike...')}
                    </span>
                </div>
                {loadingTitles || enrichingTitles.size > 0 ? (
                    <Loader2 className="h-4 w-4 animate-spin text-accent-primary" />
                ) : (
                    <ChevronDown size={18} className={`text-text-muted transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
                )}
                </button>

                {/* Dropdown Menu - Explicit bg-card for opacity and z-index to overlay search bar */}
                <AnimatePresence>
                {dropdownOpen && (
                    <motion.div 
                        initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
                        className="absolute z-[60] mt-2 w-full bg-card border border-border-strong rounded-xl shadow-xl max-h-72 overflow-y-auto custom-dropdown-scrollbar py-2"
                    >
                    {loadingTitles ? (
                        <div className="p-6 text-center text-text-muted font-bold text-xs uppercase tracking-widest">{t('general.loading', 'Duke ngarkuar...')}</div>
                    ) : (
                        lawTitles.map(title => (
                        <button
                            key={title}
                            onClick={() => handleLawSelect(title)}
                            className="w-full text-left px-5 py-3 hover:bg-hover text-sm font-medium text-text-primary hover:text-accent-primary transition-colors border-b border-border-main/50 last:border-0 flex items-center justify-between"
                        >
                            <span className="truncate pr-4">{normalizeForDisplay(getDisplayTitle(title))}</span>
                            {enrichingTitles.has(title) && <Loader2 className="shrink-0 h-3 w-3 animate-spin text-accent-primary" />}
                        </button>
                        ))
                    )}
                    </motion.div>
                )}
                </AnimatePresence>
            </div>

            {/* 2. Primary Deep Search Input */}
            <div className="relative group z-10">
                <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                <Search className={`h-5 w-5 transition-colors ${loading ? 'text-accent-primary animate-pulse' : 'text-text-muted group-focus-within:text-accent-primary'}`} />
                </div>
                <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('lawSearch.placeholder', 'Kërko nene, fjalë kyçe, koncepte juridike...')}
                className="w-full pl-14 pr-14 py-5 bg-input border border-border-main rounded-xl shadow-inner text-base font-medium text-text-primary placeholder:text-text-disabled focus:outline-none focus:border-accent-primary focus:ring-4 focus:ring-accent-primary/10 transition-all"
                autoFocus
                />
                {query && (
                <button
                    onClick={handleClear}
                    className="absolute inset-y-0 right-0 pr-5 flex items-center text-text-muted hover:text-status-danger transition-colors"
                >
                    <X className="h-5 w-5" />
                </button>
                )}
            </div>
        </div>

        {/* Loading Skeletons */}
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="glass-panel p-8 rounded-[1.5rem] animate-pulse bg-surface/50">
                <div className="h-6 bg-border-main rounded-md w-1/3 mb-4"></div>
                <div className="h-4 bg-border-main/50 rounded-md w-full mb-3"></div>
                <div className="h-4 bg-border-main/50 rounded-md w-5/6 mb-4"></div>
                <div className="h-4 bg-border-main/30 rounded-md w-1/4 mt-6"></div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        <AnimatePresence>
        {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel border border-status-danger/30 bg-status-danger/5 p-6 rounded-2xl flex items-start gap-4 shadow-sm mb-8">
            <AlertCircle className="h-6 w-6 text-status-danger shrink-0" />
            <p className="text-status-danger font-bold text-sm mt-0.5">{error}</p>
            </motion.div>
        )}
        </AnimatePresence>

        {/* Empty Search Results */}
        {!loading && hasSearched && groupedResults.length === 0 && query.trim() !== '' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel p-16 rounded-[2rem] text-center border-border-main shadow-sm flex flex-col items-center">
            <div className="w-20 h-20 bg-base rounded-full flex items-center justify-center mb-6">
                <BookOpen className="h-10 w-10 text-text-muted" strokeWidth={1.5} />
            </div>
            <p className="text-text-primary text-xl font-black tracking-tight mb-2 uppercase">
              {t('lawSearch.noResults', 'Nuk u gjet asnjë rezultat')}
            </p>
            <p className="text-base text-text-muted font-medium">
              {t('lawSearch.tryDifferent', 'Provo fjalë të ndryshme ose shkruaj një pyetje më të plotë.')}
            </p>
          </motion.div>
        )}

        {/* Search Results Grid */}
        {!loading && groupedResults.length > 0 && (
          <div className="space-y-6">
            <p className="text-[11px] text-text-muted font-black uppercase tracking-widest ml-2">
              {groupedResults.length} {groupedResults.length === 1 ? 'Rezultat i gjetur' : 'Rezultate të gjetura'}
            </p>
            
            {groupedResults.map((article, idx) => (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }} key={idx}>
                  <div className="glass-panel p-8 rounded-[1.5rem] hover:shadow-lg transition-all group border-border-main hover:border-accent-primary/50 bg-card">
                    <div className="flex flex-col gap-4">
                        
                        <div className="flex items-center flex-wrap gap-2 mb-1">
                            <span className="bg-accent-subtle text-accent-primary border border-accent-primary/20 px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5">
                                <Scale size={12} /> Referencë Ligjore
                            </span>
                            <span className="bg-base text-text-primary border border-border-main px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-widest">
                                Neni {article.article_number}
                            </span>
                        </div>

                        <Link
                            to={`/laws/overview?lawTitle=${encodeURIComponent(article.law_title)}`}
                            className="text-xl sm:text-2xl font-black text-text-primary group-hover:text-accent-primary transition-colors leading-tight"
                            title={t('lawSearch.viewAllArticles', 'Shiko të gjitha nenet')}
                        >
                            {article.law_title}
                        </Link>
                        
                        <p className="text-sm text-text-secondary leading-relaxed font-medium border-l-2 border-border-main pl-4">
                            {article.preview}
                        </p>
                        
                        <div className="flex items-center justify-between gap-4 mt-4 pt-6 border-t border-border-main">
                            <div className="flex items-center gap-3 text-xs flex-wrap">
                                <span className="px-3 py-1.5 bg-base border border-border-main rounded-lg text-text-muted font-bold">
                                    {article.source}
                                </span>
                                {article.chunkCount > 1 && (
                                <span className="px-3 py-1.5 bg-accent-subtle text-accent-primary rounded-lg font-black uppercase tracking-widest">
                                    {article.chunkCount} Pjesë
                                </span>
                                )}
                            </div>
                            
                            <div className="flex items-center gap-4">
                                <Link
                                    to={`/laws/overview?lawTitle=${encodeURIComponent(article.law_title)}`}
                                    className="hidden sm:flex text-[11px] font-black uppercase tracking-widest text-text-muted hover:text-text-primary transition-colors items-center gap-1.5"
                                    title={t('lawSearch.viewAllArticles', 'Të gjitha nenet e këtij ligji')}
                                >
                                    <FileText size={14} /> {t('lawSearch.viewAll', 'Të gjitha')}
                                </Link>
                                <Link
                                    to={`/laws/article?lawTitle=${encodeURIComponent(article.law_title)}&articleNumber=${encodeURIComponent(article.article_number)}`}
                                    className="text-[11px] font-black uppercase tracking-widest text-accent-primary hover:text-white hover:bg-accent-primary px-4 py-2 rounded-lg border border-accent-primary/30 hover:border-accent-primary transition-all flex items-center gap-1.5"
                                >
                                    {t('lawSearch.viewDetails', 'Lexo Nenin')} <ChevronRight size={14} />
                                </Link>
                            </div>
                        </div>
                    </div>
                  </div>
              </motion.div>
            ))}
          </div>
        )}

        {/* Initial Empty State */}
        {!loading && !error && rawResults.length === 0 && query.trim() === '' && (
          <div className="flex flex-col items-center text-center opacity-30 mt-24">
            <Search className="h-16 w-16 mb-6 text-text-muted" strokeWidth={1} />
            <p className="text-xl font-black text-text-primary uppercase tracking-widest">
                {t('lawSearch.startTyping', 'Hulumtimi Inteligjent')}
            </p>
            <p className="text-sm font-medium text-text-muted mt-2">Përdorni konzolën e kërkimit më lart për të filluar.</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}