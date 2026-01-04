// FILE: src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL - DOCUMENTS PANEL V8.1 (SMOOTH TRANSITION)
// 1. FIX: Removed window.location.reload() on import.
// 2. LOGIC: Updates the document list optimistically via 'onDocumentUploaded' callback.
// 3. UX: Provides instant feedback without layout shifts.

import React, { useState, useRef, useEffect } from 'react';
import { Document, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { 
    FolderOpen, Eye, Trash, Plus, Loader2, 
    Archive, Pencil, CheckSquare, Square, XCircle, 
    HardDrive, FilePlus, Lock
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ArchiveImportModal from './ArchiveImportModal';
import { sanitizeDocument } from '../utils/documentUtils';

interface DocumentsPanelProps {
  caseId: string;
  documents: Document[];
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
  connectionStatus,
  onDocumentDeleted,
  onDocumentUploaded,
  onViewOriginal,
  onRename,
  t,
  className
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  const [archivingId, setScanningIdArchive] = useState<string | null>(null); 
  const [currentFileName, setCurrentFileName] = useState<string>(""); 

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [showArchiveImport, setShowArchiveImport] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isProcessing = documents.some(d => d.status === 'PENDING' || d.status === 'PROCESSING');
  const isSystemBusy = isUploading || isProcessing;

  useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
          if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
              setShowAddMenu(false);
          }
      };
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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

  const handleDeleteDocument = async (documentId: string | undefined) => {
    if (!documentId) return;
    if (!window.confirm(t('documentsPanel.confirmDelete'))) return;
    try {
      const response = await apiService.deleteDocument(caseId, documentId);
      onDocumentDeleted(response);
    } catch (error) { alert(t('documentsPanel.deleteFailed')); }
  };

  const handleArchiveDocument = async (docId: string) => {
      setScanningIdArchive(docId);
      try {
          await apiService.archiveCaseDocument(caseId, docId);
          alert(t('documentsPanel.archiveSuccess', 'Dokumenti u arkivua me sukses!'));
      } catch (error) { alert(t('documentsPanel.archiveFailed', 'Arkivimi dështoi.')); } finally { setScanningIdArchive(null); }
  };

  const toggleSelectAll = () => {
      if (selectedIds.size === displayDocuments.length) {
          setSelectedIds(new Set()); 
      } else {
          const allIds = displayDocuments.map(d => d.id).filter(id => id !== 'ghost-upload');
          setSelectedIds(new Set(allIds));
      }
  };

  const toggleSelect = (id: string) => {
      setSelectedIds(prev => {
          const newSet = new Set(prev);
          if (newSet.has(id)) newSet.delete(id);
          else newSet.add(id);
          return newSet;
      });
  };

  const handleBulkDelete = async () => {
      if (!window.confirm(`A jeni i sigurt që doni të fshini ${selectedIds.size} dokumente?`)) return;
      setIsBulkDeleting(true);
      try {
          const idsToDelete = Array.from(selectedIds);
          await apiService.bulkDeleteDocuments(caseId, idsToDelete);
          idsToDelete.forEach(id => {
              onDocumentDeleted({ documentId: id, deletedFindingIds: [] });
          });
          setSelectedIds(new Set());
      } catch (error) {
          alert("Fshirja masive dështoi.");
      } finally {
          setIsBulkDeleting(false);
      }
  };

  // PHOENIX FIX: Replaced window.location.reload() with manual fetch logic
  const handleArchiveImportComplete = async (_count: number) => {
      try {
          // Fetch the latest list of documents for this case
          const updatedDocuments = await apiService.getDocuments(caseId);
          
          // We identify which documents are new by comparing IDs
          // Or simpler: We iterate through the new list and if it's not in the current list, we call onDocumentUploaded
          // HOWEVER, since 'onDocumentUploaded' usually appends to the top, doing it for 10 files might be weird.
          // BUT: 'CaseViewPage' handles duplicates gracefully usually.
          
          // Cleaner Approach: Since DocumentsPanel doesn't own the state, we can't "setDocuments".
          // But we can iterate the NEW files (finding the difference) and push them up.
          
          const currentIds = new Set(documents.map(d => d.id));
          const newDocs = updatedDocuments.filter(d => !currentIds.has(d.id));
          
          newDocs.forEach(doc => {
              onDocumentUploaded(sanitizeDocument(doc));
          });
          
      } catch (error) {
          console.error("Failed to refresh documents after import", error);
      }
  };

  const statusDotColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]';
      case 'CONNECTING': return 'bg-accent-start animate-pulse';
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
    <>
    <div className={`glass-panel p-4 rounded-2xl flex flex-col h-full overflow-hidden ${className}`}>
      
      {/* Header Bar */}
      <div className={`flex flex-row justify-between items-center border-b pb-3 mb-4 flex-shrink-0 gap-2 transition-colors duration-300 ${isSelectionMode ? 'border-red-500/30 bg-red-900/10 -mx-4 px-4 py-2 mt-[-1rem] rounded-t-2xl' : 'border-white/5'}`}>
        
        {isSelectionMode ? (
            <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3">
                    <button onClick={() => setSelectedIds(new Set())} className="text-gray-400 hover:text-white transition-colors">
                        <XCircle size={20} />
                    </button>
                    <span className="text-white font-bold">{selectedIds.size} të zgjedhura</span>
                </div>
                <button 
                    onClick={handleBulkDelete} 
                    disabled={isBulkDeleting}
                    className="flex items-center gap-2 px-4 py-1.5 bg-red-500/80 hover:bg-red-500 text-white rounded-lg font-bold text-sm transition-colors shadow-lg"
                >
                    {isBulkDeleting ? <Loader2 size={16} className="animate-spin" /> : <Trash size={16} />}
                    Fshi Të Gjitha
                </button>
            </div>
        ) : (
            <>
                <div className="flex items-center gap-3 min-w-0">
                    <button onClick={toggleSelectAll} className="text-text-secondary hover:text-white transition-colors" title="Select All">
                        {displayDocuments.length > 0 && selectedIds.size === displayDocuments.length ? <CheckSquare size={20} className="text-primary-start" /> : <Square size={20} />}
                    </button>
                    <h2 className="text-lg font-bold text-white truncate">{t('documentsPanel.title')}</h2>
                    <div className="flex items-center justify-center h-full pt-1" title={connectionStatus}>
                        <span className={`w-2 h-2 rounded-full ${statusDotColor(connectionStatus)} transition-colors duration-500`}></span>
                    </div>
                </div>

                <div className="relative" ref={dropdownRef}>
                    <motion.button 
                        onClick={() => !isSystemBusy && setShowAddMenu(!showAddMenu)}
                        disabled={isSystemBusy}
                        whileTap={{ scale: 0.95 }}
                        className={`h-9 w-9 flex items-center justify-center rounded-xl shadow-lg transition-all ${isSystemBusy ? 'bg-white/5 text-gray-500 cursor-not-allowed border border-white/5' : 'bg-gradient-to-br from-primary-start to-primary-end text-white shadow-primary-start/20 hover:shadow-primary-start/40'}`}
                        title={isSystemBusy ? "Prisni që dokumenti aktual të procesohet..." : "Shto Dokument"}
                    >
                        {isSystemBusy ? <Loader2 className="h-5 w-5 animate-spin" /> : <Plus className="h-5 w-5" />}
                    </motion.button>

                    <AnimatePresence>
                        {showAddMenu && !isSystemBusy && (
                            <motion.div 
                                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                className="absolute right-0 top-12 w-56 glass-high border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
                            >
                                <button onClick={() => { setShowAddMenu(false); fileInputRef.current?.click(); }} className="w-full text-left px-4 py-3 hover:bg-white/10 flex items-center gap-3 text-sm text-gray-200 transition-colors">
                                    <FilePlus size={16} className="text-primary-start" /> Ngarko Dokument
                                </button>
                                <button onClick={() => { setShowAddMenu(false); setShowArchiveImport(true); }} className="w-full text-left px-4 py-3 hover:bg-white/10 flex items-center gap-3 text-sm text-gray-200 border-t border-white/5 transition-colors">
                                    <HardDrive size={16} className="text-success-start" /> Importo nga Arkiva
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" disabled={isSystemBusy} />
            </>
        )}
      </div>

      {uploadError && (<div className="p-3 text-xs text-red-200 bg-red-500/20 border border-red-500/30 rounded-xl mb-4 font-medium">{uploadError}</div>)}
      
      <div className="space-y-3 flex-1 overflow-y-auto overflow-x-hidden pr-2 custom-scrollbar min-h-0 bg-black/20 rounded-xl p-2">
        {displayDocuments.length === 0 && (
          <div className="text-text-secondary text-center py-12 flex flex-col items-center opacity-60">
            <FolderOpen className="w-12 h-12 mb-3 text-white/20" />
            <p className="text-sm font-medium">{t('documentsPanel.noDocuments')}</p>
          </div>
        )}
        
        {displayDocuments.map((doc) => {
          const isUploadingState = doc.status === 'UPLOADING';
          const isProcessingState = doc.status === 'PENDING' || doc.status === 'PROCESSING';
          const progressPercent = doc.progress_percent || 0;
          const barColor = isUploadingState ? "bg-primary-start" : "bg-blue-500";
          const statusText = isUploadingState ? t('documentsPanel.statusUploading', 'Duke ngarkuar...') : t('documentsPanel.statusProcessing', 'Duke procesuar...');
          const statusTextColor = isUploadingState ? "text-primary-start" : "text-blue-400";
          const canInteract = !isUploadingState && !isProcessingState;
          const isSelected = selectedIds.has(doc.id);

          return (
            <motion.div 
                key={doc.id} 
                layout="position" 
                onClick={() => !isUploadingState && toggleSelect(doc.id)} 
                className={`group flex items-center justify-between p-3 border rounded-xl transition-all cursor-pointer ${isSelected ? 'bg-primary-start/20 border-primary-start/50' : 'bg-white/5 hover:bg-white/10 border-white/5 hover:border-white/10'}`}
                initial={{ opacity: 0, y: -10 }} 
                animate={{ opacity: 1, y: 0 }}
            >
              
              <div className="min-w-0 flex-1 pr-3">
                <div className="flex items-center gap-2"><p className={`text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-gray-200'}`}>{doc.file_name}</p></div>
                {(isUploadingState || isProcessingState) ? (
                    <div className="flex items-center gap-3 mt-1.5">
                        <span className={`text-[10px] ${statusTextColor} font-bold w-20 uppercase tracking-wide`}>{statusText}</span>
                        <div className="w-24 h-1 bg-white/10 rounded-full overflow-hidden"><motion.div className={`h-full ${barColor}`} initial={isUploadingState ? { width: 0 } : false} animate={{ width: `${progressPercent}%` }} transition={{ ease: "linear", duration: 0.3 }} /></div>
                        <span className="text-[9px] text-gray-400 font-mono">{progressPercent}%</span>
                    </div>
                ) : (<p className="text-[10px] text-text-secondary truncate mt-0.5 font-medium">{moment(doc.created_at).format('DD MMM YYYY, HH:mm')}</p>)}
              </div>
              
              <div className={`flex items-center gap-1 sm:gap-2 flex-shrink-0 transition-opacity ${isSelectionMode ? 'opacity-30 pointer-events-none' : 'opacity-60 group-hover:opacity-100'}`}>
                {canInteract && (
                    <button onClick={(e) => { e.stopPropagation(); onRename && onRename(doc); }} className="p-1.5 hover:bg-white/10 rounded-lg text-text-secondary hover:text-white transition-colors" title={t('documentsPanel.rename')}><Pencil size={14} /></button>
                )}
                
                {canInteract && (
                    <button onClick={(e) => { e.stopPropagation(); onViewOriginal(doc); }} className="p-1.5 hover:bg-white/10 rounded-lg text-primary-start transition-colors" title={t('documentsPanel.viewOriginal')}><Eye size={14} /></button>
                )}
                {canInteract && (
                    <button onClick={(e) => { e.stopPropagation(); handleArchiveDocument(doc.id); }} className="p-1.5 hover:bg-white/10 rounded-lg text-text-secondary hover:text-white transition-colors" title={t('documentsPanel.archive', 'Arkivo')}>{archivingId === doc.id ? <Loader2 size={14} className="animate-spin" /> : <Archive size={14} />}</button>
                )}
                {canInteract && (
                    <button onClick={(e) => { e.stopPropagation(); handleDeleteDocument(doc.id); }} className="p-1.5 hover:bg-red-500/20 rounded-lg text-red-400 hover:text-red-300 transition-colors" title={t('documentsPanel.delete')}><Trash size={14} /></button>
                )}
                {!canInteract && (
                    <Lock size={14} className="text-gray-600" />
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>

    {/* IMPORT MODAL */}
    <ArchiveImportModal 
        isOpen={showArchiveImport} 
        onClose={() => setShowArchiveImport(false)} 
        caseId={caseId}
        onImportComplete={handleArchiveImportComplete}
    />
    </>
  );
};
export default DocumentsPanel;