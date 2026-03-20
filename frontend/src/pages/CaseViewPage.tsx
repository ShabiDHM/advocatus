// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V11.4 (FIXED UNUSED isAdmin)
// 1. Removed unused 'isAdmin' prop from CaseHeader.
// 2. All mobile-friendly improvements retained.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Case, Document, DeletedDocumentResponse, CaseAnalysisResult, ChatMessage } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel, { ChatMode, Jurisdiction, ReasoningMode, LegalDomain } from '../components/ChatPanel';
import PDFViewerModal from '../components/FileViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import SpreadsheetAnalyst from '../components/SpreadsheetAnalyst';
import { DocumentSelector } from '../components/DocumentSelector';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, User, ShieldCheck, Loader2, X, Save, Calendar, Activity, Lock } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';
import DockedPDFViewer from '../components/DockedPDFViewer';

type CaseData = { details: Case | null; };
type ActiveModal = 'none' | 'analysis';
type ViewMode = 'workspace' | 'analyst';

const extractAndNormalizeHistory = (data: any): ChatMessage[] => {
    if (!data) return [];
    const rawArray = data.chat_history || data.chatHistory || data.history || data.messages || [];
    if (!Array.isArray(rawArray)) return [];
    return rawArray.map((item: any) => {
        const rawRole = (item.role || item.sender || item.author || 'user').toString().toLowerCase();
        const role: 'user' | 'ai' = (rawRole.includes('ai') || rawRole.includes('assistant') || rawRole.includes('system')) ? 'ai' : 'user';
        const content = item.content || item.message || item.text || '';
        const timestamp = item.timestamp || item.created_at || new Date().toISOString();
        return { role, content, timestamp };
    }).filter(msg => msg.content.trim() !== '');
};

const RenameDocumentModal: React.FC<{ isOpen: boolean; onClose: () => void; onRename: (newName: string) => Promise<void>; currentName: string; t: TFunction; }> = ({ isOpen, onClose, onRename, currentName, t }) => {
    const [name, setName] = useState(currentName);
    const [isSaving, setIsSaving] = useState(false);
    useEffect(() => { setName(currentName); }, [currentName]);
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault(); if (!name.trim()) return; setIsSaving(true);
        try { await onRename(name); onClose(); } finally { setIsSaving(false); }
    };
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[100] p-4">
            <div className="glass-panel w-full max-w-md p-6 rounded-2xl">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold text-text-primary">{t('documentsPanel.renameTitle')}</h3>
                    <button onClick={onClose} className="text-text-secondary hover:text-text-primary p-1 rounded-lg hover:bg-surface/10 transition-colors"><X size={24} /></button>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="mb-6"><label className="block text-sm text-text-secondary mb-2">{t('documentsPanel.newName')}</label><input autoFocus type="text" value={name} onChange={(e) => setName(e.target.value)} className="glass-input w-full rounded-xl px-4 py-3" /></div>
                    <div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="px-4 py-2 text-text-secondary hover:text-text-primary font-medium transition-colors">{t('general.cancel')}</button><button type="submit" disabled={isSaving} className="btn-primary flex items-center gap-2">{isSaving ? <Loader2 className="animate-spin h-4 w-4" /> : <Save size={16} />}{t('general.save')}</button></div>
                </form>
            </div>
        </div>
    );
};

