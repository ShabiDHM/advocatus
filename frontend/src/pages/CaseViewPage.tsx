// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V11.1 (EXECUTIVE ACTION BAR)
// 1. UNIFIED: Date, Document Selector, Analyst Toggle, Analyze button now share exact same height and base styling.
// 2. ADDED: hover-lift to all interactive items for premium feedback.
// 3. ACTIVE STATE: Analyst toggle uses primary-start border and subtle background when active.
// 4. RETAINED: All features (document selection, analysis, chat, export).

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
    isAdmin: boolean;
    selectedDocumentIds: string[];
    onDocumentSelectionChange: (ids: string[]) => void;
}> = ({ caseDetails, documents, t, onAnalyze, isAnalyzing, viewMode, setViewMode, isPro, isAdmin, selectedDocumentIds, onDocumentSelectionChange }) => {
    
    const analyzeButtonText = selectedDocumentIds.length === 0
        ? t('analysis.analyzeButton', 'Analizo Rastin')
        : t('analysis.crossExamineButton', 'Kryqëzo Dokumentin');

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

              {/* Executive Action Bar - All items same height, rounded-xl, and hover-lift where interactive */}
              <div className={`grid grid-cols-1 gap-3 w-full animate-in fade-in slide-in-from-top-2 ${isAdmin ? 'md:grid-cols-4' : 'md:grid-cols-4'}`}>
                    {/* Date badge (static, no hover) */}
                    <div className="md:col-span-1 h-12 md:h-11 rounded-xl flex items-center justify-center gap-2 px-4 bg-surface/10 border border-main text-text-secondary text-sm font-medium whitespace-nowrap">
                        <Calendar className="h-4 w-4 text-blue-400" />
                        {new Date(caseDetails.created_at).toLocaleDateString()}
                    </div>
                    
                    {/* Document selector (interactive) */}
                    {viewMode === 'workspace' && (
                        <div className="md:col-span-1 h-12 md:h-11 min-w-0">
                            <DocumentSelector
                                documents={documents.map(d => ({ id: d.id, file_name: d.file_name }))}
                                selectedIds={selectedDocumentIds}
                                onChange={onDocumentSelectionChange}
                                disabled={!isPro}
                            />
                        </div>
                    )}
                    
                    {/* Analyst toggle (interactive) */}
                    <button
                        onClick={() => isPro && setViewMode(viewMode === 'workspace' ? 'analyst' : 'workspace')}
                        disabled={!isPro}
                        className={`md:col-span-1 h-12 md:h-11 rounded-xl flex items-center justify-center gap-2.5 text-sm font-bold transition-all duration-300 whitespace-nowrap border hover-lift ${!isPro ? 'bg-surface/10 border border-main text-text-secondary cursor-not-allowed opacity-70' : viewMode === 'analyst' ? 'bg-primary-start/10 border-primary-start text-primary-start' : 'bg-surface/10 border-main text-text-secondary hover:text-text-primary hover:bg-surface/20'}`}
                        title={!isPro ? "Available on Pro Plan" : ""}
                    >
                        {!isPro ? <Lock size={16} className="text-text-secondary" /> : <Activity size={16} className={viewMode === 'analyst' ? 'text-primary-start' : 'text-text-secondary'} />}
                        <span>{t('caseView.financialAnalyst', 'Analisti Financiar')}</span>
                    </button>

                    {/* Analyze button (primary action) */}
                    <button
                        onClick={onAnalyze}
                        disabled={!isPro || isAnalyzing || viewMode !== 'workspace'}
                        className="md:col-span-1 h-12 md:h-11 btn-primary disabled:opacity-50 disabled:cursor-not-allowed hover-lift"
                        type="button"
                        title={!isPro ? "Available on Pro Plan" : ""}
                    >
                        {isAnalyzing ? (
                            <><Loader2 className="h-4 w-4 animate-spin" /> <span>{t('analysis.analyzing', 'Duke analizuar...')}</span></>
                        ) : !isPro ? (
                            <><Lock size={16} /> <span>{analyzeButtonText}</span></>
                        ) : (
                            <><ShieldCheck size={16} /> <span>{analyzeButtonText}</span></>
                        )}
                    </button>
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

  const isAdmin = useMemo(() => {
      return user?.role === 'ADMIN';
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
                isAdmin={isAdmin}
                selectedDocumentIds={selectedDocumentIds}
                onDocumentSelectionChange={setSelectedDocumentIds}
            />
        </div>
        <AnimatePresence mode="wait">
            {viewMode === 'workspace' && (
                <motion.div key="workspace" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }} className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[600px] relative z-0">
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
                        className="h-[500px] lg:h-full shadow-xl hover-lift" 
                    />
                    <ChatPanel 
                        messages={chatMessages}
                        connectionStatus={connectionStatus}
                        reconnect={reconnect}
                        onSendMessage={handleChatSubmit}
                        isSendingMessage={isSendingMessage}
                        onClearChat={handleClearChat}
                        onExportChat={handleExportChat}
                        t={t}
                        className="!h-[600px] lg!h-full w-full shadow-xl hover-lift"
                        activeContextId={caseId || 'general'}
                        isPro={isPro}
                        selectedDocumentCount={selectedDocumentIds.length}
                    />
                </motion.div>
            )}
            {viewMode === 'analyst' && isPro && (
                <motion.div key="analyst" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} transition={{ duration: 0.2 }}>
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