// FILE: src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - LAW ARTICLE PAGE V18.2 (REGEX SPLIT FIX)
// 1. FIX: Upgraded client-side text parser to use a highly tolerant Regex split, preventing empty tabs when AI phrasing varies.

import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  ArrowLeft, Scale, AlertCircle, BookOpen, Sparkles, 
  Loader2, X, BrainCircuit, User, Send, MessageCircle, FileText, ExternalLink, Download,
  ChevronLeft, ChevronRight, Search, Minus, Maximize2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ArticleData {
  law_title: string;
  article_number?: string;
  source: string;
  text: string;
  chunk_id: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'auditor';
  content: string;
  timestamp: Date;
}

// ========== PHOENIX: PRECISION LEGAL TEXT SANITIZER ==========
const normalizeText = (raw: string, articleNum?: string): string => {
  if (!raw) return '';

  let cleaned = raw;

  cleaned = cleaned.replace(/---\s*\[?FAQJA\s+\d+\]?\s*---/gi, '');
  cleaned = cleaned.replace(/GAZETA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+KOSOVËS.*?(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/FLETORJA\s+ZYRTARE\s+E\s+REPUBLIKËS\s+SË\s+SHQIPËRISË.*?(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/(?:KODI|LIGJI|UDHËZIMI|UDHËZIM)\s+Nr\.\s*[\d\/L\-]+\s+[A-ZËÇSHQËWXYZ\s\-]+(?=\n|$)/gi, '');
  cleaned = cleaned.replace(/^\s*\d{1,3}\s*$/gm, '');

  const cleanNumStr = (articleNum || '').replace(/\.$/, '').trim();
  const numMatch = cleanNumStr.match(/\d+/);
  const currentNum = numMatch ? parseInt(numMatch[0], 10) : 0;
  const isPreamble = currentNum === 0 || cleanNumStr.toLowerCase() === 'preambula' || cleanNumStr.toLowerCase() === 'hyrja';

  if (isPreamble) {
    const neni1Match = cleaned.match(/(?:^|\n)\s*(?:Neni|NENI)\s+1\b/i);
    if (neni1Match && neni1Match.index !== undefined) {
      cleaned = cleaned.substring(0, neni1Match.index).trim();
    }
  } else if (currentNum > 0) {
    const currentArticleRegex = new RegExp(`(?:^|\\n)\\s*(?:Neni|NENI)\\s+${currentNum}\\b`, 'i');
    const startMatch = cleaned.match(currentArticleRegex);
    if (startMatch && startMatch.index !== undefined) {
      cleaned = cleaned.substring(startMatch.index).trim();
    }

    const nextNum = currentNum + 1;
    const nextArticleRegex = new RegExp(`(?:^|\\n)\\s*(?:Neni|NENI)\\s+${nextNum}\\b`, 'i');
    const endMatch = cleaned.match(nextArticleRegex);
    if (endMatch && endMatch.index !== undefined) {
      cleaned = cleaned.substring(0, endMatch.index).trim();
    }

    cleaned = cleaned.replace(new RegExp(`^(?:Neni|NENI)\\s+${currentNum}\\b[:\\.\\-]*\\s*`, 'i'), '').trim();
  }

  const lines = cleaned.split('\n');
  const mergedLines: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const currentLine = lines[i].trim();
    if (!currentLine) {
      mergedLines.push(currentLine);
      continue;
    }

    if (mergedLines.length > 0 && mergedLines[mergedLines.length - 1] === currentLine) {
      continue;
    }
    
    const endsMidSentence = !/[.!?:;]$/.test(currentLine);
    const nextLine = lines[i + 1]?.trim() || '';
    const nextStartsLowercase = /^[a-zëç]/i.test(nextLine) && !/^\d+\./.test(nextLine);
    
    if (endsMidSentence && nextStartsLowercase && nextLine) {
      lines[i + 1] = currentLine + ' ' + nextLine;
    } else {
      mergedLines.push(currentLine);
    }
  }
  
  cleaned = mergedLines.join('\n');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

  const paragraphs = cleaned.split(/\n\n+/);
  const normalizedParagraphs = paragraphs
    .map(para => para.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim())
    .filter((para, index, arr) => para.length > 0 && (index === 0 || para !== arr[index - 1]));
  
  return normalizedParagraphs.join('\n\n');
};

const renderMarkdown = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-4" />;
        // Skip AI structural headers to keep the UI clean
        if (trimmed.toUpperCase().includes('### NIVELI')) return null;
        if (trimmed.toUpperCase().includes('NIVELI 1:')) return null;
        if (trimmed === '---') return null;
        const parts = trimmed.split(/(\*\*.*?\*\*)/g);
        return (
            <p key={i} className="mb-4 text-base sm:text-lg text-text-primary leading-relaxed font-medium">
                {parts.map((part, j) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                        return <strong key={j} className="font-black text-text-primary">{part.slice(2, -2)}</strong>;
                    }
                    return <span key={j}>{part}</span>;
                })}
            </p>
        );
    });
};

