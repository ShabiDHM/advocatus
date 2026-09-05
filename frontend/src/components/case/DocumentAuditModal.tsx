// FILE: frontend/src/components/case/DocumentAuditModal.tsx
// PHOENIX PROTOCOL - 3-PILLAR SINGLE-DOCUMENT FORENSIC AUDIT MODAL V15.0 (STRICT ANTI-ABUSE TOKEN BARRIER)
// ZERO TS WARNINGS • AUTO-LOAD FROM MONGO • NO ARBITRARY RE-RUN • 100% COMPLETE CODE

import React, { useState, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Scale, X, Copy, Save, CheckCircle2, 
  Loader2, Maximize2, Minimize2, Trash2, ZoomIn, ZoomOut, ArrowDown,
  Building2, Swords, Play, RefreshCw, FileSearch, AlertCircle
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { forensicService } from '../../services/forensicService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

export type DocPillarType = 'DOC_PILLAR_1' | 'DOC_PILLAR_2' | 'DOC_PILLAR_3';

interface DocumentAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  documentId: string;
  documentName: string;
  clientName?: string;
  initialPillars?: Record<string, string>;
  isAnalysisDirty?: boolean;
  onDeleteAudit?: () => Promise<void> | void;
}

const FONT_LEVELS = [
  { label: '85%', base: 13.5, h1: 19, h2: 16.5, h3: 14.5, line: 1.55 },
  { label: '100%', base: 15, h1: 21, h2: 18, h3: 16, line: 1.65 },
  { label: '115%', base: 16.5, h1: 23, h2: 19.5, h3: 17.5, line: 1.75 },
  { label: '130%', base: 18.5, h1: 26, h2: 21.5, h3: 19, line: 1.8 },
  { label: '150%', base: 21, h1: 29, h2: 24, h3: 21, line: 1.85 }
];

