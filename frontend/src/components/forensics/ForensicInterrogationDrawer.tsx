// FILE: frontend/src/components/forensics/ForensicInterrogationDrawer.tsx
// PHOENIX PROTOCOL - STANDALONE FORENSIC INTERROGATION TERMINAL V5.3 (MOBILE 100DVH & TOUCH OPTIMIZED)
// 100% COMPLETE CODE • ZERO DUPLICATIONS • ZERO TS WARNINGS

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BrainCircuit, X, Send, Trash2, Copy, CheckCircle2, 
  Loader2, Swords, Scale, User, HelpCircle, ShieldAlert, Maximize2, Minimize2, ShieldCheck
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { forensicDeskService } from '../../services/forensicDeskService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

interface ForensicMessage {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: string;
  citationAudit?: {
    is_safe: boolean;
    precedents_found: string[];
    verified_precedents: string[];
    unverified_precedents: string[];
    articles_cited: string[];
  };
}

interface ForensicInterrogationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseNumber: string;
  clientName: string;
  chainOfCustodyHash?: string;
}

const QUICK_FORENSIC_COMMANDS = [
  {
    label: 'Zbardhja e Alibive & Kontradiktave',
    icon: Swords,
    prompt: 'Kryqëzo të gjitha provat materiale dhe dëshmitë në këtë dosje dhe më nxirr listën e plotë të të gjitha kontradiktave, alibive të rreme dhe datave të pasakta.'
  },
  {
    label: 'Pyetësor Taktik Kurth për Seancë',
    icon: HelpCircle,
    prompt: 'Më harto një pyetësor taktik të thellë me 7 pyetje kurth për të ballafaquar palën kundërshtare dhe zyrtarët në seancën e ardhshme gjyqësore.'
  },
  {
    label: 'Shkeljet e Nenit 182 LPK / KPK',
    icon: Scale,
    prompt: 'Analizo të gjitha procesverbalet dhe aktvendimet e administruara dhe më nxirr shkeljet thelbësore procedurale sipas Nenit 182 të LPK-së dhe Kodit Penal.'
  },
  {
    label: 'Kryqëzimi i Provave Mjekësore & QPS',
    icon: ShieldAlert,
    prompt: 'Kryqëzo raportin e testit toksikologjik dhe provat shkencore me raportet e QPS-së dhe deklaratat e ekspertëve psikiatrikë.'
  }
];

