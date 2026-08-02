// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - LAW SEARCH V18.0 (UNIFIED SEARCH WITH INLINE STATUTORY LAWS DROPDOWN - NO REDUNDANT MODALS)

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, BookOpen, AlertCircle, ChevronRight, FileText, Scale, ArrowLeft } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
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

const DEFAULT_STATUTORY_LAWS = [
  "KUSHTETUTA E REPUBLIKËS SË KOSOVËS",
  "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
  "KODI NR. 08/L-032 I PROCEDURËS PENALE",
  "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
  "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
  "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
  "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
  "LIGJI NR. 04/L-161 PËR SIGURINË DHE SHËNDETIN NË PUNË",
  "LIGJI NR. 05/L-029 PËR TATIMIN NË TË ARDHURAT E KORPORATAVE",
  "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
  "LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE",
  "LIGJI NR. 06/L-084 PËR MBROJTJEN E FËMIJËS",
  "LIGJI NR. 08/L-257 PËR ADMINISTRIMIN E PROCEDURAVE TATIMORE",
  "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS",
  "LIGJI NR. 03/L-212 I PUNËS"
];

function normalizeForDisplay(title: string): string {
  return title.trim().replace(/\s+/g, ' ');
}

function useDebounce<T extends (...args: any[]) => any>(callback: T, delay: number) {
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const debouncedCallback = useCallback((...args: Parameters<T>) => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => callback(...args), delay);
  }, [callback, delay]);
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);
  return debouncedCallback;
}

