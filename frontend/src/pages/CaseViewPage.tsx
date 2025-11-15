// FILE: /home/user/advocatus-frontend/src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - FINAL DEFINITIVE VERSION (STATE & RENDER INTEGRITY)
// CORRECTION 1 (TRANSACTIONAL STATE): Re-architected to use the 'useReducer' hook. This is
// the definitive fix for all stale state issues. It guarantees that document and finding
// updates are atomic and transactional, preventing re-render bugs.
// CORRECTION 2 (TRANSLATION PROPAGATION): Passed the 't' function explicitly to all child
// components. This resolves the race condition where child components would render with a
// stale translation function after a parent state update.

import React, { useState, useEffect, useCallback, useMemo, useReducer } from 'react';
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

// --- STATE MANAGEMENT WITH useReducer (Definitive Fix) ---
type State = { documents: Document[]; findings: Finding[]; };
type Action = 
  | { type: 'SET_ALL_DATA'; payload: { documents: Document[]; findings: Finding[] } }
  | { type: 'ADD_OR_UPDATE_DOCUMENT'; payload: Document }
  | { type: 'DELETE_DOCUMENT_AND_FINDINGS'; payload: DeletedDocumentResponse }
  | { type: 'SET_FINDINGS'; payload: Finding[] };

const initialState: State = { documents: [], findings: [] };

function caseDataReducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_ALL_DATA':
      return { 
        documents: action.payload.documents.map(sanitizeDocument), 
        findings: action.payload.findings 
      };
    case 'ADD_OR_UPDATE_DOCUMENT': {
      const sanitizedDoc = sanitizeDocument(action.payload);
      const exists = state.documents.some(d => d.id === sanitizedDoc.id);
      if (exists) {
        return { ...state, documents: state.documents.map(d => d.id === sanitizedDoc.id ? { ...d, ...sanitizedDoc } : d) };
      }
      return { ...state, documents: [sanitizedDoc, ...state.documents] };
    }
    case 'DELETE_DOCUMENT_AND_FINDINGS': {
      const { documentId, deletedFindingIds } = action.payload;
      const deletedIdsSet = new Set(deletedFindingIds);
      return {
        documents: state.documents.filter(d => d.id !== documentId),
        findings: state.findings.filter(f => !deletedIdsSet.has(f.id))
      };
    }
    case 'SET_FINDINGS':
      return { ...state, findings: action.payload };
    default:
      return state;
  }
}

// --- SUB-COMPONENTS ---
const CaseHeader: React.FC<{ caseDetails: Case; t: TFunction; }> = ({ caseDetails, t }) => (
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

const FindingsPanel: React.FC<{ findings: Finding[]; t: TFunction; }> = ({ findings, t }) => {
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
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();
  
  const [caseData, dispatch] = useReducer(caseDataReducer, initialState);
  const { documents, findings: caseFindings } = caseData;

  const [caseDetails, setCaseDetails] = useState<Case | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('DISCONNECTED');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  
  const isReadyForSocket = isAuthenticated && !isAuthLoading && !!caseId;

  const fetchCaseData = useCallback(async () => {
    if (!caseId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [details, initialDocs, findingsResponse] = await Promise.all([
        apiService.getCaseDetails(caseId),
        apiService.getDocuments(caseId),
        apiService.getFindings(caseId)
      ]);
      setCaseDetails(details);
      dispatch({ type: 'SET_ALL_DATA', payload: { documents: initialDocs || [], findings: findingsResponse || [] } });
    } catch (err) {
      setError(t('error.failedToLoadCase'));
    } finally {
      setIsLoading(false);
    }
  }, [caseId, t]);

  useEffect(() => {
    if (!isAuthLoading && caseId) {
      fetchCaseData();
    }
  }, [caseId, isAuthLoading, fetchCaseData]);

  const pollDocumentStatus = useCallback((docId: string) => {
    const intervalId = setInterval(async () => {
        if (!caseId) { clearInterval(intervalId); return; }
        try {
            const updatedDoc = await apiService.getDocument(caseId, docId);
            const isFinished = updatedDoc.status.toUpperCase() === 'READY' || updatedDoc.status.toUpperCase() === 'FAILED';
            dispatch({ type: 'ADD_OR_UPDATE_DOCUMENT', payload: updatedDoc });
            if (isFinished) {
                clearInterval(intervalId);
                if (updatedDoc.status.toUpperCase() === 'READY') {
                    const findingsResponse = await apiService.getFindings(caseId);
                    dispatch({ type: 'SET_FINDINGS', payload: findingsResponse || [] });
                }
            }
        } catch (error) {
            clearInterval(intervalId);
        }
    }, 3000);
    return () => clearInterval(intervalId);
  }, [caseId]);
  
  const handleDocumentUploaded = (newDoc: Document) => {
    dispatch({ type: 'ADD_OR_UPDATE_DOCUMENT', payload: newDoc });
    pollDocumentStatus(newDoc.id);
  };
  
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => {
    dispatch({ type: 'DELETE_DOCUMENT_AND_FINDINGS', payload: response });
  };
  
  const handleChatMessage = useCallback((message: ChatMessage) => {
    setMessages(prev => prev.length > 0 && prev[prev.length - 1].sender === 'AI' && message.isPartial 
        ? prev.map((m, i) => i === prev.length - 1 ? { ...m, text: m.text + message.text } : m) 
        : [...prev, message]);
  }, []);

  const { reconnect, sendChatMessage } = useDocumentSocket(currentCaseId, isReadyForSocket, {
    onConnectionStatusChange: setConnectionStatus,
    onChatMessage: handleChatMessage,
    onDocumentUpdate: (doc) => dispatch({ type: 'ADD_OR_UPDATE_DOCUMENT', payload: doc }),
    onFindingsUpdate: fetchCaseData,
    onIsSendingChange: setIsSendingMessage,
  });
  
  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error && !caseDetails) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-900/50 border border-red-600 rounded-md p-6 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-red-400 mb-4" />
          <h2 className="text-xl font-semibold text-red-300 mb-2">{t('caseView.errorLoadingTitle')}</h2>
          <p className="text-red-300 mb-4">{error || t('caseView.genericError')}</p>
        </div>
      </div>
    );
  }
  
  if (!caseDetails) return null;

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
            <CaseHeader caseDetails={caseDetails} t={t} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                <DocumentsPanel
                  caseId={caseDetails.id}
                  documents={documents}
                  findings={caseFindings} 
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