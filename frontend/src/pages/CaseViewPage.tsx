// FILE: /home/user/advocatus-frontend/src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL MODIFICATION 21.2 (CRITICAL COMPILATION FIX):
// 1. SYNTAX CORRECTION: The 'catch' block in the 'fetchCaseDetails' function has been
//    corrected from the invalid '(err) => {' syntax to the correct ' (err) {'. This
//    resolves the catastrophic cascade of compilation errors.
// 2. TYPO FIX: Corrected the date formatting method in the CaseHeader from the invalid
//    'toLocaleDateDateString' to the correct 'toLocaleDateString'.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Case, Document, Finding } from '../data/types';
import { apiService } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel from '../components/ChatPanel';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import useAuth from '../context/AuthContext';
import { motion } from 'framer-motion';
import { ArrowLeft, AlertCircle, User, Briefcase, Info } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';

// --- COMPONENT: CaseHeader ---
const CaseHeader: React.FC<{ caseDetails: Case; t: (key: string) => string; }> = ({ caseDetails, t }) => (
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
        <span>{caseDetails.client?.name || 'N/A'}</span>
      </div>
      <div className="flex items-center" title={t('caseView.status')}>
        <Briefcase className="h-4 w-4 mr-2 text-primary-start" />
        <span className="capitalize">{caseDetails.status.toLowerCase()}</span>
      </div>
      <div className="flex items-center" title={t('caseCard.createdOn')}>
        <Info className="h-4 w-4 mr-2 text-primary-start" />
        {/* --- TYPO FIX: Corrected date formatting method --- */}
        <span>{new Date(caseDetails.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  </motion.div>
);

// --- COMPONENT: FindingsPanel ---
const FindingsPanel: React.FC<{ findings: Finding[]; t: (key: string) => string; }> = ({ findings, t }) => {
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
                            {t('caseView.findingSource')}: {finding.document_name}
                        </span>
                    </div>
                ))}
            </div>
        </motion.div>
    );
};


const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();
  const [caseDetails, setCaseDetails] = useState<Case | null>(null);
  const [caseFindings, setCaseFindings] = useState<Finding[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const currentCaseId = useMemo(() => caseId || '', [caseId]);

  const { documents, setDocuments, messages, connectionStatus, reconnect, sendChatMessage, isSendingMessage } = useDocumentSocket(currentCaseId);

  const fetchFindings = useCallback(async (cId: string) => {
    try {
        const response: { findings: Finding[] } = await apiService.getFindings(cId) as any;
        setCaseFindings(response.findings || []);
    } catch (err) {
        console.error(`Failed to load findings for case ${cId}:`, err);
        setCaseFindings([]);
    }
  }, []);

  const handleDocumentDeleted = useCallback((documentId: string) => {
    setDocuments(prev => prev.filter(doc => doc.id !== documentId));
    setCaseFindings(prev => prev.filter(finding => finding.document_id !== documentId));
  }, [setDocuments, setCaseFindings]);

  const handleDocumentUploaded = useCallback((newDocument: Document) => {
    setDocuments(prev => [sanitizeDocument(newDocument), ...prev].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
  }, [setDocuments]);

  const fetchCaseDetails = useCallback(async () => {
    if (!caseId) {
        setError(t('error.no_case_id'));
        setIsLoading(false);
        return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const details = await apiService.getCaseDetails(caseId);
      setCaseDetails(details);

      const rawDocs = await apiService.getDocuments(caseId);
      const initialDocs = (rawDocs || []).map(sanitizeDocument);

      const updatedDocs = await Promise.all(initialDocs.map(async doc => {
          if (doc.status !== 'READY' && doc.id && !doc.id.startsWith('temp-')) {
              try {
                  const latestDocData = await apiService.getDocument(caseId, doc.id);
                  return sanitizeDocument(latestDocData);
              } catch (e) { return doc; }
          }
          return doc;
      }));

      setDocuments(updatedDocs);
      await fetchFindings(caseId);

    } catch (err) { // <-- SYNTAX CORRECTION: Removed invalid arrow function syntax
      setError(t('error.failed_to_load_case'));
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [caseId, t, setDocuments, fetchFindings]);

  useEffect(() => {
    if (!isAuthLoading && caseId) {
        fetchCaseDetails();
    }
  }, [caseId, isAuthLoading, fetchCaseDetails]);


  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;

  if (error || !caseDetails) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-900/50 border border-red-600 rounded-md p-6 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-red-400 mb-4" />
          <h2 className="text-xl font-semibold text-red-300 mb-2">{t('case_view.errorLoadingTitle')}</h2>
          <p className="text-red-300 mb-4">{error || t('case_view.caseNotFound')}</p>
          <div className="space-x-3">
            <button
              onClick={fetchCaseDetails}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md transition duration-200"
            >
              {t('case_view.tryAgain')}
            </button>
            <Link
              to="/dashboard"
              className="px-4 py-2 border border-gray-600 rounded-md text-gray-300 hover:bg-gray-700 transition duration-200 inline-block"
            >
              {t('caseView.backToDashboard')}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <motion.div
        className="w-full min-h-[90vh]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        <div className="mb-8">
          <Link
            to="/dashboard"
            className="inline-flex items-center text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('caseView.backToDashboard')}
          </Link>
        </div>

        <div className="flex flex-col space-y-6">

            <CaseHeader caseDetails={caseDetails} t={t} />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch h-full">
                <div className="h-full min-h-0">
                    <DocumentsPanel
                    caseId={caseDetails.id}
                    documents={documents}
                    findings={caseFindings}
                    t={t}
                    connectionStatus={connectionStatus}
                    reconnect={reconnect}
                    onDocumentDeleted={handleDocumentDeleted}
                    onDocumentUploaded={handleDocumentUploaded}
                    />
                </div>

                <div className="h-full min-h-0">
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
            </div>

            <FindingsPanel findings={caseFindings} t={t} />

        </div>

      </div>
    </motion.div>
  );
};

export default CaseViewPage;