export default function LawSearchPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [rawResults, setRawResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  
  const [statuteTitles, setStatuteTitles] = useState<string[]>(DEFAULT_STATUTORY_LAWS);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiService.getLawTitles()
      .then((res: any) => {
        if (res) {
          const apiStatutes = res.statutes || res.all_titles || [];
          if (apiStatutes.length > 0) {
            const mergedStatutes = new Set([...apiStatutes, ...DEFAULT_STATUTORY_LAWS]);
            setStatuteTitles(Array.from(mergedStatutes));
          }
        }
      })
      .catch((err) => {
        console.warn("[LawSearchPage] Using default Kosovo laws fallback:", err);
      });
  }, []);

  // Close inline dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
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
    setIsDropdownOpen(false);
  };

  const handleSelectLawFromDropdown = (lawTitle: string) => {
    setIsDropdownOpen(false);
    navigate(`/laws/overview?lawTitle=${encodeURIComponent(lawTitle)}`);
  };

  // Filter statutory titles for the inline dropdown when typing
  const filteredStatutes = useMemo(() => {
    if (!query.trim()) return statuteTitles;
    const lower = query.toLowerCase();
    return statuteTitles.filter(title => normalizeForDisplay(title).toLowerCase().includes(lower));
  }, [statuteTitles, query]);

  return (
    <motion.div className="w-full min-h-screen pb-16 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-5xl mx-auto px-6 sm:px-8 pt-32">
        
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface/30 border border-border-main text-text-secondary hover:text-text-primary transition-colors hover-lift shadow-sm mb-6 group w-fit cursor-pointer"
        >
          <ArrowLeft size={16} className="transition-transform group-hover:-translate-x-1" />
          <span className="text-xs sm:text-sm font-black uppercase tracking-widest">{t('general.back', 'Kthehu')}</span>
        </button>

        {/* UNIFIED SEARCH BAR WITH INLINE LAWS DROPDOWN */}
        <div className="glass-panel p-6 sm:p-8 mb-10 shadow-sm border border-border-main flex flex-col bg-surface rounded-3xl relative" ref={dropdownRef}>
          
          <div className="relative group">
            <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
              <Search className={`h-5 w-5 transition-colors ${loading ? 'text-primary-start animate-pulse' : 'text-text-muted group-focus-within:text-primary-start'}`} />
            </div>

            <input
              type="text"
              value={query}
              onFocus={() => setIsDropdownOpen(true)}
              onChange={(e) => {
                setQuery(e.target.value);
                setIsDropdownOpen(true);
              }}
              placeholder="Kërko ligjin zyrtar ose fjalë kyçe (p.sh. Penal, Familjen, Vrasja)..."
              className="w-full pl-14 pr-14 py-5 bg-canvas border border-border-main rounded-2xl shadow-sm text-sm sm:text-base font-medium text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-4 focus:ring-primary-start/10 transition-all"
              autoFocus
            />

            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute inset-y-0 right-0 pr-5 flex items-center text-text-muted hover:text-danger-start transition-colors cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            )}
          </div>

          {/* INLINE LAWS DROPDOWN PANEL (SHOWS ON FOCUS / TYPING) */}
          <AnimatePresence>
            {isDropdownOpen && !hasSearched && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.15 }}
                className="mt-3 w-full bg-canvas border border-border-main rounded-2xl shadow-2xl overflow-hidden max-h-72 overflow-y-auto custom-scrollbar z-50 p-2"
              >
                <div className="px-3 py-2 text-[10px] font-black text-text-muted uppercase tracking-wider flex items-center gap-2 border-b border-border-main/50 mb-1">
                  <Scale size={14} className="text-primary-start" />
                  <span>Kodet dhe Ligjet Zyrtare ({filteredStatutes.length})</span>
                </div>

                {filteredStatutes.length === 0 ? (
                  <div className="p-4 text-center text-xs text-text-muted font-bold">
                    Shtypni për të kërkuar nene me fjalën "{query}"
                  </div>
                ) : (
                  filteredStatutes.map((lawTitle, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSelectLawFromDropdown(lawTitle)}
                      className="w-full text-left p-3.5 rounded-xl flex items-center justify-between text-xs sm:text-sm font-bold text-text-primary hover:bg-hover hover:text-primary-start transition-all cursor-pointer group"
                    >
                      <div className="flex items-center gap-3 min-w-0 pr-2">
                        <Scale size={16} className="text-text-muted group-hover:text-primary-start shrink-0 transition-colors" />
                        <span className="truncate">{normalizeForDisplay(lawTitle)}</span>
                      </div>
                      <ChevronRight size={16} className="text-text-muted group-hover:text-primary-start shrink-0 transition-colors" />
                    </button>
                  ))
                )}
              </motion.div>
            )}
          </AnimatePresence>

        </div>

        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="glass-panel p-8 rounded-[1.5rem] animate-pulse bg-surface/50 border border-border-main">
                <div className="h-6 bg-border-main rounded-md w-1/3 mb-4"></div>
                <div className="h-4 bg-border-main/50 rounded-md w-full mb-3"></div>
              </div>
            ))}
          </div>
        )}

        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel border border-danger-start/30 bg-danger-start/5 p-6 rounded-2xl flex items-start gap-4 shadow-sm mb-8">
              <AlertCircle className="h-6 w-6 text-danger-start shrink-0" />
              <p className="text-danger-start font-bold text-sm mt-0.5">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {!loading && hasSearched && groupedResults.length === 0 && query.trim() !== '' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel p-16 rounded-[2rem] text-center border border-border-main shadow-sm flex flex-col items-center">
            <div className="w-20 h-20 bg-canvas rounded-full flex items-center justify-center mb-6">
              <BookOpen className="h-10 w-10 text-text-muted" strokeWidth={1.5} />
            </div>
            <p className="text-text-primary text-xl font-black tracking-tight mb-2 uppercase">
              {t('lawSearch.noResults', 'Nuk u gjet asnjë rezultat')}
            </p>
          </motion.div>
        )}

        {!loading && groupedResults.length > 0 && (
          <div className="space-y-6">
            <p className="text-[11px] text-text-muted font-black uppercase tracking-widest ml-2">
              {groupedResults.length} {groupedResults.length === 1 ? 'Rezultat i gjetur' : 'Rezultate të gjetura'}
            </p>
            
            {groupedResults.map((article, idx) => (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.05 }} key={idx}>
                <div className="glass-panel p-8 rounded-[1.5rem] hover:shadow-md transition-all group border border-border-main hover:border-primary-start/50 bg-surface hover-lift">
                  <div className="flex flex-col gap-4">
                    
                    <div className="flex items-center flex-wrap gap-2 mb-1">
                      <span className="bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5">
                        <Scale size={12} /> Referencë Ligjore
                      </span>
                      <span className="bg-canvas text-text-primary border border-border-main px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-widest">
                        Neni {article.article_number}
                      </span>
                    </div>

                    <Link
                      to={`/laws/overview?lawTitle=${encodeURIComponent(article.law_title)}`}
                      className="text-xl sm:text-2xl font-black text-text-primary group-hover:text-primary-start transition-colors leading-tight"
                    >
                      {article.law_title}
                    </Link>
                    
                    <p className="text-sm text-text-secondary leading-relaxed font-medium border-l-2 border-border-main pl-4">
                      {article.preview}
                    </p>
                    
                    <div className="flex items-center justify-between gap-4 mt-4 pt-6 border-t border-border-main">
                      <div className="flex items-center gap-3 text-xs flex-wrap">
                        <span className="px-3 py-1.5 bg-canvas border border-border-main rounded-lg text-text-muted font-bold">
                          {article.source}
                        </span>
                        {article.chunkCount > 1 && (
                          <span className="px-3 py-1.5 bg-primary-start/10 text-primary-start rounded-lg font-black uppercase tracking-widest">
                            {article.chunkCount} Pjesë
                          </span>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <Link
                          to={`/laws/overview?lawTitle=${encodeURIComponent(article.law_title)}`}
                          className="hidden sm:flex text-[11px] font-black uppercase tracking-widest text-text-muted hover:text-text-primary transition-colors items-center gap-1.5"
                        >
                          <FileText size={14} /> {t('lawSearch.viewAll', 'Të gjitha')}
                        </Link>
                        <Link
                          to={`/laws/article?lawTitle=${encodeURIComponent(article.law_title)}&articleNumber=${encodeURIComponent(article.article_number)}`}
                          className="text-[11px] font-black uppercase tracking-widest text-primary-start hover:text-white hover:bg-primary-start px-4 py-2 rounded-lg border border-primary-start/30 hover:border-primary-start transition-all flex items-center gap-1.5 hover-lift shadow-sm"
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

      </div>
    </motion.div>
  );
}