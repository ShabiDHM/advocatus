// FILE: /home/user/advocatus-frontend/src/components/DocumentsPanel.tsx
// PHOENIX PROTOCOL PHASE VIII - MODIFICATION 10.0 (Type Unification and Finalization)
// CORRECTION: Unified the two separate prop interfaces into a single, definitive
// 'DocumentsPanelProps'. This ensures the component's signature is clear and that
// all required props, including 'findings', are correctly typed and expected,
// resolving the final TS2741 build error.

import React, { useState, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Document, Finding, ConnectionStatus } from '../data/types';
import { TFunction } from 'i18next';
import { apiService } from '../services/api';
import moment from 'moment';
import { FolderOpen, Eye, Repeat, Trash, FileText } from 'lucide-react';
import { motion } from 'framer-motion';

// Unified and definitive props interface
interface DocumentsPanelProps {
  caseId: string;
  documents: Document[];
  findings: Finding[];
  t: TFunction;
  onDocumentDeleted: (documentId: string) => void;
  onDocumentUploaded: (newDocument: Document) => void;
  onViewOriginal: (document: Document) => void;
  connectionStatus: ConnectionStatus;
  reconnect: () => void;
}

const MotionLink = motion(Link);

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

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      const responseData = await apiService.uploadDocument(caseId, file);
      const newDoc = { ...responseData, id: responseData.id || responseData._id };
      if (!newDoc.id) throw new Error("Upload succeeded but the server response was missing a document ID.");
      delete (newDoc as any)._id; // eslint-disable-line @typescript-eslint/no-explicit-any
      onDocumentUploaded(newDoc as Document);
    } catch (error: any) { // eslint-disable-line @typescript-eslint/no-explicit-any
      setUploadError(t('documentsPanel.uploadFailed') + `: ${error.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDocument = async (documentId: string | undefined) => {
    if (typeof documentId !== 'string' || documentId.trim() === '') return;
    if (!window.confirm(t('documentsPanel.confirmDelete'))) return;
    try {
      await apiService.deleteDocument(caseId, documentId);
      onDocumentDeleted(documentId);
    } catch (error) {
      console.error("Failed to delete document:", error);
      alert(t('documentsPanel.deleteFailed'));
    }
  };
  
  const handleReanalyze = async (documentId: string) => {
      alert(t('documentsPanel.reanalyzeAlert', { documentId }));
  };

  const getStatusInfo = (status: Document['status']) => {
    switch (status.toUpperCase()) {
      case 'READY': return { color: 'bg-success-start/20 text-success-start', label: t('documentsPanel.statusCompleted') };
      case 'PENDING': return { color: 'bg-accent-start/20 text-accent-start', label: t('documentsPanel.statusPending') };
      case 'FAILED': return { color: 'bg-red-500/20 text-red-500', label: t('documentsPanel.statusFailed') };
      default: return { color: 'bg-background-light/20 text-text-secondary', label: status };
    }
  };

  const connectionColor = () => {
    switch (connectionStatus) {
      case 'CONNECTED': return 'bg-success-start';
      case 'CONNECTING': return 'bg-accent-start';
      case 'DISCONNECTED': return 'bg-red-500';
      case 'ERROR': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const docHasFindings = useMemo(() => {
    const map = new Map<string, boolean>();
    if (Array.isArray(findings)) {
      findings.forEach(f => {
        if (f && f.document_id) {
            map.set(f.document_id, true);
        }
      });
    }
    return map;
  }, [findings]);

  return (
    <div className="documents-panel bg-background-dark p-6 rounded-2xl shadow-xl flex flex-col h-full">
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 border-b border-background-light/50 pb-3 mb-4 flex-shrink-0">
        <h2 className="text-xl font-bold text-text-primary flex-shrink-0">{t('documentsPanel.title')}</h2>
        <div className="flex flex-wrap items-center justify-start sm:justify-end gap-3">
          <span className="flex items-center text-sm text-text-secondary">
            <span className={`h-2 w-2 rounded-full mr-2 ${connectionColor()}`}></span>
            {connectionStatusText(connectionStatus)}
            {connectionStatus !== 'CONNECTED' && (
              <motion.button onClick={reconnect} className="ml-2 text-primary-start hover:text-primary-end" whileHover={{ scale: 1.05 }}>
                {t('documentsPanel.reconnect')}
              </motion.button>
            )}
          </span>
          <input type="file" ref={fileInputRef} onChange={handleFileChange} className="hidden" disabled={isUploading} accept=".pdf,.docx,.txt" />
          <motion.button
            onClick={() => fileInputRef.current?.click()}
            className="text-white font-semibold py-2 px-3 sm:px-4 rounded-xl transition-all duration-300 shadow-lg glow-primary bg-gradient-to-r from-primary-start to-primary-end"
            disabled={isUploading} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} >
            {isUploading ? t('documentsPanel.uploading') : `+ ${t('documentsPanel.uploadDocument')}`}
          </motion.button>
        </div>
      </div>
      {uploadError && (<div className="p-3 text-sm text-red-100 bg-red-700 rounded-lg mb-4">{uploadError}</div>)}

      <div className="space-y-3 flex-1 overflow-y-auto overflow-x-hidden pr-2">
        {(documents.length === 0 && !isUploading) && (
          <div className="text-text-secondary text-center py-5">
            <FolderOpen className="w-16 h-16 text-text-secondary/50 mx-auto mb-4" />
            {t('documentsPanel.noDocuments')}
          </div>
        )}
        {documents.map((doc) => {
          const statusInfo = getStatusInfo(doc.status);
          const hasFindings = docHasFindings.get(doc.id);
          return (
            <motion.div
              key={doc.id} layout="position"
              className="flex items-center justify-between p-3 bg-background-light/50 backdrop-blur-sm border border-glass-edge rounded-xl"
              initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -50 }}
            >
              <div className="truncate pr-4">
                <p className="text-sm font-medium text-text-primary flex items-center">
                    {doc.file_name}
                    {hasFindings && <span className="ml-2 text-xs text-primary-end bg-primary-start/20 px-2 py-0.5 rounded-full">Findings</span>}
                </p>
                <p className="text-xs text-text-secondary">{t('documentsPanel.uploaded')}: {moment(doc.created_at).format('YYYY-MM-DD HH:mm')}</p>
              </div>
              <div className="flex items-center space-x-2 flex-shrink-0">
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${statusInfo.color}`}>
                  {statusInfo.label}
                </span>
                {(doc.status.toUpperCase() === 'READY') && (
                  <div className="flex items-center space-x-2">
                    <motion.button onClick={() => onViewOriginal(doc)} title={t('documentsPanel.viewOriginal')} className="text-blue-400 hover:text-blue-300" whileHover={{ scale: 1.2 }}>
                      <FileText size={16} />
                    </motion.button>
                    <MotionLink to={`/case/${caseId}/documents/${doc.id}`} title={t('documentsPanel.viewExtracted')} className="text-primary-start hover:text-primary-end" whileHover={{ scale: 1.2 }}>
                      <Eye size={16} />
                    </MotionLink>
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