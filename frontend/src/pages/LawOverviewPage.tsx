// FILE: src/pages/LawOverviewPage.tsx
// PHOENIX PROTOCOL - LAW TABLE OF CONTENTS PAGE

import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Scale, Calendar, FileText } from 'lucide-react';

interface LawOverviewData {
  law_title: string;
  source: string;
  article_count: number;
  articles: string[];
}

export default function LawOverviewPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [data, setData] = useState<LawOverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const lawTitle = searchParams.get('lawTitle');

  useEffect(() => {
    if (!lawTitle) {
      setError(t('lawOverview.missingTitle', 'Titulli i ligjit mungon.'));
      setLoading(false);
      return;
    }
    apiService.getLawArticlesByTitle(lawTitle)
      .then(setData)
      .catch((err) => {
        console.error('Law overview fetch error:', err);
        setError(err.message || t('lawOverview.fetchError', 'Dështoi ngarkimi i ligjit.'));
      })
      .finally(() => setLoading(false));
  }, [lawTitle, t]);

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
            {t('lawOverview.backToSearch', 'Kthehu te kërkimi')}
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8">
      <button
        onClick={() => navigate(-1)}
        className="group mb-6 flex items-center gap-2 text-text-secondary hover:text-white transition-colors"
      >
        <ArrowLeft size={20} className="group-hover:-translate-x-1 transition-transform" />
        {t('general.back', 'Mbrapa')}
      </button>

      <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl">
        <div className="bg-gradient-to-r from-primary-start/20 to-primary-end/20 p-6 sm:p-8 border-b border-white/5">
          <div className="flex items-center gap-3 text-primary-start mb-2">
            <Scale size={24} />
            <span className="text-sm font-bold uppercase tracking-widest text-primary-start/80">
              {t('lawOverview.lawTitle', 'LIGJI')}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white leading-tight">
            {data.law_title}
          </h1>
          <div className="mt-4 flex items-center gap-3 text-xs text-text-secondary/60">
            <Calendar size={14} />
            <span>{t('lawOverview.source', 'Burimi')}: {data.source}</span>
            <FileText size={14} className="ml-2" />
            <span>{data.article_count} {t('lawOverview.articles', 'nene')}</span>
          </div>
        </div>

        <div className="p-6 sm:p-8">
          <h2 className="text-lg font-semibold text-white mb-4">
            {t('lawOverview.tableOfContents', 'Përmbajtja')}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {data.articles.map((article) => (
              <button
                key={article}
                onClick={() => navigate(`/laws/article?lawTitle=${encodeURIComponent(data.law_title)}&articleNumber=${encodeURIComponent(article)}`)}
                className="text-left px-3 py-2 bg-white/5 hover:bg-primary-start/10 rounded-lg border border-white/10 transition-colors text-sm text-text-secondary hover:text-white"
              >
                Neni {article.replace(/\.$/, '')}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}