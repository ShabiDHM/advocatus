// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - LAW SEARCH V12.0 (DUAL-TAB STATUTORY & ACADEMY SELECTOR)

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, BookOpen, AlertCircle, ChevronRight, FileText, ChevronDown, Loader2, Scale, Filter, ArrowLeft, Check, GraduationCap } from 'lucide-react';
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

// 15 Official Statutory Laws Present in data/laws/ks
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

// 13 Academy Judicial Commentaries & Guides
const DEFAULT_ACADEMY_MANUALS = [
  "AKADEMIA E DREJTËSISË - Praktika Gjyqësore e Kosovës (Case Law Kosovo)",
  "AKADEMIA E DREJTËSISË - Konkluzionet për Unifikim të Praktikës Gjyqësore",
  "AKADEMIA E DREJTËSISË - Komentari i Kodit Penal (Kosovo Commentary)",
  "AKADEMIA E DREJTËSISË - Doracak dhe Udhëzues Praktik për Gjyqtarë",
  "AKADEMIA E DREJTËSISË - Masat e Veçanta Hetimore (Special Investigative Measures)",
  "AKADEMIA E DREJTËSISË - Udhëzues Praktik mbi Drejtësinë Mjedisore",
  "AKADEMIA E DREJTËSISË - Instituti Gjyqësor dhe Departamenti për Shërbime Ligjore",
  "AKADEMIA E DREJTËSISË - Udhëzues Praktik mbi Qasjen në Drejtësi"
];

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
  const [academyTitles, setAcademyTitles] = useState<string[]>(DEFAULT_ACADEMY_MANUALS);
  const [loadingTitles, setLoadingTitles] = useState(false);
  const [selectedLaw, setSelectedLaw] = useState<string>('');
  
  const [isLawPickerOpen, setIsLawPickerOpen] = useState(false);
  const [pickerTab, setPickerTab] = useState<'statutes' | 'academy'>('statutes');
  const [lawSearchFilter, setLawSearchFilter] = useState('');
  
  const [enrichedTitles, setEnrichedTitles] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    setLoadingTitles(true);
    apiService.getLawTitles()
      .then(async (res: any) => {
        if (res) {
          const apiStatutes = res.statutes || res.all_titles || [];
          const apiAcademy = res.academic_manuals || [];

          if (apiStatutes.length > 0) {
            const mergedStatutes = new Set([...apiStatutes, ...DEFAULT_STATUTORY_LAWS]);
            setStatuteTitles(Array.from(mergedStatutes));
          }
          if (apiAcademy.length > 0) {
            const mergedAcademy = new Set([...apiAcademy, ...DEFAULT_ACADEMY_MANUALS]);
            setAcademyTitles(Array.from(mergedAcademy));
          }
        }
      })
      .catch((err) => {
        console.warn("[LawSearchPage] Using default Kosovo laws list fallback:", err);
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
    if (!lawTitle) return;
    setSelectedLaw(lawTitle);
    window.location.href = `/laws/overview?lawTitle=${encodeURIComponent(lawTitle)}`;
  };

  const getDisplayTitle = (original: string): string => {
    return enrichedTitles.has(original) ? enrichedTitles.get(original)! : original;
  };

  const activePickerList = pickerTab === 'statutes' ? statuteTitles : academyTitles;

  const filteredPickerTitles = useMemo(() => {
    if (!lawSearchFilter.trim()) return activePickerList;
    const lowerFilter = lawSearchFilter.toLowerCase();
    return activePickerList.filter(t => normalizeForDisplay(getDisplayTitle(t)).toLowerCase().includes(lowerFilter));
  }, [activePickerList, lawSearchFilter, enrichedTitles]);

  return (
    <motion.div className="w-full min-h-screen pb-16 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-5xl mx-auto px-6 sm:px-8 pt-32">
        
        {/* Navigation - Back Button */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface/30 border border-border-main text-text-secondary hover:text-text-primary transition-colors hover-lift shadow-sm mb-6 group w-fit cursor-pointer"
        >
          <ArrowLeft size={16} className="transition-transform group-hover:-translate-x-1" />
          <span className="text-xs sm:text-sm font-black uppercase tracking-widest">{t('general.back', 'Kthehu')}</span>
        </button>

        {/* Search Console Container */}
        <div className="glass-panel p-8 sm:p-10 mb-16 shadow-sm border border-border-main flex flex-col gap-6 bg-surface rounded-3xl">
            
            {/* 1. POLISHED LAW SELECTOR BUTTON */}
            <button
              type="button"
              onClick={() => setIsLawPickerOpen(true)}
              disabled={loadingTitles}
              className="w-full flex items-center justify-between px-6 py-5 bg-canvas border border-border-main hover:border-primary-start/60 rounded-2xl shadow-sm text-sm font-bold text-text-primary transition-all group hover-lift cursor-pointer relative"
            >
              <div className="flex items-center gap-3.5 min-w-0 pr-4">
                <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl shrink-0 border border-primary-start/20">
                  <Filter size={18} />
                </div>
                <span className="truncate text-left font-bold text-sm text-text-primary">
                  {selectedLaw ? normalizeForDisplay(getDisplayTitle(selectedLaw)) : "Zgjidh një ligj apo udhëzues..."}
                </span>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {selectedLaw && (
                  <span
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedLaw('');
                    }}
                    className="p-1.5 hover:bg-hover rounded-lg text-text-muted hover:text-danger-start transition-colors"
                    title="Hiq filtrin"
                  >
                    <X size={16} />
                  </span>
                )}
                {loadingTitles ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary-start" />
                ) : (
                  <ChevronDown size={18} className="text-text-muted group-hover:text-primary-start transition-colors" />
                )}
              </div>
            </button>

            {/* 2. Primary Deep Search Input */}
            <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                  <Search className={`h-5 w-5 transition-colors ${loading ? 'text-primary-start animate-pulse' : 'text-text-muted group-focus-within:text-primary-start'}`} />
                </div>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t('lawSearch.placeholder', 'Kërko nene, fjalë kyçe, koncepte juridike...')}
                  className="w-full pl-14 pr-14 py-6 bg-canvas border border-border-main rounded-2xl shadow-sm text-base font-medium text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-4 focus:ring-primary-start/10 transition-all"
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
        </div>

        {/* Results / Loading States */}
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

        {/* Error State */}
        <AnimatePresence>
        {error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-panel border border-danger-start/30 bg-danger-start/5 p-6 rounded-2xl flex items-start gap-4 shadow-sm mb-8">
            <AlertCircle className="h-6 w-6 text-danger-start shrink-0" />
            <p className="text-danger-start font-bold text-sm mt-0.5">{error}</p>
            </motion.div>
        )}
        </AnimatePresence>

        {/* Empty Search Results */}
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

        {/* Full Search Results Grid */}
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

        {!loading && !error && rawResults.length === 0 && query.trim() === '' && (
          <div className="h-32" />
        )}
      </div>

      {/* EXECUTIVE SEARCHABLE LAW SELECTION MODAL WITH DUAL TABS */}
      <AnimatePresence>
        {isLawPickerOpen && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-[9999] flex items-center justify-center p-3 sm:p-6">
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 12 }}
              transition={{ duration: 0.2 }}
              className="bg-canvas border border-border-main w-full max-w-xl rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh] text-text-primary"
            >
              {/* Modal Header */}
              <div className="p-5 sm:p-6 border-b border-border-main flex items-center justify-between bg-surface shrink-0">
                <div className="flex items-center gap-3.5">
                  <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl border border-primary-start/20 shrink-0">
                    <BookOpen size={22} />
                  </div>
                  <div>
                    <h3 className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight">Zgjidh Ligjin apo Udhëzuesin</h3>
                    <p className="text-xs text-text-muted font-medium">Zgjidh nga Kodet Zyrtare ose Praktika e Akademisë</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsLawPickerOpen(false)}
                  className="p-2.5 hover:bg-hover rounded-xl text-text-muted hover:text-text-primary transition-colors cursor-pointer border border-transparent hover:border-border-main"
                >
                  <X size={20} />
                </button>
              </div>

              {/* DUAL-TAB SWITCHER (LIGJET ZYRTARE vs UDHËZUESIT E AKADEMISË) */}
              <div className="flex border-b border-border-main bg-canvas p-2 gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setPickerTab('statutes')}
                  className={`flex-1 py-3 px-3 rounded-xl text-xs font-black uppercase tracking-wider flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    pickerTab === 'statutes'
                      ? 'bg-primary-start text-white shadow-md'
                      : 'bg-surface text-text-muted hover:text-text-primary border border-border-main'
                  }`}
                >
                  <Scale size={16} />
                  <span>📜 Ligjet Zyrtare ({statuteTitles.length})</span>
                </button>

                <button
                  type="button"
                  onClick={() => setPickerTab('academy')}
                  className={`flex-1 py-3 px-3 rounded-xl text-xs font-black uppercase tracking-wider flex items-center justify-center gap-2 transition-all cursor-pointer ${
                    pickerTab === 'academy'
                      ? 'bg-primary-start text-white shadow-md'
                      : 'bg-surface text-text-muted hover:text-text-primary border border-border-main'
                  }`}
                >
                  <GraduationCap size={16} />
                  <span>📚 Akademia ({academyTitles.length})</span>
                </button>
              </div>

              {/* Modal Search Filter Input */}
              <div className="p-4 border-b border-border-main bg-surface shrink-0">
                <div className="relative">
                  <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-primary-start pointer-events-none" />
                  <input
                    type="text"
                    value={lawSearchFilter}
                    onChange={(e) => setLawSearchFilter(e.target.value)}
                    placeholder={pickerTab === 'statutes' ? "Kërko emrin e ligjit (p.sh. Penal, Civil, Familjen)..." : "Kërko udhëzuesin ose komentarin e Akademisë..."}
                    className="w-full pl-11 pr-10 py-3.5 bg-canvas border border-border-main rounded-xl text-xs sm:text-sm font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all"
                    autoFocus
                  />
                  {lawSearchFilter && (
                    <button
                      type="button"
                      onClick={() => setLawSearchFilter('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary p-1 rounded-lg"
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Modal Scrollable Law List */}
              <div className="p-4 overflow-y-auto custom-scrollbar flex-1 space-y-2 bg-canvas min-h-[260px] max-h-[50vh]">
                {/* All Option */}
                <button
                  type="button"
                  onClick={() => {
                    setSelectedLaw('');
                    setIsLawPickerOpen(false);
                  }}
                  className={`w-full text-left p-4 rounded-2xl flex items-center justify-between text-xs sm:text-sm font-bold transition-all shadow-xs cursor-pointer ${
                    !selectedLaw 
                      ? 'bg-primary-start/15 text-primary-start border-2 border-primary-start/40' 
                      : 'bg-surface hover:bg-hover text-text-primary border border-border-main hover:border-primary-start/40'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {pickerTab === 'statutes' ? <Scale size={18} className="text-primary-start" /> : <GraduationCap size={18} className="text-primary-start" />}
                    <span className="truncate">{pickerTab === 'statutes' ? "Të gjitha ligjet zyrtare" : "Të gjithë udhëzuesit e Akademisë"}</span>
                  </div>
                  {!selectedLaw && <Check size={18} className="text-primary-start shrink-0 ml-2" />}
                </button>

                <div className="my-3 border-t border-border-main/60" />

                {filteredPickerTitles.length === 0 ? (
                  <div className="p-10 text-center text-text-muted text-xs font-bold uppercase tracking-wider bg-surface rounded-2xl border border-border-main">
                    Nuk u gjet asnjë dokument me këtë emër
                  </div>
                ) : (
                  filteredPickerTitles.map((title, idx) => {
                    const isSelected = selectedLaw === title;
                    const displayTitle = normalizeForDisplay(getDisplayTitle(title));

                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => {
                          handleLawSelect(title);
                          setIsLawPickerOpen(false);
                        }}
                        className={`w-full text-left p-4 rounded-2xl flex items-center justify-between text-xs sm:text-sm font-bold transition-all group shadow-xs cursor-pointer ${
                          isSelected 
                            ? 'bg-primary-start/15 text-primary-start border-2 border-primary-start/40' 
                            : 'bg-surface hover:bg-hover text-text-primary border border-border-main hover:border-primary-start/40'
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0 pr-3">
                          {pickerTab === 'statutes' ? (
                            <Scale size={18} className={`shrink-0 ${isSelected ? 'text-primary-start' : 'text-text-muted group-hover:text-primary-start'}`} />
                          ) : (
                            <GraduationCap size={18} className={`shrink-0 ${isSelected ? 'text-primary-start' : 'text-text-muted group-hover:text-primary-start'}`} />
                          )}
                          <span className="truncate leading-relaxed">{displayTitle}</span>
                        </div>
                        {isSelected && <Check size={18} className="text-primary-start shrink-0 ml-2" />}
                      </button>
                    );
                  })
                )}
              </div>

              {/* Modal Footer */}
              <div className="p-4 border-t border-border-main bg-surface flex justify-end items-center text-xs text-text-muted font-bold shrink-0">
                <button
                  type="button"
                  onClick={() => setIsLawPickerOpen(false)}
                  className="px-6 py-2.5 rounded-xl bg-canvas border border-border-main text-text-primary hover:bg-hover transition-colors cursor-pointer shadow-xs font-bold"
                >
                  Mbyll
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </motion.div>
  );
}