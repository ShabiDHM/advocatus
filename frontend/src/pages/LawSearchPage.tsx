// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - LAW SEARCH PAGE

import React, { useState } from 'react';
import { apiService } from '../services/api';

interface LawResult {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id: string;
}

export default function LawSearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<LawResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiService.searchLaws(query);
      setResults(data);
    } catch (err: any) {
      setError(err.message || 'Kërkimi dështoi.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Kërko në Ligje</h1>
      <form onSubmit={handleSearch} className="mb-8">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Fut fjalë kyçe..."
            className="flex-1 p-3 rounded-lg border border-gray-300 bg-white/5 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-primary-start"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-lg font-semibold disabled:opacity-50"
          >
            {loading ? 'Duke kërkuar...' : 'Kërko'}
          </button>
        </div>
      </form>

      {error && <p className="text-red-500 mb-4">{error}</p>}

      <div className="space-y-4">
        {results.map((item) => (
          <div
            key={item.chunk_id}
            className="p-4 bg-white/5 backdrop-blur-sm rounded-lg border border-white/10 hover:border-primary-start/50 transition-colors cursor-pointer"
            onClick={() => window.location.href = `/laws/${item.chunk_id}`}
          >
            <h2 className="text-lg font-semibold text-white">
              {item.law_title} {item.article_number && `– Neni ${item.article_number}`}
            </h2>
            <p className="text-sm text-gray-400 mt-1 line-clamp-2">{item.text}</p>
            <p className="text-xs text-gray-500 mt-2">Burimi: {item.source}</p>
          </div>
        ))}
      </div>
    </div>
  );
}