// FILE: src/pages/CaseViewPage.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Case, Document, DeletedDocumentResponse, CaseAnalysisResult, ChatMessage } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import ChatPanel, { ChatMode, Jurisdiction, ReasoningMode } from '../components/ChatPanel';
import PDFViewerModal from '../components/FileViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import OntologyModal from '../components/OntologyModal';
import FinancialAnalystModal from '../components/FinancialAnalystModal';
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
import { RoleSelectionModal } from '../components/case/RoleSelectionModal';
import { GatekeeperNoticeModal } from '../components/case/GatekeeperNoticeModal';

type CaseData = { details: Case | null };
type ActiveModal = 'none' | 'analysis' | 'ontology' | 'analyst';

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
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CaseAnalysisResult | null>(null);
  const [activeModal, setActiveModal] = useState<ActiveModal>('none');
  const [documentToRename, setDocumentToRename] = useState<Document | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [gatekeeperNotice, setGatekeeperNotice] = useState<string | null>(null);

  const isPro = true;

  const isAdmin = useMemo(() => {
    if (!user) return false;
    const emailStr = (user.email || '').toString().toLowerCase().trim();
    const roleStr = (user.role || (user as any).user_type || '').toString().toUpperCase().trim();
    return emailStr === 'shabanbala@gmail.com' || roleStr === 'SUPER_ADMIN';
  }, [user]);

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

      if (details && (details as any).latest_analysis) {
        setAnalysisResult((details as any).latest_analysis);
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
      setError(t('error.failedToLoadCase'));
    } finally {
      if (isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments, loadFromLocalStorage, saveToLocalStorage, persistChatHistory]);

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);

  const handleDocumentUploaded = (newDoc: Document) => setLiveDocuments((p) => [sanitizeDocument(newDoc), ...p]);
  const handleDocumentDeleted = (res: DeletedDocumentResponse) => setLiveDocuments((p) => p.filter((d) => String(d.id) !== String(res.documentId)));

  const handleClearChat = async () => {
    if (!caseId) return;
    try {
      await apiService.clearChatHistory(caseId);
      setChatMessages([]);
      await persistChatHistory([]);
      localStorage.removeItem(`chat_${caseId}`);
    } catch {
      alert(t('error.generic'));
    }
  };

  const handleClearAnalysis = async () => {
    if (!caseId) return;
    try {
      await apiService.clearCaseAnalysis(caseId);
      setAnalysisResult(null);
      setCaseData((prev) => (prev.details ? { details: { ...prev.details, latest_analysis: null } } : prev));
    } catch {
      alert(t('error.generic'));
    }
  };

  const handleRunAnalysis = async (force = false) => {
    if (!caseId) return;
    const existingAnalysis = caseData.details && (caseData.details as any).latest_analysis ? (caseData.details as any).latest_analysis : analysisResult;

    if (force && existingAnalysis) {
      const lastDocIds: string[] = (existingAnalysis as any).analyzed_doc_ids || [];
      const currentDocIds: string[] = liveDocuments.map((d) => String(d.id)).sort();
      const isIdentical = lastDocIds.length > 0 && lastDocIds.length === currentDocIds.length && lastDocIds.slice().sort().every((id, idx) => id === currentDocIds[idx]);

      if (isIdentical) {
        setGatekeeperNotice('Nuk ka ndryshime në dokumentet e rastit. Për të ekzekutuar një ri-analizë të re, kërkohet të shtohet një dokument i ri ose të fshihet një dokument ekzistues.');
        return;
      }
    }

    setIsAnalyzing(true);
    setActiveModal('none');

    try {
      const activeRole = clientPosition || 'DEFENDANT';
      const result = selectedDocumentIds.length === 0
        ? await apiService.analyzeCase(caseId, activeRole)
        : await apiService.crossExamineDocument(caseId, selectedDocumentIds[0]);

      if (result.error) {
        alert(result.error);
      } else {
        const resultWithMeta = { ...result, analyzed_doc_ids: liveDocuments.map((d) => String(d.id)).sort(), client_position: activeRole };
        setAnalysisResult(resultWithMeta);
        setActiveModal('analysis');
        setCaseData((prev) => prev.details ? { details: { ...prev.details, client_position: activeRole, latest_analysis: resultWithMeta } } : prev);
      }
    } catch {
      alert(t('error.generic'));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleRoleChosen = async (selectedRole: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL') => {
    if (!caseId) return;
    setShowRoleModal(false);
    setCaseData((prev) => (prev.details ? { details: { ...prev.details, client_position: selectedRole } } : prev));
    try {
      await apiService.updateCasePosition(caseId, selectedRole);
    } catch (e) {
      console.warn('Failed to persist position update:', e);
    }
  };

  const handleChatSubmit = async (text: string, mode: ChatMode, reasoning: ReasoningMode, domain: string, documentIds?: string[], jurisdiction?: Jurisdiction) => {
    if (!caseId) return;
    const userMessage: ChatMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
    const assistantPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    setChatMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsSendingMessage(true);

    try {
      let acc = '';
      const enrichedText = `${text}\n\n(Ju lutem, në fund të përgjigjes suaj, shtoni një seksion të titulluar 'Sugjerime:' dhe rreshtoni saktësisht 3 pyetje të shkurtra vijuese që unë mund t'i bëj më pas in lidhje me këtë përgjigje. Formatizo si: \nSugjerime:\n1. Pyetja e parë?\n2. Pyetja e dytë?\n3. Pyetja e tretë?)`;
      const stream = apiService.sendChatMessageStream(caseId, enrichedText, documentIds, jurisdiction, reasoning, mode === 'document' ? domain : undefined);

      for await (const chunk of stream) {
        acc += chunk;
        setChatMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { ...updated[updated.length - 1], content: acc };
          return updated;
        });
      }
      setChatMessages((prev) => {
        const finalMessages = [...prev];
        persistChatHistory(finalMessages);
        return finalMessages;
      });
    } catch {
      setChatMessages((prev) => {
        const withError = [...prev];
        withError[withError.length - 1] = { ...withError[withError.length - 1], content: '[Gabim Teknik]' };
        persistChatHistory(withError);
        return withError;
      });
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleViewOriginal = (doc: Document) => {
    setViewingUrl(`${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`);
    setViewingDocument(doc);
    setMinimizedDocument(null);
  };

  const handleRenameAction = async (newName: string) => {
    if (!caseId || !documentToRename) return;
    try {
      await apiService.renameDocument(caseId, documentToRename.id, newName);
      setLiveDocuments((p) => p.map((d) => (d.id === documentToRename.id ? { ...d, file_name: newName } : d)));
    } catch {
      alert(t('error.generic'));
    }
  };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-screen bg-canvas"><div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-danger border border-danger/30 rounded-2xl bg-danger/5 mt-20 max-w-lg mx-auto animate-pulse"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p className="font-bold uppercase tracking-wide">{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen pb-12 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-3 sm:px-6 lg:px-8 pt-16 sm:pt-24 pb-8">
        <CaseHeaderBar
          caseDetails={caseData.details}
          documents={liveDocuments}
          onOpenRoleModal={() => setShowRoleModal(true)}
          onRunAnalysis={handleRunAnalysis}
          onViewExistingAnalysis={() => (analysisResult || (caseData.details && (caseData.details as any).latest_analysis)) && setActiveModal('analysis')}
          onOpenOntologyModal={() => setActiveModal('ontology')}
          onOpenAnalystModal={() => setActiveModal('analyst')}
          onClearAnalysis={handleClearAnalysis}
          isAnalyzing={isAnalyzing}
          isPro={isPro}
          isAdmin={isAdmin}
          selectedDocumentIds={selectedDocumentIds}
          onDocumentSelectionChange={setSelectedDocumentIds}
        />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 sm:gap-6 z-0">
          <EvidenceVaultPanel
            caseId={caseData.details.id}
            documents={liveDocuments}
            connectionStatus={connectionStatus}
            reconnect={reconnect}
            onDocumentUploaded={handleDocumentUploaded}
            onDocumentDeleted={handleDocumentDeleted}
            onViewOriginal={handleViewOriginal}
            onRenameDocument={setDocumentToRename}
            t={t}
          />

          <div className="lg:col-span-7 flex flex-col h-[540px] sm:h-[700px] bg-surface border border-main rounded-2xl overflow-hidden shadow-sm relative">
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
              selectedDocumentCount={selectedDocumentIds.length}
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

      {isAdmin && analysisResult && <AnalysisModal isOpen={activeModal === 'analysis'} onClose={() => setActiveModal('none')} result={analysisResult} caseId={currentCaseId} isLoading={isAnalyzing} />}
      {isAdmin && <OntologyModal isOpen={activeModal === 'ontology'} onClose={() => setActiveModal('none')} caseId={currentCaseId} caseTitle={caseData.details?.title || (caseData.details as any)?.name} clientPosition={clientPosition} />}
      {isAdmin && <FinancialAnalystModal isOpen={activeModal === 'analyst'} onClose={() => setActiveModal('none')} caseId={currentCaseId} caseTitle={caseData.details?.title || (caseData.details as any)?.name} />}

      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRenameAction} currentName={documentToRename?.file_name || ''} t={t} />
      <RoleSelectionModal isOpen={showRoleModal} onClose={() => setShowRoleModal(false)} onSelectRole={handleRoleChosen} />
      <GatekeeperNoticeModal notice={gatekeeperNotice} documentCount={liveDocuments.length} onClose={() => setGatekeeperNotice(null)} />
    </motion.div>
  );
};

export default CaseViewPage;