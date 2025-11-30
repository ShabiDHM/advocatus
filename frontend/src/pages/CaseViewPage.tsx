// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW (LAYOUT REPAIR)
// 1. HEADER FIX: Compacted layout. Title & Metadata grouped left, Buttons right. Removed wasted vertical space.
// 2. PANEL FIX: Switched to pure Flexbox layout. Panels now auto-fill remaining height (flex-1) without shrinking.
// 3. STATUS: Visuals restored to "Image 2" density with "Image 1" functionality.

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Case, Document, Finding, DeletedDocumentResponse, CaseAnalysisResult } from '../data/types';
import { apiService } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel from '../components/ChatPanel';
import CaseGraph from '../components/CaseGraph';
import PDFViewerModal from '../components/PDFViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import FindingsModal from '../components/FindingsModal';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { ArrowLeft, AlertCircle, User, Briefcase, Info, ShieldCheck, Loader2, Lightbulb, FileText, Network } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';

type CaseData = {
    details: Case | null;
    findings: Finding[];
};

type ViewTab = 'documents' | 'graph';

const CaseHeader: React.FC<{ 
    caseDetails: Case; 
    t: TFunction; 
    onAnalyze: () => void; 
    onShowFindings: () => void;
    isAnalyzing: boolean; 
}> = ({ caseDetails, t, onAnalyze, onShowFindings, isAnalyzing }) => (
    <motion.div
      className="mb-2 p-4 rounded-xl shadow-md bg-background-light/50 backdrop-blur-sm border border-glass-edge flex-shrink-0"
      initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
    >
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          {/* LEFT: Title & Metadata */}
          <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-text-primary break-words mb-2 leading-tight">
                  {caseDetails.case_name}
              </h1>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-text-secondary">
                  <div className="flex items-center" title={t('caseCard.client')}>
                      <User className="h-3 w-3 mr-1.5 text-primary-start" />
                      <span>{caseDetails.client?.name || t('general.notAvailable')}</span>
                  </div>
                  <div className="flex items-center" title={t('caseView.statusLabel')}>
                      <Briefcase className="h-3 w-3 mr-1.5 text-primary-start" />
                      <span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`, { fallback: caseDetails.status })}</span>
                  </div>
                  <div className="flex items-center" title={t('caseCard.createdOn')}>
                      <Info className="h-3 w-3 mr-1.5 text-primary-start" />
                      <span>{new Date(caseDetails.created_at).toLocaleDateString()}</span>
                  </div>
              </div>
          </div>
          
          {/* RIGHT: Action Buttons */}
          <div className="flex items-center gap-2 self-start md:self-center flex-shrink-0">
              <motion.button
                onClick={onShowFindings}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-background-dark/50 border border-glass-edge text-text-primary text-sm font-medium shadow hover:bg-background-dark/80 transition-all"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Lightbulb className="h-4 w-4 text-yellow-400" />
                <span className="hidden sm:inline">{t('caseView.findingsTitle')}</span>
              </motion.button>

              <motion.button
                onClick={onAnalyze}
                disabled={isAnalyzing}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-background-dark/50 border border-glass-edge text-text-primary text-sm font-medium shadow hover:bg-background-dark/80 transition-all disabled:opacity-50"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin text-secondary-start" /> : <ShieldCheck className="h-4 w-4 text-secondary-start" />}
                <span className="hidden sm:inline">{isAnalyzing ? t('analysis.analyzing') : t('analysis.analyzeButton')}</span>
                <span className="sm:hidden">{isAnalyzing ? '...' : 'Analizo'}</span>
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

  const [activeTab, setActiveTab] = useState<ViewTab>('documents');

  const prevReadyCount = useRef(0);
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
          if (details.chat_history && details.chat_history.length > 0) {
              setMessages(details.chat_history);
          }
          const readyDocs = (initialDocs || []).filter(d => d.status === 'COMPLETED' || d.status === 'READY');
          prevReadyCount.current = readyDocs.length;
      } else {
          setCaseData(prev => ({ ...prev, findings: findingsResponse || [] }));
      }

    } catch (err) {
      console.error("Load Error:", err);
      setError(t('error.failedToLoadCase'));
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments, setMessages]);

  useEffect(() => {
     const currentReadyCount = liveDocuments.filter(d => d.status === 'COMPLETED' || d.status === 'READY').length;
     if (currentReadyCount > prevReadyCount.current) {
         fetchCaseData(false); 
     }
     prevReadyCount.current = currentReadyCount;
  }, [liveDocuments, fetchCaseData]);

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);
  
  const handleDocumentUploaded = (newDoc: Document) => {
    setLiveDocuments(prev => [sanitizeDocument(newDoc), ...prev]);
  };
  
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => {
    const { documentId } = response;
    setLiveDocuments(prev => prev.filter(d => String(d.id) !== String(documentId)));
    setCaseData(prev => {
        const newFindings = prev.findings.filter(f => String(f.document_id) !== String(documentId));
        return { ...prev, findings: newFindings };
    });
  };

  const handleClearChat = async () => {
      if (!caseId) return;
      if (!window.confirm(t('chatPanel.confirmClear'))) return;
      try {
          await apiService.clearChatHistory(caseId);
          setMessages([]); 
      } catch (err) {
          console.error("Failed to clear chat:", err);
          alert(t('error.generic'));
      }
  };

  const handleAnalyzeCase = async () => {
    if (!caseId) return;
    setIsAnalyzing(true);
    try {
        const result = await apiService.analyzeCase(caseId);
        if (result.error) {
            alert(result.error);
        } else {
            setAnalysisResult(result);
            setIsAnalysisModalOpen(true);
        }
    } catch (err) {
        console.error("Analysis failed:", err);
        alert(t('error.generic'));
    } finally {
        setIsAnalyzing(false);
    }
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
    // FIX: Using h-screen minus header offset to force full height without scrollbar issues
    <motion.div className="w-full h-[calc(100vh-64px)] flex flex-col" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-0 sm:px-6 lg:py-4 flex-grow flex flex-col min-h-0">
        
        {/* Navigation - Compact */}
        <div className="mb-2 px-4 sm:px-0 flex-shrink-0">
          <Link to="/dashboard" className="inline-flex items-center text-xs text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="h-3 w-3 mr-1" />
            {t('caseView.backToDashboard')}
          </Link>
        </div>
        
        {/* Header - Compact */}
        <div className="px-4 sm:px-0 flex-shrink-0">
            <CaseHeader 
                caseDetails={caseData.details} 
                t={t} 
                onAnalyze={handleAnalyzeCase} 
                onShowFindings={() => setIsFindingsModalOpen(true)} 
                isAnalyzing={isAnalyzing} 
            />
        </div>

        {/* Tabs - Compact */}
        <div className="px-4 sm:px-0 flex gap-4 border-b border-glass-edge mb-3 flex-shrink-0">
            <button 
                onClick={() => setActiveTab('documents')}
                className={`pb-2 px-1 flex items-center gap-2 text-sm font-medium transition-colors border-b-2 ${activeTab === 'documents' ? 'border-primary-start text-white' : 'border-transparent text-gray-400 hover:text-white'}`}
            >
                <FileText className="w-4 h-4" />
                Dokumentet
            </button>
            <button 
                onClick={() => setActiveTab('graph')}
                className={`pb-2 px-1 flex items-center gap-2 text-sm font-medium transition-colors border-b-2 ${activeTab === 'graph' ? 'border-primary-start text-white' : 'border-transparent text-gray-400 hover:text-white'}`}
            >
                <Network className="w-4 h-4" />
                Harta e Çështjes
            </button>
        </div>
        
        {/* MAIN CONTENT AREA - FLEX GROW TO FILL REMAINING SPACE */}
        {/* This creates the parallel side-by-side layout that fills the screen */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start px-4 sm:px-0 flex-1 min-h-0 overflow-hidden pb-2">
            {/* Left Panel */}
            <div className="h-full overflow-hidden flex flex-col rounded-2xl shadow-xl">
                {activeTab === 'documents' ? (
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
                        className="h-full border-none shadow-none bg-background-dark" // Fill container
                    />
                ) : (
                    <CaseGraph caseId={caseData.details.id} className="h-full bg-slate-900 border-none" />
                )}
            </div>

            {/* Right Panel: Chat */}
            <div className="h-full overflow-hidden flex flex-col rounded-2xl shadow-xl">
                <ChatPanel
                    messages={liveMessages}
                    connectionStatus={connectionStatus}
                    reconnect={reconnect}
                    onSendMessage={sendChatMessage}
                    isSendingMessage={isSendingMessage}
                    caseId={caseData.details.id}
                    onClearChat={handleClearChat}
                    t={t}
                    className="h-full border-none shadow-none bg-background-dark" // Fill container
                />
            </div>
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
      
      {analysisResult && (
          <AnalysisModal 
             isOpen={isAnalysisModalOpen}
             onClose={() => setIsAnalysisModalOpen(false)}
             result={analysisResult}
          />
      )}

      <FindingsModal 
        isOpen={isFindingsModalOpen}
        onClose={() => setIsFindingsModalOpen(false)}
        findings={caseData.findings}
      />
    </motion.div>
  );
};

export default CaseViewPage;