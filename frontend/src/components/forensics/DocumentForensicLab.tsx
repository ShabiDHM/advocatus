// FILE: frontend/src/components/forensics/DocumentForensicLab.tsx
// PHOENIX PROTOCOL - DUAL FORENSIC AUTOPSY LAB V14.15 (GREEN TOAST COMPLETELY REMOVED)
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
  Play,
  Pencil,
  Archive,
  FileSearch,
  Copy,
  Check,
  X,
  Scale
} from 'lucide-react';
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

export type AutopsyScope = 'DOCUMENT' | 'CASE';
export type PillarType = 'PILLAR_1' | 'PILLAR_2' | 'PILLAR_3';

interface DocumentForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

const FONT_LEVELS = [
  { label: '90%',   base: 14,   h1: 20,   h2: 17,   h3: 15,   line: 1.55 },
  { label: '100%',  base: 16,   h1: 22,   h2: 19,   h3: 17,   line: 1.65 },
  { label: '115%',  base: 18,   h1: 25,   h2: 21,   h3: 19,   line: 1.7 },
  { label: '130%',  base: 20,   h1: 28,   h2: 23,   h3: 21,   line: 1.75 },
  { label: '150%',  base: 23,   h1: 32,   h2: 27,   h3: 24,   line: 1.8 }
];

const DOC_PILLAR_CONFIGS: Record<PillarType, { title: string; shortTitle: string; subtitle: string; getPrompt: (docName: string) => string }> = {
  PILLAR_1: {
    title: '1. Ekzaminimi & Faktet',
    shortTitle: '1. Faktet',
    subtitle: 'Pasaporta Procedurale, Struktura e Palëve & Baza Provuese',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 1: EKZAMINIMI DHE FAKTET]\nDokumenti: "${docName}"\nDETYRË: Gjenero SHTJELLËN 1 me Claude Sonnet 4.6:\n- Seksioni 1: Pasaporta Procedurale dhe Diagnoza Juridike (Lloji i aktit, Organi nxjerrës, Numri, Afatet ligjore).\n- Seksioni 2: Struktura e Palëve dhe Legjitimiteti Procedural.\n- Seksioni 3: Kryqëzimi Forenzik i Fakteve dhe Baza Provuese e Administruar.\nPërgjigju me përpikmëri shkencore dhe nene të sakta të Kosovës.`
  },
  PILLAR_2: {
    title: '2. Nenet & Shkeljet',
    shortTitle: '2. Nenet',
    subtitle: 'Tabela e Neneve të Kosovës & Shkeljet Procedurale',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 2: NENET DHE SHKELJET]\nDokumenti: "${docName}"\nDETYRË: Gjenero SHTJELLËN 2 me Claude Sonnet 4.6:\n- Seksioni 4: Tabela e Neneve të Shkelura sipas Legjislacionit të Kosovës me precedentët e Gjykatës Supreme (PML / Revizion).\n- Seksioni 5: Gjetjet Kritike, Shkeljet Thelbësore të Procedurës (Neni 182 LPK / KPK) dhe Detektori i Pasaktësive.\nBazo arsyetimin në legjislacionin pozitiv të Kosovës.`
  },
  PILLAR_3: {
    title: '3. Kundërshtimet & Plani',
    shortTitle: '3. Plani',
    subtitle: 'Auditimi i Kërkesës, Diagnoza Korrigjuese & Master Plani',
    getPrompt: (docName: string) => `[DIREKTIVË FORENZIKE — SHTJELLA 3: KUNDËRSHTIMET DHE PLANI]\nDokumenti: "${docName}"\nDETYRË: Gjenero SHTJELLËN 3 me Claude Sonnet 4.6:\n- Seksioni 6: Auditimi i Kërkesës, Vlerësimi i Rreziqeve Procedurale dhe Forca Ekzekutive.\n- Seksioni 7: Diagnoza Korrigjuese dhe Rekomandimet Taktike mbi Goditjen e Shkresës.\n- Seksioni 8: Master Plani i Veprimit me Hapat Proceduralë dhe Afatet e Prera Ligjore.`
  }
};

