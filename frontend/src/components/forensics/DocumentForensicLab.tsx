// FILE: frontend/src/components/forensics/DocumentForensicLab.tsx
// PHOENIX PROTOCOL - DUAL FORENSIC AUTOPSY LAB V4.0 (AUTO-SCROLL STREAM & FULLSCREEN EXPAND)
// ZERO TS WARNINGS • AUTO-SCROLL TO BOTTOM • EXPAND/COLLAPSE FULLSCREEN • 100% COMPLETE CODE

import React, { useState, useEffect, useRef, useMemo } from 'react';
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
}

interface DocumentForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

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
NDALOHET GJENERIMI I NENEVE APO PLANEVE NË KËTË SHTJELLË.`
  },
  PILLAR_2: {
    title: '2. Nenet & Shkeljet',
    subtitle: 'Tabela Shteruese e Neneve të Kosovës & Detektori i Shkeljeve/Lapsuseve',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 2: NENET DHE SHKELJET]
Dokumenti: "${docName}"
DETYRË: Gjenero EKSKLUZIVISHT SHTJELLËN 2 (MOS shkruaj asnjë seksion tjetër):
- Seksioni 4: Tabela Shteruese e Neneve të Shkelura të Kosovës (Formati: Neni X i [Ligjit]) me precedentët përkatës të Gjykatës Supreme (PML / Revizion).
- Seksioni 5: Gjetjet Kritike, Shkeljet Thelbësore të Procedurës (Neni 182 LPK / KPK) dhe Detektori i Pasaktësive/Lapsuseve me Tabelën e Zëvendësimit.
NDALOHET GJENERIMI I PJESËVE TË TJERA NË KËTË SHTJELLË.`
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
PËRQENDROHU VETËM TE PLANI DHE KUNDËRSHTIMET.`
  }
};

const CASE_PILLAR_CONFIGS: Record<PillarType, { title: string; subtitle: string; prompt: string }> = {
  PILLAR_1: {
    title: '1. Fakti & Historiku',
    subtitle: 'Diagnoza Fillestare, Kronologjia e Ngjarjeve & Kryqëzimi i Palëve/Dëshmitarëve',
    prompt: `[DIREKTIVË FORENZIKE — SHTJELLA 1 E RASTIT: FAKTI DHE HISTORIKU]
Gjenero EKSKLUZIVISHT Seksionet 1 dhe 2 për të gjithë fashikullin:
- Seksioni 1: Diagnoza Procedurale dhe Gjendja Faktike e Dosjes.
- Seksioni 2: Kronologjia Tabulare e Ngjarjeve dhe Kryqëzimi i Palëve.
MOS gjenero seksionet 3, 4, 5, 6, 7, 8.`
  },
  PILLAR_2: {
    title: '2. Shkeljet & Nenet',
    subtitle: 'Matrica e Provave, Tabela e Neneve të Gjykatës Supreme & Përgjegjësia Penale/Civile',
    prompt: `[DIREKTIVË FORENZIKE — SHTJELLA 2 E RASTIT: SHKELJET DHE NENET]
Gjenero EKSKLUZIVISHT Seksionet 3, 4 dhe 5 për të gjithë fashikullin:
- Seksioni 3: Matrica e Provave Materiale.
- Seksioni 4: Tabela e Nxjerrjes së Neneve të Kosovës (Neni X i [Ligjit]).
- Seksioni 5: Përgjegjësia Penale dhe Shkeljet Thelbësore (Neni 182 LPK).
MOS gjenero seksionet e tjera.`
  },
  PILLAR_3: {
    title: '3. Plani i Veprimit',
    subtitle: 'Mjetet Juridike, Prapësimet, Kundërshtimet & Master Strategjia e Seancës',
    prompt: `[DIREKTIVË FORENZIKE — SHTJELLA 3 E RASTIT: PLANI I VEPRIMIT]
