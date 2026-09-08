// FILE: frontend/src/components/forensics/DocumentForensicLab.tsx
// PHOENIX PROTOCOL - DUAL FORENSIC AUTOPSY LAB V13.3 (FIXED IMPORTS & T FUNCTION)
// ZERO TS WARNINGS • POWERED BY CLAUDE SONNET 4.6 • 100% COMPLETE CODE

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
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
  ArrowDown,
  Eye,
  Pencil,
  Archive
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTranslation } from 'react-i18next';

import { forensicService } from '../../services/forensicService';
import { forensicDeskService, ForensicDocItem } from '../../services/forensicDeskService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';
import PDFViewerModal from '../FileViewerModal';
import { RenameDocumentModal } from '../case/RenameDocumentModal';
import { apiService, API_V1_URL } from '../../services/api';

export type AutopsyScope = 'DOCUMENT' | 'CASE';
export type PillarType = 'PILLAR_1' | 'PILLAR_2' | 'PILLAR_3';

interface DocumentForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

const FONT_LEVELS = [
  { label: '85%', base: 13.5, h1: 19, h2: 16.5, h3: 14.5, line: 1.55 },
  { label: '100%', base: 15, h1: 21, h2: 18, h3: 16, line: 1.65 },
  { label: '115%', base: 16.5, h1: 23, h2: 19.5, h3: 17.5, line: 1.75 },
  { label: '130%', base: 18.5, h1: 26, h2: 21.5, h3: 19, line: 1.8 },
  { label: '150%', base: 21, h1: 29, h2: 24, h3: 21, line: 1.85 }
];

const DOC_PILLAR_CONFIGS: Record<PillarType, { title: string; subtitle: string; getPrompt: (docName: string) => string }> = {
  PILLAR_1: {
    title: '1. Ekzaminimi & Faktet',
    subtitle: 'Pasaporta Procedurale, Struktura e Palëve & Baza Provuese e Administruar',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 1: EKZAMINIMI DHE FAKTET]
Dokumenti: "${docName}"
DETYRË: Gjenero SHTJELLËN 1 me Claude Sonnet 4.6:
- Seksioni 1: Pasaporta Procedurale dhe Diagnoza Juridike (Lloji i aktit, Organi nxjerrës, Numri, Afatet ligjore).
- Seksioni 2: Struktura e Palëve dhe Legjitimiteti Procedural.
- Seksioni 3: Kryqëzimi Forenzik i Fakteve dhe Baza Provuese e Administruar.
Përgjigju me përpikmëri shkencore dhe nene të sakta të Kosovës.`
  },
  PILLAR_2: {
    title: '2. Nenet & Shkeljet',
    subtitle: 'Tabela e Neneve të Kosovës & Shkeljet Procedurale',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 2: NENET DHE SHKELJET]
Dokumenti: "${docName}"
DETYRË: Gjenero SHTJELLËN 2 me Claude Sonnet 4.6:
- Seksioni 4: Tabela e Neneve të Shkelura sipas Legjislacionit të Kosovës me precedentët e Gjykatës Supreme (PML / Revizion).
- Seksioni 5: Gjetjet Kritike, Shkeljet Thelbësore të Procedurës (Neni 182 LPK / KPK) dhe Detektori i Pasaktësive.
Bazo arsyetimin në legjislacionin pozitiv të Kosovës.`
  },
  PILLAR_3: {
    title: '3. Kundërshtimet & Plani',
    subtitle: 'Auditimi i Kërkesës, Diagnoza Korrigjuese & Master Plani i Veprimit',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 3: KUNDËRSHTIMET DHE PLANI]
Dokumenti: "${docName}"
DETYRË: Gjenero SHTJELLËN 3 me Claude Sonnet 4.6:
- Seksioni 6: Auditimi i Kërkesës, Vlerësimi i Rreziqeve Procedurale dhe Forca Ekzekutive.
- Seksioni 7: Diagnoza Korrigjuese dhe Rekomandimet Taktike mbi Goditjen e Shkresës.
- Seksioni 8: Master Plani i Veprimit me Hapat Proceduralë dhe Afatet e Prera Ligjore.`
  }
};

const CASE_PILLAR_CONFIGS: Record<PillarType, { title: string; subtitle: string; prompt: string }> = {
  PILLAR_1: {
    title: '1. Fakti & Historiku',
    subtitle: 'Diagnoza Fillestare, Kronologjia e Ngjarjeve & Kryqëzimi i Palëve/Dëshmitarëve',
    prompt: `[DIREKTIVË FORENZIKE MASTER — SHTJELLA 1: FAKTI & HISTORIKU]
