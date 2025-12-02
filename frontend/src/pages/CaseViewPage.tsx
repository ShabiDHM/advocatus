// FILE: src/pages/CaseViewPage.tsx
import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
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

// --- Types ---
interface CaseData {
    details: Case | null;
    findings: Finding[];
}

// --- Sub-components ---

const CaseHeader: React.FC<{ 
    caseDetails: Case; 
    t: TFunction; 
    onAnalyze: () => void; 
    onShowFindings: () => void;
    isAnalyzing: boolean; 
}> = ({ caseDetails, t, onAnalyze, onShowFindings, isAnalyzing }) => (
    <motion.div
      className="p-4 rounded-xl shadow-lg bg-gray-900/40 backdrop-blur-md border border-white/10"
      initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
    >
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-white break-words mb-2 leading-tight tracking-tight">
                  {caseDetails.case_name}
              </h1>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-gray-400 font-medium">
                  <div className="flex items-center" title={t('caseCard.client')}>
                      <User className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
                      <span>{caseDetails.client?.name || t('general.notAvailable')}</span>
                  </div>
                  <div className="flex items-center" title={t('caseView.statusLabel')}>
                      <Briefcase className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
                      <span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`, { fallback: caseDetails.status })}</span>
                  </div>
                  <div className="flex items-center" title={t('caseCard.createdOn')}>
                      <Info className="h-3.5 w-3.5 mr-1.5 text-indigo-400" />
                      <span>{new Date(caseDetails.created_at).toLocaleDateString()}</span>
                  </div>
              </div>
          </div>
          
          <div className="flex items-center gap-3 self-start md:self-center flex-shrink-0">
              <motion.button
                onClick={onShowFindings}
                className="group flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800/80 border border-white/5 text-gray-200 text-sm font-medium hover:bg-gray-700 hover:border-white/20 transition-all"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Lightbulb className="h-4 w-4 text-yellow-500 group-hover:text-yellow-400 transition-colors" />
                <span className="hidden sm:inline">{t('caseView.findingsTitle')}</span>
              </motion.button>

              <motion.button
                onClick={onAnalyze}
                disabled={isAnalyzing}
                className="group flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600/90 border border-indigo-500/50 text-white text-sm font-medium shadow-lg shadow-indigo-500/20 hover:bg-indigo-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {isAnalyzing ? (
                    <Loader2 className="h-4 w-4 animate-spin text-white" />
                ) : (
                    <ShieldCheck className="h-4 w-4 text-white" />
                )}
                <span className="hidden sm:inline">
                    {isAnalyzing ? t('analysis.analyzing') : t('analysis.analyzeButton')}
                </span>
                <span className="sm:hidden">{isAnalyzing ? '...' : 'Analizo'}</span>
              </motion.button>
          </div>
      </div>
    </motion.div>
);

// --- Main Page Component ---

const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();
  const [searchParams] = useSearchParams();
  
  const [caseData, setCaseData] = useState<CaseData>({ details: null, findings: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CaseAnalysisResult | null>(null);
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);
  const [isFindingsModalOpen, setIsFindingsModalOpen] = useState(false);

  const prevReadyCount = useRef(0);
  const currentCaseId = useMemo(() => caseId || '', [caseId]);

  const { 
      documents: liveDocuments,
      setDocuments: setLiveDocuments,
      messages: liveMessages,
      setMessages, 
      connectionStatus, 
      reconnect, 
      // We don't use the hook's sendChatMessage if it doesn't support jurisdiction yet
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
          setCaseData((prev: CaseData) => ({ ...prev, findings: findingsResponse || [] }));
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

  useEffect(() => {
    if (!isLoading && caseData.details && searchParams.get('open') === 'findings') {
        setIsFindingsModalOpen(true);
    }
  }, [isLoading, caseData.details, searchParams]);
  
  const handleDocumentUploaded = (newDoc: Document) => {
    setLiveDocuments((prev: Document[]) => [sanitizeDocument(newDoc), ...prev]);
  };
  
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => {
    const { documentId } = response;
    setLiveDocuments((prev: Document[]) => prev.filter(d => String(d.id) !== String(documentId)));
    setCaseData((prev: CaseData) => {
        const newFindings = prev.findings.filter((f: Finding) => String(f.document_id) !== String(documentId));
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

  const handleChatSubmit = async (text: string, _mode: ChatMode, documentId?: string, jurisdiction?: Jurisdiction) => {
      if (!caseId) return;
      
      // Optimistic update for UI responsiveness
      const tempMsg = { sender: 'user', content: text, timestamp: new Date().toISOString() };
      // setMessages is from useDocumentSocket, might not expose a direct way to append without sending via socket
      // But typically we rely on the socket response or API response to update the list.
      // Here we will use apiService directly to support the jurisdiction param
      
      try {
          // Add user message locally first
          setMessages((prev: any) => [...prev, tempMsg]); 
          
          const responseText = await apiService.sendChatMessage(caseId, text, documentId, jurisdiction);
          
          // Add bot response
          setMessages((prev: any) => [...prev, { sender: 'ai', content: responseText, timestamp: new Date().toISOString() }]);
      } catch (err) {
          console.error("Chat Error:", err);
          alert("Failed to send message.");
      }
  };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-screen"><Loader2 className="animate-spin h-10 w-10 text-indigo-500" /></div>;
  if (error || !caseData.details) return (
    <div className="flex items-center justify-center h-screen px-4">
        <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-8 text-center max-w-lg backdrop-blur-sm">
            <AlertCircle className="mx-auto h-12 w-12 text-red-400 mb-4" />
            <h2 className="text-xl font-semibold text-red-200 mb-2">{t('caseView.errorLoadingTitle')}</h2>
            <p className="text-red-300/80 mb-4">{error || t('caseView.genericError')}</p>
            <Link to="/dashboard" className="text-sm text-indigo-400 hover:text-indigo-300 underline underline-offset-4">
                {t('caseView.backToDashboard')}
            </Link>
        </div>
    </div>
  );

  return (
    <motion.div 
        className="flex flex-col h-[calc(100vh-1rem)] md:h-[calc(100vh-2rem)] overflow-hidden" 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }}
    >
      <div className="w-full h-full flex flex-col max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-2">
        
        <div className="flex-none mb-4 space-y-3">
            <Link to="/dashboard" className="inline-flex items-center text-xs font-medium text-gray-500 hover:text-indigo-400 transition-colors">
                <ArrowLeft className="h-3 w-3 mr-1" />
                {t('caseView.backToDashboard')}
            </Link>
            
            <CaseHeader 
                caseDetails={caseData.details} 
                t={t} 
                onAnalyze={handleAnalyzeCase} 
                onShowFindings={() => setIsFindingsModalOpen(true)} 
                isAnalyzing={isAnalyzing} 
            />
        </div>
        
        <div className="flex-1 min-h-0">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
                
                <div className="h-full flex flex-col rounded-2xl shadow-2xl overflow-hidden border border-white/5 bg-gray-900/30 relative">
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
                        className="h-full w-full border-none shadow-none bg-transparent"
                    />
                </div>

                <div className="h-full flex flex-col rounded-2xl shadow-2xl overflow-hidden border border-white/5 bg-gray-900/30 relative">
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
                        className="h-full w-full border-none shadow-none bg-transparent"
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