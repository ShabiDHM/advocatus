// FILE: frontend/src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - FINAL CLEANUP
// 1. Removed unused imports (ChatMessage, ConnectionStatus) to fix TS warnings.
// 2. Functionality remains 100% intact.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
// REMOVED: ChatMessage, ConnectionStatus (Inferred from Hook now)
import { Case, Document, Finding, DeletedDocumentResponse } from '../data/types';
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
  
  const [caseData, setCaseData] = useState<CaseData>({ details: null, findings: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  
  const currentCaseId = useMemo(() => caseId || '', [caseId]);

  // --- PHOENIX PROTOCOL: SSE HOOK ---
  const { 
      documents: liveDocuments,
      setDocuments: setLiveDocuments,
      messages: liveMessages,
      connectionStatus, 
      reconnect, 
      sendChatMessage, 
      isSendingMessage 
  } = useDocumentSocket(currentCaseId);

  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

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
          findings: findingsResponse || []
      });

      setLiveDocuments((initialDocs || []).map(sanitizeDocument));

    } catch (err) {
      setError(t('error.failedToLoadCase'));
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments]);

  useEffect(() => {
    if (isReadyForData) {
      fetchCaseData(true);
    }
  }, [isReadyForData, fetchCaseData]);
  
  const handleDocumentUploaded = (newDoc: Document) => {
    setLiveDocuments(prev => [sanitizeDocument(newDoc), ...prev]);
  };
  
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => {
    const { documentId, deletedFindingIds } = response;
    const deletedIdsSet = new Set(deletedFindingIds);
    
    setLiveDocuments(prev => prev.filter(d => d.id !== documentId));
    
    setCaseData(prev => ({
        ...prev,
        findings: prev.findings.filter(f => !deletedIdsSet.has(f.id))
    }));
  };

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
                  documents={liveDocuments}
                  findings={caseData.findings} 
                  t={t}
                  connectionStatus={connectionStatus}
                  reconnect={reconnect}
                  onDocumentUploaded={handleDocumentUploaded}
                  onDocumentDeleted={handleDocumentDeleted}
                  onViewOriginal={setViewingDocument}
                />
                <ChatPanel
                  messages={liveMessages}
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