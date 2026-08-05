// FILE: src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - LAW ARTICLE PAGE V37.0 (UNIFIED CANVAS PDF ENGINE VIA FILEVIEWERMODAL)

import { useEffect, useState, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
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

  const [article, setArticle] = useState<ArticleData | null>(null);
  const [sourceInfo, setSourceInfo] = useState<SourceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [showPdfModal, setShowPdfModal] = useState(false);
  const [jumpInput, setJumpInput] = useState('');

  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryContent, setSummaryContent] = useState('');
  const [summaryError, setSummaryError] = useState('');

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isAuditing, setIsAuditing] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatVisible, setChatVisible] = useState(false);
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

    const loadArticle = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await apiService.getLawArticle(lawTitle, articleNumber);
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

        setSourceInfo(updatedSourceInfo);
        setArticle({
          law_title: data.law_title,
          article_number: data.article_number || articleNumber,
          source: data.source || `${lawTitle}.pdf`,
          text: normalizedText,
          chunk_id: chunkId,
          source_info: updatedSourceInfo,
          requested_law_title: lawTitle,
        });
      } catch (err: any) {
        console.error('[ERROR] Failed to load article:', err);
        setError(err.message || t('lawArticle.fetchError', 'Dështoi ngarkimi i artikullit.'));
      } finally {
        setLoading(false);
      }
    };

    loadArticle();
  }, [lawTitle, articleNumber, t]);

  useEffect(() => {
    if (chatContainerRef.current && chatVisible) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, chatVisible]);

  useEffect(() => {
    if (summaryContent && chatVisible && messages.length === 0 && !isSummarizing) {
      setTimeout(() => setShowSuggestions(true), 500);
      setTimeout(() => {
        chatPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        inputRef.current?.focus();
      }, 300);
    }
  }, [summaryContent, chatVisible, messages.length, isSummarizing]);

  const handleStartAudit = async () => {
    if (!article || isSummarizing) return;
    setSummaryContent('');
    setSummaryError('');
    setMessages([]);
    setShowSuggestions(false);
    setChatVisible(false);
    setIsSummarizing(true);

    try {
      const stream = apiService.explainLawStream(article.law_title, article.article_number || '', article.text);
      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setSummaryContent(accumulated);
      }
      setChatVisible(true);
    } catch (err: any) {
      console.error('[ERROR] Summary failed:', err);
      setSummaryError(t('lawArticle.aiError', 'Dështoi analiza inteligjente.'));
    } finally {
      setIsSummarizing(false);
    }
  };

  const handleSendQuery = async (query?: string) => {
    if (!article || !article.chunk_id) {
      setChatError('Artikulli nuk ka identifikues të vlefshëm. Ju lutemi rifreskoni faqen.');
      return;
    }

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
      const stream = apiService.askLawAuditor(article.chunk_id, finalQuery, article.law_title, article.article_number);
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-3xl flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-16 h-16 mb-4" />
          <h2 className="text-xl font-black text-text-primary uppercase tracking-tight mb-2">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-sm mb-6">{error}</p>
          <button
            onClick={() => navigate('/laws/search')}
            className="btn-primary flex items-center gap-2 hover-lift shadow-sm cursor-pointer"
          >
            <ArrowLeft size={16} /> {t('lawArticle.backToSearch', 'Kthehu te Biblioteka Ligjore')}
          </button>
        </div>
      </div>
    );
  }

  const rawArtNum = (article.article_number || articleNumber || '').replace(/\.$/, '').trim();

  return (
    <motion.div
      className="w-full min-h-screen pt-24 pb-12 bg-canvas text-text-primary"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 flex-1 flex flex-col">
        <div className="glass-panel p-6 sm:p-8 md:p-10 flex flex-col flex-1 shadow-sm border border-main rounded-3xl bg-surface">
          <LawArticleHeader
            onBackToLibrary={() => navigate('/laws/search')}
            prevArticleNum={prevArticleNum}
            nextArticleNum={nextArticleNum}
            onNavigateToArticle={navigateToArticleNum}
            jumpInput={jumpInput}
            onJumpInputChange={setJumpInput}
            onJumpSubmit={handleJumpSubmit}
            chatVisible={chatVisible}
            isSummarizing={isSummarizing}
            onStartAudit={handleStartAudit}
            onCloseAuditor={() => {
              setChatVisible(false);
              setMessages([]);
              setSummaryContent('');
            }}
            t={t}
          />

          <LawArticleContent
            article={article}
            sourceInfo={sourceInfo}
            isAcademicDoc={isAcademicDoc}
            rawArtNum={rawArtNum}
            prevArticleNum={prevArticleNum}
            nextArticleNum={nextArticleNum}
            onNavigateToArticle={navigateToArticleNum}
            onOpenPdf={() => setShowPdfModal(true)}
            t={t}
          />

          <LawArticleAuditorPanel
            summaryContent={summaryContent}
            isSummarizing={isSummarizing}
            summaryError={summaryError}
            cleanSummary={cleanSummary}
            chatVisible={chatVisible}
            messages={messages}
            showSuggestions={showSuggestions}
            isAuditing={isAuditing}
            chatError={chatError}
            inputQuery={inputQuery}
            onInputQueryChange={setInputQuery}
            onSendQuery={handleSendQuery}
            onCloseAuditor={() => {
              setSummaryContent('');
              setSummaryError('');
              setChatVisible(false);
            }}
            summarySectionRef={summarySectionRef}
            chatPanelRef={chatPanelRef}
            chatContainerRef={chatContainerRef}
            inputRef={inputRef}
            t={t}
          />

          <div className="bg-surface px-6 sm:px-8 py-5 flex flex-wrap justify-between items-center border-t border-main gap-4 mt-6">
            <button
              onClick={() => navigate('/laws/search')}
              className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift cursor-pointer"
            >
              <ArrowLeft size={14} /> Biblioteka Ligjore
            </button>

            <div className="flex items-center gap-3">
              {prevArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => navigateToArticleNum(prevArticleNum)}
                  className="flex items-center gap-2 px-3.5 py-1.5 bg-canvas hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary hover:border-primary-start transition-all shadow-sm cursor-pointer"
                >
                  <ChevronLeft size={14} />
                  <span>{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
                </button>
              )}

              {nextArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => navigateToArticleNum(nextArticleNum)}
                  className="flex items-center gap-2 px-3.5 py-1.5 bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 rounded-xl text-xs font-bold text-primary-start transition-all shadow-sm uppercase tracking-wider cursor-pointer"
                >
                  <span>{`Neni ${nextArticleNum}`}</span>
                  <ChevronRight size={14} />
                </button>
              )}
            </div>

            <button
              onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
              className="text-xs font-bold uppercase tracking-wider text-text-muted hover:text-text-primary transition-colors bg-canvas px-3.5 py-1.5 rounded-xl border border-main hover:border-primary-start shadow-sm cursor-pointer"
            >
              {t('general.top', 'Lart')} ↑
            </button>
          </div>
        </div>
      </div>

      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: article.source || article.law_title,
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