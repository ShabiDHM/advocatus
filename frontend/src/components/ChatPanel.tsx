// FILE: frontend/src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V52.0 (ISOLATED ANALYSIS POPUP TRIGGER)

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, BrainCircuit, User, RefreshCw, Sparkles, 
  Scale, Swords, BookOpen, HelpCircle, Coins, ArrowRight, FileSearch
} from 'lucide-react';
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
  onOpenCaseAnalysis?: () => void;
}

const formatUserDisplayMessage = (content: string) => {
  if (content.startsWith('[DIREKTIVË FORENZIKE') || content.startsWith('[DIREKTIVË E FORENZIKËS')) {
    const docMatch = content.match(/"([^"]+)"/);
    const docName = docMatch ? docMatch[1] : 'Dokumentit të Zgjedhur';
    return (
      <div className="flex items-center gap-2 font-bold text-xs sm:text-sm text-text-primary">
        <Scale size={15} className="text-primary-start shrink-0" />
        <span>Forenzika Ligjore:</span>
        <span className="text-primary-start italic truncate">{docName}</span>
      </div>
    );
  }

  if (content.toUpperCase().includes('ANALIZO RASTIN')) {
    return (
      <div className="flex items-center gap-2 font-bold text-xs sm:text-sm text-text-primary">
        <FileSearch size={15} className="text-primary-start shrink-0" />
        <span>Analizo Rastin — Raporti i Plotë Forenzik</span>
      </div>
    );
  }

  if (content.includes('shtyllat strategjike të kërkesëpadisë') || content.includes('shtyllat kryesore ku mbështetet')) {
    return (
      <div className="flex items-center gap-2 font-bold text-xs sm:text-sm text-text-primary">
        <Swords size={15} className="text-purple-500 shrink-0" />
        <span>Strategjia dhe Matrica e Provave</span>
        <span className="text-text-muted text-[10px] uppercase font-mono">(E gjithë Lënda)</span>
      </div>
    );
  }

  if (content.includes('nxirr bazën e plotë ligjore') || content.includes('baza statutore dhe jurisprudenca')) {
    return (
      <div className="flex items-center gap-2 font-bold text-xs sm:text-sm text-text-primary">
        <BookOpen size={15} className="text-blue-500 shrink-0" />
        <span>Baza Statutare dhe Jurisprudenca e Gjykatës Supreme</span>
      </div>
    );
  }

  if (content.includes('pyetësorin taktik të ballafaqimit') || content.includes('pyetjet taktike për të ballafaquar')) {
    return (
      <div className="flex items-center gap-2 font-bold text-xs sm:text-sm text-text-primary">
        <HelpCircle size={15} className="text-amber-500 shrink-0" />
        <span>Pyetësori Taktik për Seancë (Cross-Examination)</span>
      </div>
    );
  }

  if (content.includes('llogarit dëmet materiale e jomateriale') || content.includes('kamatën ligjore vonesore 8%')) {
    return (
      <div className="flex items-center gap-2 font-bold text-xs sm:text-sm text-text-primary">
        <Coins size={15} className="text-emerald-500 shrink-0" />
        <span>Llogaritja e Dëmit LMD (8%) & Masat Emergjente</span>
      </div>
    );
  }

  return content;
};

const resolveSuggestionCardUI = (query: string) => {
  const q = query.toLowerCase();

  if (q.includes('analizo rastin') || q.includes('raport i plotë')) {
    return {
      title: 'Analizo Rastin',
      desc: 'Raporti i plotë forenzik — 10 seksione me shkeljet, provat, nenet, planin e veprimit.',
      icon: <FileSearch size={16} className="text-primary-start shrink-0 mt-0.5" />
    };
  }

  if (q.includes('audito') || q.includes('kontroll forenzik')) {
    return {
      title: 'Audito Dokumentin',
      desc: 'Kontrolli forenzik i një dokumenti specifik.',
      icon: <Scale size={16} className="text-blue-500 shrink-0 mt-0.5" />
    };
  }

  if (q.includes('nxirr bazën e plotë ligjore') || q.includes('baza statutore')) {
    return {
      title: 'Baza Statutare dhe Jurisprudenca',
      desc: 'Auditimi i neneve, lapsuseve dhe precedentëve të Gjykatës Supreme.',
      icon: <BookOpen size={16} className="text-blue-500 shrink-0 mt-0.5" />
    };
  }

  return {
    title: 'Vazhdo me Analizën',
    desc: query,
    icon: <Sparkles size={16} className="text-primary-start shrink-0 mt-0.5" />
  };
};

