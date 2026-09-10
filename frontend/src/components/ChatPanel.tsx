// FILE: src/components/ChatPanel.tsx
// PHOENIX PROTOCOL - CHAT PANEL V90.0 (ZERO-LAG MEMOIZED ENGINE + ATTACHMENT PIPELINE)
// ZERO TS WARNINGS • OFFICIAL JURISTI AI BRANDING • 100% COMPLETE CODE • ULTRA 60FPS TYPING

import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, BrainCircuit, User, RefreshCw, Sparkles, 
  Scale, Swords, BookOpen, HelpCircle, Coins, ArrowRight,
  FileText, Paperclip, X, Loader2, Volume2, Table as TableIcon, Image as ImageIcon
} from 'lucide-react';
import { ChatMessage, Document } from '../data/types';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../services/api';
import { autoLinkLegalCitations, extractFollowUpQuestions } from '../utils/chatHelpers';
import { MessageCopyButton } from './chat/MessageCopyButton';
import { FeedbackButtons } from './chat/FeedbackButtons';
import { buildMarkdownComponents } from './chat/MarkdownRenderer';
import { CommandPaletteGrid } from './chat/CommandPaletteGrid';
import { ChatHeader } from './chat/ChatHeader';
import { ThinkingDots } from './chat/ThinkingDots';

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
  onAnalyzeDocument?: () => void;
  selectedDocName?: string;
  isAnalyzingCase?: boolean;
  isAnalysisDirty?: boolean;
  hasExistingAnalysis?: boolean;
}

type FileCategory = 'audio' | 'spreadsheet' | 'image' | 'document';

const detectFileCategory = (file: File): FileCategory => {
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();
  if (type.startsWith('audio/') || /\.(mp3|wav|m4a|ogg|aac|flac)$/i.test(name)) {
    return 'audio';
  }
  if (type.startsWith('image/') || /\.(jpg|jpeg|png|webp|bmp)$/i.test(name)) {
    return 'image';
  }
  if (/\.(xlsx|xls|csv)$/i.test(name) || type.includes('spreadsheet') || type.includes('excel') || type.includes('csv')) {
    return 'spreadsheet';
  }
  return 'document';
};

const isThinkingPlaceholder = (text?: string): boolean => {
  if (!text) return true;
  const clean = text.trim();
  return (
    clean === '' || 
    clean === '...' || 
    clean === '…' || 
    clean.toLowerCase().includes('duke menduar')
  );
};

const formatUserDisplayMessage = (content: string) => {
  if (content.startsWith('[DIREKTIVË FORENZIKE') || content.startsWith('[DIREKTIVË E FORENZIKËS')) {
    const docMatch = content.match(/"([^"]+)"/);
    const rawDocName = docMatch ? docMatch[1] : 'Dokumenti';
    const cleanDocName = rawDocName.replace(/\.[^/.]+$/, "");
    
    return (
      <div className="inline-flex items-center gap-2 font-bold text-xs py-0.5">
        <span className="p-1 rounded-md bg-primary-start/15 text-primary-start border border-primary-start/30 flex items-center justify-center">
          <Scale size={13} />
        </span>
        <span className="uppercase tracking-wider text-[11px] font-black text-text-primary">
          Auditimi Forenzik
        </span>
        <span className="text-text-muted">•</span>
        <span className="text-text-secondary font-medium max-w-[180px] sm:max-w-[280px] truncate text-[11px]">
          {cleanDocName}
        </span>
      </div>
    );
  }

  if (content.includes('shtyllat strategjike') || content.includes('matrica e provave')) {
    return (
      <div className="inline-flex items-center gap-2 font-bold text-xs py-0.5">
        <span className="p-1 rounded-md bg-purple-500/15 text-purple-500 border border-purple-500/30 flex items-center justify-center">
          <Swords size={13} />
        </span>
        <span className="text-[11px] font-bold text-text-primary">Strategjia & Matrica e Provave</span>
      </div>
    );
  }

  if (content.includes('nxirr bazën e plotë ligjore') || content.includes('baza statutore')) {
    return (
      <div className="inline-flex items-center gap-2 font-bold text-xs py-0.5">
        <span className="p-1 rounded-md bg-blue-500/15 text-blue-500 border border-blue-500/30 flex items-center justify-center">
          <BookOpen size={13} />
        </span>
        <span className="text-[11px] font-bold text-text-primary">Baza Statutore & Jurisprudenca</span>
      </div>
    );
  }

  if (content.includes('pyetësorin taktik')) {
    return (
      <div className="inline-flex items-center gap-2 font-bold text-xs py-0.5">
        <span className="p-1 rounded-md bg-amber-500/15 text-amber-500 border border-amber-500/30 flex items-center justify-center">
          <HelpCircle size={13} />
        </span>
        <span className="text-[11px] font-bold text-text-primary">Pyetësori Taktik për Seancë</span>
      </div>
    );
  }

  if (content.includes('llogarit dëmet') || content.includes('kamatën ligjore')) {
    return (
      <div className="inline-flex items-center gap-2 font-bold text-xs py-0.5">
        <span className="p-1 rounded-md bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 flex items-center justify-center">
          <Coins size={13} />
        </span>
        <span className="text-[11px] font-bold text-text-primary">Llogaritja e Dëmit & Kamata (LMD)</span>
      </div>
    );
  }

  return content;
};

