// FILE: src/components/law/LawArticleAuditorPanel.tsx
// PHOENIX PROTOCOL - EXPANDED WIDESCREEN AUDITOR MODAL (100% PURE ALBANIAN TEXT RENDERING)

import React, { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, X, AlertCircle, Sparkles, Send, Loader2, Trash2, RotateCcw, Play } from 'lucide-react';
import { ChatMessage, SUGGESTED_QUESTIONS } from './lawArticleTypes';
import { TFunction } from 'i18next';

interface LawArticleAuditorPanelProps {
  isOpen: boolean;
  summaryContent: string;
  isSummarizing: boolean;
  summaryError: string;
  cleanSummary: string;
  chatVisible: boolean;
  messages: ChatMessage[];
  showSuggestions: boolean;
  isAuditing: boolean;
  chatError: string | null;
  inputQuery: string;
  onInputQueryChange: (val: string) => void;
  onSendQuery: (query?: string) => void;
  onCloseAuditor: () => void;
  onStartAnalysis?: () => void;
  onClearCache?: () => void;
  onReanalyze?: () => void;
  summarySectionRef?: React.Ref<HTMLDivElement>;
  chatPanelRef?: React.Ref<HTMLDivElement>;
  chatContainerRef?: React.Ref<HTMLDivElement>;
  inputRef?: React.Ref<HTMLTextAreaElement>;
  t: TFunction;
}

