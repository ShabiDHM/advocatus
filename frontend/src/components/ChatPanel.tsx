// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V41.0 (NATIVE INTEGRATION OF DRAFT_RESULT_RENDERER & REAL A4 PAPER CANVAS)

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, BrainCircuit, User, RefreshCw, Sparkles, FileText } from 'lucide-react';
import { ChatMessage, Document } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { autoLinkLegalCitations, extractFollowUpQuestions } from '../utils/chatHelpers';
import { MessageCopyButton } from './chat/MessageCopyButton';
import { FeedbackButtons } from './chat/FeedbackButtons';
import { buildMarkdownComponents } from './chat/MarkdownRenderer';
import { CommandPaletteGrid } from './chat/CommandPaletteGrid';
import { ChatHeader } from './chat/ChatHeader';

// IMPORTIMI I DREJTPËRDREJTË I RENDERUESIT TË HARTIMIT
import { DraftResultRenderer } from '../drafting/components/DraftResultRenderer';

export type ChatMode = 'general' | 'document';
export type ReasoningMode = 'FAST' | 'DEEP';
export type Jurisdiction = 'ks' | 'al';

interface ChatPanelProps {
  messages: ChatMessage[];
  connectionStatus: string;
  reconnect: () => void;
  onSendMessage: (
    text: string,
    mode: ChatMode,
    reasoning: ReasoningMode,
    domain: string,
    documentIds?: string[],
    jurisdiction?: Jurisdiction
  ) => void;
  isSendingMessage: boolean;
  onClearChat: () => void;
  onExportChat?: () => void;
  t: TFunction;
  className?: string;
  activeContextId: string;
  isPro?: boolean;
  documents?: Document[];
  selectedDocumentIds?: string[];
  onDocumentSelectionChange?: (ids: string[]) => void;
  userSalutation?: string;
  clientPosition?: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL' | string;
}

// Detektor universal për aktet zyrtare gjyqësore
const isOfficialLegalDraft = (content: string): boolean => {
  if (!content || typeof content !== 'string') return false;
  const lower = content.toLowerCase();
  return (
    lower.includes('kallëzim penal') ||
    lower.includes('kallzim penal') ||
    lower.includes('kërkesëpadi') ||
    lower.includes('padi civile') ||
    lower.includes('kundërpadi') ||
    lower.includes('prapësim') ||
    lower.includes('d r e j t u a r') ||
    lower.includes('drejtuar:') ||
    lower.includes('organi marrës:') ||
    lower.includes('prokurorisë speciale') ||
    lower.includes('gjykatës themelore') ||
    lower.includes('gjykata themelore') ||
    lower.includes('parashtruesi:')
  );
};

