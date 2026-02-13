// FILE: src/pages/LawLibraryPage.tsx
// PHOENIX PROTOCOL - API INTEGRATION V1.1 (AUTHENTICATED SEARCH)
// 1. REPLACED: Raw fetch with apiService.axiosInstance for JWT support.
// 2. FIXED: "Not authenticated" error by utilizing unified auth headers.
// 3. STATUS: Protocol Compliant.

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';

interface LawResult {
  law_title: string;
  article_number?: string;
  chunk_id: string;
  source?: string;
  text?: string;
}

export default function LawLibraryPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    
    try {
      // Utilizing the unified axios instance which handles Bearer tokens automatically
      const response = await apiService.axiosInstance.get<LawResult[]>('/laws/search', {
        params: { q: query }
      });
      
      setResults(response.data);
    } catch (err: any) {
      console.error("[LawLibrary] Search failed:", err);
      // Handle cases where err.response exists (Axios error) or generic error
      const errorMessage = err.response?.data?.detail || err.message || 'Kërkimi dështoi';
      setError(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Biblioteka Ligjore</h1>
      <p className="text-gray-600 mb-4">
        Kërkoni ligje duke përdorur fjalë kyçe, numër të ligjit, ose nen. Rezultatet janë të renditura sipas ngjashmërisë.
      </p>
      
      <div className="flex gap-2 mb-6">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          placeholder="p.sh. alimentacion, Neni 68, 04/L-077..."
          className="flex-1 p-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary-start bg-white text-gray-900"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {loading ? 'Duke kërkuar...' : 'Kërko'}
        </button>
      </div>

      {error && (
        <div className="p-3 mb-4 bg-red-50 border border-red-200 text-red-600 rounded">
          Gabim: {error}
        </div>
      )}

      {results.length === 0 && query && !loading && !error && (
        <p className="text-gray-500">Nuk u gjet asnjë rezultat.</p>
      )}

      <div className="space-y-4">
        {results.map((r) => (
          <Link
            key={r.chunk_id}
            to={`/laws/${r.chunk_id}`}
            className="block p-4 border rounded hover:shadow-md hover:border-indigo-300 transition-all bg-white"
          >
            <h2 className="text-lg font-semibold text-indigo-900">{r.law_title}</h2>
            {r.article_number && (
              <p className="text-gray-700 mt-1 font-medium">Neni {r.article_number}</p>
            )}
            <p className="text-sm text-gray-500 mt-2 italic">Burimi: {r.source || 'i panjohur'}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}