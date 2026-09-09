// FILE: frontend/src/components/forensics/ForensicInterrogationDrawer.tsx
// PHOENIX PROTOCOL - FORENSIC INTERROGATION TERMINAL V6.4 (SYNCHRONIZED SINGLE-ZOOM FOR CHAT & TEXTAREA)
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

// Nivelet e madhësisë së fontit: aplikohen NJËKOHËSISHT në Chat dhe në Textarea
const FONT_LEVELS = [
  { label: '90%',   base: 13,   line: 1.55 },
  { label: '100%',  base: 15,   line: 1.65 },
  { label: '115%',  base: 17,   line: 1.7 },
  { label: '130%',  base: 19,   line: 1.75 },
  { label: '150%',  base: 21,   line: 1.8 }
];

/**
 * Konvertues i plotë semantik Markdown në HTML të pasur për Microsoft Word
 * Mbështet: Tabela me vija dhe ngjyra, Tituj, Lista, Kuotime, Vija ndarëse dhe Bold/Italic
 */
const markdownToWordHtml = (markdown: string): string => {
  const lines = markdown.split(/\r?\n/);
  const htmlOutput: string[] = [];

  let inTable = false;
  let tableRows: string[][] = [];
  let inList: 'ul' | 'ol' | null = null;
  let inBlockquote = false;
  let blockquoteLines: string[] = [];

  const formatInline = (text: string): string => {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code style="background-color: #f1f5f9; padding: 2px 4px; font-family: Consolas, monospace; font-size: 10pt;">$1</code>');
  };

  const flushTable = () => {
    if (tableRows.length === 0) return;
    
    let tableHtml = '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; margin: 14px 0; font-family: Calibri, Arial, sans-serif; font-size: 10.5pt; border: 1px solid #94a3b8;">';
    const isSeparator = (row: string[]) => row.every(cell => /^:?-+:?$/.test(cell.trim()));

    let startIdx = 0;
    if (tableRows.length > 1 && isSeparator(tableRows[1])) {
      tableHtml += '<thead><tr style="background-color: #f1f5f9;">';
      for (const cell of tableRows[0]) {
        tableHtml += `<th style="border: 1px solid #94a3b8; padding: 8px 12px; text-align: left; font-weight: bold; color: #0f172a; background-color: #f1f5f9;">${formatInline(cell)}</th>`;
      }
      tableHtml += '</tr></thead><tbody>';
      startIdx = 2;
    } else {
      tableHtml += '<tbody>';
    }

    for (let i = startIdx; i < tableRows.length; i++) {
      if (isSeparator(tableRows[i])) continue;
      const bg = (i % 2 === 0) ? '#ffffff' : '#f8fafc';
      tableHtml += `<tr style="background-color: ${bg};">`;
      for (const cell of tableRows[i]) {
        tableHtml += `<td style="border: 1px solid #cbd5e1; padding: 7px 12px; color: #1e293b; vertical-align: top;">${formatInline(cell)}</td>`;
      }
      tableHtml += '</tr>';
    }

    tableHtml += '</tbody></table>';
    htmlOutput.push(tableHtml);
    tableRows = [];
    inTable = false;
  };

  const flushList = () => {
    if (inList) {
      htmlOutput.push(inList === 'ul' ? '</ul>' : '</ol>');
      inList = null;
    }
  };

  const flushBlockquote = () => {
    if (inBlockquote) {
      htmlOutput.push(`<blockquote style="border-left: 4px solid #2563eb; margin: 10px 0; padding: 8px 16px; background-color: #f8fafc; color: #334155; font-style: italic; font-family: Calibri, Arial, sans-serif;">${blockquoteLines.map(formatInline).join('<br>')}</blockquote>`);
      blockquoteLines = [];
      inBlockquote = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (line.startsWith('|') && line.endsWith('|')) {
      flushList();
      flushBlockquote();
      inTable = true;
      const cells = line.slice(1, -1).split('|').map(c => c.trim());
      tableRows.push(cells);
      continue;
    } else if (inTable) {
      flushTable();
    }

    if (/^(---|---|\*\*\*|___)$/.test(line)) {
      flushList();
      flushBlockquote();
      htmlOutput.push('<hr style="border: 0; border-top: 1px solid #cbd5e1; margin: 16px 0;" />');
      continue;
    }

    const hMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (hMatch) {
      flushList();
      flushBlockquote();
      const level = hMatch[1].length;
      const text = formatInline(hMatch[2]);
      const fontSize = level === 1 ? '16pt' : level === 2 ? '14pt' : '12pt';
      htmlOutput.push(`<h${level} style="font-size: ${fontSize}; font-family: Calibri, Arial, sans-serif; font-weight: bold; color: #0f172a; margin-top: 14px; margin-bottom: 6px;">${text}</h${level}>`);
      continue;
    }

    if (line.startsWith('>')) {
      flushList();
      inBlockquote = true;
      blockquoteLines.push(line.replace(/^>\s?/, ''));
      continue;
    } else if (inBlockquote) {
      flushBlockquote();
    }

    const bulletMatch = line.match(/^([•\-\*])\s+(.+)$/);
    if (bulletMatch) {
      if (inList !== 'ul') {
        flushList();
        htmlOutput.push('<ul style="margin: 6px 0 6px 24px; padding: 0; font-family: Calibri, Arial, sans-serif;">');
        inList = 'ul';
      }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: #1e293b; font-size: 11pt;">${formatInline(bulletMatch[2])}</li>`);
      continue;
    }

    const numMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (numMatch) {
      if (inList !== 'ol') {
        flushList();
        htmlOutput.push('<ol style="margin: 6px 0 6px 24px; padding: 0; font-family: Calibri, Arial, sans-serif;">');
        inList = 'ol';
      }
      htmlOutput.push(`<li style="margin-bottom: 4px; color: #1e293b; font-size: 11pt;">${formatInline(numMatch[2])}</li>`);
      continue;
    }

    flushList();
    if (line.length === 0) {
      continue;
    }

    htmlOutput.push(`<p style="margin: 6px 0; font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1e293b;">${formatInline(line)}</p>`);
  }

  flushTable();
  flushList();
  flushBlockquote();

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Eksport Forenzik</title>
      <style>
        body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #1e293b; }
        table { border-collapse: collapse; width: 100%; border: 1px solid #94a3b8; }
        th, td { border: 1px solid #cbd5e1; padding: 7px 12px; }
        th { background-color: #f1f5f9; font-weight: bold; }
      </style>
    </head>
    <body>
      ${htmlOutput.join('\n')}
    </body>
    </html>
  `.trim();
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

  // Kontrolli Qendror i Zmadhimit të Shkrimit (Shared Zoom State)
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

  // Rillogaritja automatike e lartësisë së fushës së shkrimit sa herë që shkruhet tekst OSE ndryshohet madhësia e shkrimit
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input, fontLevelIndex]);

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

  // KOPJIMI I PASTËR DHE I FORMOSHËM PËR MICROSOFT WORD
  const handleCopyMessage = async (msgId: string, text: string) => {
    const htmlContent = markdownToWordHtml(text);

    try {
      if (navigator.clipboard && window.ClipboardItem) {
        const clipboardItem = new ClipboardItem({
          'text/html': new Blob([htmlContent], { type: 'text/html' }),
          'text/plain': new Blob([text], { type: 'text/plain' }),
        });
        await navigator.clipboard.write([clipboardItem]);
      } else {
        throw new Error('ClipboardItem nuk mbështetet.');
      }
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      try {
        const copyHandler = (e: ClipboardEvent) => {
          e.preventDefault();
          if (e.clipboardData) {
            e.clipboardData.setData('text/html', htmlContent);
            e.clipboardData.setData('text/plain', text);
          }
        };
        document.addEventListener('copy', copyHandler);
        document.execCommand('copy');
        document.removeEventListener('copy', copyHandler);
        setCopiedId(msgId);
        setTimeout(() => setCopiedId(null), 2000);
      } catch {
        await navigator.clipboard.writeText(text);
        setCopiedId(msgId);
        setTimeout(() => setCopiedId(null), 2000);
      }
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] pointer-events-none overflow-hidden">
          {/* Backdrop shfaqet VETËM në Fullscreen për të mos bllokuar workspace-in */}
          {isFullscreen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="absolute inset-0 bg-black/75 backdrop-blur-sm pointer-events-auto"
            />
          )}

          {/* Slide-over Drawer Panel me pointer-events-auto */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 26, stiffness: 240 }}
            className={`pointer-events-auto absolute top-0 right-0 h-[100dvh] max-h-[100dvh] ${
              isFullscreen 
                ? 'w-full max-w-full' 
                : 'w-full sm:w-[580px] md:w-[680px] lg:w-[780px] max-w-full shadow-[-12px_0_40px_rgba(0,0,0,0.6)]'
            } border-l border-main flex flex-col bg-card transition-all duration-300 ease-in-out`}
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
                {/* Butonat Qendrorë të Zmadhimit të Shkrimit (Kontrollojnë njëkohësisht Chat-in dhe Textarea) */}
                <div className="flex items-center gap-0.5 rounded-xl border border-main bg-surface p-0.5" aria-label="Madhësia e shkrimit">
                  <button
                    type="button"
                    onClick={handleDecreaseFont}
                    disabled={fontLevelIndex === 0}
                    className="h-7 w-7 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30 cursor-pointer flex items-center justify-center"
                    title="Zvogëlo shkrimin (Chat & Fushën e Shkrimit)"
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
                    title="Zmadho shkrimin (Chat & Fushën e Shkrimit)"
                  >
                    A+
                  </button>
                </div>

                {/* Butoni i pastrimit të bisedës */}
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

                {/* Fullscreen Toggle */}
                <button
                  type="button"
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="hidden md:flex p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                  title={isFullscreen ? "Kthe në krah (Sidebar)" : "Fullscreen"}
                >
                  {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>

                {/* Butoni Mbyll */}
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

            {/* STILIZIMI DINAMIK I NJËHUR (APLIKOHET NJËKOHËSISHT MBI MESAZHET DHE MBI TEXTAREA) */}
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
              /* RREGULLA E DETYRUESHME ME !IMPORTANT PËR FUSHËN E SHKRIMIT (TEXTAREA) */
              .forensic-interrogation-textarea,
              .forensic-interrogation-textarea::placeholder {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
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
                              title="Kopjo përgjigjen për Microsoft Word (Formatuar me Tabela)"
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
                              {/* Renderimi i Markdown për AI */}
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

            {/* Input Terminal Bar */}
            <div className={`p-3 sm:p-5 bg-surface border-t border-main shrink-0 transition-all ${isFullscreen ? 'px-6 md:px-24 lg:px-48' : ''}`}>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage(input);
                }}
                className="flex items-end gap-2 sm:gap-3 bg-canvas border border-main rounded-xl sm:rounded-2xl p-2 sm:p-2.5 focus-within:border-primary-start/50 transition-colors shadow-xs"
              >
                {/* TEXTAREA ME KLASËN E SINKRONIZUAR TË ZMADHIMIT (.forensic-interrogation-textarea) */}
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Pyet mbi provat, alibitë apo shkeljet ligjore..."
                  className="forensic-interrogation-textarea flex-1 p-1.5 sm:p-2 bg-transparent text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[44px] sm:min-h-[48px] max-h-[200px] border-0 outline-none"
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