// FILE: src/pages/LawLibraryPage.tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';

interface LawResult {
  law_title: string;
  article_number?: string;
  chunk_id: string;
  source?: string;
  text?: string;  // optional preview
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
      const res = await fetch(`/api/v1/laws/search?q=${encodeURIComponent(query)}`, {
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.text();
        throw new Error(err || 'Kërkimi dështoi');
      }
      const data = await res.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message);
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
          className="flex-1 p-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary-start"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-primary-start text-white rounded hover:bg-primary-end transition-colors disabled:opacity-50"
        >
          {loading ? 'Duke kërkuar...' : 'Kërko'}
        </button>
      </div>

      {error && <p className="text-red-600 mb-4">Gabim: {error}</p>}

      {results.length === 0 && query && !loading && (
        <p className="text-gray-500">Nuk u gjet asnjë rezultat.</p>
      )}

      <div className="space-y-4">
        {results.map((r) => (
          <Link
            key={r.chunk_id}
            to={`/laws/${r.chunk_id}`}
            className="block p-4 border rounded hover:shadow-md transition-shadow"
          >
            <h2 className="text-lg font-semibold text-primary-start">{r.law_title}</h2>
            {r.article_number && (
              <p className="text-gray-700 mt-1">Neni {r.article_number}</p>
            )}
            <p className="text-sm text-gray-500 mt-2">Burimi: {r.source || 'i panjohur'}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}