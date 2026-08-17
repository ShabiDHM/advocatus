// FILE: src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL - DOCUMENTS PANEL V14.0 (SOLID OPAQUE THEME-AWARE DROPDOWN MENU)

import React, { useState, useRef, useEffect } from 'react';
import { Document, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { 
    FolderOpen, Eye, Trash, Plus, Loader2, 
    Archive, Pencil, CheckSquare, Square, XCircle, 
    HardDrive, FilePlus, Lock, AlertTriangle
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
  const [uploadNotice, setUploadNotice] = useState<{ text: string; type: 'error' | 'warning' } | null>(null);
  
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

  const performUpload = async (file: File): Promise<void> => {
    if (file.name.startsWith('.')) return;
    setCurrentFileName(file.name);
    setUploadProgress(0);
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
      const errorMsg = error?.response?.data?.detail || error?.message || `${t('documentsPanel.uploadFailed', 'Dështoi ngarkimi')}: ${file.name}`;
      setUploadNotice({ text: errorMsg, type: 'error' });
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const rawFiles = event.target.files;
    if (!rawFiles || rawFiles.length === 0) return;

    const filesArray = Array.from(rawFiles).filter((f) => !f.name.startsWith('.'));
    if (filesArray.length === 0) return;

    setUploadNotice(null);

    const existingFileNames = new Set(
      documents.map((d) => (d.file_name || (d as any).title || '').toLowerCase().trim())
    );

    const nonDuplicateFiles: File[] = [];
    const duplicateFileNames: string[] = [];

    for (const file of filesArray) {
      const normalizedName = file.name.toLowerCase().trim();
      if (existingFileNames.has(normalizedName)) {
        duplicateFileNames.push(file.name);
      } else {
        nonDuplicateFiles.push(file);
        existingFileNames.add(normalizedName);
      }
    }

    if (duplicateFileNames.length > 0) {
      setUploadNotice({
        text: `Dokumenti "${duplicateFileNames.join(', ')}" tashmë ekziston në këtë lëndë dhe u kapërcye për të parandaluar duplikimet.`,
        type: 'warning',
      });
    }

    if (nonDuplicateFiles.length === 0) {
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    setIsUploading(true);

    try {
      for (const file of nonDuplicateFiles) {
        await performUpload(file);
      }
    } finally {
      setIsUploading(false);
      setCurrentFileName("");
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteDocument = async (documentId: string | undefined) => {
    if (!documentId) return;
    if (!window.confirm(t('documentsPanel.confirmDelete', 'A jeni i sigurt që doni të fshini këtë dokument?'))) return;
    try {
      const response = await apiService.deleteDocument(caseId, documentId);
      onDocumentDeleted(response);
    } catch (error) { 
      alert(t('documentsPanel.deleteFailed', 'Fshirja e dokumentit dështoi.')); 
    }
  };

  const handleArchiveDocument = async (docId: string) => {
      setScanningIdArchive(docId);
      try {
          await apiService.archiveCaseDocument(caseId, docId);
          alert(t('documentsPanel.archiveSuccess', 'Dokumenti u arkivua me sukses!'));
      } catch (error) { 
        alert(t('documentsPanel.archiveFailed', 'Arkivimi dështoi.')); 
      } finally { 
        setScanningIdArchive(null); 
      }
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

  const handleArchiveImportComplete = async (_count: number) => {
      try {
          const updatedDocuments = await apiService.getDocuments(caseId);
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
      case 'CONNECTED': 
        return 'bg-[#22c55e] shadow-[0_0_10px_rgba(34,197,94,0.8),0_0_4px_rgba(34,197,94,1)] animate-pulse';
      case 'CONNECTING': 
        return 'bg-warning-start animate-pulse';
      default: 
        return 'bg-danger-start animate-pulse';
    }
  };

  const displayDocuments = [...documents];
  if (isUploading && currentFileName) {
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
    <div className={`glass-panel p-4 rounded-2xl flex flex-col h-full overflow-hidden bg-canvas ${className}`}>
      
      {/* Header Bar with high-contrast selection theme */}
      <div className={`flex flex-row justify-between items-center border-b pb-3 mb-4 flex-shrink-0 gap-2 transition-colors duration-300 ${
        isSelectionMode ? 'border-rose-500/30 bg-rose-500/10 -mx-4 px-4 py-2 mt-[-1rem] rounded-t-2xl' : 'border-main'
      }`}>
        
        {isSelectionMode ? (
            <div className="flex items-center justify-between w-full h-11">
                <div className="flex items-center gap-3">
                    <button 
                        onClick={() => setSelectedIds(new Set())} 
                        className="flex items-center justify-center w-11 h-11 text-text-muted hover:text-text-primary transition-colors focus:outline-none"
                        aria-label="Clear selection"
                    >
                        <XCircle size={20} />
                    </button>
                    <span className="text-rose-600 dark:text-rose-400 font-bold text-sm">{selectedIds.size} të zgjedhura</span>
                </div>
                <button 
                    onClick={handleBulkDelete} 
                    disabled={isBulkDeleting}
                    className="flex items-center gap-2 px-4 h-11 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-bold text-xs uppercase tracking-wider transition-colors shadow-lg shadow-rose-600/25 focus:outline-none cursor-pointer active:scale-95"
                >
                    {isBulkDeleting ? <Loader2 size={16} className="animate-spin" /> : <Trash size={15} />}
                    Fshi Të Gjitha
                </button>
            </div>
        ) : (
            <>
                <div className="flex items-center gap-2 min-w-0 h-11">
                    <button 
                        onClick={toggleSelectAll} 
                        className="flex items-center justify-center w-11 h-11 text-text-muted hover:text-text-primary transition-colors focus:outline-none" 
                        title="Select All"
                    >
                        {displayDocuments.length > 0 && selectedIds.size === displayDocuments.length ? <CheckSquare size={18} className="text-primary-start" /> : <Square size={18} />}
                    </button>
                    <h2 className="text-base font-bold text-text-primary truncate select-none">{t('documentsPanel.title', 'Dokumentet')}</h2>
                    <div className="flex items-center justify-center ml-1">
                        <span className={`w-2 h-2 rounded-full ${statusDotColor(connectionStatus)} transition-all duration-300`} />
                    </div>
                </div>

                <div className="relative h-11 flex items-center" ref={dropdownRef}>
                    <motion.button 
                        onClick={() => !isSystemBusy && setShowAddMenu(!showAddMenu)}
                        disabled={isSystemBusy}
                        whileTap={{ scale: 0.95 }}
                        className={`h-11 w-11 flex items-center justify-center rounded-xl shadow-sm transition-all focus:outline-none ${
                            isSystemBusy 
                                ? 'bg-surface text-text-disabled cursor-not-allowed border border-main' 
                                : 'btn-primary p-0'
                        }`}
                        title={isSystemBusy ? "Prisni që dokumentet aktuale të procesohen..." : "Shto Dokumente"}
                    >
                        {isSystemBusy ? <Loader2 className="h-5 w-5 animate-spin text-text-muted" /> : <Plus className="h-5 w-5" />}
                    </motion.button>

                    {/* 100% SOLID OPAQUE DROPDOWN MENU */}
                    <AnimatePresence>
                        {showAddMenu && !isSystemBusy && (
                            <motion.div 
                                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 8, scale: 0.96 }}
                                transition={{ duration: 0.15 }}
                                className="absolute right-0 top-12 w-60 rounded-2xl shadow-2xl border border-main z-50 overflow-hidden text-text-primary bg-card"
                                style={{
                                  backgroundColor: 'var(--bg-card, #ffffff)',
                                  boxShadow: '0 20px 40px -8px rgba(0, 0, 0, 0.45), 0 0 0 1px var(--border-main)'
                                }}
                            >
                                <button 
                                    onClick={() => { setShowAddMenu(false); fileInputRef.current?.click(); }} 
                                    className="w-full text-left px-4.5 py-3 hover:bg-hover flex items-center gap-3 text-xs sm:text-sm font-semibold text-text-primary transition-colors focus:outline-none cursor-pointer"
                                >
                                    <FilePlus size={16} className="text-primary-start shrink-0" /> Ngarko Dokumente
                                </button>
                                <button 
                                    onClick={() => { setShowAddMenu(false); setShowArchiveImport(true); }} 
                                    className="w-full text-left px-4.5 py-3 hover:bg-hover flex items-center gap-3 text-xs sm:text-sm font-semibold text-text-primary border-t border-main transition-colors focus:outline-none cursor-pointer"
                                >
                                    <HardDrive size={16} className="text-status-success shrink-0" /> Importo nga Arkiva
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* MULTI-FILE UPLOAD INPUT */}
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  className="hidden" 
                  multiple 
                  disabled={isSystemBusy} 
                />
            </>
        )}
      </div>

      {uploadNotice && (
        <div
          className={`p-3 text-xs rounded-xl mb-4 font-medium flex items-start gap-2 border ${
            uploadNotice.type === 'warning'
              ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30'
              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30'
          }`}
        >
          <AlertTriangle size={15} className="shrink-0 mt-0.5" />
          <div className="flex-1">{uploadNotice.text}</div>
          <button
            type="button"
            onClick={() => setUploadNotice(null)}
            className="text-text-muted hover:text-text-primary text-xs font-bold"
          >
            ✕
          </button>
        </div>
      )}
      
      {/* Scrollable Container */}
      <div className="space-y-2 flex-1 overflow-y-auto overflow-x-hidden pr-1.5 custom-finance-scroll min-h-0 bg-canvas/20 rounded-xl p-2 border border-main">
        {displayDocuments.length === 0 && (
          <div className="text-text-muted text-center py-12 flex flex-col items-center opacity-60">
            <FolderOpen className="w-12 h-12 mb-3 text-text-disabled/20" />
            <p className="text-sm font-medium">{t('documentsPanel.noDocuments', 'Nuk ka dokumente në këtë lëndë.')}</p>
          </div>
        )}
        
        {displayDocuments.map((doc) => {
          const isUploadingState = doc.status === 'UPLOADING';
          const isProcessingState = doc.status === 'PENDING' || doc.status === 'PROCESSING';
          const progressPercent = doc.progress_percent || 0;
          const barColor = "bg-primary-start";
          const statusText = isUploadingState ? t('documentsPanel.statusUploading', 'Duke ngarkuar...') : t('documentsPanel.statusProcessing', 'Duke procesuar...');
          const statusTextColor = "text-primary-start";
          const canInteract = !isUploadingState && !isProcessingState;
          const isSelected = selectedIds.has(doc.id);

          return (
            <motion.div 
                key={doc.id} 
                layout="position" 
                onClick={() => !isUploadingState && toggleSelect(doc.id)} 
                className={`group flex items-center justify-between p-3 border rounded-xl transition-all cursor-pointer ${
                    isSelected 
                        ? 'bg-primary-start/10 border-primary-start/50 shadow-sm' 
                        : 'bg-surface/30 hover:bg-hover border-main'
                }`}
                initial={{ opacity: 0, y: -10 }} 
                animate={{ opacity: 1, y: 0 }}
            >
              
              <div className="min-w-0 flex-1 pr-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold truncate text-text-primary">{doc.file_name}</p>
                </div>
                {(isUploadingState || isProcessingState) ? (
                    <div className="flex items-center gap-3 mt-1.5">
                        <span className={`text-[10px] ${statusTextColor} font-bold uppercase tracking-wider w-24`}>{statusText}</span>
                        <div className="w-24 h-1.5 bg-surface rounded-full overflow-hidden border border-main">
                          <motion.div className={`h-full ${barColor}`} initial={isUploadingState ? { width: 0 } : false} animate={{ width: `${progressPercent}%` }} transition={{ ease: "linear", duration: 0.3 }} />
                        </div>
                        <span className="text-xs text-text-muted font-mono">{progressPercent}%</span>
                    </div>
                ) : (
                  <p className="text-xs text-text-muted truncate mt-0.5 font-medium font-mono">{moment(doc.created_at).format('DD MMM YYYY, HH:mm')}</p>
                )}
              </div>
              
              {/* Row action tools */}
              <div className={`flex items-center gap-1.5 flex-shrink-0 transition-opacity ${isSelectionMode ? 'opacity-30 pointer-events-none' : 'opacity-60 group-hover:opacity-100'}`}>
                {canInteract && (
                    <button 
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onRename && onRename(doc); }} 
                        className="flex items-center justify-center w-8 h-8 hover:bg-hover rounded-lg text-text-muted hover:text-text-primary transition-colors focus:outline-none" 
                        title={t('documentsPanel.rename', 'Riemërto')}
                    >
                        <Pencil size={13} />
                    </button>
                )}
                
                {canInteract && (
                    <button 
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onViewOriginal(doc); }} 
                        className="flex items-center justify-center w-8 h-8 hover:bg-hover rounded-lg text-primary-start transition-colors focus:outline-none" 
                        title={t('documentsPanel.viewOriginal', 'Shiko')}
                    >
                        <Eye size={13} />
                    </button>
                )}
                {canInteract && (
                    <button 
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleArchiveDocument(doc.id); }} 
                        className="flex items-center justify-center w-8 h-8 hover:bg-hover rounded-lg text-text-muted hover:text-text-primary transition-colors focus:outline-none" 
                        title={t('documentsPanel.archive', 'Arkivo')}
                    >
                        {archivingId === doc.id ? <Loader2 size={13} className="animate-spin text-primary-start" /> : <Archive size={13} />}
                    </button>
                )}
                {canInteract && (
                    <button 
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleDeleteDocument(doc.id); }} 
                        className="flex items-center justify-center w-8 h-8 hover:bg-rose-500/15 rounded-lg text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 transition-colors focus:outline-none" 
                        title={t('documentsPanel.delete', 'Fshij')}
                    >
                        <Trash size={13} />
                    </button>
                )}
                {!canInteract && (
                    <Lock size={13} className="text-text-disabled/40 mr-2" />
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