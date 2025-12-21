// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW PAGE V8.5 (PROP FIX)
// 1. FIX: Renamed 'onMinimizeRequest' to 'onMinimize' to match PDFViewerModal interface.
// 2. STATUS: Clean build.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Case, Document, DeletedDocumentResponse, CaseAnalysisResult, ChatMessage } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel, { ChatMode, Jurisdiction } from '../components/ChatPanel';
import PDFViewerModal from '../components/PDFViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import GlobalContextSwitcher from '../components/GlobalContextSwitcher';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, User, Briefcase, Info, ShieldCheck, Loader2, X, Save, FileText, Maximize2 } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';

type CaseData = {
    details: Case | null;
};
type ActiveModal = 'none' | 'analysis';

// --- PHOENIX: DOCKED PDF COMPONENT ---
const DockedPDFViewer: React.FC<{ document: Document; onExpand: () => void; onClose: () => void; }> = ({ document, onExpand, onClose }) => {
    return (
        <AnimatePresence>
            <motion.div
                initial={{ y: "100%", opacity: 0 }}
                animate={{ y: "0%", opacity: 1 }}
                exit={{ y: "100%", opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="fixed bottom-4 right-4 z-[9998] w-72 bg-background-light/80 backdrop-blur-xl border border-glass-edge rounded-xl shadow-2xl flex items-center justify-between p-3"
            >
                <div className="flex items-center gap-3 min-w-0">
                    <FileText className="h-5 w-5 text-primary-start flex-shrink-0" />
                    <p className="text-xs font-medium text-gray-200 truncate">{document.file_name}</p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={onExpand} className="p-1.5 hover:bg-white/10 rounded-md text-gray-400 hover:text-white transition-colors" title="Expand">
                        <Maximize2 size={16} />
                    </button>
                    <button onClick={onClose} className="p-1.5 hover:bg-red-500/10 rounded-md text-gray-400 hover:text-red-400 transition-colors" title="Close">
                        <X size={16} />
                    </button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
};

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
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
            <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6 shadow-2xl">
                <div className="flex justify-between items-center mb-6"><h3 className="text-xl font-bold text-white">{t('documentsPanel.renameTitle')}</h3><button onClick={onClose} className="text-gray-400 hover:text-white"><X size={24} /></button></div>
                <form onSubmit={handleSubmit}>
                    <div className="mb-6"><label className="block text-sm text-gray-400 mb-2">{t('documentsPanel.newName')}</label><input autoFocus type="text" value={name} onChange={(e) => setName(e.target.value)} className="w-full bg-background-light border border-glass-edge rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none" /></div>
                    <div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white font-medium">{t('general.cancel')}</button><button type="submit" disabled={isSaving} className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold flex items-center gap-2">{isSaving ? <Loader2 className="animate-spin h-4 w-4" /> : <Save size={16} />}{t('general.save')}</button></div>
                </form>
            </div>
        </div>
    );
};

// --- RESPONSIVE HEADER COMPONENT ---
const CaseHeader: React.FC<{ 
    caseDetails: Case;
    documents: Document[];
    activeContextId: string;
    onContextChange: (id: string) => void;
    t: TFunction; 
    onAnalyze: () => void;
    isAnalyzing: boolean; 
}> = ({ caseDetails, documents, activeContextId, onContextChange, t, onAnalyze, isAnalyzing }) => {
    
    const analyzeButtonText = activeContextId === 'general' 
        ? t('analysis.analyzeButton', 'Analizo Rastin')
        : t('analysis.crossExamineButton', 'Kryqëzo Dokumentin');

    return (
        <motion.div 
            className="relative z-30 mb-6 p-4 rounded-2xl shadow-lg bg-background-light/50 backdrop-blur-sm border border-white/10" 
            initial={{ opacity: 0, y: -10 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ duration: 0.3 }}
        >
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="flex-1 min-w-0 w-full">
                  <h1 className="text-lg sm:text-xl font-bold text-white break-words mb-2 leading-snug">
                    {caseDetails.case_name || caseDetails.title || t('caseView.unnamedCase', 'Rast pa Emër')}
                  </h1>
                  <div className="flex flex-row flex-wrap items-center gap-x-6 gap-y-2 text-xs sm:text-sm text-text-secondary">
                      <div className="flex items-center"><User className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{caseDetails.client?.name || 'N/A'}</span></div>
                      <div className="flex items-center"><Briefcase className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`)}</span></div>
                      <div className="flex items-center"><Info className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{new Date(caseDetails.created_at).toLocaleDateString()}</span></div>
                  </div>
              </div>
              
              <div className="flex flex-col md:flex-row items-center gap-3 w-full md:w-auto mt-4 md:mt-0">
                  <GlobalContextSwitcher documents={documents} activeContextId={activeContextId} onContextChange={onContextChange} className="w-full md:w-auto" />
                  
                  <button onClick={onAnalyze} disabled={isAnalyzing} className="w-full md:w-auto flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-black/20 hover:bg-black/40 border border-white/10 text-gray-200 text-sm font-medium transition-all disabled:opacity-50" type="button">{isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin text-primary-start" /> : <ShieldCheck className="h-4 w-4 text-primary-start" />}<span className="inline">{isAnalyzing ? t('analysis.analyzing') : analyzeButtonText}</span></button>
              </div>
          </div>
        </motion.div>
    );
};

const CaseViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
  const { caseId } = useParams<{ caseId: string }>();
  
  const [caseData, setCaseData] = useState<CaseData>({ details: null });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // PDF Viewer State
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const [minimizedDocument, setMinimizedDocument] = useState<Document | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<CaseAnalysisResult | null>(null);
  const [activeModal, setActiveModal] = useState<ActiveModal>('none');
  const [documentToRename, setDocumentToRename] = useState<Document | null>(null);
  
  const [activeContextId, setActiveContextId] = useState<string>('general');

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
  const handleChatSubmit = (text: string, _mode: ChatMode, documentId?: string, jurisdiction?: Jurisdiction) => { sendChatMessage(text, documentId, jurisdiction); };
  
  // Viewer Handlers
  const handleViewOriginal = (doc: Document) => { const url = `${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`; setViewingUrl(url); setViewingDocument(doc); setMinimizedDocument(null); };
  const handleCloseViewer = () => { setViewingDocument(null); setViewingUrl(null); };
  const handleMinimizeViewer = () => { if (viewingDocument) { setMinimizedDocument(viewingDocument); handleCloseViewer(); } };
  const handleExpandViewer = () => { if (minimizedDocument) { handleViewOriginal(minimizedDocument); } };

  const handleRename = async (newName: string) => { if (!caseId || !documentToRename) return; try { await apiService.renameDocument(caseId, documentToRename.id, newName); setLiveDocuments(prev => prev.map(d => d.id === documentToRename.id ? { ...d, file_name: newName } : d)); } catch (error) { alert(t('error.generic')); } };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-red-400 border border-red-600 rounded-md bg-red-900/50"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p>{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen bg-background-dark pb-10" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:py-6">
        <CaseHeader caseDetails={caseData.details} documents={liveDocuments} activeContextId={activeContextId} onContextChange={setActiveContextId} t={t} onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[600px]">
            <DocumentsPanel caseId={caseData.details.id} documents={liveDocuments} t={t} connectionStatus={connectionStatus} reconnect={reconnect} onDocumentUploaded={handleDocumentUploaded} onDocumentDeleted={handleDocumentDeleted} onViewOriginal={handleViewOriginal} onRename={(doc) => setDocumentToRename(doc)} className="h-[500px] lg:h-full" />
            <ChatPanel messages={liveMessages} connectionStatus={connectionStatus} reconnect={reconnect} onSendMessage={handleChatSubmit} isSendingMessage={isSendingMessage} onClearChat={handleClearChat} t={t} className="!h-[600px] lg:!h-full w-full" activeContextId={activeContextId} />
        </div>
      </div>
      
      {/* PHOENIX FIX: Updated prop name to 'onMinimize' */}
      {viewingDocument && (<PDFViewerModal documentData={viewingDocument} caseId={caseData.details.id} onClose={handleCloseViewer} onMinimize={handleMinimizeViewer} t={t} directUrl={viewingUrl} isAuth={true} />)}
      {minimizedDocument && <DockedPDFViewer document={minimizedDocument} onExpand={handleExpandViewer} onClose={() => setMinimizedDocument(null)} />}

      {analysisResult && (<AnalysisModal isOpen={activeModal === 'analysis'} onClose={() => setActiveModal('none')} result={analysisResult} />)}
      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRename} currentName={documentToRename?.file_name || ''} t={t} />
    </motion.div>
  );
};

export default CaseViewPage;