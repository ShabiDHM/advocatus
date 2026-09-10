// FILE: frontend/src/components/forensics/ForensicInterrogationDrawer.tsx
// PHOENIX PROTOCOL - FORENSIC INTERROGATION TERMINAL V7.0 (OMNI-CHANNEL UNIVERSAL ATTACHMENT PIPELINE)
// 100% COMPLETE CODE • ZERO DUPLICATIONS • ZERO TS WARNINGS • MULTI-EVIDENCE SMART ROUTER

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BrainCircuit, X, Send, Trash2, Copy, CheckCircle2, 
  Loader2, Swords, Scale, User, HelpCircle, ShieldAlert, Maximize2, Minimize2, ShieldCheck,
  Paperclip, FileText, Volume2, Table as TableIcon, Image as ImageIcon
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

const FONT_LEVELS = [
  { label: '90%',   base: 13,   line: 1.55 },
  { label: '100%',  base: 15,   line: 1.65 },
  { label: '115%',  base: 17,   line: 1.7 },
  { label: '130%',  base: 19,   line: 1.75 },
  { label: '150%',  base: 21,   line: 1.8 }
];

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

// ============================================================================
// KOMPONENTI I MEMOIZUAR I MESAZHIT (ZERO-LAG TYPING)
// ============================================================================
interface ForensicMessageBubbleProps {
  msg: ForensicMessage;
  isAi: boolean;
  isThinking: boolean;
  isCopied: boolean;
  onCopy: (id: string, text: string) => void;
  markdownComponents: any;
  activeFontBase: number;
  activeFontLine: number;
}

