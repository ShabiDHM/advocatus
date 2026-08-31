// FILE: src/components/law/LawArticleAuditorPanel.tsx
// PHOENIX PROTOCOL - AUDITOR MODAL POPUP DIALOG WITH CLEAN TYPOGRAPHY & PURGE CACHE

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BrainCircuit, X, AlertCircle, Sparkles, MessageCircle, Send, Loader2, Trash2, FileText } from 'lucide-react';
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
  onClearCache?: () => void;
  summarySectionRef: React.Ref<HTMLDivElement>;
  chatPanelRef: React.Ref<HTMLDivElement>;
  chatContainerRef: React.Ref<HTMLDivElement>;
  inputRef: React.Ref<HTMLTextAreaElement>;
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
  onClearCache,
  chatContainerRef,
  inputRef,
  t,
}) => {
  const [activeTab, setActiveTab] = useState<'analysis' | 'chat'>('analysis');

  if (!isOpen) return null;

  // Renderim i pastër dhe elegant tipografik pa linqe të ngatërruara
  const renderCleanTypography = (text: string) => {
    if (!text) return null;
    const lines = text.split('\n');

    return lines.map((line, i) => {
      const trimmed = line.trim();
      if (!trimmed) return <div key={i} className="h-3" />;

      // Tituj me Ikona (📌, ⚖️, ⚠️, 🔗)
      if (trimmed.startsWith('📌') || trimmed.startsWith('⚖️') || trimmed.startsWith('⚠️') || trimmed.startsWith('🔗') || trimmed.startsWith('###')) {
        const cleanTitle = trimmed.replace(/^###\s*/, '').replace(/\*\*/g, '');
        return (
          <h4 key={i} className="text-sm sm:text-base font-bold text-text-primary mt-4 mb-2 flex items-center gap-2 border-b border-main/40 pb-1.5">
            {cleanTitle}
          </h4>
        );
      }

      // Rreshta me pika
      if (trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('* ')) {
        const itemText = trimmed.replace(/^[-•*]\s*/, '').replace(/\*\*/g, '');
        return (
          <li key={i} className="ml-4 text-xs sm:text-sm text-text-secondary leading-relaxed list-disc mb-1.5 font-sans">
            {itemText}
          </li>
        );
      }

      // Paragraf standard i pastër
      const cleanParagraph = trimmed.replace(/\*\*/g, '');
      return (
        <p key={i} className="text-xs sm:text-sm text-text-secondary leading-relaxed font-sans mb-3 text-left">
          {cleanParagraph}
        </p>
      );
    });
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-hidden">
        
        {/* Backdrop Overlay */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onCloseAuditor}
          className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        />

        {/* Modal Box Dialog */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2 }}
          className="relative z-10 w-full max-w-3xl bg-surface border border-main rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[88vh] overflow-hidden"
        >
          
          {/* Header i Modalit me Titull, Butonin Shlyej dhe Mbyll */}
          <div className="px-5 sm:px-7 py-4 border-b border-main flex items-center justify-between bg-canvas/60 shrink-0">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 sm:h-10 sm:w-10 rounded-xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center text-primary-start">
                <BrainCircuit size={20} />
              </div>
              <div>
                <h3 className="text-xs sm:text-sm font-black text-text-primary uppercase tracking-wider">
                  Auditimi Inteligjent i Nenit
                </h3>
                <p className="text-[11px] text-text-muted">Analizë dhe këshillim ligjor i verifikuar</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Butoni Shlyej Memoren (Clear Cache) */}
              {onClearCache && summaryContent && (
                <button
                  type="button"
                  onClick={onClearCache}
                  className="h-9 px-3 flex items-center gap-1.5 text-xs font-semibold text-text-muted hover:text-danger-start bg-canvas hover:bg-danger-start/10 border border-main hover:border-danger-start/30 rounded-xl transition-all cursor-pointer"
                  title="Fshij analizën e ruajtur nga memoria"
                >
                  <Trash2 size={14} />
                  <span className="hidden sm:inline">Shlyej</span>
                </button>
              )}

              {/* Butoni Mbyll */}
              <button
                type="button"
                onClick={onCloseAuditor}
                className="h-9 w-9 flex items-center justify-center rounded-xl bg-canvas hover:bg-hover border border-main text-text-muted hover:text-text-primary transition-all cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Skedat (Tabs: Analiza Ligjore vs Bisedë me Auditorin) */}
          <div className="grid grid-cols-2 p-1.5 bg-canvas border-b border-main shrink-0 gap-1">
            <button
              type="button"
              onClick={() => setActiveTab('analysis')}
              className={`py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                activeTab === 'analysis' ? 'bg-primary-start text-white shadow-sm' : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <FileText size={14} />
              <span>Interpretimi Ligjor</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('chat')}
              className={`py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
                activeTab === 'chat' ? 'bg-primary-start text-white shadow-sm' : 'text-text-muted hover:text-text-primary'
              }`}
            >
              <MessageCircle size={14} />
              <span>Bisedë me Auditorin</span>
            </button>
          </div>

          {/* Trupi i Modalit me Scroll të Pastër */}
          <div className="p-5 sm:p-7 overflow-y-auto custom-scrollbar flex-1 bg-surface">
            
            {/* SKEDA 1: INTERPRETIMI LIGJOR */}
            {activeTab === 'analysis' && (
              <div>
                {summaryError && (
                  <div className="bg-danger-start/10 border border-danger-start/20 rounded-xl p-4 text-danger-start text-xs font-semibold flex items-center gap-2 mb-4">
                    <AlertCircle size={16} /> {summaryError}
                  </div>
                )}

                {isSummarizing && !summaryContent && (
                  <div className="space-y-3 py-6">
                    <div className="flex items-center gap-2 text-primary-start text-xs font-bold mb-4">
                      <Loader2 size={16} className="animate-spin" />
                      <span>Duke analizuar nenin nga baza ligjore...</span>
                    </div>
                    <div className="h-4 bg-primary-start/10 rounded w-full animate-pulse" />
                    <div className="h-4 bg-primary-start/10 rounded w-5/6 animate-pulse" />
                    <div className="h-4 bg-primary-start/10 rounded w-4/6 animate-pulse" />
                  </div>
                )}

                {summaryContent && (
                  <div className="space-y-2">
                    {renderCleanTypography(cleanSummary)}
                    {isSummarizing && (
                      <span className="inline-block w-2 h-4 bg-primary-start animate-pulse ml-1 align-middle" />
                    )}
                  </div>
                )}

                <div className="mt-6 pt-4 border-t border-main/60 flex items-center gap-2 text-[11px] text-text-muted font-medium">
                  <Sparkles size={13} className="text-primary-start shrink-0" />
                  <span>{t('lawArticle.aiDisclaimer', 'Analizë e ruajtur në memorie për të gjitha pajisjet tuaja.')}</span>
                </div>
              </div>
            )}

            {/* SKEDA 2: BISEDË INTERAKTIVE */}
            {activeTab === 'chat' && (
              <div className="flex flex-col h-full">
                <div ref={chatContainerRef} className="space-y-3.5 max-h-[350px] overflow-y-auto custom-scrollbar pr-1 mb-4">
                  {messages.length === 0 && (
                    <div className="text-center py-6">
                      <MessageCircle className="mx-auto text-text-muted mb-2 opacity-50" size={32} />
                      <p className="text-xs font-bold text-text-primary">Bëni pyetje mbi këtë nen</p>
                      <p className="text-[11px] text-text-muted mt-0.5">Auditori do të përgjigjet bazuar vetëm në legjislacionin zyrtar.</p>
                    </div>
                  )}

                  {messages.map((msg) => (
                    <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                      <div
                        className={`w-full max-w-[88%] p-3.5 rounded-2xl border text-xs sm:text-sm shadow-xs ${
                          msg.role === 'user'
                            ? 'bg-primary-start/10 border-primary-start/30 text-text-primary'
                            : 'bg-canvas border-main text-text-primary'
                        }`}
                      >
                        {msg.role === 'auditor' ? (
                          <div className="leading-relaxed">
                            {renderCleanTypography(msg.content) || <span className="inline-block w-2 h-4 bg-primary-start animate-pulse" />}
                          </div>
                        ) : (
                          <p className="font-medium whitespace-pre-wrap">{msg.content}</p>
                        )}
                        <p className="text-[9px] mt-1 text-text-muted">
                          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                  ))}

                  {showSuggestions && messages.length === 0 && (
                    <div className="flex flex-col gap-2 mt-2">
                      <p className="text-[11px] text-text-muted font-bold uppercase tracking-wider">Pyetje të shpeshta:</p>
                      <div className="flex flex-wrap gap-1.5">
                        {SUGGESTED_QUESTIONS.map((question: string, idx: number) => (
                          <button
                            key={idx}
                            onClick={() => onSendQuery(question)}
                            className="text-[11px] bg-canvas border border-main hover:border-primary-start/40 text-text-primary px-3 py-1.5 rounded-xl transition-all text-left cursor-pointer"
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
                      <div className="bg-canvas border border-main p-3 rounded-2xl flex gap-1.5">
                        <span className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-1.5 h-1.5 bg-primary-start rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  )}

                  {chatError && (
                    <div className="bg-danger-start/10 border border-danger-start/30 rounded-xl p-3 text-danger-start text-xs flex items-center gap-2">
                      <AlertCircle size={14} /> {chatError}
                    </div>
                  )}
                </div>

                {/* Inputi i Bisedës */}
                <div className="flex gap-2 items-end pt-2 border-t border-main">
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
                    placeholder="Bëj një pyetje konkrete për këtë nen..."
                    rows={2}
                    className="flex-1 p-2.5 bg-canvas border border-main rounded-xl text-xs sm:text-sm resize-none text-text-primary focus:border-primary-start outline-none transition-all placeholder:text-text-muted/60"
                    disabled={isAuditing}
                  />
                  <button
                    type="button"
                    onClick={() => onSendQuery()}
                    disabled={!inputQuery.trim() || isAuditing}
                    className="h-10 w-10 flex items-center justify-center rounded-xl bg-primary-start text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-primary-start/90 transition-all shadow-sm cursor-pointer shrink-0"
                  >
                    {isAuditing ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                  </button>
                </div>
              </div>
            )}

          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default LawArticleAuditorPanel;