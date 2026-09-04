// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW PAGE V86.0 (TOTAL WIPEOUT INTEGRATION FOR SINGLE DOCUMENT AUDIT)

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Case, Document, DeletedDocumentResponse, ChatMessage } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import ChatPanel, { ChatMode, Jurisdiction, ReasoningMode } from '../components/ChatPanel';
import PDFViewerModal from '../components/FileViewerModal';
import DockedPDFViewer from '../components/DockedPDFViewer';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { AlertCircle } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { extractAndNormalizeHistory, getUserSalutation } from '../utils/caseHelpers';
import { CaseHeaderBar } from '../components/case/CaseHeaderBar';
import { EvidenceVaultPanel } from '../components/case/EvidenceVaultPanel';
import { RenameDocumentModal } from '../components/case/RenameDocumentModal';
import { CaseAnalysisModal } from '../components/case/CaseAnalysisModal';
import { DocumentAuditModal } from '../components/case/DocumentAuditModal';

type CaseData = { details: Case | null };

const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading, isAuthenticated, user } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();

  const [caseData, setCaseData] = useState<CaseData>({ details: null });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const [minimizedDocument, setMinimizedDocument] = useState<Document | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);
  const [viewingInitialPage, setViewingInitialPage] = useState<number>(1);
  const [documentToRename, setDocumentToRename] = useState<Document | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  // 1. State për Analizën e Plotë të Lëndës (ANALIZO RASTIN)
  const [isAnalyzingCase, setIsAnalyzingCase] = useState<boolean>(false);
  const [analysisResultText, setAnalysisResultText] = useState<string>('');
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState<boolean>(false);

  // 2. State i Dedikuar për Auditimin e 1 Dokumenti (Peshorja ⚖️)
  const [isDocAuditModalOpen, setIsDocAuditModalOpen] = useState<boolean>(false);
  const [docAuditResultText, setDocAuditResultText] = useState<string>('');
  const [currentAuditedDoc, setCurrentAuditedDoc] = useState<Document | null>(null);
  const [isAuditingDoc, setIsAuditingDoc] = useState<boolean>(false);

  const isPro = true;
  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, connectionStatus, reconnect } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  const userSalutation = useMemo(() => getUserSalutation(user), [user]);
  const caseTitle = useMemo(() => (caseData.details as any)?.title || (caseData.details as any)?.case_name || 'Lënda Ligjore', [caseData.details]);
  const clientName = useMemo(() => (caseData.details as any)?.client_name || (caseData.details as any)?.client?.name || 'Klienti', [caseData.details]);
  const clientPosition = useMemo(() => (caseData.details as any)?.client_position || 'DEFENDANT', [caseData.details]);

  const saveToLocalStorage = useCallback((messages: ChatMessage[]) => {
    if (!caseId) return;
    localStorage.setItem(`chat_${caseId}`, JSON.stringify(messages));
  }, [caseId]);

  const loadFromLocalStorage = useCallback((): ChatMessage[] | null => {
    if (!caseId) return null;
    const stored = localStorage.getItem(`chat_${caseId}`);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          return parsed.filter((m) => m && typeof m.content === 'string' && m.content.trim() !== '');
        }
      } catch {
        return null;
      }
    }
    return null;
  }, [caseId]);

  const persistChatHistory = useCallback(async (messages: ChatMessage[]) => {
    saveToLocalStorage(messages);
    if (!caseId) return;
    try {
      await apiService.updateChatHistory(caseId, messages);
    } catch (err) {
      console.error('Failed to persist chat history:', err);
    }
  }, [caseId, saveToLocalStorage]);

  const fetchCaseData = useCallback(async (isInitialLoad = false) => {
    if (!caseId) return;
    if (isInitialLoad) setIsLoading(true);
    setError(null);
    try {
      const [details, initialDocs] = await Promise.all([
        apiService.getCaseDetails(caseId),
        apiService.getDocuments(caseId),
      ]);
      setCaseData({ details });
      setLiveDocuments((initialDocs || []).map(sanitizeDocument));

      const rawAnalysis = (details as any)?.latest_deep_analysis || (details as any)?.latest_comprehensive_analysis || (details as any)?.latest_analysis;
      if (typeof rawAnalysis === 'string' && rawAnalysis.trim().length > 100) {
        setAnalysisResultText(rawAnalysis.trim());
      }

      const backendMessages = extractAndNormalizeHistory(details);
      if (backendMessages.length > 0) {
        setChatMessages(backendMessages);
        saveToLocalStorage(backendMessages);
      } else {
        const localMessages = loadFromLocalStorage();
        if (localMessages && localMessages.length > 0) {
          setChatMessages(localMessages);
          persistChatHistory(localMessages);
        } else {
          setChatMessages([]);
        }
      }
    } catch {
      setError(t('error.failedToLoadCase', 'Dështoi ngarkimi i lëndës.'));
    } finally {
      if (isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments, loadFromLocalStorage, saveToLocalStorage, persistChatHistory]);

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);

  // Auto-Sync Polling
  useEffect(() => {
    const hasProcessingDocs = liveDocuments.some(
      (doc) => doc.status === 'PROCESSING' || doc.status === 'PENDING'
    );

    if (!hasProcessingDocs || !caseId) return;

    const interval = setInterval(async () => {
      try {
        const latestDocs = await apiService.getDocuments(caseId);
        if (Array.isArray(latestDocs)) {
          setLiveDocuments(latestDocs.map(sanitizeDocument));
        }
      } catch (err) {
        console.warn('Auto-sync documents polling error:', err);
      }
    }, 2500);

    return () => clearInterval(interval);
  }, [liveDocuments, caseId, setLiveDocuments]);

  const handleDocumentUploaded = (newDoc: Document) => setLiveDocuments((p) => [sanitizeDocument(newDoc), ...p]);
  const handleDocumentDeleted = (res: DeletedDocumentResponse) => setLiveDocuments((p) => p.filter((d) => String(d.id) !== String(res.documentId)));

  const handleViewOriginal = useCallback((doc: Document) => {
    setViewingInitialPage(1);
    setViewingUrl(`${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`);
    setViewingDocument(doc);
    setMinimizedDocument(null);
  }, [caseId]);

  // DËGJUESI 1: Për dokumentet e lëndës
  useEffect(() => {
    const handleOpenDocPreview = (e: any) => {
      const { fileName, href } = e.detail || {};
      if (!fileName && !href) return;

      const cleanSearch = (fileName || '').toString().toLowerCase().trim().replace(/^[\(\[\s"']+|[\)\]\s"']+$|\.pdf$/gi, '');
      const docIdFromHref = (href || '').match(/\/documents\/([a-f0-9]{24})/i)?.[1]?.toLowerCase();

      const matchedDoc = liveDocuments.find((doc) => {
        const docId = String(doc.id || (doc as any)._id || '').toLowerCase();
        if (docIdFromHref && docId === docIdFromHref) return true;
        if (href && href.toLowerCase().includes(docId)) return true;

        const docName = (doc.file_name || (doc as any).title || '').toLowerCase();
        if (cleanSearch && (docName.includes(cleanSearch) || cleanSearch.includes(docName.replace(/\.pdf$/i, '')))) {
          return true;
        }
        return false;
      });

      if (matchedDoc) {
        handleViewOriginal(matchedDoc);
      } else if (liveDocuments.length > 0 && cleanSearch) {
        const fuzzyMatch = liveDocuments.find((d) => {
          const words = cleanSearch.split(/\s+/).filter((w: string) => w.length > 3);
          const name = (d.file_name || (d as any).title || '').toLowerCase();
          return words.some((w: string) => name.includes(w));
        });
        if (fuzzyMatch) {
          handleViewOriginal(fuzzyMatch);
        }
      }
    };

    window.addEventListener('open_document_preview', handleOpenDocPreview);
    return () => window.removeEventListener('open_document_preview', handleOpenDocPreview);
  }, [liveDocuments, handleViewOriginal]);

  // DËGJUESI 2: Precedentët e Gjykatës Supreme
  useEffect(() => {
    const handleOpenPrecedent = async (e: any) => {
      const { caseNumber } = e.detail || {};
      if (!caseNumber) return;

      try {
        const cleanCaseNo = caseNumber.trim();
        const res = await apiService.axiosInstance.get('/laws/case-page', {
          params: { law_title: cleanCaseNo }
        });

        const targetPage = (res.data && res.data.page) ? Number(res.data.page) : 1;
        const rawLawTitle = (res.data && res.data.law_title) ? res.data.law_title : cleanCaseNo;
        const pdfFileName = rawLawTitle.toLowerCase().endsWith('.pdf') ? rawLawTitle : `${rawLawTitle}.pdf`;
        const encoded = encodeURIComponent(pdfFileName);

        const url = `${API_V1_URL}/laws/caselaw/pdf/${encoded}`;

        setViewingInitialPage(targetPage);
        setViewingUrl(url);
        setViewingDocument({
          id: cleanCaseNo,
          file_name: pdfFileName,
          mime_type: 'application/pdf',
          status: 'READY',
          created_at: new Date().toISOString()
        } as any);
        setMinimizedDocument(null);
      } catch (err) {
        console.error("Failed to open supreme precedent preview directly:", err);
      }
    };

    window.addEventListener('open_precedent_preview', handleOpenPrecedent);
    return () => window.removeEventListener('open_precedent_preview', handleOpenPrecedent);
  }, []);

  // 🧹 PASTRIMI TOTAL I CHATIT
  const handleClearChat = async () => {
    if (!caseId) return;
    try {
      await apiService.clearChatHistory(caseId);
      setChatMessages([]);
      setAnalysisResultText('');
      setCaseData((prev) => ({
        ...prev,
        details: prev.details ? ({
          ...prev.details,
          latest_deep_analysis: '',
          latest_comprehensive_analysis: '',
          analysis_dirty: true,
        } as any) : null,
      }));
      await persistChatHistory([]);
      localStorage.removeItem(`chat_${caseId}`);
    } catch {
      alert(t('error.generic', 'Ndodhi një gabim.'));
    }
  };

  const handleDeleteAnalysisFromModal = useCallback(() => {
    setAnalysisResultText('');
    setCaseData((prev) => ({
      ...prev,
      details: prev.details ? ({
        ...prev.details,
        latest_deep_analysis: '',
        latest_comprehensive_analysis: '',
        analysis_dirty: true,
      } as any) : null,
    }));
  }, []);

  // 🧹 TOTAL WIPEOUT I AUDITIMIT TË DOKUMENTIT (FRONTEND STATE + MONGODB DATABASE)
  const handleDeleteDocAuditFromModal = useCallback(async () => {
    if (!currentAuditedDoc || !caseId) return;
    const targetId = String(currentAuditedDoc.id);

    // 1. Pastrim i menjëhershëm në frontend
    setDocAuditResultText('');
    setLiveDocuments((prev) => prev.map((d) => String(d.id) === targetId ? {
      ...d,
      latest_analysis: '',
      latest_forensic_audit: '',
      last_audited_at: null
    } as any : d));

    // 2. Fshirje e plotë nga MongoDB Atlas përmes Backend API
    try {
      await apiService.clearDocumentAudit(caseId, targetId);
    } catch (err) {
      console.error("Failed to clear document audit on MongoDB:", err);
      alert("Dështoi fshirja e auditimit nga baza e të dhënave.");
    }
  }, [caseId, currentAuditedDoc, setLiveDocuments]);

  const handleChatSubmit = useCallback(async (
    text: string, 
    mode: ChatMode, 
    reasoning: ReasoningMode, 
    domain: string, 
    documentIds?: string[], 
    jurisdiction?: Jurisdiction
  ) => {
    if (!caseId) return;
    const userMessage: ChatMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
    const assistantPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    
    setChatMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsSendingMessage(true);

    try {
      let acc = '';
      const stream = apiService.sendChatMessageStream(
        caseId, 
        text, 
        documentIds, 
        jurisdiction, 
        reasoning, 
        mode === 'document' ? domain : 'automatic'
      );

      for await (const chunk of stream) {
        acc += chunk;
        const currentAcc = acc;

        setChatMessages((prev) => {
          const updated = [...prev];
          if (updated.length > 0) {
            updated[updated.length - 1] = { ...updated[updated.length - 1], content: currentAcc };
          }
          return updated;
        });

        await new Promise((resolve) => setTimeout(resolve, 10));
      }

      setChatMessages((prev) => {
        const finalMessages = [...prev];
        persistChatHistory(finalMessages);
        return finalMessages;
      });
    } catch (err: any) {
      console.error("[Chat Stream Error]:", err);
      const errorDetail = err?.message || 'Nuk u arrit komunikimi me shërbimin AI.';
      setChatMessages((prev) => {
        const withError = [...prev];
        if (withError.length > 0) {
          withError[withError.length - 1] = { 
            ...withError[withError.length - 1], 
            content: `[Gabim Teknik] ${errorDetail}` 
          };
        }
        persistChatHistory(withError);
        return withError;
      });
    } finally {
      setIsSendingMessage(false);
    }
  }, [caseId, persistChatHistory]);

  // ⚡ BUTONI "ANALIZO RASTIN": HAPJE NË CaseAnalysisModal
  const handleStartBackgroundCaseAnalysis = useCallback(async () => {
    if (!caseId || isAnalyzingCase) return;

    const existing = 
      (analysisResultText && analysisResultText.trim().length > 100 ? analysisResultText : '') ||
      (typeof (caseData.details as any)?.latest_deep_analysis === 'string' && (caseData.details as any)?.latest_deep_analysis.trim().length > 100 ? (caseData.details as any)?.latest_deep_analysis : '') ||
      (typeof (caseData.details as any)?.latest_comprehensive_analysis === 'string' && (caseData.details as any)?.latest_comprehensive_analysis.trim().length > 100 ? (caseData.details as any)?.latest_comprehensive_analysis : '') ||
      '';

    if (existing && existing.trim().length > 100) {
      setAnalysisResultText(existing.trim());
      setIsAnalysisModalOpen(true);
      return;
    }

    setAnalysisResultText('');
    setIsAnalysisModalOpen(true);
    setIsAnalyzingCase(true);

    try {
      const prompt = "ANALIZO RASTIN — Gjenero Raportin Master të Plotë Doktrinar të Gjykatës Supreme për të gjithë fashikullin e lëndës, duke kryer autopsinë forenzike të të gjitha shkresave, procesverbaleve dhe provave materiale.";
      const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic');
      
      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setAnalysisResultText(accumulated);
      }

      if (accumulated.trim().length > 0) {
        setCaseData((prev) => ({
          ...prev,
          details: prev.details ? ({
            ...prev.details,
            latest_deep_analysis: accumulated,
            latest_comprehensive_analysis: accumulated,
            analysis_dirty: false,
          } as any) : null,
        }));
      }
    } catch (err) {
      console.error("Case Background Analysis Error:", err);
      alert("Ndodhi një gabim gjatë gjenerimit të raportit. Ju lutem provoni përsëri.");
    } finally {
      setIsAnalyzingCase(false);
    }
  }, [caseId, isAnalyzingCase, analysisResultText, caseData.details]);

  // ⚖️ BUTONI I PESHORES NË DOKUMENT: HAPJE NË DocumentAuditModal (ZERO CHAT POLLUTION)
  const handleVerifyDocumentLaws = useCallback(async (doc: Document) => {
    if (!caseId || isAuditingDoc) return;

    const docIdStr = String(doc.id);
    const docName = doc.file_name || 'Dokument';
    setCurrentAuditedDoc(doc);

    // 1. Hapje në 0ms nëse ky dokument tashmë e ka auditimin të kryer më parë
    const existingAudit = (doc as any).latest_analysis || (doc as any).latest_forensic_audit;
    if (typeof existingAudit === 'string' && existingAudit.trim().length > 100) {
      setDocAuditResultText(existingAudit.trim());
      setIsDocAuditModalOpen(true);
      return;
    }

    // 2. Nëse jo, hap menjëherë modalin e dedikuar dhe transmeto live stream brenda tij
    setDocAuditResultText('');
    setIsDocAuditModalOpen(true);
    setIsAuditingDoc(true);

    try {
      const supremeAuditPrompt = `[DIREKTIVË FORENZIKE E GJYKATËS SUPREME TË KOSOVËS]
Kryej auditimin e thellë forenzik të shkallës më të lartë të dokumentit "${docName}" sipas të 8 seksioneve të plota doktrinare, me nxjerrjen e çdo neni në Tabelën e Seksionit 4 me formatin Neni X i [Ligjit] për verifikim 1-klikim.`;

      const stream = apiService.sendChatMessageStream(caseId, supremeAuditPrompt, [docIdStr], 'ks', 'DEEP', 'document');

      let accumulated = '';
      for await (const chunk of stream) {
        accumulated += chunk;
        setDocAuditResultText(accumulated);
      }

      if (accumulated.trim().length > 0) {
        setLiveDocuments((prev) => prev.map((d) => String(d.id) === docIdStr ? {
          ...d,
          latest_analysis: accumulated,
          latest_forensic_audit: accumulated
        } as any : d));
      }
    } catch (err) {
      console.error("Single Document Audit Error:", err);
      alert("Ndodhi një gabim gjatë auditimit të dokumentit.");
    } finally {
      setIsAuditingDoc(false);
    }
  }, [caseId, isAuditingDoc, setLiveDocuments]);

  const handleRenameAction = async (newName: string) => {
    if (!caseId || !documentToRename) return;
    try {
      await apiService.renameDocument(caseId, documentToRename.id, newName);
      setLiveDocuments((p) => p.map((d) => (d.id === documentToRename.id ? { ...d, file_name: newName } : d)));
    } catch {
      alert(t('error.generic', 'Ndodhi një gabim.'));
    }
  };

  if (isAuthLoading || isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-canvas">
        <div className="w-14 h-14 border-4 border-primary-start border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !caseData.details) {
    return (
      <div className="p-8 text-center text-danger border border-danger/30 rounded-2xl bg-danger/5 mt-20 max-w-lg mx-auto animate-pulse">
        <AlertCircle className="mx-auto h-12 w-12 mb-4" />
        <p className="font-bold uppercase tracking-wide">{error}</p>
      </div>
    );
  }

  return (
    <motion.div className="w-full min-h-screen pb-8 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 pt-16 sm:pt-20 pb-4">
        
        <CaseHeaderBar
          caseDetails={caseData.details}
          documents={liveDocuments}
        />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 z-0 items-stretch">
          <EvidenceVaultPanel
            caseId={caseData.details.id}
            documents={liveDocuments}
            connectionStatus={connectionStatus}
            reconnect={reconnect}
            onDocumentUploaded={handleDocumentUploaded}
            onDocumentDeleted={handleDocumentDeleted}
            onViewOriginal={handleViewOriginal}
            onRenameDocument={setDocumentToRename}
            onVerifyDocumentLaws={handleVerifyDocumentLaws}
            t={t}
          />

          <div className="lg:col-span-7 flex flex-col h-[580px] sm:h-[720px] lg:h-[calc(100vh-200px)] min-h-[650px] bg-surface border border-main rounded-2xl overflow-hidden shadow-sm relative">
            <ChatPanel
              messages={chatMessages}
              connectionStatus={connectionStatus}
              reconnect={reconnect}
              onSendMessage={handleChatSubmit}
              isSendingMessage={isSendingMessage}
              onClearChat={handleClearChat}
              t={t}
              className="h-full w-full bg-transparent border-0 rounded-none"
              activeContextId={currentCaseId}
              isPro={isPro}
              documents={liveDocuments}
              selectedDocumentIds={selectedDocumentIds}
              onDocumentSelectionChange={setSelectedDocumentIds}
              userSalutation={userSalutation}
              clientPosition={clientPosition}
              onOpenCaseAnalysis={handleStartBackgroundCaseAnalysis}
              isAnalyzingCase={isAnalyzingCase}
            />
          </div>
        </div>
      </div>

      {viewingDocument && (
        <PDFViewerModal
          documentData={viewingDocument}
          caseId={caseData.details.id}
          onClose={() => { setViewingDocument(null); setViewingUrl(null); }}
          onMinimize={() => { if (viewingDocument) { setMinimizedDocument(viewingDocument); setViewingDocument(null); } }}
          t={t}
          directUrl={viewingUrl}
          isAuth={true}
          initialPage={viewingInitialPage}
        />
      )}
      {minimizedDocument && <DockedPDFViewer document={minimizedDocument} onExpand={() => handleViewOriginal(minimizedDocument)} onClose={() => setMinimizedDocument(null)} />}

      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRenameAction} currentName={documentToRename?.file_name || ''} t={t} />

      {/* MODAL 1: ANALIZA E PLOTË E LËNDËS (TË GJITHA SHKRESAT) */}
      <CaseAnalysisModal
        isOpen={isAnalysisModalOpen}
        onClose={() => setIsAnalysisModalOpen(false)}
        analysisText={analysisResultText}
        caseId={currentCaseId}
        caseTitle={caseTitle}
        clientName={clientName}
        onDeleteAnalysis={handleDeleteAnalysisFromModal}
      />

      {/* MODAL 2: AUDITIMI I DEDIKUAR PËR 1 DOKUMENT TË VETËM (PESHORJA ⚖️) */}
      <DocumentAuditModal
        isOpen={isDocAuditModalOpen}
        onClose={() => setIsDocAuditModalOpen(false)}
        auditText={docAuditResultText}
        caseId={currentCaseId}
        documentId={String(currentAuditedDoc?.id || '')}
        documentName={currentAuditedDoc?.file_name || 'Dokument'}
        clientName={clientName}
        onDeleteAudit={handleDeleteDocAuditFromModal}
      />
    </motion.div>
  );
};

export default CaseViewPage;