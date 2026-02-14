// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - LAW SEARCH PAGE (FIXED NAVIGATION)

import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, BookOpen, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';

interface LawResult {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id: string;
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
  const [results, setResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const performSearch = useCallback(async (searchTerm: string) => {
    if (!searchTerm.trim()) {
      setResults([]);
      setHasSearched(false);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiService.searchLaws(searchTerm);
      setResults(data);
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
    setResults([]);
    setHasSearched(false);
    setError('');
  };

  return (
    <div className="max-w-5xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl sm:text-4xl font-black text-text-primary tracking-tight mb-2">
          {t('lawSearch.title', 'Biblioteka Ligjore')}
        </h1>
        <p className="text-text-secondary text-sm sm:text-base max-w-2xl">
          {t('lawSearch.subtitle', 'Kërko në të gjitha ligjet e Kosovës duke përdorur kërkim semantik. Shkruani një pyetje ose fjalë kyçe dhe ne do të gjejmë nenet më të rëndësishme për ju.')}
        </p>
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
          className="glass-input w-full pl-12 pr-12 py-4 text-base rounded-2xl transition-all"
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

      {!loading && hasSearched && results.length === 0 && query.trim() !== '' && (
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

      {!loading && results.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-text-secondary font-medium">
            {results.length} {results.length === 1 ? t('lawSearch.result', 'rezultat') : t('lawSearch.results', 'rezultate')}
          </p>
          {results.map((item) => (
            <Link
              key={item.chunk_id}
              to={`/laws/${item.chunk_id}`}
              className="glass-panel p-6 rounded-2xl hover:shadow-xl transition-all cursor-pointer group block no-underline"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <h2 className="text-xl font-bold text-text-primary group-hover:text-primary-start transition-colors mb-1">
                    {item.law_title}
                    {item.article_number && (
                      <span className="text-text-secondary ml-2 font-normal">
                        – Neni {item.article_number}
                      </span>
                    )}
                  </h2>
                  <p className="text-sm text-text-secondary mb-3 line-clamp-3">
                    {item.text}
                  </p>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="px-2 py-1 bg-white/5 rounded-full text-text-secondary">
                      {item.source}
                    </span>
                    <span className="text-primary-start group-hover:text-primary-end transition-colors font-medium">
                      {t('lawSearch.viewDetails', 'Shiko detajet')} →
                    </span>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {!loading && !error && results.length === 0 && query.trim() === '' && (
        <div className="text-center text-text-secondary/40 text-sm mt-12">
          <Search className="h-8 w-8 mx-auto mb-3 opacity-30" />
          <p>{t('lawSearch.startTyping', 'Fillo të shkruash për të kërkuar...')}</p>
        </div>
      )}
    </div>
  );
}