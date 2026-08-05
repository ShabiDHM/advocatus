// FILE: src/pages/LawLibraryPage.tsx
// PHOENIX PROTOCOL - LAW LIBRARY V7.1 (DECOUPLED & MODULARIZED ATOMIC ARCHITECTURE)

import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Search, AlertCircle, BookOpen, ArrowLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { LawResult, DEFAULT_LAWS } from '../components/law/lawLibraryTypes';
import { LawLibrarySearchCard } from '../components/law/LawLibrarySearchCard';
import { LawLibraryResultCard } from '../components/law/LawLibraryResultCard';

export default function LawLibraryPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [selectedLaw, setSelectedLaw] = useState('');
  const [availableLaws, setAvailableLaws] = useState<string[]>(DEFAULT_LAWS);

  const [results, setResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchLawsList = async () => {
      try {
        const response = await apiService.axiosInstance.get('/laws/list');
        let fetched: string[] = [];

        if (Array.isArray(response.data)) {
          fetched = response.data;
        } else if (response.data && Array.isArray(response.data.laws)) {
          fetched = response.data.laws;
        } else if (response.data && Array.isArray(response.data.data)) {
          fetched = response.data.data;
        }

        if (fetched.length > 0) {
          setAvailableLaws(fetched);
        }
      } catch {
        console.warn('[LawLibrary] Using default Kosovo laws list fallback');
      }
    };

    if (isAuthenticated) {
      fetchLawsList();
    }
  }, [isAuthenticated]);

  const handleSearch = async () => {
    if (!query.trim() && !selectedLaw) return;
    if (!isAuthenticated) {
      setError('Duhet të jeni i identifikuar për të përdorur këtë veçori.');
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
        setError('Sesioni juaj ka skaduar ose nuk jeni i identifikuar. Ju lutem hyni përsëri.');
      } else {
        setError(err.response?.data?.detail || 'Kërkimi dështoi. Provoni përsëri.');
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
    <motion.div className="w-full min-h-screen pb-16 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        <div className="mb-6">
          <button
            onClick={() => navigate(-1)}
            className="group inline-flex items-center gap-2.5 px-4 py-2 rounded-xl bg-surface border border-main text-text-primary hover:border-primary-start/60 transition-all shadow-sm text-xs font-black uppercase tracking-wider hover-lift cursor-pointer"
          >
            <ArrowLeft size={16} className="text-primary-start" />
            <span>Kthehu</span>
          </button>
        </div>

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

        {!isAuthenticated && (
          <div className="mb-8 p-5 bg-warning-start/10 border border-warning-start/30 text-warning-start rounded-2xl flex items-center gap-4 shadow-sm">
            <AlertCircle size={24} className="shrink-0" />
            <div className="flex flex-col gap-1">
              <p className="text-sm font-bold uppercase tracking-widest">Qasje e Kufizuar</p>
              <p className="text-text-primary font-medium">Ju duhet të hyni në llogari për të kryer kërkime në bibliotekë.</p>
            </div>
            <Link to="/login" className="ml-auto btn-primary px-6 py-2.5 hover-lift shadow-sm">
              Hyni Këtu
            </Link>
          </div>
        )}

        <LawLibrarySearchCard
          selectedLaw={selectedLaw}
          onSelectedLawChange={setSelectedLaw}
          availableLaws={availableLaws}
          query={query}
          onQueryChange={setQuery}
          onSearch={handleSearch}
          loading={loading}
          isAuthenticated={isAuthenticated}
        />

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="p-4 mb-8 bg-danger-start/10 border border-danger-start/30 text-danger-start rounded-2xl flex items-center gap-3 shadow-sm"
            >
              <AlertCircle size={18} className="shrink-0" />
              <span className="font-bold text-xs tracking-wide">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="space-y-4">
          {results.map((r, index) => (
            <LawLibraryResultCard key={r.chunk_id || index} result={r} index={index} />
          ))}

          {results.length === 0 && (query || selectedLaw) && !loading && !error && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center justify-center py-16 text-center">
              <Search size={48} className="text-text-muted/60 mb-4" strokeWidth={1.5} />
              <p className="text-text-primary font-black text-base uppercase tracking-wider">Nuk u gjetën të dhëna</p>
              <p className="text-text-muted text-xs mt-1 font-medium max-w-md">
                Nuk ka asnjë rezultat për kërkimin tuaj. Provoni fjalë kyçe të tjera ose hiqni filtrin e ligjit.
              </p>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}