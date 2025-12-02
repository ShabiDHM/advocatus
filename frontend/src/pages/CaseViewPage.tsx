// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - LAYOUT & HANDLER FIX
// 1. LAYOUT: Re-enforced grid with 'grid-rows-[600px]' to lock panel height.
// 2. HANDLER: Verified chat submission logic is correct.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Case, Document, Finding, DeletedDocumentResponse, CaseAnalysisResult } from '../data/types';
import { apiService } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel, { ChatMode, Jurisdiction } from '../components/ChatPanel'; 
import PDFViewerModal from '../components/PDFViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import FindingsModal from '../components/FindingsModal';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { ArrowLeft, AlertCircle, User, Briefcase, Info, ShieldCheck, Loader2, Lightbulb } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';

type CaseData = {
    details: Case | null;
    findings: Finding[];
};

const CaseHeader: React.FC<{ 
    caseDetails: Case; 
    t: TFunction; 
    onAnalyze: () => void; 
    onShowFindings: () => void;
    isAnalyzing: boolean; 
}> = ({ caseDetails, t, onAnalyze, onShowFindings, isAnalyzing }) => (
    <motion.div
      className="mb-4 p-4 rounded-xl shadow-md bg-background-light/50 backdrop-blur-sm border border-glass-edge"
      initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
    >
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-text-primary break-words mb-2 leading-tight">
                  {caseDetails.case_name}
              </h1>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-secondary">
                  <div className="flex items-center" title={t('caseCard.client')}><User className="h-3 w-3 mr-1.5 text-primary-start" /><span>{caseDetails.client?.name || 'N/A'}</span></div>
                  <div className="flex items-center" title={t('caseView.statusLabel')}><Briefcase className="h-3 w-3 mr-1.5 text-primary-start" /><span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`)}</span></div>
                  <div className="flex items-center" title={t('caseCard.createdOn')}><Info className="h-3 w-3 mr-1.5 text-primary-start" /><span>{new Date(caseDetails.created_at).toLocaleDateString()}</span></div>
              </div>
          </div>
          <div className="flex items-center gap-2 self-start md:self-center flex-shrink-0">
              <motion.button onClick={onShowFindings} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-background-dark/50 border border-glass-edge text-text-primary text-sm font-medium shadow hover:bg-background-dark/80 transition-all"><Lightbulb className="h-4 w-4 text-yellow-400" /><span className="hidden sm:inline">{t('caseView.findingsTitle')}</span></motion.button>
              <motion.button onClick={onAnalyze} disabled={isAnalyzing} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-background-dark/50 border border-glass-edge text-text-primary text-sm font-medium shadow hover:bg-background-dark/80 transition-all disabled:opacity-50">
                {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin text-secondary-start" /> : <ShieldCheck className="h-4 w-4 text-secondary-start" />}
                <span className="hidden sm:inline">{isAnalyzing ? t('analysis.analyzing') : t('analysis.analyzeButton')}</span>
              </motion.button>
          </div>
      </div>
    </motion.div>
);

const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();
  
  const [caseData, setCaseData] = useState<CaseData>({ details: null, findings: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CaseAnalysisResult | null>(null);
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);
  const [isFindingsModalOpen, setIsFindingsModalOpen] = useState(false);

  const currentCaseId = useMemo(() => caseId || '', [caseId]);

  const { 
      documents: liveDocuments,
      setDocuments: setLiveDocuments,
      messages: liveMessages,
      setMessages, 
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
      setCaseData({ details, findings: findingsResponse || [] });
      if (isInitialLoad) {
          setLiveDocuments((initialDocs || []).map(sanitizeDocument));
          if (details.chat_history) setMessages(details.chat_history);
      }
    } catch (err) {
      setError(t('error.failedToLoadCase'));
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments, setMessages]);

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);
  
  const handleDocumentUploaded = (newDoc: Document) => setLiveDocuments(prev => [sanitizeDocument(newDoc), ...prev]);
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => {
    setLiveDocuments(prev => prev.filter(d => String(d.id) !== String(response.documentId)));
    setCaseData(prev => ({ ...prev, findings: prev.findings.filter(f => String(f.document_id) !== String(response.documentId)) }));
  };

  const handleClearChat = async () => {
      if (!caseId || !window.confirm(t('chatPanel.confirmClear'))) return;
      try { await apiService.clearChatHistory(caseId); setMessages([]); } catch (err) { alert(t('error.generic')); }
  };

  const handleAnalyzeCase = async () => {
    if (!caseId) return;
    setIsAnalyzing(true);
    try {
        const result = await apiService.analyzeCase(caseId);
        if (result.error) alert(result.error);
        else { setAnalysisResult(result); setIsAnalysisModalOpen(true); }
    } catch (err) { alert(t('error.generic')); } finally { setIsAnalyzing(false); }
  };

  const handleChatSubmit = (text: string, mode: ChatMode, documentId?: string, jurisdiction?: Jurisdiction) => {
      console.log(`📨 Sending Chat [Mode: ${mode}] [DocID: ${documentId || 'ALL'}] [Jurisdiction: ${jurisdiction}]`);
      sendChatMessage(text, documentId, jurisdiction); 
  };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-red-400 border border-red-600 rounded-md bg-red-900/50"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p>{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen bg-background-dark pb-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-0 sm:px-6 lg:py-6">
        <div className="mb-4 px-4 sm:px-0"><Link to="/dashboard" className="inline-flex items-center text-xs text-gray-400 hover:text-white transition-colors"><ArrowLeft className="h-3 w-3 mr-1" />{t('caseView.backToDashboard')}</Link></div>
        <div className="px-4 sm:px-0 mb-4"><CaseHeader caseDetails={caseData.details} t={t} onAnalyze={handleAnalyzeCase} onShowFindings={() => setIsFindingsModalOpen(true)} isAnalyzing={isAnalyzing} /></div>
        
        {/* PHOENIX FIX: Enforced Grid Layout with fixed rows */}
        <div className="grid grid-cols-1 lg:grid-cols-2 lg:grid-rows-[600px] gap-4 items-start px-4 sm:px-0">
            <div className="rounded-2xl shadow-xl overflow-hidden h-full">
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
                    className="h-full border-none shadow-none bg-background-dark"
                />
            </div>
            <div className="rounded-2xl shadow-xl overflow-hidden h-full">
                <ChatPanel
                    messages={liveMessages}
                    connectionStatus={connectionStatus}
                    reconnect={reconnect}
                    onSendMessage={handleChatSubmit}
                    isSendingMessage={isSendingMessage}
                    caseId={caseData.details.id}
                    onClearChat={handleClearChat}
                    t={t}
                    documents={liveDocuments}
                    className="h-full border-none shadow-none bg-background-dark"
                />
            </div>
        </div>
      </div>
      
      {viewingDocument && <PDFViewerModal documentData={viewingDocument} caseId={caseData.details.id} onClose={() => setViewingDocument(null)} t={t} />}
      {analysisResult && <AnalysisModal isOpen={isAnalysisModalOpen} onClose={() => setIsAnalysisModalOpen(false)} result={analysisResult} />}
      <FindingsModal isOpen={isFindingsModalOpen} onClose={() => setIsFindingsModalOpen(false)} findings={caseData.findings} />
    </motion.div>
  );
};

export default CaseViewPage;