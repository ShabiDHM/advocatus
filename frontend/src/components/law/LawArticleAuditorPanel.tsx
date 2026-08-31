// FILE: src/components/law/LawArticleAuditorPanel.tsx
// PHOENIX PROTOCOL - 100% MANUAL-TRIGGER AUDITOR MODAL WITH CLEAN CTA & INLINE CHAT

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
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
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

  // Renderim i pastër tipografik
  const renderCleanTypography = (text: string) => {
    if (!text) return null;
    const lines = text.split('\n');

    return lines.map((line, i) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={i} className="h-3" />;

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
            className="text-sm sm:text-base font-bold text-slate-900 dark:text-white mt-5 mb-2 flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-1.5"
          >
            {cleanTitle}
          </h4>
        );
      }

      if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
        const itemText = trimmed.replace(/^[-•*]\s*/, '').replace(/\*\*/g, '');
        return (
          <li
            key={i}
            className="ml-4 text-xs sm:text-sm text-slate-700 dark:text-slate-200 leading-relaxed list-disc mb-1.5 font-sans"
          >
            {itemText}
          </li>
        );
      }

      const cleanParagraph = trimmed.replace(/\*\*/g, '');
      return (
        <p
          key={i}
          className="text-xs sm:text-sm text-slate-700 dark:text-slate-200 leading-relaxed font-sans mb-3 text-left"
        >
          {cleanParagraph}
        </p>
      );
    });
  };

  const modalContent = (
    <AnimatePresence>
      <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-6 overflow-hidden">
        
        {/* 1. Backdrop i Fortë */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onCloseAuditor}
          className="fixed inset-0 bg-black/85 backdrop-blur-md"
        />

        {/* 2. Trupi i Modalit (100% Solid Opaque) */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 15 }}
          transition={{ duration: 0.2 }}
          style={{ backgroundColor: '#0B101D' }}
          className="relative z-10 w-full max-w-3xl bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-800 rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[90vh] sm:max-h-[85vh] overflow-hidden text-slate-900 dark:text-slate-100"
        >
          
          {/* Header me Titull, Ikonat Rianalizo, Shlyej dhe Mbyll */}
          <div className="px-5 sm:px-7 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-[#070B14] shrink-0">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center text-primary-start shrink-0">
                <BrainCircuit size={20} />
              </div>
              <div>
                <h3 className="text-xs sm:text-sm font-black uppercase tracking-wider text-slate-900 dark:text-white">
                  Auditimi Inteligjent i Nenit
                </h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Analizë dhe këshillim ligjor me DeepSeek</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Butoni Rianalizo */}
              {onReanalyze && summaryContent && !isSummarizing && (
                <button
                  type="button"
                  onClick={onReanalyze}
                  className="h-9 w-9 flex items-center justify-center rounded-xl bg-white dark:bg-[#0E1526] text-slate-400 hover:text-primary-start hover:bg-primary-start/10 border border-slate-200 dark:border-slate-700 transition-all cursor-pointer shadow-xs"
                  title="Rianalizo nenin nga e para"
                >
                  <RotateCcw size={15} />
                </button>
              )}

              {/* Butoni Shlyej */}
              {onClearCache && summaryContent && (
                <button
                  type="button"
                  onClick={onClearCache}
                  className="h-9 w-9 flex items-center justify-center rounded-xl bg-white dark:bg-[#0E1526] text-slate-400 hover:text-red-500 hover:bg-red-500/10 border border-slate-200 dark:border-slate-700 transition-all cursor-pointer shadow-xs"
                  title="Shlyej analizën nga memoria"
                >
                  <Trash2 size={15} />
                </button>
              )}

              {/* Butoni Mbyll */}
              <button
                type="button"
                onClick={onCloseAuditor}
                className="h-9 w-9 flex items-center justify-center rounded-xl bg-white dark:bg-[#0E1526] hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-400 hover:text-white transition-all cursor-pointer shadow-xs"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Përmbajtja me Scroll */}
          <div className="p-5 sm:p-7 overflow-y-auto custom-scrollbar flex-1 space-y-6">
            
            {/* 1. SEKSIONI I ANALIZËS LIGJORE */}
            <div>
              {summaryError && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-500 text-xs font-semibold flex items-center gap-2 mb-4">
                  <AlertCircle size={16} /> {summaryError}
                </div>
              )}

              {/* GJENDJA FILLARE (KUR NUK KA ANALIZË): BUTONI MANUAL "FILLO ANALIZËN" */}
              {!summaryContent && !isSummarizing && (
                <div className="py-8 px-4 border border-dashed border-slate-300 dark:border-slate-800 rounded-2xl flex flex-col items-center justify-center text-center bg-slate-50/50 dark:bg-[#070B14]/40">
                  <div className="h-12 w-12 rounded-2xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center text-primary-start mb-3">
                    <Sparkles size={24} />
                  </div>
                  <h4 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white mb-1">
                    Analizë dhe Interpretim me AI
                  </h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mb-5 leading-relaxed">
                    Kliko butonin e mëposhtëm për të gjeneruar analizën e thellë ligjore të këtij neni, ose bëj një pyetje direkte në fushën e chat-it.
                  </p>
                  
                  {onStartAnalysis && (
                    <button
                      type="button"
                      onClick={onStartAnalysis}
                      className="h-10 px-5 flex items-center gap-2 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider transition-all shadow-md hover-lift cursor-pointer"
                    >
                      <Play size={14} fill="currentColor" />
                      <span>Fillo Analizën e Nenit</span>
                    </button>
                  )}
                </div>
              )}

              {/* GJATË GJENERIMIT */}
              {isSummarizing && !summaryContent && (
                <div className="space-y-3 py-4">
                  <div className="flex items-center gap-2 text-primary-start text-xs font-bold mb-3">
                    <Loader2 size={15} className="animate-spin" />
                    <span>Duke analizuar nenin me DeepSeek...</span>
                  </div>
                  <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-full animate-pulse" />
                  <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-5/6 animate-pulse" />
                  <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-4/6 animate-pulse" />
                </div>
              )}

              {/* TEKSTI I ANALIZËS SË PËRFUNDUAR */}
              {summaryContent && (
                <div className="space-y-2">
                  {renderCleanTypography(cleanSummary)}
                  {isSummarizing && (
                    <span className="inline-block w-2 h-4 bg-primary-start animate-pulse ml-1 align-middle" />
                  )}
                </div>
              )}

              {summaryContent && (
                <div className="mt-5 pt-3 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2 text-[11px] text-slate-400 font-medium">
                  <Sparkles size={13} className="text-primary-start shrink-0" />
                  <span>{t('lawArticle.aiDisclaimer', 'Analizë e ruajtur në memorie për të gjitha pajisjet.')}</span>
                </div>
              )}
            </div>

            {/* 2. SEKSIONI I BISEDËS */}
            <div className="pt-4 border-t border-slate-200 dark:border-slate-800">
              <div ref={chatContainerRef} className="space-y-3 mb-2">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`w-full max-w-[90%] p-3.5 rounded-2xl text-xs sm:text-sm shadow-xs ${
                        msg.role === 'user'
                          ? 'bg-primary-start/15 border border-primary-start/30 text-slate-900 dark:text-white'
                          : 'bg-slate-100 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100'
                      }`}
                    >
                      {msg.role === 'auditor' ? (
                        <div className="leading-relaxed">
                          {renderCleanTypography(msg.content) || (
                            <span className="inline-block w-2 h-4 bg-primary-start animate-pulse" />
                          )}
                        </div>
                      ) : (
                        <p className="font-medium whitespace-pre-wrap">{msg.content}</p>
                      )}
                      <p className="text-[9px] mt-1 text-slate-400">
                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                ))}

                {/* Sugjerimet */}
                {showSuggestions && messages.length === 0 && (
                  <div className="flex flex-col gap-2 mt-3">
                    <p className="text-[11px] text-slate-400 font-bold uppercase tracking-wider">Pyetje të sugjeruara:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {SUGGESTED_QUESTIONS.map((question: string, idx: number) => (
                        <button
                          key={idx}
                          onClick={() => onSendQuery(question)}
                          className="text-[11px] bg-slate-100 dark:bg-[#070B14] border border-slate-200 dark:border-slate-800 hover:border-primary-start/50 text-slate-700 dark:text-slate-300 px-3 py-1.5 rounded-xl transition-all text-left cursor-pointer"
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
                    <AlertCircle size={14} /> {chatError}
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* 3. Tastiera Dinamike Auto-Expanding */}
          <div className="p-3 sm:p-4 bg-slate-50 dark:bg-[#070B14] border-t border-slate-200 dark:border-slate-800 shrink-0">
            <div className="flex gap-2 items-end">
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
                style={{ height: '42px', minHeight: '42px', maxHeight: '120px' }}
                className="flex-1 px-3.5 py-2.5 bg-white dark:bg-[#0B101D] border border-slate-200 dark:border-slate-700 rounded-xl text-xs sm:text-sm resize-none overflow-y-auto custom-scrollbar text-slate-900 dark:text-white focus:border-primary-start outline-none transition-all placeholder:text-slate-400"
                disabled={isAuditing}
              />
              <button
                type="button"
                onClick={handleSendClick}
                disabled={!inputQuery.trim() || isAuditing}
                className="h-[42px] w-[42px] flex items-center justify-center rounded-xl bg-primary-start text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-start/90 transition-all shadow-sm cursor-pointer shrink-0"
              >
                {isAuditing ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
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