Gjenero Seksionet 1 dhe 2 për të gjithë fashikullin e lëndës me Claude Sonnet 4.6:
- Seksioni 1: Diagnoza Procedurale dhe Gjendja Faktike e Dosjes.
- Seksioni 2: Rindërtimi Kronologjik i Datave dhe Veprimeve Vendimtare Procedurale.
- Kryqëzimi i Dëshmive, Palëve, Gjyqtarëve dhe Ekspertëve nga provat reale.`
  },
  PILLAR_2: {
    title: '2. Shkeljet & Nenet',
    subtitle: 'Matrica e Provave, Tabela e Neneve të Gjykatës Supreme & Përgjegjësia Penale/Civile',
    prompt: `[DIREKTIVË FORENZIKE MASTER — SHTJELLA 2: SHKELJET & NENET]
Gjenero Seksionet 3, 4 dhe 5 për të gjithë fashikullin me Claude Sonnet 4.6:
- Seksioni 3: Matrica e Provave Materiale dhe Provat Kontradiktore.
- Seksioni 4: Tabela e Nxjerrjes së Neneve të Kosovës (Neni X i [Ligjit]).
- Seksioni 5: Përgjegjësia Ligjore dhe Shkeljet Thelbësore (Neni 182 LPK / KPP).`
  },
  PILLAR_3: {
    title: '3. Plani i Veprimit',
    subtitle: 'Mjetet Juridike, Prapësimet, Kundërshtimet & Master Strategjia e Seancës',
    prompt: `[DIREKTIVË FORENZIKE MASTER — SHTJELLA 3: PLANI I VEPRIMIT]
