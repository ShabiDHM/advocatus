// FILE: frontend/src/components/forensics/ForensicInterrogationDrawer.tsx
// PHOENIX PROTOCOL - STANDALONE FORENSIC INTERROGATION TERMINAL V2.0 (MONGODB ATLAS & MULTI-DEVICE SYNC)
// ZERO TS WARNINGS • POWERED BY CLAUDE SONNET 4.6 • ATOMIC $UNSET PURGE • 100% COMPLETE CODE

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BrainCircuit, X, Send, Trash2, Copy, CheckCircle2, 
  Loader2, Swords, Scale, User, HelpCircle, ShieldAlert
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

interface ForensicMessage {
  id: string;
  role: 'user' | 'ai';
  content: string;
  timestamp: string;
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
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  // 1. Ngarkimi nga MongoDB Atlas në hapje (Multi-Device Sync)
  useEffect(() => {
    if (isOpen && caseId) {
      apiService.axiosInstance.get<ForensicMessage[]>(`/cases/${caseId}/forensic-chat`)
        .then((res) => {
          if (Array.isArray(res.data)) {
            setMessages(res.data);
          } else {
            setMessages([]);
          }
        })
        .catch(() => {
          setMessages([]);
        });
    }
  }, [isOpen, caseId]);

  // 2. Ruajtja automatike në MongoDB Atlas pas çdo përgjigjeje
  const persistForensicMessages = useCallback(async (newMessages: ForensicMessage[]) => {
    if (!caseId) return;
    try {
      await apiService.axiosInstance.put(`/cases/${caseId}/forensic-chat`, {
        forensic_chat_history: newMessages
      });
    } catch (err) {
      console.error("Failed to persist forensic chat to MongoDB:", err);
    }
  }, [caseId]);

  // Auto-scroll kur mbërrin mesazhi
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Rregullimi dinamik i lartësisë së inputit
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  // Dërgimi i pyetjes te Claude Sonnet 4.6 me modalitetin DEEP
  const handleSendMessage = async (textToSend: string) => {
    const cleanText = textToSend.trim();
    if (!cleanText || isStreaming || !caseId || isPurging) return;

    const userMsg: ForensicMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: cleanText,
      timestamp: new Date().toISOString()
    };

    const aiMsgId = `ai_${Date.now()}`;
    const aiPlaceholder: ForensicMessage = {
      id: aiMsgId,
      role: 'ai',
      content: '',
      timestamp: new Date().toISOString()
    };

    const updatedWithUser = [...messages, userMsg, aiPlaceholder];
    setMessages(updatedWithUser);
    setInput('');
    setIsStreaming(true);

    try {
      const stream = apiService.sendChatMessageStream(
        caseId,
        cleanText,
        undefined,
        'ks',
        'DEEP',
        'automatic',
        false
      );

      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        const currentAcc = accumulated;

        setMessages((prev) => {
          const next = [...prev];
          const lastIdx = next.findIndex(m => m.id === aiMsgId);
          if (lastIdx !== -1) {
            next[lastIdx] = { ...next[lastIdx], content: currentAcc };
          }
          return next;
        });
      }

