// FILE: src/pages/CaseViewPage.tsx
// PHOENIX PROTOCOL - CASE VIEW V19.0 (ZERO WARNINGS & INTEGRATED STANCE TOGGLE)

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
import { AlertCircle, ShieldCheck, Loader2, X, Save, Calendar, Activity, Lock, RefreshCw, Eye, Trash2, AlertTriangle, FileText, Shield, Swords } from 'lucide-react';
import { sanitizeDocument } from '../utils/documentUtils';
import { TFunction } from 'i18next';
import DockedPDFViewer from '../components/DockedPDFViewer';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

type CaseData = { details: Case | null; };
type ActiveModal = 'none' | 'analysis';
type ViewMode = 'workspace' | 'analyst';

// ========== PHOENIX: BULLETPROOF CHAT HISTORY NORMALIZER ==========
const extractAndNormalizeHistory = (data: any): ChatMessage[] => {
    if (!data) return [];
    const rawArray = data.chat_history || data.chatHistory || data.history || data.messages || [];
    if (!Array.isArray(rawArray)) return [];

    return rawArray
        .map((item: any) => {
            if (!item) return null;

            const rawRole = (item.role || item.sender || item.author || 'user').toString().toLowerCase();
            const role: 'user' | 'ai' = (rawRole.includes('ai') || rawRole.includes('assistant') || rawRole.includes('system')) ? 'ai' : 'user';
            
            let contentStr = '';
            if (typeof item.content === 'string') {
                contentStr = item.content;
            } else if (typeof item.message === 'string') {
                contentStr = item.message;
            } else if (typeof item.text === 'string') {
                contentStr = item.text;
            } else if (item.content && typeof item.content === 'object') {
                contentStr = item.content.text || item.content.message || JSON.stringify(item.content);
            } else {
                contentStr = safeString(item.content || item.message || item.text);
            }

            const timestamp = item.timestamp || item.created_at || new Date().toISOString();
            return { role, content: contentStr, timestamp };
        })
        .filter((msg): msg is ChatMessage => Boolean(msg && typeof msg.content === 'string' && msg.content.trim() !== ''));
};

