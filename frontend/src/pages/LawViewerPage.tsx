// FILE: src/pages/LawViewerPage.tsx
// PHOENIX PROTOCOL - LAW VIEWER PAGE (FIXED)

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Loader2, AlertCircle } from 'lucide-react';

interface LawData {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
}

export default function LawViewerPage() {
  const { chunkId } = useParams<{ chunkId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [law, setLaw] = useState<LawData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!chunkId) {
      setError(t('lawViewer.missingId', 'ID e fragmentit mungon.'));
      setLoading(false);
      return;
    }
    apiService.getLawByChunkId(chunkId)
      .then(setLaw)
      .catch((err) => {
        console.error('Law fetch error:', err);
        setError(err.message || t('lawViewer.fetchError', 'Dështoi ngarkimi i ligjit.'));
      })
      .finally(() => setLoading(false));
  }, [chunkId, t]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin h-12 w-12 text-primary-start" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="glass-panel border border-red-500/30 bg-red-500/10 p-8 rounded-2xl flex flex-col items-center gap-4">
          <AlertCircle className="h-12 w-12 text-red-500" />
          <p className="text-red-200 text-center">{error}</p>
          <button
            onClick={() => navigate('/laws/search')}
            className="mt-4 px-6 py-2 bg-primary-start text-white rounded-lg hover:bg-primary-end transition-colors"
          >
            {t('lawViewer.backToSearch', 'Kthehu te kërkimi')}
          </button>
        </div>
      </div>
    );
  }

  if (!law) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="glass-panel p-8 rounded-2xl text-center">
          <p className="text-text-secondary">{t('lawViewer.notFound', 'Ligji nuk u gjet.')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <button
        onClick={() => navigate(-1)}
        className="mb-6 flex items-center gap-2 text-text-secondary hover:text-white transition-colors"
      >
        <ArrowLeft size={20} />
        {t('general.back', 'Mbrapa')}
      </button>
      <div className="glass-panel p-8 rounded-2xl">
        <h1 className="text-3xl font-bold text-white mb-2">{law.law_title}</h1>
        {law.article_number && (
          <h2 className="text-xl text-primary-start mb-6">Neni {law.article_number}</h2>
        )}
        <p className="text-sm text-text-secondary mb-6">Burimi: {law.source}</p>
        <div className="prose prose-invert max-w-none">
          {law.text.split('\n').map((para, idx) => (
            <p key={idx} className="mb-4 text-gray-300 leading-relaxed">{para}</p>
          ))}
        </div>
      </div>
    </div>
  );
}