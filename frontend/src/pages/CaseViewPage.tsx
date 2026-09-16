// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW PAGE V104.0 (DYNAMIC DOSSIER/DOCUMENT AUDIT)
// ZERO TS WARNINGS • 100% COMPLETE CODE • SYMMETRIC SPLIT DESKTOP • NATIVE 3-TAB MOBILE

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
import { AlertCircle, FileText, Film, BrainCircuit } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { extractAndNormalizeHistory, getUserSalutation } from '../utils/caseHelpers';
import { CaseHeaderBar } from '../components/case/CaseHeaderBar';
import { EvidenceVaultPanel, EvidenceSubTab } from '../components/case/EvidenceVaultPanel';
import { RenameDocumentModal } from '../components/case/RenameDocumentModal';
import { StandardDocumentAuditModal } from '../components/case/StandardDocumentAuditModal';

type CaseData = { details: Case | null };

type MobileMainTab = 'DOCS' | 'MEDIA' | 'CHAT';

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

  // Tab-i i vetëm dhe i unifikuar në celular (3 Zgjedhje të pastra)
  const [mobileTab, setMobileTab] = useState<MobileMainTab>('DOCS');
  const [vaultSubTab, setVaultSubTab] = useState<EvidenceSubTab>('documents');

  // Dritarja Modale e Auditimit
  const [isDocAuditModalOpen, setIsDocAuditModalOpen] = useState<boolean>(false);
  const [currentAuditedDoc, setCurrentAuditedDoc] = useState<Document | null>(null);

  const isPro = true;
  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, connectionStatus, reconnect } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  const userSalutation = useMemo(() => getUserSalutation(user), [user]);
  const clientName = useMemo(() => (caseData.details as any)?.client_name || (caseData.details as any)?.client?.name || 'Klienti', [caseData.details]);
  const clientPosition = useMemo(() => (caseData.details as any)?.client_position || 'DEFENDANT', [caseData.details]);

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
    // Në telefon, kalo menjëherë te biseda për ta pyetur AI-n mbi atë shkresë
    setMobileTab('CHAT');
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

  const handleVerifyDocumentLaws = useCallback((doc: Document) => {
    if (!caseId) return;
    setCurrentAuditedDoc(doc);
    setIsDocAuditModalOpen(true);
  }, [caseId]);

  // DEGËZIMI DINAMIK: DOKUMENT i selektuar → Modal | FASHIKULL → Stream i analizës
  const handleTriggerSelectedDocAudit = useCallback(() => {
    // KASO 1: Nuk ka dokument të selektuar → Analizë e fashikullit të plotë
    if (!selectedDocObj) {
      if (!caseId) return;

      const docCount = liveDocuments.length;
      const dossierPrompt = `[DIREKTIVË PËR ANALIZËN E FASHIKULLIT TË PLOTË]
Analizoni të gjitha ${docCount} shkresat e kësaj lënde si një fashikull i vetëm dhe koherent:

1. Rindërtimi kronologjik i ngjarjeve kryesore nga të gjitha shkresat (data, akte, palë).
2. Struktura e plotë e aktorëve, palëve, dëshmitarëve dhe deklarimeve të tyre verbatim.
3. Kontradiktat thelbësore mes provave dhe deklaratave të ndryshme.
4. Baza ligjore e zbatueshme me nene të sakta të legjislacionit pozitiv të Kosovës dhe shkeljet procedurale thelbësore.
5. Rekomandimi taktik përfundimtar dhe hapat e ardhshëm proceduralë me afate ligjore.

Rregull i hekurt: NUK lejohet rishkrimi, zëvendësimi apo korrigjimi automatik i neneve dhe precedenteve. Për çdo gabim, paraqit: (a) siç është cituar në shkresë, (b) neni/precedenti i saktë si REKOMANDIM i veçantë, (c) arsyeja e saktë e problemit.`;

      handleChatSubmit(dossierPrompt, 'document', 'DEEP', 'automatic', undefined, 'ks');
      return;
    }

    // KASO 2: Dokument i selektuar → Hap modalin e auditimit (i njëjti si më parë)
    handleVerifyDocumentLaws(selectedDocObj);
  }, [selectedDocObj, liveDocuments.length, caseId, handleChatSubmit, handleVerifyDocumentLaws]);

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
      <div className="max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 pt-16 sm:pt-20 pb-2 space-y-2.5 sm:space-y-3.5 flex-1 flex flex-col">
        
        <CaseHeaderBar
          caseDetails={caseData.details}
          documents={liveDocuments}
        />

        {/* SHIRITI I VETËM UNIFIKUAR NË CELULAR - 3 ZGJEDHJE TË PASTRA (ZERO DYFISHIM) */}
        <div className="flex lg:hidden items-center bg-surface border border-main rounded-xl p-1 shadow-xs shrink-0">
          <button
            type="button"
            onClick={() => {
              setMobileTab('DOCS');
              setVaultSubTab('documents');
            }}
            className={`flex-1 py-2 px-1.5 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1 transition-all cursor-pointer min-h-[38px] ${
              mobileTab === 'DOCS' 
                ? 'bg-primary-start text-white shadow-sm' 
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <FileText size={13} className="shrink-0" />
            <span className="truncate">Dokumentet ({liveDocuments.length})</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setMobileTab('MEDIA');
              setVaultSubTab('audio');
            }}
            className={`flex-1 py-2 px-1.5 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1 transition-all cursor-pointer min-h-[38px] ${
              mobileTab === 'MEDIA' 
                ? 'bg-primary-start text-white shadow-sm' 
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Film size={13} className="shrink-0" />
            <span className="truncate">Audio & Video</span>
          </button>

          <button
            type="button"
            onClick={() => setMobileTab('CHAT')}
            className={`flex-1 py-2 px-1.5 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1 transition-all cursor-pointer min-h-[38px] ${
              mobileTab === 'CHAT' 
                ? 'bg-primary-start text-white shadow-sm' 
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <BrainCircuit size={13} className="shrink-0" />
            <span className="truncate">Biseda</span>
          </button>
        </div>

        {/* PANELET E PUNËS (100% PA DYFISHIM NË CELULAR) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 sm:gap-4 lg:gap-6 z-0 h-[calc(100dvh-185px)] sm:h-[calc(100dvh-200px)] lg:h-[720px] max-h-[850px] items-stretch flex-1 min-h-[480px]">
          
          {/* PANELI I PROVAVE: SHFAQET KUR ZGJIDHET 'DOCS' OSE 'MEDIA' */}
          <div className={`lg:col-span-5 h-full overflow-y-auto flex-col ${
            mobileTab === 'DOCS' || mobileTab === 'MEDIA' ? 'flex' : 'hidden lg:flex'
          }`}>
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
              activeSubTab={vaultSubTab}
              onSubTabChange={setVaultSubTab}
              t={t}
            />
          </div>

          {/* PANELI I BISEDËS: SHFAQET KUR ZGJIDHET 'CHAT' */}
          <div className={`lg:col-span-7 flex-col bg-surface border border-main rounded-2xl overflow-hidden shadow-sm relative h-full ${
            mobileTab === 'CHAT' ? 'flex' : 'hidden lg:flex'
          }`}>
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
              onAnalyzeDocument={handleTriggerSelectedDocAudit}
              selectedDocName={selectedDocObj?.file_name}
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