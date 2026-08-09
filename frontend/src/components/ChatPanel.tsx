// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V33.0 (SINGLE FLUID STREAMING & SMART THINKING BUBBLE)

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, BrainCircuit, User, RefreshCw, Sparkles } from 'lucide-react';
import { ChatMessage } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { autoLinkLegalCitations, extractFollowUpQuestions } from '../utils/chatHelpers';
import { ThinkingDots } from './chat/ThinkingDots';
import { MessageCopyButton } from './chat/MessageCopyButton';
import { FeedbackButtons } from './chat/FeedbackButtons';
import { buildMarkdownComponents } from './chat/MarkdownRenderer';
import { CommandPaletteGrid } from './chat/CommandPaletteGrid';
import { ChatHeader } from './chat/ChatHeader';

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
  selectedDocumentCount?: number;
  userSalutation?: string;
  clientPosition?: 'DEFENDANT' | 'PLAINTIFF';
}

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
  selectedDocumentCount = 0,
  userSalutation = 'Avokat',
  clientPosition = 'DEFENDANT',
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
    onSendMessage(text, mode, reasoningMode, 'automatic', [], 'ks');
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

  // Filter out empty placeholder AI messages while sending so duplicate brain icons never show
  const displayMessages = safeMessages.filter(
    (m) => m && typeof m.content === 'string' && m.content.trim() !== ''
  );

  // Determine if AI is waiting for its first token to arrive
  const isAwaitingFirstToken =
    isSendingMessage &&
    (displayMessages.length === 0 || displayMessages[displayMessages.length - 1].role === 'user');

  return (
    <div className={`flex flex-col glass-panel overflow-hidden h-full w-full border border-main bg-canvas shadow-sm ${className}`}>
      <ChatHeader
        connectionStatus={connectionStatus}
        activeContextId={activeContextId}
        selectedDocumentCount={selectedDocumentCount}
        onClearChat={onClearChat}
        onExportChat={onExportChat}
        t={t}
      />

      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-canvas/10 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden shadow-[inset_0_1px_8px_rgba(0,0,0,0.01)] border-b border-main flex flex-col justify-start">
        <AnimatePresence initial={false}>
          {displayMessages.length === 0 && !isSendingMessage && (
            <CommandPaletteGrid userSalutation={userSalutation} clientPosition={clientPosition} onSendMessage={sendMessage} />
          )}

          {displayMessages.map((msg, idx) => {
            const { cleanText, questions: suggestedQuestions } = extractFollowUpQuestions(msg.content);
            const autoLinkedText = autoLinkLegalCitations(cleanText);

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
                      ? 'bg-primary-start text-white border-primary-start'
                      : 'bg-surface border-main text-text-secondary'
                  }`}
                >
                  {msg.role === 'ai' ? <BrainCircuit size={16} /> : <User size={16} />}
                </div>

                <div
                  className={`relative max-w-[88%] rounded-xl py-3 px-4 text-xs sm:text-sm shadow-sm border border-main bg-surface text-text-primary ${
                    msg.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'
                  }`}
                >
                  {msg.content && <MessageCopyButton text={msg.content} />}

                  <div className="markdown-content select-text prose prose-slate max-w-none prose-sm leading-relaxed">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {autoLinkedText}
                    </ReactMarkdown>
                  </div>

                  {msg.role === 'ai' &&
                    idx === displayMessages.length - 1 &&
                    !isSendingMessage &&
                    suggestedQuestions.length > 0 && (
                      <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-main animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider flex items-center gap-1">
                          <Sparkles size={11} className="text-primary-start animate-pulse" />{' '}
                          {t('chat.suggestedFollowUps', 'Pyetje Sugjeruese')}
                        </span>
                        <div className="flex flex-col sm:flex-row flex-wrap gap-2">
                          {suggestedQuestions.map((q, qIdx) => (
                            <button
                              key={qIdx}
                              type="button"
                              onClick={() => sendMessage(q)}
                              className="px-3 py-2 bg-surface border border-main hover:border-primary-start/40 text-text-secondary hover:text-text-primary rounded-xl text-xs font-semibold text-left transition-all hover-lift focus:outline-none shadow-sm flex items-center gap-1.5"
                            >
                              <span className="w-1.5 h-1.5 bg-primary-start/40 rounded-full shrink-0" />
                              {q}
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
              </motion.div>
            );
          })}

          {/* THINKING BUBBLE - Shows ONLY before the first AI token arrives */}
          {isAwaitingFirstToken && (
            <motion.div key="thinking" initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary-start text-white flex items-center justify-center shadow-sm shrink-0 border border-primary-start">
                <BrainCircuit size={16} className="animate-pulse" />
              </div>
              <div className="bg-surface border border-main rounded-xl rounded-tl-sm px-4 py-2.5 shadow-sm flex items-center gap-2">
                <span className="text-xs font-bold text-primary-start tracking-wide">
                  Sokrati duke menduar
                </span>
                <ThinkingDots />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />
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