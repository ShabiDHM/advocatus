// FILE: src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL - DOCUMENTS PANEL V18.0 (SINGLE UNIFIED PROGRESS BAR • ZERO GHOST DUPLICATES)

import React, { useState, useRef, useEffect } from 'react';
import { Document, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { 
    FolderOpen, Eye, Trash, Plus, Loader2, 
    Archive, Pencil, CheckSquare, Square, XCircle, 
    Lock, AlertTriangle
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
  const [uploadNotice, setUploadNotice] = useState<{ text: string; type: 'error' | 'warning' } | null>(null);
  
  const [archivingId, setScanningIdArchive] = useState<string | null>(null); 
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
    setIsUploading(true);
    setUploadNotice(null);

    try {
      const responseData = await apiService.uploadDocument(caseId, file, () => {});
      const rawData = responseData as any;
      const newDoc: Document = {
          ...responseData,
          id: responseData.id || rawData._id, 
          status: 'PROCESSING',
          progress_percent: 30, 
          progress_message: 'Duke procesuar...'
      } as any;
      onDocumentUploaded(newDoc);
    } catch (error: any) {
      console.error(`Failed to upload ${file.name}`, error);
      const errorMsg = error?.response?.data?.detail || error?.message || `${t('documentsPanel.uploadFailed', 'Dështoi ngarkimi')}: ${file.name}`;
      setUploadNotice({ text: errorMsg, type: 'error' });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadNotice(null);

    // Duplicate Check
    const normalizedName = file.name.toLowerCase().trim();
    const isDuplicate = documents.some(
      (d) => (d.file_name || (d as any).title || '').toLowerCase().trim() === normalizedName
    );

    if (isDuplicate) {
      setUploadNotice({
        text: `Dokumenti "${file.name}" tashmë ekziston në këtë lëndë. Fshini versionin ekzistues nëse dëshironi ta zëvendësoni.`,
        type: 'warning',
      });
      if (fileInputRef.current) fileInputRef.current.value = '';
      return;
    }

    await performUpload(file);
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
      if (selectedIds.size === documents.length) {
          setSelectedIds(new Set()); 
      } else {
          const allIds = documents.map(d => d.id);
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

  const isSelectionMode = selectedIds.size > 0;

  return (
    <>
    <div className={`glass-panel p-4 rounded-2xl flex flex-col h-full overflow-hidden bg-canvas ${className}`}>
      
      {/* Header Bar */}
      <div className={`flex flex-row justify-between items-center border-b pb-3 mb-4 flex-shrink-0 gap-2 transition-colors duration-300 ${
        isSelectionMode ? 'border-rose-500/30 bg-rose-500/10 -mx-4 px-4 py-2 mt-[-1rem] rounded-t-2xl' : 'border-main'
      }`}>
        
        {isSelectionMode ? (
            <div className="flex items-center justify-between w-full h-11">
                <div className="flex items-center gap-3">
                    <button 
                        onClick={() => setSelectedIds(new Set())} 
                        className="flex items-center justify-center w-11 h-11 text-text-muted hover:text-text-primary transition-colors focus:outline-none cursor-pointer"
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
                        className="flex items-center justify-center w-11 h-11 text-text-muted hover:text-text-primary transition-colors focus:outline-none cursor-pointer" 
                        title="Select All"
                    >
                        {documents.length > 0 && selectedIds.size === documents.length ? <CheckSquare size={18} className="text-primary-start" /> : <Square size={18} />}
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
                        className={`h-11 w-11 flex items-center justify-center rounded-xl shadow-sm transition-all focus:outline-none cursor-pointer ${
                            isSystemBusy 
                                ? 'bg-surface text-text-disabled cursor-not-allowed border border-main' 
                                : 'btn-primary p-0'
                        }`}
                        title={isSystemBusy ? "Prisni që dokumenti të procesohet..." : "Shto Dokument"}
                    >
                        {isSystemBusy ? <Loader2 className="h-5 w-5 animate-spin text-text-muted" /> : <Plus className="h-5 w-5" />}
                    </motion.button>

                    <AnimatePresence>
                        {showAddMenu && !isSystemBusy && (
                            <motion.div 
                                initial={{ opacity: 0, y: 6, scale: 0.96 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 6, scale: 0.96 }}
                                transition={{ duration: 0.12 }}
                                className="absolute right-0 top-12 w-52 rounded-2xl shadow-2xl border border-main z-50 overflow-hidden text-text-primary bg-card divide-y divide-main"
                                style={{
                                  backgroundColor: 'var(--bg-card, #ffffff)',
                                  boxShadow: '0 20px 40px -8px rgba(0, 0, 0, 0.4), 0 0 0 1px var(--border-main)'
                                }}
                            >
                                <button 
                                    onClick={() => { setShowAddMenu(false); fileInputRef.current?.click(); }} 
                                    className="w-full text-left px-4 py-3 hover:bg-hover text-xs font-bold uppercase tracking-wider text-text-primary transition-colors focus:outline-none cursor-pointer"
                                >
                                    Ngarko Dokument
                                </button>
                                <button 
                                    onClick={() => { setShowAddMenu(false); setShowArchiveImport(true); }} 
                                    className="w-full text-left px-4 py-3 hover:bg-hover text-xs font-bold uppercase tracking-wider text-text-primary transition-colors focus:outline-none cursor-pointer"
                                >
                                    Importo nga Arkiva
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  className="hidden" 
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
      
      {/* Unified Documents List - One single card per document */}
      <div className="space-y-2 flex-1 overflow-y-auto overflow-x-hidden pr-1.5 custom-finance-scroll min-h-0 bg-canvas/20 rounded-xl p-2 border border-main">
        {documents.length === 0 && (
          <div className="text-text-muted text-center py-12 flex flex-col items-center opacity-60">
            <FolderOpen className="w-12 h-12 mb-3 text-text-disabled/20" />
            <p className="text-sm font-medium">{t('documentsPanel.noDocuments', 'Nuk ka dokumente në këtë lëndë.')}</p>
          </div>
        )}
        
        {documents.map((doc) => {
          const isProcessingState = doc.status === 'PENDING' || doc.status === 'PROCESSING';
          const progressPercent = isProcessingState ? (doc.progress_percent && doc.progress_percent > 10 ? doc.progress_percent : 45) : 100;
          const statusText = isProcessingState ? (doc.progress_message || 'Duke procesuar...') : 'Gati';
          const canInteract = !isProcessingState;
          const isSelected = selectedIds.has(doc.id);

          return (
            <motion.div 
                key={doc.id} 
                layout="position" 
                onClick={() => canInteract && toggleSelect(doc.id)} 
                className={`group flex items-center justify-between p-3 border rounded-xl transition-all cursor-pointer ${
                    isSelected 
                        ? 'bg-primary-start/10 border-primary-start/50 shadow-sm' 
                        : 'bg-surface/30 hover:bg-hover border-main'
                }`}
                initial={{ opacity: 0, y: -6 }} 
                animate={{ opacity: 1, y: 0 }}
            >
              
              <div className="min-w-0 flex-1 pr-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold truncate text-text-primary">{doc.file_name}</p>
                </div>
                {isProcessingState ? (
                    <div className="flex items-center gap-3 mt-1.5">
                        <span className="text-[10px] text-primary-start font-bold uppercase tracking-wider truncate max-w-[140px] sm:max-w-[200px]">
                          {statusText}
                        </span>
                        <div className="w-24 sm:w-28 h-1.5 bg-surface rounded-full overflow-hidden border border-main">
                          <motion.div 
                            className="h-full bg-primary-start" 
                            animate={{ width: `${progressPercent}%` }} 
                            transition={{ ease: "easeOut", duration: 0.3 }} 
                          />
                        </div>
                        <span className="text-xs text-text-muted font-mono font-bold">{progressPercent}%</span>
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
                        className="flex items-center justify-center w-8 h-8 hover:bg-hover rounded-lg text-text-muted hover:text-text-primary transition-colors focus:outline-none cursor-pointer" 
                        title={t('documentsPanel.rename', 'Riemërto')}
                    >
                        <Pencil size={13} />
                    </button>
                )}
                
                {canInteract && (
                    <button 
                        type="button"
                        onClick={(e) => { e.stopPropagation(); onViewOriginal(doc); }} 
                        className="flex items-center justify-center w-8 h-8 hover:bg-hover rounded-lg text-primary-start transition-colors focus:outline-none cursor-pointer" 
                        title={t('documentsPanel.viewOriginal', 'Shiko')}
                    >
                        <Eye size={13} />
                    </button>
                )}
                {canInteract && (
                    <button 
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleArchiveDocument(doc.id); }} 
                        className="flex items-center justify-center w-8 h-8 hover:bg-hover rounded-lg text-text-muted hover:text-text-primary transition-colors focus:outline-none cursor-pointer" 
                        title={t('documentsPanel.archive', 'Arkivo')}
                    >
                        {archivingId === doc.id ? <Loader2 size={13} className="animate-spin text-primary-start" /> : <Archive size={13} />}
                    </button>
                )}
                {canInteract && (
                    <button 
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleDeleteDocument(doc.id); }} 
                        className="flex items-center justify-center w-8 h-8 hover:bg-rose-500/15 rounded-lg text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 transition-colors focus:outline-none cursor-pointer" 
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