export const ForensicInterrogationDrawer: React.FC<ForensicInterrogationDrawerProps> = ({
  isOpen,
  onClose,
  caseId,
  caseNumber,
  clientName,
  chainOfCustodyHash,
}) => {
  const [messages, setMessages] = useState<ForensicMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  // Ngarkimi i historikut nga MongoDB sapo hapet dritarja
  const loadChatHistory = useCallback(async () => {
    if (!caseId) return;
    try {
      const rawList = await forensicDeskService.getChatHistory(caseId);
      if (Array.isArray(rawList)) {
        const mapped: ForensicMessage[] = rawList.map((m: any) => ({
          id: m._id || m.id || `msg-${Math.random()}`,
          role: m.role === 'assistant' || m.role === 'ai' ? 'ai' : 'user',
          content: m.content || '',
          timestamp: m.created_at || new Date().toISOString(),
          citationAudit: m.citation_audit
        }));
        setMessages(mapped);
      }
    } catch (err) {
      console.warn("Nuk u ngarkua dot historiku i bisedës nga MongoDB:", err);
    }
  }, [caseId]);

  useEffect(() => {
    if (isOpen && caseId) {
      loadChatHistory();
    }
  }, [isOpen, caseId, loadChatHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  // Dërgimi i pyetjes me streaming
  const handleSendMessage = async (textToSend: string) => {
    const cleanText = textToSend.trim();
    if (!cleanText || isProcessing || !caseId || isPurging) return;

    const userMsg: ForensicMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: cleanText,
      timestamp: new Date().toISOString()
    };

    const aiPlaceholderId = `ai_${Date.now()}`;
    const aiPlaceholder: ForensicMessage = {
      id: aiPlaceholderId,
      role: 'ai',
      content: '',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMsg, aiPlaceholder]);
    setInput('');
    setIsProcessing(true);

    try {
      const stream = await forensicDeskService.streamForensicChat(
        caseId,
        cleanText,
        `Lënda: ${caseNumber} - ${clientName}. Vula: ${chainOfCustodyHash || 'AKTIVE'}`
      );

      const reader = stream.getReader();
      const decoder = new TextDecoder('utf-8');
      let accumulated = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        accumulated += chunk;

        setMessages(prev => {
          const next = [...prev];
          const idx = next.findIndex(m => m.id === aiPlaceholderId);
          if (idx !== -1) {
            next[idx] = {
              ...next[idx],
              content: accumulated,
            };
          }
          return next;
        });
      }
    } catch (err: any) {
      console.error("Forensic Chat Error:", err);
      setMessages(prev => {
        const next = [...prev];
        const idx = next.findIndex(m => m.id === aiPlaceholderId);
        if (idx !== -1) {
          next[idx] = {
            ...next[idx],
            content: `[GABIM FORENZIK: ${err?.message || 'Lidhja me Claude Sonnet 4.6 dështoi.'}]`
          };
        }
        return next;
      });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClearConsole = async () => {
    if (messages.length === 0 || !caseId || isPurging) return;
    const confirmWipe = window.confirm(
      "A jeni i sigurt që dëshironi të asgjësoni plotësisht bisedën forenzike nga MongoDB Atlas (Total Cascade Wipeout)?"
    );
    if (!confirmWipe) return;

    setIsPurging(true);
    try {
      await forensicDeskService.clearChatHistory(caseId);
      setMessages([]);
    } catch (err: any) {
      console.error("Dështoi fshirja e bisedës nga serveri:", err);
      alert(err?.response?.data?.detail || "Dështoi fshirja e bisedës nga MongoDB.");
    } finally {
      setIsPurging(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(input);
    }
  };

  const handleCopyMessage = (msgId: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] select-none pointer-events-auto overflow-hidden">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/75 backdrop-blur-sm"
          />

          {/* Slide-over Drawer Panel (100dvh për Mobile Keyboard Friendly) */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 240 }}
            className={`absolute top-0 right-0 h-[100dvh] max-h-[100dvh] ${
              isFullscreen 
                ? 'w-full max-w-full' 
                : 'w-full sm:w-[580px] md:w-[680px] lg:w-[760px] max-w-full'
            } border-l border-main shadow-2xl flex flex-col bg-card transition-all duration-300 ease-in-out`}
            style={{ backgroundColor: 'var(--bg-card, #020617)' }}
          >
            {/* Top Header */}
            <div className="p-3 sm:p-4 border-b border-main bg-surface/90 shrink-0 flex items-center justify-between gap-2.5">
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl sm:rounded-2xl bg-gradient-to-br from-primary-start to-indigo-700 text-white flex items-center justify-center border border-primary-start/30 shadow-md shrink-0">
                  <BrainCircuit size={18} className="sm:w-5 sm:h-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <h3 className="text-xs sm:text-sm md:text-base font-black uppercase tracking-wider text-text-primary truncate">
                      Terminali Forenzik
                    </h3>
                    <span className="hidden xs:inline-flex px-1.5 py-0.5 rounded-full bg-primary-start/20 text-primary-start border border-primary-start/40 text-[9px] font-mono font-bold uppercase shrink-0">
                      Claude Sonnet 4.6
                    </span>
                  </div>
                  <p className="text-[10px] sm:text-xs text-text-muted truncate font-mono mt-0.5">
                    {caseNumber}: <span className="text-text-primary font-bold">{clientName}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                {/* Butoni i Koshit të Plehrave */}
                <button
                  type="button"
                  onClick={handleClearConsole}
                  disabled={messages.length === 0 || isProcessing || isPurging}
                  className={`p-1.5 sm:p-2 rounded-xl transition-colors cursor-pointer ${
                    messages.length === 0 
                      ? 'text-text-muted/30 cursor-not-allowed' 
                      : 'text-text-muted hover:text-rose-500 hover:bg-rose-500/10'
                  }`}
                  title="Fshi bisedën (Total Wipeout)"
                >
                  {isPurging ? <Loader2 size={16} className="animate-spin text-rose-500" /> : <Trash2 size={16} />}
                </button>

                {/* Fullscreen Toggle në Tablet/Desktop */}
                <button
                  type="button"
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="hidden md:flex p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                  title={isFullscreen ? "Zvogëlo" : "Fullscreen"}
                >
                  {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>

                {/* Close */}
                <button
                  type="button"
                  onClick={onClose}
                  className="p-1.5 sm:p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                  title="Mbyll"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Message Stream Area */}
            <div className={`flex-1 overflow-y-auto p-3.5 sm:p-6 custom-finance-scroll space-y-4 bg-canvas/30 select-text ${isFullscreen ? 'px-6 md:px-24 lg:px-48' : ''}`}>
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-2 sm:p-6 my-auto space-y-4 sm:space-y-6">
                  <div className="w-14 h-14 sm:w-20 sm:h-20 rounded-2xl sm:rounded-[2rem] bg-primary-start/10 text-primary-start flex items-center justify-center border border-primary-start/20 shadow-inner shrink-0">
                    <BrainCircuit size={28} className="sm:w-10 sm:h-10" />
                  </div>
                  <div className="max-w-xl">
                    <h4 className="text-sm sm:text-base md:text-lg font-black uppercase tracking-tight text-text-primary">
                      Terminali Hetimor Ekskluziv
                    </h4>
                    <p className="text-xs sm:text-sm text-text-muted mt-1 leading-relaxed">
                      Shtroni pyetje hetimore mbi provat, datat, deklaratat dhe shkeljet ligjore.
                    </p>
                  </div>

                  {/* Quick Forensic Action Chips */}
                  <div className="w-full max-w-2xl grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 pt-2">
                    {QUICK_FORENSIC_COMMANDS.map((cmd, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSendMessage(cmd.prompt)}
                        className="p-3 sm:p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start/50 rounded-xl sm:rounded-2xl text-left transition-all cursor-pointer shadow-xs group flex flex-col justify-between"
                      >
                        <div className="flex items-center gap-2 mb-1.5">
                          <cmd.icon size={15} className="text-primary-start shrink-0" />
                          <span className="text-xs sm:text-sm font-bold text-text-primary group-hover:text-primary-start transition-colors">
                            {cmd.label}
                          </span>
                        </div>
                        <p className="text-[11px] text-text-muted line-clamp-2 leading-snug">
                          {cmd.prompt}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-4 sm:space-y-6">
                  {messages.map((msg) => {
                    const isAi = msg.role === 'ai';
                    const isThinking = isAi && isProcessing && msg.content === '';

                    return (
                      <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex gap-2.5 sm:gap-3.5 ${isAi ? 'flex-row' : 'flex-row-reverse'}`}
                      >
                        {/* Avatar */}
                        <div
                          className={`w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0 border shadow-xs ${
                            isAi
                              ? 'bg-primary-start text-white border-primary-start'
                              : 'bg-surface border-main text-text-primary'
                          }`}
                        >
                          {isAi ? <BrainCircuit size={16} className="sm:w-5 sm:h-5" /> : <User size={16} className="sm:w-5 sm:h-5" />}
                        </div>

                        {/* Bubble Content */}
                        <div
                          className={`relative max-w-[88%] rounded-2xl py-2.5 px-3.5 sm:py-3.5 sm:px-5 border shadow-sm ${
                            isAi
                              ? 'bg-surface border-main text-text-primary rounded-tl-xs'
                              : 'bg-primary-start/15 border-primary-start/30 text-text-primary rounded-tr-xs font-medium'
                          }`}
                        >
                          {isAi && msg.content && (
                            <button
                              type="button"
                              onClick={() => handleCopyMessage(msg.id, msg.content)}
                              className="absolute top-2.5 right-2.5 p-1 text-text-muted hover:text-text-primary rounded-lg transition-colors cursor-pointer"
                              title="Kopjo përgjigjen"
                            >
                              {copiedId === msg.id ? <CheckCircle2 size={14} className="text-status-success" /> : <Copy size={14} />}
                            </button>
                          )}

                          {isThinking ? (
                            <div className="flex items-center gap-2 py-1">
                              <Loader2 size={16} className="animate-spin text-primary-start" />
                              <span className="text-xs sm:text-sm font-bold text-primary-start">
                                Duke arsyetuar mbi provat...
                              </span>
                            </div>
                          ) : isAi ? (
                            <div className="space-y-1.5">
                              <div className="markdown-content prose prose-slate dark:prose-invert max-w-none text-text-primary text-xs sm:text-sm leading-relaxed">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                  {autoLinkLegalCitations(msg.content)}
                                </ReactMarkdown>
                              </div>

                              {msg.citationAudit && (
                                <div className="pt-2 border-t border-main/60 flex items-center gap-2 text-[10px] text-text-muted font-mono flex-wrap">
                                  <ShieldCheck size={11} className="text-emerald-500 shrink-0" />
                                  <span>Nene: {msg.citationAudit.articles_cited?.length || 0}</span>
                                  <span>• Precedentë: {msg.citationAudit.verified_precedents?.length || 0}</span>
                                </div>
                              )}
                            </div>
                          ) : (
                            <p className="whitespace-pre-wrap leading-relaxed text-xs sm:text-sm">{msg.content}</p>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Input Terminal Bar (Optimizuar për Tastierën Mobile) */}
            <div className={`p-3 sm:p-4 bg-surface border-t border-main shrink-0 transition-all ${isFullscreen ? 'px-6 md:px-24 lg:px-48' : ''}`}>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage(input);
                }}
                className="flex items-end gap-2 sm:gap-2.5 bg-canvas border border-main rounded-xl sm:rounded-2xl p-2 focus-within:border-primary-start/50 transition-colors shadow-xs"
              >
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Pyet mbi provat, alibitë apo shkeljet..."
                  // 16px (text-base) në mobile për të parandaluar auto-zoom në iOS
                  className="flex-1 p-1.5 sm:p-2 bg-transparent text-base sm:text-sm text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[44px] max-h-[140px] border-0 outline-none"
                  rows={1}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isProcessing || isPurging}
                  className="h-10 w-10 sm:h-11 sm:w-11 bg-primary-start text-white rounded-xl shadow-md flex items-center justify-center hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 cursor-pointer mb-0.5"
                  title="Dërgo"
                >
                  {isProcessing ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} className="ml-0.5" />}
                </button>
              </form>
              <div className="flex items-center justify-between mt-2 px-1 text-[10px] sm:text-xs text-text-muted">
                <span className="truncate">Vula: {chainOfCustodyHash ? `${chainOfCustodyHash.slice(0, 16)}...` : 'E Vërtetuar'}</span>
                <span className="font-mono font-medium shrink-0 ml-2">Sonnet 4.6</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default ForensicInterrogationDrawer;