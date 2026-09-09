// FILE: frontend/src/components/forensics/ForensicInterrogationDrawer.tsx
// PHOENIX PROTOCOL - FORENSIC INTERROGATION TERMINAL V6.1 (RICH-TEXT WORD COMPATIBLE COPY)
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
    label: 'Pyetësor Taktik Kurth',
    icon: HelpCircle,
    prompt: 'Më harto një pyetësor taktik të thellë me 7 pyetje kurth për të ballafaquar palën kundërshtare dhe zyrtarët në seancën e ardhshme gjyqësore.'
  },
  {
    label: 'Shkeljet e Nenit 182 LPK / KPK',
    icon: Scale,
    prompt: 'Analizo të gjitha procesverbalet dhe aktvendimet e administruara dhe më nxirr shkeljet thelbësore procedurale sipas Nenit 182 të LPK-së dhe Kodit Penal.'
  },
  {
    label: 'Kryqëzimi i Provave & QPS',
    icon: ShieldAlert,
    prompt: 'Kryqëzo raportin e testit toksikologjik dhe provat shkencore me raportet e QPS-së dhe deklaratat e ekspertëve psikiatrikë.'
  }
];

// Nivelet e madhësisë së fontit për Chat-in
const FONT_LEVELS = [
  { label: '90%',   base: 13,   line: 1.55 },
  { label: '100%',  base: 15,   line: 1.65 },
  { label: '115%',  base: 17,   line: 1.7 },
  { label: '130%',  base: 19,   line: 1.75 },
  { label: '150%',  base: 21,   line: 1.8 }
];

