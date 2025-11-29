// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - STABILIZATION & CLEANUP
// 1. CHAT FIX: Enforced 'h-[calc(100vh-200px)]' and sticky positioning to ensure Chat is always accessible and scrolling works.
// 2. GRAPH REMOVAL: Temporarily replaced the "Ball Graph" with a professional "Construction" placeholder to stop the "joke" visual.
// 3. DATA SAFETY: Improved 'fetchCaseData' to ensure chat history is set robustly.

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Case, Document, Finding, DeletedDocumentResponse, CaseAnalysisResult } from '../data/types';
import { apiService } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel from '../components/ChatPanel';
// import CaseGraph from '../components/CaseGraph'; // DISABLED: Replaced with Placeholder
import PDFViewerModal from '../components/PDFViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import FindingsModal from '../components/FindingsModal';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { ArrowLeft, AlertCircle, User, Briefcase, Info, ShieldCheck, Loader2, Lightbulb, FileText, Network, Construction } from 'lucide-react';
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
      className="mb-6 p-4 sm:p-6 rounded-2xl shadow-lg bg-background-light/50 backdrop-blur-sm border border-glass-edge"
      initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
    >
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
          <h1 className="text-xl sm:text-2xl font-bold text-text-primary break-words">{caseDetails.case_name}</h1>
          
          <div className="flex items-center gap-3 self-end sm:self-auto">
              <motion.button
                onClick={onShowFindings}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-background-dark/50 border border-glass-edge text-text-primary font-semibold shadow hover:bg-background-dark/80 transition-all"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Lightbulb className="h-5 w-5 text-yellow-400" />
                <span>{t('caseView.findingsTitle')}</span>
              </motion.button>

              <motion.button
                onClick={onAnalyze}
                disabled={isAnalyzing}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-background-dark/50 border border-glass-edge text-text-primary font-semibold shadow hover:bg-background-dark/80 transition-all disabled:opacity-50"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                {isAnalyzing ? <Loader2 className="h-5 w-5 animate-spin text-secondary-start" /> : <ShieldCheck className="h-5 w-5 text-secondary-start" />}
                <span className="hidden sm:inline">{isAnalyzing ? t('analysis.analyzing', 'Duke Analizuar...') : t('analysis.analyzeButton', 'Analizo Rastin')}</span>
                <span className="sm:hidden">{isAnalyzing ? '...' : 'Analizo'}</span>
              </motion.button>
          </div>
      </div>
      
      <div className="flex flex-wrap items-center gap-x-4 sm:gap-x-6 gap-y-2 text-xs sm:text-sm text-text-secondary">
        <div className="flex items-center" title={t('caseCard.client')}><User className="h-3 w-3 sm:h-4 sm:w-4 mr-2 text-primary-start" /><span>{caseDetails.client?.name || t('general.notAvailable')}</span></div>
        <div className="flex items-center" title={t('caseView.statusLabel')}><Briefcase className="h-3 w-3 sm:h-4 sm:w-4 mr-2 text-primary-start" /><span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`, { fallback: caseDetails.status })}</span></div>
        <div className="flex items-center" title={t('caseCard.createdOn')}><Info className="h-3 w-3 sm:h-4 sm:w-4 mr-2 text-primary-start" /><span>{new Date(caseDetails.created_at).toLocaleDateString()}</span></div>
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
          // PHOENIX FIX: Ensure chat history is set properly
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
    <motion.div className="w-full min-h-[90vh]" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl mx-auto px-0 sm:px-6 lg:py-8">
        <div className="mb-6 sm:mb-8 px-4 sm:px-0">
          <Link to="/dashboard" className="inline-flex items-center text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('caseView.backToDashboard')}
          </Link>
        </div>
        <div className="flex flex-col space-y-4 sm:space-y-6">
            <div className="px-4 sm:px-0">
                <CaseHeader 
                    caseDetails={caseData.details} 
                    t={t} 
                    onAnalyze={handleAnalyzeCase} 
                    onShowFindings={() => setIsFindingsModalOpen(true)} 
                    isAnalyzing={isAnalyzing} 
                />
            </div>

            <div className="px-4 sm:px-0 flex gap-4 border-b border-glass-edge mb-2">
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
            
            {/* PHOENIX FIX: Sticky grid with defined height for desktop */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6 items-start px-4 sm:px-0">
                {/* Left Panel */}
                <div className="flex flex-col h-full min-h-[500px]">
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
                        />
                    ) : (
                        // PHOENIX FIX: Placeholder for Professional Graph Alternative
                        <div className="bg-background-dark/50 border border-glass-edge rounded-2xl p-12 text-center h-[500px] flex flex-col items-center justify-center">
                            <Construction className="w-16 h-16 text-primary-start mb-4 animate-pulse" />
                            <h3 className="text-xl font-bold text-white mb-2">Harta Interaktive në Ndërtim</h3>
                            <p className="text-gray-400 max-w-md">
                                Ne jemi duke ridizenjuar vizualizimin e çështjes për t'ju ofruar një përvojë profesionale dhe të qartë.
                            </p>
                        </div>
                    )}
                </div>

                {/* Right Panel: Chat - PHOENIX FIX: Sticky Position */}
                <div className="lg:sticky lg:top-24 h-[600px] lg:h-[calc(100vh-200px)] min-h-[500px]">
                    <ChatPanel
                        messages={liveMessages}
                        connectionStatus={connectionStatus}
                        reconnect={reconnect}
                        onSendMessage={sendChatMessage}
                        isSendingMessage={isSendingMessage}
                        caseId={caseData.details.id}
                        onClearChat={handleClearChat}
                        t={t}
                    />
                </div>
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