Gjenero EKSKLUZIVISHT Seksionet 6, 7 dhe 8 për të gjithë fashikullin:
- Seksioni 6: Përgatitja e Mjeteve Juridike.
- Seksioni 7: Pyetësori Taktik për Seancë me Pyetje Kurth.
- Seksioni 8: Master Plani i Veprimit me Afate të Prera.
MOS gjenero seksionet e para.`
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

  const [docPillars, setDocPillars] = useState<Record<PillarType, string>>({
    PILLAR_1: '',
    PILLAR_2: '',
    PILLAR_3: ''
  });

  const [casePillars, setCasePillars] = useState<Record<PillarType, string>>({
    PILLAR_1: '',
    PILLAR_2: '',
    PILLAR_3: ''
  });

  const [loadingPillars, setLoadingPillars] = useState<Record<PillarType, boolean>>({
    PILLAR_1: false,
    PILLAR_2: false,
    PILLAR_3: false
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

  // AUTO-SCROLL AUTOMATIK GJATË STREAM-IT
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

  useEffect(() => {
    if (caseId) {
      loadDocuments();
      loadCasePillars();
    }
  }, [caseId]);

  const loadCasePillars = async () => {
    if (!caseId) return;
    try {
      const details: any = await apiService.getCaseDetails(caseId);
      if (details?.forensic_pillars) {
        setCasePillars({
          PILLAR_1: details.forensic_pillars.PILLAR_1 || '',
          PILLAR_2: details.forensic_pillars.PILLAR_2 || '',
          PILLAR_3: details.forensic_pillars.PILLAR_3 || ''
        });
      }
    } catch {}
  };

  useEffect(() => {
    if (selectedDocId && caseId) {
      setDocPillars({ PILLAR_1: '', PILLAR_2: '', PILLAR_3: '' });
      apiService.getDocument(caseId, selectedDocId).then((doc: any) => {
        if (doc?.forensic_pillars) {
          setDocPillars({
            PILLAR_1: doc.forensic_pillars.DOC_PILLAR_1 || doc.forensic_pillars.PILLAR_1 || '',
            PILLAR_2: doc.forensic_pillars.DOC_PILLAR_2 || doc.forensic_pillars.PILLAR_2 || '',
            PILLAR_3: doc.forensic_pillars.DOC_PILLAR_3 || doc.forensic_pillars.PILLAR_3 || ''
          });
        }
      }).catch(() => {});
    }
  }, [selectedDocId, caseId]);

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
        has_violation: Boolean(d.has_violation || (d.audit_result && (d.audit_result.includes('SHKELJE') || d.audit_result.includes('Neni 182'))))
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

  const handleGeneratePillar = async (pillar: PillarType) => {
    if (!caseId || loadingPillars[pillar]) return;

    setLoadingPillars((prev) => ({ ...prev, [pillar]: true }));
    isUserScrolledUpRef.current = false;

    if (autopsyScope === 'DOCUMENT') {
      if (!activeDoc) return;
      setDocPillars((prev) => ({ ...prev, [pillar]: '' }));

      try {
        const prompt = DOC_PILLAR_CONFIGS[pillar].getPrompt(activeDoc.name);
        const stream = apiService.sendChatMessageStream(
          caseId,
          prompt,
          [activeDoc.id],
          'ks',
          'DEEP',
          'automatic',
          false
        );

        let accumulated = '';
        for await (const chunk of stream) {
          accumulated += chunk;
          const currentAcc = accumulated;
          setDocPillars((prev) => ({ ...prev, [pillar]: currentAcc }));
        }

        if (accumulated.trim().length > 50) {
          await forensicService.saveDocumentPillar(caseId, activeDoc.id, pillar, accumulated);
        }
      } catch (err) {
        console.error(`Doc Pillar Error [${pillar}]:`, err);
        alert(`Ndodhi një gabim gjatë auditimit.`);
      } finally {
        setLoadingPillars((prev) => ({ ...prev, [pillar]: false }));
      }
    } else {
      setCasePillars((prev) => ({ ...prev, [pillar]: '' }));

      try {
        const prompt = CASE_PILLAR_CONFIGS[pillar].prompt;
        const stream = apiService.sendChatMessageStream(
          caseId,
          prompt,
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
          setCasePillars((prev) => ({ ...prev, [pillar]: currentAcc }));
        }

        if (accumulated.trim().length > 50) {
          await forensicService.saveCasePillar(caseId, pillar, accumulated);
        }
      } catch (err) {
        console.error(`Case Pillar Error [${pillar}]:`, err);
        alert(`Ndodhi një gabim gjatë analizës së rastit.`);
      } finally {
        setLoadingPillars((prev) => ({ ...prev, [pillar]: false }));
      }
    }
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
    <div className={`grid grid-cols-1 ${isFullscreen ? 'lg:grid-cols-1' : 'lg:grid-cols-12'} gap-6 transition-all duration-300`}>
      {/* KOLONA E MAJTË (Fshihet kur zmadhohet në ekran të plotë) */}
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

      {/* KOLONA E DJATHTË: AUTOPSIA ME AUTO-SCROLL DHE EXPAND */}
      <div className={`${isFullscreen ? 'lg:col-span-12' : 'lg:col-span-7'} glass-panel p-5 sm:p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4 flex flex-col justify-between transition-all duration-300 relative`}>
        <div className="space-y-3">
          {/* Header Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-3.5">
            <div className="flex items-center bg-surface border border-main rounded-xl p-1 shrink-0">
              <button
                type="button"
                onClick={() => setAutopsyScope('DOCUMENT')}
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
                onClick={() => setAutopsyScope('CASE')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all cursor-pointer ${
                  autopsyScope === 'CASE'
                    ? 'bg-primary-start text-white shadow-sm'
                    : 'text-text-muted hover:text-text-primary'
                }`}
              >
                Autopsia e Rastit
              </button>
            </div>

            {/* Butonat me Zgjerim (Expand) */}
            <div className="flex items-center gap-2">
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

          {/* 3 SHTJELLAT */}
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
                  onClick={() => setActivePillar(pillarKey)}
                  className={`px-2.5 sm:px-3 py-2 rounded-xl text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer border ${
                    isSelected
                      ? pillarKey === 'PILLAR_1'
                        ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                        : pillarKey === 'PILLAR_2'
                        ? 'bg-amber-600 text-white border-amber-600 shadow-sm'
                        : 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                      : 'bg-surface hover:bg-hover text-text-muted border-main'
                  }`}
                >
                  {isLoading ? (
                    <Loader2 size={12} className="animate-spin text-white" />
                  ) : null}
                  <span className="truncate">{cfg.title}</span>
                  {hasContent && !isLoading && (
                    <span className={`w-1.5 h-1.5 rounded-full ${isSelected ? 'bg-white' : 'bg-status-success'}`} title="E ruajtur në MongoDB" />
                  )}
                </button>
              );
            })}
          </div>

          <div className="py-1 px-1 flex items-center justify-between gap-2 text-text-muted text-[11px]">
            <p className="truncate font-medium">{currentConfigs[activePillar].subtitle}</p>
            {currentPillarContent && !isCurrentPillarLoading && (
              <button
                type="button"
                onClick={() => handleGeneratePillar(activePillar)}
                className="text-primary-start hover:text-primary-end font-bold hover:underline cursor-pointer shrink-0"
              >
                <span>Rigjenero</span>
              </button>
            )}
          </div>

          {/* TRUPI I AUTOPSISË ME AUTO-SCROLL */}
          <div 
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className={`${isFullscreen ? 'h-[620px]' : 'h-[460px]'} overflow-y-auto custom-finance-scroll p-4 sm:p-6 bg-surface/50 rounded-2xl border border-main text-text-primary select-text flex flex-col relative transition-all duration-200`}
          >
            {!currentPillarContent && !isCurrentPillarLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 my-auto">
                <h4 className="text-xs sm:text-sm font-black uppercase tracking-tight text-text-primary mb-1">
                  {currentConfigs[activePillar].title}
                </h4>
                <p className="text-[11px] text-text-muted max-w-sm mb-5 leading-relaxed">
                  {autopsyScope === 'DOCUMENT'
                    ? (activeDoc ? `Klikoni më poshtë për të kryer autopsinë e shkresës "${activeDoc.name}".` : 'Përzgjidhni një shkresë në të majtë.')
                    : 'Klikoni më poshtë për të kryer analizën e thellë për të gjithë fashikullin.'}
                </p>
                <button
                  type="button"
                  disabled={autopsyScope === 'DOCUMENT' && !selectedDocId}
                  onClick={() => handleGeneratePillar(activePillar)}
                  className="px-5 py-2.5 bg-primary-start hover:brightness-110 text-white rounded-xl font-bold text-xs uppercase tracking-wider shadow-md shadow-primary-start/20 cursor-pointer transition-all disabled:opacity-40"
                >
                  <span>Analizo {currentConfigs[activePillar].title}</span>
                </button>
              </div>
            ) : isCurrentPillarLoading && !currentPillarContent ? (
              <div className="flex-1 flex flex-col items-center justify-center p-8 my-auto">
                <Loader2 className="w-9 h-9 animate-spin text-primary-start mb-3" />
                <p className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Duke analizuar {currentConfigs[activePillar].title}...
                </p>
                <p className="text-[10px] text-text-muted mt-1">
                  Juristi AI po kryen autopsinë e thellë doktrinare.
                </p>
              </div>
            ) : (
              <div className="markdown-content prose prose-slate dark:prose-invert max-w-none text-xs sm:text-sm leading-relaxed text-text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {autoLinkedContent}
                </ReactMarkdown>
                {isCurrentPillarLoading && (
                  <div className="inline-flex items-center gap-2 mt-4 px-3 py-1.5 rounded-lg bg-primary-start/10 text-primary-start border border-primary-start/20 text-xs font-bold">
                    <Loader2 size={13} className="animate-spin" />
                    <span>Duke gjeneruar rrjedhën doktrinare...</span>
                  </div>
                )}
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