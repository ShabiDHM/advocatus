// FILE: frontend/src/components/forensics/DocumentForensicLab.tsx
// PHOENIX PROTOCOL - DUAL FORENSIC AUTOPSY LAB V11.0 (CONTROLLED TRIGGER & PURGE PERSISTENCE)
// ZERO TS WARNINGS • NO UNWANTED AUTO-GENERATION • ATOMIC $UNSET INTEGRATION • 100% COMPLETE CODE

import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Loader2,
  RefreshCw,
  Search,
  Maximize2,
  Minimize2,
  ArrowDown
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { apiService } from '../../services/api';
import { forensicService } from '../../services/forensicService';
import { autoLinkLegalCitations } from '../../utils/chatHelpers';
import { buildMarkdownComponents } from '../chat/MarkdownRenderer';

export type AutopsyScope = 'DOCUMENT' | 'CASE';
export type PillarType = 'PILLAR_1' | 'PILLAR_2' | 'PILLAR_3';

interface DocumentItem {
  id: string;
  name: string;
  sizeFormatted: string;
  content_type?: string;
  created_at?: string;
  extracted_text?: string;
  status?: string;
  has_violation?: boolean;
  forensic_pillars?: Record<string, string>;
}

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
DETYRË: Gjenero EKSKLUZIVISHT SHTJELLËN 1 (MOS shkruaj asnjë seksion tjetër):
- Seksioni 1: Pasaporta Procedurale dhe Diagnoza Juridike (Lloji i aktit, Organi nxjerrës, Numri, Afatet ligjore prekluzive).
- Seksioni 2: Struktura e Palëve dhe Legjitimiteti Procedural.
- Seksioni 3: Kryqëzimi Forenzik i Fakteve dhe Baza Provuese e Administruar.
RREGULL I HEKURT: Përfundo të gjithë SHTJELLËN 1 brenda kësaj përgjigjeje pa u ndërprerë!`
  },
  PILLAR_2: {
    title: '2. Nenet & Shkeljet',
    subtitle: 'Tabela Shteruese e Neneve të Kosovës & Detektori i Shkeljeve/Lapsuseve',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 2: NENET DHE SHKELJET]
Dokumenti: "${docName}"
DETYRË: Gjenero EKSKLUZIVISHT SHTJELLËN 2 (MOS shkruaj asnjë seksion tjetër):
- Seksioni 4: Tabela Shteruese e Neneve të Shkelura të Kosovës (Formati: Neni X i [Ligjit]) me precedentët përkatës të Gjykatës Supreme (PML / Revizion).
- Seksioni 5: Gjetjet Kritike, Shkeljet Thelbësore të Procedurës (Neni 182 LPK / KPK) dhe Detektori i Pasaktësive/Lapsuseve me Tabelën e Zëvendësimit.
RREGULL I HEKURT: Përfundo të gjithë SHTJELLËN 2 brenda kësaj përgjigjeje pa u ndërprerë!`
  },
  PILLAR_3: {
    title: '3. Kundërshtimet & Plani',
    subtitle: 'Auditimi i Kërkesës, Diagnoza Korrigjuese & Master Plani i Veprimit',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 3: KUNDËRSHTIMET DHE PLANI]
Dokumenti: "${docName}"
DETYRË: Gjenero EKSKLUZIVISHT SHTJELLËN 3 (MOS shkruaj asnjë seksion tjetër):
- Seksioni 6: Auditimi i Kërkesës, Vlerësimi i Rreziqeve Procedurale dhe Forca Ekzekutive.
- Seksioni 7: Diagnoza Korrigjuese dhe Rekomandimet Taktike mbi Goditjen e Shkresës.
- Seksioni 8: Master Plani i Veprimit me Hapat Proceduralë dhe Afatet e Prera Ligjore.
RREGULL I HEKURT: Përfundo të gjithë SHTJELLËN 3 brenda kësaj përgjigjeje pa u ndërprerë!`
  }
};

const CASE_PILLAR_CONFIGS: Record<PillarType, { title: string; subtitle: string; prompt: string }> = {
  PILLAR_1: {
    title: '1. Fakti & Historiku',
    subtitle: 'Diagnoza Fillestare, Kronologjia e Ngjarjeve & Kryqëzimi i Palëve/Dëshmitarëve',
    prompt: `[DIREKTIVË FORENZIKE — SHTJELLA 1: FAKTI & HISTORIKU]