const resolveSuggestionCardUI = (query: string) => {
  const q = query.toLowerCase();

  if (q.includes('harto') || q.includes('kallëzim') || q.includes('padi') || q.includes('ankesë')) {
    return {
      title: 'Harto Shkresën / Mjetin Ligjor',
      desc: query,
      icon: <FileText size={16} className="text-primary-start shrink-0 mt-0.5" />
    };
  }

  if (q.includes('pyetësor') || q.includes('pyetje') || q.includes('seancë')) {
    return {
      title: 'Pyetësori Taktik për Seancë',
      desc: query,
      icon: <HelpCircle size={16} className="text-amber-500 shrink-0 mt-0.5" />
    };
  }

  if (q.includes('contra legem') || q.includes('matrica') || q.includes('audito') || q.includes('ndarje')) {
    return {
      title: 'Veprim Procedural & Ndarje',
      desc: query,
      icon: <Scale size={16} className="text-blue-500 shrink-0 mt-0.5" />
    };
  }

  if (q.includes('dëm') || q.includes('kamat') || q.includes('shum')) {
    return {
      title: 'Llogaritja e Dëmit & Kamata',
      desc: query,
      icon: <Coins size={16} className="text-emerald-500 shrink-0 mt-0.5" />
    };
  }

  return {
    title: 'Hapi i Sugjeruar',
    desc: query,
    icon: <Sparkles size={16} className="text-primary-start shrink-0 mt-0.5" />
  };
};

// ============================================================================
// KOMPONENTI I MEMOIZUAR I MESAZHIT (ZERO-LAG TYPING)
// ============================================================================
interface ClientMessageBubbleProps {
  msg: ChatMessage;
  idx: number;
  isLastMessage: boolean;
  isSendingMessage: boolean;
  onSendMessage: (text: string) => void;
  onFeedback: (idx: number) => void;
  feedbackGiven: boolean;
  onRetry: () => void;
  activeContextId: string;
  markdownComponents: any;
  t: TFunction;
}