export const LawArticleAuditorPanel: React.FC<LawArticleAuditorPanelProps> = ({
  isOpen,
  summaryContent,
  isSummarizing,
  summaryError,
  cleanSummary,
  messages,
  showSuggestions,
  isAuditing,
  chatError,
  inputQuery,
  onInputQueryChange,
  onSendQuery,
  onCloseAuditor,
  onStartAnalysis,
  onClearCache,
  onReanalyze,
  chatContainerRef,
  inputRef,
  t,
}) => {
  const [mounted, setMounted] = useState(false);
  const localTextareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  if (!isOpen || !mounted) return null;

  // Auto-Zgjerimi i Tastierës sipas Tekstit
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onInputQueryChange(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 130)}px`;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!inputQuery.trim() || isAuditing) return;
      onSendQuery();
      if (localTextareaRef.current) {
        localTextareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleSendClick = () => {
    if (!inputQuery.trim() || isAuditing) return;
    onSendQuery();
    if (localTextareaRef.current) {
      localTextareaRef.current.style.height = 'auto';
    }
  };

  // Renderim i pastër në gjuhën shqipe
  const renderCleanTypography = (text: string) => {
    if (!text) return null;
    const lines = text.split('\n');

    return lines.map((line, i) => {
      let trimmed = line.trim();
      if (!trimmed) return <div key={i} className="h-3" />;

      // Pastrimi automatik i termave latine nëse kanë mbetur në memorie
      trimmed = trimmed.replace(/ratio\s*legis/gi, 'Fryma e Ligjit');

      // Tituj me Ikona (📌, ⚖️, ⚠️, 🔗)
      if (
        trimmed.startsWith('📌') ||
        trimmed.startsWith('⚖️') ||
        trimmed.startsWith('⚠️') ||
        trimmed.startsWith('🔗') ||
        trimmed.startsWith('###')
      ) {
        const cleanTitle = trimmed.replace(/^###\s*/, '').replace(/\*\*/g, '');
        return (
          <h4
            key={i}
            className="text-sm sm:text-base md:text-lg font-bold text-slate-900 dark:text-white mt-6 mb-2.5 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2"
          >
            {cleanTitle}
          </h4>
        );
      }

      // Rreshta me pika
      if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
        const itemText = trimmed.replace(/^[-•*]\s*/, '').replace(/\*\*/g, '');
        return (
          <li
            key={i}
            className="ml-4 sm:ml-6 text-xs sm:text-sm md:text-[15px] text-slate-700 dark:text-slate-200 leading-relaxed list-disc mb-2 font-sans"
          >
            {itemText}
          </li>
        );
      }

      const cleanParagraph = trimmed.replace(/\*\*/g, '');
      return (
        <p
          key={i}
          className="text-xs sm:text-sm md:text-[15px] text-slate-700 dark:text-slate-200 leading-relaxed font-sans mb-3.5 text-left"
        >
          {cleanParagraph}
        </p>
      );
    });
  };

  const modalContent = (
    <AnimatePresence>
      <div className="fixed inset-0 z-[9999] flex items-center justify-center p-2 sm:p-4 md:p-6 lg:p-8 overflow-hidden">
        
        {/* 1. Backdrop i Fortë */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onCloseAuditor}
          className="fixed inset-0 bg-black/85 backdrop-blur-md"
        />

        {/* 2. Trupi i Zgjeruar i Modalit (MAX-W-5XL) */}
        <motion.div
          initial={{ opacity: 0, scale: 0.97, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.97, y: 15 }}
          transition={{ duration: 0.2 }}
          style={{ backgroundColor: '#0B101D' }}
          className="relative z-10 w-full max-w-5xl xl:max-w-6xl bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[92vh] sm:max-h-[88vh] overflow-hidden text-slate-900 dark:text-slate-100"
        >
          
          {/* Header me Titull dhe Kontrolle */}
          <div className="px-6 sm:px-8 py-4 sm:py-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-[#070B14] shrink-0">
            <div className="flex items-center gap-3.5">
              <div className="h-10 w-10 sm:h-11 sm:w-11 rounded-xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center text-primary-start shrink-0">
                <BrainCircuit size={22} />
              </div>
              <div>
                <h3 className="text-xs sm:text-base font-black uppercase tracking-wider text-slate-900 dark:text-white">
                  Auditimi Inteligjent i Nenit
                </h3>
                <p className="text-[11px] sm:text-xs text-slate-500 dark:text-slate-400">Analizë dhe këshillim ligjor me DeepSeek</p>
              </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-2.5">
              {/* Butoni Rianalizo */}
              {onReanalyze && summaryContent && !isSummarizing && (
                <button
                  type="button"
                  onClick={onReanalyze}
                  className="h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center rounded-xl bg-white dark:bg-[#0E1526] text-slate-400 hover:text-primary-start hover:bg-primary-start/10 border border-slate-200 dark:border-slate-700 transition-all cursor-pointer shadow-xs"
                  title="Rianalizo nenin nga e para"
                >
                  <RotateCcw size={16} />
                </button>
              )}

              {/* Butoni Shlyej */}
              {onClearCache && summaryContent && (
                <button
                  type="button"
                  onClick={onClearCache}
                  className="h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center rounded-xl bg-white dark:bg-[#0E1526] text-slate-400 hover:text-red-500 hover:bg-red-500/10 border border-slate-200 dark:border-slate-700 transition-all cursor-pointer shadow-xs"
                  title="Shlyej analizën nga memoria"
                >
                  <Trash2 size={16} />
                </button>
              )}

              {/* Butoni Mbyll */}
              <button
                type="button"
                onClick={onCloseAuditor}
                className="h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center rounded-xl bg-white dark:bg-[#0E1526] hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-400 hover:text-white transition-all cursor-pointer shadow-xs"
              >
                <X size={17} />
              </button>
            </div>
          </div>

          {/* Përmbajtja me Scroll */}
          <div className="px-6 sm:px-10 py-6 sm:py-8 overflow-y-auto custom-scrollbar flex-1 space-y-6 sm:space-y-8">
            
            {/* 1. SEKSIONI I ANALIZËS LIGJORE */}
            <div>
              {summaryError && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-500 text-xs sm:text-sm font-semibold flex items-center gap-2 mb-4">
                  <AlertCircle size={17} /> {summaryError}
                </div>
              )}

              {/* GJENDJA FILLARE: BUTONI MANUAL "FILLO ANALIZËN" */}
              {!summaryContent && !isSummarizing && (
                <div className="py-12 px-6 border border-dashed border-slate-300 dark:border-slate-800 rounded-3xl flex flex-col items-center justify-center text-center bg-slate-50/50 dark:bg-[#070B14]/40">
                  <div className="h-14 w-14 rounded-2xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center text-primary-start mb-4">
                    <Sparkles size={28} />
                  </div>
                  <h4 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white mb-1.5">
                    Analizë dhe Interpretim me AI
                  </h4>
                  <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-lg mb-6 leading-relaxed">
                    Kliko butonin e mëposhtëm për të gjeneruar analizën e thellë ligjore të këtij neni, ose bëj një pyetje direkte në fushën e chat-it.
                  </p>
                  
                  {onStartAnalysis && (
                    <button
                      type="button"
                      onClick={onStartAnalysis}
                      className="h-11 px-6 flex items-center gap-2.5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white text-xs sm:text-sm font-bold uppercase tracking-wider transition-all shadow-lg hover-lift cursor-pointer"
                    >
                      <Play size={15} fill="currentColor" />
                      <span>Fillo Analizën e Nenit</span>
                    </button>
                  )}
                </div>
              )}

              {/* GJATË GJENERIMIT */}
              {isSummarizing && !summaryContent && (
                <div className="space-y-4 py-6">
                  <div className="flex items-center gap-2 text-primary-start text-xs sm:text-sm font-bold mb-4">
                    <Loader2 size={17} className="animate-spin" />
                    <span>Duke analizuar nenin me DeepSeek...</span>
                  </div>
                  <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded-lg w-full animate-pulse" />
                  <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded-lg w-5/6 animate-pulse" />
                  <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded-lg w-4/6 animate-pulse" />
                </div>
              )}

              {/* TEKSTI I ANALIZËS SË PËRFUNDUAR */}
              {summaryContent && (
                <div className="space-y-2.5 max-w-[110ch]">
                  {renderCleanTypography(cleanSummary)}
                  {isSummarizing && (
                    <span className="inline-block w-2 h-4 bg-primary-start animate-pulse ml-1 align-middle" />
                  )}
                </div>
              )}

              {summaryContent && (
                <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2 text-xs text-slate-400 font-medium">
                  <Sparkles size={14} className="text-primary-start shrink-0" />
                  <span>{t('lawArticle.aiDisclaimer', 'Analizë e ruajtur në memorie për të gjitha pajisjet.')}</span>
                </div>
              )}
            </div>

            {/* 2. SEKSIONI I BISEDËS */}
            {summaryContent && (
              <div className="pt-6 border-t border-slate-200 dark:border-slate-800">
                <div ref={chatContainerRef} className="space-y-3.5 mb-2">
                  {messages.map((msg) => (
                    <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                      <div
                        className={`w-full max-w-[85%] p-4 rounded-2xl text-xs sm:text-sm shadow-xs ${
                          msg.role === 'user'
                            ? 'bg-primary-start/15 border border-primary-start/30 text-slate-900 dark:text-white'
                            : 'bg-slate-100 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100'
                        }`}
                      >
                        {msg.role === 'auditor' ? (
                          <div className="leading-relaxed max-w-[100ch]">
                            {renderCleanTypography(msg.content) || (
                              <span className="inline-block w-2 h-4 bg-primary-start animate-pulse" />
                            )}
                          </div>
                        ) : (
                          <p className="font-medium whitespace-pre-wrap">{msg.content}</p>
                        )}
                        <p className="text-[10px] mt-1.5 text-slate-400">
                          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))}

                  {/* Sugjerimet */}
                  {showSuggestions && messages.length === 0 && (
                    <div className="flex flex-col gap-2 mt-3">
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">Pyetje të sugjeruara:</p>
                      <div className="flex flex-wrap gap-2">
                        {SUGGESTED_QUESTIONS.map((question: string, idx: number) => (
                          <button
                            key={idx}
                            onClick={() => onSendQuery(question)}
                            className="text-xs bg-slate-100 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 hover:border-primary-start/50 text-slate-700 dark:text-slate-300 px-3.5 py-2 rounded-xl transition-all text-left cursor-pointer"
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
                      <div className="bg-slate-100 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 p-3 rounded-2xl flex gap-1.5">
                        <span className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  )}

                  {chatError && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 text-red-500 text-xs flex items-center gap-2">
                      <AlertCircle size={15} /> {chatError}
                    </div>
                  )}
                </div>
              </div>
            )}

          </div>

          {/* 3. Tastiera Dinamike e Zgjeruar */}
          <div className="p-4 sm:p-5 bg-slate-50 dark:bg-[#070B14] border-t border-slate-200 dark:border-slate-800 shrink-0">
            <div className="flex gap-2.5 items-end max-w-5xl mx-auto w-full">
              <textarea
                ref={(el) => {
                  localTextareaRef.current = el;
                  if (typeof inputRef === 'function') {
                    (inputRef as (node: HTMLTextAreaElement | null) => void)(el);
                  } else if (inputRef && typeof inputRef === 'object' && 'current' in inputRef) {
                    (inputRef as React.MutableRefObject<HTMLTextAreaElement | null>).current = el;
                  }
                }}
                value={inputQuery}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                placeholder="Bëj një pyetje konkrete për këtë nen..."
                rows={1}
                style={{ height: '44px', minHeight: '44px', maxHeight: '130px' }}
                className="flex-1 px-4 py-2.5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm resize-none overflow-y-auto custom-scrollbar text-slate-900 dark:text-white focus:border-primary-start outline-none transition-all placeholder:text-slate-400"
                disabled={isAuditing}
              />
              <button
                type="button"
                onClick={handleSendClick}
                disabled={!inputQuery.trim() || isAuditing}
                className="h-[44px] w-[44px] flex items-center justify-center rounded-xl bg-primary-start text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-start/90 transition-all shadow-md cursor-pointer shrink-0"
              >
                {isAuditing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
            </div>
          </div>

        </motion.div>
      </div>
    </AnimatePresence>
  );

  return createPortal(modalContent, document.body);
};

export default LawArticleAuditorPanel;