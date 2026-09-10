// FILE: frontend/src/components/forensics/DocumentForensicLab.tsx
// PHOENIX PROTOCOL - INTEGRATED FORENSIC STUDIO V17.0 (DUAL-MODE: SINGLE DOC & FULL DOSSIER + TOGGLE DESELECT)
// ZERO TS WARNINGS • POWERED BY CLAUDE SONNET 4.6 • 100% COMPLETE CODE • PIXEL-PERFECT SYMMETRY

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  Trash2,
  Loader2,
  RefreshCw,
  Search,
  Maximize2,
  Minimize2,
  Eye,
  Play,
  Pencil,
  Archive,
  FileSearch,
  Copy,
  Check,
  X,
  Send,
  BrainCircuit,
  User,
  Paperclip,
  Sparkles,
  ShieldCheck} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTranslation } from 'react-i18next';

import { forensicDeskService, ForensicDocItem } from '../../services/forensicDeskService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';
import PDFViewerModal from '../FileViewerModal';
import { RenameDocumentModal } from '../case/RenameDocumentModal';
import { API_V1_URL } from '../../services/api';
import { apiClient } from '../../services/apiClient';

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

interface DocumentForensicLabProps {
  caseId: string;
  clientName?: string;
  caseNumber?: string;
  chainOfCustodyHash?: string;
  onEvidenceChange?: () => void;
}

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
      className={`flex gap-2.5 sm:gap-3.5 ${isAi ? 'flex-row' : 'flex-row-reverse'}`}
    >
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 border shadow-sm ${
          isAi
            ? 'bg-gradient-to-br from-primary-start to-indigo-700 text-white border-primary-start/50'
            : 'bg-surface border-main text-text-primary'
        }`}
      >
        {isAi ? <BrainCircuit size={16} /> : <User size={16} />}
      </div>

      <div
        className={`relative max-w-[88%] rounded-2xl py-3 px-4 border shadow-sm ${
          isAi
            ? 'bg-surface border-main text-text-primary rounded-tl-sm'
            : 'bg-primary-start/10 border-primary-start/30 text-text-primary rounded-tr-sm font-medium'
        }`}
      >
        {isAi && msg.content && (
          <button
            type="button"
            onClick={() => onCopy(msg.id, msg.content)}
            className="absolute top-2.5 right-2.5 p-1 text-text-muted hover:text-primary-start hover:bg-primary-start/10 rounded-lg transition-colors cursor-pointer"
            title="Kopjo përgjigjen për Microsoft Word"
          >
            {isCopied ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
          </button>
        )}

        {isThinking ? (
          <div className="flex items-center gap-2 py-1">
            <Loader2 size={16} className="animate-spin text-primary-start" />
            <span className="text-xs font-bold text-primary-start">
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
              <div className="pt-2.5 border-t border-main/60 flex items-center gap-2 text-[10px] sm:text-[11px] text-text-muted font-mono flex-wrap">
                <ShieldCheck size={12} className="text-emerald-500 shrink-0" />
                <span>Nene: <span className="font-bold text-text-primary">{msg.citationAudit.articles_cited?.length || 0}</span></span>
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
// KOMPONENTI KRYESOR FORENZIK ME ZGJEDHJE DHE ÇZGJEDHJE (TOGGLE DESELECT)
// ============================================================================
export const DocumentForensicLab: React.FC<DocumentForensicLabProps> = ({
  caseId,
  clientName = 'Pala e Regjistruar',
  caseNumber = 'LËNDA FORENZIKE',
  chainOfCustodyHash,
  onEvidenceChange
}) => {
  const { t } = useTranslation();

  const [documents, setDocuments] = useState<ForensicDocItem[]>([]);
  // selectedDocId mund të jetë null (Gjendja Neutrale / Fashikulli i Plotë)
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgressText, setUploadProgressText] = useState<string>('');
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [mobileTab, setMobileTab] = useState<'DOCS' | 'CHAT'>('DOCS');

  // Gjendja e Chat-it Simetrik
  const [messages, setMessages] = useState<ForensicMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [isFullscreenChat, setIsFullscreenChat] = useState<boolean>(false);

  // Gjendja e bashkëngjitjes në Chat
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [isUploadingChatDoc, setIsUploadingChatDoc] = useState<boolean>(false);
  const [chatUploadStatusText, setChatUploadStatusText] = useState<string>('');

  // Modals & Viewers
  const [viewingDoc, setViewingDoc] = useState<ForensicDocItem | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);
  const [extractedModalData, setExtractedModalData] = useState<{ docName: string; text: string } | null>(null);
  const [loadingTextDocId, setLoadingTextDocId] = useState<string | null>(null);
  const [copiedExtractedText, setCopiedExtractedText] = useState<boolean>(false);
  const [renameDocId, setRenameDocId] = useState<string | null>(null);
  const [renameDocName, setRenameDocName] = useState<string>('');
  const [archivingDocId, setArchivingDocId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatFileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);
  
  // Dokumenti aktiv (ose null nëse jemi në gjendje neutrale / fashikull i plotë)
  const activeDoc = useMemo(() => documents.find(d => d.id === selectedDocId), [documents, selectedDocId]);

  // Kontrolli i Madhësisë së Shkrimit
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_forensic_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1;
    } catch {
      return 1;
    }
  });
  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleIncreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleDecreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(1);
    try { localStorage.setItem('juristi_forensic_font_size', '1'); } catch {}
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
      console.warn("Nuk u ngarkua historiku i bisedës:", err);
    }
  }, [caseId]);

  const loadDocuments = useCallback(async (silent: boolean = false) => {
    if (!caseId) return;
    if (!silent) setLoadingDocs(true);
    try {
      const docs = await forensicDeskService.listForensicDocuments(caseId);
      setDocuments(docs);
    } catch (err) {
      console.error("Dështoi ngarkimi i dokumenteve forenzike:", err);
    } finally {
      if (!silent) setLoadingDocs(false);
    }
  }, [caseId]);

  useEffect(() => {
    const hasProcessing = documents.some(d => d.status === 'PROCESSING' || d.status === 'UPLOADING');
    if (!hasProcessing) return;

    const interval = setInterval(() => {
      loadDocuments(true);
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, loadDocuments]);

  useEffect(() => {
    if (caseId) {
      loadDocuments();
      loadChatHistory();
    }
  }, [caseId, loadDocuments, loadChatHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  // TOGGLE SELECT / DESELECT: Nëse klikoni dokumentin aktiv, ai ÇZGJIHET (kthehet neutral te fashikulli)
  const handleToggleSelectDoc = (docId: string) => {
    setSelectedDocId(prev => (prev === docId ? null : docId));
    if (window.innerWidth < 1024) setMobileTab('CHAT');
  };

  const handleUploadFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || !caseId) return;
    setIsUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgressText(`Duke ngarkuar: ${file.name}...`);
        await forensicDeskService.uploadForensicDocument(caseId, file);
      }
      setUploadProgressText("Shkresat u ngarkuan me sukses.");
      await loadDocuments();
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Gabim gjatë ngarkimit të dokumentit:", err);
      alert("Dështoi ngarkimi i dokumentit.");
    } finally {
      setIsUploading(false);
      setUploadProgressText('');
    }
  };

  const handleDeleteDocument = async (docId: string, docName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    const confirmDelete = window.confirm(`A jeni i sigurt që dëshironi të fshini shkresën "${docName}" nga dosja?`);
    if (!confirmDelete) return;

    setDeletingDocId(docId);
    try {
      await forensicDeskService.deleteForensicDocument(caseId, docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      if (selectedDocId === docId) {
        setSelectedDocId(null);
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e dokumentit:", err);
      alert("Dështoi fshirja e dokumentit nga serveri.");
    } finally {
      setDeletingDocId(null);
    }
  };

  const handleViewDocument = (doc: ForensicDocItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    const url = `${API_V1_URL}/forensic/documents/${caseId}/${doc.id}/preview`;
    setViewingUrl(url);
    setViewingDoc(doc);
  };

  const handleViewMediaDocument = (doc: ForensicDocItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId || !doc.media_id || !doc.media_type) return;
    const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    if (!token) return;

    let streamUrl = '';
    if (doc.media_type === 'audio') {
      streamUrl = forensicDeskService.getForensicAudioStreamUrl(caseId, doc.media_id, token);
    } else if (doc.media_type === 'video' || doc.media_type === 'image') {
      streamUrl = forensicDeskService.getForensicVisualStreamUrl(caseId, doc.media_id, token);
    }

    if (streamUrl) window.open(streamUrl, '_blank', 'noopener,noreferrer');
  };

  const handleViewExtractedText = async (doc: ForensicDocItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId || !doc.id) return;

    setLoadingTextDocId(doc.id);
    try {
      const response = await apiClient.get<string>(
        `/forensic/documents/${caseId}/${doc.id}/extracted-text`,
        { responseType: 'text' }
      );
      const text = response.data || '';
      if (!text || !text.trim()) {
        alert("Teksti nuk është gati ende (po procesohet).");
        return;
      }
      setExtractedModalData({ docName: doc.file_name, text });
      setCopiedExtractedText(false);
    } catch (err) {
      alert("Teksti i ekstraktuar nuk është i disponueshëm.");
    } finally {
      setLoadingTextDocId(null);
    }
  };

  const handleConfirmRename = async (newName: string) => {
    if (!caseId || !renameDocId) return;
    try {
      await forensicDeskService.renameForensicDocument(caseId, renameDocId, newName);
      setDocuments(prev => prev.map(d => d.id === renameDocId ? { ...d, file_name: newName } : d));
    } catch {
      alert("Dështoi riemërtimi.");
    } finally {
      setRenameDocId(null);
      setRenameDocName('');
    }
  };

  const handleArchiveDocument = async (doc: ForensicDocItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    if (!window.confirm(`A dëshironi ta arkivoni shkresën "${doc.file_name}"?`)) return;

    setArchivingDocId(doc.id);
    try {
      await apiClient.post(`/forensic/documents/${caseId}/${doc.id}/archive`);
      setDocuments(prev => prev.map(d => d.id === doc.id ? { ...d, status: 'ARCHIVED' } : d));
      if (onEvidenceChange) onEvidenceChange();
    } catch {
      alert("Dështoi arkivimi i dokumentit.");
    } finally {
      setArchivingDocId(null);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setInput(val);
    const target = e.target;
    target.style.height = 'auto';
    target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
  };

  const handleChatFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setAttachedFile(file);
    if (e.target) e.target.value = '';
  };

  const waitForEvidenceProcessing = async (category: FileCategory, evidenceId: string): Promise<boolean> => {
    for (let i = 0; i < 18; i++) {
      await new Promise(res => setTimeout(res, 1200));
      try {
        if (category === 'audio') {
          const audios = await forensicDeskService.listForensicAudio(caseId);
          const match = audios.find(a => (a.id === evidenceId || a._id === evidenceId));
          if (match && (match.status === 'READY' || match.status === 'PROCESSED')) return true;
        } else {
          const docs = await forensicDeskService.listForensicDocuments(caseId);
          const match = docs.find(d => (d.id === evidenceId || d._id === evidenceId));
          if (match && (match.status === 'READY' || match.status === 'PROCESSED' || (match.extracted_text && match.extracted_text.length > 50))) {
            return true;
          }
        }
      } catch {}
    }
    return false;
  };

  // DËRGIMI I MESAZHIT: NËSE KA DOKUMENT TË PËRZGJEDHUR, FOKUSOHET TE AI; NËSE JO, VEPRON ME TË GJITHË FASHIKULLIN
  const handleSendChatMessage = async (textToSend: string) => {
    const cleanText = textToSend.trim();
    if ((!cleanText && !attachedFile) || isProcessing || isUploadingChatDoc || !caseId || isPurging) return;

    let userPromptText = cleanText;
    let fileUploadedNotice = '';

    if (attachedFile) {
      setIsUploadingChatDoc(true);
      const category = detectFileCategory(attachedFile);
      const currentFileName = attachedFile.name;

      try {
        if (category === 'audio') {
          setChatUploadStatusText('Duke ngarkuar audion...');
          const uploadedAudio = await forensicDeskService.uploadForensicAudio(caseId, attachedFile);
          const audioId = uploadedAudio.id || uploadedAudio._id || '';

          setChatUploadStatusText('Duke zbardhur transkriptin audio me AI...');
          if (audioId) await waitForEvidenceProcessing('audio', audioId);

          fileUploadedNotice = `\n\n🎙️ [PROVË AUDIO E ZBARDHUR NË LABORATOR: ${uploadedAudio.file_name || currentFileName}]`;
          if (!userPromptText) {
            userPromptText = `Ju lutem analizoni këtë regjistrim audio/dëshmi të sapongarkuar: ${currentFileName}. Nxirrni kërcënimet, kontradiktat, alibitë dhe elementet e veprave penale.`;
          }
        } else {
          setChatUploadStatusText('Duke ngarkuar dhe kryer OCR...');
          const uploadedDoc = await forensicDeskService.uploadForensicDocument(caseId, attachedFile);
          const docId = uploadedDoc.id || uploadedDoc._id || '';

          setChatUploadStatusText('Duke lexuar faqet me OCR dhe indeksuar në RAG...');
          if (docId) await waitForEvidenceProcessing('document', docId);

          fileUploadedNotice = `\n\n📎 [DOKUMENT I PROCESUAR: ${uploadedDoc.file_name || currentFileName}]`;
          if (!userPromptText) {
            userPromptText = `Ju lutem bëni analizën e plotë ligjore dhe hetimore të këtij dokumenti të sapongarkuar: ${currentFileName}. Nxirrni personat, datat, deklaratat dhe shkeljet ligjore.`;
          }
        }

        await loadDocuments(true);
        if (onEvidenceChange) onEvidenceChange();
      } catch (uploadErr: any) {
        alert(`Dështoi ngarkimi i provës: ${uploadErr?.message || 'Gabim në server'}`);
        setIsUploadingChatDoc(false);
        setChatUploadStatusText('');
        return;
      } finally {
        setIsUploadingChatDoc(false);
        setChatUploadStatusText('');
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
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setIsProcessing(true);

    // KONTEKSTI DINAMIK: DOKUMENT SPECIFIK APO FASHIKULLI I PLOTË
    const contextHeader = activeDoc
      ? `Lënda: ${caseNumber} - ${clientName}. Dokumenti i fokusuar: ${activeDoc.file_name}. Vula: ${chainOfCustodyHash || 'AKTIVE'}`
      : `Lënda: ${caseNumber} - ${clientName}. FASHIKULLI I PLOTË (${documents.length} shkresa të administruara). Vula: ${chainOfCustodyHash || 'AKTIVE'}`;

    try {
      const stream = await forensicDeskService.streamForensicChat(
        caseId,
        fullMessageContent,
        contextHeader
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
            next[idx] = { ...next[idx], content: accumulated };
          }
          return next;
        });
      }
    } catch (err: any) {
      setMessages(prev => {
        const next = [...prev];
        const idx = next.findIndex(m => m.id === aiPlaceholderId);
        if (idx !== -1) {
          next[idx] = { ...next[idx], content: `[GABIM: ${err?.message || 'Lidhja me Claude dështoi.'}]` };
        }
        return next;
      });
    } finally {
      setIsProcessing(false);
    }
  };

  // BUTONI I SHPEJTË DINAMIK: ANALIZO DOKUMENTIN (NËSE KA DOK) APO ANALIZO FASHIKULLIN (NËSE ËSHTË NEUTRAL)
  const handleQuickAction = () => {
    if (isProcessing) return;

    if (activeDoc) {
      // 1. Analizë e dokumentit të përzgjedhur
      const prompt = `[DIREKTIVË FORENZIKE] Ju lutem bëni analizën e plotë ligjore dhe hetimore të shkresës: "${activeDoc.file_name}".