const DOC_PILLAR_CONFIGS: Record<DocPillarType, { title: string; subtitle: string; icon: any; getPrompt: (docName: string) => string }> = {
  DOC_PILLAR_1: {
    title: '1. Ekzaminimi & Faktet',
    subtitle: 'Pasaporta Procedurale, Struktura e Palëve & Baza Provuese e Administruar',
    icon: Building2,
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE E DOKUMENTIT — SHTJELLA 1: EKZAMINIMI DHE FAKTET]
Kryej autopsinë forenzike të dokumentit "${docName}" ekskluzivisht për SHTJELLËN 1:
- Seksioni 1: Pasaporta Procedurale dhe Diagnoza Juridike (Lloji i aktit, Organi nxjerrës, Numri i protokollit, Afatet ligjore prekluzive të atakimit).
- Seksioni 2: Struktura e Palëve dhe Legjitimiteti Procedural (Parashtruesi, Pala Kundërshtare, Interesi Juridik).
- Seksioni 3: Kryqëzimi Forenzik i Fakteve dhe Baza Provuese e Administruar (Faktet thelbësore, Provat materiale, Boshllëqet provuese).
Ofro analizë shteruese, të thellë doktrinare dhe pa shkurtime.`
  },
  DOC_PILLAR_2: {
    title: '2. Nenet & Shkeljet',
    subtitle: 'Tabela Shteruese e Neneve të Kosovës & Detektori i Shkeljeve/Lapsuseve',
    icon: Scale,
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE E DOKUMENTIT — SHTJELLA 2: NENET DHE SHKELJET]
Kryej autopsinë forenzike të dokumentit "${docName}" ekskluzivisht për SHTJELLËN 2:
- Seksioni 4: Tabela Shteruese e Dispozitave Ligjore të Kosovës dhe Precedentëve të Gjykatës Supreme (Çdo nen të formatohet ekzaktësisht "Neni X i [Ligjit]" për verifikim 1-klikim me precedentin përkatës PML ose Revizion).
- Seksioni 5: Gjetjet Kritike, Shkeljet Thelbësore të Procedurës (Neni 182 LPK / KPK) dhe Detektori i Pasaktësive/Lapsuseve me Tabelën e Zëvendësimit Ligjor.
Gjenero tabelat e plota dhe arsyetimin doktrinar të shkallës më të lartë.`
  },
  DOC_PILLAR_3: {
    title: '3. Kundërshtimet & Plani',
    subtitle: 'Auditimi i Kërkesës, Diagnoza Korrigjuese & Master Plani i Veprimit',
    icon: Swords,
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE E DOKUMENTIT — SHTJELLA 3: KUNDËRSHTIMET DHE PLANI]
Kryej autopsinë forenzike të dokumentit "${docName}" ekskluzivisht për SHTJELLËN 3:
- Seksioni 6: Auditimi i Kërkesës, Vlerësimi i Rreziqeve Procedurale dhe Forca Ekzekutive e Aktit.
- Seksioni 7: Diagnoza Korrigjuese dhe Rekomandimet e Drejtpërdrejta Taktike mbi Goditjen e Shkresës (Prapësime, Ankesa, Kundërshtime Ekspertize).
- Seksioni 8: Master Plani i Veprimit me Hapat Proceduralë dhe Afatet e Prera Ligjore (Hapi 1 Urgjenca, Hapi 2 Plotësimi, Hapi 3 Mbrojtja).
Ofro strategji agresive dhe taktike të fitores ligjore.`
  }
};

export const DocumentAuditModal: React.FC<DocumentAuditModalProps> = ({
  isOpen,
  onClose,
  caseId,
  documentId,
  documentName,
  clientName = 'Klienti',
  initialPillars = {},
  isAnalysisDirty = false,
  onDeleteAudit,
}) => {
  const [activePillar, setActivePillar] = useState<DocPillarType>('DOC_PILLAR_1');

  // Gjendja e 3 Shtjellave (Ngarkohet direkt nga MongoDB)
  const [pillarResults, setPillarResults] = useState<Record<DocPillarType, string>>({
    DOC_PILLAR_1: initialPillars.DOC_PILLAR_1 || initialPillars.PILLAR_1 || '',
    DOC_PILLAR_2: initialPillars.DOC_PILLAR_2 || initialPillars.PILLAR_2 || '',
    DOC_PILLAR_3: initialPillars.DOC_PILLAR_3 || initialPillars.PILLAR_3 || ''
  });

  const [loadingPillars, setLoadingPillars] = useState<Record<DocPillarType, boolean>>({
    DOC_PILLAR_1: false,
    DOC_PILLAR_2: false,
    DOC_PILLAR_3: false
  });

  const [copied, setCopied] = useState<boolean>(false);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveSuccess, setArchiveSuccess] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState<boolean>(false);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUpRef = useRef<boolean>(false);

  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_doc_audit_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 2;
    } catch {
      return 2;
    }
  });

  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);

  // BARIERA E KURSIMIT: Ngarkim në 0ms nga MongoDB kur hapet modali i dokumentit
  useEffect(() => {
    if (isOpen && documentId) {
      if (initialPillars && Object.keys(initialPillars).length > 0) {
        setPillarResults({
          DOC_PILLAR_1: initialPillars.DOC_PILLAR_1 || initialPillars.PILLAR_1 || '',
          DOC_PILLAR_2: initialPillars.DOC_PILLAR_2 || initialPillars.PILLAR_2 || '',
          DOC_PILLAR_3: initialPillars.DOC_PILLAR_3 || initialPillars.PILLAR_3 || ''
        });
      } else if (caseId) {
        apiService.getDocument(caseId, documentId).then((doc: any) => {
          if (doc?.forensic_pillars) {
            setPillarResults({
              DOC_PILLAR_1: doc.forensic_pillars.DOC_PILLAR_1 || doc.forensic_pillars.PILLAR_1 || '',
              DOC_PILLAR_2: doc.forensic_pillars.DOC_PILLAR_2 || doc.forensic_pillars.PILLAR_2 || '',
              DOC_PILLAR_3: doc.forensic_pillars.DOC_PILLAR_3 || doc.forensic_pillars.PILLAR_3 || ''
            });
          }
        }).catch(() => {});
      }
    }
  }, [isOpen, documentId, caseId, initialPillars]);

  const currentContent = pillarResults[activePillar] || '';
  const isCurrentLoading = loadingPillars[activePillar];
  const autoLinkedContent = useMemo(() => autoLinkLegalCitations(currentContent), [currentContent]);

  const handleGeneratePillar = async (pillar: DocPillarType) => {
    if (!caseId || !documentId || loadingPillars[pillar]) return;

    setLoadingPillars((prev) => ({ ...prev, [pillar]: true }));
    setPillarResults((prev) => ({ ...prev, [pillar]: '' }));

    try {
      const prompt = DOC_PILLAR_CONFIGS[pillar].getPrompt(documentName);
      const stream = apiService.sendChatMessageStream(
        caseId,
        prompt,
        [documentId],
        'ks',
        'DEEP',
        'document',
        false // PHOENIX FIX: Izolim absolut nga Chat-i
      );

      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        const currentAcc = accumulated;
        setPillarResults((prev) => ({ ...prev, [pillar]: currentAcc }));
      }

      // PERSISTENCA NË MONGO ATLAS: Ruan menjëherë shtjellën e dokumentit në bazën e të dhënave
      if (accumulated.trim().length > 50) {
        await forensicService.saveDocumentPillar(caseId, documentId, pillar, accumulated);
      }
    } catch (err) {
      console.error(`Document Pillar Audit Error [${pillar}]:`, err);
      alert(`Ndodhi një gabim gjatë auditimit të ${DOC_PILLAR_CONFIGS[pillar].title}.`);
    } finally {
      setLoadingPillars((prev) => ({ ...prev, [pillar]: false }));
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    const container = scrollContainerRef.current;
    if (!container) return;

    if (!isUserScrolledUpRef.current) {
      container.scrollTop = container.scrollHeight;
    }
  }, [currentContent, isOpen]);

  const handleScroll = () => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    const userScrolledUp = distanceFromBottom > 80;
    isUserScrolledUpRef.current = userScrolledUp;
    setShowScrollBottomBtn(userScrolledUp);
  };

  const scrollToBottom = () => {
    const container = scrollContainerRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
    isUserScrolledUpRef.current = false;
    setShowScrollBottomBtn(false);
  };

  if (!isOpen) return null;

  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleDecreaseFont = () => {
    setFontLevelIndex((prev) => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_doc_audit_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleIncreaseFont = () => {
    setFontLevelIndex((prev) => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_doc_audit_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(2);
    try { localStorage.setItem('juristi_doc_audit_font_size', '2'); } catch {}
  };

  const handleCopy = () => {
    if (!currentContent) return;
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleArchive = async () => {
    if (!caseId || !currentContent) return;
    setIsArchiving(true);
    setArchiveSuccess(false);
    try {
      const archiveTitle = `${DOC_PILLAR_CONFIGS[activePillar].title} - ${documentName}`;
      await apiService.archiveForensicReport(caseId, archiveTitle, currentContent);
      setArchiveSuccess(true);
      setTimeout(() => setArchiveSuccess(false), 3000);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Dështoi ruajtja në arkiv.");
    } finally {
      setIsArchiving(false);
    }
  };

  const handleDeleteAudit = async () => {
    if (!caseId || !documentId) return;
    if (!window.confirm(`A jeni i sigurt që doni të fshini auditimin e dokumentit "${documentName}" nga MongoDB?`)) return;

    setIsDeleting(true);
    try {
      setPillarResults({ DOC_PILLAR_1: '', DOC_PILLAR_2: '', DOC_PILLAR_3: '' });
      if (onDeleteAudit) {
        await onDeleteAudit();
      }
    } catch (err: any) {
      console.error("Failed to delete audit:", err);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/85 backdrop-blur-md flex items-center justify-center z-[250] p-0 sm:p-3 md:p-6 select-none">
        <motion.div
          initial={{ opacity: 0, scale: 0.98, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.98, y: 10 }}
          className={`glass-panel w-full ${
            isFullscreen 
              ? 'h-full max-h-screen rounded-none border-0' 
              : 'h-full sm:h-[94vh] max-w-6xl sm:max-h-[960px] rounded-none sm:rounded-3xl border-0 sm:border sm:border-main'
          } p-3 sm:p-5 md:p-7 shadow-2xl bg-card flex flex-col transition-all duration-200 relative overflow-hidden`}
          style={{ backgroundColor: 'var(--bg-card, #ffffff)' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-3 sm:pb-4 border-b border-main shrink-0 gap-2">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-primary-start/15 text-primary-start rounded-xl sm:rounded-2xl flex items-center justify-center border border-primary-start/30 shrink-0 shadow-xs">
                <FileSearch className="w-4 h-4 sm:w-5 sm:h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-xs sm:text-sm md:text-base font-black text-text-primary uppercase tracking-tight truncate leading-tight">
                    Auditimi Forenzik i Shkresës
                  </h3>
                  {isAnalysisDirty && (
                    <span className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-[10px] font-bold uppercase flex items-center gap-1 shrink-0 animate-pulse">
                      <AlertCircle size={11} /> Shkresë e Përditësuar
                    </span>
                  )}
                </div>
                <p className="text-[10px] sm:text-xs text-text-muted font-medium truncate mt-0.5 font-mono">
                  {documentName} <span className="opacity-60">•</span> {clientName}
                </p>
              </div>
            </div>

            {/* Kontrollet */}
            <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">
              <div className="flex items-center bg-surface border border-main rounded-lg sm:rounded-xl p-0.5 text-xs shadow-inner">
                <button
                  type="button"
                  onClick={handleDecreaseFont}
                  disabled={fontLevelIndex <= 0}
                  className="p-1 sm:px-2 sm:py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-md hover:bg-hover transition-colors font-bold flex items-center cursor-pointer"
                  title="Zvogëlo Tekstin (A-)"
                >
                  <ZoomOut className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                  <span className="hidden sm:inline ml-0.5">A-</span>
                </button>
                <button
                  type="button"
                  onClick={handleResetFont}
                  className="px-1.5 sm:px-2 py-0.5 sm:py-1 text-[10px] sm:text-[11px] font-mono font-bold text-primary-start hover:text-primary-end rounded-md hover:bg-hover transition-colors cursor-pointer"
                  title="Rivendos Madhësinë"
                >
                  {activeFont.label}
                </button>
                <button
                  type="button"
                  onClick={handleIncreaseFont}
                  disabled={fontLevelIndex >= FONT_LEVELS.length - 1}
                  className="p-1 sm:px-2 sm:py-1 text-text-muted hover:text-text-primary disabled:opacity-30 rounded-md hover:bg-hover transition-colors font-bold flex items-center cursor-pointer"
                  title="Zmadho Tekstin (A+)"
                >
                  <span className="hidden sm:inline mr-0.5">A+</span>
                  <ZoomIn className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                </button>
              </div>

              {/* Koshi shfaqet VETËM nëse përcillet onDeleteAudit (Admin Only) */}
              {onDeleteAudit && (
                <button
                  type="button"
                  onClick={handleDeleteAudit}
                  disabled={isDeleting}
                  className="p-1.5 sm:p-2 text-text-muted hover:text-rose-600 hover:bg-rose-500/10 rounded-lg sm:rounded-xl transition-colors cursor-pointer"
                  title="Pastro Auditimin nga MongoDB"
                >
                  {isDeleting ? <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin text-rose-500" /> : <Trash2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
                </button>
              )}

              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="hidden sm:flex p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                title={isFullscreen ? "Zvogëlo" : "Zmadho Ekranin"}
              >
                {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>

              <button
                type="button"
                onClick={onClose}
                className="p-1.5 sm:p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-lg sm:rounded-xl transition-colors cursor-pointer"
                title="Mbyll"
              >
                <X className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          </div>

          {/* VETËM 3 SHTJELLAT E DOKUMENTIT (3-PILLAR SWITCHER) */}
          <div className="pt-2.5 pb-1 grid grid-cols-3 gap-1.5 sm:gap-2 shrink-0">
            {(Object.keys(DOC_PILLAR_CONFIGS) as DocPillarType[]).map((pillarKey) => {
              const cfg = DOC_PILLAR_CONFIGS[pillarKey];
              const IconComp = cfg.icon;
              const isSelected = activePillar === pillarKey;
              const hasContent = Boolean(pillarResults[pillarKey]?.trim());
              const isLoading = loadingPillars[pillarKey];

              return (
                <button
                  key={pillarKey}
                  type="button"
                  onClick={() => setActivePillar(pillarKey)}
                  className={`px-2.5 sm:px-3 py-2 rounded-xl text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer border ${
                    isSelected
                      ? pillarKey === 'DOC_PILLAR_1'
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                        : pillarKey === 'DOC_PILLAR_2'
                        ? 'bg-amber-600 text-white border-amber-600 shadow-sm'
                        : 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                      : 'bg-surface hover:bg-hover text-text-muted border-main'
                  }`}
                >
                  {isLoading ? (
                    <Loader2 size={13} className="animate-spin text-white" />
                  ) : (
                    <IconComp size={13} className={isSelected ? 'text-white' : 'text-text-muted'} />
                  )}
                  <span className="truncate">{cfg.title}</span>
                  {hasContent && !isLoading && (
                    <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-white' : 'bg-status-success'}`} title="E ruajtur në MongoDB" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Shiriti Nën-Titull & Përditësimi VETËM NËSE KA NDRYSHIM */}
          <div className="py-1 px-1 flex items-center justify-between gap-2 shrink-0 text-text-muted text-[11px]">
            <p className="truncate font-medium">{DOC_PILLAR_CONFIGS[activePillar].subtitle}</p>
            {currentContent && !isCurrentLoading && isAnalysisDirty && (
              <button
                type="button"
                onClick={() => handleGeneratePillar(activePillar)}
                className="px-2 py-0.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-bold flex items-center gap-1 cursor-pointer shrink-0 transition-all"
                title="Shkresa është përditësuar. Klikoni për të rifreskuar këtë shtjellë!"
              >
                <RefreshCw size={11} className="animate-spin" />
                <span>Përditëso Shtjellën</span>
              </button>
            )}
          </div>

          {/* Trupi i Auditimit me Markdown Renderer */}
          <div 
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto overflow-x-hidden custom-finance-scroll p-3 sm:p-6 md:p-8 my-1 bg-surface/40 rounded-xl sm:rounded-2xl border border-main text-text-primary shadow-inner select-text relative touch-pan-y flex flex-col"
          >
            <style>{`
              .doc-audit-report p,
              .doc-audit-report li,
              .doc-audit-report span:not(.lucide) {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .doc-audit-report td {
                font-size: ${Math.max(11.5, activeFont.base - 1.5)}px !important;
                line-height: 1.45 !important;
                padding: 6px 8px !important;
              }
              .doc-audit-report th {
                font-size: ${Math.max(11, activeFont.base - 2)}px !important;
                padding: 8px 8px !important;
              }
              .doc-audit-report h1 {
                font-size: ${activeFont.h1}px !important;
                line-height: 1.25 !important;
                margin-top: 1.2em !important;
                margin-bottom: 0.5em !important;
              }
              .doc-audit-report h2 {
                font-size: ${activeFont.h2}px !important;
                line-height: 1.3 !important;
                margin-top: 1.1em !important;
                margin-bottom: 0.4em !important;
              }
              .doc-audit-report h3 {
                font-size: ${activeFont.h3}px !important;
                line-height: 1.35 !important;
                margin-top: 0.9em !important;
                margin-bottom: 0.3em !important;
              }
              .doc-audit-report table {
                display: block !important;
                width: 100% !important;
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch !important;
                margin: 1em 0 !important;
              }
            `}</style>

            {!currentContent && !isCurrentLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto">
                <div className="w-14 h-14 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center mb-4 border border-primary-start/20">
                  {React.createElement(DOC_PILLAR_CONFIGS[activePillar].icon, { size: 28 })}
                </div>
                <h4 className="text-sm sm:text-base font-black uppercase tracking-tight text-text-primary mb-1">
                  {DOC_PILLAR_CONFIGS[activePillar].title}
                </h4>
                <p className="text-xs text-text-muted max-w-md mb-6 leading-relaxed">
                  {DOC_PILLAR_CONFIGS[activePillar].subtitle}. Kjo shtjellë nuk është analizuar ende për këtë shkresë.
                </p>
                <button
                  type="button"
                  onClick={() => handleGeneratePillar(activePillar)}
                  className="px-6 py-3 bg-primary-start hover:brightness-110 text-white rounded-xl font-bold text-xs uppercase tracking-wider shadow-lg shadow-primary-start/20 flex items-center gap-2 cursor-pointer transition-all hover-lift"
                >
                  <Play size={14} className="fill-white" />
                  <span>Analizo {DOC_PILLAR_CONFIGS[activePillar].title}</span>
                </button>
              </div>
            ) : isCurrentLoading && !currentContent ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 my-auto">
                <Loader2 className="w-10 h-10 animate-spin text-primary-start mb-3" />
                <p className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Duke analizuar {DOC_PILLAR_CONFIGS[activePillar].title}...
                </p>
                <p className="text-[11px] text-text-muted mt-1">
                  Juristi AI po kryen autopsinë e shkresës "{documentName}".
                </p>
              </div>
            ) : (
              <div className="markdown-content doc-audit-report prose prose-slate dark:prose-invert max-w-none text-text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {autoLinkedContent}
                </ReactMarkdown>
                {isCurrentLoading && (
                  <div className="inline-flex items-center gap-2 mt-4 px-3 py-1.5 rounded-lg bg-primary-start/10 text-primary-start border border-primary-start/20 text-xs font-bold">
                    <Loader2 size={13} className="animate-spin" />
                    <span>Duke gjeneruar rrjedhën doktrinare të shkresës...</span>
                  </div>
                )}
              </div>
            )}
          </div>

          <AnimatePresence>
            {showScrollBottomBtn && (
              <motion.button
                initial={{ opacity: 0, y: 10, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 10, scale: 0.9 }}
                type="button"
                onClick={scrollToBottom}
                className="absolute bottom-16 sm:bottom-20 right-4 sm:right-10 z-20 px-3 py-1.5 sm:px-3.5 sm:py-2 bg-slate-900/90 hover:bg-slate-900 text-white text-[11px] sm:text-xs font-bold rounded-full shadow-2xl border border-slate-700/80 backdrop-blur-md flex items-center gap-1.5 cursor-pointer hover:border-sky-500/50 transition-all"
              >
                <span>Te Fundi</span>
                <ArrowDown className="w-3 h-3 sm:w-3.5 sm:h-3.5 animate-bounce" />
              </motion.button>
            )}
          </AnimatePresence>

          {/* Veprimet: Vetëm Ruajtje në Arkiv dhe Kopjim */}
          <div className="flex items-center justify-between pt-2.5 sm:pt-3 border-t border-main gap-2 sm:gap-3 shrink-0">
            <button
              type="button"
              onClick={handleArchive}
              disabled={isArchiving || !currentContent}
              className="flex-1 sm:flex-initial h-10 px-3 sm:px-5 bg-surface hover:bg-hover border border-main rounded-xl text-[11px] sm:text-xs font-bold uppercase tracking-wider text-primary-start flex items-center justify-center gap-1.5 sm:gap-2 transition-all shadow-sm disabled:opacity-40 cursor-pointer min-h-[40px]"
            >
              {isArchiving ? (
                <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" />
              ) : archiveSuccess ? (
                <CheckCircle2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-status-success" />
              ) : (
                <Save className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              )}
              <span className="truncate">{archiveSuccess ? 'U ruajt!' : 'Ruaj në Arkiv'}</span>
            </button>

            <button
              type="button"
              onClick={handleCopy}
              disabled={!currentContent}
              className="flex-1 sm:flex-initial h-10 px-4 sm:px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-[11px] sm:text-xs uppercase tracking-wider shadow-sm transition-all flex items-center justify-center gap-1.5 sm:gap-2 disabled:opacity-40 cursor-pointer min-h-[40px]"
            >
              <Copy className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> 
              <span className="truncate">{copied ? 'U Kopjua!' : 'Kopjo Shtjellën'}</span>
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default DocumentAuditModal;