const CASE_PILLAR_CONFIGS: Record<PillarType, { title: string; shortTitle: string; subtitle: string; prompt: string }> = {
  PILLAR_1: {
    title: '1. Fakti & Historiku',
    shortTitle: '1. Historiku',
    subtitle: 'Diagnoza Fillestare, Kronologjia e Ngjarjeve & Kryqëzimi',
    prompt: `[DIREKTIVË FORENZIKE MASTER — SHTJELLA 1: FAKTI & HISTORIKU]\nGjenero Seksionet 1 dhe 2 për të gjithë fashikullin e lëndës me Claude Sonnet 4.6:\n- Seksioni 1: Diagnoza Procedurale dhe Gjendja Faktike e Dosjes.\n- Seksioni 2: Rindërtimi Kronologjik i Datave dhe Veprimeve Vendimtare Procedurale.\n- Kryqëzimi i Dëshmive, Palëve, Gjyqtarëve dhe Ekspertëve nga provat reale.`
  },
  PILLAR_2: {
    title: '2. Shkeljet & Nenet',
    shortTitle: '2. Shkeljet',
    subtitle: 'Matrica e Provave & Tabela e Neneve të Gjykatës Supreme',
    prompt: `[DIREKTIVË FORENZIKE MASTER — SHTJELLA 2: SHKELJET & NENET]\nGjenero Seksionet 3, 4 dhe 5 për të gjithë fashikullin me Claude Sonnet 4.6:\n- Seksioni 3: Matrica e Provave Materiale dhe Provat Kontradiktore.\n- Seksioni 4: Tabela e Nxjerrjes së Neneve të Kosovës (Neni X i [Ligjit]).\n- Seksioni 5: Përgjegjësia Ligjore dhe Shkeljet Thelbësore (Neni 182 LPK / KPP).`
  },
  PILLAR_3: {
    title: '3. Plani i Veprimit',
    shortTitle: '3. Plani',
    subtitle: 'Mjetet Juridike, Prapësimet & Master Strategjia e Seancës',
    prompt: `[DIREKTIVË FORENZIKE MASTER — SHTJELLA 3: PLANI I VEPRIMIT]\nGjenero Seksionet 6, 7 dhe 8 për të gjithë fashikullin me Claude Sonnet 4.6:\n- Seksioni 6: Përgatitja e Mjeteve Juridike (Ankesa, Prapësime, Padi, Masë Sigurimi).\n- Seksioni 7: Pyetësori Taktik për Seancë me Pyetje Kurth.\n- Seksioni 8: Master Plani i Veprimit me Afate të Prera.`
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

  // Ndërrimi i skedës në Mobile/Tablet (< lg)
  const [mobileActiveTab, setMobileActiveTab] = useState<'DOCS' | 'AUTOPSY'>('DOCS');

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

  // Shikuesi i dokumenteve PDF
  const [viewingDoc, setViewingDoc] = useState<ForensicDocItem | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);

  // MODAL I DEDIKUAR PËR TEKSTIN E EKSTRAKTUAR
  const [extractedModalData, setExtractedModalData] = useState<{
    docName: string;
    text: string;
  } | null>(null);
  const [loadingTextDocId, setLoadingTextDocId] = useState<string | null>(null);
  const [copiedExtractedText, setCopiedExtractedText] = useState<boolean>(false);

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
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1;
    } catch {
      return 1;
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
    setFontLevelIndex(1);
    try { localStorage.setItem('juristi_forensic_font_size', '1'); } catch {}
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
      const pillars = await forensicDeskService.getForensicCasePillars(caseId);
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

  const loadDocuments = useCallback(async (silent: boolean = false) => {
    if (!caseId) return;
    if (!silent) setLoadingDocs(true);
    try {
      const docs = await forensicDeskService.listForensicDocuments(caseId);
      setDocuments(docs);

      if (docs.length > 0 && !selectedDocId) {
        setSelectedDocId(docs[0].id);
      }
    } catch (err) {
      console.error("Dështoi ngarkimi i dokumenteve forenzike:", err);
    } finally {
      if (!silent) setLoadingDocs(false);
    }
  }, [caseId, selectedDocId]);

  // AUTO-POLLING NËSE KA DOKUMENTE NË 'PROCESSING'
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
        setUploadProgressText(`Duke ngarkuar: ${file.name}...`);
        await forensicDeskService.uploadForensicDocument(caseId, file);
      }
      setUploadProgressText("Shkresat u ngarkuan. Po fillon procesimi...");
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
    if (!token) {
      alert('Token mungon. Ju lutemi kyçuni përsëri.');
      return;
    }

    let streamUrl = '';
    if (doc.media_type === 'audio') {
      streamUrl = forensicDeskService.getForensicAudioStreamUrl(caseId, doc.media_id, token);
    } else if (doc.media_type === 'video') {
      streamUrl = forensicDeskService.getForensicVisualStreamUrl(caseId, doc.media_id, token);
    } else if (doc.media_type === 'image') {
      streamUrl = forensicDeskService.getForensicVisualStreamUrl(caseId, doc.media_id, token);
    }

    if (streamUrl) {
      window.open(streamUrl, '_blank', 'noopener,noreferrer');
    }
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
        alert("Teksti i ekstraktuar nuk është i disponueshëm për këtë dokument (mund të jetë ende në procesim).");
        return;
      }

      setExtractedModalData({
        docName: doc.file_name,
        text: text
      });
      setCopiedExtractedText(false);
    } catch (err) {
      console.error("Dështoi ngarkimi i tekstit të ekstraktuar:", err);
      alert("Teksti i ekstraktuar nuk është i disponueshëm për këtë dokument.");
    } finally {
      setLoadingTextDocId(null);
    }
  };

  const handleCopyExtractedModalText = () => {
    if (!extractedModalData?.text) return;
    navigator.clipboard.writeText(extractedModalData.text);
    setCopiedExtractedText(true);
    setTimeout(() => setCopiedExtractedText(false), 2000);
  };

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

  const handleArchiveDocument = async (doc: ForensicDocItem, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!caseId) return;
    const confirmArchive = window.confirm(`A dëshironi ta arkivoni shkresën "${doc.file_name}"?`);
    if (!confirmArchive) return;

    setArchivingDocId(doc.id);
    try {
      await apiClient.post(`/forensic/documents/${caseId}/${doc.id}/archive`);
      setDocuments(prev =>
        prev.map(d =>
          d.id === doc.id ? { ...d, status: 'ARCHIVED' } : d
        )
      );
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
    const confirmSingleDelete = window.confirm(`A jeni i sigurt që doni të fshini nga MongoDB VETËM "${activeCfg.title}"?`);
    if (!confirmSingleDelete) return;

    setIsDeletingPillars(true);
    try {
      if (autopsyScope === 'DOCUMENT') {
        if (!selectedDocId) return;
        await forensicDeskService.deleteForensicDocPillar(caseId, selectedDocId, activePillar);
        setDocPillars(prev => ({ ...prev, [activePillar]: '' }));
      } else {
        await forensicDeskService.deleteForensicCasePillar(caseId, activePillar);
        setCasePillars(prev => ({ ...prev, [activePillar]: '' }));
      }
    } catch (err) {
      console.error("Failed to purge single pillar:", err);
      alert("Dështoi pastrimi i kësaj shtjelle.");
    } finally {
      setIsDeletingPillars(false);
    }
  };

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

      const prompt = DOC_PILLAR_CONFIGS[pillar].getPrompt(targetDoc.file_name);
      try {
        const stream = await forensicDeskService.streamForensicChat(
          caseId,
          prompt,
          `Ekspertizë mbi shkresën: ${targetDoc.file_name}`
        );
        const reader = stream.getReader();
        const decoder = new TextDecoder('utf-8');
        let accumulated = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          accumulated += chunk;
          setDocPillars(prev => ({ ...prev, [pillar]: accumulated }));
        }

        if (accumulated.trim().length > 50) {
          try {
            await forensicDeskService.saveForensicDocPillarContent(caseId, targetDoc.id, pillar, accumulated);
          } catch (saveErr) {
            console.warn("Could not save doc pillar:", saveErr);
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

      const prompt = CASE_PILLAR_CONFIGS[pillar].prompt;
      try {
        const stream = await forensicDeskService.streamForensicChat(
          caseId,
          prompt,
          `Ekspertizë master mbi të gjithë fashikullin e lëndës.`
        );
        const reader = stream.getReader();
        const decoder = new TextDecoder('utf-8');
        let accumulated = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          accumulated += chunk;
          setCasePillars(prev => ({ ...prev, [pillar]: accumulated }));
        }

        if (accumulated.trim().length > 50) {
          try {
            await forensicDeskService.saveForensicCasePillarContent(caseId, pillar, accumulated);
          } catch (saveErr) {
            console.warn("Could not save case pillar:", saveErr);
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

      await forensicDeskService.sealCustody(caseId, `Arkivim i analizës: ${activeTitle}`, []);
      setArchiveReportSuccess(true);
      setTimeout(() => setArchiveReportSuccess(false), 3000);
      if (onEvidenceChange) onEvidenceChange();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi arkivimi i raportit.");
    } finally {
      setIsArchivingReport(false);
    }
  };

  const filteredDocs = documents.filter(d =>
    (d.file_name || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const currentConfigs = autopsyScope === 'DOCUMENT' ? DOC_PILLAR_CONFIGS : CASE_PILLAR_CONFIGS;

  const handleCloseViewer = () => {
    setViewingDoc(null);
    setViewingUrl(null);
  };

  const wordCount = useMemo(() => {
    if (!extractedModalData?.text) return 0;
    return extractedModalData.text.trim().split(/\s+/).filter(Boolean).length;
  }, [extractedModalData?.text]);

  const charCount = extractedModalData?.text?.length || 0;

  return (
    <div className="space-y-4 select-none relative">
      
      {/* SHIRITI I KALIMIT NË MOBILE & TABLET (< lg) */}
      <div className="flex lg:hidden items-center bg-surface border border-main rounded-2xl p-1 shadow-sm">
        <button
          type="button"
          onClick={() => setMobileActiveTab('DOCS')}
          className={`flex-1 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            mobileActiveTab === 'DOCS'
              ? 'bg-primary-start text-white shadow-sm'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          <FileText size={14} />
          <span>Shkresat ({documents.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setMobileActiveTab('AUTOPSY')}
          className={`flex-1 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            mobileActiveTab === 'AUTOPSY'
              ? 'bg-primary-start text-white shadow-sm'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          <Scale size={14} />
          <span>Autopsia & Shtjellat</span>
        </button>
      </div>

      {/* RRJETI KRYESOR (GRID) */}
      <div className={`grid grid-cols-1 ${isFullscreen ? 'lg:grid-cols-1' : 'lg:grid-cols-12'} gap-4 sm:gap-6 transition-all duration-300`}>
        
        {/* KOLONA E MAJTË: SHKRESAT */}
        {(!isFullscreen && (mobileActiveTab === 'DOCS' || window.innerWidth >= 1024)) && (
          <div className="lg:col-span-5 space-y-3 sm:space-y-4">
            
            {/* Zona e Ngarkimit */}
            <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-2.5 sm:space-y-3">
              <div className="flex items-center justify-between border-b border-main pb-2">
                <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                  <FileText size={15} className="text-primary-start" /> Administrimi i Shkresave
                </h3>
                <span className="text-[10px] sm:text-[11px] font-mono text-text-muted">Vision OCR</span>
              </div>

              <div
                onClick={() => !isUploading && fileInputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  if (!isUploading) handleUploadFiles(e.dataTransfer.files);
                }}
                className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-xl sm:rounded-2xl p-4 sm:p-5 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-1.5"
              >
                {isUploading ? (
                  <div className="flex flex-col items-center justify-center gap-2 py-1">
                    <Loader2 size={20} className="animate-spin text-primary-start" />
                    <span className="text-xs sm:text-sm font-bold text-primary-start">{uploadProgressText}</span>
                  </div>
                ) : (
                  <>
                    <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                      <UploadCloud size={18} className="sm:w-5 sm:h-5" />
                    </div>
                    <div>
                      <p className="text-xs sm:text-sm font-bold text-text-primary">Kliko ose tërhiq shkresat</p>
                      <p className="text-[10px] sm:text-[11px] text-text-muted">PDF, DOCX, Skanime të zbardhura me AI</p>
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

            {/* Lista e Dokumenteve */}
            <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="relative flex-1">
                  <Search size={13} className="absolute left-3 top-2.5 text-text-muted" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Filtro shkresat..."
                    className="w-full bg-surface border border-main rounded-xl pl-8 pr-3 py-1.5 text-xs sm:text-sm text-text-primary focus:outline-none focus:border-primary-start"
                  />
                </div>
                <button
                  onClick={() => loadDocuments(false)}
                  title="Rifresko listën"
                  className="p-2 bg-surface hover:bg-hover border border-main rounded-xl text-text-muted hover:text-text-primary transition-colors cursor-pointer shrink-0"
                >
                  <RefreshCw size={13} className={loadingDocs ? 'animate-spin' : ''} />
                </button>
              </div>

              <div className="space-y-2 max-h-[360px] sm:max-h-[420px] overflow-y-auto custom-finance-scroll pr-1">
                {filteredDocs.length === 0 ? (
                  <div className="text-center py-8 text-xs sm:text-sm text-text-muted">
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
                        onClick={() => {
                          setSelectedDocId(doc.id);
                          setAutopsyScope('DOCUMENT');
                          setActivePillar('PILLAR_1');
                          if (window.innerWidth < 1024) {
                            setMobileActiveTab('AUTOPSY');
                          }
                        }}
                        className={`p-2.5 sm:p-3 rounded-xl sm:rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-2 sm:gap-3 ${
                          isSelected && autopsyScope === 'DOCUMENT'
                            ? 'bg-primary-start/10 border-primary-start text-primary-start shadow-sm'
                            : 'bg-surface border-main hover:border-primary-start/40 text-text-primary'
                        } ${isArchived ? 'opacity-60' : ''}`}
                      >
                        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
                          <div className={`p-1.5 sm:p-2 rounded-xl shrink-0 ${isSelected && autopsyScope === 'DOCUMENT' ? 'bg-primary-start text-white' : 'bg-surface/80 text-text-muted'}`}>
                            {isMedia ? <Play size={15} /> : <FileText size={15} />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-bold truncate text-xs sm:text-sm text-text-primary">
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

                        <div className="flex items-center gap-0.5 sm:gap-1 shrink-0">
                          {isMedia ? (
                            <button
                              type="button"
                              onClick={(e) => handleViewMediaDocument(doc, e)}
                              title="Luaj"
                              className="p-1.5 text-text-muted hover:text-blue-500 rounded-lg hover:bg-blue-500/10 transition-colors cursor-pointer"
                            >
                              <Play size={14} />
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) => handleViewDocument(doc, e)}
                              title="Shiko origjinalin"
                              className="p-1.5 text-text-muted hover:text-blue-500 rounded-lg hover:bg-blue-500/10 transition-colors cursor-pointer"
                            >
                              <Eye size={14} />
                            </button>
                          )}

                          {!isMedia && (
                            <button
                              type="button"
                              onClick={(e) => handleViewExtractedText(doc, e)}
                              disabled={isTextLoading}
                              title="Shiko tekstin"
                              className={`p-1.5 rounded-lg transition-colors cursor-pointer disabled:opacity-40 ${
                                isProcessing 
                                  ? 'text-amber-500 hover:bg-amber-500/10' 
                                  : 'text-text-muted hover:text-emerald-500 hover:bg-emerald-500/10'
                              }`}
                            >
                              {isTextLoading ? <Loader2 size={14} className="animate-spin text-emerald-500" /> : <FileSearch size={14} />}
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={(e) => handleRenameDocument(doc, e)}
                            title="Riemërto"
                            className="hidden sm:inline-flex p-1.5 text-text-muted hover:text-amber-500 rounded-lg hover:bg-amber-500/10 transition-colors cursor-pointer"
                          >
                            <Pencil size={14} />
                          </button>

                          <button
                            type="button"
                            onClick={(e) => handleArchiveDocument(doc, e)}
                            disabled={isArchiving || isArchived}
                            title="Arkivo"
                            className="hidden sm:inline-flex p-1.5 text-text-muted hover:text-purple-500 rounded-lg hover:bg-purple-500/10 transition-colors cursor-pointer disabled:opacity-40"
                          >
                            {isArchiving ? <Loader2 size={14} className="animate-spin text-purple-500" /> : <Archive size={14} />}
                          </button>

                          <button
                            type="button"
                            onClick={(e) => handleDeleteDocument(doc.id, doc.file_name, e)}
                            disabled={isDeleting}
                            title="Fshi"
                            className="p-1.5 text-text-muted hover:text-rose-500 rounded-lg hover:bg-rose-500/10 transition-colors cursor-pointer disabled:opacity-40"
                          >
                            {isDeleting ? <Loader2 size={14} className="animate-spin text-rose-500" /> : <Trash2 size={14} />}
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

        {/* KOLONA E DJATHTË: AUTOPSIA */}
        {(!isFullscreen && (mobileActiveTab === 'AUTOPSY' || window.innerWidth >= 1024)) && (
          <div className={`${isFullscreen ? 'lg:col-span-12' : 'lg:col-span-7'} glass-panel p-4 sm:p-6 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3 sm:space-y-4 flex flex-col justify-between transition-all duration-300 relative`}>
            <div className="space-y-3">
              
              {/* Shirit i Veprimeve të Autopsisë */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-main pb-3">
                
                {/* Zgjedhja e Shtrirjes (Dokument vs Rast) */}
                <div className="flex items-center bg-surface border border-main rounded-xl p-1 shrink-0 w-full sm:w-auto">
                  <button
                    type="button"
                    onClick={() => {
                      setAutopsyScope('DOCUMENT');
                      setActivePillar('PILLAR_1');
                    }}
                    className={`flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs sm:text-sm font-bold uppercase tracking-wider transition-all cursor-pointer ${
                      autopsyScope === 'DOCUMENT'
                        ? 'bg-primary-start text-white shadow-sm'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    Dokument
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setAutopsyScope('CASE');
                      setActivePillar('PILLAR_1');
                    }}
                    className={`flex-1 sm:flex-initial px-3 py-1.5 rounded-lg text-xs sm:text-sm font-bold uppercase tracking-wider transition-all cursor-pointer ${
                      autopsyScope === 'CASE'
                        ? 'bg-primary-start text-white shadow-sm'
                        : 'text-text-muted hover:text-text-primary'
                    }`}
                  >
                    Rast i Plotë
                  </button>
                </div>

                {/* Butonat e Madhësisë dhe Veprimeve */}
                <div className="flex items-center justify-between sm:justify-end gap-1.5 flex-wrap">
                  <div className="flex items-center gap-0.5 rounded-xl border border-main bg-surface p-1">
                    <button
                      type="button"
                      onClick={handleDecreaseFont}
                      disabled={fontLevelIndex === 0}
                      className="h-6 w-6 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30"
                    >
                      A−
                    </button>
                    <button
                      type="button"
                      onClick={handleResetFont}
                      className="min-w-8 rounded-lg px-1 text-[10px] font-bold text-text-muted hover:bg-hover"
                    >
                      {activeFont.label}
                    </button>
                    <button
                      type="button"
                      onClick={handleIncreaseFont}
                      disabled={fontLevelIndex === FONT_LEVELS.length - 1}
                      className="h-6 w-6 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30"
                    >
                      A+
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={handleAdminPurgeSinglePillar}
                    disabled={isDeletingPillars || !currentPillarContent}
                    className="h-8 w-8 bg-surface hover:bg-rose-500/10 border border-main text-text-muted hover:text-rose-500 rounded-xl flex items-center justify-center transition-all disabled:opacity-30 cursor-pointer"
                    title="Fshi këtë shtjellë"
                  >
                    {isDeletingPillars ? <Loader2 size={13} className="animate-spin text-rose-500" /> : <Trash2 size={13} />}
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsFullscreen(!isFullscreen)}
                    className="hidden sm:flex h-8 w-8 bg-surface hover:bg-hover border border-main rounded-xl text-text-primary items-center justify-center transition-all cursor-pointer"
                    title="Fullscreen"
                  >
                    {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                  </button>

                  <button
                    type="button"
                    onClick={handleCopyReport}
                    disabled={!currentPillarContent}
                    className="h-8 px-2.5 sm:px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center justify-center transition-all disabled:opacity-40 cursor-pointer"
                  >
                    <span>{copiedReport ? 'U Kopjua' : 'Kopjo'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleArchiveReport}
                    disabled={isArchivingReport || !currentPillarContent}
                    className="h-8 px-3 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center justify-center transition-all disabled:opacity-40 cursor-pointer"
                  >
                    {isArchivingReport ? <Loader2 size={13} className="animate-spin" /> : <span>{archiveReportSuccess ? 'U Ruajt!' : 'Arkivo'}</span>}
                  </button>
                </div>
              </div>

              {/* Informacioni i Dokumentit Aktiv */}
              <div className="text-xs sm:text-sm text-text-muted truncate">
                {autopsyScope === 'DOCUMENT' ? (
                  <p className="truncate">
                    Dokumenti: <span className="font-bold text-text-primary">{activeDoc?.file_name || 'Asnjë i përzgjedhur'}</span>
                  </p>
                ) : (
                  <p className="truncate">
                    Fashikulli: <span className="font-bold text-text-primary">Ekspertizë Master mbi Lëndën</span>
                  </p>
                )}
              </div>

              {/* SHIRITI I 3 SHTJELLAVE */}
              <div className="grid grid-cols-3 gap-1 sm:gap-2">
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
                      className={`px-2 sm:px-3 py-2 rounded-xl text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center sm:justify-between gap-1 transition-all cursor-pointer border ${
                        isSelected
                          ? pillarKey === 'PILLAR_1'
                            ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                            : pillarKey === 'PILLAR_2'
                            ? 'bg-amber-600 text-white border-amber-600 shadow-sm'
                            : 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                          : 'bg-surface hover:bg-hover text-text-muted border-main'
                      }`}
                    >
                      <div className="flex items-center gap-1 truncate">
                        {isLoading ? (
                          <Loader2 size={11} className="animate-spin text-white shrink-0" />
                        ) : hasContent ? (
                          <CheckCircle2 size={11} className={isSelected ? 'text-white shrink-0' : 'text-emerald-500 shrink-0'} />
                        ) : null}
                        <span className="truncate sm:hidden">{cfg.shortTitle}</span>
                        <span className="truncate hidden sm:inline">{cfg.title}</span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Nëntitulli i Shtjellës dhe Butoni Rigjenero */}
              <div className="py-0.5 flex items-center justify-between gap-2 text-text-muted text-[11px] sm:text-xs">
                <p className="truncate font-medium">{currentConfigs[activePillar].subtitle}</p>
                {currentPillarContent && !isCurrentPillarLoading && (
                  <button
                    type="button"
                    onClick={() => handleGeneratePillar(activePillar)}
                    className="text-primary-start font-bold hover:underline cursor-pointer shrink-0"
                  >
                    Rigjenero
                  </button>
                )}
              </div>

              {/* TRUPI I TEKSTIT TË AUTOPSISË */}
              <div 
                ref={scrollContainerRef}
                onScroll={handleScroll}
                className={`${isFullscreen ? 'h-[620px]' : 'h-[380px] sm:h-[460px]'} overflow-y-auto custom-finance-scroll p-3.5 sm:p-6 bg-surface/50 rounded-2xl border border-main text-text-primary select-text flex flex-col relative transition-all duration-200`}
              >
                <style>{`
                  .dynamic-forensic-report p,
                  .dynamic-forensic-report li,
                  .dynamic-forensic-report span:not(.lucide) {
                    font-size: ${activeFont.base}px !important;
                    line-height: ${activeFont.line} !important;
                  }
                  .dynamic-forensic-report td {
                    font-size: ${Math.max(11, activeFont.base - 2)}px !important;
                    line-height: 1.4 !important;
                    padding: 4px 6px !important;
                  }
                  .dynamic-forensic-report th {
                    font-size: ${Math.max(11, activeFont.base - 2)}px !important;
                    padding: 6px 6px !important;
                  }
                  .dynamic-forensic-report h1 {
                    font-size: ${activeFont.h1}px !important;
                    line-height: 1.25 !important;
                    margin-top: 1em !important;
                    margin-bottom: 0.4em !important;
                  }
                  .dynamic-forensic-report h2 {
                    font-size: ${activeFont.h2}px !important;
                    line-height: 1.3 !important;
                    margin-top: 0.9em !important;
                    margin-bottom: 0.3em !important;
                  }
                  .dynamic-forensic-report h3 {
                    font-size: ${activeFont.h3}px !important;
                    line-height: 1.35 !important;
                    margin-top: 0.8em !important;
                    margin-bottom: 0.25em !important;
                  }
                  .dynamic-forensic-report table {
                    display: block !important;
                    width: 100% !important;
                    overflow-x: auto !important;
                    -webkit-overflow-scrolling: touch !important;
                    margin: 0.8em 0 !important;
                  }
                `}</style>

                {!currentPillarContent && !isCurrentPillarLoading ? (
                  <div className="flex-1 flex flex-col items-center justify-center text-center p-4 sm:p-8 my-auto space-y-3">
                    <h4 className="text-sm sm:text-base font-black uppercase tracking-tight text-text-primary">
                      {currentConfigs[activePillar].title}
                    </h4>
                    <p className="text-xs sm:text-sm text-text-muted max-w-xs sm:max-w-sm">
                      Kjo shtjellë është gati për ekzaminim doktrinar.
                    </p>
                    <button
                      type="button"
                      onClick={() => handleGeneratePillar(activePillar)}
                      className="px-5 py-2.5 bg-primary-start hover:brightness-110 text-white rounded-xl font-bold text-xs sm:text-sm uppercase tracking-wider shadow-md flex items-center justify-center cursor-pointer transition-all hover-lift"
                    >
                      <span>Analizo {currentConfigs[activePillar].shortTitle}</span>
                    </button>
                  </div>
                ) : isCurrentPillarLoading && !currentPillarContent ? (
                  <div className="flex-1 flex flex-col items-center justify-center p-6 my-auto">
                    <Loader2 className="w-8 h-8 animate-spin text-primary-start mb-2" />
                    <p className="text-xs sm:text-sm font-bold text-text-primary uppercase tracking-wider">
                      Duke analizuar {currentConfigs[activePillar].title}...
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
                    className="sticky bottom-2 right-2 ml-auto z-20 px-2.5 py-1 bg-slate-900 text-white text-xs font-bold rounded-full shadow-lg border border-slate-700 flex items-center gap-1 cursor-pointer"
                  >
                    <span>Poshtë</span>
                    <ArrowDown size={12} className="animate-bounce" />
                  </button>
                )}
              </div>
            </div>

            <div className="pt-2.5 border-t border-main flex items-center justify-between text-[10px] sm:text-xs text-text-muted">
              <span className="font-medium truncate">
                Pajtueshëm me Gjykatën Supreme të Kosovës
              </span>
              <span className="font-mono text-[10px] shrink-0">Claude Sonnet 4.6</span>
            </div>
          </div>
        )}
      </div>

      {/* MODAL I TEKSTIT TË EKSTRAKTUAR */}
      {extractedModalData && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-2.5 sm:p-6 md:p-8">
          <div className="relative w-full max-w-6xl xl:max-w-7xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col h-[90vh] sm:h-[88vh] animate-in fade-in zoom-in-95 duration-200">
            
            <div className="flex items-center justify-between px-4 sm:px-8 py-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-900/90 gap-2 shrink-0">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
                  <FileText size={18} className="sm:w-5 sm:h-5" />
                </div>
                <div className="truncate">
                  <h3 className="text-xs sm:text-base font-bold text-slate-900 dark:text-slate-100 truncate">
                    {extractedModalData.docName}
                  </h3>
                  <p className="text-[10px] sm:text-xs text-slate-500 dark:text-slate-400 font-mono">
                    {wordCount.toLocaleString()} fjalë • {charCount.toLocaleString()} karaktere
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
                <button
                  type="button"
                  onClick={handleCopyExtractedModalText}
                  className="px-2.5 sm:px-3.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer border border-slate-200 dark:border-slate-700"
                >
                  {copiedExtractedText ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                  <span className="hidden xs:inline">{copiedExtractedText ? 'U Kopjua!' : 'Kopjo'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setExtractedModalData(null)}
                  className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
                  title="Mbyll"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="p-4 sm:p-8 md:p-10 overflow-y-auto custom-finance-scroll bg-white dark:bg-slate-950 flex-1">
              <pre className="whitespace-pre-wrap font-sans text-xs sm:text-sm md:text-base leading-relaxed text-slate-800 dark:text-slate-200 select-text font-normal max-w-none">
                {extractedModalData.text}
              </pre>
            </div>

            <div className="px-4 sm:px-8 py-2.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/80 flex items-center justify-between text-[11px] text-slate-500 shrink-0">
              <span className="hidden sm:inline">Korpus ligjor i indeksuar me AI</span>
              <button
                type="button"
                onClick={() => setExtractedModalData(null)}
                className="font-bold text-slate-700 dark:text-slate-300 hover:underline cursor-pointer ml-auto"
              >
                Mbyll Dritaren
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modals for Document Actions */}
      {viewingDoc && (
        <PDFViewerModal
          documentData={viewingDoc as any}
          caseId={caseId}
          onClose={handleCloseViewer}
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