const ClientMessageBubble: React.FC<ClientMessageBubbleProps> = React.memo(({
  msg,
  idx,
  isLastMessage,
  isSendingMessage,
  onSendMessage,
  onFeedback,
  feedbackGiven,
  onRetry,
  activeContextId,
  markdownComponents,
  t
}) => {
  const { cleanText, questions: suggestedQuestions } = useMemo(
    () => extractFollowUpQuestions(msg.content),
    [msg.content]
  );

  const autoLinkedText = useMemo(
    () => autoLinkLegalCitations(cleanText),
    [cleanText]
  );

  const isSpecialCommand = msg.role === 'user' && (
    msg.content.startsWith('[DIREKTIVË') || 
    msg.content.includes('shtyllat strategjike') ||
    msg.content.includes('nxirr bazën e plotë ligjore') ||
    msg.content.includes('pyetësorin taktik') ||
    msg.content.includes('llogarit dëmet materiale')
  );

  const isAiPlaceholder = msg.role === 'ai' && isThinkingPlaceholder(msg.content);

  return (
    <motion.div
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
        {msg.role === 'ai' ? <BrainCircuit size={16} /> : isSpecialCommand ? <Scale size={16} /> : <User size={16} />}
      </div>

      <div
        className={`relative max-w-[85%] rounded-xl py-2.5 px-3.5 text-xs sm:text-sm shadow-sm border border-main bg-surface text-text-primary ${
          msg.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'
        }`}
      >
        {msg.content && !isSpecialCommand && !isAiPlaceholder && <MessageCopyButton text={msg.content} />}

        {msg.role === 'user' ? (
          formatUserDisplayMessage(msg.content)
        ) : isAiPlaceholder ? (
          <div className="flex items-center gap-2 py-0.5">
            <span className="text-xs font-bold text-primary-start tracking-wide">
              Juristi AI duke menduar
            </span>
            <ThinkingDots />
          </div>
        ) : (
          <div className="markdown-content select-text prose prose-slate dark:prose-invert max-w-none prose-sm leading-relaxed text-text-primary">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {autoLinkedText}
            </ReactMarkdown>
          </div>
        )}

        {msg.role === 'ai' &&
          !isAiPlaceholder &&
          isLastMessage &&
          !isSendingMessage &&
          suggestedQuestions.length > 0 && (
            <div className="flex flex-col gap-2.5 mt-5 pt-4 border-t border-main/50 animate-in fade-in slide-in-from-bottom-2 duration-300">
              <span className="text-[10px] font-black text-text-muted uppercase tracking-widest flex items-center gap-1.5 ml-1">
                <Sparkles size={12} className="text-primary-start animate-pulse" />
                {t('chat.suggestedFollowUps', 'Hapat e Ardhshëm të Sugjeruar nga Juristi AI')}
              </span>
              
              <div className="flex flex-col gap-2 w-full">
                {suggestedQuestions.map((q, qIdx) => {
                  const cardInfo = resolveSuggestionCardUI(q);
                  return (
                    <button
                      key={qIdx}
                      type="button"
                      onClick={() => onSendMessage(q)}
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
          !isAiPlaceholder &&
          activeContextId !== 'general' &&
          typeof msg.content === 'string' &&
          msg.content.trim() !== '' &&
          !msg.content.startsWith('[Gabim Teknik') && (
            <FeedbackButtons
              messageIndex={idx}
              caseId={activeContextId}
              onFeedback={(i) => onFeedback(i)}
              disabled={feedbackGiven}
            />
          )}

        {msg.role === 'ai' &&
          typeof msg.content === 'string' &&
          msg.content.startsWith('[Gabim Teknik') && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 px-3 py-2 bg-danger-start/10 text-danger-start border border-danger-start/20 rounded-lg text-[10px] font-semibold uppercase flex items-center gap-1.5 hover:bg-danger-start/20 transition-all hover-lift focus:outline-none cursor-pointer"
            >
              <RefreshCw size={12} /> {t('chat.retry', 'Riprovo')}
            </button>
          )}
      </div>
    </motion.div>
  );
});

ClientMessageBubble.displayName = 'ClientMessageBubble';

// ============================================================================
// KOMPONENTI KRYESOR CHAT PANEL
// ============================================================================
export const ChatPanel: React.FC<ChatPanelProps> = (props) => {
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
    onAnalyzeDocument,
    selectedDocName,
    isAnalyzingCase = false,
    isAnalysisDirty = false,
    hasExistingAnalysis = false,
  } = props;

  const [input, setInput] = useState('');
  const [reasoningMode] = useState<ReasoningMode>('DEEP');
  const [feedbackGiven, setFeedbackGiven] = useState<Set<number>>(new Set());
  const [lastUserMessage, setLastUserMessage] = useState<string>('');

  // Gjendja e bashkëngjitjes së skedarit me 📎
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [isUploadingAttachment, setIsUploadingAttachment] = useState<boolean>(false);
  const [uploadStatusText, setUploadStatusText] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSendingMessage]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInput(val);
    const target = e.target;
    target.style.height = 'auto';
    target.style.height = `${Math.min(target.scrollHeight, 250)}px`;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAttachedFile(file);
    }
    if (e.target) {
      e.target.value = '';
    }
  };

  const handleRemoveAttachedFile = () => {
    setAttachedFile(null);
  };

  const sendMessage = async (text: string) => {
    const cleanText = text.trim();
    if ((!cleanText && !attachedFile) || isSendingMessage || isUploadingAttachment) return;

    let textToSend = cleanText;
    let fileNotice = '';

    // Nëse kemi bashkëngjitur skedar me 📎 dhe jemi brenda një lënde
    if (attachedFile && activeContextId && activeContextId !== 'general') {
      setIsUploadingAttachment(true);
      setUploadStatusText(`Duke ngarkuar dhe indeksuar: ${attachedFile.name}...`);
      try {
        await apiService.uploadDocument(activeContextId, attachedFile, () => {});
        fileNotice = `\n\n📎 [DOKUMENT I BASHKANGJITUR: ${attachedFile.name}]`;
        if (!textToSend) {
          textToSend = `Ju lutem analizoni këtë shkresë të sapo ngarkuar: ${attachedFile.name}. Nxirrni faktet kyçe dhe bazën ligjore.`;
        }
      } catch (uploadErr: any) {
        console.error("Dështoi ngarkimi i skedarit në chat:", uploadErr);
        alert(`Dështoi ngarkimi i skedarit: ${uploadErr?.response?.data?.detail || uploadErr?.message || 'Gabim gjatë ngarkimit'}`);
        setIsUploadingAttachment(false);
        setUploadStatusText('');
        return;
      } finally {
        setIsUploadingAttachment(false);
        setUploadStatusText('');
        setAttachedFile(null);
      }
    }

    const fullMessage = `${textToSend}${fileNotice}`;
    const mode = activeContextId === 'general' ? 'general' : 'document';
    setLastUserMessage(fullMessage);
    onSendMessage(fullMessage, mode, reasoningMode, 'automatic', selectedDocumentIds, 'ks');
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleFeedback = useCallback((index: number) => {
    setFeedbackGiven((prev) => new Set(prev).add(index));
  }, []);

  const handleRetry = useCallback(() => {
    if (lastUserMessage) sendMessage(lastUserMessage);
  }, [lastUserMessage]);

  const safeMessages = Array.isArray(messages) ? messages : [];

  const displayMessages = useMemo(() => {
    return safeMessages.filter(
      (m) => m && typeof m.content === 'string' && m.content.trim() !== ''
    );
  }, [safeMessages]);

  const lastMessage = safeMessages.length > 0 ? safeMessages[safeMessages.length - 1] : null;
  const isAiCurrentlyStreaming = 
    lastMessage?.role === 'ai' && 
    typeof lastMessage.content === 'string' && 
    !isThinkingPlaceholder(lastMessage.content);

  const isAwaitingFirstToken = isSendingMessage && !isAiCurrentlyStreaming;

  const renderAttachedBadge = () => {
    if (!attachedFile) return null;
    const cat = detectFileCategory(attachedFile);

    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 px-3 py-1.5 mb-2 bg-primary-start/15 border border-primary-start/40 rounded-xl text-xs text-text-primary w-fit shadow-xs"
      >
        {cat === 'audio' && <Volume2 size={14} className="text-amber-400 shrink-0" />}
        {cat === 'spreadsheet' && <TableIcon size={14} className="text-emerald-400 shrink-0" />}
        {cat === 'image' && <ImageIcon size={14} className="text-sky-400 shrink-0" />}
        {cat === 'document' && <FileText size={14} className="text-primary-start shrink-0" />}

        <span className="font-bold truncate max-w-[200px] sm:max-w-[300px] text-text-primary">
          {attachedFile.name}
        </span>
        <span className="text-[10px] text-text-muted font-mono uppercase">
          ({(attachedFile.size / 1024).toFixed(0)} KB)
        </span>
        <button
          type="button"
          onClick={handleRemoveAttachedFile}
          className="ml-1 p-0.5 text-text-muted hover:text-rose-500 hover:bg-rose-500/10 rounded-md transition-colors cursor-pointer"
          title="Hiq skedarin"
        >
          <X size={13} />
        </button>
      </motion.div>
    );
  };

  return (
    <div className={`flex flex-col glass-panel overflow-hidden h-full w-full border border-main bg-canvas shadow-sm ${className}`}>
      <ChatHeader
        connectionStatus={connectionStatus}
        activeContextId={activeContextId}
        onClearChat={onClearChat}
        onExportChat={onExportChat}
        t={t}
        isPro={isPro}
        onAnalyzeCase={onOpenCaseAnalysis}
        onAnalyzeDocument={onAnalyzeDocument}
        selectedDocName={selectedDocName}
        isAnalyzingCase={isAnalyzingCase}
        isAnalysisDirty={isAnalysisDirty}
        hasExistingAnalysis={hasExistingAnalysis}
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
              {displayMessages.map((msg, idx) => (
                <ClientMessageBubble
                  key={idx}
                  msg={msg}
                  idx={idx}
                  isLastMessage={idx === displayMessages.length - 1}
                  isSendingMessage={isSendingMessage}
                  onSendMessage={sendMessage}
                  onFeedback={handleFeedback}
                  feedbackGiven={feedbackGiven.has(idx)}
                  onRetry={handleRetry}
                  activeContextId={activeContextId}
                  markdownComponents={markdownComponents}
                  t={t}
                />
              ))}

              {isAwaitingFirstToken && !displayMessages.some(m => m.role === 'ai' && isThinkingPlaceholder(m.content)) && (
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
                  <div className="bg-surface border border-main rounded-xl rounded-tl-sm px-4 py-2.5 shadow-sm flex items-center gap-2">
                    <span className="text-xs font-bold text-primary-start tracking-wide">
                      Juristi AI duke menduar
                    </span>
                    <ThinkingDots />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* INPUT AREA */}
      <div className="p-3 sm:p-4 bg-surface shrink-0 z-20">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          className="max-w-5xl mx-auto"
        >
          {/* BADGE I SKEDARIT TË BASHKANGJITUR */}
          {renderAttachedBadge()}

          {/* INPUT I FSHEHUR PËR SKEDARIN */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".pdf,.docx,.doc,.txt,.xlsx,.xls,.csv,.mp3,.wav,.m4a,image/*"
            className="hidden"
          />

          <div className="flex items-end gap-2 bg-canvas border border-main rounded-xl p-2 transition-all focus-within:ring-2 focus-within:ring-primary-start/20 focus-within:border-primary-start/50 shadow-sm">
            {/* BUTONI PAPERCLIP 📎 */}
            {activeContextId !== 'general' && (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isSendingMessage || isUploadingAttachment}
                className={`p-2 rounded-lg transition-all cursor-pointer mb-0.5 shrink-0 ${
                  attachedFile
                    ? 'bg-primary-start text-white shadow-xs'
                    : 'text-text-muted hover:text-primary-start hover:bg-primary-start/10'
                }`}
                title="Bashkëngjit dokument në lëndë (.pdf, .docx, Excel, foto)"
              >
                <Paperclip size={16} />
              </button>
            )}

            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={
                isUploadingAttachment
                  ? uploadStatusText
                  : attachedFile
                  ? `Shtoni pyetje për ${attachedFile.name} (ose shtypni Dërgo)...`
                  : t('chatPanel.inputPlaceholder', 'Shkruaj mesazhin tuaj këtu...')
              }
              disabled={isUploadingAttachment}
              className="flex-1 p-2 bg-transparent text-xs sm:text-sm leading-relaxed text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[40px] max-h-[200px] border-0 outline-none ring-0 scrollbar-none [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden disabled:opacity-60"
              rows={1}
            />

            <button
              type="submit"
              disabled={(!input.trim() && !attachedFile) || isSendingMessage || isUploadingAttachment}
              className="h-9 w-9 flex items-center justify-center bg-primary-start text-white rounded-lg shadow-md shadow-primary-start/15 hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 mb-0.5 focus:outline-none hover-lift cursor-pointer"
            >
              {isSendingMessage || isUploadingAttachment ? (
                <Loader2 size={15} className="animate-spin text-white" />
              ) : (
                <Send size={15} className="ml-0.5" />
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChatPanel;