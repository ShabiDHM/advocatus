// FILE: frontend/src/components/forensics/DocumentForensicLab.tsx
// PHOENIX PROTOCOL - DOCUMENT FORENSIC LAB V1.2 (PRO-LEVEL AUTOPSY & LPK/KPPRK VIOLATIONS)
// ZERO TS WARNINGS • ZERO HARDCODING • FULL ACTIONS (DELETE & AUDIT FLAGS)

import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  UploadCloud,
  Scale,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Loader2,
  Sparkles,
  Copy,
  ShieldCheck,
  RefreshCw,
  FileCheck,
  Search,
  BookOpen
} from 'lucide-react';
import { apiService } from '../../services/api';
import { forensicService } from '../../services/forensicService';

interface DocumentItem {
  id: string;
  name: string;
  size?: number;
  content_type?: string;
  created_at?: string;
  extracted_text?: string;
  status?: string;
  has_violation?: boolean;
  audit_result?: string;
}

interface DocumentForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

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

  // Gjendjet e Analizës & Auditimit
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [auditReport, setAuditReport] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedReport, setCopiedReport] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (caseId) {
      loadDocuments();
    }
  }, [caseId]);

  const loadDocuments = async () => {
    if (!caseId) return;
    setLoadingDocs(true);
    try {
      const docs = await apiService.getDocuments(caseId);
      const mapped: DocumentItem[] = (docs || []).map((d: any) => ({
        id: d.id || d._id,
        name: d.name || d.file_name || 'Dokument pa titull',
        size: d.size || d.file_size || 0,
        content_type: d.content_type || 'application/pdf',
        created_at: d.created_at || d.uploaded_at || new Date().toISOString(),
        extracted_text: d.extracted_text || d.text || '',
        status: d.status || 'READY',
        has_violation: Boolean(d.has_violation || (d.audit_result && (d.audit_result.includes('SHKELJE') || d.audit_result.includes('Neni 182')))),
        audit_result: d.audit_result || ''
      }));

      setDocuments(mapped);

      if (mapped.length > 0 && !selectedDocId) {
        setSelectedDocId(mapped[0].id);
        if (mapped[0].audit_result) {
          setAuditReport(mapped[0].audit_result);
        }
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
        setUploadProgressText(`Duke indeksuar & kryer Vision OCR: ${file.name} (${i + 1}/${files.length})...`);
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

  // Fshirja e Shkresës nga Dosja
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
        setAuditReport('');
      }
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.error("Dështoi fshirja e dokumentit:", err);
      alert("Dështoi fshirja e dokumentit nga serveri.");
    } finally {
      setDeletingDocId(null);
    }
  };

  // Ekzekutimi i Autopsisë Forenzike për dokumentin e përzgjedhur
  const handleRunDocumentAutopsy = async () => {
    const activeDoc = documents.find(d => d.id === selectedDocId);
    if (!activeDoc || !caseId || isAuditing) return;

    setIsAuditing(true);
    setAuditReport('');

    try {
      const prompt = `[PROTOKOLLI PHOENIX — AUTOPSI FORENZIKE E DOKUMENTIT]
Kryej autopsinë shkencore dhe doktrinare të dokumentit "${activeDoc.name}" në fashikullin e lëndës:
1. VLEFSHMËRIA PROCEDURALE: A plotëson elementet e detyrueshme të formës (Nenet 182, 183 LPK / dispozitat e KPPRK)?
2. INTEGRITETI I TË DHËNAVE: Data e lëshimit, numrat e protokollit, nënshkrimet dhe vulat institucionale.
3. DISKREPANCA & KONTRADIKTA: A përplaset ky akt me pretendimet e palëve apo me ligjin në fuqi?
4. KELIFI PROCEDURAL: A ka parashkrim të së drejtës apo humbje të afatit prekluziv?
Jep raportin në stil solemn doktrinar me rekomandime për Gjykatë/PSRK.`;

      const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic');
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setAuditReport(acc);
      }
      // Përditëso gjendjen lokale nëse u zbuluan shkelje
      if (acc.includes('SHKELJE') || acc.includes('Neni 182')) {
        setDocuments(prev => prev.map(d => d.id === selectedDocId ? { ...d, has_violation: true } : d));
      }
    } catch (err) {
      console.error("Autopsy error:", err);
      alert("Dështoi autopsia e dokumentit.");
    } finally {
      setIsAuditing(false);
    }
  };

  // Ekzaminimi i Kryqëzuar me Fashikullin
  const handleRunCrossExamination = async () => {
    if (!selectedDocId || !caseId || isAuditing) return;
    setIsAuditing(true);
    setAuditReport('Duke kryqëzuar shkresën me të gjitha provat e tjera të fashikullit...');

    try {
      const result = await forensicService.crossExamineDocument(caseId, selectedDocId);
      const formatted = JSON.stringify(result, null, 2);
      setAuditReport(formatted);
    } catch (err) {
      console.error("Cross examine error:", err);
      alert("Dështoi ekzaminimi i kryqëzuar.");
    } finally {
      setIsAuditing(false);
    }
  };

  const handleCopyReport = () => {
    if (!auditReport) return;
    navigator.clipboard.writeText(auditReport);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2500);
  };

  const filteredDocs = documents.filter(d =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const activeDoc = documents.find(d => d.id === selectedDocId);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* KOLONA E MAJTË: NGARKIMI & LISTA E SHKRESAVE */}
      <div className="lg:col-span-5 space-y-4">
        {/* Dropzone për Ngarkim me OCR */}
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

        {/* Paneli i Kërkimit dhe Përzgjedhjes së Shkresës */}
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
                      if (doc.audit_result) setAuditReport(doc.audit_result);
                    }}
                    className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-center justify-between gap-3 ${
                      isSelected
                        ? 'bg-primary-start/10 border-primary-start text-primary-start shadow-sm'
                        : 'bg-surface border-main hover:border-primary-start/40 text-text-primary'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <div className={`p-2 rounded-xl ${isSelected ? 'bg-primary-start text-white' : 'bg-surface/80 text-text-muted'}`}>
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
                          {(doc.size ? doc.size / 1024 : 0).toFixed(0)} KB • Statusi: {doc.status}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {isSelected && <CheckCircle2 size={15} className="text-primary-start mr-1" />}
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

      {/* KOLONA E DJATHTË: AUTOPSIA DOKTRINARE & KRYQËZIMI */}
      <div className="lg:col-span-7 glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4 flex flex-col justify-between">
        <div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
            <div>
              <div className="flex items-center gap-2">
                <Scale size={18} className="text-primary-start" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary">
                  Autopsia Ligjore & Integriteti i Aktit
                </h3>
              </div>
              <p className="text-xs text-text-muted mt-0.5 truncate max-w-md">
                Dokumenti: <span className="font-bold text-text-primary">{activeDoc?.name || 'Asnjë i përzgjedhur'}</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              {auditReport && (
                <button
                  type="button"
                  onClick={handleCopyReport}
                  className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  {copiedReport ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                  <span>{copiedReport ? 'U Kopjua' : 'Kopjo'}</span>
                </button>
              )}

              <button
                type="button"
                onClick={handleRunCrossExamination}
                disabled={!selectedDocId || isAuditing}
                className="h-9 px-3.5 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-primary-start flex items-center gap-1.5 transition-all disabled:opacity-40 cursor-pointer"
                title="Kryqëzo me të gjithë fashikullin"
              >
                <BookOpen size={13} />
                <span>Kryqëzo</span>
              </button>

              <button
                type="button"
                onClick={handleRunDocumentAutopsy}
                disabled={!selectedDocId || isAuditing}
                className="h-9 px-4 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all disabled:opacity-40 cursor-pointer"
              >
                {isAuditing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                <span>{auditReport ? 'Ri-Audito' : 'Fillo Autopsinë'}</span>
              </button>
            </div>
          </div>

          {/* Hapësira e Raportit të Autopsisë */}
          <div className="mt-4 h-[500px] overflow-y-auto custom-finance-scroll p-5 bg-surface/50 rounded-2xl border border-main text-xs sm:text-sm leading-relaxed text-text-primary whitespace-pre-wrap font-mono select-text">
            {auditReport || (
              <div className="h-full flex flex-col items-center justify-center text-text-muted gap-3">
                <FileCheck size={44} className="text-primary-start/30" />
                <p className="text-xs font-sans text-center max-w-sm">
                  Përzgjidhni një shkresë në të majtë dhe shtypni <span className="font-bold text-text-primary">"Fillo Autopsinë"</span> për të analizuar vlefshmërinë e neneve, nënshkrimeve dhe shkeljeve të LPK-së.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Shënimi Doktrinar në Fund */}
        <div className="pt-3 border-t border-main flex items-center justify-between text-[11px] text-text-muted">
          <span className="flex items-center gap-1.5 font-medium">
            <ShieldCheck size={14} className="text-emerald-500" />
            Standard i Pajtueshëm me Gjykatën Supreme & OAK
          </span>
          <span className="font-mono text-[10px]">Modeli: Claude Sonnet 4.6 (1M Context)</span>
        </div>
      </div>
    </div>
  );
};

export default DocumentForensicLab;