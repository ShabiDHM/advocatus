// FILE: src/pages/LawArticlePage.tsx
// PHOENIX PROTOCOL - LAW ARTICLE PAGE V10.1 (ALIGNED WITH API SIGNATURE)

import { useEffect, useState, useRef, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Scale, Calendar, AlertCircle, BookOpen, Sparkles, Loader2, X, BrainCircuit, User, Send, MessageCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// TASK 3: ArticleData interface with chunk_id
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

// ========== PHOENIX: ENHANCED TEXT SANITIZATION ==========
const normalizeText = (raw: string): string => {
  if (!raw) return '';

  let cleaned = raw.replace(/---\s*\[?FAQJA\s+\d+\]?\s*---/gi, '');
  const lawHeaderRegex = /(?:^|\n)\s*LIGJI\s+NR\.\s+\d+[\/\-]?[A-Z]?\d*\s+[A-ZËÇSHQËWXYZ].*?(?=\n|$)/gi;
  cleaned = cleaned.replace(lawHeaderRegex, '');
  
  const lines = cleaned.split('\n');
  const mergedLines: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const currentLine = lines[i].trim();
    if (!currentLine) {
      mergedLines.push(currentLine);
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
  cleaned = cleaned.replace(/(\d+\.)\s*\n\s*\1/g, '$1');
  cleaned = cleaned.replace(/(\d+\.)\s*\n\s*\d+\.\s*/g, '$1 ');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  cleaned = cleaned.trim();
  
  const paragraphs = cleaned.split(/\n\n+/);
  const normalizedParagraphs = paragraphs.map(para =>
    para.replace(/\n/g, ' ').replace(/\s+/g, ' ').trim()
  );
  
  return normalizedParagraphs.filter(p => p.length > 0).join('\n\n');
};

// ========== LIGHTWEIGHT MARKDOWN RENDERER ==========
const renderMarkdown = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-4" />;
        if (trimmed.toUpperCase().includes('### NIVELI')) return null;
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

// Helper function to generate a fallback chunk_id when backend doesn't provide one
const generateFallbackChunkId = (lawTitle: string, articleNumber: string): string => {
  const cleanTitle = lawTitle.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 80);
  const cleanArticle = articleNumber.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20);
  return `chunk_${cleanTitle}_${cleanArticle}`;
};

