// FILE: src/pages/LawLibraryPage.tsx
// PHOENIX PROTOCOL - AUTHENTICATED SEARCH V1.2 (SESSION VALIDATION)
// 1. ADDED: useAuth check to ensure search only proceeds if isAuthenticated is true.
// 2. FIXED: Improved error handling for 401 Unauthorized cases.
// 3. STATUS: Protocol Compliant.

import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Search, AlertCircle, Loader2 } from 'lucide-react';

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

  // Protect the route: If not loading and not authenticated, redirect
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
        <div className="flex items-center justify-center min-h-[400px]">
            <Loader2 className="animate-spin text-indigo-600 w-8 h-8" />
        </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <Search className="text-indigo-600" />
          Biblioteka Ligjore
        </h1>
        <p className="text-gray-600 mt-2">
          Kërkoni në bazën tonë të të dhënave ligjore për nene, rregullore dhe vendime.
        </p>
      </header>
      
      {!isAuthenticated && (
          <div className="mb-6 p-4 bg-amber-50 border-l-4 border-amber-400 text-amber-800 flex items-center gap-3">
              <AlertCircle size={20} />
              <p>Ju duhet të <strong>hyni në llogari</strong> për të kryer kërkime në bibliotekë.</p>
              <Link to="/login" className="ml-auto font-bold underline hover:text-amber-900">Hyni këtu</Link>
          </div>
      )}

      <div className="flex gap-2 mb-8">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="p.sh. Kodi Civil, Neni 45, Ligji për punën..."
          disabled={!isAuthenticated}
          className="flex-1 p-3 border rounded-lg shadow-sm focus:ring-2 focus:ring-indigo-500 bg-white text-gray-900 disabled:bg-gray-100 disabled:cursor-not-allowed"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !isAuthenticated}
          className="px-6 py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition-all shadow-md disabled:opacity-50"
        >
          {loading ? 'Duke kërkuar...' : 'Kërko'}
        </button>
      </div>

      {error && (
        <div className="p-4 mb-6 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center gap-2">
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      <div className="grid gap-4">
        {results.map((r) => (
          <Link
            key={r.chunk_id}
            to={`/laws/${r.chunk_id}`}
            className="block p-5 border border-gray-200 rounded-xl hover:shadow-lg hover:border-indigo-300 transition-all bg-white group"
          >
            <h2 className="text-xl font-bold text-gray-900 group-hover:text-indigo-600 transition-colors">
                {r.law_title}
            </h2>
            {r.article_number && (
              <p className="text-indigo-700 font-medium mt-1">Neni {r.article_number}</p>
            )}
            <p className="text-sm text-gray-500 mt-3 flex items-center gap-1">
                <span className="font-semibold uppercase text-xs bg-gray-100 px-2 py-0.5 rounded">Burimi</span>
                {r.source || 'i panjohur'}
            </p>
          </Link>
        ))}
        
        {results.length === 0 && query && !loading && !error && (
            <div className="text-center py-12 text-gray-500">
                Nuk u gjet asnjë rezultat për "{query}".
            </div>
        )}
      </div>
    </div>
  );
}