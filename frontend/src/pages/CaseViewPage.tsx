// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW PAGE V100.1 (PANEL MAX-HEIGHT + SCROLL FIX)
// ZERO TS WARNINGS • 100% COMPLETE CODE

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
import { StandardCaseAnalysisModal } from '../components/case/StandardCaseAnalysisModal';
import { StandardDocumentAuditModal } from '../components/case/StandardDocumentAuditModal';

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

  // 1. Dritarja Modale: Analizo Rastin
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState<boolean>(false);

  // 2. Dritarja Modale: Analizo Dokumentin
  const [isDocAuditModalOpen, setIsDocAuditModalOpen] = useState<boolean>(false);
  const [currentAuditedDoc, setCurrentAuditedDoc] = useState<Document | null>(null);

  const isPro = true;
  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, connectionStatus, reconnect } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  const userSalutation = useMemo(() => getUserSalutation(user), [user]);
  const caseTitle = useMemo(() => (caseData.details as any)?.title || (caseData.details as any)?.case_name || 'Lënda Ligjore', [caseData.details]);
  const clientName = useMemo(() => (caseData.details as any)?.client_name || (caseData.details as any)?.client?.name || 'Klienti', [caseData.details]);
  const clientPosition = useMemo(() => (caseData.details as any)?.client_position || 'DEFENDANT', [caseData.details]);

  const isAnalysisDirty = useMemo(() => {
    return Boolean((caseData.details as any)?.analysis_dirty);
  }, [caseData.details]);

  const selectedDocObj = useMemo(() => {
    if (selectedDocumentIds.length > 0) {
      return liveDocuments.find(d => selectedDocumentIds.includes(String(d.id))) || null;
    }
    return null;
  }, [selectedDocumentIds, liveDocuments]);

  const handleSelectDocument = useCallback((doc: Document) => {
    const docIdStr = String(doc.id);
    setSelectedDocumentIds((prev) => {
      if (prev.includes(docIdStr)) {
        return [];
      } else {
        return [docIdStr];
      }
    });
  }, []);

  const saveToLocalStorage = useCallback((messages: ChatMessage[]) => {
    if (!caseId) return;
    localStorage.setItem(`chat_${caseId}`, JSON.stringify(messages));
  }, [caseId]);

  const persistChatHistory = useCallback(async (messages: ChatMessage[]) => {
    if (!caseId) return;
    saveToLocalStorage(messages);
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

      const backendMessages = extractAndNormalizeHistory(details);
      if (backendMessages.length > 0) {
        setChatMessages(backendMessages);
        saveToLocalStorage(backendMessages);
      } else {
        setChatMessages([]);
        localStorage.removeItem(`chat_${caseId}`);
      }
    } catch {
      setError(t('error.failedToLoadCase', 'Dështoi ngarkimi i lëndës.'));
    } finally {
      if (isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments, saveToLocalStorage]);

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);

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

  const handleClearChat = async () => {
    if (!caseId) return;
    try {
      await apiService.clearChatHistory(caseId);
      try {
        await apiService.updateChatHistory(caseId, []);
      } catch {}

      localStorage.removeItem(`chat_${caseId}`);
      setChatMessages([]);
      
      setCaseData((prev) => ({
        ...prev,
        details: prev.details ? ({
          ...prev.details,
          chat_history: [],
        } as any) : null,
      }));
    } catch (err) {
      console.error("Dështoi pastrimi i bisedës në server:", err);
      alert(t('error.generic', 'Ndodhi një gabim gjatë pastrimit të bisedës.'));
    }
  };

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
        mode === 'document' ? domain : 'automatic',
        true
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

  const handleOpenCaseAnalysis = useCallback(() => {
    setIsAnalysisModalOpen(true);
  }, []);

  const handleVerifyDocumentLaws = useCallback((doc: Document) => {
    if (!caseId) return;
    setCurrentAuditedDoc(doc);
    setIsDocAuditModalOpen(true);
  }, [caseId]);

  const handleTriggerSelectedDocAudit = useCallback(() => {
    if (!selectedDocObj) {
      alert("Ju lutem klikoni mbi një shkresë në listën majtas për ta analizuar.");
      return;
    }
    handleVerifyDocumentLaws(selectedDocObj);
  }, [selectedDocObj, handleVerifyDocumentLaws]);

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
    <motion.div className="w-full min-h-screen pb-6 bg-canvas text-text-primary flex flex-col" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 pt-16 sm:pt-20 pb-2 space-y-3 sm:space-y-4 flex-1 flex flex-col">
        
        <CaseHeaderBar
          caseDetails={caseData.details}
          documents={liveDocuments}
        />

        {/* PHOENIX FIX: Barazimi i lartësisë së dy paneleve me Grid dhe Flex-1 */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5 lg:gap-6 z-0 flex-1 min-h-[520px]">
          {/* PANELI I MAJTË (DOKUMENTET) - MAX HEIGHT 600 + SCROLL */}
          <div className="lg:col-span-5 h-full max-h-[600px] overflow-y-auto flex flex-col">
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
              selectedDocumentId={selectedDocObj ? String(selectedDocObj.id) : ''}
              onSelectDocument={handleSelectDocument}
              t={t}
            />
          </div>

          {/* PANELI I DJATHTË (CHAT) */}
          <div className="lg:col-span-7 flex flex-col bg-surface border border-main rounded-2xl overflow-hidden shadow-sm relative h-full">
            <ChatPanel
              messages={chatMessages}
              connectionStatus={connectionStatus}
              reconnect={reconnect}
              onSendMessage={handleChatSubmit}
              isSendingMessage={isSendingMessage}
              onClearChat={handleClearChat}
              t={t}
              className="h-full w-full bg-transparent border-0 rounded-none flex-1"
              activeContextId={currentCaseId}
              isPro={isPro}
              documents={liveDocuments}
              selectedDocumentIds={selectedDocumentIds}
              onDocumentSelectionChange={setSelectedDocumentIds}
              userSalutation={userSalutation}
              clientPosition={clientPosition}
              onOpenCaseAnalysis={handleOpenCaseAnalysis}
              onAnalyzeDocument={handleTriggerSelectedDocAudit}
              selectedDocName={selectedDocObj?.file_name}
              isAnalysisDirty={isAnalysisDirty}
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

      <StandardCaseAnalysisModal
        isOpen={isAnalysisModalOpen}
        onClose={() => setIsAnalysisModalOpen(false)}
        caseId={currentCaseId}
        caseTitle={caseTitle}
        clientName={clientName}
        isAnalysisDirty={isAnalysisDirty}
      />

      <StandardDocumentAuditModal
        isOpen={isDocAuditModalOpen}
        onClose={() => setIsDocAuditModalOpen(false)}
        caseId={currentCaseId}
        documentId={String(selectedDocObj?.id || currentAuditedDoc?.id || '')}
        documentName={selectedDocObj?.file_name || currentAuditedDoc?.file_name || 'Dokument'}
        clientName={clientName}
      />
    </motion.div>
  );
};

export default CaseViewPage;