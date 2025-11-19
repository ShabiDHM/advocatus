// FILE: src/pages/CaseViewPage.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Case, Document, Finding, ChatMessage, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { apiService } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel from '../components/ChatPanel';
import PDFViewerModal from '../components/PDFViewerModal';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import useAuth from '../context/AuthContext';
import { motion } from 'framer-motion';
import { ArrowLeft, AlertCircle, User, Briefcase, Info } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';

type CaseData = {
    details: Case | null;
    documents: Document[];
    findings: Finding[];
};

// --- SUB-COMPONENTS ---
const CaseHeader: React.FC<{ caseDetails: Case; t: TFunction; }> = ({ caseDetails, t }) => (
    <motion.div
      className="mb-6 p-6 rounded-2xl shadow-lg bg-background-light/50 backdrop-blur-sm border border-glass-edge"
      initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
    >
      <h1 className="text-2xl font-bold text-text-primary mb-2">{caseDetails.case_name}</h1>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-text-secondary">
        <div className="flex items-center" title={t('caseCard.client')}><User className="h-4 w-4 mr-2 text-primary-start" /><span>{caseDetails.client?.name || t('general.notAvailable')}</span></div>
        <div className="flex items-center" title={t('caseView.statusLabel')}><Briefcase className="h-4 w-4 mr-2 text-primary-start" /><span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`, { fallback: caseDetails.status })}</span></div>
        <div className="flex items-center" title={t('caseCard.createdOn')}><Info className="h-4 w-4 mr-2 text-primary-start" /><span>{new Date(caseDetails.created_at).toLocaleDateString()}</span></div>
      </div>
    </motion.div>
);
const FindingsPanel: React.FC<{ findings: Finding[]; t: TFunction; }> = ({ findings, t }) => {
    if (findings.length === 0) return null;
    return (
        <motion.div className="mt-6 p-6 rounded-2xl shadow-lg bg-background-light/50 backdrop-blur-sm border border-glass-edge"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.2 }} >
            <h3 className="text-xl font-bold text-text-primary mb-4">{t('caseView.findingsTitle')}</h3>
            <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                {findings.map((finding) => (
                    <div key={finding.id} className="p-3 bg-background-dark/30 rounded-lg border border-glass-edge/50">
                        <p className="text-sm text-text-secondary">{finding.finding_text}</p>
                        <span className="text-xs text-text-secondary/60 mt-2 block">{t('caseView.findingSource')}: {finding.document_name || finding.document_id}</span>
                    </div>
                ))}
            </div>
        </motion.div>
    );
};
// --- END SUB-COMPONENTS ---


const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();
  
  const [caseData, setCaseData] = useState<CaseData>({ details: null, documents: [], findings: [] });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;
  const isReadyForSocket = isReadyForData && !isLoading;

  const fetchCaseData = useCallback(async (isInitialLoad = false) => {
    if (!caseId) return;
    if(isInitialLoad) setIsLoading(true);
    setError(null);
    try {
      const [details, initialDocs, findingsResponse] = await Promise.all([
        apiService.getCaseDetails(caseId),
        apiService.getDocuments(caseId),
        apiService.getFindings(caseId)
      ]);
      setCaseData({
          details,
          documents: (initialDocs || []).map(sanitizeDocument),
          findings: findingsResponse || []
      });
    } catch (err) {
      setError(t('error.failedToLoadCase'));
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t]);

  useEffect(() => {
    if (isReadyForData) {
      fetchCaseData(true);
    }
  }, [isReadyForData, fetchCaseData]);

  const pollDocumentStatus = useCallback((docId: string) => {
    const intervalId = setInterval(async () => {
        if (!caseId) { clearInterval(intervalId); return; }
        try {
            const updatedDoc = await apiService.getDocument(caseId, docId);
            const isFinished = updatedDoc.status.toUpperCase() === 'READY' || updatedDoc.status.toUpperCase() === 'FAILED';
            setCaseData(prev => ({ ...prev, documents: prev.documents.map(d => d.id === updatedDoc.id ? sanitizeDocument(updatedDoc) : d) }));
            if (isFinished) {
                clearInterval(intervalId);
                if (updatedDoc.status.toUpperCase() === 'READY') {
                    const findingsResponse = await apiService.getFindings(caseId);
                    setCaseData(prev => ({ ...prev, findings: findingsResponse || [] }));
                }
            }
        } catch { clearInterval(intervalId); }
    }, 3000);
    return () => clearInterval(intervalId);
  }, [caseId]);
  
  const handleDocumentUploaded = (newDoc: Document) => {
    setCaseData(prev => ({ ...prev, documents: [sanitizeDocument(newDoc), ...prev.documents] }));
    pollDocumentStatus(newDoc.id);
  };
  
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => {
    const { documentId, deletedFindingIds } = response;
    const deletedIdsSet = new Set(deletedFindingIds);
    setCaseData(prev => ({
        ...prev,
        documents: prev.documents.filter(d => d.id !== documentId),
        findings: prev.findings.filter(f => !deletedIdsSet.has(f.id))
    }));
  };
  
  const handleChatMessage = useCallback((message: ChatMessage) => {
    // FIXED: Added strict undefined checks for message text concatenation (TS18048)
    setMessages(prev => {
      if (prev.length > 0 && prev[prev.length - 1].sender === 'AI' && message.isPartial) {
        return prev.map((m, i) => i === prev.length - 1 
          ? { ...m, text: (m.text || '') + (message.text || '') } 
          : m
        );
      }
      return [...prev, message];
    });
  }, []);

  const { reconnect, sendChatMessage } = useDocumentSocket(currentCaseId, isReadyForSocket, {
    onConnectionStatusChange: setConnectionStatus,
    onChatMessage: handleChatMessage,
    // FIXED: Added explicit type annotation for 'doc' (TS7006)
    onDocumentUpdate: (doc: Document) => setCaseData(prev => ({ ...prev, documents: prev.documents.map(d => d.id === doc.id ? sanitizeDocument(doc) : d) })),
    onFindingsUpdate: () => fetchCaseData(),
    onIsSendingChange: setIsSendingMessage,
  });
  
  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error || !caseData.details) return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-900/50 border border-red-600 rounded-md p-6 text-center">
            <AlertCircle className="mx-auto h-12 w-12 text-red-400 mb-4" />
            <h2 className="text-xl font-semibold text-red-300 mb-2">{t('caseView.errorLoadingTitle')}</h2>
            <p className="text-red-300 mb-4">{error || t('caseView.genericError')}</p>
        </div>
    </div>
  );

  return (
    <motion.div className="w-full min-h-[90vh]" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:py-8">
        <div className="mb-8">
          <Link to="/dashboard" className="inline-flex items-center text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('caseView.backToDashboard')}
          </Link>
        </div>
        <div className="flex flex-col space-y-6">
            <CaseHeader caseDetails={caseData.details} t={t} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                <DocumentsPanel
                  caseId={caseData.details.id}
                  documents={caseData.documents}
                  findings={caseData.findings} 
                  t={t}
                  connectionStatus={connectionStatus}
                  reconnect={reconnect}
                  onDocumentUploaded={handleDocumentUploaded}
                  onDocumentDeleted={handleDocumentDeleted}
                  onViewOriginal={setViewingDocument}
                />
                <ChatPanel
                  messages={messages}
                  connectionStatus={connectionStatus}
                  reconnect={reconnect}
                  onSendMessage={sendChatMessage}
                  isSendingMessage={isSendingMessage}
                  caseId={caseData.details.id}
                  t={t}
                />
            </div>
            <FindingsPanel findings={caseData.findings} t={t} />
        </div>
      </div>
      {viewingDocument && (
        <PDFViewerModal 
          documentData={viewingDocument}
          caseId={caseData.details.id}
          onClose={() => setViewingDocument(null)}
          t={t}
        />
      )}
    </motion.div>
  );
};

export default CaseViewPage;