const ChatPanel: React.FC<ChatPanelProps> = ({
  messages = [],
  connectionStatus,
  onSendMessage,
  isSendingMessage,
  onClearChat,
  onExportChat,
  t,
  className,
  activeContextId,
  documents = [],
  selectedDocumentIds = [],
  onDocumentSelectionChange,
  userSalutation = 'Avokat',
  clientPosition = 'DEFENDANT',
  isPro = true,
}) => {
  const [input, setInput] = useState('');
  const [reasoningMode] = useState<ReasoningMode>('DEEP');
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());
  const [lastUserMessage, setLastUserMessage] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSendingMessage]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 250)}px`;
    }
  }, [input]);

  const sendMessage = (text: string) => {
    if (!text.trim() || isSendingMessage) return;
    const mode = activeContextId === 'general' ? 'general' : 'document';
    setLastUserMessage(text);
    onSendMessage(text, mode, reasoningMode, 'automatic', selectedDocumentIds, 'ks');
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleFeedback = (index: number) => {
    setFeedbackGiven((prev) => new Set(prev).add(index));
  };

  const handleRetry = () => {
    if (lastUserMessage) sendMessage(lastUserMessage);
  };

  const safeMessages = Array.isArray(messages) ? messages : [];

  const displayMessages = safeMessages.filter(
    (m) => m && typeof m.content === 'string' && m.content.trim() !== ''
  );

  const isAwaitingFirstToken =
    isSendingMessage &&
    (displayMessages.length === 0 || displayMessages[displayMessages.length - 1].role === 'user');

  return (
    <div className={`flex flex-col glass-panel overflow-hidden h-full w-full border border-main bg-canvas shadow-sm ${className}`}>
      <ChatHeader
        connectionStatus={connectionStatus}
        activeContextId={activeContextId}
        onClearChat={onClearChat}
        onExportChat={onExportChat}
        t={t}
        documents={documents}
        selectedDocumentIds={selectedDocumentIds}
        onDocumentSelectionChange={onDocumentSelectionChange}
        isPro={isPro}
      />

      {/* BODY CONTEXT */}
      <div className="flex-1 overflow-y-auto p-3 sm:p-5 bg-canvas/10 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden shadow-[inset_0_1px_8px_rgba(0,0,0,0.01)] border-b border-main flex flex-col">
        {displayMessages.length === 0 && !isSendingMessage ? (
          <div className="flex-1 min-h-full flex items-center justify-center w-full">
            <CommandPaletteGrid
              userSalutation={userSalutation}
              clientPosition={clientPosition}
              selectedDocumentIds={selectedDocumentIds}
              documents={documents}
              onSendMessage={sendMessage}
            />
          </div>
        ) : (
          <div className="space-y-6 w-full">
            <AnimatePresence initial={false}>
              {displayMessages.map((msg, idx) => {
                const { cleanText, questions: suggestedQuestions } = extractFollowUpQuestions(msg.content);
                const autoLinkedText = autoLinkLegalCitations(cleanText);
                const isDraft = msg.role === 'ai' && isOfficialLegalDraft(cleanText);

                return (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 group ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                  >
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border shadow-sm ${
                        msg.role === 'ai'
                          ? isDraft
                            ? 'bg-emerald-600 text-white border-emerald-600 shadow-emerald-500/20'
                            : 'bg-primary-start text-white border-primary-start'
                          : 'bg-surface border-main text-text-secondary'
                      }`}
                    >
                      {msg.role === 'ai' ? (
                        isDraft ? <FileText size={16} /> : <BrainCircuit size={16} />
                      ) : (
                        <User size={16} />
                      )}
                    </div>

                    {/* DUAL-MODE CONTAINER */}
                    {isDraft ? (
                      /* 🏛️ REAL A4 LEGAL PAPER CANVAS (EXACT MATCH ME MODULIN HARTIMI) */
                      <div className="w-full max-w-[21cm] my-2">
                        <div className="bg-white text-black p-8 sm:p-14 shadow-[0_0_40px_rgba(0,0,0,0.12)] rounded-sm min-h-[29.7cm] border border-gray-200 font-serif leading-relaxed text-[11pt]">
                          
                          {/* Header Bar */}
                          <div className="flex justify-between items-center border-b border-gray-200 pb-3 mb-8 font-sans">
                            <span className="text-[10px] font-black uppercase tracking-widest text-gray-500 flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                              DOKUMENT ZYRTAR GJYQËSOR (A4 CANVAS)
                            </span>
                            <MessageCopyButton text={msg.content} />
                          </div>

                          {/* Native Draft Result Renderer */}
                          <div className="text-black prose-p:text-black prose-headings:text-black prose-strong:text-black">
                            <DraftResultRenderer text={autoLinkedText} t={t} />
                          </div>
                        </div>

                        {/* Optional Feedback Buttons */}
                        {activeContextId !== 'general' && (
                          <div className="mt-3 flex justify-end">
                            <FeedbackButtons
                              messageIndex={idx}
                              caseId={activeContextId}
                              onFeedback={(i) => handleFeedback(i)}
                              disabled={feedbackGiven.has(idx)}
                            />
                          </div>
                        )}
                      </div>
                    ) : (
                      /* 💬 STANDARD CONVERSATIONAL CHAT BUBBLE */
                      <div
                        className={`relative max-w-[88%] rounded-xl py-3 px-4 text-xs sm:text-sm shadow-sm border border-main bg-surface text-text-primary ${
                          msg.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'
                        }`}
                      >
                        {msg.content && <MessageCopyButton text={msg.content} />}

                        <div className="markdown-content select-text prose prose-slate dark:prose-invert max-w-none prose-sm leading-relaxed text-text-primary">
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                            {autoLinkedText}
                          </ReactMarkdown>
                        </div>

                        {/* Suggested Questions (Clickable Action Buttons) */}
                        {msg.role === 'ai' &&
                          idx === displayMessages.length - 1 &&
                          !isSendingMessage &&
                          suggestedQuestions.length > 0 && (
                            <div className="flex flex-col gap-2 mt-4 pt-4 border-t border-main/50 animate-in fade-in slide-in-from-bottom-2 duration-300">
                              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                                <Sparkles size={12} className="text-primary-start animate-pulse" />
                                {t('chat.suggestedFollowUps', 'Pyetje Sugjeruese')}
                              </span>
                              <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                                {suggestedQuestions.map((q, qIdx) => (
                                  <button
                                    key={qIdx}
                                    type="button"
                                    onClick={() => sendMessage(q)}
                                    className="px-3.5 py-2.5 bg-surface hover:bg-hover border border-main hover:border-primary-start/50 text-text-secondary hover:text-text-primary rounded-xl text-xs font-bold text-left transition-all hover-lift focus:outline-none shadow-sm flex items-center gap-2 cursor-pointer"
                                  >
                                    <span className="w-2 h-2 bg-primary-start rounded-full shrink-0" />
                                    <span>{q}</span>
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}

                        {msg.role === 'ai' &&
                          activeContextId !== 'general' &&
                          typeof msg.content === 'string' &&
                          msg.content.trim() !== '' &&
                          !msg.content.startsWith('[Gabim Teknik') && (
                            <FeedbackButtons
                              messageIndex={idx}
                              caseId={activeContextId}
                              onFeedback={(i) => handleFeedback(i)}
                              disabled={feedbackGiven.has(idx)}
                            />
                          )}

                        {msg.role === 'ai' &&
                          typeof msg.content === 'string' &&
                          msg.content.startsWith('[Gabim Teknik') && (
                            <button
                              type="button"
                              onClick={handleRetry}
                              className="mt-3 px-3 py-2 bg-danger-start/10 text-danger-start border border-danger-start/20 rounded-lg text-[10px] font-semibold uppercase flex items-center gap-1.5 hover:bg-danger-start/20 transition-all hover-lift focus:outline-none cursor-pointer"
                            >
                              <RefreshCw size={12} /> {t('chat.retry', 'Riprovo')}
                            </button>
                          )}
                      </div>
                    )}
                  </motion.div>
                );
              })}

              {/* ANIMATED THINKING BUBBLE */}
              {isAwaitingFirstToken && (
                <motion.div 
                  key="thinking" 
                  initial={{ opacity: 0, y: 5 }} 
                  animate={{ opacity: 1, y: 0 }} 
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="flex items-start gap-3"
                >
                  <div className="w-8 h-8 rounded-lg bg-primary-start text-white flex items-center justify-center shadow-sm shrink-0 border border-primary-start">
                    <BrainCircuit size={16} className="animate-pulse" />
                  </div>
                  <div className="bg-surface border border-main rounded-xl rounded-tl-sm px-4 py-2.5 shadow-sm flex items-center gap-2.5">
                    <span className="text-xs font-bold text-primary-start tracking-wide">
                      Sokrati duke menduar
                    </span>
                    <div className="flex items-center gap-1 ml-0.5">
                      <motion.span
                        animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }}
                        transition={{ repeat: Infinity, duration: 0.85, ease: 'easeInOut', delay: 0 }}
                        className="w-1.5 h-1.5 rounded-full bg-primary-start inline-block"
                      />
                      <motion.span
                        animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }}
                        transition={{ repeat: Infinity, duration: 0.85, ease: 'easeInOut', delay: 0.2 }}
                        className="w-1.5 h-1.5 rounded-full bg-primary-start inline-block"
                      />
                      <motion.span
                        animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }}
                        transition={{ repeat: Infinity, duration: 0.85, ease: 'easeInOut', delay: 0.4 }}
                        className="w-1.5 h-1.5 rounded-full bg-primary-start inline-block"
                      />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="p-3 sm:p-4 bg-surface shrink-0 z-20">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="max-w-5xl mx-auto"
        >
          <div className="flex items-end gap-2 bg-canvas border border-main rounded-xl p-2 transition-all focus-within:ring-2 focus-within:ring-primary-start/20 focus-within:border-primary-start/50 shadow-sm">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('chatPanel.inputPlaceholder', 'Shkruaj mesazhin tuaj këtu...')}
              className="flex-1 p-2 bg-transparent text-xs sm:text-sm leading-relaxed text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[40px] max-h-[200px] border-0 outline-none ring-0 scrollbar-none [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
              rows={1}
            />
            <button
              type="submit"
              disabled={!input.trim() || isSendingMessage}
              className="h-9 w-9 flex items-center justify-center bg-primary-start text-white rounded-lg shadow-md shadow-primary-start/15 hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 mb-0.5 focus:outline-none hover-lift cursor-pointer"
            >
              <Send size={15} className="ml-0.5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;