Gjenero EKSKLUZIVISHT Seksionet 1 dhe 2 për të gjithë fashikullin:
- Seksioni 1: Diagnoza Procedurale dhe Gjendja Faktike e Dosjes.
- Seksioni 2: Rindërtimi Kronologjik i Datave dhe Veprimeve Vendimtare Procedurale.
- Kryqëzimi i Dëshmive, Palëve, Gjyqtarëve dhe Ekspertëve.
RREGULL I HEKURT: Përfundo të gjithë SHTJELLËN 1 brenda kësaj përgjigjeje pa u ndërprerë!`
  },
  PILLAR_2: {
    title: '2. Shkeljet & Nenet',
    subtitle: 'Matrica e Provave, Tabela e Neneve të Gjykatës Supreme & Përgjegjësia Penale/Civile',
    prompt: `[DIREKTIVË FORENZIKE — SHTJELLA 2: SHKELJET & NENET]
Gjenero EKSKLUZIVISHT Seksionet 3, 4 dhe 5 për të gjithë fashikullin:
- Seksioni 3: Matrica e Provave Materiale dhe Provat Kontradiktore.
- Seksioni 4: Tabela e Nxjerrjes së Neneve të Kosovës (Neni X i [Ligjit]).
- Seksioni 5: Përgjegjësia Penale (Nenet 383, 414, 427 KPK) dhe Shkeljet Thelbësore (Neni 182 LPK).
RREGULL I HEKURT: Përfundo të gjithë SHTJELLËN 2 brenda kësaj përgjigjeje pa u ndërprerë!`
  },
  PILLAR_3: {
    title: '3. Plani i Veprimit',
    subtitle: 'Mjetet Juridike, Prapësimet, Kundërshtimet & Master Strategjia e Seancës',
    prompt: `[DIREKTIVË FORENZIKE — SHTJELLA 3: PLANI I VEPRIMIT]
