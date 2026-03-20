// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V14.1 (SYNTAX & LOGIC TOTAL FIX)
// 1. FIXED: All JSX parsing errors and mismatched tags.
// 2. FIXED: Implemented 'caseView.financialAnalyst' and 'caseView.analyzeCase' keys.
// 3. FIXED: Action Bar is PERMANENT. Grid never shifts or collapses between views.
// 4. RETAINED: 100% logic (Streaming, Sockets, Modals, Rename, Deletion).

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
        return { role, content: item.content || item.message || '', timestamp: item.timestamp || new Date().toISOString() };
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-md flex items-center justify-center z-[200] p-4">
            <div className="bg-surface w-full max-w-md p-8 rounded-[2rem] shadow-lawyer-dark border border-border-main animate-in zoom-in-95">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-sm font-black text-text-primary uppercase tracking-widest">{t('documentsPanel.renameTitle')}</h3>
                    <button onClick={onClose} className="p-2 hover:bg-surface-secondary rounded-xl transition-colors"><X size={20} /></button>
                </div>
                <form onSubmit={handleSubmit}>
                    <input autoFocus value={name} onChange={(e) => setName(e.target.value)} className="glass-input w-full mb-6 py-4 font-bold" />
                    <div className="flex justify-end gap-3">
                        <button type="button" onClick={onClose} className="px-5 py-2 text-sm font-bold text-text-muted">{t('general.cancel')}</button>
                        <button type="submit" disabled={isSaving} className="btn-primary flex items-center gap-2">
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

    const cardBase = "h-12 flex items-center justify-center gap-3 px-6 rounded-xl bg-surface border border-border-main shadow-lawyer-light transition-all duration-300 hover-lift text-[11px] font-black uppercase tracking-widest";

    return (
        <motion.div className="mb-8" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          {/* Header Title Section */}
          <div className="flex flex-col gap-2 mb-8 ml-2">
              <h1 className="text-4xl font-black text-text-primary tracking-tighter leading-none">
                {caseDetails.case_name || caseDetails.title || t('caseView.unnamedCase')}
              </h1>
              <div className="flex items-center gap-2 opacity-60">
                <User size={14} className="text-primary-start" />
                <span className="text-xs font-bold uppercase tracking-widest text-text-secondary">{caseDetails.client?.name || "Private Client"}</span>
              </div>
          </div>

          {/* PERMANENT ACTION BAR - Grid logic is fixed */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 items-center">
              
              {/* Card 1: Date */}
              <div className={cardBase}>
                  <Calendar size={16} className="text-primary-start opacity-70" />
                  <span className="text-text-secondary">{new Date(caseDetails.created_at).toLocaleDateString()}</span>
              </div>

              {/* Card 2: Document Selector */}
              <div className="h-12 relative group hover-lift">
                  <DocumentSelector
                      documents={documents.map(d => ({ id: d.id, file_name: d.file_name }))}
                      selectedIds={selectedDocumentIds}
                      onChange={onDocumentSelectionChange}
                      disabled={!isPro}
                  />
              </div>
              
              {/* Card 3: Analyst Toggle */}
              <button
                  onClick={() => isPro && setViewMode(viewMode === 'workspace' ? 'analyst' : 'workspace')}
                  disabled={!isPro}
                  className={`${cardBase} ${viewMode === 'analyst' ? 'border-primary-start bg-primary-start/5 text-primary-start' : 'text-text-secondary'} ${!isPro ? 'opacity-40 cursor-not-allowed' : ''}`}
              >
                  {!isPro ? <Lock size={16} /> : <Activity size={16} className={viewMode === 'analyst' ? 'text-primary-start' : 'text-primary-start opacity-70'} />}
                  <span>{t('caseView.financialAnalyst')}</span>
              </button>

              {/* Card 4: Analyze Button */}
              <button
                  onClick={onAnalyze}
                  disabled={!isPro || isAnalyzing}
                  className={`${cardBase} group border-primary-start/30 active:scale-95 disabled:opacity-40`}
              >
                  {isAnalyzing ? (
                      <span className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin text-primary-start" />
                        <span className="text-primary-start">{t('analysis.analyzing')}</span>
                      </span>
                  ) : (
                      <span className="flex items-center gap-2">
                        <ShieldCheck size={18} className="text-primary-start" />
                        <span className="text-primary-start">{analyzeButtonText}</span>
                      </span>
                  )}
              </button>
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
      setChatMessages(extractAndNormalizeHistory(details));
    } catch {
      setError(t('error.failedToLoadCase'));
    } finally {
      if(isInitialLoad) setIsLoading(false);
    }
  }, [caseId, t, setLiveDocuments]);

  useEffect(() => { if (isReadyForData) fetchCaseData(true); }, [isReadyForData, fetchCaseData]);

  const handleDocumentUploaded = (newDoc: Document) => { setLiveDocuments(p => [sanitizeDocument(newDoc), ...p]); };
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => { setLiveDocuments(p => p.filter(d => String(d.id) !== String(response.documentId))); };
  
  const handleClearChat = async () => {
    if (!caseId) return;
    try { await apiService.clearChatHistory(caseId); setChatMessages([]); } catch { alert(t('error.generic')); }
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
    setChatMessages(p => [...p, { role: 'user', content: text, timestamp: new Date().toISOString() }, { role: 'ai', content: '', timestamp: new Date().toISOString() }]);
    setIsSendingMessage(true);
    try {
      let acc = '';
      const stream = apiService.sendChatMessageStream(caseId, text, documentIds, jurisdiction, reasoning, mode === 'document' ? domain : undefined);
      for await (const chunk of stream) {
        acc += chunk;
        setChatMessages(p => {
          const next = [...p];
          next[next.length - 1] = { ...next[next.length - 1], content: acc };
          return next;
        });
      }
    } catch { setChatMessages(p => [...p, { role: 'ai', content: '[Gabim Teknik]', timestamp: new Date().toISOString() }]);
    } finally { setIsSendingMessage(false); }
  };

  const handleViewOriginal = (doc: Document) => { setViewingUrl(`${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`); setViewingDocument(doc); setMinimizedDocument(null); };
  const handleRenameAction = async (newName: string) => { if (!caseId || !documentToRename) return; try { await apiService.renameDocument(caseId, documentToRename.id, newName); setLiveDocuments(p => p.map(d => d.id === documentToRename.id ? { ...d, file_name: newName } : d)); } catch { alert(t('error.generic')); } };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-screen bg-canvas"><Loader2 className="animate-spin h-12 w-12 text-primary-start" /></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-danger-start border border-danger-start/30 rounded-[2rem] bg-danger-start/5 mt-20 max-w-lg mx-auto"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p className="font-black uppercase tracking-widest">{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen pb-12" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-6 sm:px-8 pt-24 pb-8">
        <CaseHeader 
            caseDetails={caseData.details} documents={liveDocuments} t={t} 
            onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} viewMode={viewMode} setViewMode={setViewMode} isPro={isPro} selectedDocumentIds={selectedDocumentIds} onDocumentSelectionChange={setSelectedDocumentIds}
        />
        
        <AnimatePresence mode="wait">
            {viewMode === 'workspace' && (
                <motion.div key="workspace" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }} className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-auto lg:h-[700px]">
                    <DocumentsPanel 
                        caseId={caseData.details.id} documents={liveDocuments} t={t} connectionStatus={connectionStatus} reconnect={reconnect} 
                        onDocumentUploaded={handleDocumentUploaded} onDocumentDeleted={handleDocumentDeleted} onViewOriginal={handleViewOriginal} onRename={setDocumentToRename} 
                        className="h-full w-full shadow-lawyer-light hover-lift" 
                    />
                    <ChatPanel 
                        messages={chatMessages} connectionStatus={connectionStatus} reconnect={reconnect} onSendMessage={handleChatSubmit} isSendingMessage={isSendingMessage} onClearChat={handleClearChat} 
                        t={t} className="h-full w-full shadow-lawyer-light hover-lift" activeContextId={currentCaseId} isPro={isPro} selectedDocumentCount={selectedDocumentIds.length}
                    />
                </motion.div>
            )}
            {viewMode === 'analyst' && isPro && (
                <motion.div key="analyst" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2 }}>
                    <SpreadsheetAnalyst caseId={caseData.details.id} />
                </motion.div>
            )}
        </AnimatePresence>
      </div>
      {viewingDocument && (<PDFViewerModal documentData={viewingDocument} caseId={caseData.details.id} onClose={() => {setViewingDocument(null); setViewingUrl(null);}} onMinimize={() => {if(viewingDocument){setMinimizedDocument(viewingDocument); setViewingDocument(null);}}} t={t} directUrl={viewingUrl} isAuth={true} />)}
      {minimizedDocument && <DockedPDFViewer document={minimizedDocument} onExpand={() => handleViewOriginal(minimizedDocument)} onClose={() => setMinimizedDocument(null)} />}
      {analysisResult && (<AnalysisModal isOpen={activeModal === 'analysis'} onClose={() => setActiveModal('none')} result={analysisResult} caseId={currentCaseId} />)}
      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRenameAction} currentName={documentToRename?.file_name || ''} t={t} />
    </motion.div>
  );
};

export default CaseViewPage;