// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW PAGE V6.8
// 1. UI FIX: Share button converted to Icon-Only (Square, p-2.5) to match adjacent button heights.
// 2. STATUS: Production-ready.

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Case, Document, Finding, DeletedDocumentResponse, CaseAnalysisResult, ChatMessage } from '../data/types';
import { apiService, API_V1_URL } from '../services/api';
import DocumentsPanel from '../components/DocumentsPanel';
import ChatPanel, { ChatMode, Jurisdiction } from '../components/ChatPanel';
import PDFViewerModal from '../components/PDFViewerModal';
import AnalysisModal from '../components/AnalysisModal';
import FindingsModal from '../components/FindingsModal';
import GlobalContextSwitcher from '../components/GlobalContextSwitcher';
import { useDocumentSocket } from '../hooks/useDocumentSocket';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { AlertCircle, User, Briefcase, Info, ShieldCheck, Loader2, Lightbulb, X, Save, Share2, CheckCircle } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';

type CaseData = {
    details: Case | null;
    findings: Finding[];
};
type ActiveModal = 'none' | 'findings' | 'analysis';

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
    onShowFindings: () => void;
    isAnalyzing: boolean; 
    isRefetchingFindings: boolean;
}> = ({ caseDetails, documents, activeContextId, onContextChange, t, onAnalyze, onShowFindings, isAnalyzing, isRefetchingFindings }) => {
    const [linkCopied, setLinkCopied] = useState(false);
    const handleCopyLink = () => { const link = `${window.location.origin}/portal/${caseDetails.id}`; navigator.clipboard.writeText(link); setLinkCopied(true); setTimeout(() => setLinkCopied(false), 2000); };
    
    const analyzeButtonText = activeContextId === 'general' 
        ? t('analysis.analyzeButton', 'Analizo Rastin')
        : t('analysis.crossExamineButton', 'Kryqëzo Dokumentin');

    return (
        <motion.div className="mb-6 p-4 rounded-2xl shadow-lg bg-background-light/50 backdrop-blur-sm border border-white/10" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="flex-1 min-w-0 w-full">
                  <h1 className="text-xl sm:text-2xl font-bold text-text-primary break-words mb-3 leading-tight">{caseDetails.case_name}</h1>
                  <div className="flex flex-row flex-wrap items-center gap-x-6 gap-y-2 text-xs sm:text-sm text-text-secondary"><div className="flex items-center"><User className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{caseDetails.client?.name || 'N/A'}</span></div><div className="flex items-center"><Briefcase className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{t(`caseView.statusTypes.${caseDetails.status.toUpperCase()}`)}</span></div><div className="flex items-center"><Info className="h-3.5 w-3.5 mr-1.5 text-primary-start" /><span>{new Date(caseDetails.created_at).toLocaleDateString()}</span></div></div>
              </div>
              
              <div className="flex flex-col md:flex-row items-center gap-3 w-full md:w-auto mt-4 md:mt-0">
                  <GlobalContextSwitcher documents={documents} activeContextId={activeContextId} onContextChange={onContextChange} className="w-full md:w-auto" />
                  
                  <div className="flex items-center gap-3 w-full md:w-auto">
                    {/* Share Button: Icon Only, p-2.5 for ~36px height matching peers */}
                    <button 
                        onClick={handleCopyLink} 
                        title={linkCopied ? t('general.copied', 'E kopjuar!') : t('general.share', 'Ndaj')}
                        className={`flex items-center justify-center p-2.5 rounded-xl border transition-all flex-shrink-0 ${linkCopied ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-black/20 hover:bg-black/40 text-gray-200 border-white/10'}`} 
                        type="button"
                    >
                        {linkCopied ? <CheckCircle size={16} /> : <Share2 size={16} />}
                    </button>

                    <button onClick={onShowFindings} disabled={isRefetchingFindings} className="flex-1 md:flex-initial flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-black/20 hover:bg-black/40 border border-white/10 text-gray-200 text-sm font-medium transition-all" type="button">
                        {isRefetchingFindings ? <Loader2 className="h-4 w-4 animate-spin text-amber-400" /> : <Lightbulb className="h-4 w-4 text-amber-400" />}
                        <span className="inline">{t('caseView.findingsTitle')}</span>
                    </button>
                  </div>
                  
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
  
  const [caseData, setCaseData] = useState<CaseData>({ details: null, findings: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewingDocument, setViewingDocument] = useState<Document | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isRefetchingFindings, ] = useState(false); 
  const [analysisResult, setAnalysisResult] = useState<CaseAnalysisResult | null>(null);
  const [activeAnalysisDocId, setActiveAnalysisDocId] = useState<string | undefined>(undefined);
  const [activeModal, setActiveModal] = useState<ActiveModal>('none');
  const [documentToRename, setDocumentToRename] = useState<Document | null>(null);
  
  const [activeContextId, setActiveContextId] = useState<string>('general');
  const [modalFindings, setModalFindings] = useState<Finding[]>([]);

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
      const [details, initialDocs, findingsResponse] = await Promise.all([apiService.getCaseDetails(caseId), apiService.getDocuments(caseId), apiService.getFindings(caseId)]);
      setCaseData({ details, findings: findingsResponse || [] });
      if (isInitialLoad) { setLiveDocuments((initialDocs || []).map(sanitizeDocument)); const serverHistory = extractAndNormalizeHistory(details); if (serverHistory.length > 0) setMessages(serverHistory); }
    } catch (err) { setError(t('error.failedToLoadCase')); } finally { if(isInitialLoad) setIsLoading(false); }
  }, [caseId, t, setLiveDocuments, setMessages]);

  useEffect(() => { if (isReadyForData) fetchCaseData(true); }, [isReadyForData, fetchCaseData]);
  
  const handleDocumentUploaded = (newDoc: Document) => { setLiveDocuments(prev => [sanitizeDocument(newDoc), ...prev]); };
  const handleDocumentDeleted = (response: DeletedDocumentResponse) => { setLiveDocuments(prev => prev.filter(d => String(d.id) !== String(response.documentId))); setCaseData(prev => ({ ...prev, findings: prev.findings.filter(f => String(f.document_id) !== String(response.documentId)) })); };
  const handleClearChat = async () => { if (!caseId) return; try { await apiService.clearChatHistory(caseId); setMessages([]); localStorage.removeItem(`chat_history_${currentCaseId}`); } catch (err) { alert(t('error.generic')); } };

  const handleAnalyze = async () => {
    if (!caseId) return;
    setIsAnalyzing(true);
    setActiveModal('none');
    setActiveAnalysisDocId(undefined); 

    try {
        let result: CaseAnalysisResult;
        if (activeContextId === 'general') {
            result = await apiService.analyzeCase(caseId);
            if ((result as any).target_document_id) {
                setActiveAnalysisDocId((result as any).target_document_id);
            }
        } else {
            result = await apiService.crossExamineDocument(caseId, activeContextId);
            setActiveAnalysisDocId(activeContextId);
        }
        
        if (result.error) alert(result.error);
        else { setAnalysisResult(result); setActiveModal('analysis'); }

    } catch (err) { alert(t('error.generic')); } 
    finally { setIsAnalyzing(false); }
  };

  const handleShowFindings = async () => {
      let findingsToShow: Finding[] = [];
      if (activeContextId === 'general') {
          findingsToShow = caseData.findings;
      } else {
          findingsToShow = caseData.findings.filter(f => f.document_id === activeContextId || (Array.isArray(f.document_name) && f.document_name.includes(activeContextId)));
      }
      setModalFindings(findingsToShow);
      setActiveModal('findings');
  };
  
  const handleChatSubmit = (text: string, _mode: ChatMode, documentId?: string, jurisdiction?: Jurisdiction) => { sendChatMessage(text, documentId, jurisdiction); };
  const handleViewOriginal = (doc: Document) => { const url = `${API_V1_URL}/cases/${caseId}/documents/${doc.id}/preview`; setViewingUrl(url); setViewingDocument(doc); };
  const handleRename = async (newName: string) => { if (!caseId || !documentToRename) return; try { await apiService.renameDocument(caseId, documentToRename.id, newName); setLiveDocuments(prev => prev.map(d => d.id === documentToRename.id ? { ...d, file_name: newName } : d)); } catch (error) { alert(t('error.generic')); } };

  if (isAuthLoading || isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;
  if (error || !caseData.details) return <div className="p-8 text-center text-red-400 border border-red-600 rounded-md bg-red-900/50"><AlertCircle className="mx-auto h-12 w-12 mb-4" /><p>{error}</p></div>;

  return (
    <motion.div className="w-full min-h-screen bg-background-dark pb-10" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:py-6">
        <CaseHeader 
            caseDetails={caseData.details} 
            documents={liveDocuments}
            activeContextId={activeContextId}
            onContextChange={setActiveContextId}
            t={t} 
            onAnalyze={handleAnalyze} 
            onShowFindings={handleShowFindings}
            isAnalyzing={isAnalyzing} 
            isRefetchingFindings={isRefetchingFindings}
        />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-auto lg:h-[600px]">
            <DocumentsPanel
                caseId={caseData.details.id}
                documents={liveDocuments}
                findings={caseData.findings} 
                t={t}
                connectionStatus={connectionStatus}
                reconnect={reconnect}
                onDocumentUploaded={handleDocumentUploaded}
                onDocumentDeleted={handleDocumentDeleted}
                onViewOriginal={handleViewOriginal}
                onRename={(doc) => setDocumentToRename(doc)}
                className="h-[500px] lg:h-full" 
            />
            <ChatPanel 
                messages={liveMessages} 
                connectionStatus={connectionStatus} 
                reconnect={reconnect} 
                onSendMessage={handleChatSubmit} 
                isSendingMessage={isSendingMessage} 
                onClearChat={handleClearChat} 
                t={t} 
                className="!h-[600px] lg:!h-full w-full"
                activeContextId={activeContextId}
            />
        </div>
      </div>
      {viewingDocument && (<PDFViewerModal documentData={viewingDocument} caseId={caseData.details.id} onClose={() => { setViewingDocument(null); setViewingUrl(null); }} t={t} directUrl={viewingUrl} isAuth={true} />)}
      {analysisResult && (
          <AnalysisModal 
            isOpen={activeModal === 'analysis'} 
            onClose={() => setActiveModal('none')} 
            result={analysisResult} 
            caseId={caseData.details.id}
            docId={activeAnalysisDocId}
          />
      )}
      <FindingsModal isOpen={activeModal === 'findings'} onClose={() => setActiveModal('none')} findings={modalFindings} />
      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRename} currentName={documentToRename?.file_name || ''} t={t} />
    </motion.div>
  );
};

export default CaseViewPage;