// FILE: src/pages/LawViewerPage.tsx
// PHOENIX PROTOCOL - ENHANCED LAW VIEWER (PROFESSIONAL PRESENTATION)

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, FileText, Calendar, Scale } from 'lucide-react';

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
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="glass-panel border border-red-500/30 bg-red-500/10 p-8 rounded-2xl flex flex-col items-center gap-4">
          <div className="text-red-500 text-5xl mb-2">⚠️</div>
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
          <FileText className="h-12 w-12 mx-auto text-text-secondary mb-4" />
          <p className="text-text-secondary">{t('lawViewer.notFound', 'Ligji nuk u gjet.')}</p>
        </div>
      </div>
    );
  }

  // Format the text into paragraphs
  const paragraphs = law.text.split('\n').filter(p => p.trim() !== '');

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="group mb-6 flex items-center gap-2 text-text-secondary hover:text-white transition-colors"
      >
        <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
        {t('general.back', 'Mbrapa')}
      </button>

      {/* Main content card */}
      <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl">
        {/* Header with law title */}
        <div className="bg-gradient-to-r from-primary-start/20 to-primary-end/20 p-6 sm:p-8 border-b border-white/5">
          <div className="flex items-center gap-3 text-primary-start mb-2">
            <Scale size={24} />
            <span className="text-sm font-bold uppercase tracking-widest text-primary-start/80">
              {t('lawViewer.lawTitle', 'LIGJI')}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white leading-tight">
            {law.law_title}
          </h1>
          {law.article_number && (
            <div className="mt-2 flex items-center gap-2">
              <div className="h-0.5 w-8 bg-primary-start/50 rounded-full"></div>
              <p className="text-lg text-primary-start font-semibold">
                {t('lawViewer.article', 'Neni')} {law.article_number}
              </p>
            </div>
          )}
        </div>

        {/* Source badge */}
        <div className="px-6 sm:px-8 pt-4 flex items-center gap-2 text-xs text-text-secondary/60">
          <Calendar size={14} />
          <span>{t('lawViewer.source', 'Burimi')}: {law.source}</span>
        </div>

        {/* Article text */}
        <div className="p-6 sm:p-8 pt-4">
          <div className="prose prose-invert prose-lg max-w-none">
            {paragraphs.map((para, idx) => (
              <p key={idx} className="mb-4 text-gray-300 leading-relaxed">
                {para}
              </p>
            ))}
          </div>
        </div>

        {/* Footer with navigation */}
        <div className="px-6 sm:px-8 pb-6 flex justify-between items-center border-t border-white/5 pt-4">
          <button
            onClick={() => navigate('/laws/search')}
            className="text-sm text-text-secondary hover:text-primary-start transition-colors flex items-center gap-1"
          >
            <ArrowLeft size={16} />
            {t('lawViewer.backToSearch', 'Kthehu te kërkimi')}
          </button>
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="text-sm text-text-secondary hover:text-white transition-colors"
          >
            {t('general.top', 'Lart')} ↑
          </button>
        </div>
      </div>
    </div>
  );
}