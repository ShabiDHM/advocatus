// FILE: src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL - ALIGNMENT FIX
// 1. STYLE: Vertically aligned the 'Green Dot' with the title.
// 2. MOBILE: Ensured header buttons don't wrap awkwardly.

import React, { useState, useRef } from 'react';
import { Document, Finding, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { FolderOpen, Eye, Trash, Plus, Loader2, RefreshCw, ScanEye, Archive } from 'lucide-react';
import { motion } from 'framer-motion';

interface DocumentsPanelProps {
  caseId: string;
  documents: Document[];
  findings: Finding[];
  t: TFunction;
  onDocumentDeleted: (response: DeletedDocumentResponse) => void;
  onDocumentUploaded: (newDocument: Document) => void;
  onViewOriginal: (document: Document) => void;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
  className?: string;
}

const DocumentsPanel: React.FC<DocumentsPanelProps> = ({
  caseId,
  documents,
  connectionStatus,
  reconnect,
  onDocumentDeleted,
  onDocumentUploaded,
  onViewOriginal,
  t,
  className
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [scanningId, setScanningId] = useState<string | null>(null); 
  const [archivingId, setArchivingId] = useState<string | null>(null); 

  const performUpload = async (file: File) => {
    setIsUploading(true);
    setUploadError(null);
    try {
      const responseData = await apiService.uploadDocument(caseId, file);
      const rawData = responseData as any;
      const newDoc: Document = {
          ...responseData,
          id: responseData.id || rawData._id, 
          status: 'PENDING',
          progress_percent: 5,
          progress_message: t('documentsPanel.statusPending')
      } as any;
      
      onDocumentUploaded(newDoc);
    } catch (error: any) {
      setUploadError(t('documentsPanel.uploadFailed') + `: ${error.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) performUpload(file);
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
      try {
          await apiService.deepScanDocument(caseId, docId);
          alert(t('documentsPanel.scanStarted', 'Deep Scan filloi! Kontrolloni gjetjet pas pak.'));
      } catch (error) {
          alert(t('error.generic'));
      } finally {
          setScanningId(null);
      }
  };

  const handleArchiveDocument = async (docId: string) => {
      setArchivingId(docId);
      try {
          await apiService.archiveCaseDocument(caseId, docId);
          alert("Dokumenti u arkivua me sukses!");
      } catch (error) {
          alert("Arkivimi dështoi.");
      } finally {
          setArchivingId(null);
      }
  };

  const statusDotColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]';
      case 'CONNECTING': return 'bg-yellow-500 animate-pulse';
      default: return 'bg-red-500';
    }
  };

  return (
    <div className={`documents-panel bg-background-dark/40 backdrop-blur-md border border-white/10 p-4 rounded-2xl shadow-xl flex flex-col ${className || 'h-[500px]'}`}>
      <div className="flex flex-row justify-between items-center border-b border-white/10 pb-3 mb-4 flex-shrink-0 gap-2">
        <div className="flex items-center gap-3 min-w-0">
            <h2 className="text-lg font-bold text-text-primary truncate">{t('documentsPanel.title')}</h2>
            
            {/* Visual Dot Only - Center Aligned */}
            <div className="flex items-center justify-center h-full pt-1" title={connectionStatus}>
                <span className={`w-2.5 h-2.5 rounded-full ${statusDotColor(connectionStatus)} transition-colors duration-500`}></span>
            </div>
            
            {connectionStatus !== 'CONNECTED' && (
                <button onClick={reconnect} className="text-gray-400 hover:text-white transition-colors" title={t('documentsPanel.reconnect')}>
                    <RefreshCw size={14} />
                </button>
            )}
        </div>

        <div className="flex-shrink-0 flex gap-2">
          <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" disabled={isUploading} />
          <motion.button
            onClick={() => fileInputRef.current?.click()}
            className="h-9 w-9 flex items-center justify-center rounded-xl bg-primary-start hover:bg-primary-end text-white shadow-lg shadow-primary-start/20 transition-all"
            title={t('documentsPanel.uploadDocument')} 
            disabled={isUploading} 
            whileHover={{ scale: 1.05 }} 
            whileTap={{ scale: 0.95 }} 
          >
            {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Plus className="h-5 w-5" />}
          </motion.button>
        </div>
      </div>

      {uploadError && (<div className="p-3 text-xs text-red-100 bg-red-700/50 border border-red-500/50 rounded-lg mb-4">{uploadError}</div>)}

      <div className="space-y-3 flex-1 overflow-y-auto overflow-x-hidden pr-2 custom-scrollbar">
        {(documents.length === 0 && !isUploading) && (
          <div className="text-text-secondary text-center py-10 flex flex-col items-center">
            <FolderOpen className="w-12 h-12 text-text-secondary/30 mb-3" />
            <p className="text-sm">{t('documentsPanel.noDocuments')}</p>
          </div>
        )}
        
        {documents.map((doc) => {
          const isReady = doc.status.toUpperCase() === 'READY' || doc.status.toUpperCase() === 'COMPLETED';
          const isPending = doc.status.toUpperCase() === 'PENDING';
          const progressPercent = (doc as any).progress_percent;

          return (
            <motion.div
              key={doc.id} layout="position"
              className="group flex items-center justify-between p-3 bg-background-light/30 hover:bg-background-light/50 border border-white/5 hover:border-white/10 rounded-xl transition-all"
              initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
            >
              <div className="min-w-0 flex-1 pr-3">
                <p className="text-sm font-medium text-gray-200 truncate">{doc.file_name}</p>
                {isPending ? (
                    <div className="w-full max-w-[150px] mt-1.5 h-1 bg-white/10 rounded-full overflow-hidden">
                        <motion.div className="h-full bg-primary-start" initial={{ width: 0 }} animate={{ width: `${progressPercent || 5}%` }} />
                    </div>
                ) : (
                    <p className="text-[10px] text-gray-500 truncate mt-0.5">{moment(doc.created_at).format('YYYY-MM-DD HH:mm')}</p>
                )}
              </div>
              
              <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
                 {isReady && (
                  <>
                    <button onClick={() => handleDeepScan(doc.id)} className="p-1.5 hover:bg-white/10 rounded-lg text-secondary-start transition-colors" title={t('documentsPanel.deepScan')}>
                        {scanningId === doc.id ? <Loader2 size={14} className="animate-spin" /> : <ScanEye size={14} />}
                    </button>
                    <button onClick={() => onViewOriginal(doc)} className="p-1.5 hover:bg-white/10 rounded-lg text-blue-400 transition-colors" title={t('documentsPanel.viewOriginal')}>
                        <Eye size={14} />
                    </button>
                    <button onClick={() => handleArchiveDocument(doc.id)} className="p-1.5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title="Archive">
                        {archivingId === doc.id ? <Loader2 size={14} className="animate-spin" /> : <Archive size={14} />}
                    </button>
                  </>
                )}
                <button onClick={() => handleDeleteDocument(doc.id)} className="p-1.5 hover:bg-red-500/20 rounded-lg text-red-500/70 hover:text-red-500 transition-colors" title={t('documentsPanel.delete')}>
                  <Trash size={14} />
                </button>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default DocumentsPanel;