Gjenero Seksionet 6, 7 dhe 8 për të gjithë fashikullin me Claude Sonnet 4.6:
- Seksioni 6: Përgatitja e Mjeteve Juridike (Ankesa, Prapësime, Padi, Masë Sigurimi).
- Seksioni 7: Pyetësori Taktik për Seancë me Pyetje Kurth.
- Seksioni 8: Master Plani i Veprimit me Afate të Prera.`
  }
};

export const DocumentForensicLab: React.FC<DocumentForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  const { t } = useTranslation();
  const [documents, setDocuments] = useState<ForensicDocItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgressText, setUploadProgressText] = useState<string>('');
  const [deletingDocId, setDeletingDocId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');

  const [autopsyScope, setAutopsyScope] = useState<AutopsyScope>('DOCUMENT');
  const [activePillar, setActivePillar] = useState<PillarType>('PILLAR_1');
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState<boolean>(false);
  const [isDeletingPillars, setIsDeletingPillars] = useState<boolean>(false);

  const [docPillars, setDocPillars] = useState<Record<PillarType, string>>({
    PILLAR_1: '', PILLAR_2: '', PILLAR_3: ''
  });

  const [casePillars, setCasePillars] = useState<Record<PillarType, string>>({
    PILLAR_1: '', PILLAR_2: '', PILLAR_3: ''
  });

  const [loadingPillars, setLoadingPillars] = useState<Record<PillarType, boolean>>({
    PILLAR_1: false, PILLAR_2: false, PILLAR_3: false
  });

  const [copiedReport, setCopiedReport] = useState<boolean>(false);
  const [isArchivingReport, setIsArchivingReport] = useState<boolean>(false);
  const [archiveReportSuccess, setArchiveReportSuccess] = useState<boolean>(false);

  // States for document actions
  const [viewingDoc, setViewingDoc] = useState<ForensicDocItem | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);
  const [renameDocId, setRenameDocId] = useState<string | null>(null);
  const [renameDocName, setRenameDocName] = useState<string>('');
  const [archivingDocId, setArchivingDocId] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledUpRef = useRef<boolean>(false);

  const markdownComponents = useMemo(() => buildMarkdownComponents(), []);
  const activeDoc = useMemo(() => documents.find(d => d.id === selectedDocId), [documents, selectedDocId]);

  const activePillarsMap = autopsyScope === 'DOCUMENT' ? docPillars : casePillars;
  const currentPillarContent = activePillarsMap[activePillar] || '';
  const isCurrentPillarLoading = loadingPillars[activePillar];
  const autoLinkedContent = useMemo(() => autoLinkLegalCitations(currentPillarContent), [currentPillarContent]);

  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_forensic_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 2;
    } catch {
      return 2;
    }
  });

  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleDecreaseFont = () => {
    setFontLevelIndex((prev) => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleIncreaseFont = () => {
    setFontLevelIndex((prev) => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(2);
    try { localStorage.setItem('juristi_forensic_font_size', '2'); } catch {}
  };

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    if (!isUserScrolledUpRef.current) {
      container.scrollTop = container.scrollHeight;
    }
  }, [currentPillarContent, isCurrentPillarLoading]);

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

  const loadCasePillars = useCallback(async () => {
    if (!caseId) return;
    try {
      const pillars = await forensicService.getCasePillars(caseId);
      if (pillars && typeof pillars === 'object') {
        setCasePillars({
          PILLAR_1: pillars.PILLAR_1 || '',
          PILLAR_2: pillars.PILLAR_2 || '',
          PILLAR_3: pillars.PILLAR_3 || ''
        });
      }
    } catch {
      setCasePillars({ PILLAR_1: '', PILLAR_2: '', PILLAR_3: '' });
    }
  }, [caseId]);

  const loadDocPillars = useCallback(async (docId: string) => {
    if (!caseId || !docId) return;
    try {
      const pillars = await forensicDeskService.getForensicDocPillars(caseId, docId);
      setDocPillars({
        PILLAR_1: pillars.PILLAR_1 || '',
        PILLAR_2: pillars.PILLAR_2 || '',
        PILLAR_3: pillars.PILLAR_3 || ''
      });
    } catch {
      setDocPillars({ PILLAR_1: '', PILLAR_2: '', PILLAR_3: '' });
    }
  }, [caseId]);

  const loadDocuments = useCallback(async () => {
    if (!caseId) return;
    setLoadingDocs(true);
    try {
      const docs = await forensicDeskService.listForensicDocuments(caseId);
      setDocuments(docs);

      if (docs.length > 0 && !selectedDocId) {
        setSelectedDocId(docs[0].id);
      }
    } catch (err) {
      console.error("Dështoi ngarkimi i dokumenteve forenzike:", err);
    } finally {
      setLoadingDocs(false);
    }
  }, [caseId, selectedDocId]);

  useEffect(() => {
    if (caseId) {
      loadDocuments();
      if (autopsyScope === 'CASE') {
        loadCasePillars();
      }
    }
  }, [caseId, autopsyScope, loadDocuments, loadCasePillars]);

  useEffect(() => {
    if (selectedDocId && caseId && autopsyScope === 'DOCUMENT') {
      loadDocPillars(selectedDocId);
    }
  }, [selectedDocId, caseId, autopsyScope, loadDocPillars]);

  const handleUploadFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || !caseId) return;
    setIsUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgressText(`Duke ngarkuar me vulë të kujdestarisë: ${file.name}...`);
        await forensicDeskService.uploadForensicDocument(caseId, file);
      }
      setUploadProgressText("Shkresat u ngarkuan dhe u vulosën.");
      await loadDocuments();
      if (onEvidenceChange) onEvidenceChange();
    } catch (err: any) {
      console.error("Gabim gjatë ngarkimit të dokumentit:", err);
      alert("Dështoi ngarkimi dhe indeksimi i dokumentit.");
    } finally {
      setIsUploading(false);
      setUploadProgressText('');
    }
  };

  const handleDeleteDocument = async (docId: string, docName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    const confirmDelete = window.confirm(`A jeni i sigurt që dëshironi të hiqni shkresën "${docName}" nga fashikulli forenzik?`);
    if (!confirmDelete) return;

    setDeletingDocId(docId);
    try {
      await forensicDeskService.deleteForensicDocument(caseId, docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      if (selectedDocId === docId) {
        setSelectedDocId(null);
        setDocPillars({ PILLAR_1: '', PILLAR_2: '', PILLAR_3: '' });
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e dokumentit:", err);
      alert("Dështoi fshirja e dokumentit nga serveri.");
    } finally {
      setDeletingDocId(null);
    }
  };

  // --- Document View Handler ---
  const handleViewDocument = (doc: ForensicDocItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    // Use the main case document preview endpoint
    const url = `${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`;
    setViewingUrl(url);
    setViewingDoc(doc);
  };

  // --- Document Rename Handlers ---
  const handleRenameDocument = (doc: ForensicDocItem, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenameDocId(doc.id);
    setRenameDocName(doc.file_name);
  };

  const handleConfirmRename = async (newName: string) => {
    if (!caseId || !renameDocId) return;
    try {
      await forensicDeskService.renameForensicDocument(caseId, renameDocId, newName);
      setDocuments(prev =>
        prev.map(d => d.id === renameDocId ? { ...d, file_name: newName } : d)
      );
    } catch (err) {
      console.error("Dështoi riemërtimi:", err);
      alert("Dështoi riemërtimi i dokumentit.");
    } finally {
      setRenameDocId(null);
      setRenameDocName('');
    }
  };

  // --- Document Archive Handler ---
  const handleArchiveDocument = async (doc: ForensicDocItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    const confirmArchive = window.confirm(`A dëshironi ta arkivoni shkresën "${doc.file_name}"?`);
    if (!confirmArchive) return;

    setArchivingDocId(doc.id);
    try {
      await apiService.archiveCaseDocument(caseId, doc.id);
      setDocuments(prev => prev.filter(d => d.id !== doc.id));
      if (selectedDocId === doc.id) {
        setSelectedDocId(null);
        setDocPillars({ PILLAR_1: '', PILLAR_2: '', PILLAR_3: '' });
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi arkivimi:", err);
      alert("Dështoi arkivimi i dokumentit.");
    } finally {
      setArchivingDocId(null);
    }
  };

  const handleAdminPurgeSinglePillar = async () => {
    if (!caseId || !currentPillarContent) return;
    
    const activeCfg = autopsyScope === 'DOCUMENT' ? DOC_PILLAR_CONFIGS[activePillar] : CASE_PILLAR_CONFIGS[activePillar];
    const confirmSingleDelete = window.confirm(`A jeni i sigurt që doni të fshini nga MongoDB VETËM "${activeCfg.title}"? Shtjellat e tjera do të mbeten të paprekura!`);
    if (!confirmSingleDelete) return;

    setIsDeletingPillars(true);
    try {
      if (autopsyScope === 'DOCUMENT') {
        if (!selectedDocId) return;
        await forensicDeskService.deleteForensicDocPillar(caseId, selectedDocId, activePillar);
        setDocPillars(prev => ({ ...prev, [activePillar]: '' }));
      } else {
        await forensicService.deleteCasePillar(caseId, activePillar);
        setCasePillars(prev => ({ ...prev, [activePillar]: '' }));
      }
    } catch (err) {
      console.error("Failed to purge single pillar:", err);
      alert("Dështoi pastrimi i kësaj shtjelle.");
    } finally {
      setIsDeletingPillars(false);
    }
  };

  // GJENERIMI I BLINDUAR NËPËRMJET SHËRBIMIT TË ZYRËS FORENZIKE
  const handleGeneratePillar = useCallback(async (pillar: PillarType, scopeVal: AutopsyScope = autopsyScope, docIdVal: string | null = selectedDocId) => {
    if (!caseId || loadingPillars[pillar]) return;

    setLoadingPillars((prev) => ({ ...prev, [pillar]: true }));
    isUserScrolledUpRef.current = false;

    if (scopeVal === 'DOCUMENT') {
      const targetDoc = documents.find(d => d.id === docIdVal);
      if (!targetDoc) {
        setLoadingPillars((prev) => ({ ...prev, [pillar]: false }));
        return;
      }
      setDocPillars((prev) => ({ ...prev, [pillar]: '' }));

      try {
        const prompt = DOC_PILLAR_CONFIGS[pillar].getPrompt(targetDoc.file_name);
        const result = await forensicDeskService.sendChatMessage(
          caseId,
          prompt,
          `Ekspertizë mbi shkresën: ${targetDoc.file_name}`
        );
        const content = result.content || '';
        setDocPillars((prev) => ({ ...prev, [pillar]: content }));

        if (content.trim().length > 50) {
          try {
            await forensicService.saveDocumentPillar(caseId, targetDoc.id, pillar, content);
          } catch (saveErr) {
            console.warn("Could not save doc pillar to MongoDB:", saveErr);
          }
        }
      } catch (err) {
        console.error(`Doc Pillar Error [${pillar}]:`, err);
        alert(`Ndodhi një gabim gjatë auditimit të ${DOC_PILLAR_CONFIGS[pillar].title}.`);
      } finally {
        setLoadingPillars((prev) => ({ ...prev, [pillar]: false }));
      }
    } else {
      setCasePillars((prev) => ({ ...prev, [pillar]: '' }));

      try {
        const prompt = CASE_PILLAR_CONFIGS[pillar].prompt;
        const result = await forensicDeskService.sendChatMessage(
          caseId,
          prompt,
          `Ekspertizë master mbi të gjithë fashikullin e lëndës.`
        );
        const content = result.content || '';
        setCasePillars((prev) => ({ ...prev, [pillar]: content }));

        if (content.trim().length > 50) {
          try {
            await forensicService.saveCasePillar(caseId, pillar, content);
          } catch (saveErr) {
            console.warn("Could not save case pillar to MongoDB:", saveErr);
          }
        }
      } catch (err) {
        console.error(`Case Pillar Error [${pillar}]:`, err);
        alert(`Ndodhi një gabim gjatë analizës së rastit.`);
      } finally {
        setLoadingPillars((prev) => ({ ...prev, [pillar]: false }));
      }
    }
  }, [caseId, loadingPillars, autopsyScope, selectedDocId, documents]);

  const handleSelectPillar = (pillarKey: PillarType) => {
    setActivePillar(pillarKey);
  };

  const handleCopyReport = () => {
    if (!currentPillarContent) return;
    navigator.clipboard.writeText(currentPillarContent);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2500);
  };

  const handleArchiveReport = async () => {
    if (!caseId || !currentPillarContent) return;
    setIsArchivingReport(true);
    setArchiveReportSuccess(false);

    try {
      const activeTitle = autopsyScope === 'DOCUMENT'
        ? `${DOC_PILLAR_CONFIGS[activePillar].title} - ${activeDoc?.file_name || 'Dokument'}`
        : `${CASE_PILLAR_CONFIGS[activePillar].title} - Fashikulli i Plotë`;

      await forensicService.archiveForensicReport(caseId, activeTitle, currentPillarContent);
      setArchiveReportSuccess(true);
      setTimeout(() => setArchiveReportSuccess(false), 3000);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Dështoi ruajtja në arkiv.");
    } finally {
      setIsArchivingReport(false);
    }
  };

  const filteredDocs = documents.filter(d =>
    (d.file_name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const currentConfigs = autopsyScope === 'DOCUMENT' ? DOC_PILLAR_CONFIGS : CASE_PILLAR_CONFIGS;

  return (
    <div className={`grid grid-cols-1 ${isFullscreen ? 'lg:grid-cols-1' : 'lg:grid-cols-12'} gap-6 transition-all duration-300 select-none`}>
      {/* KOLONA E MAJTË */}
      {!isFullscreen && (
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-main pb-2.5">
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                <FileText size={15} className="text-primary-start" /> Administrimi i Shkresave
              </h3>
              <span className="text-[10px] font-mono text-text-muted">Vision OCR & LPK</span>
            </div>

            <div
              onClick={() => !isUploading && fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (!isUploading) handleUploadFiles(e.dataTransfer.files);
              }}
              className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-2xl p-5 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-2"
            >
              {isUploading ? (
                <div className="flex flex-col items-center justify-center gap-2 py-2">
                  <Loader2 size={22} className="animate-spin text-primary-start" />
                  <span className="text-xs font-bold text-primary-start">{uploadProgressText}</span>
                </div>
              ) : (
                <>
                  <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                    <UploadCloud size={20} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-text-primary">Kliko ose tërhiq shkresat (PDF, DOCX, Skanime)</p>
                    <p className="text-[10px] text-text-muted">Optimizuar me OCR për shkrimet gjyqësore në shqip</p>
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

          <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="relative flex-1 mr-2">
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
                onClick={loadDocuments}
                title="Rifresko listën"
                className="p-2 bg-surface hover:bg-hover border border-main rounded-xl text-text-muted hover:text-text-primary transition-colors cursor-pointer"
              >
                <RefreshCw size={13} className={loadingDocs ? 'animate-spin' : ''} />
              </button>
            </div>

            <div className="space-y-2 max-h-[420px] overflow-y-auto custom-finance-scroll pr-1">
              {filteredDocs.length === 0 ? (
                <div className="text-center py-8 text-xs text-text-muted">
                  {loadingDocs ? 'Duke ngarkuar shkresat...' : 'Nuk u gjet asnjë shkresë në dosje.'}
                </div>
              ) : (
                filteredDocs.map((doc) => {
                  const isSelected = doc.id === selectedDocId;
                  const isDeleting = doc.id === deletingDocId;
                  const isArchiving = doc.id === archivingDocId;

                  return (
                    <div
                      key={doc.id}
                      onClick={() => {
                        setSelectedDocId(doc.id);
                        setAutopsyScope('DOCUMENT');
                        setActivePillar('PILLAR_1');
                      }}
                      className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                        isSelected && autopsyScope === 'DOCUMENT'
                          ? 'bg-primary-start/10 border-primary-start text-primary-start shadow-sm'
                          : 'bg-surface border-main hover:border-primary-start/40 text-text-primary'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <div className={`p-2 rounded-xl ${isSelected && autopsyScope === 'DOCUMENT' ? 'bg-primary-start text-white' : 'bg-surface/80 text-text-muted'}`}>
                          <FileText size={16} />
                        </div>
                        <div className="truncate text-xs">
                          <p className="font-bold truncate text-text-primary">{doc.file_name}</p>
                          <p className="text-[10px] font-mono text-text-muted">Statusi: {doc.status}</p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {isSelected && autopsyScope === 'DOCUMENT' && <CheckCircle2 size={15} className="text-primary-start mr-1" />}
                        
                        {/* Eye - View */}
                        <button
                          type="button"
                          onClick={(e) => handleViewDocument(doc, e)}
                          title="Shiko dokumentin"
                          className="p-1.5 text-text-muted hover:text-blue-500 rounded-lg hover:bg-blue-500/10 transition-colors cursor-pointer"
                        >
                          <Eye size={13} />
                        </button>

                        {/* Pencil - Rename */}
                        <button
                          type="button"
                          onClick={(e) => handleRenameDocument(doc, e)}
                          title="Riemërto"
                          className="p-1.5 text-text-muted hover:text-amber-500 rounded-lg hover:bg-amber-500/10 transition-colors cursor-pointer"
                        >
                          <Pencil size={13} />
                        </button>

                        {/* Archive */}
                        <button
                          type="button"
                          onClick={(e) => handleArchiveDocument(doc, e)}
                          disabled={isArchiving}
                          title="Arkivo"
                          className="p-1.5 text-text-muted hover:text-purple-500 rounded-lg hover:bg-purple-500/10 transition-colors cursor-pointer disabled:opacity-40"
                        >
                          {isArchiving ? <Loader2 size={13} className="animate-spin text-purple-500" /> : <Archive size={13} />}
                        </button>

                        {/* Delete - already present */}
                        <button
                          type="button"
                          onClick={(e) => handleDeleteDocument(doc.id, doc.file_name, e)}
                          disabled={isDeleting}
                          title="Hiq nga dosja forenzike"
                          className="p-1.5 text-text-muted hover:text-rose-500 rounded-lg hover:bg-rose-500/10 transition-colors cursor-pointer disabled:opacity-40"
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

      {/* KOLONA E DJATHTË */}
      <div className={`${isFullscreen ? 'lg:col-span-12' : 'lg:col-span-7'} glass-panel p-5 sm:p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4 flex flex-col justify-between transition-all duration-300 relative`}>
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-3.5">
            <div className="flex items-center bg-surface border border-main rounded-xl p-1 shrink-0">
              <button
                type="button"
                onClick={() => {
                  setAutopsyScope('DOCUMENT');
                  setActivePillar('PILLAR_1');
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
                  autopsyScope === 'DOCUMENT'
                    ? 'bg-primary-start text-white shadow-sm'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                Autopsia e Dokumentit
              </button>

              <button
                type="button"
                onClick={() => {
                  setAutopsyScope('CASE');
                  setActivePillar('PILLAR_1');
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
                  autopsyScope === 'CASE'
                    ? 'bg-primary-start text-white shadow-sm'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                Autopsia e Rastit
              </button>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 rounded-xl border border-main bg-surface p-1" aria-label="Madhësia e shkrimit">
                <button
                  type="button"
                  onClick={handleDecreaseFont}
                  disabled={fontLevelIndex === 0}
                  title="Zvogëlo madhësinë e shkrimit"
                  className="h-6 w-6 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30"
                >
                  A−
                </button>
                <button
                  type="button"
                  onClick={handleResetFont}
                  title="Rivendos madhësinë e shkrimit"
                  className="min-w-9 rounded-lg px-1 text-[10px] font-bold text-text-muted hover:bg-hover hover:text-text-primary"
                >
                  {activeFont.label}
                </button>
                <button
                  type="button"
                  onClick={handleIncreaseFont}
                  disabled={fontLevelIndex === FONT_LEVELS.length - 1}
                  title="Rrit madhësinë e shkrimit"
                  className="h-6 w-6 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30"
                >
                  A+
                </button>
              </div>

              <button
                type="button"
                onClick={handleAdminPurgeSinglePillar}
                disabled={isDeletingPillars || !currentPillarContent}
                className="h-8 w-8 bg-surface hover:bg-rose-500/10 border border-main hover:border-rose-500/30 text-text-muted hover:text-rose-500 rounded-xl flex items-center justify-center transition-all disabled:opacity-30 cursor-pointer shadow-sm"
                title={`Fshi VETËM "${currentConfigs[activePillar].title}" nga MongoDB`}
              >
                {isDeletingPillars ? <Loader2 size={13} className="animate-spin text-rose-500" /> : <Trash2 size={14} />}
              </button>

              <button
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)}
                className="h-8 w-8 bg-surface hover:bg-hover border border-main rounded-xl text-text-primary flex items-center justify-center transition-all cursor-pointer shadow-sm"
                title={isFullscreen ? "Zvogëlo pamjen" : "Zgjero në ekran të plotë"}
              >
                {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              </button>

              <button
                type="button"
                onClick={handleCopyReport}
                disabled={!currentPillarContent}
                className="h-8 px-3.5 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center justify-center transition-all disabled:opacity-40 cursor-pointer shadow-sm"
              >
                <span>{copiedReport ? 'U Kopjua' : 'Kopjo'}</span>
              </button>

              <button
                type="button"
                onClick={handleArchiveReport}
                disabled={isArchivingReport || !currentPillarContent}
                className="h-8 px-3.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center transition-all disabled:opacity-40 cursor-pointer shadow-sm"
              >
                {isArchivingReport ? <Loader2 size={13} className="animate-spin" /> : <span>{archiveReportSuccess ? 'U Ruajt!' : 'Arkivo'}</span>}
              </button>
            </div>
          </div>

          <div className="text-xs text-text-muted">
            {autopsyScope === 'DOCUMENT' ? (
              <p>
                Dokumenti në Ekzaminim: <span className="font-bold text-text-primary">{activeDoc?.file_name || 'Asnjë i përzgjedhur'}</span>
              </p>
            ) : (
              <p>
                Fashikulli i Plotë: <span className="font-bold text-text-primary">Ekspertizë Master për të Gjithë Dosjen</span>
              </p>
            )}
          </div>

          {/* SHIRITI I 3 SHTJELLAVE */}
          <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
            {(Object.keys(currentConfigs) as PillarType[]).map((pillarKey) => {
              const cfg = currentConfigs[pillarKey];
              const isSelected = activePillar === pillarKey;
              const hasContent = Boolean(activePillarsMap[pillarKey]?.trim());
              const isLoading = loadingPillars[pillarKey];

              return (
                <button
                  key={pillarKey}
                  type="button"
                  onClick={() => handleSelectPillar(pillarKey)}
                  className={`px-2.5 sm:px-3 py-2 rounded-xl text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-between gap-1.5 transition-all cursor-pointer border ${
                    isSelected
                      ? pillarKey === 'PILLAR_1'
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                        : pillarKey === 'PILLAR_2'
                        ? 'bg-amber-600 text-white border-amber-600 shadow-sm'
                        : 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                      : 'bg-surface hover:bg-hover text-text-muted border-main'
                  }`}
                >
                  <div className="flex items-center gap-1.5 truncate">
                    {isLoading ? (
                      <Loader2 size={12} className="animate-spin text-white shrink-0" />
                    ) : hasContent ? (
                      <CheckCircle2 size={12} className={isSelected ? 'text-white shrink-0' : 'text-emerald-500 shrink-0'} />
                    ) : null}
                    <span className="truncate">{cfg.title}</span>
                  </div>

                  {isLoading ? (
                    <span className="text-[9px] font-mono font-bold bg-white/20 px-1.5 py-0.5 rounded-full animate-pulse">Duke gjeneruar</span>
                  ) : hasContent ? (
                    <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-full ${isSelected ? 'bg-white/20 text-white' : 'bg-emerald-500/15 text-emerald-500'}`}>
                      E Gatshme
                    </span>
                  ) : (
                    <span className="text-[9px] font-mono text-text-muted opacity-60">Në Pritje</span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="py-1 px-1 flex items-center justify-between gap-2 shrink-0 text-text-muted text-[11px]">
            <p className="truncate font-medium">{currentConfigs[activePillar].subtitle}</p>
            {currentPillarContent && !isCurrentPillarLoading && (
              <button
                type="button"
                onClick={() => handleGeneratePillar(activePillar)}
                className="text-primary-start hover:text-primary-end font-bold hover:underline cursor-pointer shrink-0 text-xs"
              >
                <span>Rigjenero</span>
              </button>
            )}
          </div>

          {/* TRUPI I AUTOPSISË */}
          <div 
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className={`${isFullscreen ? 'h-[620px]' : 'h-[460px]'} overflow-y-auto custom-finance-scroll p-4 sm:p-6 bg-surface/50 rounded-2xl border border-main text-text-primary select-text flex flex-col relative transition-all duration-200`}
          >
            <style>{`
              .dynamic-forensic-report p,
              .dynamic-forensic-report li,
              .dynamic-forensic-report span:not(.lucide) {
                font-size: ${activeFont.base}px !important;
                line-height: ${activeFont.line} !important;
              }
              .dynamic-forensic-report td {
                font-size: ${Math.max(11.5, activeFont.base - 1.5)}px !important;
                line-height: 1.45 !important;
                padding: 6px 8px !important;
              }
              .dynamic-forensic-report th {
                font-size: ${Math.max(11, activeFont.base - 2)}px !important;
                padding: 8px 8px !important;
              }
              .dynamic-forensic-report h1 {
                font-size: ${activeFont.h1}px !important;
                line-height: 1.25 !important;
                margin-top: 1.2em !important;
                margin-bottom: 0.5em !important;
              }
              .dynamic-forensic-report h2 {
                font-size: ${activeFont.h2}px !important;
                line-height: 1.3 !important;
                margin-top: 1.1em !important;
                margin-bottom: 0.4em !important;
              }
              .dynamic-forensic-report h3 {
                font-size: ${activeFont.h3}px !important;
                line-height: 1.35 !important;
                margin-top: 0.9em !important;
                margin-bottom: 0.3em !important;
              }
              .dynamic-forensic-report table {
                display: block !important;
                width: 100% !important;
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch !important;
                margin: 1em 0 !important;
              }
            `}</style>

            {!currentPillarContent && !isCurrentPillarLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 sm:p-12 my-auto space-y-4">
                <h4 className="text-sm sm:text-base font-black uppercase tracking-tight text-text-primary">
                  {currentConfigs[activePillar].title}
                </h4>
                <p className="text-xs text-text-muted max-w-sm">
                  Kjo shtjellë është e pastër. Klikoni butonin më poshtë kur të dëshironi të filloni auditimin doktrinar.
                </p>
                <button
                  type="button"
                  onClick={() => handleGeneratePillar(activePillar)}
                  className="px-6 py-3 bg-primary-start hover:brightness-110 text-white rounded-xl font-bold text-xs uppercase tracking-wider shadow-lg shadow-primary-start/20 flex items-center justify-center cursor-pointer transition-all hover-lift"
                >
                  <span>Analizo {currentConfigs[activePillar].title}</span>
                </button>
              </div>
            ) : isCurrentPillarLoading && !currentPillarContent ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 my-auto">
                <Loader2 className="w-10 h-10 animate-spin text-primary-start mb-3" />
                <p className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Duke analizuar {currentConfigs[activePillar].title}...
                </p>
                <p className="text-[10px] text-text-muted mt-1">
                  Juristi AI po kryen autopsinë e thellë doktrinare.
                </p>
              </div>
            ) : (
              <div className="markdown-content dynamic-forensic-report prose prose-slate dark:prose-invert max-w-none text-text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {autoLinkedContent}
                </ReactMarkdown>
              </div>
            )}

            {showScrollBottomBtn && (
              <button
                type="button"
                onClick={scrollToBottom}
                className="sticky bottom-2 right-2 ml-auto z-20 px-3 py-1.5 bg-slate-900 text-white text-[11px] font-bold rounded-full shadow-lg border border-slate-700 flex items-center gap-1 cursor-pointer"
              >
                <span>Te Fundi</span>
                <ArrowDown size={12} className="animate-bounce" />
              </button>
            )}
          </div>
        </div>

        <div className="pt-3 border-t border-main flex items-center justify-between text-[11px] text-text-muted">
          <span className="font-medium">
            Standard i Pajtueshëm me Gjykatën Supreme të Kosovës & OAK
          </span>
          <span className="font-mono text-[10px]">Modeli: Claude Sonnet 4.6 (1:1 Dedicated Architecture)</span>
        </div>
      </div>

      {/* Modals for Document Actions */}
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