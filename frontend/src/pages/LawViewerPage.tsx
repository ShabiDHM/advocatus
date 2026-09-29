// FILE: src/pages/LawViewerPage.tsx
// PHOENIX PROTOCOL - LAW VIEWER V9.0
//
// V9.0: FIX fake verification + repeals + dead code.
//   - V1: Shtuar RepealedWarning (is_repealed + warning)
//   - V2: HEQUR isAcademicDoc dead code (akademia u hoq në V22.0)
//   - V3: PDF URL → /caselaw/pdf ose /pdf sipas source
//   - V5: LawData tipizuar me is_repealed/warning/page (nga ArticleData)
//   - V6: Shtuar AbortController
//   - V7: Hequr `t` nga deps për të shmangur refetch në ndryshim gjuhe
//   - V10: Normalizim \r\n në paragraphs
//   - V14: Error handling me 401/404/500
//
// V8.0: Versioni i vjetër.

import { useEffect, useState, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { API_V1_URL } from '../services/api';
import { lawService } from '../services/lawService';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft, Calendar, Scale, AlertCircle, BookOpen, FileText, ExternalLink,
} from 'lucide-react';
import { motion } from 'framer-motion';
import FileViewerModal from '../components/FileViewerModal';
import { RepealedWarning } from '../components/law/RepealedWarning';
import type { ArticleData } from '../components/law/lawArticleTypes';

