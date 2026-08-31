// FILE: src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - LAW ARTICLE PAGE CONNECTED TO MODULAR LAW SERVICE

import { useEffect, useState, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { lawService } from '../services/lawService';
import { API_V1_URL } from '../services/apiClient';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { motion } from 'framer-motion';

import { SourceInfo, ArticleData, ChatMessage } from '../components/law/lawArticleTypes';
import { normalizeText, generateFallbackChunkId } from '../utils/lawArticleHelpers';
import { LawArticleHeader } from '../components/law/LawArticleHeader';
import { LawArticleContent } from '../components/law/LawArticleContent';
import { LawArticleAuditorPanel } from '../components/law/LawArticleAuditorPanel';
import FileViewerModal from '../components/FileViewerModal';

export default function LawArticlePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const [article, setArticle] = useState<(ArticleData & { page_number?: number; page?: number }) | null>(null);
  const [sourceInfo, setSourceInfo] = useState<SourceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [showPdfModal, setShowPdfModal] = useState(false);
  const [showAuditorModal, setShowAuditorModal] = useState(false);
  const [jumpInput, setJumpInput] = useState('');

  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryContent, setSummaryContent] = useState('');
  const [summaryError, setSummaryError] = useState('');

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isAuditing, setIsAuditing] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const summarySectionRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chatPanelRef = useRef<HTMLDivElement>(null);

  const lawTitle = searchParams.get('lawTitle');
  const articleNumber = searchParams.get('articleNumber');

  const isAcademicDoc = useMemo(() => {
    const raw = (article?.law_title || article?.source || lawTitle || '').toString().toUpperCase();
    return (
      raw.includes('AKADEMIA') ||
      raw.includes('CASE_LAW') ||
      raw.includes('DORACAK') ||
      raw.includes('UDHEZUES') ||
      raw.includes('LËNDËSH') ||
      raw.includes('LENDESH')
    );
  }, [article?.law_title, article?.source, lawTitle]);

  const currentNum = useMemo(() => {
    const cleanNum = (article?.article_number || articleNumber || '').replace(/\.$/, '').trim();
    const match = cleanNum.match(/\d+/);
    if (match) return parseInt(match[0], 10);
    if (cleanNum.toLowerCase() === 'preambula' || cleanNum.toLowerCase() === 'hyrja' || cleanNum === '0') return 0;
    return null;
  }, [article?.article_number, articleNumber]);

  const prevArticleNum = currentNum !== null && currentNum > 0 ? (currentNum === 1 ? '0' : String(currentNum - 1)) : null;
  const nextArticleNum = currentNum !== null ? String(currentNum + 1) : null;

  const cleanSummary = useMemo(() => {
    if (!summaryContent) return '';
    return summaryContent.replace(/\n\n---\n\*Kjo përgjigje është gjeneruar nga AI, vetëm për referenc\.\*/g, '').trim();
  }, [summaryContent]);

  useEffect(() => {
    if (!lawTitle || !articleNumber) {
      setError(t('lawArticle.missingParams', 'Parametrat e artikullit mungojnë.'));
      setLoading(false);
      return;
    }

    const loadArticleAndCache = async () => {
      setLoading(true);
      setError('');
      try {
        // 1. Ngarko Nenin përmes LawService
        const data = await lawService.getLawArticle(lawTitle, articleNumber);
        const normalizedText = normalizeText(data.text, data.article_number || articleNumber);

        let chunkId = data.chunk_id || '';
        if (!chunkId) {
          chunkId = generateFallbackChunkId(lawTitle, articleNumber);
        }

        const isAcademic =
          (data.law_title || data.source || lawTitle).toUpperCase().includes('AKADEMIA') ||
          (data.law_title || data.source || lawTitle).toUpperCase().includes('CASE_LAW') ||
          (data.law_title || data.source || lawTitle).toUpperCase().includes('LËNDËSH');

        const updatedSourceInfo: SourceInfo = data.source_info || {
          confidence: {
            level: 'HIGH',
            label: isAcademic ? 'Udhëzues i Praktikës Gjyqësore' : 'Tekst Zyrtar i Verifikuar (100%)',
            icon: isAcademic ? '📚' : '📜',
            color: isAcademic ? 'text-sky-400' : 'text-emerald-500',
            description: isAcademic ? 'Analizë dhe udhëzues nga Akademia e Drejtësisë.' : 'Nen i nxjerrë direkt nga Kodi / Ligji Zyrtar i Kosovës.',
            score: 0.98,
          },
          matched_law: data.law_title,
          matched_article: data.article_number || articleNumber,
          source_file: data.source,
          was_mapped: data.law_title !== lawTitle,
          mapped_from: lawTitle,
          multiple_matches: false,
          matching_laws: [],
          strategy_used: 'exact',
          verification_hint: isAcademic
            ? `📚 Akademia e Drejtësisë: ${data.law_title}`
            : `✅ Ligji Zyrtar i Kosovës: ${data.law_title}`,
          match_count: 1,
          is_official_statute: !isAcademic,
        };

        const pageNum = (data as any).page_number || (data as any).page;

        setSourceInfo(updatedSourceInfo);
        setArticle({
          law_title: data.law_title,
          article_number: data.article_number || articleNumber,
          source: data.source || `${lawTitle}.pdf`,
          page_number: pageNum,
          page: pageNum,
          text: normalizedText,
          chunk_id: chunkId,
          source_info: updatedSourceInfo,
          requested_law_title: lawTitle,
        });

        // 2. ⚡ KONTROLLO MONGODB NË REFRESH PËRMES LAWSERVICE
        const cachedAnalysis = await lawService.getCachedLawAnalysis(lawTitle, articleNumber);
        if (cachedAnalysis) {
          setSummaryContent(cachedAnalysis);
        } else {
          setSummaryContent('');
        }
      } catch (err: any) {
        console.error('[ERROR] Failed to load article:', err);
        setError(err.message || t('lawArticle.fetchError', 'Dështoi ngarkimi i artikullit.'));
      } finally {
        setLoading(false);
      }
    };

    loadArticleAndCache();
  }, [lawTitle, articleNumber, t]);

  // Hapja e Modalit
  const handleOpenModalOnly = () => {
    setShowAuditorModal(true);
  };

  // Nisja e Analizës me DeepSeek
  const handleStartAnalysis = async () => {
    if (!article || isSummarizing) return;
    setIsSummarizing(true);
    setSummaryError('');
    try {
      const stream = lawService.explainLawStream(article.law_title, article.article_number || '', article.text);
      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setSummaryContent(accumulated);
      }
    } catch (err: any) {
      console.error('[ERROR] Summary failed:', err);
      setSummaryError(t('lawArticle.aiError', 'Dështoi analiza inteligjente.'));
    } finally {
      setIsSummarizing(false);
    }
  };

  // Rianalizo Nenin (Fresh Run)
  const handleReanalyze = async () => {
    if (!article || isSummarizing) return;
    setSummaryContent('');
    setSummaryError('');
    setIsSummarizing(true);

    try {
      await lawService.clearLawCache(article.law_title, article.article_number || '');

      const stream = lawService.explainLawStream(article.law_title, article.article_number || '', article.text);
      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setSummaryContent(accumulated);
      }
    } catch (err: any) {
      console.error('[ERROR] Reanalyze failed:', err);
      setSummaryError(t('lawArticle.aiError', 'Dështoi rianaliza inteligjente.'));
    } finally {
      setIsSummarizing(false);
    }
  };

  // Shlyej Analizën nga Memoria
  const handleClearCache = async () => {
    if (!article) return;
    try {
      await lawService.clearLawCache(article.law_title, article.article_number || '');
      setSummaryContent('');
      setMessages([]);
    } catch (err) {
      console.error('Purge cache failed:', err);
    }
  };

  const handleSendQuery = async (query?: string) => {
    if (!article || !article.chunk_id) return;

    const finalQuery = query ?? inputQuery.trim();
    if (!finalQuery || isAuditing) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: finalQuery,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputQuery('');
    setIsAuditing(true);
    setChatError(null);
    setShowSuggestions(false);

    const auditorMessageId = (Date.now() + 1).toString();
    setMessages((prev) => [...prev, { id: auditorMessageId, role: 'auditor', content: '', timestamp: new Date() }]);

    try {
      const stream = lawService.askLawAuditor(article.chunk_id, finalQuery, article.law_title, article.article_number);
      let accumulatedContent = '';

      for await (const chunk of stream) {
        accumulatedContent += chunk;
        setMessages((prev) =>
          prev.map((msg) => (msg.id === auditorMessageId ? { ...msg, content: accumulatedContent } : msg))
        );
      }
    } catch (err: any) {
      console.error('[ERROR] Audit query failed:', err);
      setChatError(err.message || 'Dështoi komunikimi me Auditorin.');
      setMessages((prev) => prev.filter((msg) => msg.id !== auditorMessageId));
    } finally {
      setIsAuditing(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const navigateToArticleNum = (targetArt: string) => {
    if (!lawTitle) return;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    navigate(`/laws/article?lawTitle=${encodeURIComponent(lawTitle)}&articleNumber=${encodeURIComponent(targetArt)}`);
  };

  const handleJumpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!jumpInput.trim() || !lawTitle) return;
    const clean = jumpInput.trim().replace(/^neni\s*/i, '');
    navigateToArticleNum(clean);
    setJumpInput('');
  };

  const pdfUrl = article?.source ? `${API_V1_URL}/laws/pdf/${encodeURIComponent(article.source)}` : null;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20 bg-canvas">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 sm:pt-28">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-8 sm:p-10 rounded-3xl flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-14 h-14 sm:w-16 sm:h-16 mb-4" />
          <h2 className="text-lg sm:text-xl font-black text-text-primary uppercase tracking-tight mb-2">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-sm mb-6">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="btn-primary flex items-center gap-2 hover-lift shadow-sm cursor-pointer"
          >
            <ArrowLeft size={16} /> Kthehu mbrapa
          </button>
        </div>
      </div>
    );
  }

  const rawArtNum = (article.article_number || articleNumber || '').replace(/\.$/, '').trim();
  const targetPage = article.page_number || article.page;

  return (
    <motion.div
      className="w-full min-h-screen pt-20 sm:pt-24 pb-10 bg-canvas text-text-primary"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 flex-1 flex flex-col">
        <div className="glass-panel p-4 sm:p-8 md:p-10 flex flex-col flex-1 shadow-sm border border-main rounded-2xl sm:rounded-3xl bg-surface">
          
          <LawArticleHeader
            sourceInfo={sourceInfo}
            isAcademicDoc={isAcademicDoc}
            prevArticleNum={prevArticleNum}
            nextArticleNum={nextArticleNum}
            onNavigateToArticle={navigateToArticleNum}
            jumpInput={jumpInput}
            onJumpInputChange={setJumpInput}
            onJumpSubmit={handleJumpSubmit}
            chatVisible={showAuditorModal}
            isSummarizing={isSummarizing}
            onStartAudit={handleOpenModalOnly}
            onCloseAuditor={() => setShowAuditorModal(false)}
            t={t}
          />

          <LawArticleContent
            article={article}
            rawArtNum={rawArtNum}
            onOpenPdf={() => setShowPdfModal(true)}
            t={t}
          />

          {/* AUDITOR MODAL DIALOG */}
          <LawArticleAuditorPanel
            isOpen={showAuditorModal}
            summaryContent={summaryContent}
            isSummarizing={isSummarizing}
            summaryError={summaryError}
            cleanSummary={cleanSummary}
            chatVisible={true}
            messages={messages}
            showSuggestions={showSuggestions}
            isAuditing={isAuditing}
            chatError={chatError}
            inputQuery={inputQuery}
            onInputQueryChange={setInputQuery}
            onSendQuery={handleSendQuery}
            onCloseAuditor={() => setShowAuditorModal(false)}
            onStartAnalysis={handleStartAnalysis}
            onClearCache={handleClearCache}
            onReanalyze={handleReanalyze}
            summarySectionRef={summarySectionRef}
            chatPanelRef={chatPanelRef}
            chatContainerRef={chatContainerRef}
            inputRef={inputRef}
            t={t}
          />

          {/* Shiriti i poshtëm */}
          <div className="bg-surface px-4 sm:px-8 py-4 sm:py-5 flex justify-center items-center border-t border-main gap-3 sm:gap-4 mt-5 sm:mt-6">
            <div className="flex items-center gap-2 sm:gap-3 w-full sm:w-auto justify-center">
              {prevArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => navigateToArticleNum(prevArticleNum)}
                  className="h-9 sm:h-10 px-3 sm:px-4 flex items-center justify-center gap-1.5 sm:gap-2 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-semibold text-text-primary hover:border-primary-start transition-all shadow-sm cursor-pointer active:scale-95"
                >
                  <ChevronLeft size={14} className="text-primary-start" />
                  <span>{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
                </button>
              )}

              {nextArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => navigateToArticleNum(nextArticleNum)}
                  className="h-9 sm:h-10 px-3 sm:px-4 flex items-center justify-center gap-1.5 sm:gap-2 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-semibold text-text-primary hover:border-primary-start transition-all shadow-sm cursor-pointer active:scale-95"
                >
                  <span>{`Neni ${nextArticleNum}`}</span>
                  <ChevronRight size={14} className="text-primary-start" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: article.source || article.law_title,
            title: article.law_title,
            article_number: article.article_number || articleNumber,
            page_number: targetPage,
            page: targetPage,
            mime_type: 'application/pdf',
          }}
          initialPage={targetPage}
          directUrl={pdfUrl}
          isAuth={true}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </motion.div>
  );
}