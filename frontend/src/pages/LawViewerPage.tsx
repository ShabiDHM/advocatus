// FILE: src/pages/LawViewerPage.tsx
// PHOENIX PROTOCOL - LAW VIEWER PAGE (FIXED 401)

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiService } from '../services/api'; // import the service

interface LawData {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
}

export default function LawViewerPage() {
  const { chunkId } = useParams<{ chunkId: string }>();
  const [law, setLaw] = useState<LawData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiService.getLawByChunkId(chunkId!)
      .then(setLaw)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [chunkId]);

  if (loading) return <div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error) return <div className="p-8 text-red-600">Gabim: {error}</div>;
  if (!law) return <div className="p-8">Nuk u gjet ligji.</div>;

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white shadow-lg rounded-lg mt-8">
      <h1 className="text-2xl font-bold mb-2">{law.law_title}</h1>
      {law.article_number && (
        <h2 className="text-xl text-gray-700 mb-4">Neni {law.article_number}</h2>
      )}
      <p className="text-sm text-gray-500 mb-4">Burimi: {law.source}</p>
      <div className="prose prose-lg max-w-none">
        {law.text.split('\n').map((para, idx) => (
          <p key={idx} className="mb-2">{para}</p>
        ))}
      </div>
      <button
        onClick={() => window.history.back()}
        className="mt-6 px-4 py-2 bg-primary-start text-white rounded hover:bg-primary-end transition-colors"
      >
        Kthehu
      </button>
    </div>
  );
}