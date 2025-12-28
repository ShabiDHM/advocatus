// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V9.0 (GLASS & MOBILE OPTIMIZED)
// 1. LAYOUT: Mobile stack (grid-cols-1) -> Desktop split (grid-cols-2).
// 2. DESIGN: Applied global 'glass-panel' classes and refined header gradients.
// 3. UX: Improved docked PDF viewer positioning for mobile devices.

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
import { AlertCircle, User, ShieldCheck, Loader2, X, Save, FileText, Maximize2, Calendar } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';

type CaseData = {
    details: Case | null;
};
type ActiveModal = 'none' | 'analysis';

// --- DOCKED PDF VIEWER (GLASS STYLE) ---
const DockedPDFViewer: React.FC<{ document: Document; onExpand: () => void; onClose: () => void; }> = ({ document, onExpand, onClose }) => {
    const { t } = useTranslation();
    return (
        <AnimatePresence>
            <motion.div
                initial={{ y: "100%", opacity: 0 }}
                animate={{ y: "0%", opacity: 1 }}
                exit={{ y: "100%", opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="fixed bottom-20 lg:bottom-4 right-4 z-[9998] w-[calc(100%-2rem)] sm:w-80 bg-background-dark/80 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl flex items-center justify-between p-3"
            >
                <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 bg-red-500/10 rounded-lg border border-red-500/10">
                        <FileText className="h-5 w-5 text-red-400 flex-shrink-0" />
                    </div>
                    <p className="text-sm font-medium text-white truncate">{document.file_name}</p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={onExpand} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title={t('general.expand', 'Zgjero')}>
                        <Maximize2 size={18} />
                    </button>
                    <button onClick={onClose} className="p-2 hover:bg-red-500/10 rounded-lg text-gray-400 hover:text-red-400 transition-colors" title={t('general.close', 'Mbyll')}>
                        <X size={18} />
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

// --- RENAME MODAL (GLASS STYLE) ---
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
                    <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors">
                        <X size={24} />
                    </button>
                </div>
                <form onSubmit={handleSubmit}>
                    <div className="mb-6">
                        <label className="block text-sm text-gray-400 mb-2">{t('documentsPanel.newName')}</label>
                        <input autoFocus type="text" value={name} onChange={(e) => setName(e.target.value)} className="glass-input w-full rounded-xl px-4 py-3" />
                    </div>
                    <div className="flex justify-end gap-3">
                        <button type="button" onClick={onClose} className="px-4 py-2 text-gray-400 hover:text-white font-medium transition-colors">{t('general.cancel')}</button>
                        <button type="submit" disabled={isSaving} className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-primary-start/20 transition-all active:scale-95">
                            {isSaving ? <Loader2 className="animate-spin h-4 w-4" /> : <Save size={16} />}
                            {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

// --- HEADER COMPONENT (GLASS STYLE) ---
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
            className="relative z-30 mb-6 rounded-2xl shadow-2xl border border-white/5 group overflow-hidden" 
            initial={{ opacity: 0, y: -10 }} 
            animate={{ opacity: 1, y: 0 }} 
            transition={{ duration: 0.3 }}
        >
          {/* Glass Background */}
          <div className="absolute inset-0 bg-background-light/40 backdrop-blur-md" />
          <div className="absolute top-0 right-0 p-32 bg-primary-start/10 blur-[100px] rounded-full pointer-events-none" />

          <div className="relative p-5 sm:p-6 flex flex-col gap-5 z-10">
              {/* TOP SECTION */}
              <div className="flex flex-col gap-1">
                  <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white tracking-tight leading-snug break-words">
                    {caseDetails.case_name || caseDetails.title || t('caseView.unnamedCase', 'Rast pa Emër')}
                  </h1>
                  <div className="flex items-center gap-2 text-gray-400 mt-1">
                      <User className="h-4 w-4 text-primary-start" />
                      <span className="text-sm sm:text-base font-medium">
                          {caseDetails.client?.name || t('caseCard.unknownClient', 'Klient i Panjohur')}
                      </span>
                  </div>
              </div>

              <div className="h-px w-full bg-gradient-to-r from-transparent via-white/10 to-transparent" />

              {/* BOTTOM SECTION - Mobile Optimized Stacking */}
              <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3 w-full">
                  
                  <div className="flex items-center justify-center gap-2 px-4 h-12 md:h-11 rounded-xl bg-white/5 border border-white/10 text-gray-300 text-sm font-medium whitespace-nowrap min-w-[140px]">
                      <Calendar className="h-4 w-4 text-blue-400" />
                      {new Date(caseDetails.created_at).toLocaleDateString()}
                  </div>

                  <div className="flex-1 w-full md:w-auto h-12 md:h-11">
                     <GlobalContextSwitcher documents={documents} activeContextId={activeContextId} onContextChange={onContextChange} className="w-full h-full" />
                  </div>
                  
                  <button 
                      onClick={onAnalyze} 
                      disabled={isAnalyzing} 
                      className={`
                          w-full md:w-auto px-6 h-12 md:h-11 rounded-xl 
                          flex items-center justify-center gap-2.5 
                          text-sm font-bold text-white shadow-lg transition-all duration-300 whitespace-nowrap
                          ${isAnalyzing ? 'bg-white/5 border border-white/10 cursor-not-allowed' : 'bg-gradient-to-r from-primary-start to-primary-end hover:shadow-primary-start/20 hover:scale-[1.02] active:scale-95 border border-transparent'}
                      `}
                      type="button"
                  >
                      {isAnalyzing ? (
                          <>
                              <Loader2 className="h-4 w-4 animate-spin text-white/70" />
                              <span className="text-white/70">{t('analysis.analyzing')}...</span>
                          </>
                      ) : (
                          <>
                              <ShieldCheck className="h-4 w-4" />
                              <span>{analyzeButtonText}</span>
                          </>
                      )}
                  </button>
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
  
  const handleViewOriginal = (doc: Document) => { const url = `${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`; setViewingUrl(url); setViewingDocument(doc); setMinimizedDocument(null); };
  const handleCloseViewer = () => { setViewingDocument(null); setViewingUrl(null); };
  const handleMinimizeViewer = () => { if (viewingDocument) { setMinimizedDocument(viewingDocument); handleCloseViewer(); } };
  const handleExpandViewer = () => { if (minimizedDocument) { handleViewOriginal(minimizedDocument); } };

  const handleRename = async (newName: string) => { if (!caseId || !documentToRename) return; try { await apiService.renameDocument(caseId, documentToRename.id, newName); setLiveDocuments(prev => prev.map(d => d.id === documentToRename.id ? { ...d, file_name: newName } : d)); } catch (error) { alert(t('error.generic')); } };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-red-400 border border-red-600 rounded-md bg-red-900/50 mt-10 mx-4"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p>{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen pb-10" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:py-6">
        
        <div className="mt-4 lg:mt-0">
            <CaseHeader caseDetails={caseData.details} documents={liveDocuments} activeContextId={activeContextId} onContextChange={setActiveContextId} t={t} onAnalyze={handleAnalyze} isAnalyzing={isAnalyzing} />
        </div>
        
        {/* MAIN GRID: 1 col on mobile, 2 cols on desktop */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[600px]">
            {/* Left: Documents (Full height on mobile or fixed 500px) */}
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
                className="h-[500px] lg:h-full shadow-xl" 
            />
            
            {/* Right: Chat (Full height on mobile or fixed 600px) */}
            <ChatPanel 
                messages={liveMessages} 
                connectionStatus={connectionStatus} 
                reconnect={reconnect} 
                onSendMessage={handleChatSubmit} 
                isSendingMessage={isSendingMessage} 
                onClearChat={handleClearChat} 
                t={t} 
                className="!h-[600px] lg:!h-full w-full shadow-xl" 
                activeContextId={activeContextId} 
            />
        </div>
      </div>
      
      {/* Modal and Viewer Logic */}
      {viewingDocument && (<PDFViewerModal documentData={viewingDocument} caseId={caseData.details.id} onClose={handleCloseViewer} onMinimize={handleMinimizeViewer} t={t} directUrl={viewingUrl} isAuth={true} />)}
      {minimizedDocument && <DockedPDFViewer document={minimizedDocument} onExpand={handleExpandViewer} onClose={() => setMinimizedDocument(null)} />}

      {analysisResult && (<AnalysisModal isOpen={activeModal === 'analysis'} onClose={() => setActiveModal('none')} result={analysisResult} />)}
      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRename} currentName={documentToRename?.file_name || ''} t={t} />
    </motion.div>
  );
};

export default CaseViewPage;