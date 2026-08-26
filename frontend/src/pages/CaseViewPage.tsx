// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW PAGE V56.0 (SUPREME COURT JURISPRUDENCE & FORENSIC AUDIT DISPATCHER)

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
  const [documentToRename, setDocumentToRename] = useState<Document | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  const isPro = true;
  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, connectionStatus, reconnect } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  const userSalutation = useMemo(() => getUserSalutation(user), [user]);
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

  const handleDocumentUploaded = (newDoc: Document) => setLiveDocuments((p) => [sanitizeDocument(newDoc), ...p]);
  const handleDocumentDeleted = (res: DeletedDocumentResponse) => setLiveDocuments((p) => p.filter((d) => String(d.id) !== String(res.documentId)));

  const handleViewOriginal = useCallback((doc: Document) => {
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
      setChatMessages([]);
      await persistChatHistory([]);
      localStorage.removeItem(`chat_${caseId}`);
    } catch {
      alert(t('error.generic', 'Ndodhi një gabim.'));
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

  // 1-CLICK SUPREME COURT FORENSIC AUDITOR (700+ PAGE JURISPRUDENCE GROUNDING)
  const handleVerifyDocumentLaws = useCallback((doc: Document) => {
    const docIdStr = String(doc.id);
    setSelectedDocumentIds([docIdStr]);

    const docName = doc.file_name || 'këtë dokument';
    const supremeAuditPrompt = `[DIREKTIVË FORENZIKE E GJYKATËS SUPREME TË KOSOVËS]
Duke u bazuar në dokumentin e zgjedhur "${docName}" dhe në bazën e jurisprudencës të Gjykatës Supreme të Kosovës (700+ faqe), kryej auditimin e plotë forenzik ligjor sipas 5 seksioneve të detyrueshme:

1. PIKAT KRYESORE DHE PROVAT E ADMINISTRUARA
   - Përmblidh saktësisht faktet e verifikuara dhe provat e këtij akti pa asnjë ndryshim.

2. BAZA LIGJORE DHE KORNIZA STATUTARE
   - Lidh çdo nen, paragraf dhe ligj pozitiv të aplikueshëm (KPRK, KPPRK, LPK, LMD, Kushtetutë, Konventa).

3. ⚠️ PARALAJMËRIME & SUGJERIME STATUTARE (AUDITIMI I LAPSUSEVE)
   - Audito me saktësi nëse shkresa ka lapsuse numerike të neneve apo referenca të papërshtatshme me ligjin pozitiv dhe sugjero dispozitën e saktë për avokatin.

4. 🏛️ OPINIONI DHE PRAKTIKA E GJYKATËS SUPREME TË KOSOVËS (700+ FAQE JURISPRUDENCË)
   - Cito qëndrimet doktrinare dhe precedentët e Kolegjit Penal/Civil të Gjykatës Supreme të Kosovës (Aktgjykimet PML, komentarin e Prof. Dr. Fejzullah Hasanit mbi figurat e veprave, rehabilitimin ligjor Neni 93, bashkëkryerjen, dhe ligjshmërinë e provave).
   - Jep vlerësimin doktrinar të Gjyqtarit Suprem mbi qëndrueshmërinë ligjore të kësaj shkrese.

5. REKOMANDIMI STRATEGJIK DHE HAPAT E ARDHSHËM PROCEDURALË
   - Hapat e menjëhershëm proceduralë dhe veprimet me organet kompetente.`;

    handleChatSubmit(supremeAuditPrompt, 'document', 'DEEP', 'automatic', [docIdStr], 'ks');
  }, [handleChatSubmit]);

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
        
        {/* SHIRITI I IDENTITETIT */}
        <CaseHeaderBar
          caseDetails={caseData.details}
          documents={liveDocuments}
        />

        {/* DY SHTYLLAT KRYESORE */}
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
        />
      )}
      {minimizedDocument && <DockedPDFViewer document={minimizedDocument} onExpand={() => handleViewOriginal(minimizedDocument)} onClose={() => setMinimizedDocument(null)} />}

      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRenameAction} currentName={documentToRename?.file_name || ''} t={t} />
    </motion.div>
  );
};

export default CaseViewPage;