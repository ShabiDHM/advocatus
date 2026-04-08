// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V16.14 (PERFECT 2-COLUMN LAYOUT ALIGNMENT)

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
import { AlertCircle, ShieldCheck, Loader2, X, Save, Calendar, Activity, Lock } from 'lucide-react';
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
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[200] p-4">
            <div className="bg-card w-full max-w-md p-8 rounded-2xl shadow-xl border border-border-main animate-in zoom-in-95">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold text-text-primary uppercase tracking-wider">{t('documentsPanel.renameTitle')}</h3>
                    <button onClick={onClose} className="p-2 hover:bg-surface rounded-xl transition-colors"><X size={20} /></button>
                </div>
                <form onSubmit={handleSubmit}>
                    <input autoFocus value={name} onChange={(e) => setName(e.target.value)} className="glass-input w-full mb-6 py-3 text-base" />
                    <div className="flex justify-end gap-3">
                        <button type="button" onClick={onClose} className="px-5 py-2 text-sm font-medium text-text-muted hover:text-text-primary transition-colors">{t('general.cancel')}</button>
                        <button type="submit" disabled={isSaving} className="btn-primary flex items-center gap-2">
                            {isSaving ? <Loader2 className="animate-spin h-4 w-4" /> : <Save size={16} />} {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// ========== REFACTORED HEADER: 2-COLUMN LAYOUT FOR PERFECT ALIGNMENT ==========
// The header now uses a 2-column grid (left and right) with nested grids for buttons,
// ensuring each column's buttons span the full width of the panel below.
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
        ? t('caseView.analyzeCase')
        : t('analysis.crossExamineButton', 'Kryqëzo Dokumentin');

    const buttonBase = "h-12 flex items-center justify-center gap-3 px-4 rounded-xl glass-panel bg-canvas/40 border border-border-main shadow-sm transition-all duration-300 hover-lift text-xs font-black uppercase tracking-widest w-full text-text-primary";

    return (
        <motion.div className="relative mb-6 z-[30]" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            {/* 2-column grid that matches the width of the panels below */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
                
                {/* LEFT COLUMN */}
                <div className="flex flex-col gap-4">
                    {/* Top row: two buttons in a sub-grid */}
                    <div className="grid grid-cols-2 gap-3">
                        {/* Button 1: Date */}
                        <div className={buttonBase}>
                            <Calendar size={16} className="text-primary opacity-70 shrink-0" />
                            <span className="truncate">{new Date(caseDetails.created_at).toLocaleDateString()}</span>
                        </div>
                        {/* Button 2: Document Selector (E GJITHË DOSJA) */}
                        <div className="relative z-[60]">
                            <DocumentSelector
                                documents={documents.map(d => ({ id: d.id, file_name: d.file_name }))}
                                selectedIds={selectedDocumentIds}
                                onChange={onDocumentSelectionChange}
                                disabled={!isPro}
                            />
                        </div>
                    </div>
                    {/* Bottom: DocumentsPanel */}
                    <div className="flex-1">
                        {/* The DocumentsPanel will be rendered here in the main layout, 
                            but we keep the header as just the top buttons. 
                            The actual panel is placed below in the main component. */}
                    </div>
                </div>

                {/* RIGHT COLUMN */}
                <div className="flex flex-col gap-4">
                    {/* Top row: two buttons in a sub-grid */}
                    <div className="grid grid-cols-2 gap-3">
                        {/* Button 3: Financial Analyst toggle */}
                        <button
                            onClick={() => isPro && setViewMode(viewMode === 'workspace' ? 'analyst' : 'workspace')}
                            disabled={!isPro}
                            className={`${buttonBase} ${
                                viewMode === 'analyst' 
                                ? 'border-primary bg-primary/10 text-primary shadow-accent-glow' 
                                : 'hover:border-primary/50 text-text-primary'
                            } ${!isPro && 'opacity-40 cursor-not-allowed'}`}
                        >
                            {!isPro ? <Lock size={16} className="shrink-0" /> : <Activity size={16} className={viewMode === 'analyst' ? 'text-primary shrink-0' : 'text-primary opacity-70 shrink-0'} />}
                            <span className="truncate">{t('caseView.financialAnalyst')}</span>
                        </button>
                        {/* Button 4: Analyze button */}
                        <button
                            onClick={onAnalyze}
                            disabled={!isPro || isAnalyzing}
                            className={`${buttonBase} hover:border-primary/50 active:scale-95 disabled:opacity-40`}
                        >
                            {isAnalyzing ? (
                                <span className="flex items-center gap-2 min-w-0">
                                    <span className="flex items-center justify-center animate-spin shrink-0">
                                        <Loader2 className="h-4 w-4 text-primary" />
                                    </span>
                                    <span className="text-primary truncate">{t('analysis.analyzing')}</span>
                                </span>
                            ) : (
                                <span className="flex items-center gap-2 min-w-0">
                                    <ShieldCheck size={16} className="text-primary shrink-0" />
                                    <span className="text-primary truncate">{analyzeButtonText}</span>
                                </span>
                            )}
                        </button>
                    </div>
                    {/* Bottom: ChatPanel */}
                    <div className="flex-1">
                        {/* The ChatPanel will be rendered here in the main layout */}
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

// ========== MAIN COMPONENT ==========
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

  // --- CHAT PERSISTENCE HELPER (localStorage + backend) ---
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
      
      // Load chat: try backend first, fallback to localStorage
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

  const handleAnalyze = async () => {
    if (!caseId) return;
    setIsAnalyzing(true);
    setActiveModal('none');
    try {
      let result = selectedDocumentIds.length === 0 ? await apiService.analyzeCase(caseId) : await apiService.crossExamineDocument(caseId, selectedDocumentIds[0]);
      if (result.error) alert(result.error);
      else { setAnalysisResult(result); setActiveModal('analysis'); }
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

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-screen bg-canvas"><div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-danger border border-danger/30 rounded-2xl bg-danger/5 mt-20 max-w-lg mx-auto"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p className="font-bold uppercase tracking-wide">{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen pb-12" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-20 sm:pt-24 pb-8">
        {/* Header with 2-column button layout */}
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
        
        {/* Main content area: 2-column grid matching the header exactly */}
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
              {/* LEFT COLUMN: DocumentsPanel */}
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
                  className="h-full w-full shadow-sm hover-lift" 
                />
              </div>
              
              {/* RIGHT COLUMN: ChatPanel */}
              <div className="flex flex-col h-auto lg:h-[700px] mt-6 lg:mt-0">
                <ChatPanel 
                  messages={chatMessages} 
                  connectionStatus={connectionStatus} 
                  reconnect={reconnect} 
                  onSendMessage={handleChatSubmit} 
                  isSendingMessage={isSendingMessage} 
                  onClearChat={handleClearChat} 
                  t={t} 
                  className="h-full w-full shadow-sm hover-lift" 
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
              className="z-0"
            >
              <SpreadsheetAnalyst caseId={caseData.details.id} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      {/* Modals and viewers (unchanged) */}
      {viewingDocument && (<PDFViewerModal documentData={viewingDocument} caseId={caseData.details.id} onClose={() => {setViewingDocument(null); setViewingUrl(null);}} onMinimize={() => {if(viewingDocument){setMinimizedDocument(viewingDocument); setViewingDocument(null);}}} t={t} directUrl={viewingUrl} isAuth={true} />)}
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