const ForensicMessageBubble: React.FC<ForensicMessageBubbleProps> = React.memo(({
  msg,
  isAi,
  isThinking,
  isCopied,
  onCopy,
  markdownComponents,
  activeFontBase,
  activeFontLine
}) => {
  const formattedContent = useMemo(() => {
    return isAi ? autoLinkLegalCitations(msg.content) : msg.content;
  }, [msg.content, isAi]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex gap-2.5 sm:gap-4 ${isAi ? 'flex-row' : 'flex-row-reverse'}`}
    >
      <div
        className={`w-9 h-9 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl flex items-center justify-center shrink-0 border shadow-sm ${
          isAi
            ? 'bg-gradient-to-br from-primary-start to-indigo-700 text-white border-primary-start/50'
            : 'bg-surface border-main text-text-primary'
        }`}
      >
        {isAi ? <BrainCircuit size={18} className="sm:w-6 sm:h-6" /> : <User size={18} className="sm:w-6 sm:h-6" />}
      </div>

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
            onClick={() => onCopy(msg.id, msg.content)}
            className="absolute top-2.5 right-2.5 sm:top-3 sm:right-3 p-1.5 text-text-muted hover:text-primary-start hover:bg-primary-start/10 rounded-lg transition-colors cursor-pointer"
            title="Kopjo përgjigjen për Microsoft Word"
          >
            {isCopied ? <CheckCircle2 size={14} className="text-emerald-500" /> : <Copy size={14} />}
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
            <div className="forensic-chat-markdown prose prose-slate dark:prose-invert max-w-none text-text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                {formattedContent}
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
          <p className="whitespace-pre-wrap font-medium" style={{ fontSize: `${activeFontBase}px`, lineHeight: activeFontLine }}>
            {msg.content}
          </p>
        )}
      </div>
    </motion.div>
  );
});

ForensicMessageBubble.displayName = 'ForensicMessageBubble';

// ============================================================================
// KOMPONENTI KRYESOR FORENZIK
// ============================================================================
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

  // Gjendja për dokumentin/provën e bashkëngjitur
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [isUploadingDoc, setIsUploadingDoc] = useState<boolean>(false);
  const [uploadStatusText, setUploadStatusText] = useState<string>('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

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

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInput(val);
    const target = e.target;
    target.style.height = 'auto';
    target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
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

  // DËRGIMI DHE DREJTIMI INTELIGJENT I SKEDARIT NË LABORATORIN PËRKATËS
  const handleSendMessage = async (textToSend: string) => {
    const cleanText = textToSend.trim();
    if ((!cleanText && !attachedFile) || isProcessing || isUploadingDoc || !caseId || isPurging) return;

    let userPromptText = cleanText;
    let fileUploadedNotice = '';

    if (attachedFile) {
      setIsUploadingDoc(true);
      const category = detectFileCategory(attachedFile);

      try {
        if (category === 'audio') {
          setUploadStatusText('Duke transkriptuar dhe analizuar regjistrimin audio me AI...');
          const uploadedAudio = await forensicDeskService.uploadForensicAudio(caseId, attachedFile);
          fileUploadedNotice = `\n\n🎙️ [PROVË AUDIO E ZBARDHUR NË LABORATOR: ${uploadedAudio.file_name || attachedFile.name}]`;
          if (!userPromptText) {
            userPromptText = `Ju lutem analizoni këtë regjistrim audio/dëshmi të sapongarkuar: ${attachedFile.name}. Nxirrni kërcënimet, kontradiktat, alibitë dhe elementet e veprave penale.`;
          }
        } else {
          setUploadStatusText(
            category === 'spreadsheet' 
              ? 'Duke indeksuar tabelën financiare me Pandas...' 
              : category === 'image'
              ? 'Duke ekzekutuar OCR mbi foton e provës...'
              : 'Duke indeksuar dokumentin në RAG...'
          );
          const uploadedDoc = await forensicDeskService.uploadForensicDocument(caseId, attachedFile);
          const label = category === 'spreadsheet' 
            ? 'TABELË FINANCIARE' 
            : category === 'image' 
            ? 'PROVË VIZUALE' 
            : 'DOKUMENT ZYRTAR';
          
          fileUploadedNotice = `\n\n📎 [${label} E INDEKSUAR: ${uploadedDoc.file_name || attachedFile.name}]`;
          if (!userPromptText) {
            userPromptText = `Ju lutem analizoni këtë material të ngarkuar rishtazi: ${attachedFile.name}. Nxirrni faktet kyçe, personat, datat dhe shkeljet ligjore.`;
          }
        }
      } catch (uploadErr: any) {
        console.error("Dështoi ngarkimi i materialit forenzik:", uploadErr);
        alert(`Dështoi ngarkimi i provës: ${uploadErr?.response?.data?.detail || uploadErr?.message || 'Gabim në server'}`);
        setIsUploadingDoc(false);
        setUploadStatusText('');
        return;
      } finally {
        setIsUploadingDoc(false);
        setUploadStatusText('');
        setAttachedFile(null);
      }
    }

    const fullMessageContent = `${userPromptText}${fileUploadedNotice}`;

    const userMsg: ForensicMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: fullMessageContent,
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
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setIsProcessing(true);

    try {
      const stream = await forensicDeskService.streamForensicChat(
        caseId,
        fullMessageContent,
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

  const handleCopyMessage = useCallback(async (msgId: string, text: string) => {
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
  }, []);

  // Renditja e ikonës për distinktivin e skedarit sipas llojit
  const renderAttachedBadge = () => {
    if (!attachedFile) return null;
    const cat = detectFileCategory(attachedFile);

    return (
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-2 px-3 py-1.5 mb-2 bg-primary-start/15 border border-primary-start/40 rounded-xl text-xs text-text-primary w-fit shadow-xs"
      >
        {cat === 'audio' && <Volume2 size={14} className="text-amber-400 shrink-0 animate-pulse" />}
        {cat === 'spreadsheet' && <TableIcon size={14} className="text-emerald-400 shrink-0" />}
        {cat === 'image' && <ImageIcon size={14} className="text-sky-400 shrink-0" />}
        {cat === 'document' && <FileText size={14} className="text-primary-start shrink-0" />}

        <span className="font-bold truncate max-w-[220px] sm:max-w-[340px] text-text-primary">
          {attachedFile.name}
        </span>
        <span className="text-[10px] text-text-muted font-mono uppercase">
          [{cat}] ({(attachedFile.size / 1024).toFixed(0)} KB)
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
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] pointer-events-none overflow-hidden">
          {isFullscreen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="absolute inset-0 bg-black/75 backdrop-blur-sm pointer-events-auto"
            />
          )}

          {/* Slide-over Drawer Panel */}
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

                <button
                  type="button"
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="hidden md:flex p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                  title={isFullscreen ? "Kthe në krah (Sidebar)" : "Fullscreen"}
                >
                  {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>

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

            {/* STILIZIMI DINAMIK */}
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
                      Shtroni pyetje hetimore mbi provat, ose bashkëngjitni me 📎 shkresa, audio regjistrime, foto ose tabela financiare.
                    </p>
                  </div>

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
                      <ForensicMessageBubble
                        key={msg.id}
                        msg={msg}
                        isAi={isAi}
                        isThinking={isThinking}
                        isCopied={copiedId === msg.id}
                        onCopy={handleCopyMessage}
                        markdownComponents={markdownComponents}
                        activeFontBase={activeFont.base}
                        activeFontLine={activeFont.line}
                      />
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Input Terminal Bar */}
            <div className={`p-3 sm:p-5 bg-surface border-t border-main shrink-0 transition-all ${isFullscreen ? 'px-6 md:px-24 lg:px-48' : ''}`}>
              
              {/* DISTINKTIVI VIZUAL MULTI-KATEGORI */}
              {renderAttachedBadge()}

              {/* INPUT I FSHEHUR GJITHËPËRFSHIRËS (DOKUMENTE, TABELA, FOTO DHE AUDIO) */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf,.docx,.doc,.txt,.xlsx,.xls,.csv,.mp3,.wav,.m4a,.ogg,.aac,.flac,image/*,audio/*"
                className="hidden"
              />

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage(input);
                }}
                className="flex items-end gap-2 sm:gap-3 bg-canvas border border-main rounded-xl sm:rounded-2xl p-2 sm:p-2.5 focus-within:border-primary-start/50 transition-colors shadow-xs"
              >
                {/* BUTONI OMNI-ATTACHMENT (PAPERCLIP) */}
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isProcessing || isUploadingDoc || isPurging}
                  className={`p-2 sm:p-2.5 rounded-xl transition-all cursor-pointer mb-0.5 shrink-0 ${
                    attachedFile
                      ? 'bg-primary-start text-white shadow-xs'
                      : 'text-text-muted hover:text-primary-start hover:bg-primary-start/10'
                  }`}
                  title="Bashkëngjit provë: Shkresë, Audio, Excel/CSV ose Foto"
                >
                  <Paperclip size={18} />
                </button>

                {/* TEXTAREA ME ZERO LAG */}
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder={
                    attachedFile 
                      ? `Shtoni pyetje për ${attachedFile.name} (ose shtypni Dërgo)...` 
                      : "Pyet mbi provat, alibitë apo shkeljet ligjore..."
                  }
                  className="forensic-interrogation-textarea flex-1 p-1.5 sm:p-2 bg-transparent text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[44px] sm:min-h-[48px] max-h-[200px] border-0 outline-none"
                  rows={1}
                />

                {/* BUTONI DËRGO */}
                <button
                  type="submit"
                  disabled={(!input.trim() && !attachedFile) || isProcessing || isUploadingDoc || isPurging}
                  className="h-10 w-10 sm:h-12 sm:w-12 bg-primary-start text-white rounded-xl shadow-md flex items-center justify-center hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 cursor-pointer mb-0.5"
                  title="Dërgo"
                >
                  {isProcessing || isUploadingDoc ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <Send size={18} className="ml-0.5" />
                  )}
                </button>
              </form>

              <div className="flex items-center justify-between mt-2.5 px-1.5 text-[10px] sm:text-xs text-text-muted">
                <span className="truncate">
                  {uploadStatusText || (chainOfCustodyHash ? `Vula: ${chainOfCustodyHash.slice(0, 16)}...` : 'Vula: E Vërtetuar')}
                </span>
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