const CaseHeader: React.FC<{ 
    caseDetails: Case;
    documents: Document[];
    t: TFunction; 
    onAnalyze: () => void;
    isAnalyzing: boolean; 
    viewMode: ViewMode;
    setViewMode: (mode: ViewMode) => void;
    isPro: boolean; 
    selectedDocumentIds: string[];
    onDocumentSelectionChange: (ids: string[]) => void;
}> = ({ caseDetails, documents, t, onAnalyze, isAnalyzing, viewMode, setViewMode, isPro, selectedDocumentIds, onDocumentSelectionChange }) => {
    
    const analyzeButtonText = selectedDocumentIds.length === 0
        ? t('analysis.analyzeButton', 'Analizo Rastin')
        : t('analysis.crossExamineButton', 'Kryqëzo Dokumentin');

    // Determine which buttons to show based on view mode and pro status
    const showDateBadge = true;
    const showDocumentSelector = viewMode === 'workspace';
    const showAnalystToggle = true;
    const showAnalyzeButton = viewMode === 'workspace';

    // Grid columns count on mobile: 1; on md: 4 (all buttons visible)
    const buttonCount = [showDateBadge, showDocumentSelector, showAnalystToggle, showAnalyzeButton].filter(Boolean).length;
    const gridColsClass = buttonCount === 4 ? 'grid-cols-1 md:grid-cols-4' : 'grid-cols-1';

    return (
        <motion.div className="relative mb-6 group" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <div className="absolute inset-0 rounded-panel overflow-hidden border border-main shadow-xl">
              <div className="absolute inset-0 bg-surface/40 backdrop-blur-md" />
              <div className="absolute top-0 right-0 p-32 bg-primary-start/5 blur-[100px] rounded-full pointer-events-none" />
          </div>

          <div className="relative p-5 sm:p-6 flex flex-col gap-5 z-10">
              <div className="flex flex-col gap-1">
                  <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-text-primary tracking-tight leading-snug break-words">{caseDetails.case_name || caseDetails.title || t('caseView.unnamedCase', 'Rast pa Emër')}</h1>
                  <div className="flex items-center gap-2 text-text-secondary mt-1"><User className="h-4 w-4 text-primary-start" /><span className="text-sm sm:text-base font-medium">{caseDetails.client?.name || t('caseCard.unknownClient', 'Klient i Panjohur')}</span></div>
              </div>

              <div className="h-px w-full bg-gradient-to-r from-transparent via-main to-transparent" />

              {/* Executive Action Bar - responsive grid */}
              <div className={`grid ${gridColsClass} gap-3 w-full animate-in fade-in slide-in-from-top-2`}>
                    {/* Date badge */}
                    {showDateBadge && (
                        <div className="h-12 md:h-11 rounded-xl flex items-center justify-center gap-2 px-4 bg-surface/10 border border-main text-text-secondary text-sm font-medium whitespace-nowrap">
                            <Calendar className="h-4 w-4 text-blue-400" />
                            <span className="hidden xs:inline">{new Date(caseDetails.created_at).toLocaleDateString()}</span>
                            <span className="xs:hidden">{new Date(caseDetails.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                        </div>
                    )}
                    
                    {/* Document selector (only in workspace) */}
                    {showDocumentSelector && (
                        <div className="h-12 md:h-11 min-w-0">
                            <DocumentSelector
                                documents={documents.map(d => ({ id: d.id, file_name: d.file_name }))}
                                selectedIds={selectedDocumentIds}
                                onChange={onDocumentSelectionChange}
                                disabled={!isPro}
                            />
                        </div>
                    )}
                    
                    {/* Analyst toggle */}
                    {showAnalystToggle && (
                        <button
                            onClick={() => isPro && setViewMode(viewMode === 'workspace' ? 'analyst' : 'workspace')}
                            disabled={!isPro}
                            className={`h-12 md:h-11 rounded-xl flex items-center justify-center gap-2.5 text-sm font-medium transition-all duration-300 whitespace-nowrap border hover-lift ${
                                !isPro 
                                    ? 'bg-surface/10 border border-main text-text-secondary cursor-not-allowed opacity-70' 
                                    : viewMode === 'analyst' 
                                        ? 'bg-primary-start/10 border-primary-start text-primary-start' 
                                        : 'bg-surface/10 border-main text-text-secondary hover:text-text-primary hover:bg-surface/20'
                            }`}
                            title={!isPro ? "Available on Pro Plan" : ""}
                        >
                            {!isPro ? <Lock size={16} className="text-text-secondary" /> : <Activity size={16} className={viewMode === 'analyst' ? 'text-primary-start' : 'text-text-secondary'} />}
                            <span className="hidden xs:inline">{t('caseView.financialAnalyst', 'Analisti Financiar')}</span>
                            <span className="xs:hidden">{t('caseView.financialAnalystShort', 'Analist')}</span>
                        </button>
                    )}

                    {/* Analyze button */}
                    {showAnalyzeButton && (
                        <button
                            onClick={onAnalyze}
                            disabled={!isPro || isAnalyzing}
                            className={`h-12 md:h-11 rounded-xl flex items-center justify-center gap-2.5 text-sm font-medium transition-all duration-300 whitespace-nowrap border hover-lift ${
                                !isPro || isAnalyzing
                                    ? 'bg-surface/10 border-main text-text-secondary cursor-not-allowed opacity-70'
                                    : 'bg-surface/10 border-main text-primary-start hover:bg-primary-start/5 hover:border-primary-start'
                            }`}
                            type="button"
                            title={!isPro ? "Available on Pro Plan" : ""}
                        >
                            {isAnalyzing ? (
                                <><Loader2 size={16} className="animate-spin text-primary-start" /> <span>{t('analysis.analyzing', 'Duke analizuar...')}</span></>
                            ) : !isPro ? (
                                <><Lock size={16} className="text-text-secondary" /> <span className="hidden xs:inline">{analyzeButtonText}</span><span className="xs:hidden">{t('analysis.analyzeShort', 'Analizo')}</span></>
                            ) : (
                                <><ShieldCheck size={16} className="text-primary-start" /> <span className="hidden xs:inline">{analyzeButtonText}</span><span className="xs:hidden">{t('analysis.analyzeShort', 'Analizo')}</span></>
                            )}
                        </button>
                    )}
              </div>
          </div>
        </motion.div>
    );
};

const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading, isAuthenticated, user } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();
  
  const [caseData, setCaseData] = useState<CaseData>({ details: null });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const [minimizedDocument, setMinimizedDocument] = useState<Document | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CaseAnalysisResult | null>(null);
  const [activeModal, setActiveModal] = useState<ActiveModal>('none');
  const [documentToRename, setDocumentToRename] = useState<Document | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('workspace');
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);

  // Local chat messages (managed via HTTP streaming)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  const isPro = useMemo(() => {
      if (!user) return false;
      return user.subscription_tier === 'PRO' || user.role === 'ADMIN';
  }, [user]);

  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, connectionStatus, reconnect } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  const fetchCaseData = useCallback(async (isInitialLoad = false) => {
    if (!caseId) return;
    if(isInitialLoad) setIsLoading(true);
    setError(null);
    try {
      const [details, initialDocs] = await Promise.all([
        apiService.getCaseDetails(caseId),
        apiService.getDocuments(caseId)
      ]);
      setCaseData({ details });
      setLiveDocuments((initialDocs || []).map(sanitizeDocument));
      
      const serverHistory = extractAndNormalizeHistory(details);
      setChatMessages(serverHistory);
      
      if (serverHistory.length > 0) {
        localStorage.setItem(`chat_history_${caseId}`, JSON.stringify(serverHistory));
      } else {
        localStorage.removeItem(`chat_history_${caseId}`);
      }
    } catch (err) {
      setError(t('error.failedToLoadCase'));
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments]);

  useEffect(() => {
    if (isReadyForData) fetchCaseData(true);
  }, [isReadyForData, fetchCaseData]);

  useEffect(() => {
    if (!currentCaseId) return;
    if (chatMessages.length > 0) {
      localStorage.setItem(`chat_history_${currentCaseId}`, JSON.stringify(chatMessages));
    } else {
      localStorage.removeItem(`chat_history_${currentCaseId}`);
    }
  }, [chatMessages, currentCaseId]);

  const handleDocumentUploaded = (newDoc: Document) => { setLiveDocuments(prev => [sanitizeDocument(newDoc), ...prev]); };
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => { setLiveDocuments(prev => prev.filter(d => String(d.id) !== String(response.documentId))); };
  
  const handleClearChat = async () => {
    if (!caseId) return;
    try {
      await apiService.clearChatHistory(caseId);
      setChatMessages([]);
      localStorage.removeItem(`chat_history_${currentCaseId}`);
    } catch (err) {
      alert(t('error.generic'));
    }
  };

  const handleAnalyze = async () => {
    if (!caseId) return;
    setIsAnalyzing(true);
    setActiveModal('none');
    try {
      let result: CaseAnalysisResult;
      if (selectedDocumentIds.length === 0) {
        result = await apiService.analyzeCase(caseId);
      } else {
        result = await apiService.crossExamineDocument(caseId, selectedDocumentIds[0]);
      }
      if (result.error) alert(result.error);
      else {
        setAnalysisResult(result);
        setActiveModal('analysis');
      }
    } catch (err) {
      alert(t('error.generic'));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleChatSubmit = async (
    text: string,
    _mode: ChatMode,
    reasoning: ReasoningMode,
    _domain: LegalDomain,
    documentIds?: string[],
    jurisdiction?: Jurisdiction
  ) => {
    if (!caseId) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, userMessage]);
    setIsSendingMessage(true);

    const aiMessage: ChatMessage = {
      role: 'ai',
      content: '',
      timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, aiMessage]);

    try {
      let fullResponse = '';
      const stream = apiService.sendChatMessageStream(
        caseId,
        text,
        documentIds,
        jurisdiction,
        reasoning,
        _domain
      );
      for await (const chunk of stream) {
        fullResponse += chunk;
        setChatMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = {
            ...newMessages[newMessages.length - 1],
            content: fullResponse,
          };
          return newMessages;
        });
      }
    } catch (error) {
      console.error('Chat stream error:', error);
      setChatMessages(prev => [
        ...prev,
        {
          role: 'ai',
          content: '[Gabim Teknik: Lidhja me shërbimin dështoi.]',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleExportChat = () => {
    const content = chatMessages.map(m => `${m.role === 'user' ? 'Përdoruesi' : 'AI'}: ${m.content}`).join('\n\n---\n\n');
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-${caseId}-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleViewOriginal = (doc: Document) => { const url = `${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`; setViewingUrl(url); setViewingDocument(doc); setMinimizedDocument(null); };
  const handleCloseViewer = () => { setViewingDocument(null); setViewingUrl(null); };
  const handleMinimizeViewer = () => { if (viewingDocument) { setMinimizedDocument(viewingDocument); handleCloseViewer(); } };
  const handleExpandViewer = () => { if (minimizedDocument) { handleViewOriginal(minimizedDocument); } };
  const handleRename = async (newName: string) => { if (!caseId || !documentToRename) return; try { await apiService.renameDocument(caseId, documentToRename.id, newName); setLiveDocuments(prev => prev.map(d => d.id === documentToRename.id ? { ...d, file_name: newName } : d)); } catch (error) { alert(t('error.generic')); } };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-danger-start border border-danger-start/30 rounded-md bg-danger-start/10 mt-10 mx-4"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p>{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen pb-10" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 pt-24 pb-6">
        <div>
            <CaseHeader 
                caseDetails={caseData.details} 
                documents={liveDocuments}
                t={t} 
                onAnalyze={handleAnalyze} 
                isAnalyzing={isAnalyzing} 
                viewMode={viewMode}
                setViewMode={setViewMode}
                isPro={isPro}
                selectedDocumentIds={selectedDocumentIds}
                onDocumentSelectionChange={setSelectedDocumentIds}
            />
        </div>
        <AnimatePresence mode="wait">
            {viewMode === 'workspace' && (
                <motion.div key="workspace" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }} className="flex flex-col lg:flex-row gap-6 mt-6 min-h-[500px]">
                    <div className="flex-1 min-w-0">
                        <DocumentsPanel 
                            caseId={caseData.details.id} 
                            documents={liveDocuments} 
                            t={t} 
                            connectionStatus={connectionStatus} 
                            reconnect={reconnect} 
                            onDocumentUploaded={handleDocumentUploaded} 
                            onDocumentDeleted={handleDocumentDeleted} 
                            onViewOriginal={handleViewOriginal} 
                            onRename={(doc) => setDocumentToRename(doc)} 
                            className="h-full w-full shadow-xl hover-lift" 
                        />
                    </div>
                    <div className="flex-1 min-w-0 mt-6 lg:mt-0">
                        <ChatPanel 
                            messages={chatMessages}
                            connectionStatus={connectionStatus}
                            reconnect={reconnect}
                            onSendMessage={handleChatSubmit}
                            isSendingMessage={isSendingMessage}
                            onClearChat={handleClearChat}
                            onExportChat={handleExportChat}
                            t={t}
                            className="h-full w-full shadow-xl hover-lift"
                            activeContextId={caseId || 'general'}
                            isPro={isPro}
                            selectedDocumentCount={selectedDocumentIds.length}
                        />
                    </div>
                </motion.div>
            )}
            {viewMode === 'analyst' && isPro && (
                <motion.div key="analyst" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} transition={{ duration: 0.2 }} className="mt-6">
                    <SpreadsheetAnalyst caseId={caseData.details.id} />
                </motion.div>
            )}
        </AnimatePresence>
      </div>
      {viewingDocument && (<PDFViewerModal documentData={viewingDocument} caseId={caseData.details.id} onClose={handleCloseViewer} onMinimize={handleMinimizeViewer} t={t} directUrl={viewingUrl} isAuth={true} />)}
      {minimizedDocument && <DockedPDFViewer document={minimizedDocument} onExpand={handleExpandViewer} onClose={() => setMinimizedDocument(null)} />}
      {analysisResult && (<AnalysisModal isOpen={activeModal === 'analysis'} onClose={() => setActiveModal('none')} result={analysisResult} caseId={currentCaseId} />)}
      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRename} currentName={documentToRename?.file_name || ''} t={t} />
    </motion.div>
  );
};

export default CaseViewPage;