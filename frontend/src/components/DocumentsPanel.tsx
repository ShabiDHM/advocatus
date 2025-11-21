// FILE: src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL - LINT FIX
// 1. CLEANUP: Removed unused 'useMemo' import.
// 2. UI: Maintains the polished badge style and responsive layout.

import React, { useState, useRef } from 'react';
import { Document, Finding, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { FolderOpen, Eye, Trash, Plus, Loader2 } from 'lucide-react';
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
}

const DocumentsPanel: React.FC<DocumentsPanelProps> = ({
  caseId,
  documents,
  t,
  connectionStatus,
  reconnect,
  onDocumentDeleted,
  onDocumentUploaded,
  onViewOriginal
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const connectionStatusText = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return t('documentsPanel.statusConnected');
      case 'CONNECTING': return t('documentsPanel.statusConnecting');
      case 'DISCONNECTED': return t('documentsPanel.statusDisconnected');
      case 'ERROR': return t('documentsPanel.statusError');
      default: return status;
    }
  };

  const statusColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'CONNECTING': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
      default: return 'bg-red-500/10 text-red-400 border-red-500/20';
    }
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const responseData = await apiService.uploadDocument(caseId, file);
      
      const rawData = responseData as any;
      const newDoc: Document = {
          ...responseData,
          id: responseData.id || rawData._id, 
          status: 'PENDING' 
      };

      if (!newDoc.id) throw new Error("Upload succeeded but ID is missing.");

      onDocumentUploaded(newDoc);
      
    } catch (error: any) {
      setUploadError(t('documentsPanel.uploadFailed') + `: ${error.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDocument = async (documentId: string | undefined) => {
    if (!documentId) return;
    if (!window.confirm(t('documentsPanel.confirmDelete'))) return;
    try {
      const response = await apiService.deleteDocument(caseId, documentId);
      onDocumentDeleted(response);
    } catch (error) {
      console.error("Failed to delete document:", error);
      alert(t('documentsPanel.deleteFailed'));
    }
  };

  const getStatusInfo = (status: Document['status']) => {
    const s = status ? status.toUpperCase() : 'PENDING';
    switch (s) {
      case 'READY': 
      case 'COMPLETED': 
        return { color: 'bg-success-start/20 text-success-start', label: t('documentsPanel.statusCompleted') };
      case 'PENDING': 
        return { color: 'bg-accent-start/20 text-accent-start', label: t('documentsPanel.statusPending') };
      case 'FAILED': 
        return { color: 'bg-red-500/20 text-red-500', label: t('documentsPanel.statusFailed') };
      default: 
        return { color: 'bg-background-light/20 text-text-secondary', label: status };
    }
  };

  return (
    <div className="documents-panel bg-background-dark p-4 sm:p-6 rounded-2xl shadow-xl flex flex-col h-full">
      {/* Header */}
      <div className="flex flex-row justify-between items-center border-b border-background-light/50 pb-3 mb-4 flex-shrink-0 gap-2">
        <div className="flex items-center gap-2 sm:gap-4 min-w-0 overflow-hidden">
            <h2 className="text-lg sm:text-xl font-bold text-text-primary truncate">{t('documentsPanel.title')}</h2>
            
            <div className={`text-[10px] sm:text-xs px-2 sm:px-3 py-1 rounded-full border flex items-center gap-1.5 transition-all whitespace-nowrap ${statusColor(connectionStatus)}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${connectionStatus === 'CONNECTED' ? 'bg-green-400' : 'bg-red-400'}`}></span>
                {connectionStatusText(connectionStatus)}
                {connectionStatus !== 'CONNECTED' && (
                  <motion.button onClick={reconnect} className="ml-1 underline hover:text-white" whileHover={{ scale: 1.05 }}>
                    {t('documentsPanel.reconnect')}
                  </motion.button>
                )}
            </div>
        </div>

        <div className="flex-shrink-0">
          <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" disabled={isUploading} />
          <motion.button
            onClick={() => fileInputRef.current?.click()}
            className="h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center rounded-xl transition-all duration-300 shadow-lg glow-primary bg-gradient-to-r from-primary-start to-primary-end text-white"
            title={t('documentsPanel.uploadDocument')} 
            disabled={isUploading} 
            whileHover={{ scale: 1.05 }} 
            whileTap={{ scale: 0.95 }} 
          >
            {isUploading ? <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" /> : <Plus className="h-5 w-5 sm:h-6 sm:w-6" />}
          </motion.button>
        </div>
      </div>

      {uploadError && (<div className="p-3 text-xs sm:text-sm text-red-100 bg-red-700 rounded-lg mb-4">{uploadError}</div>)}

      <div className="space-y-3 flex-1 overflow-y-auto overflow-x-hidden pr-2 max-h-[250px] sm:max-h-[20rem]">
        {(documents.length === 0 && !isUploading) && (
          <div className="text-text-secondary text-center py-5">
            <FolderOpen className="w-12 h-12 sm:w-16 sm:h-16 text-text-secondary/50 mx-auto mb-4" />
            <p className="text-sm sm:text-base">{t('documentsPanel.noDocuments')}</p>
          </div>
        )}
        {documents.map((doc) => {
          const statusInfo = getStatusInfo(doc.status);
          const isReady = doc.status.toUpperCase() === 'READY' || doc.status.toUpperCase() === 'COMPLETED';
          
          return (
            <motion.div
              key={doc.id} layout="position"
              className="flex items-center justify-between p-3 bg-background-light/50 backdrop-blur-sm border border-glass-edge rounded-xl"
              initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -50 }}
            >
              <div className="truncate pr-2 min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-sm font-medium text-text-primary truncate">{doc.file_name}</p>
                </div>
                <p className="text-[10px] sm:text-xs text-text-secondary truncate">{t('documentsPanel.uploaded')}: {moment(doc.created_at).format('YYYY-MM-DD HH:mm')}</p>
              </div>
              
              <div className="flex items-center space-x-2 flex-shrink-0">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold hidden sm:inline-block ${statusInfo.color}`}>
                  {statusInfo.label}
                </span>
                <span className={`w-2 h-2 rounded-full sm:hidden ${statusInfo.color.split(' ')[0]}`} title={statusInfo.label}></span>

                {isReady && (
                  <div className="flex items-center space-x-1 sm:space-x-2">
                    <motion.button onClick={() => onViewOriginal(doc)} title={t('documentsPanel.viewOriginal')} className="text-primary-start hover:text-primary-end p-1" whileHover={{ scale: 1.2 }}>
                      <Eye size={16} />
                    </motion.button>
                  </div>
                )}
                <motion.button onClick={() => handleDeleteDocument(doc.id)} title={t('documentsPanel.delete')} className="text-red-500 hover:text-red-400 p-1" whileHover={{ scale: 1.2 }}>
                  <Trash size={16} />
                </motion.button>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default DocumentsPanel;