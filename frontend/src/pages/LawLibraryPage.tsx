// FILE: src/pages/LawLibraryPage.tsx
// PHOENIX PROTOCOL - LAW LIBRARY V8.0
//
// V8.0: FIX hardcoding + endpoint jo-ekzistues + repeals.
//   - L1: HEQUR /laws/list (nuk ekziston) → kalohet në /laws/titles
//   - L2: HEQUR DEFAULT_LAWS hardcoded
//   - L3: Search pa `law_title` param (backend nuk e pranon)
//   - L4: Guard për q bosh (paraprakisht 400)
//   - L10: Shtuar repealed_statutes state (shfaqet warning)
//   - Tipizim i plotë (LawResult, TitlesResponse)
//
// V7.1: Versioni i vjetër.

import { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Search, AlertCircle, BookOpen, ArrowLeft, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import type { LawResult, RepealedStatuteItem } from '../components/law/lawLibraryTypes';
import { LawLibrarySearchCard } from '../components/law/LawLibrarySearchCard';
import { LawLibraryResultCard } from '../components/law/LawLibraryResultCard';

export default function LawLibraryPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  const [query, setQuery] = useState('');
  const [selectedLaw, setSelectedLaw] = useState('');
  const [availableLaws, setAvailableLaws] = useState<string[]>([]);
  const [repealedMap, setRepealedMap] = useState<Map<string, RepealedStatuteItem>>(new Map());

  const [results, setResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // V8.0: Ngarko listën e ligjeve nga /laws/titles (jo /laws/list)
  useEffect(() => {
    if (!isAuthenticated) return;

    const controller = new AbortController();

    (async () => {
      try {
        const response = await apiService.axiosInstance.get(
          '/laws/titles',
          { signal: controller.signal },
        );
        const data = response.data || {};

        const statutes: string[] = Array.isArray(data.statutes) ? data.statutes : [];
        const repealed: RepealedStatuteItem[] = Array.isArray(data.repealed_statutes)
          ? data.repealed_statutes
          : [];

        setAvailableLaws(statutes);

        const map = new Map<string, RepealedStatuteItem>();
        for (const item of repealed) {
          if (item?.law_title) map.set(item.law_title, item);
        }
        setRepealedMap(map);
      } catch (err: any) {
        if (err?.name === 'CanceledError' || err?.name === 'AbortError') return;
        console.warn('[LawLibrary] Failed to load law titles:', err);
        setAvailableLaws([]);
      }
    })();

    return () => controller.abort();
  }, [isAuthenticated]);

  const repealedTitlesSet = useMemo(() => new Set(repealedMap.keys()), [repealedMap]);

  const handleSearch = async () => {
    // V8.0: Guard për q bosh (backend 400)
    if (!query.trim()) {
      setError('Shkruani një fjalë kyçe për të kërkuar.');
      return;
    }
    if (!isAuthenticated) {
      setError('Duhet të jeni i identifikuar për të përdorur këtë veçori.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // V8.0: vetëm `q` + `limit` (backend nuk pranon law_title)
      const response = await apiService.axiosInstance.get<LawResult[]>(
        '/laws/search',
        { params: { q: query.trim(), limit: 50 } },
      );

      let data = Array.isArray(response.data) ? response.data : [];

      // Filtrim client-side sipas selectedLaw (backend nuk e bën)
      if (selectedLaw) {
        data = data.filter((r) => r.law_title === selectedLaw);
      }

      setResults(data);
    } catch (err: any) {
      if (err.response?.status === 401) {
        setError('Sesioni juaj ka skaduar ose nuk jeni i identifikuar. Ju lutem hyni përsëri.');
      } else if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Kërkesa nuk është e saktë.');
      } else {
        setError(
          err.response?.data?.detail ||
          err.message ||
          'Kërkimi dështoi. Provoni përsëri.',
        );
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

        {/* Warning për ligje të shfuqizuara (V8.0) */}
        {repealedMap.size > 0 && (
          <div className="mb-6 p-4 bg-warning-start/5 border border-warning-start/30 rounded-2xl flex items-start gap-3 shadow-sm">
            <AlertTriangle size={18} className="text-warning-start shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-xs font-bold text-warning-start uppercase tracking-wider mb-1">
                Njoftim: Ligje të shfuqizuara në bibliotekë
              </p>
              <p className="text-text-secondary text-xs leading-relaxed">
                {repealedMap.size} ligj(e) në bibliotekë janë shfuqizuar. Do të shfaqen me shenjë ⚠️ në listën e filtrimit.
              </p>
            </div>
          </div>
        )}

        <LawLibrarySearchCard
          selectedLaw={selectedLaw}
          onSelectedLawChange={setSelectedLaw}
          availableLaws={availableLaws}
          repealedTitles={repealedTitlesSet}
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

          {results.length === 0 && query && !loading && !error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-16 text-center"
            >
              <Search size={48} className="text-text-muted/60 mb-4" strokeWidth={1.5} />
              <p className="text-text-primary font-black text-base uppercase tracking-wider">
                Nuk u gjetën të dhëna
              </p>
              <p className="text-text-muted text-xs mt-1 font-medium max-w-md">
                Nuk ka asnjë rezultat për kërkimin tuaj. Provoni fjalë kyçe të tjera.
              </p>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}