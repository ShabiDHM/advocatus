// FILE: src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL - DOCUMENTS PANEL V6.0 (HYBRID BULK ACTIONS)
// 1. ADDED: Checkbox column + Select All functionality.
// 2. UI: Header toggles between "Upload Mode" and "Action Mode".
// 3. LOGIC: Allows bulk deletion of 20+ documents instantly.

import React, { useState, useRef, useEffect } from 'react';
import { Document, Finding, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { 
    FolderOpen, Eye, Trash, Plus, Loader2, 
    ScanEye, Archive, Pencil, FolderInput, CheckCircle,
    CheckSquare, Square, XCircle
} from 'lucide-react';
import { motion } from 'framer-motion';

interface DocumentsPanelProps {
  caseId: string;
  documents: Document[];
  findings: Finding[];
  t: TFunction;
  onDocumentDeleted: (response: DeletedDocumentResponse) => void;
  onDocumentUploaded: (newDocument: Document) => void;
  onViewOriginal: (document: Document) => void;
  onRename?: (document: Document) => void; 
  connectionStatus: ConnectionStatus;
  reconnect: () => void; 
  className?: string;
}

const DocumentsPanel: React.FC<DocumentsPanelProps> = ({
  caseId,
  documents,
  findings, 
  connectionStatus,
  onDocumentDeleted,
  onDocumentUploaded,
  onViewOriginal,
  onRename,
  t,
  className
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  const [scanningId, setScanningId] = useState<string | null>(null); 
  const [scannedDocIds, setScannedDocIds] = useState<Set<string>>(new Set());
  
  const [archivingId, setScanningIdArchive] = useState<string | null>(null); 
  const [currentFileName, setCurrentFileName] = useState<string>(""); 

  // --- BULK SELECTION STATE ---
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  // Persistence Logic
  useEffect(() => {
      const storageKey = `scanned_docs_${caseId}`;
      const saved = localStorage.getItem(storageKey);
      let initialSet = new Set<string>();
      
      if (saved) {
          try {
              const parsed = JSON.parse(saved);
              if (Array.isArray(parsed)) initialSet = new Set(parsed);
          } catch (e) { console.error("Failed to parse scanned docs", e); }
      }
      if (findings && findings.length > 0) {
          findings.forEach(f => { if (f.document_id) initialSet.add(f.document_id); });
      }
      setScannedDocIds(initialSet);
  }, [caseId, findings]); 

  const markAsScanned = (docId: string) => {
      setScannedDocIds(prev => {
          const newSet = new Set(prev);
          newSet.add(docId);
          localStorage.setItem(`scanned_docs_${caseId}`, JSON.stringify(Array.from(newSet)));
          return newSet;
      });
  };

  const performUpload = async (file: File) => {
    if (file.name.startsWith('.')) return;
    setCurrentFileName(file.name);
    setUploadProgress(0);
    setIsUploading(true);
    try {
      const responseData = await apiService.uploadDocument(caseId, file, (percent) => setUploadProgress(percent));
      const rawData = responseData as any;
      const newDoc: Document = {
          ...responseData,
          id: responseData.id || rawData._id, 
          status: 'PENDING',
          progress_percent: 0, 
          progress_message: t('documentsPanel.statusPending', 'Duke pritur...')
      } as any;
      onDocumentUploaded(newDoc);
    } catch (error: any) {
      console.error(`Failed to upload ${file.name}`, error);
      setUploadError(`${t('documentsPanel.uploadFailed')}: ${file.name}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) { setUploadError(null); await performUpload(file); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  const handleFolderChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files;
      if (!files || files.length === 0) return;
      setUploadError(null);
      const fileArray = Array.from(files);
      for (let i = 0; i < fileArray.length; i++) { await performUpload(fileArray[i]); }
      setCurrentFileName("");
      if (folderInputRef.current) folderInputRef.current.value = '';
  };

  const handleDeleteDocument = async (documentId: string | undefined) => {
    if (!documentId) return;
    if (!window.confirm(t('documentsPanel.confirmDelete'))) return;
    try {
      const response = await apiService.deleteDocument(caseId, documentId);
      onDocumentDeleted(response);
    } catch (error) { alert(t('documentsPanel.deleteFailed')); }
  };

  const handleDeepScan = async (docId: string) => {
      setScanningId(docId);
      try {
          await apiService.deepScanDocument(caseId, docId);
          markAsScanned(docId);
      } catch (error) { alert(t('error.generic')); } finally { setScanningId(null); }
  };

  const handleArchiveDocument = async (docId: string) => {
      setScanningIdArchive(docId);
      try {
          await apiService.archiveCaseDocument(caseId, docId);
          alert(t('documentsPanel.archiveSuccess', 'Dokumenti u arkivua me sukses!'));
      } catch (error) { alert(t('documentsPanel.archiveFailed', 'Arkivimi dështoi.')); } finally { setScanningIdArchive(null); }
  };

  // --- BULK ACTIONS LOGIC ---
  const toggleSelect = (id: string) => {
      setSelectedIds(prev => {
          const newSet = new Set(prev);
          if (newSet.has(id)) newSet.delete(id);
          else newSet.add(id);
          return newSet;
      });
  };

  const toggleSelectAll = () => {
      if (selectedIds.size === displayDocuments.length) {
          setSelectedIds(new Set()); // Deselect all
      } else {
          const allIds = displayDocuments.map(d => d.id).filter(id => id !== 'ghost-upload');
          setSelectedIds(new Set(allIds));
      }
  };

  const handleBulkDelete = async () => {
      if (!window.confirm(`A jeni i sigurt që doni të fshini ${selectedIds.size} dokumente?`)) return;
      setIsBulkDeleting(true);
      try {
          const idsToDelete = Array.from(selectedIds);
          await apiService.bulkDeleteDocuments(caseId, idsToDelete);
          
          // Optimistically update UI
          idsToDelete.forEach(id => {
              // We construct a fake response to reuse existing handler
              onDocumentDeleted({ documentId: id, deletedFindingIds: [] });
          });
          setSelectedIds(new Set());
      } catch (error) {
          alert("Fshirja masive dështoi.");
      } finally {
          setIsBulkDeleting(false);
      }
  };

  const statusDotColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]';
      case 'CONNECTING': return 'bg-yellow-500 animate-pulse';
      default: return 'bg-red-500';
    }
  };

  const displayDocuments = [...documents];
  if (isUploading) {
      displayDocuments.unshift({
          id: 'ghost-upload',
          file_name: currentFileName,
          status: 'UPLOADING',
          // @ts-ignore
          progress_percent: uploadProgress,
          created_at: new Date().toISOString()
      } as unknown as Document);
  }

  const isSelectionMode = selectedIds.size > 0;

  return (
    <div className={`documents-panel bg-background-dark/40 backdrop-blur-md border border-white/10 p-4 rounded-2xl shadow-xl flex flex-col h-full overflow-hidden ${className}`}>
      
      {/* HEADER: DYNAMIC SWITCHING */}
      <div className={`flex flex-row justify-between items-center border-b pb-3 mb-4 flex-shrink-0 gap-2 transition-colors duration-300 ${isSelectionMode ? 'border-red-500/30 bg-red-900/10 -mx-4 px-4 py-2 mt-[-1rem] rounded-t-2xl' : 'border-white/10'}`}>
        
        {isSelectionMode ? (
            // BULK ACTION MODE HEADER
            <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3">
                    <button onClick={() => setSelectedIds(new Set())} className="text-gray-400 hover:text-white">
                        <XCircle size={20} />
                    </button>
                    <span className="text-white font-bold">{selectedIds.size} të zgjedhura</span>
                </div>
                <button 
                    onClick={handleBulkDelete} 
                    disabled={isBulkDeleting}
                    className="flex items-center gap-2 px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded-lg font-bold text-sm transition-colors shadow-lg"
                >
                    {isBulkDeleting ? <Loader2 size={16} className="animate-spin" /> : <Trash size={16} />}
                    Fshi Të Gjitha
                </button>
            </div>
        ) : (
            // NORMAL MODE HEADER
            <>
                <div className="flex items-center gap-3 min-w-0">
                    {/* MASTER CHECKBOX */}
                    <button onClick={toggleSelectAll} className="text-gray-500 hover:text-white transition-colors" title="Select All">
                        {displayDocuments.length > 0 && selectedIds.size === displayDocuments.length ? <CheckSquare size={20} className="text-primary-start" /> : <Square size={20} />}
                    </button>
                    <h2 className="text-lg font-bold text-text-primary truncate">{t('documentsPanel.title')}</h2>
                    <div className="flex items-center justify-center h-full pt-1" title={connectionStatus}>
                        <span className={`w-2.5 h-2.5 rounded-full ${statusDotColor(connectionStatus)} transition-colors duration-500`}></span>
                    </div>
                </div>

                <div className="flex-shrink-0 flex gap-2">
                    <input type="file" ref={folderInputRef} onChange={handleFolderChange} className="hidden" 
                        // @ts-ignore 
                        webkitdirectory="" directory="" multiple 
                    />
                    <motion.button onClick={() => folderInputRef.current?.click()} className="h-9 px-3 flex items-center justify-center rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 transition-all" title={t('documentsPanel.uploadFolderTooltip')} disabled={isUploading} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                        {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <FolderInput className="h-5 w-5" />}
                    </motion.button>

                    <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" disabled={isUploading} />
                    <motion.button onClick={() => fileInputRef.current?.click()} className="h-9 w-9 flex items-center justify-center rounded-xl bg-primary-start hover:bg-primary-end text-white shadow-lg shadow-primary-start/20 transition-all" title={t('documentsPanel.uploadDocument')} disabled={isUploading} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                        {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Plus className="h-5 w-5" />}
                    </motion.button>
                </div>
            </>
        )}
      </div>

      {uploadError && (<div className="p-3 text-xs text-red-100 bg-red-700/50 border border-red-500/50 rounded-lg mb-4">{uploadError}</div>)}
      
      <div className="space-y-3 flex-1 overflow-y-auto overflow-x-hidden pr-2 custom-scrollbar min-h-0">
        {displayDocuments.length === 0 && (
          <div className="text-text-secondary text-center py-10 flex flex-col items-center">
            <FolderOpen className="w-12 h-12 text-text-secondary/30 mb-3" />
            <p className="text-sm">{t('documentsPanel.noDocuments')}</p>
          </div>
        )}
        
        {displayDocuments.map((doc) => {
          let status = doc.status?.toUpperCase() || 'PENDING';
          if ((doc as any).status === 'UPLOADING') status = 'UPLOADING';

          const isUploadingState = status === 'UPLOADING';
          const isProcessingState = status === 'PENDING';
          const isReady = status === 'READY' || status === 'COMPLETED';
          const progressPercent = (doc as any).progress_percent || 0;
          const barColor = isUploadingState ? "bg-primary-start" : "bg-blue-500";
          const statusText = isUploadingState ? t('documentsPanel.statusUploading', 'Duke ngarkuar...') : t('documentsPanel.statusProcessing', 'Duke procesuar...');
          const statusTextColor = isUploadingState ? "text-primary-start" : "text-blue-400";
          const canInteract = !isUploadingState && !isProcessingState;
          const isScanning = scanningId === doc.id;
          const isDone = scannedDocIds.has(doc.id);
          const isSelected = selectedIds.has(doc.id);

          return (
            <motion.div 
                key={doc.id} 
                layout="position" 
                className={`group flex items-center justify-between p-3 border rounded-xl transition-all ${isSelected ? 'bg-primary-900/20 border-primary-500/50' : 'bg-background-light/30 hover:bg-background-light/50 border-white/5 hover:border-white/10'}`}
                initial={{ opacity: 0, y: -10 }} 
                animate={{ opacity: 1, y: 0 }}
            >
              
              {/* CHECKBOX COLUMN */}
              {!isUploadingState && (
                  <div className="mr-3 flex-shrink-0">
                      <button onClick={() => toggleSelect(doc.id)} className="text-gray-500 hover:text-white transition-colors">
                          {isSelected ? <CheckSquare size={18} className="text-primary-start" /> : <Square size={18} />}
                      </button>
                  </div>
              )}

              <div className="min-w-0 flex-1 pr-3">
                <div className="flex items-center gap-2"><p className={`text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-gray-200'}`}>{doc.file_name}</p></div>
                {(isUploadingState || isProcessingState) ? (
                    <div className="flex items-center gap-3 mt-1.5">
                        <span className={`text-[10px] ${statusTextColor} font-medium w-16`}>{statusText}</span>
                        <div className="w-24 h-1 bg-white/10 rounded-full overflow-hidden"><motion.div className={`h-full ${barColor}`} initial={isUploadingState ? { width: 0 } : false} animate={{ width: `${progressPercent}%` }} transition={{ ease: "linear", duration: 0.3 }} /></div>
                        <span className="text-[9px] text-gray-400 font-mono">{progressPercent}%</span>
                    </div>
                ) : (<p className="text-[10px] text-gray-500 truncate mt-0.5">{moment(doc.created_at).format('YYYY-MM-DD HH:mm')}</p>)}
              </div>
              
              {/* ACTION BUTTONS (Preserved, but hidden if Bulk Mode is active to reduce clutter? No, user said keep them) */}
              <div className={`flex items-center gap-1 sm:gap-2 flex-shrink-0 transition-opacity ${isSelectionMode ? 'opacity-30 pointer-events-none' : 'opacity-80 group-hover:opacity-100'}`}>
                {canInteract && (
                    <button onClick={() => onRename && onRename(doc)} className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title={t('documentsPanel.rename')}><Pencil size={14} /></button>
                )}
                <button onClick={() => isReady && handleDeepScan(doc.id)} disabled={!isReady || isScanning} className={`p-1.5 rounded-lg transition-all duration-300 ${isScanning ? "bg-primary-start/20 text-blue-400" : isDone ? "bg-green-500/20 text-green-400" : isReady ? "hover:bg-white/10 text-secondary-start" : "text-gray-600 cursor-not-allowed opacity-50"}`} title={isDone ? t('general.saveSuccess') : t('documentsPanel.deepScan')}>
                    {isScanning ? <Loader2 size={14} className="animate-spin" /> : isDone ? <CheckCircle size={14} /> : <ScanEye size={14} />}
                </button>
                {canInteract && (
                    <button onClick={() => onViewOriginal(doc)} className="p-1.5 hover:bg-white/10 rounded-lg text-blue-400 transition-colors" title={t('documentsPanel.viewOriginal')}><Eye size={14} /></button>
                )}
                {canInteract && (
                    <button onClick={() => handleArchiveDocument(doc.id)} className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title={t('documentsPanel.archive', 'Arkivo')}>{archivingId === doc.id ? <Loader2 size={14} className="animate-spin" /> : <Archive size={14} />}</button>
                )}
                {canInteract && (
                    <button onClick={() => handleDeleteDocument(doc.id)} className="p-1.5 hover:bg-red-500/20 rounded-lg text-red-500/70 hover:text-red-500 transition-colors" title={t('documentsPanel.delete')}><Trash size={14} /></button>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
export default DocumentsPanel;