// Suggested questions for the auditor
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

  // Parse dual perspective from summary
  const perspectives = useMemo(() => {
    let cleanText = summaryContent.replace(/\n\n---\n\*Kjo përgjigje është gjeneruar nga AI, vetëm për referencë\.\*/g, '');
    let parts = cleanText.split('[NDARJA]');
    if (parts.length < 2) {
        parts = cleanText.split(/(?:\n---\n|\n### NIVELI 2.*?\n)/i);
    }
    return {
        senior: parts[0] ? parts[0].trim() : '',
        citizen: parts[1] ? parts[1].trim() : ''
    };
  }, [summaryContent]);

  // TASK 3: Load article and set state with chunk_id
  useEffect(() => {
    if (!lawTitle || !articleNumber) {
      setError(t('lawArticle.missingParams', 'Parametrat e artikullit mungojnë.'));
      setLoading(false);
      return;
    }
    
    const loadArticle = async () => {
      try {
        const data = await apiService.getLawArticle(lawTitle, articleNumber);
        const normalizedText = normalizeText(data.text);
        
        // Get chunk_id from response or generate fallback
        let chunkId = data.chunk_id || '';
        
        if (!chunkId) {
          chunkId = generateFallbackChunkId(lawTitle, articleNumber);
          console.log('[DEBUG] Backend did not provide chunk_id, using fallback:', chunkId);
        } else {
          console.log('[DEBUG] Using chunk_id from backend:', chunkId);
        }
        
        // TASK 3: Set article with chunk_id
        setArticle({
          law_title: data.law_title,
          article_number: data.article_number || articleNumber,
          source: data.source,
          text: normalizedText,
          chunk_id: chunkId,
        });
        
        console.log('[DEBUG] Article loaded successfully with chunk_id:', chunkId);
      } catch (err: any) {
        console.error('[ERROR] Failed to load article:', err);
        setError(err.message || t('lawArticle.fetchError', 'Dështoi ngarkimi i artikullit.'));
      } finally {
        setLoading(false);
      }
    };
    
    loadArticle();
  }, [lawTitle, articleNumber, t]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatContainerRef.current && chatVisible) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, chatVisible]);

  // Initialize chat after summary finishes
  useEffect(() => {
    if (summaryContent && chatVisible && messages.length === 0 && !isSummarizing) {
      console.log('[DEBUG] Chat initialized, showing suggestions');
      setTimeout(() => {
        setShowSuggestions(true);
      }, 500);
      
      setTimeout(() => {
        chatPanelRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        inputRef.current?.focus();
      }, 300);
    }
  }, [summaryContent, chatVisible, messages.length, isSummarizing]);

  // Single button triggers summary + chat
  const handleStartAudit = async () => {
    if (!article || isSummarizing) return;
    
    console.log('[DEBUG] Starting audit for article:', article.law_title);
    console.log('[DEBUG] Article chunk_id:', article.chunk_id);
    
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
      
      console.log('[DEBUG] Summary completed, showing chat');
      setChatVisible(true);
      
    } catch (err: any) {
      console.error('[ERROR] Summary failed:', err);
      setSummaryError(t('lawArticle.aiError', 'Dështoi analiza inteligjente.'));
    } finally {
      setIsSummarizing(false);
    }
  };

  // TASK 2: Handle sending a chat query - passes chunk_id to API
  const handleSendQuery = async (query?: string) => {
    console.log('[DEBUG] handleSendQuery called');
    
    if (!article) {
      console.log('[ERROR] No article loaded');
      setChatError('Artikulli nuk është ngarkuar. Ju lutemi rifreskoni faqen.');
      return;
    }

    // Validate chunk_id exists
    console.log('[DEBUG] Sending chunk_id to Auditor:', article.chunk_id);
    
    if (!article.chunk_id) {
      console.log('[ERROR] No chunk_id available - this should not happen');
      setChatError('Artikulli nuk ka identifikues të vlefshëm. Ju lutemi rifreskoni faqen.');
      return;
    }

    const finalQuery = query ?? inputQuery.trim();
    if (!finalQuery) {
      console.log('[DEBUG] Empty query, ignoring');
      return;
    }
    
    if (isAuditing) {
      console.log('[DEBUG] Already auditing, ignoring');
      return;
    }

    console.log('[DEBUG] Sending query to auditor:', finalQuery);
    console.log('[DEBUG] Using chunk_id:', article.chunk_id);

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
      console.log('[DEBUG] Calling apiService.askLawAuditor with chunk_id:', article.chunk_id);
      // TASK 2: Pass chunk_id as first argument, query as second
      const stream = apiService.askLawAuditor(article.chunk_id, finalQuery);
      let accumulatedContent = '';

      for await (const chunk of stream) {
        accumulatedContent += chunk;
        console.log('[DEBUG] Received chunk, length:', chunk.length);
        setMessages(prev => prev.map(msg =>
          msg.id === auditorMessageId
            ? { ...msg, content: accumulatedContent }
            : msg
        ));
      }
      console.log('[DEBUG] Query completed successfully');
    } catch (err: any) {
      console.error('[ERROR] Audit query failed:', err);
      setChatError(err.message || 'Dështoi komunikimi me Auditorin.');
      setMessages(prev => prev.filter(msg => msg.id !== auditorMessageId));
    } finally {
      setIsAuditing(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleSuggestedClick = (question: string) => {
    console.log('[DEBUG] Suggested question clicked:', question);
    handleSendQuery(question);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendQuery();
    }
  };

  const handleCloseAuditor = () => {
    console.log('[DEBUG] Closing auditor');
    setChatVisible(false);
    setMessages([]);
    setSummaryContent('');
    setShowSuggestions(false);
  };

  const handleBack = () => {
    navigate('/business/briefing', { state: { activeMode: 'library' } });
  };

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
          <button onClick={handleBack} className="btn-primary flex items-center gap-2 hover-lift shadow-sm"><ArrowLeft size={18} /> {t('lawArticle.backToSearch', 'Kthehu te kërkimi')}</button>
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
          
          <div className="flex items-center justify-between mb-8">
            <button
              onClick={handleBack}
              className="group flex items-center gap-3 text-text-muted hover:text-text-primary transition-colors font-bold text-sm uppercase tracking-widest hover-lift"
            >
              <div className="p-2 rounded-lg bg-surface border border-border-main group-hover:border-primary-start transition-colors">
                <ArrowLeft size={16} className="text-primary-start" />
              </div>
              {t('general.back', 'Kthehu Mbrapa')}
            </button>

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
                onClick={handleCloseAuditor}
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
                  <div className="flex items-center gap-2 bg-canvas text-text-secondary border border-border-main px-3 py-1.5 rounded-lg">
                    <Calendar size={14} />
                    <span className="text-xs font-bold uppercase tracking-widest truncate max-w-[150px] sm:max-w-[200px]">{article.source}</span>
                  </div>
                </div>
                <h1 className="text-2xl sm:text-3xl font-black text-text-primary leading-tight tracking-tighter">{article.law_title}</h1>
                <div className="flex items-center gap-4 border-t border-border-main/50 pt-6 mt-2">
                  <Scale size={24} className="text-primary-start" />
                  <p className="text-lg font-black text-primary-start uppercase tracking-widest">{t('lawArticle.article', 'Neni')} {article.article_number || ''}</p>
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
                                onClick={() => handleSuggestedClick(question)}
                                className="text-xs bg-surface border border-border-main hover:border-primary-start hover:bg-primary-start/5 text-text-primary px-3 py-2 rounded-xl transition-all text-left cursor-pointer"
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

                    {/* Chat Input */}
                    <div className="flex gap-3 items-end mt-4">
                      <textarea
                        ref={inputRef}
                        value={inputQuery}
                        onChange={(e) => setInputQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
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

            {/* Footer Actions */}
            <div className="bg-surface px-8 py-6 flex justify-between items-center border-t border-border-main">
              <button
                onClick={handleBack}
                className="text-xs font-black uppercase tracking-widest text-text-muted hover:text-primary-start transition-colors flex items-center gap-2 hover-lift"
              >
                <ArrowLeft size={14} /> {t('lawArticle.backToSearch', 'Kthehu te kërkimi')}
              </button>
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
    </motion.div>
  );
}