const safeString = (val: any): string => {
    if (!val) return '';
    if (typeof val === 'string') return val;
    try {
        return JSON.stringify(val);
    } catch {
        return String(val);
    }
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
    onClearAnalysis: () => void;
    isAnalyzing: boolean;
    viewMode: ViewMode;
    setViewMode: (mode: ViewMode) => void;
    isPro: boolean;
    selectedDocumentIds: string[];
    onDocumentSelectionChange: (ids: string[]) => void;
    clientPosition: 'DEFENDANT' | 'PLAINTIFF';
    onPositionToggle: (pos: 'DEFENDANT' | 'PLAINTIFF') => void;
}> = ({ caseDetails, documents, t, onAnalyze, onClearAnalysis, isAnalyzing, viewMode, setViewMode, isPro, selectedDocumentIds, onDocumentSelectionChange, clientPosition, onPositionToggle }) => {
    
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
                
                {/* LEFT COLUMN: Date, Selector & Client Stance Switcher */}
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

                {/* RIGHT COLUMN: Client Stance, Analyst & Re-analysis Controls */}
                <div className="flex flex-col gap-4">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        {/* Client Position Stance Switcher Pill */}
                        <div className="flex items-center p-1 bg-surface border border-main rounded-xl h-11 w-full select-none">
                            <button
                                type="button"
                                onClick={() => onPositionToggle('DEFENDANT')}
                                className={`flex-1 h-9 rounded-lg text-[10px] font-black uppercase tracking-wider flex items-center justify-center gap-1 transition-all focus:outline-none ${
                                    clientPosition === 'DEFENDANT'
                                        ? 'bg-primary-start text-white shadow-sm'
                                        : 'text-text-muted hover:text-text-primary'
                                }`}
                                title="Mbrojtja e të Paditurit"
                            >
                                <Shield size={12} />
                                <span className="truncate">I Paditur</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => onPositionToggle('PLAINTIFF')}
                                className={`flex-1 h-9 rounded-lg text-[10px] font-black uppercase tracking-wider flex items-center justify-center gap-1 transition-all focus:outline-none ${
                                    clientPosition === 'PLAINTIFF'
                                        ? 'bg-primary-start text-white shadow-sm'
                                        : 'text-text-muted hover:text-text-primary'
                                }`}
                                title="Përfaqësimi i Paditësit"
                            >
                                <Swords size={12} />
                                <span className="truncate">Paditës</span>
                            </button>
                        </div>

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
                        
                        {/* Minimalist Split-Button Wrapper */}
                        <div className="w-full">
                            {hasExistingAnalysis ? (
                                <div className="h-11 flex items-center justify-between rounded-xl glass-panel bg-surface border border-main shadow-sm text-xs font-bold uppercase tracking-wider text-text-primary overflow-hidden w-full">
                                    <button
                                        type="button"
                                        onClick={() => onAnalyze(false)}
                                        disabled={isAnalyzing}
                                        className="flex-1 h-full flex items-center justify-center gap-2 px-3 hover:bg-hover hover:text-primary-start transition-all duration-200 focus:outline-none"
                                        title="Shiko Analizën ekzistuese"
                                    >
                                        <Eye size={15} className="text-primary-start shrink-0" />
                                        <span className="truncate text-primary-start">Shiko Analizën</span>
                                    </button>

                                    <div className="border-r border-main h-6 shrink-0" />

                                    <button
                                        type="button"
                                        onClick={() => onAnalyze(true)}
                                        disabled={isAnalyzing}
                                        className="flex-initial px-3 h-full flex items-center justify-center gap-2 hover:bg-hover hover:text-primary-start transition-all duration-200 focus:outline-none"
                                        title="Rianalizo sërish me AI"
                                    >
                                        <RefreshCw size={14} className={`text-text-muted shrink-0 ${isAnalyzing ? "animate-spin text-primary-start" : ""}`} />
                                    </button>

                                    <div className="border-r border-main h-6 shrink-0" />

                                    <button
                                        type="button"
                                        onClick={onClearAnalysis}
                                        disabled={isAnalyzing}
                                        className="flex-initial px-4 h-full flex items-center justify-center gap-2 hover:bg-hover hover:text-danger-start transition-all duration-200 focus:outline-none"
                                        title="Fshi analizën e ruajtur"
                                    >
                                        <Trash2 size={14} className="text-text-muted hover:text-danger-start shrink-0" />
                                    </button>
                                </div>
                            ) : (
                                <button
                                    type="button"
                                    onClick={() => onAnalyze(false)} 
                                    disabled={!isPro || isAnalyzing}
                                    className={`${buttonBase} disabled:opacity-40`}
                                >
                                    {analyzeButtonText}
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
  const { isLoading: isAuthLoading, isAuthenticated } = useAuth();
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

  const [clientPosition, setClientPosition] = useState<'DEFENDANT' | 'PLAINTIFF'>('DEFENDANT');
  const [gatekeeperNotice, setGatekeeperNotice] = useState<string | null>(null);

  const isPro = true; 
  
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
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
            return parsed.filter(m => m && typeof m.content === 'string' && m.content.trim() !== '');
        }
      } catch { return null; }
    }
    return null;
  }, [caseId]);

  const persistChatHistory = useCallback(async (messages: ChatMessage[]) => {
    saveToLocalStorage(messages);
    if (!caseId) return;
    try {
      await apiService.updateChatHistory(caseId, messages);
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
      
      if (details && (details as any).client_position) {
          setClientPosition((details as any).client_position.toUpperCase() === 'PLAINTIFF' ? 'PLAINTIFF' : 'DEFENDANT');
      }

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

  const handleClearAnalysis = async () => {
    if (!caseId) return;
    try {
        await apiService.clearCaseAnalysis(caseId);
        setAnalysisResult(null);
        setCaseData(prev => prev.details ? { details: { ...prev.details, latest_analysis: null } } : prev);
    } catch {
        alert(t('error.generic'));
    }
  };

  const handlePositionToggle = async (newPos: 'DEFENDANT' | 'PLAINTIFF') => {
      if (!caseId) return;
      setClientPosition(newPos);
      try {
          await apiService.updateCasePosition(caseId, newPos);
      } catch (err) {
          console.error("Failed to set position:", err);
      }
  };

  const handleAnalyze = async (force = false) => {
    if (!caseId) return;

    const existingAnalysis = caseData.details && (caseData.details as any).latest_analysis ? (caseData.details as any).latest_analysis : analysisResult;
    
    if (existingAnalysis && !force && selectedDocumentIds.length === 0) {
        setAnalysisResult(existingAnalysis);
        setActiveModal('analysis');
        return;
    }

    if (force && existingAnalysis) {
        const lastDocIds: string[] = (existingAnalysis as any).analyzed_doc_ids || [];
        const currentDocIds: string[] = liveDocuments.map(d => String(d.id)).sort();

        const isIdentical = 
            lastDocIds.length > 0 &&
            lastDocIds.length === currentDocIds.length &&
            lastDocIds.slice().sort().every((id, idx) => id === currentDocIds[idx]);

        if (isIdentical) {
            setGatekeeperNotice("Nuk ka ndryshime në dokumentet e rastit. Për të ekzekutuar një ri-analizë të re, kërkohet të shtohet një dokument i ri ose të fshihet një dokument ekzistues.");
            return;
        }
    }
    
    setIsAnalyzing(true);
    setActiveModal('none');
    try {
      let result = selectedDocumentIds.length === 0 ? await apiService.analyzeCase(caseId, clientPosition) : await apiService.crossExamineDocument(caseId, selectedDocumentIds[0]);
      if (result.error) alert(result.error);
      else { 
        const resultWithDocIds = {
            ...result,
            analyzed_doc_ids: liveDocuments.map(d => String(d.id)).sort(),
            client_position: clientPosition
        };

        setAnalysisResult(resultWithDocIds); 
        setActiveModal('analysis'); 
        setCaseData(prev => prev.details ? { details: { ...prev.details, latest_analysis: resultWithDocIds } } : prev);
      }
    } catch { 
        alert(t('error.generic')); 
    } finally { 
        setIsAnalyzing(false); 
    }
  };

  const handleChatSubmit = async (text: string, mode: ChatMode, reasoning: ReasoningMode, domain: LegalDomain, documentIds?: string[], jurisdiction?: Jurisdiction) => {
    if (!caseId) return;
    const userMessage: ChatMessage = { role: 'user', content: text, timestamp: new Date().toISOString() };
    const assistantPlaceholder: ChatMessage = { role: 'ai', content: '', timestamp: new Date().toISOString() };
    setChatMessages(prev => [...prev, userMessage, assistantPlaceholder]);
    setIsSendingMessage(true);
    try {
      let acc = '';
      
      const enrichedText = `${text}\n\n(Ju lutem, në fund të përgjigjes suaj, shtoni një seksion të titulluar 'Sugjerime:' dhe rreshtoni saktësisht 3 pyetje të shkurtra vijuese që unë mund t'i bëj më pas in lidhje me këtë përgjigje. Formatizo si: \nSugjerime:\n1. Pyetja e parë?\n2. Pyetja e dytë?\n3. Pyetja e tretë?)`;
      
      const stream = apiService.sendChatMessageStream(
          caseId, 
          enrichedText, 
          documentIds, 
          jurisdiction, 
          reasoning, 
          mode === 'document' ? domain : undefined
      );
      
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
            onClearAnalysis={handleClearAnalysis} 
            isAnalyzing={isAnalyzing} 
            viewMode={viewMode} 
            setViewMode={setViewMode} 
            isPro={isPro} 
            selectedDocumentIds={selectedDocumentIds} 
            onDocumentSelectionChange={setSelectedDocumentIds}
            clientPosition={clientPosition}
            onPositionToggle={handlePositionToggle}
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
          onPositionChange={handlePositionToggle}
        />
      )}
      <RenameDocumentModal isOpen={!!documentToRename} onClose={() => setDocumentToRename(null)} onRename={handleRenameAction} currentName={documentToRename?.file_name || ''} t={t} />

      <AnimatePresence>
        {gatekeeperNotice && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[300] p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="glass-panel w-full max-w-md p-6 sm:p-8 rounded-3xl shadow-2xl border border-warning-start/30 bg-canvas text-center"
            >
              <div className="w-14 h-14 bg-warning-start/15 border border-warning-start/30 rounded-2xl flex items-center justify-center mx-auto mb-5 text-warning-start">
                <AlertTriangle size={28} />
              </div>

              <h3 className="text-lg sm:text-xl font-bold text-text-primary uppercase tracking-tight mb-3">
                S'ka Ndryshime në Lëndë
              </h3>

              <p className="text-xs sm:text-sm text-text-secondary leading-relaxed font-medium mb-6">
                {gatekeeperNotice}
              </p>

              <div className="p-3.5 bg-surface border border-border-main rounded-xl text-[11px] text-text-muted flex items-center gap-2 font-mono mb-6 justify-center">
                <FileText size={14} className="text-primary-start shrink-0" />
                <span>Dokumente Aktive: {liveDocuments.length}</span>
              </div>

              <button
                type="button"
                onClick={() => setGatekeeperNotice(null)}
                className="btn-primary w-full h-11 rounded-xl text-xs font-bold uppercase tracking-wider shadow-lg shadow-primary-start/15 focus:outline-none"
              >
                E Kuptova
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </motion.div>
  );
};

export default CaseViewPage;