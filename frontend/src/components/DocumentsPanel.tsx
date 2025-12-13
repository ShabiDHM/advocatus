// FILE: src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL - DOCUMENTS PANEL V5.5 (I18N FIX)
// 1. FIXED: Removed hardcoded text ("Kryqëzo Provat", "Archive", "Uploading...").
// 2. STATUS: Fully localized.

import React, { useState, useRef } from 'react';
import { Document, Finding, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { 
    FolderOpen, Eye, Trash, Plus, Loader2, 
    ScanEye, Archive, Pencil, FolderInput, CheckCircle, Swords
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
  onCrossExamine?: (document: Document) => void;
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
  onCrossExamine,
  t,
  className
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [scanningId, setScanningId] = useState<string | null>(null); 
  const [completedScanId, setCompletedScanId] = useState<string | null>(null);
  const [archivingId, setScanningIdArchive] = useState<string | null>(null); 
  const [currentFileName, setCurrentFileName] = useState<string>(""); 

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
    if (file) {
        setUploadError(null);
        await performUpload(file);
        if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFolderChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files;
      if (!files || files.length === 0) return;
      setUploadError(null);
      const fileArray = Array.from(files);
      for (let i = 0; i < fileArray.length; i++) {
          await performUpload(fileArray[i]);
      }
      setCurrentFileName("");
      if (folderInputRef.current) folderInputRef.current.value = '';
  };

  const handleDeleteDocument = async (documentId: string | undefined) => {
    if (!documentId) return;
    if (!window.confirm(t('documentsPanel.confirmDelete'))) return;
    try {
      const response = await apiService.deleteDocument(caseId, documentId);
      onDocumentDeleted(response);
    } catch (error) {
      alert(t('documentsPanel.deleteFailed'));
    }
  };

  const handleDeepScan = async (docId: string) => {
      setScanningId(docId);
      setCompletedScanId(null);
      try {
          await apiService.deepScanDocument(caseId, docId);
          setCompletedScanId(docId);
          setTimeout(() => setCompletedScanId(null), 3000);
      } catch (error) {
          alert(t('error.generic'));
      } finally {
          setScanningId(null);
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

  return (
    <div className={`documents-panel bg-background-dark/40 backdrop-blur-md border border-white/10 p-4 rounded-2xl shadow-xl flex flex-col h-full overflow-hidden ${className}`}>
      <div className="flex flex-row justify-between items-center border-b border-white/10 pb-3 mb-4 flex-shrink-0 gap-2">
        <div className="flex items-center gap-3 min-w-0">
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
          
          // PHOENIX FIX: Localized Status Text
          const statusText = isUploadingState 
            ? t('documentsPanel.statusUploading', 'Duke ngarkuar...') 
            : t('documentsPanel.statusProcessing', 'Duke procesuar...');
            
          const statusTextColor = isUploadingState ? "text-primary-start" : "text-blue-400";
          
          const canInteract = !isUploadingState && !isProcessingState;

          const isScanning = scanningId === doc.id;
          const isDone = completedScanId === doc.id;

          return (
            <motion.div key={doc.id} layout="position" className="group flex items-center justify-between p-3 bg-background-light/30 hover:bg-background-light/50 border border-white/5 hover:border-white/10 rounded-xl transition-all" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
              <div className="min-w-0 flex-1 pr-3">
                <div className="flex items-center gap-2"><p className="text-sm font-medium text-gray-200 truncate">{doc.file_name}</p></div>
                {(isUploadingState || isProcessingState) ? (
                    <div className="flex items-center gap-3 mt-1.5">
                        <span className={`text-[10px] ${statusTextColor} font-medium w-16`}>{statusText}</span>
                        <div className="w-24 h-1 bg-white/10 rounded-full overflow-hidden"><motion.div className={`h-full ${barColor}`} initial={isUploadingState ? { width: 0 } : false} animate={{ width: `${progressPercent}%` }} transition={{ ease: "linear", duration: 0.3 }} /></div>
                        <span className="text-[9px] text-gray-400 font-mono">{progressPercent}%</span>
                    </div>
                ) : (<p className="text-[10px] text-gray-500 truncate mt-0.5">{moment(doc.created_at).format('YYYY-MM-DD HH:mm')}</p>)}
              </div>
              
              <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
                {canInteract && (
                    <button onClick={() => onRename && onRename(doc)} className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title={t('documentsPanel.rename')}><Pencil size={14} /></button>
                )}
                
                {/* CROSS-EXAMINE BUTTON - LOCALIZED TOOLTIP */}
                {canInteract && onCrossExamine && (
                    <button onClick={() => onCrossExamine(doc)} className="p-1.5 hover:bg-orange-500/20 rounded-lg text-orange-400/80 hover:text-orange-400 transition-colors" title={t('documentsPanel.crossExamine', 'Kryqëzo Provat')}>
                        <Swords size={14} />
                    </button>
                )}

                {/* DEEP SCAN */}
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