// FILE: /home/user/advocatus-frontend/src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL PHASE VIII - MODIFICATION 9.0 (Type Safety and Prop Drilling)
// CORRECTION 1: Corrected the Promise.all call for 'getFindings' to handle the
// API's direct return of a Finding[] array, resolving the TS2352 conversion error.
// CORRECTION 2: Restored the 'findings' prop on the <DocumentsPanel> component,
// ensuring the child component receives the data it needs and resolving the TS2741 error.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Case, Document, Finding, ChatMessage, ConnectionStatus } from '../data/types';
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

// --- SUB-COMPONENTS (No changes) ---
const CaseHeader: React.FC<{ caseDetails: Case; t: TFunction<"translation", undefined>; }> = ({ caseDetails, t }) => (
    <motion.div
      className="mb-6 p-6 rounded-2xl shadow-lg bg-background-light/50 backdrop-blur-sm border border-glass-edge"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <h1 className="text-2xl font-bold text-text-primary mb-2">{caseDetails.case_name}</h1>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-text-secondary">
        <div className="flex items-center" title={t('caseCard.client')}>
          <User className="h-4 w-4 mr-2 text-primary-start" />
          <span>{caseDetails.client?.name || t('general.notAvailable')}</span>
        </div>
        <div className="flex items-center" title={t('caseView.statusLabel')}>
          <Briefcase className="h-4 w-4 mr-2 text-primary-start" />
          <span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`, { fallback: caseDetails.status })}</span>
        </div>
        <div className="flex items-center" title={t('caseCard.createdOn')}>
          <Info className="h-4 w-4 mr-2 text-primary-start" />
          <span>{new Date(caseDetails.created_at).toLocaleDateString()}</span>
        </div>
      </div>
    </motion.div>
);

const FindingsPanel: React.FC<{ findings: Finding[]; t: TFunction<"translation", undefined>; }> = ({ findings, t }) => {
    if (findings.length === 0) {
        return null;
    }
    return (
        <motion.div
            className="mt-6 p-6 rounded-2xl shadow-lg bg-background-light/50 backdrop-blur-sm border border-glass-edge"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
        >
            <h3 className="text-xl font-bold text-text-primary mb-4">{t('caseView.findingsTitle')}</h3>
            <div className="space-y-4 max-h-96 overflow-y-auto pr-2">
                {findings.map((finding) => (
                    <div key={finding.id} className="p-3 bg-background-dark/30 rounded-lg border border-glass-edge/50">
                        <p className="text-sm text-text-secondary">{finding.finding_text}</p>
                        <span className="text-xs text-text-secondary/60 mt-2 block">
                            {t('caseView.findingSource')}: {finding.document_name || finding.document_id}
                        </span>
                    </div>
                ))}
            </div>
        </motion.div>
    );
};
// --- END SUB-COMPONENTS ---


const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();
  
  // --- STATE MANAGEMENT ---
  const [caseDetails, setCaseDetails] = useState<Case | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [caseFindings, setCaseFindings] = useState<Finding[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const currentCaseId = useMemo(() => caseId || '', [caseId]);

  // --- DATA FETCHING ---
  const fetchCaseData = useCallback(async () => {
    if (!caseId) {
        setError(t('error.noCaseId'));
        setIsLoading(false);
        return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const [details, initialDocs, findingsResponse] = await Promise.all([
        apiService.getCaseDetails(caseId),
        apiService.getDocuments(caseId),
        apiService.getFindings(caseId)
      ]);
      setCaseDetails(details);
      setDocuments((initialDocs || []).map(sanitizeDocument));
      // The API returns Finding[], not { findings: Finding[] }, this is the fix.
      setCaseFindings(findingsResponse || []);
    } catch (err) {
      setError(t('error.failedToLoadCase'));
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, t]);

  useEffect(() => {
    if (!isAuthLoading && caseId) {
      fetchCaseData();
    }
  }, [caseId, isAuthLoading, fetchCaseData]);


  // --- WEBSOCKET EVENT HANDLERS ---
  const handleConnectionStatusChange = useCallback((status: ConnectionStatus, errorMsg: string | null) => {
    setConnectionStatus(status);
    if (errorMsg) setError(prev => prev || errorMsg);
  }, []);

  const handleChatMessage = useCallback((message: ChatMessage) => {
    setMessages(prevMessages => {
        const newMessages = [...prevMessages];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage?.sender === 'AI' && message.isPartial) {
            lastMessage.text += message.text;
            return newMessages;
        }
        return [...newMessages, message];
    });
  }, []);

  const handleDocumentUpdate = useCallback((docData: any) => { // eslint-disable-line @typescript-eslint/no-explicit-any
    const sanitizedDoc = sanitizeDocument({
      ...docData,
      created_at: docData.uploadedAt || new Date().toISOString(),
    });

    if (sanitizedDoc.status?.toUpperCase() === 'DELETED') {
        console.log('[CaseViewPage] Document deleted event received:', sanitizedDoc.id);
        setDocuments(prev => prev.filter(d => d.id !== sanitizedDoc.id));
    } else {
        setDocuments(prev => {
            const exists = prev.some(d => d.id === sanitizedDoc.id);
            if (exists) {
                console.log('[CaseViewPage] Document updated event received:', sanitizedDoc.id);
                return prev.map(d => d.id === sanitizedDoc.id ? { ...d, ...sanitizedDoc } : d);
            } else {
                console.log('[CaseViewPage] New document added event received:', sanitizedDoc.id);
                return [sanitizedDoc, ...prev];
            }
        });
    }
  }, []);

  const handleFindingsUpdate = useCallback((findingsData: { action: string; document_id: string }) => {
    if (findingsData.action === 'delete_by_document') {
        console.log('[CaseViewPage] Findings deleted event received for doc:', findingsData.document_id);
        setCaseFindings(prev => prev.filter(f => f.document_id !== findingsData.document_id));
    }
  }, []);


  // --- HOOK INITIALIZATION ---
  const { reconnect, sendChatMessage } = useDocumentSocket(currentCaseId, !isAuthLoading && !!caseId, {
    onConnectionStatusChange: handleConnectionStatusChange,
    onChatMessage: handleChatMessage,
    onDocumentUpdate: handleDocumentUpdate,
    onFindingsUpdate: handleFindingsUpdate,
    onIsSendingChange: setIsSendingMessage,
  });

  // --- RENDER LOGIC ---
  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;

  if (error && !caseDetails) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-900/50 border border-red-600 rounded-md p-6 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-red-400 mb-4" />
          <h2 className="text-xl font-semibold text-red-300 mb-2">{t('caseView.errorLoadingTitle')}</h2>
          <p className="text-red-300 mb-4">{error || t('caseView.genericError')}</p>
          <div className="space-x-3">
            <button
              onClick={fetchCaseData}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md transition duration-200"
            >
              {t('caseView.tryAgain')}
            </button>
            <Link to="/dashboard" className="px-4 py-2 border border-gray-600 rounded-md text-gray-300 hover:bg-gray-700 transition duration-200 inline-block">
              {t('caseView.backToDashboard')}
            </Link>
          </div>
        </div>
      </div>
    );
  }
  
  if (!caseDetails) return null;

  return (
    <motion.div
        className="w-full min-h-[90vh]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:py-8">
        <div className="mb-8">
          <Link to="/dashboard" className="inline-flex items-center text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('caseView.backToDashboard')}
          </Link>
        </div>

        <div className="flex flex-col space-y-6">
            <CaseHeader caseDetails={caseDetails} t={t} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                <DocumentsPanel
                  caseId={caseDetails.id}
                  documents={documents}
                  findings={caseFindings} 
                  t={t}
                  connectionStatus={connectionStatus}
                  reconnect={reconnect}
                  onDocumentUploaded={(newDoc) => handleDocumentUpdate(newDoc)}
                  onDocumentDeleted={(docId) => setDocuments(docs => docs.filter(d => d.id !== docId))}
                  onViewOriginal={setViewingDocument}
                />
                <ChatPanel
                  messages={messages}
                  connectionStatus={connectionStatus}
                  reconnect={reconnect}
                  onSendMessage={sendChatMessage}
                  isSendingMessage={isSendingMessage}
                  caseId={caseDetails.id}
                  t={t}
                />
            </div>
            
            <FindingsPanel findings={caseFindings} t={t} />
        </div>
      </div>
      
      {viewingDocument && (
        <PDFViewerModal 
          documentData={viewingDocument}
          caseId={caseDetails.id}
          onClose={() => setViewingDocument(null)}
          t={t}
        />
      )}
    </motion.div>
  );
};

export default CaseViewPage;