const ChatPanel: React.FC<ChatPanelProps> = (props) => {
  const {
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
    userSalutation = 'Avokat',
    clientPosition = 'DEFENDANT',
    isPro = true,
    onOpenCaseAnalysis,
  } = props;

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
        isPro={isPro}
        onAnalyzeCase={() => {
          if (onOpenCaseAnalysis) {
            onOpenCaseAnalysis();
          } else {
            sendMessage("ANALIZO RASTIN");
          }
        }}
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
          <div className="space-y-4 w-full">
            <AnimatePresence initial={false}>
              {displayMessages.map((msg, idx) => {
                const { cleanText, questions: suggestedQuestions } = extractFollowUpQuestions(msg.content);
                const autoLinkedText = autoLinkLegalCitations(cleanText);

                const isSpecialCommand = msg.role === 'user' && (
                  msg.content.startsWith('[DIREKTIVË') || 
                  msg.content.toUpperCase().includes('ANALIZO RASTIN') ||
                  msg.content.includes('shtyllat strategjike') ||
                  msg.content.includes('nxirr bazën e plotë ligjore') ||
                  msg.content.includes('pyetësorin taktik') ||
                  msg.content.includes('llogarit dëmet materiale')
                );

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
                          : isSpecialCommand
                            ? 'bg-primary-start/10 border-primary-start/20 text-primary-start'
                            : 'bg-surface border-main text-text-secondary'
                      }`}
                    >
                      {msg.role === 'ai' ? <BrainCircuit size={16} /> : isSpecialCommand ? <FileSearch size={16} /> : <User size={16} />}
                    </div>

                    <div
                      className={`relative max-w-[88%] rounded-xl py-3 px-4 text-xs sm:text-sm shadow-sm border border-main bg-surface text-text-primary ${
                        msg.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'
                      }`}
                    >
                      {msg.content && !isSpecialCommand && <MessageCopyButton text={msg.content} />}

                      {msg.role === 'user' ? (
                        formatUserDisplayMessage(msg.content)
                      ) : (
                        <div className="markdown-content select-text prose prose-slate dark:prose-invert max-w-none prose-sm leading-relaxed text-text-primary">
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                            {autoLinkedText}
                          </ReactMarkdown>
                        </div>
                      )}

                      {msg.role === 'ai' &&
                        idx === displayMessages.length - 1 &&
                        !isSendingMessage &&
                        suggestedQuestions.length > 0 && (
                          <div className="flex flex-col gap-2.5 mt-5 pt-4 border-t border-main/50 animate-in fade-in slide-in-from-bottom-2 duration-300">
                            <span className="text-[10px] font-black text-text-muted uppercase tracking-widest flex items-center gap-1.5 ml-1">
                              <Sparkles size={12} className="text-primary-start animate-pulse" />
                              {t('chat.suggestedFollowUps', 'Hapat e Ardhshëm të Sugjeruar')}
                            </span>
                            
                            <div className="flex flex-col gap-2 w-full">
                              {suggestedQuestions.map((q, qIdx) => {
                                const cardInfo = resolveSuggestionCardUI(q);
                                return (
                                  <button
                                    key={qIdx}
                                    type="button"
                                    onClick={() => sendMessage(q)}
                                    className="w-full p-3 sm:p-3.5 bg-surface hover:bg-hover border border-main hover:border-primary-start/50 text-text-secondary hover:text-text-primary rounded-2xl text-left transition-all hover-lift focus:outline-none shadow-sm flex items-start justify-between gap-3 group cursor-pointer"
                                  >
                                    <div className="flex items-start gap-2.5 min-w-0">
                                      {cardInfo.icon}
                                      <div className="min-w-0">
                                        <p className="font-bold text-xs text-text-primary group-hover:text-primary-start transition-colors">
                                          {cardInfo.title}
                                        </p>
                                        <p className="text-[11px] text-text-muted mt-0.5 line-clamp-1 leading-snug">
                                          {cardInfo.desc}
                                        </p>
                                      </div>
                                    </div>
                                    <ArrowRight size={14} className="text-text-muted group-hover:text-primary-start group-hover:translate-x-0.5 transition-all shrink-0 mt-1" />
                                  </button>
                                );
                              })}
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
                      <motion.span animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }} transition={{ repeat: Infinity, duration: 0.85, ease: 'easeInOut', delay: 0 }} className="w-1.5 h-1.5 rounded-full bg-primary-start inline-block" />
                      <motion.span animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }} transition={{ repeat: Infinity, duration: 0.85, ease: 'easeInOut', delay: 0.2 }} className="w-1.5 h-1.5 rounded-full bg-primary-start inline-block" />
                      <motion.span animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }} transition={{ repeat: Infinity, duration: 0.85, ease: 'easeInOut', delay: 0.4 }} className="w-1.5 h-1.5 rounded-full bg-primary-start inline-block" />
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