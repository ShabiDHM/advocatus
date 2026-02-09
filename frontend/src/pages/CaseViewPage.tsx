// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V10.1 (I18N FIX)
// 1. FIX: Removed hardcoded "Analyzing......" string.
// 2. I18N: Button state now uses t('analysis.analyzing') for translation.
// 3. INTEGRITY: Retained all Modal, Analyst, and Workspace logic.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Case, Document, DeletedDocumentResponse, CaseAnalysisResult, ChatMessage } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel, { ChatMode, Jurisdiction, ReasoningMode } from '../components/ChatPanel';
import PDFViewerModal from '../components/FileViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import GlobalContextSwitcher from '../components/GlobalContextSwitcher';
import SpreadsheetAnalyst from '../components/SpreadsheetAnalyst';
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
            <div className="glass-high w-full max-w-md p-6 rounded-2xl animate-in fade-in zoom-in-95 duration-200">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold text-white">{t('documentsPanel.renameTitle')}</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors"><X size={24} /></button>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="mb-6"><label className="block text-sm text-gray-400 mb-2">{t('documentsPanel.newName')}</label><input autoFocus type="text" value={name} onChange={(e) => setName(e.target.value)} className="glass-input w-full rounded-xl px-4 py-3" /></div>
                    <div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white font-medium transition-colors">{t('general.cancel')}</button><button type="submit" disabled={isSaving} className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary-start/20 transition-all active:scale-95">{isSaving ? <Loader2 className="animate-spin h-4 w-4" /> : <Save size={16} />}{t('general.save')}</button></div>
                </form>
            </div>
        </div>
    );
};