export default function LawViewerPage() {
  const { chunkId } = useParams<{ chunkId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [law, setLaw] = useState<ArticleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPdfModal, setShowPdfModal] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!chunkId) {
      setError(t('lawViewer.missingId', 'ID e fragmentit mungon.'));
      setLoading(false);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError('');

    lawService
      .getLawByChunkId(chunkId, controller.signal)
      .then((res) => {
        if (controller.signal.aborted) return;
        setLaw(res);
      })
      .catch((err: any) => {
        if (err?.name === 'CanceledError' || err?.name === 'AbortError') return;
        console.error('[LawViewerPage] Fetch error:', err);
        if (controller.signal.aborted) return;

        const status = err?.response?.status;
        let msg = err?.message || t('lawViewer.fetchError', 'Dështoi ngarkimi i ligjit.');
        if (status === 401) {
          msg = t('lawViewer.unauthorized', 'Sesioni ka skaduar. Hyni përsëri.');
        } else if (status === 404) {
          msg = t('lawViewer.notFound', 'Dokumenti nuk u gjet.');
        } else if (status === 500) {
          msg = t('lawViewer.serverError', 'Gabim në server. Provoni përsëri.');
        } else if (err?.response?.data?.detail) {
          msg = err.response.data.detail;
        }
        setError(msg);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [chunkId, t]);

  // V9: PDF URL sipas llojit
  const pdfUrl = useMemo(() => {
    if (!law?.source) return null;
    const encoded = encodeURIComponent(law.source);
    // Nëse ka prefix case_law në source ose law_title përmban "Gjykata Supreme" → caselaw
    const isCaselaw =
      /case_law|supreme|praktik/i.test(law.source) ||
      /Gjykata\s+Supreme/i.test(law.law_title);
    return isCaselaw
      ? `${API_V1_URL}/laws/caselaw/pdf/${encoded}`
      : `${API_V1_URL}/laws/pdf/${encoded}`;
  }, [law?.source, law?.law_title]);

  // V9: paragraph normalization (\r\n + \r)
  const paragraphs = useMemo(() => {
    if (!law?.text) return [];
    return law.text
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      .split('\n')
      .filter((p) => p.trim() !== '');
  }, [law?.text]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20 bg-canvas">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">
          {t('general.loading', 'Duke ngarkuar...')}
        </p>
      </div>
    );
  }

  if (error || !law) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-3xl flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-16 h-16 mb-4" />
          <h2 className="text-xl font-black text-text-primary uppercase tracking-tight mb-2">
            {t('general.error', 'Gabim')}
          </h2>
          <p className="text-text-secondary text-sm mb-6">
            {error || 'Ligji nuk u gjet.'}
          </p>
          <button
            onClick={() => navigate('/laws/search')}
            className="btn-primary flex items-center gap-2 hover-lift shadow-sm cursor-pointer"
          >
            <ArrowLeft size={16} />
            {t('lawViewer.backToSearch', 'Kthehu te kërkimi')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="w-full min-h-screen pb-16 bg-canvas text-text-primary"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        <button
          onClick={() => navigate(-1)}
          className="group mb-6 flex items-center gap-2.5 text-text-muted hover:text-text-primary transition-colors font-bold text-xs uppercase tracking-wider hover-lift cursor-pointer"
        >
          <div className="p-2 rounded-xl bg-surface border border-main group-hover:border-primary-start transition-colors">
            <ArrowLeft size={16} className="text-primary-start" />
          </div>
          <span>{t('general.back', 'Kthehu Mbrapa')}</span>
        </button>

        <div className="glass-panel p-0 flex flex-col overflow-hidden shadow-sm border border-main rounded-3xl bg-surface">
          <div className="bg-canvas px-6 sm:px-10 py-8 border-b border-main relative overflow-hidden">
            <div className="relative z-10 flex flex-col gap-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1 rounded-lg">
                  <BookOpen size={14} />
                  <span className="text-[10px] font-black uppercase tracking-wider">
                    {t('lawViewer.officialLabel', 'LIGJI DHE RREGULLORJA ZYRTARE')}
                  </span>
                </div>

                {pdfUrl && (
                  <button
                    type="button"
                    onClick={() => setShowPdfModal(true)}
                    className="flex items-center gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all hover-lift cursor-pointer"
                  >
                    <FileText size={14} />
                    <span>{t('lawViewer.viewFullPdf', 'Shiko PDF të Plotë')}</span>
                    <ExternalLink size={12} />
                  </button>
                )}
              </div>

              <h1 className="text-2xl sm:text-4xl font-black text-text-primary leading-tight tracking-tight">
                {law.law_title}
              </h1>

              <div className="flex flex-wrap items-center gap-3 border-t border-main/50 pt-5 mt-1">
                <div className="flex items-center gap-2 bg-surface text-text-secondary border border-main px-3.5 py-1.5 rounded-xl">
                  <Calendar size={15} className="text-primary-start" />
                  <span className="text-xs font-bold uppercase tracking-wider truncate max-w-[250px]">
                    {law.source}
                  </span>
                </div>

                {law.article_number && (
                  <div className="flex items-center gap-2 bg-surface text-primary-start border border-primary-start/30 px-3.5 py-1.5 rounded-xl">
                    <Scale size={15} />
                    <span className="text-xs font-bold uppercase tracking-wider">
                      {t('lawViewer.article', 'Neni')} {law.article_number}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* V9: Repealed warning */}
          {law.is_repealed && (
            <div className="px-6 sm:px-10 pt-5">
              <RepealedWarning info={law.repealed_info} warning={law.warning} />
            </div>
          )}

          <div className="bg-canvas/50 px-6 sm:px-12 py-10">
            <div className="max-w-[85ch] mx-auto">
              {paragraphs.map((para, idx) => (
                <p
                  key={idx}
                  className="mb-5 text-sm sm:text-base text-text-primary leading-relaxed font-medium text-justify"
                >
                  {para}
                </p>
              ))}
            </div>
          </div>

          <div className="bg-surface px-6 sm:px-10 py-5 flex justify-between items-center border-t border-main">
            <button
              onClick={() => navigate('/laws/search')}
              className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift cursor-pointer"
            >
              <ArrowLeft size={14} />
              {t('lawViewer.backToSearch', 'Kthehu te kërkimi')}
            </button>
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-text-primary transition-colors bg-canvas px-3.5 py-1.5 rounded-xl border border-main hover:border-primary-start shadow-sm cursor-pointer"
            >
              {t('general.top', 'Kthehu Lart')} ↑
            </button>
          </div>
        </div>
      </div>

      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: law.source || law.law_title,
            mime_type: 'application/pdf',
          }}
          directUrl={pdfUrl}
          isAuth={true}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </motion.div>
  );
}