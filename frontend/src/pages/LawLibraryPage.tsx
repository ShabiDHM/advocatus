// FILE: src/pages/LawLibraryPage.tsx
// PHOENIX PROTOCOL - LAW LIBRARY V3.0 (WORLD CLASS EXECUTIVE REFINEMENT)
// 1. FIXED: Eradicated hardcoded white/gray/indigo colors. Now uses semantic tokens.
// 2. FIXED: Page dynamically adapts to Light (Courtroom) and Dark (Executive Suite) modes perfectly.
// 3. ENHANCED: Applied 'hover-lift' and 'glass-panel' architecture to search results.
// 4. UPDATED: Replaced custom shadows with 'shadow-sm' and removed hardcoded color references.
// 5. RETAINED: 100% of authentication protection and API logic.

import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Search, AlertCircle, Loader2, BookOpen, Scale, ArrowRight, Link as LinkIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface LawResult {
  law_title: string;
  article_number?: string;
  chunk_id: string;
  source?: string;
  text?: string;
}

export default function LawLibraryPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      console.warn("[LawLibrary] Unauthorized access attempt. Redirecting to login.");
      // Optional: navigate('/login');
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleSearch = async () => {
    if (!query.trim()) return;
    if (!isAuthenticated) {
        setError("Duhet të jeni i identifikuar (Logged In) për të përdorur këtë veçori.");
        return;
    }

    setLoading(true);
    setError('');
    
    try {
      const response = await apiService.axiosInstance.get<LawResult[]>('/laws/search', {
        params: { q: query }
      });
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
        <div className="flex flex-col items-center justify-center min-h-screen pt-20">
            <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
            <p className="text-text-primary font-black uppercase tracking-widest text-sm">Duke ngarkuar...</p>
        </div>
    );
  }

  return (
    <motion.div 
      className="w-full min-h-screen pb-16 bg-canvas"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="max-w-4xl mx-auto px-6 sm:px-8 pt-32">
        
        {/* Executive Page Header */}
        <header className="mb-12 flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-primary-start/10 flex items-center justify-center text-primary-start shadow-sm">
              <BookOpen size={24} />
            </div>
            <h1 className="text-4xl font-black text-text-primary tracking-tighter leading-none">
              Biblioteka Ligjore
            </h1>
          </div>
          <p className="text-text-secondary text-lg ml-1 font-medium max-w-2xl leading-relaxed">
            Kërkoni në bazën e të dhënave ligjore për nene, rregullore dhe vendime me saktësi AI.
          </p>
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

        {/* High-Fidelity Search Bar */}
        <div className="relative mb-12 group">
          <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
            <Search className={`h-6 w-6 transition-colors ${loading ? 'text-primary-start animate-pulse' : 'text-primary-start/50 group-focus-within:text-primary-start'}`} />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Kërkoni (p.sh. Kodi Civil, Neni 45)..."
            disabled={!isAuthenticated}
            className="w-full pl-14 pr-32 py-5 bg-surface border-2 border-border-main rounded-[1.5rem] shadow-sm text-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-4 focus:ring-primary-start/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <div className="absolute inset-y-0 right-3 flex items-center">
            <button
              onClick={handleSearch}
              disabled={loading || !isAuthenticated || !query.trim()}
              className="btn-primary h-10 px-8 disabled:opacity-30 disabled:hover:brightness-100 hover-lift shadow-sm"
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : 'KËRKO'}
            </button>
          </div>
        </div>

        {/* Error State */}
        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="p-5 mb-8 bg-danger-start/10 border border-danger-start/30 text-danger-start rounded-2xl flex items-center gap-3 shadow-sm">
              <AlertCircle size={20} className="shrink-0" />
              <span className="font-bold text-sm tracking-wide">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Search Results Grid */}
        <div className="space-y-6">
          {results.map((r, index) => (
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                key={r.chunk_id}
            >
                <Link
                to={`/laws/${r.chunk_id}`}
                className="glass-panel p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-6 group hover-lift border border-border-main hover:border-primary-start/50"
                >
                <div className="flex flex-col gap-3 flex-1 min-w-0">
                    
                    <div className="flex flex-wrap items-center gap-3">
                        <span className="bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5">
                            <Scale size={12} /> Referencë Ligjore
                        </span>
                        {r.article_number && (
                            <span className="bg-canvas text-text-primary border border-border-main px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-widest">
                                Neni {r.article_number}
                            </span>
                        )}
                    </div>

                    <h2 className="text-xl sm:text-2xl font-black text-text-primary group-hover:text-primary-start transition-colors truncate">
                        {r.law_title}
                    </h2>
                    
                    <div className="flex items-center gap-2 mt-1">
                        <LinkIcon size={14} className="text-text-muted" />
                        <span className="text-xs font-bold text-text-muted uppercase tracking-widest truncate max-w-md">
                            {r.source || 'Burim i panjohur'}
                        </span>
                    </div>
                </div>

                <div className="hidden sm:flex w-12 h-12 rounded-2xl bg-canvas border border-border-main items-center justify-center text-text-muted group-hover:text-white group-hover:bg-primary-start group-hover:border-primary-start group-hover:shadow-sm transition-all shrink-0">
                    <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
                </div>
                </Link>
            </motion.div>
          ))}
          
          {/* Empty State */}
          {results.length === 0 && query && !loading && !error && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center py-20 opacity-40">
                  <Search size={64} className="text-text-muted mb-6" strokeWidth={1.5} />
                  <p className="text-text-primary font-black text-lg uppercase tracking-widest text-center">Nuk u gjetën të dhëna</p>
                  <p className="text-text-muted text-sm mt-2 font-medium">Nuk ka asnjë rezultat për termat "{query}". Provoni fjalë kyçe të tjera.</p>
              </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}