const CaseHeader: React.FC<{ 
    caseDetails: Case;
    documents: Document[];
    activeContextId: string;
    onContextChange: (id: string) => void;
    t: TFunction; 
    onAnalyze: () => void;
    isAnalyzing: boolean; 
    viewMode: ViewMode;
    setViewMode: (mode: ViewMode) => void;
    isPro: boolean; 
    isAdmin: boolean;
}> = ({ caseDetails, documents, activeContextId, onContextChange, t, onAnalyze, isAnalyzing, viewMode, setViewMode, isPro, isAdmin }) => {
    
    const analyzeButtonText = activeContextId === 'general' 
        ? t('analysis.analyzeButton', 'Analizo Rastin')
        : t('analysis.crossExamineButton', 'Kryqëzo Dokumentin');

    return (
        <motion.div className="relative mb-6 group" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <div className="absolute inset-0 rounded-2xl overflow-hidden border border-white/5 shadow-2xl">
              <div className="absolute inset-0 bg-background-light/40 backdrop-blur-md" />
              <div className="absolute top-0 right-0 p-32 bg-primary-start/10 blur-[100px] rounded-full pointer-events-none" />
          </div>

          <div className="relative p-5 sm:p-6 flex flex-col gap-5 z-10">
              <div className="flex flex-col gap-1">
                  <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white tracking-tight leading-snug break-words">{caseDetails.case_name || caseDetails.title || t('caseView.unnamedCase', 'Rast pa Emër')}</h1>
                  <div className="flex items-center gap-2 text-gray-400 mt-1"><User className="h-4 w-4 text-primary-start" /><span className="text-sm sm:text-base font-medium">{caseDetails.client?.name || t('caseCard.unknownClient', 'Klient i Panjohur')}</span></div>
              </div>

              <div className="h-px w-full bg-gradient-to-r from-transparent via-white/10 to-transparent" />

              <div className={`grid grid-cols-1 gap-3 w-full animate-in fade-in slide-in-from-top-2 ${isAdmin ? 'md:grid-cols-4' : 'md:grid-cols-4'}`}>
                    <div className="md:col-span-1 flex items-center justify-center gap-2 px-4 h-12 md:h-11 rounded-xl bg-white/5 border border-white/10 text-gray-300 text-sm font-medium whitespace-nowrap"><Calendar className="h-4 w-4 text-blue-400" />{new Date(caseDetails.created_at).toLocaleDateString()}</div>
                    <div className="md:col-span-1 h-12 md:h-11 min-w-0">{viewMode === 'workspace' && (<GlobalContextSwitcher documents={documents} activeContextId={activeContextId} onContextChange={onContextChange} className="w-full h-full" />)}</div>
                    
                    <button onClick={() => isPro && setViewMode(viewMode === 'workspace' ? 'analyst' : 'workspace')} disabled={!isPro} className={`md:col-span-1 h-12 md:h-11 rounded-xl flex items-center justify-center gap-2.5 text-sm font-bold transition-all duration-300 whitespace-nowrap border ${!isPro ? 'bg-white/5 border-white/10 text-gray-500 cursor-not-allowed opacity-70' : viewMode === 'analyst' ? 'bg-primary-start/20 border-primary-start text-white' : 'text-gray-400 border-transparent hover:text-white hover:bg-white/5'}`} title={!isPro ? "Available on Pro Plan" : ""}>
                        {!isPro ? <Lock className="h-4 w-4" /> : <Activity className="h-4 w-4" />}
                        <span>{t('caseView.financialAnalyst', 'Analisti Financiar')}</span>
                    </button>

                    <button onClick={onAnalyze} disabled={!isPro || isAnalyzing || viewMode !== 'workspace'} className={`md:col-span-1 h-12 md:h-11 rounded-xl flex items-center justify-center gap-2.5 text-sm font-bold text-white shadow-lg transition-all duration-300 whitespace-nowrap border border-transparent ${!isPro ? 'bg-gray-700/50 cursor-not-allowed text-gray-400 shadow-none' : 'bg-primary-start hover:bg-primary-end shadow-primary-start/20'} disabled:opacity-70`} type="button" title={!isPro ? "Available on Pro Plan" : ""}>
                        {isAnalyzing ? (
                            <><Loader2 className="h-4 w-4 animate-spin text-white/70" /> <span className="text-white/70">{t('analysis.analyzing', 'Duke analizuar...')}</span></>
                        ) : !isPro ? (
                            <><Lock className="h-4 w-4" /> <span>{analyzeButtonText}</span></>
                        ) : (
                            <><ShieldCheck className="h-4 w-4" /> <span>{analyzeButtonText}</span></>
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
  const [activeContextId, setActiveContextId] = useState<string>('general');
  const [viewMode, setViewMode] = useState<ViewMode>('workspace');

  const isPro = useMemo(() => {
      if (!user) return false;
      return user.subscription_tier === 'PRO' || user.role === 'ADMIN';
  }, [user]);

  const isAdmin = useMemo(() => {
      return user?.role === 'ADMIN';
  }, [user]);

  const currentCaseId = useMemo(() => caseId || '', [caseId]);
  const { documents: liveDocuments, setDocuments: setLiveDocuments, messages: liveMessages, setMessages, connectionStatus, reconnect, sendChatMessage, isSendingMessage } = useDocumentSocket(currentCaseId);
  const isReadyForData = isAuthenticated && !isAuthLoading && !!caseId;

  useEffect(() => { if (!currentCaseId) return; const cached = localStorage.getItem(`chat_history_${currentCaseId}`); if (cached) { try { const parsed = JSON.parse(cached); if (Array.isArray(parsed) && parsed.length > 0) setMessages(parsed); } catch (e) {} } }, [currentCaseId, setMessages]);
  useEffect(() => { if (!currentCaseId) return; if (liveMessages.length > 0) localStorage.setItem(`chat_history_${currentCaseId}`, JSON.stringify(liveMessages)); }, [liveMessages, currentCaseId]);

  const fetchCaseData = useCallback(async (isInitialLoad = false) => {
    if (!caseId) return;
    if(isInitialLoad) setIsLoading(true);
    setError(null);
    try {
      const [details, initialDocs] = await Promise.all([apiService.getCaseDetails(caseId), apiService.getDocuments(caseId)]);
      setCaseData({ details });
      if (isInitialLoad) { setLiveDocuments((initialDocs || []).map(sanitizeDocument)); const serverHistory = extractAndNormalizeHistory(details); if (serverHistory.length > 0) setMessages(serverHistory); }
    } catch (err) { setError(t('error.failedToLoadCase')); } finally { if(isInitialLoad) setIsLoading(false); }
  }, [caseId, t, setLiveDocuments, setMessages]);

  useEffect(() => { if (isReadyForData) fetchCaseData(true); }, [isReadyForData, fetchCaseData]);

  const handleDocumentUploaded = (newDoc: Document) => { setLiveDocuments(prev => [sanitizeDocument(newDoc), ...prev]); };
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => { setLiveDocuments(prev => prev.filter(d => String(d.id) !== String(response.documentId))); };
  const handleClearChat = async () => { if (!caseId) return; try { await apiService.clearChatHistory(caseId); setMessages([]); localStorage.removeItem(`chat_history_${currentCaseId}`); } catch (err) { alert(t('error.generic')); } };
  const handleAnalyze = async () => { if (!caseId) return; setIsAnalyzing(true); setActiveModal('none'); try { let result: CaseAnalysisResult; if (activeContextId === 'general') { result = await apiService.analyzeCase(caseId); } else { result = await apiService.crossExamineDocument(caseId, activeContextId); } if (result.error) alert(result.error); else { setAnalysisResult(result); setActiveModal('analysis'); } } catch (err) { alert(t('error.generic')); } finally { setIsAnalyzing(false); } };
  const handleChatSubmit = (text: string, _mode: ChatMode, reasoning: ReasoningMode, documentId?: string, jurisdiction?: Jurisdiction) => { sendChatMessage(text, reasoning, documentId, jurisdiction); };
  const handleViewOriginal = (doc: Document) => { const url = `${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`; setViewingUrl(url); setViewingDocument(doc); setMinimizedDocument(null); };
  const handleCloseViewer = () => { setViewingDocument(null); setViewingUrl(null); };
  const handleMinimizeViewer = () => { if (viewingDocument) { setMinimizedDocument(viewingDocument); handleCloseViewer(); } };
  const handleExpandViewer = () => { if (minimizedDocument) { handleViewOriginal(minimizedDocument); } };
  const handleRename = async (newName: string) => { if (!caseId || !documentToRename) return; try { await apiService.renameDocument(caseId, documentToRename.id, newName); setLiveDocuments(prev => prev.map(d => d.id === documentToRename.id ? { ...d, file_name: newName } : d)); } catch (error) { alert(t('error.generic')); } };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-red-400 border border-red-600 rounded-md bg-red-900/50 mt-10 mx-4"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p>{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen pb-10" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 pt-24 pb-6">
        <div>
            <CaseHeader 
                caseDetails={caseData.details} 
                documents={liveDocuments}
                activeContextId={activeContextId} 
                onContextChange={setActiveContextId}
                t={t} 
                onAnalyze={handleAnalyze} 
                isAnalyzing={isAnalyzing} 
                viewMode={viewMode}
                setViewMode={setViewMode}
                isPro={isPro}
                isAdmin={isAdmin}
            />
        </div>
        <AnimatePresence mode="wait">
            {viewMode === 'workspace' && (
                <motion.div key="workspace" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.2 }} className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[600px] relative z-0">
                    <DocumentsPanel caseId={caseData.details.id} documents={liveDocuments} t={t} connectionStatus={connectionStatus} reconnect={reconnect} onDocumentUploaded={handleDocumentUploaded} onDocumentDeleted={handleDocumentDeleted} onViewOriginal={handleViewOriginal} onRename={(doc) => setDocumentToRename(doc)} className="h-[500px] lg:h-full shadow-xl" />
                    <ChatPanel messages={liveMessages} connectionStatus={connectionStatus} reconnect={reconnect} onSendMessage={handleChatSubmit} isSendingMessage={isSendingMessage} onClearChat={handleClearChat} t={t} className="!h-[600px] lg!h-full w-full shadow-xl" activeContextId={activeContextId} isPro={isPro} />
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