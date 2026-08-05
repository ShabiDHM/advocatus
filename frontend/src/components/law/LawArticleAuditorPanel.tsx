// FILE: src/components/law/LawArticleAuditorPanel.tsx
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, X, AlertCircle, Sparkles, MessageCircle, Send, Loader2 } from 'lucide-react';
import { ChatMessage, SUGGESTED_QUESTIONS } from './lawArticleTypes';
import { LawCitationText } from '../LawCitationText';
import { TFunction } from 'i18next';

interface LawArticleAuditorPanelProps {
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
  summarySectionRef: React.Ref<HTMLDivElement>;
  chatPanelRef: React.Ref<HTMLDivElement>;
  chatContainerRef: React.Ref<HTMLDivElement>;
  inputRef: React.Ref<HTMLTextAreaElement>;
  t: TFunction;
}

export const LawArticleAuditorPanel: React.FC<LawArticleAuditorPanelProps> = ({
  summaryContent,
  isSummarizing,
  summaryError,
  cleanSummary,
  chatVisible,
  messages,
  showSuggestions,
  isAuditing,
  chatError,
  inputQuery,
  onInputQueryChange,
  onSendQuery,
  onCloseAuditor,
  summarySectionRef,
  chatPanelRef,
  chatContainerRef,
  inputRef,
  t,
}) => {
  const renderMarkdown = (text: string) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={i} className="h-4" />;
      if (trimmed.toUpperCase().includes('### NIVELI')) return null;
      if (trimmed.toUpperCase().includes('NIVELI 1:')) return null;
      if (trimmed.toUpperCase().includes('[NDARJA]')) return null;
      if (trimmed === '---') return null;
      return (
        <p key={i} className="mb-4 text-[15px] sm:text-[16px] text-text-primary leading-[1.75] font-normal">
          <LawCitationText text={trimmed} />
        </p>
      );
    });
  };

  return (
    <>
      <AnimatePresence>
        {(summaryContent || isSummarizing || summaryError) && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            ref={summarySectionRef}
            className="border-t border-primary-start/30 bg-primary-start/[0.02] overflow-hidden"
          >
            <div className="p-6 sm:p-10 relative">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4 border-b border-main pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-primary-start text-white rounded-xl flex items-center justify-center shadow-sm shrink-0">
                    <BrainCircuit size={20} />
                  </div>
                  <h3 className="text-base font-black text-text-primary uppercase tracking-wider">Interpretimi Ligjor</h3>
                </div>

                <button
                  type="button"
                  onClick={onCloseAuditor}
                  className="p-2 bg-surface border border-main rounded-xl text-text-muted hover:text-danger-start hover:border-danger-start/30 transition-colors hover-lift self-end sm:self-auto cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>

              {summaryError && (
                <div className="bg-danger-start/5 border border-danger-start/20 rounded-xl p-4 text-danger-start text-xs font-medium flex items-center gap-2">
                  <AlertCircle size={16} /> {summaryError}
                </div>
              )}

              {isSummarizing && !summaryContent && (
                <div className="space-y-3">
                  <div className="h-4 bg-primary-start/10 rounded w-full animate-pulse" />
                  <div className="h-4 bg-primary-start/10 rounded w-5/6 animate-pulse" />
                  <div className="h-4 bg-primary-start/10 rounded w-4/6 animate-pulse" />
                </div>
              )}

              {summaryContent && (
                <div className="min-h-[150px]">
                  {renderMarkdown(cleanSummary)}
                  {isSummarizing && <span className="inline-block w-2 h-5 bg-primary-start animate-pulse ml-1 align-middle" />}
                </div>
              )}

              <div className="mt-6 pt-4 border-t border-main/50 flex items-center gap-2 text-[10px] text-text-muted font-bold uppercase tracking-wider">
                <Sparkles size={12} className="text-primary-start" />
                {t('lawArticle.aiDisclaimer', 'Rezultati i gjeneruar nga modeli juridik i AI')}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

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
                  <h3 className="text-sm font-black text-text-primary uppercase tracking-wider">
                    {t('lawArticle.auditorTitle', 'Bisedë me Auditorin')}
                  </h3>
                  <p className="text-xs text-text-muted">{t('lawArticle.auditorSubtitle', 'Bazuar në tekstin e ligjit')}</p>
                </div>
              </div>

              <div ref={chatContainerRef} className="space-y-4 max-h-[400px] overflow-y-auto custom-scrollbar mb-4 pr-2">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`w-full max-w-[90%] p-4 rounded-2xl glass-panel bg-surface border border-main text-text-primary shadow-sm ${
                        msg.role === 'user' ? 'bg-primary-start/5 border-primary-start/30' : ''
                      }`}
                    >
                      {msg.role === 'auditor' ? (
                        <div className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap">
                          {renderMarkdown(msg.content) || <span className="inline-block w-2 h-4 bg-primary-start animate-pulse" />}
                        </div>
                      ) : (
                        <p className="text-xs sm:text-sm font-medium whitespace-pre-wrap text-text-primary">{msg.content}</p>
                      )}
                      <p className="text-[10px] mt-2 text-text-muted">
                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                ))}

                {showSuggestions && messages.length === 0 && (
                  <div className="flex flex-col gap-2 mt-2">
                    <p className="text-xs text-text-muted font-bold uppercase tracking-wider">Pyetje të sugjeruara:</p>
                    <div className="flex flex-wrap gap-2">
                      {SUGGESTED_QUESTIONS.map((question: string, idx: number) => (
                        <button
                          key={idx}
                          onClick={() => onSendQuery(question)}
                          className="text-xs bg-surface border border-main hover:bg-primary-start/10 hover:border-primary-start/40 text-text-primary px-3.5 py-2 rounded-xl transition-all text-left cursor-pointer"
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
                    <div className="bg-surface border border-main p-3.5 rounded-2xl">
                      <div className="flex gap-1.5">
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
                  onChange={(e) => onInputQueryChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      onSendQuery();
                    }
                  }}
                  placeholder={t('lawArticle.chatPlaceholder', 'Bëj një pyetje për këtë nen...')}
                  rows={2}
                  className="flex-1 p-3 bg-surface border border-main rounded-xl text-xs sm:text-sm resize-none text-text-primary focus:border-primary-start outline-none transition-all placeholder:text-text-muted"
                  disabled={isAuditing}
                />
                <button
                  type="button"
                  onClick={() => onSendQuery()}
                  disabled={!inputQuery.trim() || isAuditing}
                  className="h-11 w-11 flex items-center justify-center rounded-xl bg-primary-start text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-start/90 transition-all shadow-sm cursor-pointer"
                >
                  {isAuditing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};