      setMessages((prev) => {
        persistForensicMessages(prev);
        return prev;
      });
    } catch (err: any) {
      console.error("Forensic Interrogation Stream Error:", err);
      setMessages((prev) => {
        const next = [...prev];
        const lastIdx = next.findIndex(m => m.id === aiMsgId);
        if (lastIdx !== -1) {
          next[lastIdx] = { 
            ...next[lastIdx], 
            content: `[Gabim Teknik në Terminalin Forenzik: ${err?.message || 'Nuk u arrit lidhja me Claude Sonnet 4.6.'}]` 
          };
        }
        persistForensicMessages(next);
        return next;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(input);
    }
  };

  // 3. TOTAL CASCADE WIPEOUT NË MONGODB ATLAS
  const handleClearConsole = async () => {
    if (messages.length === 0 || !caseId || isPurging) return;
    const confirmWipe = window.confirm("A jeni i sigurt që dëshironi të asgjësoni plotësisht bisedën forenzike nga Baza e të Dhënave (Total Cascade Wipeout)?");
    if (!confirmWipe) return;

    setIsPurging(true);
    try {
      await apiService.axiosInstance.delete(`/cases/${caseId}/forensic-chat`);
      setMessages([]);
    } catch (err) {
      console.error("Could not wipe forensic chat on MongoDB:", err);
      alert("Dështoi asgjësimi i bisedës forenzike në server.");
    } finally {
      setIsPurging(false);
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
        <div className="fixed inset-0 z-[200] select-none pointer-events-auto">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/75 backdrop-blur-sm"
          />

          {/* Slide-over Drawer Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 240 }}
            className="absolute top-0 right-0 bottom-0 w-full sm:w-[580px] md:w-[680px] lg:w-[760px] max-w-[96vw] border-l border-main shadow-2xl flex flex-col bg-card"
            style={{ backgroundColor: 'var(--bg-card, #020617)' }}
          >
            {/* Top Header */}
            <div className="p-4 border-b border-main bg-surface/80 shrink-0 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-primary-start to-indigo-700 text-white flex items-center justify-center border border-primary-start/30 shadow-md shrink-0">
                  <BrainCircuit size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="text-xs sm:text-sm font-black uppercase tracking-wider text-text-primary truncate">
                      Terminali i Hetimit Forenzik
                    </h3>
                    <span className="px-2 py-0.5 rounded-full bg-primary-start/20 text-primary-start border border-primary-start/40 text-[9px] font-mono font-bold uppercase shrink-0">
                      Claude Sonnet 4.6 • 1M
                    </span>
                  </div>
                  <p className="text-[10px] sm:text-[11px] text-text-muted truncate font-mono mt-0.5">
                    {caseNumber}: <span className="text-text-primary font-bold">{clientName}</span>
                    {chainOfCustodyHash && <span className="opacity-60 ml-2">[{chainOfCustodyHash}]</span>}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                {messages.length > 0 && (
                  <button
                    type="button"
                    onClick={handleClearConsole}
                    disabled={isStreaming || isPurging}
                    className="p-2 text-text-muted hover:text-rose-500 hover:bg-rose-500/10 rounded-xl transition-colors cursor-pointer disabled:opacity-30"
                    title="Asgjëso bisedën nga MongoDB Atlas (Total Wipeout)"
                  >
                    {isPurging ? <Loader2 size={16} className="animate-spin text-rose-500" /> : <Trash2 size={16} />}
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                  title="Mbyll Terminalin"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* Message Stream Area */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 custom-finance-scroll space-y-4 bg-canvas/30 select-text">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-4 sm:p-8 my-auto space-y-5">
                  <div className="w-16 h-16 rounded-3xl bg-primary-start/10 text-primary-start flex items-center justify-center border border-primary-start/20 shadow-inner">
                    <BrainCircuit size={32} />
                  </div>
                  <div className="max-w-md">
                    <h4 className="text-sm sm:text-base font-black uppercase tracking-tight text-text-primary">
                      Console Hetimore e SuperAdminit
                    </h4>
                    <p className="text-xs text-text-muted mt-1 leading-relaxed">
                      Merrni në pyetje inteligjencën doktrinare mbi të gjitha shkresat e fashikullit. Biseda sinkronizohet automatikisht në të gjitha pajisjet tuaja nëpërmjet **MongoDB Atlas**.
                    </p>
                  </div>

                  {/* Quick Forensic Action Chips */}
                  <div className="w-full max-w-lg grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                    {QUICK_FORENSIC_COMMANDS.map((cmd, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSendMessage(cmd.prompt)}
                        className="p-3 bg-surface hover:bg-hover border border-main hover:border-primary-start/50 rounded-2xl text-left transition-all cursor-pointer shadow-xs group flex flex-col justify-between"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <cmd.icon size={14} className="text-primary-start shrink-0" />
                          <span className="text-[11px] font-bold text-text-primary group-hover:text-primary-start transition-colors">
                            {cmd.label}
                          </span>
                        </div>
                        <p className="text-[10px] text-text-muted line-clamp-2 leading-snug">
                          {cmd.prompt}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((msg) => {
                    const isAi = msg.role === 'ai';
                    const isThinking = isAi && isStreaming && msg.content === '';

                    return (
                      <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex gap-3 ${isAi ? 'flex-row' : 'flex-row-reverse'}`}
                      >
                        {/* Avatar */}
                        <div
                          className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border shadow-xs ${
                            isAi
                              ? 'bg-primary-start text-white border-primary-start'
                              : 'bg-surface border-main text-text-primary'
                          }`}
                        >
                          {isAi ? <BrainCircuit size={16} /> : <User size={16} />}
                        </div>

                        {/* Bubble Content */}
                        <div
                          className={`relative max-w-[88%] rounded-2xl py-3 px-4 text-xs sm:text-sm border shadow-sm ${
                            isAi
                              ? 'bg-surface border-main text-text-primary rounded-tl-xs'
                              : 'bg-primary-start/15 border-primary-start/30 text-text-primary rounded-tr-xs font-medium'
                          }`}
                        >
                          {/* Copy Action for AI Responses */}
                          {isAi && msg.content && (
                            <button
                              type="button"
                              onClick={() => handleCopyMessage(msg.id, msg.content)}
                              className="absolute top-2.5 right-2.5 p-1 text-text-muted hover:text-text-primary rounded-lg transition-colors cursor-pointer"
                              title="Kopjo përgjigjen"
                            >
                              {copiedId === msg.id ? <CheckCircle2 size={13} className="text-status-success" /> : <Copy size={13} />}
                            </button>
                          )}

                          {isThinking ? (
                            <div className="flex items-center gap-2 py-1">
                              <Loader2 size={14} className="animate-spin text-primary-start" />
                              <span className="text-xs font-bold text-primary-start">
                                Claude Sonnet 4.6 po arsyeton mbi fashikullin...
                              </span>
                            </div>
                          ) : isAi ? (
                            <div className="markdown-content prose prose-slate dark:prose-invert max-w-none text-text-primary text-xs sm:text-sm leading-relaxed">
                              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                {autoLinkLegalCitations(msg.content)}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Input Terminal Bar */}
            <div className="p-3 sm:p-4 bg-surface border-t border-main shrink-0">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage(input);
                }}
                className="flex items-end gap-2 bg-canvas border border-main rounded-2xl p-2 focus-within:border-primary-start/50 transition-colors shadow-xs"
              >
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Pyet Claude Sonnet 4.6 mbi provat, alibitë apo shkeljet procedurale..."
                  className="flex-1 p-2 bg-transparent text-xs sm:text-sm text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[40px] max-h-[160px] border-0 outline-none"
                  rows={1}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isStreaming || isPurging}
                  className="h-9 w-9 bg-primary-start text-white rounded-xl shadow-md flex items-center justify-center hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 cursor-pointer"
                  title="Dërgo pyetjen hetimore"
                >
                  {isStreaming ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} className="ml-0.5" />}
                </button>
              </form>
              <div className="flex items-center justify-between mt-2 px-1 text-[10px] text-text-muted">
                <span>Sinkronizuar në MongoDB Atlas • Multi-Device Sync</span>
                <span className="font-mono">Modeli: anthropic/claude-sonnet-4.6</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default ForensicInterrogationDrawer;