const markdownToHtml = (markdown: string): string => {
  const escapeHtml = (value: string) => value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  return escapeHtml(markdown)
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/__(.+?)__/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^(.+)$/s, '<p>$1</p>');
};

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

  // Kontrolli i Zmadhimit të Shkrimit
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_chat_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1;
    } catch {
      return 1;
    }
  });
  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleIncreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_chat_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleDecreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_chat_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(1);
    try { localStorage.setItem('juristi_chat_font_size', '1'); } catch {}
  };

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

  // KOPJIMI I PASTËR DHE I FORNATUAR PËR MICROSOFT WORD (RICH TEXT)
  const handleCopyMessage = async (msgId: string, text: string) => {
    try {
      // Përpunon Markdown në format HTML
      const htmlContent = markdownToHtml(text);
      
      // Krijon një objekt ClipboardItem me HTML dhe Tekst të thjeshtë
      const clipboardItem = new ClipboardItem({
        'text/html': new Blob([htmlContent], { type: 'text/html' }),
        'text/plain': new Blob([text], { type: 'text/plain' }),
      });
      
      await navigator.clipboard.write([clipboardItem]);
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      // Nëse API-ja ClipboardItem dështon (p.sh. shfletues i vjetër), kthehet te kopjimi klasik
      console.warn('Clipboard API nuk mundi të ruajë HTML, po përdorim vetëm tekst.', err);
      navigator.clipboard.writeText(text);
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    }
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
                : 'w-full sm:w-[600px] md:w-[700px] lg:w-[800px] max-w-full'
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
                    <h3 className="text-sm sm:text-base font-black uppercase tracking-wider text-text-primary truncate">
                      Terminali Forenzik
                    </h3>
                    <span className="hidden xs:inline-flex px-1.5 py-0.5 rounded-full bg-primary-start/20 text-primary-start border border-primary-start/40 text-[9px] sm:text-[10px] font-mono font-bold uppercase shrink-0">
                      Sonnet 4.6
                    </span>
                  </div>
                  <p className="text-[10px] sm:text-[11px] text-text-muted truncate font-mono mt-0.5">
                    {caseNumber}: <span className="text-text-primary font-bold">{clientName}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                {/* KONTROLLI I ZMADHIMIT TË SHKRIMIT */}
                <div className="flex items-center gap-0.5 rounded-xl border border-main bg-surface p-0.5" aria-label="Madhësia e shkrimit">
                  <button
                    type="button"
                    onClick={handleDecreaseFont}
                    disabled={fontLevelIndex === 0}
                    className="h-7 w-7 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30 cursor-pointer flex items-center justify-center"
                    title="Zvogëlo shkrimin"
                  >
                    A−
                  </button>
                  <button
                    type="button"
                    onClick={handleResetFont}
                    title="Rivendos madhësinë e shkrimit"
                    className="min-w-8 text-[10px] font-bold text-text-muted hover:bg-hover rounded text-center cursor-pointer px-1 h-7 flex items-center justify-center"
                  >
                    {activeFont.label}
                  </button>
                  <button
                    type="button"
                    onClick={handleIncreaseFont}
                    disabled={fontLevelIndex === FONT_LEVELS.length - 1}
                    className="h-7 w-7 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30 cursor-pointer flex items-center justify-center"
                    title="Zmadho shkrimin"
                  >
                    A+
                  </button>
                </div>

                {/* Butoni i Koshit të Plehrave */}
                <button
                  type="button"
                  onClick={handleClearConsole}
                  disabled={messages.length === 0 || isProcessing || isPurging}
                  className={`p-2 rounded-xl transition-colors cursor-pointer ${
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
                  className="p-2 bg-rose-500/10 text-rose-500 hover:bg-rose-600 hover:text-white rounded-xl transition-colors cursor-pointer"
                  title="Mbyll"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* STILI DINAMIK PËR MARKDOWN BAZUAR NË FONT CONTROL */}
            <style>{`
              .forensic-chat-markdown p,
              .forensic-chat-markdown li,
              .forensic-chat-markdown span:not(.lucide) {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .forensic-chat-markdown h1, 
              .forensic-chat-markdown h2, 
              .forensic-chat-markdown h3 {
                font-size: ${activeFont.base + 2}px !important;
                line-height: 1.4 !important;
                margin-top: 1em !important;
                margin-bottom: 0.5em !important;
              }
            `}</style>

            {/* Message Stream Area */}
            <div className={`flex-1 overflow-y-auto p-4 sm:p-6 custom-finance-scroll space-y-5 sm:space-y-6 bg-canvas/30 select-text ${isFullscreen ? 'px-6 md:px-24 lg:px-48' : ''}`}>
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-2 sm:p-6 my-auto space-y-4 sm:space-y-6">
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl sm:rounded-[2rem] bg-primary-start/10 text-primary-start flex items-center justify-center border border-primary-start/20 shadow-inner shrink-0">
                    <BrainCircuit size={32} className="sm:w-10 sm:h-10" />
                  </div>
                  <div className="max-w-xl">
                    <h4 className="text-base sm:text-lg md:text-xl font-black uppercase tracking-tight text-text-primary">
                      Terminali Hetimor Ekskluziv
                    </h4>
                    <p className="text-xs sm:text-sm text-text-muted mt-1.5 leading-relaxed">
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
                        className="p-3.5 sm:p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start/50 rounded-xl sm:rounded-2xl text-left transition-all cursor-pointer shadow-xs group flex flex-col justify-between"
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <cmd.icon size={16} className="text-primary-start shrink-0" />
                          <span className="text-xs sm:text-sm font-bold text-text-primary group-hover:text-primary-start transition-colors">
                            {cmd.label}
                          </span>
                        </div>
                        <p className="text-[11px] sm:text-xs text-text-muted line-clamp-2 leading-relaxed">
                          {cmd.prompt}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-5 sm:space-y-6">
                  {messages.map((msg) => {
                    const isAi = msg.role === 'ai';
                    const isThinking = isAi && isProcessing && msg.content === '';

                    return (
                      <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`flex gap-2.5 sm:gap-4 ${isAi ? 'flex-row' : 'flex-row-reverse'}`}
                      >
                        {/* Avatar */}
                        <div
                          className={`w-9 h-9 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl flex items-center justify-center shrink-0 border shadow-sm ${
                            isAi
                              ? 'bg-gradient-to-br from-primary-start to-indigo-700 text-white border-primary-start/50'
                              : 'bg-surface border-main text-text-primary'
                          }`}
                        >
                          {isAi ? <BrainCircuit size={18} className="sm:w-6 sm:h-6" /> : <User size={18} className="sm:w-6 sm:h-6" />}
                        </div>

                        {/* Bubble Content */}
                        <div
                          className={`relative max-w-[88%] rounded-2xl py-3 px-4 sm:py-4 sm:px-6 border shadow-sm ${
                            isAi
                              ? 'bg-surface border-main text-text-primary rounded-tl-sm'
                              : 'bg-primary-start/10 border-primary-start/30 text-text-primary rounded-tr-sm font-medium'
                          }`}
                        >
                          {isAi && msg.content && (
                            <button
                              type="button"
                              onClick={() => handleCopyMessage(msg.id, msg.content)}
                              className="absolute top-2.5 right-2.5 sm:top-3 sm:right-3 p-1.5 text-text-muted hover:text-primary-start hover:bg-primary-start/10 rounded-lg transition-colors cursor-pointer"
                              title="Kopjo përgjigjen për Microsoft Word"
                            >
                              {copiedId === msg.id ? <CheckCircle2 size={14} className="text-emerald-500" /> : <Copy size={14} />}
                            </button>
                          )}

                          {isThinking ? (
                            <div className="flex items-center gap-2.5 py-1.5">
                              <Loader2 size={18} className="animate-spin text-primary-start" />
                              <span className="text-xs sm:text-sm font-bold text-primary-start">
                                Duke arsyetuar mbi provat...
                              </span>
                            </div>
                          ) : isAi ? (
                            <div className="space-y-2">
                              {/* RENDERUESI I FONTIT DINAMIK PËR AI */}
                              <div className="forensic-chat-markdown prose prose-slate dark:prose-invert max-w-none text-text-primary">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                                  {autoLinkLegalCitations(msg.content)}
                                </ReactMarkdown>
                              </div>

                              {msg.citationAudit && (
                                <div className="pt-3 border-t border-main/60 flex items-center gap-2 text-[10px] sm:text-[11px] text-text-muted font-mono flex-wrap">
                                  <ShieldCheck size={13} className="text-emerald-500 shrink-0" />
                                  <span>Nene të Zbuluara: <span className="font-bold text-text-primary">{msg.citationAudit.articles_cited?.length || 0}</span></span>
                                  <span>• Precedentë: <span className="font-bold text-text-primary">{msg.citationAudit.verified_precedents?.length || 0}</span></span>
                                </div>
                              )}
                            </div>
                          ) : (
                            /* PËRGJIGJA E PËRDORUESIT (TEXT NORMAL DINAMIK) */
                            <p className="whitespace-pre-wrap font-medium" style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}>
                              {msg.content}
                            </p>
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
            <div className={`p-3 sm:p-5 bg-surface border-t border-main shrink-0 transition-all ${isFullscreen ? 'px-6 md:px-24 lg:px-48' : ''}`}>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage(input);
                }}
                className="flex items-end gap-2 sm:gap-3 bg-canvas border border-main rounded-xl sm:rounded-2xl p-2 sm:p-2.5 focus-within:border-primary-start/50 transition-colors shadow-xs"
              >
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Pyet mbi provat, alibitë apo shkeljet ligjore..."
                  // E RËNDËSISHME: font-size mbajtur në minimum 16px për mobile për të ndaluar auto-zoom në iPhone
                  className="flex-1 p-1.5 sm:p-2 bg-transparent text-base text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[44px] sm:min-h-[48px] max-h-[160px] border-0 outline-none"
                  rows={1}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isProcessing || isPurging}
                  className="h-10 w-10 sm:h-12 sm:w-12 bg-primary-start text-white rounded-xl shadow-md flex items-center justify-center hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 cursor-pointer mb-0.5"
                  title="Dërgo"
                >
                  {isProcessing ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} className="ml-0.5" />}
                </button>
              </form>
              <div className="flex items-center justify-between mt-2.5 px-1.5 text-[10px] sm:text-xs text-text-muted">
                <span className="truncate">Vula e Çështjes: {chainOfCustodyHash ? `${chainOfCustodyHash.slice(0, 16)}...` : 'E Vërtetuar'}</span>
                <span className="font-mono font-medium shrink-0 ml-2">Modeli: anthropic/claude-sonnet-4.6</span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default ForensicInterrogationDrawer;