const generateFallbackChunkId = (lawTitle: string, articleNumber: string): string => {
  const cleanTitle = lawTitle.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 80);
  const cleanArticle = articleNumber.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20);
  return `chunk_${cleanTitle}_${cleanArticle}`;
};

const SUGGESTED_QUESTIONS = [
  'Cilat janë detyrimet kryesore sipas këtij neni?',
  'Çfarë ndodh nëse shkelet ky nen?',
  'A ka ndonjë afat kohor që duhet respektuar?',
  'Si mund ta zbatoj këtë nen në praktikë?',
];

export default function LawArticlePage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [article, setArticle] = useState<ArticleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // --- PDF MODAL & MINIMIZE STATE ---
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [isPdfMinimized, setIsPdfMinimized] = useState(false);
  const [jumpInput, setJumpInput] = useState('');

  // --- AI SUMMARY STATE ---
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryContent, setSummaryContent] = useState('');
  const [activePerspective, setActivePerspective] = useState<'senior' | 'citizen'>('senior');
  const [summaryError, setSummaryError] = useState('');
  
  // --- CHAT STATE ---
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isAuditing, setIsAuditing] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatVisible, setChatVisible] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  
  // --- Refs ---
  const summarySectionRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chatPanelRef = useRef<HTMLDivElement>(null);

  const lawTitle = searchParams.get('lawTitle');
  const articleNumber = searchParams.get('articleNumber');

  const currentNum = useMemo(() => {
    const cleanNum = (article?.article_number || articleNumber || '').replace(/\.$/, '').trim();
    const match = cleanNum.match(/\d+/);
    if (match) return parseInt(match[0], 10);
    if (cleanNum.toLowerCase() === 'preambula' || cleanNum.toLowerCase() === 'hyrja' || cleanNum === '0') return 0;
    return null;
  }, [article?.article_number, articleNumber]);

  const prevArticleNum = currentNum !== null && currentNum > 0 ? (currentNum === 1 ? '0' : String(currentNum - 1)) : null;
  const nextArticleNum = currentNum !== null ? String(currentNum + 1) : null;

  // ========== PHOENIX: BULLETPROOF DUAL-PERSPECTIVE REGEX PARSER ==========
  const perspectives = useMemo(() => {
    if (!summaryContent) return { senior: '', citizen: '' };

    let cleanText = summaryContent
      .replace(/\n\n---\n\*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë\.\*/g, '')
      .trim();

    let seniorText = '';
    let citizenText = '';

    // PHOENIX UPGRADE: Highly tolerant regex split catches ANY variation of the Level 2 / Citizen marker
    const splitRegex = /(?:\[NDARJA\]|NIVELI 2[:\-]?|### NIVELI 2[:\-]?|KËSHILLIM PËR QYTETARIN|### KËSHILLIM)/i;
    const match = cleanText.match(splitRegex);

    if (match && match.index !== undefined) {
        seniorText = cleanText.substring(0, match.index).trim();
        citizenText = cleanText.substring(match.index + match[0].length).trim();
    }

    // Clean up residual Markdown headers inside parsed parts
    const cleanHeaders = (str: string) => {
        return str
            .replace(/^(?:###?\s*)?NIVELI\s*[12]\s*[:\-]*\s*(?:OPINIONI\s+PROFESIONAL\s*\(Për\s+Juristët\)|KËSHILLIM\s+PËR\s+QYTETARIN\s*\(Gjuhë\s+e\s+Thjeshtë\)|OPINIONI\s+PROFESIONAL|KËSHILLIM\s+PËR\s+QYTETARIN)?/gi, '')
            .trim();
    };

    seniorText = cleanHeaders(seniorText);
    citizenText = cleanHeaders(citizenText);

    // ULTRA-ROBUST SELF-HEALING FALLBACK: If either tab parses empty, clone whole text to both
    if (!seniorText || !citizenText) {
        const fallbackText = cleanText
            .replace(/###?\s*NIVELI\s*[12].*?(\n|$)/gi, '')
            .replace(/\[NDARJA\]/gi, '')
            .trim();
        return {
            senior: fallbackText,
            citizen: fallbackText
        };
    }

    return {
        senior: seniorText,
        citizen: citizenText
    };
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
        
        setArticle({
          law_title: data.law_title,
          article_number: data.article_number || articleNumber,
          source: data.source || `${lawTitle}.pdf`,
          text: normalizedText,
          chunk_id: chunkId,
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
      setTimeout(() => {
        setShowSuggestions(true);
      }, 500);
      
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
    setActivePerspective('senior');
    
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
    setMessages(prev => [...prev, userMessage]);
    setInputQuery('');
    setIsAuditing(true);
    setChatError(null);
    setShowSuggestions(false);

    const auditorMessageId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, {
      id: auditorMessageId,
      role: 'auditor',
      content: '',
      timestamp: new Date(),
    }]);

    try {
      const stream = apiService.askLawAuditor(article.chunk_id, finalQuery);
      let accumulatedContent = '';

      for await (const chunk of stream) {
        accumulatedContent += chunk;
        setMessages(prev => prev.map(msg =>
          msg.id === auditorMessageId
            ? { ...msg, content: accumulatedContent }
            : msg
        ));
      }
    } catch (err: any) {
      console.error('[ERROR] Audit query failed:', err);
      setChatError(err.message || 'Dështoi komunikimi me Auditorin.');
      setMessages(prev => prev.filter(msg => msg.id !== auditorMessageId));
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

  const handleBackToLibrary = () => {
    navigate('/laws/search');
  };

  const pdfUrl = article?.source ? `${API_V1_URL}/laws/pdf/${encodeURIComponent(article.source)}` : null;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen pt-20">
        <div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin mb-6 shadow-sm"></div>
        <p className="text-text-primary font-black uppercase tracking-widest text-sm">{t('general.loading', 'Duke ngarkuar...')}</p>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-3xl mx-auto px-6 pt-32">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 p-10 rounded-[2rem] flex flex-col items-center text-center shadow-sm">
          <AlertCircle className="text-danger-start w-20 h-20 mb-6" />
          <h2 className="text-2xl font-black text-text-primary uppercase tracking-tighter mb-3">{t('general.error', 'Gabim')}</h2>
          <p className="text-text-secondary text-lg mb-8">{error}</p>
          <button onClick={handleBackToLibrary} className="btn-primary flex items-center gap-2 hover-lift shadow-sm">
            <ArrowLeft size={18} /> {t('lawArticle.backToSearch', 'Kthehu te Biblioteka Ligjore')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      className="w-full min-h-screen pt-24 pb-12 bg-canvas flex flex-col"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 w-full flex-1 flex flex-col">
        <div className="glass-panel p-6 sm:p-8 md:p-10 flex flex-col flex-1 shadow-lawyer-dark border border-border-main">
          
          {/* Top Control Bar */}
          <div className="flex flex-wrap items-center justify-between mb-8 gap-4">
            <button
              onClick={handleBackToLibrary}
              className="group flex items-center gap-3 text-text-muted hover:text-text-primary transition-colors font-bold text-xs sm:text-sm uppercase tracking-widest hover-lift"
            >
              <div className="p-2 rounded-lg bg-surface border border-border-main group-hover:border-primary-start transition-colors">
                <ArrowLeft size={16} className="text-primary-start" />
              </div>
              <span>Biblioteka Ligjore</span>
            </button>

            {/* Middle Zone: Fast Stepper & Jump Box */}
            <div className="flex items-center gap-2 flex-wrap">
              {prevArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => navigateToArticleNum(prevArticleNum)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-surface border border-border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none"
                  title="Neni i Mëparshëm"
                >
                  <ChevronLeft size={14} className="text-primary-start" />
                  <span className="hidden sm:inline">{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
                </button>
              )}

              <form onSubmit={handleJumpSubmit} className="relative flex items-center">
                <Search size={12} className="absolute left-3 text-text-muted pointer-events-none" />
                <input
                  type="text"
                  placeholder="Kërko nenin..."
                  value={jumpInput}
                  onChange={(e) => setJumpInput(e.target.value)}
                  className="w-28 sm:w-32 h-9 pl-8 pr-2 bg-canvas border border-border-main rounded-xl text-xs font-bold text-text-primary focus:border-primary-start focus:ring-1 focus:ring-primary-start/30 focus:outline-none"
                />
              </form>

              {nextArticleNum !== null && (
                <button
                  type="button"
                  onClick={() => navigateToArticleNum(nextArticleNum)}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold bg-surface border border-border-main hover:border-primary-start/60 text-text-primary transition-all hover-lift shadow-sm focus:outline-none"
                  title="Neni i Ardhshëm"
                >
                  <span className="hidden sm:inline">{`Neni ${nextArticleNum}`}</span>
                  <ChevronRight size={14} className="text-primary-start" />
                </button>
              )}
            </div>

            {/* AI Audit Action Button */}
            {!chatVisible ? (
              <button
                onClick={handleStartAudit}
                disabled={isSummarizing}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm hover-lift btn-primary"
              >
                {isSummarizing ? <Loader2 size={14} className="animate-spin" /> : <BrainCircuit size={14} />}
                {isSummarizing ? t('lawArticle.analyzing', 'Duke Analizuar...') : t('lawArticle.auditBtn', 'Auditimi Ligjor')}
              </button>
            ) : (
              <button
                onClick={() => { setChatVisible(false); setMessages([]); setSummaryContent(''); }}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all shadow-sm bg-surface border border-border-main text-text-primary hover:border-danger-start hover:text-danger-start"
              >
                <X size={14} />
                {t('lawArticle.closeAuditor', 'Mbyll Auditorin')}
              </button>
            )}
          </div>

          <div className="p-0 flex flex-col overflow-hidden shadow-sm border border-border-main rounded-2xl">
            
            {/* Header */}
            <div className="bg-surface px-8 py-10 border-b border-border-main relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-primary-start/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
              <div className="relative z-10 flex flex-col gap-6">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="flex items-center gap-2 bg-primary-start/10 text-primary-start border border-primary-start/20 px-3 py-1.5 rounded-lg">
                    <BookOpen size={14} />
                    <span className="text-xs font-black uppercase tracking-widest">{t('lawArticle.lawTitle', 'LIGJI')}</span>
                  </div>

                  {/* Interactive Clickable PDF Source Pill */}
                  <button
                    type="button"
                    onClick={() => { setShowPdfModal(true); setIsPdfMinimized(false); }}
                    className="flex items-center gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 px-3 py-1.5 rounded-lg transition-all hover-lift cursor-pointer focus:outline-none"
                    title="Shiko dokumentin PDF të plotë zyrtar"
                  >
                    <FileText size={14} />
                    <span className="text-xs font-bold uppercase tracking-widest truncate max-w-[150px] sm:max-w-[220px]">
                      {article.source}
                    </span>
                    <ExternalLink size={12} className="opacity-80 shrink-0" />
                  </button>
                </div>

                <h1 className="text-2xl sm:text-3xl font-black text-text-primary leading-tight tracking-tighter">{article.law_title}</h1>
                <div className="flex items-center justify-between border-t border-border-main/50 pt-6 mt-2">
                  <div className="flex items-center gap-3">
                    <Scale size={24} className="text-primary-start" />
                    <p className="text-lg font-black text-primary-start uppercase tracking-widest">
                      {(() => {
                        const cleanNum = (article.article_number || articleNumber || '').replace(/\.$/, '').trim();
                        const isPreamble = cleanNum === '0' || cleanNum.toLowerCase() === 'preambula' || cleanNum.toLowerCase() === 'hyrja';
                        return isPreamble ? 'Preambula' : `${t('lawArticle.article', 'Neni')} ${cleanNum}`;
                      })()}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    {prevArticleNum !== null && (
                      <button
                        type="button"
                        onClick={() => navigateToArticleNum(prevArticleNum)}
                        className="p-2 rounded-lg bg-canvas hover:bg-hover border border-border-main text-text-muted hover:text-primary-start transition-colors"
                        title="Neni i Mëparshëm"
                      >
                        <ChevronLeft size={16} />
                      </button>
                    )}
                    {nextArticleNum !== null && (
                      <button
                        type="button"
                        onClick={() => navigateToArticleNum(nextArticleNum)}
                        className="p-2 rounded-lg bg-canvas hover:bg-hover border border-border-main text-text-muted hover:text-primary-start transition-colors"
                        title="Neni i Ardhshëm"
                      >
                        <ChevronRight size={16} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Reading Surface */}
            <div className="bg-surface/50 px-8 sm:px-12 py-12 shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)]">
              <div className="max-w-[75ch] mx-auto">
                <div className="text-base sm:text-lg text-text-primary leading-relaxed font-medium whitespace-pre-wrap text-justify">
                  {article.text}
                </div>
              </div>
            </div>

            {/* AI SUMMARY SECTION */}
            <AnimatePresence>
              {(summaryContent || isSummarizing || summaryError) && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  ref={summarySectionRef}
                  className="border-t border-primary-start/30 bg-primary-start/[0.02] overflow-hidden"
                >
                  <div className="p-8 sm:p-12 relative">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-6 border-b border-border-main/50 pb-6">
                      <div className="flex bg-surface p-1.5 rounded-2xl border border-border-main shadow-inner w-full sm:w-auto">
                        <button
                          onClick={() => setActivePerspective('senior')}
                          className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                            activePerspective === 'senior'
                              ? 'bg-primary-start text-white shadow-sm'
                              : 'text-text-muted hover:text-text-primary hover:bg-canvas'
                          }`}
                        >
                          <BrainCircuit size={16} /> Analiza Profesionale
                        </button>
                        <button
                          onClick={() => setActivePerspective('citizen')}
                          className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                            activePerspective === 'citizen'
                              ? 'bg-primary-start text-white shadow-sm'
                              : 'text-text-muted hover:text-text-primary hover:bg-canvas'
                          }`}
                        >
                          <User size={16} /> Për Qytetarin
                        </button>
                      </div>
                      <button
                        onClick={() => { setSummaryContent(''); setSummaryError(''); setChatVisible(false); }}
                        className="p-3 bg-surface border border-border-main rounded-xl text-text-muted hover:text-danger-start hover:border-danger-start/30 transition-colors hover-lift self-end sm:self-auto"
                      >
                        <X size={20} />
                      </button>
                    </div>

                    {summaryError && (
                      <div className="bg-danger-start/5 border border-danger-start/20 rounded-xl p-6 text-danger-start text-sm font-medium flex items-center gap-3">
                        <AlertCircle size={18} /> {summaryError}
                      </div>
                    )}

                    {isSummarizing && !summaryContent && (
                      <div className="space-y-4">
                        <div className="h-4 bg-primary-start/10 rounded w-full animate-pulse" />
                        <div className="h-4 bg-primary-start/10 rounded w-5/6 animate-pulse" />
                        <div className="h-4 bg-primary-start/10 rounded w-4/6 animate-pulse" />
                      </div>
                    )}

                    {summaryContent && (
                      <div className="min-h-[150px]">
                        {activePerspective === 'senior' && renderMarkdown(perspectives.senior)}
                        {activePerspective === 'citizen' && renderMarkdown(perspectives.citizen)}
                        {isSummarizing && <span className="inline-block w-2 h-5 bg-primary-start animate-pulse ml-1 align-middle" />}
                      </div>
                    )}
                    
                    <div className="mt-8 pt-6 border-t border-border-main/30 flex items-center gap-2 text-[10px] text-text-muted font-black uppercase tracking-widest">
                      <Sparkles size={12} className="text-primary-start" /> 
                      {t('lawArticle.aiDisclaimer', 'Rezultati i gjeneruar nga modeli juridik i AI')}
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* CHAT PANEL */}
            <AnimatePresence>
              {chatVisible && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  ref={chatPanelRef}
                  className="border-t border-primary-start/30 bg-primary-start/[0.02] overflow-hidden"
                >
                  <div className="p-6 sm:p-8">
                    <div className="flex items-center gap-3 mb-6">
                      <div className="h-10 w-10 flex items-center justify-center bg-primary-start/10 rounded-xl border border-primary-start/20">
                        <MessageCircle className="text-primary-start" size={20} />
                      </div>
                      <div>
                        <h3 className="text-sm font-black text-text-primary uppercase tracking-widest">
                          {t('lawArticle.auditorTitle', 'Bisedë me Auditorin')}
                        </h3>
                        <p className="text-xs text-text-muted">
                          {t('lawArticle.auditorSubtitle', 'Bazuar në tekstin e ligjit')}
                        </p>
                      </div>
                    </div>

                    <div
                      ref={chatContainerRef}
                      className="space-y-4 max-h-[400px] overflow-y-auto custom-scrollbar mb-4 pr-2"
                    >
                      {messages.map((msg) => (
                        <div
                          key={msg.id}
                          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div
                            className={`max-w-[85%] p-4 rounded-2xl ${
                              msg.role === 'user'
                                ? 'bg-primary-start text-white rounded-br-sm'
                                : 'bg-surface border border-border-main text-text-primary rounded-bl-sm'
                            }`}
                          >
                            {msg.role === 'auditor' ? (
                              <div className="text-sm leading-relaxed whitespace-pre-wrap">
                                {renderMarkdown(msg.content) || (
                                  <span className="inline-block w-2 h-4 bg-primary-start animate-pulse" />
                                )}
                              </div>
                            ) : (
                              <p className="text-sm font-medium whitespace-pre-wrap">{msg.content}</p>
                            )}
                            <p className={`text-[10px] mt-2 ${msg.role === 'user' ? 'text-white/60' : 'text-text-muted'}`}>
                              {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                        </div>
                      ))}
                      
                      {showSuggestions && messages.length === 0 && (
                        <div className="flex flex-col gap-2 mt-2">
                          <p className="text-xs text-text-muted font-medium uppercase tracking-widest">Pyetje të sugjeruara:</p>
                          <div className="flex flex-wrap gap-2">
                            {SUGGESTED_QUESTIONS.map((question, idx) => (
                              <button
                                key={idx}
                                onClick={() => handleSendQuery(question)}
                                className="text-xs bg-surface border border-border-main hover:bg-primary-start hover:bg-primary-start/5 text-text-primary px-3 py-2 rounded-xl transition-all text-left cursor-pointer"
                                type="button"
                              >
                                {question}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {isAuditing && (
                        <div className="flex justify-start">
                          <div className="bg-surface border border-border-main p-4 rounded-2xl rounded-bl-sm">
                            <div className="flex gap-1">
                              <span className="w-2 h-2 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                              <span className="w-2 h-2 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                              <span className="w-2 h-2 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                            </div>
                          </div>
                        </div>
                      )}
                      {chatError && (
                        <div className="bg-danger-start/10 border border-danger-start/30 rounded-xl p-3">
                          <p className="text-danger-start text-xs font-medium flex items-center gap-2">
                            <AlertCircle size={14} /> {chatError}
                          </p>
                        </div>
                      )}
                    </div>

                    <div className="flex gap-3 items-end mt-4">
                      <textarea
                        ref={inputRef}
                        value={inputQuery}
                        onChange={(e) => setInputQuery(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendQuery(); } }}
                        placeholder={t('lawArticle.chatPlaceholder', 'Bëj një pyetje për këtë nen...')}
                        rows={2}
                        className="flex-1 p-3 bg-surface border border-border-main rounded-xl text-sm resize-none text-text-primary focus:border-primary-start outline-none transition-all placeholder:text-text-muted"
                        disabled={isAuditing}
                      />
                      <button
                        onClick={() => handleSendQuery()}
                        disabled={!inputQuery.trim() || isAuditing || !article?.chunk_id}
                        className="h-12 w-12 flex items-center justify-center rounded-xl bg-primary-start text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-end transition-all shadow-sm hover-lift"
                      >
                        {isAuditing ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                      </button>
                    </div>

                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Bottom Footer Stepper */}
            <div className="bg-surface px-8 py-6 flex flex-wrap justify-between items-center border-t border-border-main gap-4">
              <button
                onClick={handleBackToLibrary}
                className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift"
              >
                <ArrowLeft size={14} /> Biblioteka Ligjore
              </button>

              <div className="flex items-center gap-3">
                {prevArticleNum !== null && (
                  <button
                    type="button"
                    onClick={() => navigateToArticleNum(prevArticleNum)}
                    className="flex items-center gap-2 px-4 py-2 bg-canvas hover:bg-hover border border-border-main rounded-xl text-xs font-bold text-text-primary hover:border-primary-start transition-all hover-lift shadow-sm"
                  >
                    <ChevronLeft size={16} />
                    <span>{prevArticleNum === '0' ? 'Preambula' : `Neni ${prevArticleNum}`}</span>
                  </button>
                )}

                {nextArticleNum !== null && (
                  <button
                    type="button"
                    onClick={() => navigateToArticleNum(nextArticleNum)}
                    className="flex items-center gap-2 px-4 py-2 bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 rounded-xl text-xs font-black text-primary-start transition-all hover-lift shadow-sm uppercase tracking-wider"
                  >
                    <span>{`Neni ${nextArticleNum}`}</span>
                    <ChevronRight size={16} />
                  </button>
                )}
              </div>

              <button
                onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
                className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-text-primary transition-colors bg-canvas px-4 py-2 rounded-lg border border-border-main hover:border-primary-start hover-lift shadow-sm"
              >
                {t('general.top', 'Lart')} ↑
              </button>
            </div>

          </div>
        </div>
      </div>

      {/* FULL PDF SCROLLABLE MODAL */}
      <AnimatePresence>
        {showPdfModal && pdfUrl && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[200] p-4 sm:p-6">
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }} 
              animate={{ scale: 1, opacity: 1 }} 
              exit={{ scale: 0.95, opacity: 0 }} 
              className="glass-panel w-full max-w-6xl h-[90vh] rounded-2xl border border-border-main flex flex-col overflow-hidden shadow-2xl bg-canvas"
            >
              {/* Modal Header Controls */}
              <div className="px-6 py-4 bg-surface border-b border-border-main flex justify-between items-center shrink-0">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="p-2 bg-primary-start/10 text-primary-start rounded-lg border border-primary-start/20 shrink-0">
                    <FileText size={18} />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm sm:text-base font-black text-text-primary uppercase tracking-tight truncate">
                      {article.law_title}
                    </h3>
                    <p className="text-xs text-text-muted font-mono truncate">
                      {article.source}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <a 
                    href={pdfUrl} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="p-2.5 bg-surface border border-border-main hover:border-primary-start text-text-primary rounded-xl transition-all focus:outline-none flex items-center gap-2 text-xs font-bold uppercase tracking-wider"
                    title="Shkarko PDF"
                  >
                    <Download size={15} />
                    <span className="hidden sm:inline">Shkarko PDF</span>
                  </a>

                  <button 
                    type="button"
                    onClick={() => setIsPdfMinimized(true)} 
                    className="p-2.5 bg-surface border border-border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none"
                    aria-label="Minimize PDF viewer"
                    title="Minimizo"
                  >
                    <Minus size={18} />
                  </button>

                  <button 
                    type="button"
                    onClick={() => { setShowPdfModal(false); setIsPdfMinimized(false); }} 
                    className="p-2.5 bg-surface border border-border-main hover:bg-hover text-text-primary rounded-xl transition-all focus:outline-none"
                    aria-label="Close PDF viewer"
                    title="Mbyll"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              {/* Scrollable PDF Iframe Container */}
              <div className="flex-1 w-full h-full bg-slate-900 relative">
                <iframe 
                  src={pdfUrl} 
                  title={article.source} 
                  className="w-full h-full border-none"
                />
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* MINIMIZED DOCKED FLOATING PDF STATUS CARD */}
      <AnimatePresence>
        {showPdfModal && isPdfMinimized && article && (
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 50, opacity: 0 }}
            className="fixed bottom-6 right-6 z-[250] flex items-center gap-3.5 p-3.5 bg-surface border border-border-main rounded-2xl shadow-2xl backdrop-blur-md max-w-md"
          >
            <div className="p-2.5 bg-primary-start/15 text-primary-start rounded-xl shrink-0 border border-primary-start/20">
              <FileText size={18} />
            </div>
            
            <div 
              className="min-w-0 flex-1 cursor-pointer" 
              onClick={() => setIsPdfMinimized(false)}
            >
              <p className="text-xs font-black text-text-primary uppercase truncate tracking-tight">
                {article.law_title}
              </p>
              <p className="text-[10px] text-text-muted font-mono truncate">
                {article.source}
              </p>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                type="button"
                onClick={() => setIsPdfMinimized(false)}
                className="p-2 bg-canvas hover:bg-hover border border-border-main text-primary-start hover:text-primary-hover rounded-xl transition-all focus:outline-none shadow-sm"
                title="Zgjero (Full Screen)"
              >
                <Maximize2 size={14} />
              </button>

              <button
                type="button"
                onClick={() => { setShowPdfModal(false); setIsPdfMinimized(false); }}
                className="p-2 bg-canvas hover:bg-hover border border-border-main text-text-muted hover:text-danger-start rounded-xl transition-all focus:outline-none shadow-sm"
                title="Mbyll"
              >
                <X size={14} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </motion.div>
  );
}