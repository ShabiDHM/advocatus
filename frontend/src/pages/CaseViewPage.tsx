// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - MOBILE HEADER FIX
// 1. MOBILE: Improved CaseHeader flex-wrapping to prevent overlap.
// 2. LAYOUT: Ensured back button doesn't stick awkwardly.

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
      className="mb-6 p-4 rounded-2xl shadow-lg bg-background-light/50 backdrop-blur-sm border border-white/10"
      initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
    >
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex-1 min-w-0 w-full">
              <h1 className="text-xl sm:text-2xl font-bold text-text-primary break-words mb-3 leading-tight">
                  {caseDetails.case_name}
              </h1>
              {/* Mobile: Wrap flex-row to stack nicely if too tight */}
              <div className="flex flex-row flex-wrap items-center gap-x-6 gap-y-2 text-xs sm:text-sm text-text-secondary">
                  <div className="flex items-center"><User className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{caseDetails.client?.name || 'N/A'}</span></div>
                  <div className="flex items-center"><Briefcase className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`)}</span></div>
                  <div className="flex items-center"><Info className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{new Date(caseDetails.created_at).toLocaleDateString()}</span></div>
              </div>
          </div>
          
          <div className="flex items-center gap-3 self-start md:self-center flex-shrink-0 w-full md:w-auto mt-2 md:mt-0">
              <button onClick={onShowFindings} className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-black/20 hover:bg-black/40 border border-white/10 text-gray-200 text-sm font-medium transition-all"><Lightbulb className="h-4 w-4 text-amber-400" /><span className="inline">{t('caseView.findingsTitle')}</span></button>
              <button onClick={onAnalyze} disabled={isAnalyzing} className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-secondary-start/10 hover:bg-secondary-start/20 border border-secondary-start/30 text-secondary-start text-sm font-medium transition-all disabled:opacity-50">{isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}<span className="inline">{isAnalyzing ? t('analysis.analyzing') : t('analysis.analyzeButton')}</span></button>
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
      console.error("Load Error:", err);
      setError(t('error.failedToLoadCase'));
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments, setMessages]);

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);
  
  const handleDocumentUploaded = (newDoc: Document) => {
    setLiveDocuments(prev => [sanitizeDocument(newDoc), ...prev]);
  };
  
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

  const handleChatSubmit = (text: string, _mode: ChatMode, documentId?: string, jurisdiction?: Jurisdiction) => {
      sendChatMessage(text, documentId, jurisdiction); 
  };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-red-400 border border-red-600 rounded-md bg-red-900/50"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p>{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen bg-background-dark pb-10" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:py-6">
        <div className="mb-4"><Link to="/dashboard" className="inline-flex items-center text-xs text-gray-400 hover:text-white transition-colors"><ArrowLeft className="h-3 w-3 mr-1" />{t('caseView.backToDashboard')}</Link></div>
        <CaseHeader caseDetails={caseData.details} t={t} onAnalyze={handleAnalyzeCase} onShowFindings={() => setIsFindingsModalOpen(true)} isAnalyzing={isAnalyzing} />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            <div className="w-full h-[500px]">
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
                    className="h-full"
                />
            </div>

            <div className="w-full h-[500px]">
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
                    className="h-full"
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