1. Të dhënat procedurale (Organi, numri i lëndës/aktit, data).
2. Struktura e personave të përfshirë dhe rolet procedurale.
3. Rrethanat faktike dhe deklaratat fjalë për fjalë (Verbatim).
4. Shkeljet ligjore, kontradiktat dhe pasojat procedurale sipas Kodit Penal dhe Procedurës Penale/Civile të Kosovës.`;
      handleSendChatMessage(prompt);
    } else {
      // 2. Analizë e gjithë fashikullit të lëndës (Neutral)
      const prompt = `[DIREKTIVË FORENZIKE — FASHIKULLI I PLOTË] Ju lutem bëni analizën e thellë të të gjithë fashikullit të lëndës duke kryqëzuar të gjitha ${documents.length} shkresat dhe provat e administruara:
1. Rindërtimi kronologjik i ngjarjeve nga të gjitha shkresat.
2. Struktura e plotë e aktorëve, personave të dyshuar, zyrtarëve dhe deklarimeve të tyre.
3. Kontradiktat thelbësore dhe alibitë e rreme të zbuluara mes provave.
4. Shkeljet thelbësore procedurale (Neni 182 LPK / KPP) dhe masat e menjëhershme ligjore.`;
      handleSendChatMessage(prompt);
    }
  };

  const handleClearChat = async () => {
    if (messages.length === 0 || !caseId || isPurging) return;
    if (!window.confirm("A jeni i sigurt që dëshironi të asgjësoni bisedën forenzike nga MongoDB Atlas?")) return;

    setIsPurging(true);
    try {
      await forensicDeskService.clearChatHistory(caseId);
      setMessages([]);
    } catch {
      alert("Dështoi pastrimi i bisedës.");
    } finally {
      setIsPurging(false);
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
        throw new Error();
      }
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      await navigator.clipboard.writeText(text);
      setCopiedId(msgId);
      setTimeout(() => setCopiedId(null), 2000);
    }
  }, []);

  const filteredDocs = documents.filter(d =>
    (d.file_name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-4 select-none relative">
      
      {/* SHIRITI I KALIMIT NË MOBILE (< lg) */}
      <div className="flex lg:hidden items-center bg-surface border border-main rounded-2xl p-1 shadow-sm">
        <button
          type="button"
          onClick={() => setMobileTab('DOCS')}
          className={`flex-1 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            mobileTab === 'DOCS' ? 'bg-primary-start text-white shadow-sm' : 'text-text-muted hover:text-text-primary'
          }`}
        >
          <FileText size={14} />
          <span>Shkresat ({documents.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setMobileTab('CHAT')}
          className={`flex-1 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            mobileTab === 'CHAT' ? 'bg-primary-start text-white shadow-sm' : 'text-text-muted hover:text-text-primary'
          }`}
        >
          <BrainCircuit size={14} />
          <span>Terminali Forenzik</span>
        </button>
      </div>

      {/* STILI I FONTIT DINAMIK PËR CHAT DHE TEXTAREA */}
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
        .forensic-integrated-textarea,
        .forensic-integrated-textarea::placeholder {
          font-size: ${activeFont.base}px !important;
          line-height: ${activeFont.line} !important;
        }
      `}</style>

      {/* RRJETI SIMETRIK ME LARTËSI TË NJËJTË (SPLIT-SCREEN WORKSPACE) */}
      <div className={`grid grid-cols-1 ${isFullscreenChat ? 'lg:grid-cols-1' : 'lg:grid-cols-12'} gap-4 sm:gap-6 items-stretch h-[calc(100vh-210px)] min-h-[680px] max-h-[820px] transition-all duration-300`}>
        
        {/* KOLONA E MAJTË: SHKRESAT (5 Kolona në Desktop) */}
        {(!isFullscreenChat && (mobileTab === 'DOCS' || window.innerWidth >= 1024)) && (
          <div className="lg:col-span-5 flex flex-col h-full gap-3 sm:gap-4 min-h-0 overflow-hidden">
            
            {/* Zona e Ngarkimit (Fikse lart) */}
            <div className="glass-panel p-3.5 sm:p-4 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm shrink-0 space-y-2">
              <div className="flex items-center justify-between border-b border-main pb-1.5">
                <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                  <FileText size={15} className="text-primary-start" /> Administrimi i Shkresave
                </h3>
                <span className="text-[10px] font-mono text-text-muted">Vision OCR</span>
              </div>

              <div
                onClick={() => !isUploading && fileInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (!isUploading) handleUploadFiles(e.dataTransfer.files);
                }}
                className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-xl sm:rounded-2xl p-3 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-1"
              >
                {isUploading ? (
                  <div className="flex flex-col items-center justify-center gap-1.5 py-1">
                    <Loader2 size={18} className="animate-spin text-primary-start" />
                    <span className="text-xs font-bold text-primary-start">{uploadProgressText}</span>
                  </div>
                ) : (
                  <>
                    <div className="w-8 h-8 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                      <UploadCloud size={16} />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-text-primary">Kliko ose tërhiq shkresat</p>
                      <p className="text-[10px] text-text-muted">PDF, DOCX, Skanime me AI</p>
                    </div>
                  </>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => handleUploadFiles(e.target.files)}
              />
            </div>

            {/* Lista e Shkresave (Flex-1 me Scroll të Pavarur) */}
            <div className="glass-panel p-3.5 sm:p-4 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm flex-1 min-h-0 flex flex-col gap-2.5 overflow-hidden">
              <div className="flex items-center justify-between gap-2 shrink-0">
                <div className="relative flex-1">
                  <Search size={13} className="absolute left-3 top-2.5 text-text-muted" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Filtro shkresat..."
                    className="w-full bg-surface border border-main rounded-xl pl-8 pr-3 py-1.5 text-xs text-text-primary focus:outline-none focus:border-primary-start"
                  />
                </div>
                <button
                  onClick={() => loadDocuments(false)}
                  title="Rifresko listën"
                  className="p-1.5 bg-surface hover:bg-hover border border-main rounded-xl text-text-muted hover:text-text-primary transition-colors cursor-pointer shrink-0"
                >
                  <RefreshCw size={13} className={loadingDocs ? 'animate-spin' : ''} />
                </button>
              </div>

              <div className="space-y-2 flex-1 min-h-0 overflow-y-auto custom-finance-scroll pr-1">
                {filteredDocs.length === 0 ? (
                  <div className="text-center py-12 text-xs text-text-muted">
                    {loadingDocs ? 'Duke ngarkuar shkresat...' : 'Nuk u gjet asnjë shkresë.'}
                  </div>
                ) : (
                  filteredDocs.map((doc) => {
                    const isSelected = doc.id === selectedDocId;
                    const isDeleting = doc.id === deletingDocId;
                    const isArchiving = doc.id === archivingDocId;
                    const isArchived = doc.status === 'ARCHIVED';
                    const isTextLoading = doc.id === loadingTextDocId;
                    const isProcessing = doc.status === 'PROCESSING' || doc.status === 'UPLOADING';
                    const isMedia = doc.media_type === 'audio' || doc.media_type === 'video' || doc.media_type === 'image';

                    return (
                      <div
                        key={doc.id}
                        // E RËNDËSISHME: TOGGLE DESELECT NËSE KLIKOHET PËRSËRI DOKUMENTI I NJËJTË
                        onClick={() => handleToggleSelectDoc(doc.id)}
                        className={`p-2.5 rounded-xl sm:rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-2 ${
                          isSelected
                            ? 'bg-primary-start/15 border-primary-start text-primary-start shadow-sm ring-1 ring-primary-start/30'
                            : 'bg-surface border-main hover:border-primary-start/40 text-text-primary'
                        } ${isArchived ? 'opacity-60' : ''}`}
                      >
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <div className={`p-1.5 rounded-xl shrink-0 ${isSelected ? 'bg-primary-start text-white' : 'bg-surface/80 text-text-muted'}`}>
                            {isMedia ? <Play size={14} /> : <FileText size={14} />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-bold truncate text-xs text-text-primary">
                              {doc.file_name}
                            </p>
                            <div className="flex items-center gap-1 mt-0.5">
                              {isProcessing ? (
                                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-amber-500/15 text-amber-500 text-[9px] font-mono font-bold animate-pulse">
                                  <Loader2 size={9} className="animate-spin" /> Procesim...
                                </span>
                              ) : (
                                <span className="text-[10px] font-mono text-emerald-500 font-semibold">
                                  ✓ E Procesuar
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-0.5 shrink-0">
                          {isMedia ? (
                            <button
                              type="button"
                              onClick={(e) => handleViewMediaDocument(doc, e)}
                              title="Luaj"
                              className="p-1 text-text-muted hover:text-blue-500 rounded-lg hover:bg-blue-500/10 transition-colors cursor-pointer"
                            >
                              <Play size={13} />
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) => handleViewDocument(doc, e)}
                              title="Shiko origjinalin"
                              className="p-1 text-text-muted hover:text-blue-500 rounded-lg hover:bg-blue-500/10 transition-colors cursor-pointer"
                            >
                              <Eye size={13} />
                            </button>
                          )}

                          {!isMedia && (
                            <button
                              type="button"
                              onClick={(e) => handleViewExtractedText(doc, e)}
                              disabled={isTextLoading}
                              title="Shiko tekstin"
                              className={`p-1 rounded-lg transition-colors cursor-pointer disabled:opacity-40 ${
                                isProcessing 
                                  ? 'text-amber-500 hover:bg-amber-500/10' 
                                  : 'text-text-muted hover:text-emerald-500 hover:bg-emerald-500/10'
                              }`}
                            >
                              {isTextLoading ? <Loader2 size={13} className="animate-spin text-emerald-500" /> : <FileSearch size={13} />}
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setRenameDocId(doc.id);
                              setRenameDocName(doc.file_name);
                            }}
                            title="Riemërto"
                            className="hidden sm:inline-flex p-1 text-text-muted hover:text-amber-500 rounded-lg hover:bg-amber-500/10 transition-colors cursor-pointer"
                          >
                            <Pencil size={13} />
                          </button>

                          <button
                            type="button"
                            onClick={(e) => handleArchiveDocument(doc, e)}
                            disabled={isArchiving || isArchived}
                            title="Arkivo"
                            className="hidden sm:inline-flex p-1 text-text-muted hover:text-purple-500 rounded-lg hover:bg-purple-500/10 transition-colors cursor-pointer disabled:opacity-40"
                          >
                            {isArchiving ? <Loader2 size={13} className="animate-spin text-purple-500" /> : <Archive size={13} />}
                          </button>

                          <button
                            type="button"
                            onClick={(e) => handleDeleteDocument(doc.id, doc.file_name, e)}
                            disabled={isDeleting}
                            title="Fshi"
                            className="p-1 text-text-muted hover:text-rose-500 rounded-lg hover:bg-rose-500/10 transition-colors cursor-pointer disabled:opacity-40"
                          >
                            {isDeleting ? <Loader2 size={13} className="animate-spin text-rose-500" /> : <Trash2 size={13} />}
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        )}

        {/* KOLONA E DJATHTË: CHAT TERMINAL (7 Kolona në Desktop - Simetrik & Bounded) */}
        {(!isFullscreenChat && (mobileTab === 'CHAT' || window.innerWidth >= 1024)) || isFullscreenChat ? (
          <div className={`${isFullscreenChat ? 'lg:col-span-12' : 'lg:col-span-7'} glass-panel rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm flex flex-col h-full min-h-0 overflow-hidden transition-all duration-300 relative`}>
            
            {/* HEADER I PASTËR DHE MINIMALIST (PA 'TERMINALI HETIMOR' DHE PA 'SONNET 4.6') */}
            <div className="px-3 sm:px-4 py-2 border-b border-main bg-surface/90 shrink-0 flex items-center justify-between gap-2 min-h-[44px]">
              
              {/* Informacioni i Dokumentit Aktiv OSE Fashikullit të Plotë */}
              <div className="flex items-center gap-2 min-w-0 flex-1">
                {activeDoc ? (
                  <div className="flex items-center gap-1.5 min-w-0 bg-primary-start/10 border border-primary-start/20 px-2.5 py-1 rounded-xl">
                    <FileText size={13} className="text-primary-start shrink-0" />
                    <span className="text-[11px] text-text-muted shrink-0 font-medium">Dokument:</span>
                    <span className="text-xs font-bold text-primary-start truncate font-mono">{activeDoc.file_name}</span>
                    {/* BUTONI X PËR T'U KTHYER NË GJENDJEN NEUTRALE (FASHIKULLI I PLOTË) */}
                    <button
                      type="button"
                      onClick={() => setSelectedDocId(null)}
                      className="ml-1 p-0.5 text-text-muted hover:text-rose-500 rounded hover:bg-rose-500/10 transition-colors cursor-pointer"
                      title="Kthehu te Fashikulli i Plotë (Çzgjidh)"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-1.5 min-w-0 px-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                    <span className="text-xs font-bold text-text-primary truncate font-mono">
                      Fashikulli i Plotë: {clientName} ({documents.length} shkresa)
                    </span>
                  </div>
                )}
              </div>

              {/* BUTONAT E VEPRIMIT NË HEADER */}
              <div className="flex items-center gap-1.5 shrink-0">
                
                {/* Butoni Dinamik: "Analizo Dokumentin" (nëse ka dok) ose "Analizo Fashikullin" (nëse neutral) */}
                <button
                  type="button"
                  onClick={handleQuickAction}
                  disabled={isProcessing}
                  className="h-7 px-2.5 bg-primary-start hover:brightness-110 text-white rounded-lg text-[11px] font-bold uppercase tracking-wider flex items-center gap-1 shadow-sm transition-all cursor-pointer disabled:opacity-40"
                  title={activeDoc ? "Analizo këtë dokument" : "Analizo dhe kryqëzo gjithë fashikullin"}
                >
                  <Sparkles size={12} className={isProcessing ? 'animate-spin' : ''} />
                  <span>{activeDoc ? 'Analizo Dokumentin' : 'Analizo Fashikullin'}</span>
                </button>

                {/* Kontrolli i Madhësisë së Shkrimit */}
                <div className="flex items-center gap-0.5 rounded-lg border border-main bg-surface p-0.5">
                  <button
                    type="button"
                    onClick={handleDecreaseFont}
                    disabled={fontLevelIndex === 0}
                    className="h-6 w-6 rounded text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30 cursor-pointer flex items-center justify-center"
                    title="Zvogëlo shkrimin"
                  >
                    A−
                  </button>
                  <button
                    type="button"
                    onClick={handleResetFont}
                    title="Rivendos madhësinë"
                    className="min-w-6 text-[10px] font-bold text-text-muted hover:bg-hover rounded text-center px-1 h-6 flex items-center justify-center"
                  >
                    {activeFont.label}
                  </button>
                  <button
                    type="button"
                    onClick={handleIncreaseFont}
                    disabled={fontLevelIndex === FONT_LEVELS.length - 1}
                    className="h-6 w-6 rounded text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30 cursor-pointer flex items-center justify-center"
                    title="Zmadho shkrimin"
                  >
                    A+
                  </button>
                </div>

                {/* Butoni i Pastrimit të Bisedës */}
                <button
                  type="button"
                  onClick={handleClearChat}
                  disabled={messages.length === 0 || isProcessing || isPurging}
                  className="p-1.5 rounded-lg text-text-muted hover:text-rose-500 hover:bg-rose-500/10 transition-colors cursor-pointer disabled:opacity-30"
                  title="Fshi bisedën"
                >
                  {isPurging ? <Loader2 size={14} className="animate-spin text-rose-500" /> : <Trash2 size={14} />}
                </button>

                {/* Fullscreen Toggle */}
                <button
                  type="button"
                  onClick={() => setIsFullscreenChat(!isFullscreenChat)}
                  className="hidden md:flex p-1.5 text-text-muted hover:text-text-primary hover:bg-hover rounded-lg transition-colors cursor-pointer"
                  title={isFullscreenChat ? "Zvogëlo" : "Fullscreen"}
                >
                  {isFullscreenChat ? <Minimize2 size={14} /> : <Maximize2 size={15} />}
                </button>
              </div>
            </div>

            {/* MESSAGE STREAM AREA: SCROLL I PLOTË DHE I PAVARUR BRENDA KUTISË */}
            <div className="flex-1 min-h-0 overflow-y-auto p-3.5 sm:p-4 custom-finance-scroll space-y-3.5 bg-canvas/20 select-text">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-4 my-auto space-y-2.5">
                  <div className="w-12 h-12 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center border border-primary-start/20 shadow-inner">
                    <BrainCircuit size={24} />
                  </div>
                  <div className="max-w-md">
                    <h4 className="text-xs sm:text-sm font-black uppercase tracking-tight text-text-primary">
                      Studio Hetimore e Integruar
                    </h4>
                    <p className="text-[11px] text-text-muted mt-1 leading-relaxed">
                      {activeDoc ? (
                        <span>Jeni duke analizuar shkresën <strong className="text-primary-start">{activeDoc.file_name}</strong>. Klikoni <strong>"Analizo Dokumentin"</strong> ose shtroni pyetje më poshtë.</span>
                      ) : (
                        <span>Fashikulli me të gjitha <strong>{documents.length} shkresat</strong> është gati. Klikoni <strong>"Analizo Fashikullin"</strong> për kryqëzim të plotë, ose zgjidhni një shkresë majtas.</span>
                      )}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3.5">
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

            {/* INPUT TERMINAL BAR (Fiks në fund me fushë të zgjuar dinamike) */}
            <div className="p-2.5 sm:p-3 bg-surface border-t border-main shrink-0">
              
              {attachedFile && (
                <div className="flex items-center gap-1.5 px-2.5 py-1 mb-1.5 bg-primary-start/15 border border-primary-start/40 rounded-lg text-xs text-text-primary w-fit">
                  <Paperclip size={12} className="text-primary-start shrink-0" />
                  <span className="font-bold truncate max-w-[180px] text-[11px]">{attachedFile.name}</span>
                  <button
                    type="button"
                    onClick={() => setAttachedFile(null)}
                    className="p-0.5 text-text-muted hover:text-rose-500"
                  >
                    <X size={11} />
                  </button>
                </div>
              )}

              <input
                type="file"
                ref={chatFileInputRef}
                onChange={handleChatFileChange}
                accept=".pdf,.docx,.doc,.txt,.xlsx,.xls,.csv,.mp3,.wav,.m4a,image/*"
                className="hidden"
              />

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendChatMessage(input);
                }}
                className="flex items-end gap-2 bg-canvas border border-main rounded-xl p-1.5 focus-within:border-primary-start/50 transition-colors shadow-xs"
              >
                <button
                  type="button"
                  onClick={() => chatFileInputRef.current?.click()}
                  disabled={isProcessing || isUploadingChatDoc}
                  className={`p-1.5 rounded-lg transition-all cursor-pointer mb-0.5 shrink-0 ${
                    attachedFile
                      ? 'bg-primary-start text-white'
                      : 'text-text-muted hover:text-primary-start hover:bg-primary-start/10'
                  }`}
                  title="Bashkëngjit provë"
                >
                  <Paperclip size={15} />
                </button>

                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={handleInputChange}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendChatMessage(input);
                    }
                  }}
                  placeholder={
                    isUploadingChatDoc
                      ? chatUploadStatusText
                      : attachedFile
                      ? `Shtoni pyetje për ${attachedFile.name}...`
                      : activeDoc
                      ? `Pyet për "${activeDoc.file_name}" (ose kliko '✕' lart për gjithë dosjen)...`
                      : `Pyet mbi të gjithë fashikullin (${documents.length} shkresa të lidhura)...`
                  }
                  className="forensic-integrated-textarea flex-1 p-1 bg-transparent text-xs sm:text-sm text-text-primary placeholder:text-text-disabled focus:outline-none resize-none min-h-[38px] max-h-[140px] border-0 outline-none"
                  rows={1}
                />

                <button
                  type="submit"
                  disabled={(!input.trim() && !attachedFile) || isProcessing || isUploadingChatDoc}
                  className="h-8 w-8 bg-primary-start text-white rounded-lg shadow-sm flex items-center justify-center hover:brightness-110 active:scale-95 transition-all disabled:opacity-30 disabled:cursor-not-allowed shrink-0 cursor-pointer mb-0.5"
                  title="Dërgo"
                >
                  {isProcessing || isUploadingChatDoc ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Send size={14} className="ml-0.5" />
                  )}
                </button>
              </form>
            </div>
          </div>
        ) : null}
      </div>

      {/* Modal i Leximit të Tekstit të Ekstraktuar */}
      {extractedModalData && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6">
          <div className="relative w-full max-w-5xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col h-[88vh] animate-in fade-in duration-200">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/90 shrink-0">
              <div className="flex items-center gap-2.5">
                <FileText size={18} className="text-emerald-500" />
                <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 truncate">
                  {extractedModalData.docName}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard.writeText(extractedModalData.text);
                    setCopiedExtractedText(true);
                    setTimeout(() => setCopiedExtractedText(false), 2000);
                  }}
                  className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs font-bold flex items-center gap-1.5 cursor-pointer"
                >
                  {copiedExtractedText ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                  <span>{copiedExtractedText ? 'U Kopjua!' : 'Kopjo'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setExtractedModalData(null)}
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto custom-finance-scroll bg-white dark:bg-slate-950 flex-1 select-text">
              <pre className="whitespace-pre-wrap font-sans text-xs sm:text-sm text-slate-800 dark:text-slate-200">
                {extractedModalData.text}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Shikuesi PDF */}
      {viewingDoc && (
        <PDFViewerModal
          documentData={viewingDoc as any}
          caseId={caseId}
          onClose={() => { setViewingDoc(null); setViewingUrl(null); }}
          onMinimize={() => {}}
          t={t}
          directUrl={viewingUrl}
          isAuth={true}
          initialPage={1}
        />
      )}

      {/* Modali i Riemërtimit */}
      <RenameDocumentModal
        isOpen={!!renameDocId}
        onClose={() => { setRenameDocId(null); setRenameDocName(''); }}
        onRename={handleConfirmRename}
        currentName={renameDocName}
        t={t}
      />
    </div>
  );
};

export default DocumentForensicLab;