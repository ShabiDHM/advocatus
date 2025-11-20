// FILE: src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL - UI ALIGNMENT
// 1. Connection Badge: Now identical to ChatPanel (Pill shape, green bg, glow).
// 2. Upload Button: Converted to a clean Icon-only button (Plus icon).
// 3. Layout: Adjusted header alignment to accommodate the new button styles.

import React, { useState, useRef, useMemo } from 'react';
import { Document, Finding, ConnectionStatus, DeletedDocumentResponse } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { FolderOpen, Eye, Repeat, Trash, Plus, Loader2 } from 'lucide-react';
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
  findings,
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

  // PHOENIX UI UPDATE: Matched style with ChatPanel
  const statusColor = (status: ConnectionStatus) => {
    switch (status) {
      case 'CONNECTED': return 'bg-success-start text-white glow-accent';
      case 'CONNECTING': return 'bg-accent-start text-white';
      case 'DISCONNECTED': return 'bg-red-500 text-white';
      case 'ERROR': return 'bg-red-500 text-white';
      default: return 'bg-background-light text-text-secondary';
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
  
  const handleReanalyze = async (documentId: string) => {
      alert(t('documentsPanel.reanalyzeAlert', { documentId }));
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

  const docHasFindings = useMemo(() => {
    const map = new Map<string, boolean>();
    if (Array.isArray(findings)) {
      findings.forEach(f => {
        if (f && f.document_id) {
            map.set(String(f.document_id), true);
        }
      });
    }
    return map;
  }, [findings]);

  return (
    <div className="documents-panel bg-background-dark p-6 rounded-2xl shadow-xl flex flex-col h-full">
      {/* Header */}
      <div className="flex flex-row justify-between items-center border-b border-background-light/50 pb-3 mb-4 flex-shrink-0 gap-2">
        <div className="flex items-center gap-4 min-w-0">
            <h2 className="text-xl font-bold text-text-primary truncate">{t('documentsPanel.title')}</h2>
            
            {/* PHOENIX UI UPDATE: Connection Badge (Identical to ChatPanel) */}
            <div className={`text-xs font-semibold px-3 py-1 rounded-full flex items-center transition-all whitespace-nowrap ${statusColor(connectionStatus)}`}>
                {connectionStatusText(connectionStatus)}
                {connectionStatus !== 'CONNECTED' && (
                  <motion.button onClick={reconnect} className="ml-2 underline text-white/80 hover:text-white" whileHover={{ scale: 1.05 }}>
                    {t('documentsPanel.reconnect')}
                  </motion.button>
                )}
            </div>
        </div>

        {/* PHOENIX UI UPDATE: Icon-Only Upload Button */}
        <div className="flex-shrink-0">
          <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" disabled={isUploading} />
          <motion.button
            onClick={() => fileInputRef.current?.click()}
            className="h-10 w-10 flex items-center justify-center rounded-xl transition-all duration-300 shadow-lg glow-primary bg-gradient-to-r from-primary-start to-primary-end text-white"
            title={t('documentsPanel.uploadDocument')} // Tooltip
            disabled={isUploading} 
            whileHover={{ scale: 1.05 }} 
            whileTap={{ scale: 0.95 }} 
          >
            {isUploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Plus className="h-6 w-6" />}
          </motion.button>
        </div>
      </div>

      {uploadError && (<div className="p-3 text-sm text-red-100 bg-red-700 rounded-lg mb-4">{uploadError}</div>)}

      <div className="space-y-3 flex-1 overflow-y-auto overflow-x-hidden pr-2 max-h-[20rem]">
        {(documents.length === 0 && !isUploading) && (
          <div className="text-text-secondary text-center py-5">
            <FolderOpen className="w-16 h-16 text-text-secondary/50 mx-auto mb-4" />
            {t('documentsPanel.noDocuments')}
          </div>
        )}
        {documents.map((doc) => {
          const statusInfo = getStatusInfo(doc.status);
          const hasFindings = docHasFindings.get(doc.id);
          const isReady = doc.status.toUpperCase() === 'READY' || doc.status.toUpperCase() === 'COMPLETED';
          
          return (
            <motion.div
              key={doc.id} layout="position"
              className="flex items-center justify-between p-3 bg-background-light/50 backdrop-blur-sm border border-glass-edge rounded-xl"
              initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -50 }}
            >
              <div className="truncate pr-4 min-w-0 flex-1">
                <p className="text-sm font-medium text-text-primary flex items-center truncate">
                    <span className="truncate">{doc.file_name}</span>
                    {hasFindings && <span className="ml-2 text-xs text-primary-end bg-primary-start/20 px-2 py-0.5 rounded-full flex-shrink-0">Findings</span>}
                </p>
                <p className="text-xs text-text-secondary">{t('documentsPanel.uploaded')}: {moment(doc.created_at).format('YYYY-MM-DD HH:mm')}</p>
              </div>
              <div className="flex items-center space-x-2 flex-shrink-0">
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${statusInfo.color}`}>
                  {statusInfo.label}
                </span>
                {isReady && (
                  <div className="flex items-center space-x-2">
                    <motion.button onClick={() => onViewOriginal(doc)} title={t('documentsPanel.viewOriginal')} className="text-primary-start hover:text-primary-end" whileHover={{ scale: 1.2 }}>
                      <Eye size={16} />
                    </motion.button>
                    <motion.button onClick={() => handleReanalyze(doc.id)} title={t('documentsPanel.reanalyze')} className="text-accent-start hover:text-accent-end" whileHover={{ scale: 1.2 }}>
                      <Repeat size={16} />
                    </motion.button>
                  </div>
                )}
                <motion.button onClick={() => handleDeleteDocument(doc.id)} title={t('documentsPanel.delete')} className="text-red-500 hover:text-red-400" whileHover={{ scale: 1.2 }}>
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