// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V16.19 (ANALYSIS RETENTION & LIVE CACHING)
// 1. FIX: Loads pre-existing latest_analysis directly from database into local state on boot for instant viewing (0 seconds delay).
// 2. FIX: Replaced standard analyze button with "Shiko Analizën" (View) when analysis exists, adding a small "Rianalizo" (Re-analyze) button next to it.
// 3. FIX: Bound the onClick handlers of both buttons to correct 'onAnalyze' props inside CaseHeader child component.

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
import { AlertCircle, ShieldCheck, Loader2, X, Save, Calendar, Activity, Lock, RefreshCw, Eye } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';
import DockedPDFViewer from '../components/DockedPDFViewer';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

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
    
    useLockBodyScroll(isOpen);

    useEffect(() => { setName(currentName); }, [currentName]);
    
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault(); 
        if (!name.trim()) return; 
        setIsSaving(true);
        try { 
            await onRename(name); 
            onClose(); 
        } finally { 
            setIsSaving(false); 
        }
    };
    
    if (!isOpen) return null;
    
    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[200] p-4">
            <div className="bg-canvas w-full max-w-md p-6 sm:p-8 rounded-2xl shadow-2xl border border-main animate-in zoom-in-95">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold text-text-primary uppercase tracking-wider">{t('documentsPanel.renameTitle')}</h3>
                    <button 
                        onClick={onClose} 
                        className="flex items-center justify-center w-11 h-11 rounded-xl text-text-muted hover:text-text-primary hover:bg-hover transition-colors focus:outline-none"
                        aria-label="Close"
                    >
                        <X size={20} />
                    </button>
                </div>
                <form onSubmit={handleSubmit} className="space-y-5">
                    <input 
                        autoFocus 
                        value={name} 
                        onChange={(e) => setName(e.target.value)} 
                        className="w-full h-11 px-4 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                    />
                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
                        <button 
                            type="button" 
                            onClick={onClose} 
                            className="w-full sm:w-auto px-5 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-colors focus:outline-none"
                        >
                            {t('general.cancel')}
                        </button>
                        <button 
                            type="submit" 
                            disabled={isSaving} 
                            className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-bold bg-primary-start hover:bg-opacity-90 text-white flex items-center justify-center gap-2 focus:outline-none shadow-lg shadow-primary-start/15"
                        >
                            {isSaving ? <Loader2 className="animate-spin h-4 w-4" /> : <Save size={16} />} {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

const CaseHeader: React.FC<{
    caseDetails: Case;
    documents: Document[];
    t: TFunction;
    onAnalyze: (force?: boolean) => void;
    isAnalyzing: boolean;
    viewMode: ViewMode;
    setViewMode: (mode: ViewMode) => void;
    isPro: boolean;
    selectedDocumentIds: string[];
    onDocumentSelectionChange: (ids: string[]) => void;
}> = ({ caseDetails, documents, t, onAnalyze, isAnalyzing, viewMode, setViewMode, isPro, selectedDocumentIds, onDocumentSelectionChange }) => {
    
    // Check if an analysis already exists in database
    const hasExistingAnalysis = !!(caseDetails as any).latest_analysis && selectedDocumentIds.length === 0;

    const analyzeButtonText = isAnalyzing
        ? (
            <span className="flex items-center gap-2 min-w-0">
                <span className="flex items-center justify-center animate-spin shrink-0">
                    <Loader2 className="h-4 w-4 text-primary-start" />
                </span>
                <span className="text-primary-start truncate">{t('analysis.analyzing')}</span>
            </span>
          )
        : hasExistingAnalysis
        ? (
            <span className="flex items-center gap-2 min-w-0">
                <Eye size={15} className="text-primary-start shrink-0" />
                <span className="text-primary-start truncate">Shiko Analizën</span>
            </span>
          )
        : selectedDocumentIds.length === 0
        ? (
            <span className="flex items-center gap-2 min-w-0">
                <ShieldCheck size={15} className="text-primary-start shrink-0" />
                <span className="text-primary-start truncate">{t('caseView.analyzeCase')}</span>
            </span>
          )
        : (
            <span className="flex items-center gap-2 min-w-0">
                <ShieldCheck size={15} className="text-primary-start shrink-0" />
                <span className="text-primary-start truncate">{t('analysis.crossExamineButton', 'Kryqëzo Dokumentin')}</span>
            </span>
          );

    const buttonBase = "h-11 flex items-center justify-center gap-2.5 px-4 rounded-xl glass-panel bg-surface border border-main shadow-sm transition-all duration-250 hover:bg-hover hover:border-main/80 text-xs font-bold uppercase tracking-wider w-full text-text-primary focus:outline-none";

    return (
        <motion.div className="relative mb-6 z-[30]" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
                
                {/* LEFT COLUMN */}
                <div className="flex flex-col gap-4">
                    <div className="grid grid-cols-2 gap-3">
                        <div className={buttonBase}>
                            <Calendar size={15} className="text-primary-start opacity-70 shrink-0" />
                            <span className="truncate select-none">{new Date(caseDetails.created_at).toLocaleDateString()}</span>
                        </div>
                        <div className="relative z-[60]">
                            <DocumentSelector
                                documents={documents.map(d => ({ id: d.id, file_name: d.file_name }))}
                                selectedIds={selectedDocumentIds}
                                onChange={onDocumentSelectionChange}
                                disabled={!isPro}
                            />
                        </div>
                    </div>
                </div>

                {/* RIGHT COLUMN */}
                <div className="flex flex-col gap-4">
                    <div className="grid grid-cols-2 gap-3">
                        <button
                            type="button"
                            onClick={() => isPro && setViewMode(viewMode === 'workspace' ? 'analyst' : 'workspace')}
                            disabled={!isPro}
                            className={`${buttonBase} ${
                                viewMode === 'analyst' 
                                ? 'border-primary-start bg-primary-start/10 text-primary-start shadow-accent-glow' 
                                : 'text-text-primary'
                            } ${!isPro && 'opacity-40 cursor-not-allowed'}`}
                        >
                            {!isPro ? <Lock size={15} className="shrink-0 text-text-muted" /> : <Activity size={15} className={viewMode === 'analyst' ? 'text-primary-start shrink-0' : 'text-primary-start opacity-70 shrink-0'} />}
                            <span className="truncate hidden sm:inline">{t('caseView.financialAnalyst')}</span>
                            <span className="truncate sm:hidden">Financat</span>
                        </button>
                        
                        {/* Persistent Analysis Button Wrapper */}
                        <div className="flex items-center gap-2 w-full">
                            <button
                                type="button"
                                onClick={() => onAnalyze()} // FIX: Correctly invokes bound prop 'onAnalyze' instead of undefined handleAnalyze
                                disabled={!isPro || isAnalyzing}
                                className={`${buttonBase} disabled:opacity-40`}
                            >
                                {analyzeButtonText}
                            </button>
                            
                            {/* Rianalizo (Re-analyze) explicit trigger button shown only if analysis already exists */}
                            {hasExistingAnalysis && (
                                <button
                                    type="button"
                                    onClick={() => onAnalyze(true)}
                                    disabled={!isPro || isAnalyzing}
                                    className="h-11 w-11 shrink-0 flex items-center justify-center rounded-xl glass-panel bg-surface border border-main hover:bg-hover hover:border-main/80 text-text-muted hover:text-primary-start transition-all duration-250 focus:outline-none"
                                    title="Rianalizo sërish me AI"
                                >
                                    <RefreshCw size={15} className={isAnalyzing ? "animate-spin" : ""} />
                                </button>
                            )}
                        </div>
                    </div>
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
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

  const isPro = useMemo(() => user?.subscription_tier === 'PRO' || user?.role === 'ADMIN', [user]);
  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, connectionStatus, reconnect } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  const saveToLocalStorage = useCallback((messages: ChatMessage[]) => {
    if (!caseId) return;
    localStorage.setItem(`chat_${caseId}`, JSON.stringify(messages));
  }, [caseId]);

  const loadFromLocalStorage = useCallback((): ChatMessage[] | null => {
    if (!caseId) return null;
    const stored = localStorage.getItem(`chat_${caseId}`);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch { return null; }
    }
    return null;
  }, [caseId]);

  const persistChatHistory = useCallback(async (messages: ChatMessage[]) => {
    saveToLocalStorage(messages);
    if (!caseId) return;
    try {
      await apiService.updateChatHistory(caseId, messages);
      console.log("Chat history saved to backend");
    } catch (err) {
      console.error('Failed to persist chat history to backend:', err);
    }
  }, [caseId, saveToLocalStorage]);

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
      
      // Load pre-existing persistent AI analysis results if present
      if (details && (details as any).latest_analysis) {
        setAnalysisResult((details as any).latest_analysis);
      }
      
      const backendMessages = extractAndNormalizeHistory(details);
      if (backendMessages.length > 0) {
        setChatMessages(backendMessages);
        saveToLocalStorage(backendMessages);
      } else {
        const localMessages = loadFromLocalStorage();
        if (localMessages && localMessages.length > 0) {
          setChatMessages(localMessages);
          persistChatHistory(localMessages);
        } else {
          setChatMessages([]);
        }
      }
    } catch {
      setError(t('error.failedToLoadCase'));
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments, loadFromLocalStorage, saveToLocalStorage, persistChatHistory]);

  useEffect(() => { if (isReadyForData) fetchCaseData(true); }, [isReadyForData, fetchCaseData]);

  const handleDocumentUploaded = (newDoc: Document) => { setLiveDocuments(p => [sanitizeDocument(newDoc), ...p]); };
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => { setLiveDocuments(p => p.filter(d => String(d.id) !== String(response.documentId))); };
  
  const handleClearChat = async () => {
    if (!caseId) return;
    try { 
      await apiService.clearChatHistory(caseId); 
      setChatMessages([]);
      await persistChatHistory([]);
      localStorage.removeItem(`chat_${caseId}`);
    } catch { alert(t('error.generic')); }
  };

  const handleAnalyze = async (force = false) => {
    if (!caseId) return;
    
    // Open immediately with 0 seconds delay if saved analysis exists (and not force re-analyzing or cross-examining)
    if (caseData.details && (caseData.details as any).latest_analysis && !force && selectedDocumentIds.length === 0) {
        setAnalysisResult((caseData.details as any).latest_analysis);
        setActiveModal('analysis');
        return;
    }
    
    setIsAnalyzing(true);
    setActiveModal('none');
    try {
      let result = selectedDocumentIds.length === 0 ? await apiService.analyzeCase(caseId) : await apiService.crossExamineDocument(caseId, selectedDocumentIds[0]);
      if (result.error) alert(result.error);
      else { 
        setAnalysisResult(result); 
        setActiveModal('analysis'); 
        // Instantly cache in the local UI state so it stays loaded
        setCaseData(prev => prev.details ? { details: { ...prev.details, latest_analysis: result } } : prev);
      }
    } catch { alert(t('error.generic')); } finally { setIsAnalyzing(false); }
  };

  const handleChatSubmit = async (text: string, mode: ChatMode, reasoning: ReasoningMode, domain: LegalDomain, documentIds?: string[], jurisdiction?: Jurisdiction) => {
    if (!caseId) return;
    const userMessage: ChatMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
    const assistantPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    setChatMessages(prev => [...prev, userMessage, assistantPlaceholder]);
    setIsSendingMessage(true);
    try {
      let acc = '';
      const stream = apiService.sendChatMessageStream(caseId, text, documentIds, jurisdiction, reasoning, mode === 'document' ? domain : undefined);
      for await (const chunk of stream) {
        acc += chunk;
        setChatMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { ...updated[updated.length - 1], content: acc };
          return updated;
        });
      }
      setChatMessages(prev => {
        const finalMessages = [...prev];
        persistChatHistory(finalMessages);
        return finalMessages;
      });
    } catch {
      const errorMsg = '[Gabim Teknik]';
      setChatMessages(prev => {
        const withError = [...prev];
        withError[withError.length - 1] = { ...withError[withError.length - 1], content: errorMsg };
        persistChatHistory(withError);
        return withError;
      });
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleViewOriginal = (doc: Document) => { setViewingUrl(`${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`); setViewingDocument(doc); setMinimizedDocument(null); };
  const handleRenameAction = async (newName: string) => { if (!caseId || !documentToRename) return; try { await apiService.renameDocument(caseId, documentToRename.id, newName); setLiveDocuments(p => p.map(d => d.id === documentToRename.id ? { ...d, file_name: newName } : d)); } catch { alert(t('error.generic')); } };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-screen bg-canvas"><div className="w-16 h-16 border-4 border-primary-start border-t-transparent rounded-full animate-spin"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-danger border border-danger/30 rounded-2xl bg-danger/5 mt-20 max-w-lg mx-auto animate-pulse"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p className="font-bold uppercase tracking-wide">{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen pb-12 bg-canvas" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24 pb-8">
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
        
        <AnimatePresence mode="wait">
          {viewMode === 'workspace' && (
            <motion.div 
              key="workspace" 
              initial={{ opacity: 0, y: 10 }} 
              animate={{ opacity: 1, y: 0 }} 
              exit={{ opacity: 0, y: -10 }} 
              transition={{ duration: 0.2 }} 
              className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8 z-0"
            >
              <div className="flex flex-col h-auto lg:h-[700px]">
                <DocumentsPanel 
                  caseId={caseData.details.id} 
                  documents={liveDocuments} 
                  t={t} 
                  connectionStatus={connectionStatus} 
                  reconnect={reconnect} 
                  onDocumentUploaded={handleDocumentUploaded} 
                  onDocumentDeleted={handleDocumentDeleted} 
                  onViewOriginal={handleViewOriginal} 
                  onRename={setDocumentToRename} 
                  className="h-full w-full shadow-sm hover-lift border border-main rounded-2xl overflow-hidden bg-canvas" 
                />
              </div>
              
              <div className="flex flex-col h-auto lg:h-[700px] mt-6 lg:mt-0">
                <ChatPanel 
                  messages={chatMessages} 
                  connectionStatus={connectionStatus} 
                  reconnect={reconnect} 
                  onSendMessage={handleChatSubmit} 
                  isSendingMessage={isSendingMessage} 
                  onClearChat={handleClearChat} 
                  t={t} 
                  className="h-full w-full shadow-sm hover-lift border border-main rounded-2xl overflow-hidden bg-canvas" 
                  activeContextId={currentCaseId} 
                  isPro={isPro} 
                  selectedDocumentCount={selectedDocumentIds.length}
                />
              </div>
            </motion.div>
          )}
          {viewMode === 'analyst' && isPro && (
            <motion.div 
              key="analyst" 
              initial={{ opacity: 0, y: 10 }} 
              animate={{ opacity: 1, y: 0 }} 
              exit={{ opacity: 0, y: -10 }} 
              transition={{ duration: 0.2 }} 
              className="z-0 border border-main rounded-2xl overflow-hidden bg-canvas"
            >
              <SpreadsheetAnalyst caseId={caseData.details.id} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      {viewingDocument && (
        <PDFViewerModal 
          documentData={viewingDocument} 
          caseId={caseData.details.id} 
          onClose={() => {setViewingDocument(null); setViewingUrl(null);}} 
          onMinimize={() => {if(viewingDocument){setMinimizedDocument(viewingDocument); setViewingDocument(null);}}} 
          t={t} 
          directUrl={viewingUrl} 
          isAuth={true} 
        />
      )}
      {minimizedDocument && <DockedPDFViewer document={minimizedDocument} onExpand={() => handleViewOriginal(minimizedDocument)} onClose={() => setMinimizedDocument(null)} />}
      {analysisResult && (
        <AnalysisModal 
          isOpen={activeModal === 'analysis'} 
          onClose={() => setActiveModal('none')} 
          result={analysisResult} 
          caseId={currentCaseId} 
          isLoading={isAnalyzing}
        />
      )}
      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRenameAction} currentName={documentToRename?.file_name || ''} t={t} />
    </motion.div>
  );
};

export default CaseViewPage;