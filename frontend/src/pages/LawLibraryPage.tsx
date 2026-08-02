// FILE: src/pages/LawLibraryPage.tsx
// PHOENIX PROTOCOL - LAW LIBRARY V5.0 (PORTAL-BASED FLOATING DROPDOWN MENU)

import { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  Search, AlertCircle, Loader2, BookOpen, Scale, ArrowRight, 
  Link as LinkIcon, ArrowLeft, Filter, ChevronDown, Check, X 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface LawResult {
  law_title: string;
  article_number?: string;
  chunk_id: string;
  source?: string;
  text?: string;
}

const DEFAULT_LAWS = [
  "Kodi Penal i Republikës së Kosovës",
  "Kodi i Procedurës Penale",
  "Kodi Civil i Republikës së Kosovës",
  "Ligji për Marrëdhëniet e Detyrimeve",
  "Ligji për Familjen i Kosovës",
  "Ligji i Punës",
  "Ligji për Mbrojtjen e të Dhënave Personale",
  "Ligji për Shoqëritë Tregtare"
];

export default function LawLibraryPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  
  const [query, setQuery] = useState('');
  const [selectedLaw, setSelectedLaw] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [availableLaws, setAvailableLaws] = useState<string[]>(DEFAULT_LAWS);
  const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number; width: number } | null>(null);

  const [results, setResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const dropdownContainerRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Measure button bounds for portal positioning
  const updateDropdownPosition = () => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setDropdownPos({
        top: rect.bottom + 8,
        left: rect.left,
        width: rect.width,
      });
    }
  };

  const toggleDropdown = () => {
    if (!isDropdownOpen) {
      updateDropdownPosition();
    }
    setIsDropdownOpen(!isDropdownOpen);
  };

  // Close dropdown on outside click or scroll
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        dropdownContainerRef.current && !dropdownContainerRef.current.contains(target) &&
        buttonRef.current && !buttonRef.current.contains(target)
      ) {
        setIsDropdownOpen(false);
      }
    };

    const handleScrollOrResize = () => {
      if (isDropdownOpen) {
        updateDropdownPosition();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('scroll', handleScrollOrResize, true);
    window.addEventListener('resize', handleScrollOrResize);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('scroll', handleScrollOrResize, true);
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [isDropdownOpen]);

  // Fetch registered laws list on mount
  useEffect(() => {
    const fetchLawsList = async () => {
      try {
        const response = await apiService.axiosInstance.get<string[]>('/laws/list');
        if (response.data && response.data.length > 0) {
          setAvailableLaws(response.data);
        }
      } catch (err) {
        // Fallback to DEFAULT_LAWS
      }
    };
    if (isAuthenticated) {
      fetchLawsList();
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      console.warn("[LawLibrary] Unauthorized access attempt. Redirecting to login.");
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleSearch = async () => {
    if (!query.trim() && !selectedLaw) return;
    if (!isAuthenticated) {
        setError("Duhet të jeni i identifikuar për të përdorur këtë veçori.");
        return;
    }

    setLoading(true);
    setError('');
    
    try {
      const params: any = {};
      if (query.trim()) params.q = query.trim();
      if (selectedLaw) params.law_title = selectedLaw;

      const response = await apiService.axiosInstance.get<LawResult[]>('/laws/search', { params });
      setResults(response.data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        setError("Sesioni juaj ka skaduar ose nuk jeni i identifikuar. Ju lutem hyni përsëri.");
      } else {
        setError(err.response?.data?.detail || "Kërkimi dështoi. Provoni përsëri.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (isLoading) {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen pt-20 bg-canvas">
            <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
            <p className="text-text-primary font-black uppercase tracking-widest text-sm">Duke ngarkuar...</p>
        </div>
    );
  }

  return (
    <motion.div 
      className="w-full min-h-screen pb-16 bg-canvas text-text-primary"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {/* STANDARDIZED EXECUTIVE MAX-W-7XL CONTAINER */}
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        
        {/* Back Navigation Button */}
        <div className="mb-6">
          <button
            onClick={() => navigate(-1)}
            className="group inline-flex items-center gap-2.5 px-4 py-2 rounded-xl bg-surface border border-main text-text-primary hover:border-primary-start/60 transition-all shadow-sm text-xs font-black uppercase tracking-wider hover-lift cursor-pointer"
          >
            <ArrowLeft size={16} className="text-primary-start" />
            <span>Kthehu</span>
          </button>
        </div>

        {/* Executive Page Header */}
        <header className="mb-8 sm:mb-10 flex flex-col gap-3">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-primary-start/10 flex items-center justify-center text-primary-start border border-primary-start/20 shadow-sm shrink-0">
              <BookOpen size={24} />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-black text-text-primary tracking-tight uppercase leading-none">
                Biblioteka Ligjore
              </h1>
              <p className="text-text-secondary text-xs sm:text-sm font-medium mt-1 leading-relaxed">
                Kërkoni në bazën e të dhënave ligjore të Republikës së Kosovës për nene, rregullore dhe kodet zyrtare.
              </p>
            </div>
          </div>
        </header>
        
        {/* Authentication Warning State */}
        {!isAuthenticated && (
            <div className="mb-8 p-5 bg-warning-start/10 border border-warning-start/30 text-warning-start rounded-2xl flex items-center gap-4 shadow-sm">
                <AlertCircle size={24} className="shrink-0" />
                <div className="flex flex-col gap-1">
                    <p className="text-sm font-bold uppercase tracking-widest">Qasje e Kufizuar</p>
                    <p className="text-text-primary font-medium">Ju duhet të hyni në llogari për të kryer kërkime në bibliotekë.</p>
                </div>
                <Link to="/login" className="ml-auto btn-primary px-6 py-2.5 hover-lift shadow-sm">Hyni Këtu</Link>
            </div>
        )}

        {/* SEARCH & FILTER CARD CONTAINER */}
        <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-main bg-surface shadow-sm mb-10">
          
          <div className="flex flex-col gap-4">
            
            {/* 1. SELECT LAW DROPDOWN BUTTON */}
            <div className="relative" ref={dropdownContainerRef}>
              <button
                ref={buttonRef}
                type="button"
                onClick={toggleDropdown}
                disabled={!isAuthenticated}
                className="w-full flex items-center justify-between px-5 py-4 bg-canvas border border-main hover:border-primary-start/60 rounded-2xl shadow-sm text-xs sm:text-sm font-bold text-text-primary transition-all focus:outline-none focus:ring-2 focus:ring-primary-start/20 disabled:opacity-50 cursor-pointer"
              >
                <div className="flex items-center gap-3 min-w-0 pr-2">
                  <Filter size={18} className="text-primary-start shrink-0" />
                  <span className="truncate">
                    {selectedLaw ? selectedLaw : "Zgjidh një ligj"}
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {selectedLaw && (
                    <span 
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedLaw('');
                      }}
                      className="p-1 hover:bg-hover rounded-lg text-text-muted hover:text-danger-start transition-colors"
                      title="Hiq filtrin"
                    >
                      <X size={16} />
                    </span>
                  )}
                  <ChevronDown size={18} className={`text-text-muted transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} />
                </div>
              </button>
            </div>

            {/* 2. HIGH-FIDELITY SEARCH BAR */}
            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                <Search className={`h-5 w-5 transition-colors ${loading ? 'text-primary-start animate-pulse' : 'text-primary-start/60 group-focus-within:text-primary-start'}`} />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Kërko nene, fjalë kyçe, koncepte juridike..."
                disabled={!isAuthenticated}
                className="w-full pl-13 pr-36 py-4 bg-canvas border border-main rounded-2xl shadow-sm text-sm sm:text-base text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <div className="absolute inset-y-0 right-2.5 flex items-center">
                <button
                  type="button"
                  onClick={handleSearch}
                  disabled={loading || !isAuthenticated || (!query.trim() && !selectedLaw)}
                  className="h-10 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider disabled:opacity-30 transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : 'KËRKO'}
                </button>
              </div>
            </div>

          </div>

        </div>

        {/* Error State */}
        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="p-4 mb-8 bg-danger-start/10 border border-danger-start/30 text-danger-start rounded-2xl flex items-center gap-3 shadow-sm">
              <AlertCircle size={18} className="shrink-0" />
              <span className="font-bold text-xs tracking-wide">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Search Results Grid */}
        <div className="space-y-4">
          {results.map((r, index) => {
            const articleNum = r.article_number || '1';
            const articleUrl = `/laws/article?lawTitle=${encodeURIComponent(r.law_title)}&articleNumber=${encodeURIComponent(articleNum)}`;

            return (
              <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.04 }}
                  key={r.chunk_id || index}
              >
                  <Link
                    to={articleUrl}
                    className="glass-panel p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 group hover-lift border border-main hover:border-primary-start/60 rounded-2xl bg-surface"
                  >
                    <div className="flex flex-col gap-2 flex-1 min-w-0">
                        
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="bg-primary-start/10 text-primary-start border border-primary-start/20 px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5">
                                <Scale size={12} /> Referencë Ligjore
                            </span>
                            {r.article_number && (
                                <span className="bg-canvas text-text-primary border border-main px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider">
                                    Neni {r.article_number}
                                </span>
                            )}
                        </div>

                        <h2 className="text-base sm:text-lg font-black text-text-primary group-hover:text-primary-start transition-colors truncate">
                            {r.law_title}
                        </h2>

                        {r.text && (
                          <p className="text-xs sm:text-sm text-text-secondary line-clamp-2 leading-relaxed">
                            {r.text}
                          </p>
                        )}
                        
                        {r.source && (
                          <div className="flex items-center gap-2 mt-0.5">
                              <LinkIcon size={12} className="text-text-muted" />
                              <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider truncate max-w-xl">
                                  {r.source}
                              </span>
                          </div>
                        )}
                    </div>

                    <div className="hidden sm:flex w-10 h-10 rounded-xl bg-canvas border border-main items-center justify-center text-text-muted group-hover:text-white group-hover:bg-primary-start group-hover:border-primary-start transition-all shrink-0">
                        <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </Link>
              </motion.div>
            );
          })}
          
          {/* Empty State */}
          {results.length === 0 && (query || selectedLaw) && !loading && !error && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center py-16 text-center">
                  <Search size={48} className="text-text-muted/60 mb-4" strokeWidth={1.5} />
                  <p className="text-text-primary font-black text-base uppercase tracking-wider">Nuk u gjetën të dhëna</p>
                  <p className="text-text-muted text-xs mt-1 font-medium max-w-md">Nuk ka asnjë rezultat për kërkimin tuaj. Provoni fjalë kyçe të tjera ose hiqni filtrin e ligjit.</p>
              </motion.div>
          )}
        </div>
      </div>

      {/* PORTAL FLOATING DROPDOWN POPUP MENU (Z-[9999] DIRECT BODY PORTAL) */}
      {isDropdownOpen && dropdownPos && ReactDOM.createPortal(
        <AnimatePresence>
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.12 }}
            style={{
              position: 'fixed',
              top: `${dropdownPos.top}px`,
              left: `${dropdownPos.left}px`,
              width: `${dropdownPos.width}px`,
            }}
            className="z-[9999] bg-surface border border-main rounded-2xl shadow-2xl max-h-72 overflow-y-auto custom-scrollbar p-2 space-y-1 backdrop-blur-xl"
          >
            <button
              type="button"
              onClick={() => {
                setSelectedLaw('');
                setIsDropdownOpen(false);
              }}
              className={`w-full text-left px-4 py-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-between transition-colors ${
                !selectedLaw ? 'bg-primary-start/10 text-primary-start' : 'hover:bg-hover text-text-primary'
              }`}
            >
              <span>Të gjitha ligjet (Të gjithë artikujt)</span>
              {!selectedLaw && <Check size={16} className="text-primary-start" />}
            </button>

            <div className="my-1 border-t border-main/60" />

            {availableLaws.map((lawName, idx) => {
              const isSelected = selectedLaw === lawName;
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setSelectedLaw(lawName);
                    setIsDropdownOpen(false);
                  }}
                  className={`w-full text-left px-4 py-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-between transition-colors truncate ${
                    isSelected ? 'bg-primary-start/10 text-primary-start' : 'hover:bg-hover text-text-primary'
                  }`}
                >
                  <span className="truncate pr-2">{lawName}</span>
                  {isSelected && <Check size={16} className="text-primary-start shrink-0" />}
                </button>
              );
            })}
          </motion.div>
        </AnimatePresence>,
        document.body
      )}

    </motion.div>
  );
}