Gjenero EKSKLUZIVISHT Seksionet 6, 7 dhe 8 për të gjithë fashikullin:
- Seksioni 6: Përgatitja e Mjeteve Juridike (Ankesa, Prapësime, Padi, Kallëzime Penale).
- Seksioni 7: Pyetësori Taktik për Seancë me Pyetje Kurth për Palën Kundërshtare dhe Ekspertët.
- Seksioni 8: Master Plani i Veprimit me Afate të Prera.
RREGULL I HEKURT: Përfundo të gjithë SHTJELLËN 3 brenda kësaj përgjigjeje pa u ndërprerë!`
  }
};

export const DocumentForensicLab: React.FC<DocumentForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
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
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveSuccess, setArchiveSuccess] = useState<boolean>(false);

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

  const extractFileSize = (d: any): string => {
    const rawBytes = d.size ?? d.file_size ?? d.bytes ?? d.file_size_bytes ?? d.length ?? d.metadata?.file_size ?? d.metadata?.size;
    if (rawBytes !== undefined && rawBytes !== null) {
      const num = typeof rawBytes === 'string' ? parseFloat(rawBytes) : Number(rawBytes);
      if (!isNaN(num) && num > 0) {
        if (num < 1024) return `${num} B`;
        if (num < 1024 * 1024) return `${(num / 1024).toFixed(0)} KB`;
        return `${(num / (1024 * 1024)).toFixed(1)} MB`;
      }
    }
    return 'PDF e Indeksuar';
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
      const pillars = await forensicService.getDocumentPillars(caseId, docId);
      if (pillars && typeof pillars === 'object') {
        setDocPillars({
          PILLAR_1: pillars.PILLAR_1 || '',
          PILLAR_2: pillars.PILLAR_2 || '',
          PILLAR_3: pillars.PILLAR_3 || ''
        });
      } else {
        setDocPillars({ PILLAR_1: '', PILLAR_2: '', PILLAR_3: '' });
      }
    } catch {
      setDocPillars({ PILLAR_1: '', PILLAR_2: '', PILLAR_3: '' });
    }
  }, [caseId]);

  useEffect(() => {
    if (caseId) {
      loadDocuments();
      if (autopsyScope === 'CASE') {
        loadCasePillars();
      }
    }
  }, [caseId, autopsyScope, loadCasePillars]);

  useEffect(() => {
    if (selectedDocId && caseId && autopsyScope === 'DOCUMENT') {
      loadDocPillars(selectedDocId);
    }
  }, [selectedDocId, caseId, autopsyScope, loadDocPillars]);

  const loadDocuments = async () => {
    if (!caseId) return;
    setLoadingDocs(true);
    try {
      const docs = await apiService.getDocuments(caseId);
      const mapped: DocumentItem[] = (docs || []).map((d: any) => ({
        id: d.id || d._id,
        name: d.name || d.file_name || 'Dokument pa titull',
        sizeFormatted: extractFileSize(d),
        content_type: d.content_type || 'application/pdf',
        created_at: d.created_at || d.uploaded_at || new Date().toISOString(),
        extracted_text: d.extracted_text || d.text || '',
        status: d.status || 'READY',
        has_violation: Boolean(d.has_violation || (d.audit_result && (d.audit_result.includes('SHKELJE') || d.audit_result.includes('Neni 182')))),
        forensic_pillars: d.forensic_pillars || {}
      }));

      setDocuments(mapped);

      if (mapped.length > 0 && !selectedDocId) {
        setSelectedDocId(mapped[0].id);
      }
    } catch (err) {
      console.error("Dështoi ngarkimi i dokumenteve:", err);
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleUploadFiles = async (files: FileList | null) => {
    if (!files || files.length === 0 || !caseId) return;
    setIsUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setUploadProgressText(`Duke indeksuar me OCR: ${file.name} (${i + 1}/${files.length})...`);
        await apiService.uploadDocument(caseId, file);
      }
      setUploadProgressText("Dokumentet u indeksuan me sukses!");
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
      await apiService.deleteDocument(caseId, docId);
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

  // TOTAL ATOMIC PURGE NË MONGODB ATLAS ($UNSET)
  const handleAdminPurgeSinglePillar = async () => {
    if (!caseId || !currentPillarContent) return;
    
    const activeCfg = autopsyScope === 'DOCUMENT' ? DOC_PILLAR_CONFIGS[activePillar] : CASE_PILLAR_CONFIGS[activePillar];
    const confirmSingleDelete = window.confirm(`A jeni i sigurt që doni të fshini nga MongoDB VETËM "${activeCfg.title}"? Shtjellat e tjera do të mbeten të paprekura!`);
    if (!confirmSingleDelete) return;

    setIsDeletingPillars(true);
    try {
      if (autopsyScope === 'DOCUMENT') {
        if (!selectedDocId || !activeDoc) return;
        
        await forensicService.deleteDocumentPillar(caseId, selectedDocId, activePillar);
        
        // Zbraz menjëherë state-in lokal dhe cache-in e dokumentit
        setDocPillars(prev => ({ ...prev, [activePillar]: '' }));
        setDocuments(prev => prev.map(d => d.id === selectedDocId ? {
          ...d,
          forensic_pillars: { ...(d.forensic_pillars || {}), [activePillar]: '' }
        } : d));
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

  // GJENERIMI DHE RUAJTJA NË MONGODB ME DËSHIRË TË PËRDORUESIT
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
        const prompt = DOC_PILLAR_CONFIGS[pillar].getPrompt(targetDoc.name);
        const stream = apiService.sendChatMessageStream(caseId, prompt, [targetDoc.id], 'ks', 'DEEP', 'document', false);

        let accumulated = '';
        for await (const chunk of stream) {
          accumulated += chunk;
          const currentAcc = accumulated;
          setDocPillars((prev) => ({ ...prev, [pillar]: currentAcc }));
        }

        if (accumulated.trim().length > 50) {
          try {
            await forensicService.saveDocumentPillar(caseId, targetDoc.id, pillar, accumulated);
            setDocuments(prev => prev.map(d => d.id === targetDoc.id ? {
              ...d,
              forensic_pillars: { ...(d.forensic_pillars || {}), [pillar]: accumulated }
            } : d));
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
        const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic', false);

        let accumulated = '';
        for await (const chunk of stream) {
          accumulated += chunk;
          const currentAcc = accumulated;
          setCasePillars((prev) => ({ ...prev, [pillar]: currentAcc }));
        }

        if (accumulated.trim().length > 50) {
          try {
            await forensicService.saveCasePillar(caseId, pillar, accumulated);
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

  // KALIMI MES TAB-EVE: THJESHT NDRYSHON PAMJEN PA ASNJË FORCIM TË GJENERIMIT
  const handleSelectPillar = (pillarKey: PillarType) => {
    setActivePillar(pillarKey);
  };

  const handleCopyReport = () => {
    if (!currentPillarContent) return;
    navigator.clipboard.writeText(currentPillarContent);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2500);
  };

  const handleArchivePillar = async () => {
    if (!caseId || !currentPillarContent) return;
    setIsArchiving(true);
    setArchiveSuccess(false);

    try {
      const activeTitle = autopsyScope === 'DOCUMENT'
        ? `${DOC_PILLAR_CONFIGS[activePillar].title} - ${activeDoc?.name || 'Dokument'}`
        : `${CASE_PILLAR_CONFIGS[activePillar].title} - Fashikulli i Plotë`;

      await apiService.archiveForensicReport(caseId, activeTitle, currentPillarContent);
      setArchiveSuccess(true);
      setTimeout(() => setArchiveSuccess(false), 3000);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Dështoi ruajtja në arkiv.");
    } finally {
      setIsArchiving(false);
    }
  };

  const filteredDocs = documents.filter(d =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
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
                          <div className="flex items-center gap-1.5">
                            <p className="font-bold truncate text-text-primary">{doc.name}</p>
                            {doc.has_violation && (
                              <span title="Shkelje procedurale e zbuluar!" className="text-rose-500 shrink-0">
                                <AlertCircle size={13} />
                              </span>
                            )}
                          </div>
                          <p className="text-[10px] font-mono text-text-muted">
                            {doc.sizeFormatted} • Statusi: {doc.status}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {isSelected && autopsyScope === 'DOCUMENT' && <CheckCircle2 size={15} className="text-primary-start mr-1" />}
                        <button
                          type="button"
                          onClick={(e) => handleDeleteDocument(doc.id, doc.name, e)}
                          disabled={isDeleting}
                          title="Hiq nga dosja forenzike"
                          className="p-1.5 text-text-muted hover:text-rose-500 rounded-lg hover:bg-rose-500/10 transition-colors cursor-pointer"
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
          {/* Header Bar */}
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

            {/* Butonat e Veprimit me Total Cascade Wipeout për Shtjellën Aktive */}
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
                onClick={handleArchivePillar}
                disabled={isArchiving || !currentPillarContent}
                className="h-8 px-3.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center transition-all disabled:opacity-40 cursor-pointer shadow-sm"
              >
                {isArchiving ? <Loader2 size={13} className="animate-spin" /> : <span>{archiveSuccess ? 'U Ruajt!' : 'Arkivo'}</span>}
              </button>
            </div>
          </div>

          <div className="text-xs text-text-muted">
            {autopsyScope === 'DOCUMENT' ? (
              <p>
                Dokumenti në Ekzaminim: <span className="font-bold text-text-primary">{activeDoc?.name || 'Asnjë i përzgjedhur'}</span>
              </p>
            ) : (
              <p>
                Fashikulli i Plotë: <span className="font-bold text-text-primary">Ekspertizë Master për të Gjithë Dosjen</span>
              </p>
            )}
          </div>

          {/* SHIRITI I 3 SHTJELLAVE (STATUS REAL, ZERO AUTO-TRIGGER) */}
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
          <span className="font-mono text-[10px]">Modeli: Claude Sonnet 4.6 (1M Context)</span>
        </div>
      </div>
    </div>
  );
};

export default DocumentForensicLab;