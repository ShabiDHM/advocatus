// FILE: /home/user/advocatus-frontend/src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL MODIFICATION 17.0 (FINAL DATA CONTRACT ALIGNMENT):
// 1. CRITICAL FIX: Aligned the document sorting logic in `handleDocumentUploaded` with
//    the refactored 'Document' data contract from types.ts.
// 2. All references to the obsolete `uploadedAt` property have been replaced with the
//    correct `created_at` property, resolving the final TypeScript build errors.
// 3. This completes the system-wide refactoring, ensuring the entire frontend codebase
//    is now consistent with the authoritative data contract.
//
// PHOENIX PROTOCOL MODIFICATION 16.0 (STATE MACHINE ALIGNMENT)
// ...

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
import { ArrowLeft, AlertCircle } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';

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
        const response: any = await apiService.getFindings(cId); 
        const findingsArray = response.findings || [];
        setCaseFindings(findingsArray);
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
    // --- PHOENIX PROTOCOL FIX: Use correct field `created_at` ---
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

    } catch (err) {
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
          <div className="flex items-center space-x-4 mb-4">
            <Link
              to="/dashboard"
              className="inline-flex items-center text-gray-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              {t('caseView.backToDashboard')}
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch h-full grid-rows-[1fr]">
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
        
      </div>
    </motion.div>
  );
};

export default CaseViewPage;