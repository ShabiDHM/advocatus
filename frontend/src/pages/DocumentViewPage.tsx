// FILE: src/pages/DocumentViewPage.tsx
// PHOENIX PROTOCOL - DOCUMENT VIEW V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, border-main, text-text-primary, text-text-secondary, text-text-muted.
// 2. Preserved all functionality.
// 3. Consistent with other pages.

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Document } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import moment from 'moment';
import { motion } from 'framer-motion';
import { FileText, Download, Clock, Zap, ArrowLeft, Loader2 } from 'lucide-react';

const DocumentViewPage: React.FC = () => {
  const { t } = useTranslation();
  const { caseId, documentId } = useParams<{ caseId: string; documentId: string }>();
  
  const [docDetails, setDocDetails] = useState<Document | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  const fetchData = useCallback(async () => {
    if (!caseId || !documentId) {
      setError(t('documentView.missingIdError'));
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const metadata = await apiService.getDocument(caseId, documentId);
      setDocDetails(metadata);
      
      const isReady = metadata.status === 'READY' || metadata.status === 'COMPLETED';

      if (isReady) {
        const contentResponse = await apiService.getDocumentContent(caseId, documentId);
        setContent(contentResponse.text);
      } else {
        setContent(null);
      }
    } catch (e: any) {
      console.error("[DocumentView] Fetching error:", e);
      setError(e.message || t('documentView.loadFailedError'));
    } finally {
      setIsLoading(false);
    }
  }, [caseId, documentId, t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDownload = async () => {
    if (!caseId || !documentId || !docDetails) return;
    setIsDownloading(true);
    try {
      const blob = await apiService.downloadDocumentReport(caseId, documentId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${docDetails.file_name}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
    } finally {
      setIsDownloading(false);
    }
  };
  
  const getStatusInfo = (status: Document['status']) => {
    const s = status ? status.toUpperCase() : 'PENDING';
    switch (s) {
      case 'READY':
      case 'COMPLETED':
        return { color: 'bg-success-start/10 text-success-start border border-success-start/20', icon: <Zap size={16} />, label: t('documentView.statusReady') };
      case 'PENDING':
        return { color: 'bg-warning-start/10 text-warning-start border border-warning-start/20', icon: <Clock size={16} />, label: t('documentView.statusPending') };
      case 'FAILED':
        return { color: 'bg-danger-start/10 text-danger-start border border-danger-start/20', icon: <Zap size={16} />, label: t('documentView.statusFailed') };
      default:
        return { color: 'bg-surface/30 text-text-secondary border border-main', icon: <FileText size={16} />, label: status };
    }
  };

  if (isLoading) return (
    <div className="flex items-center justify-center h-[calc(100vh-64px)] bg-canvas">
      <Loader2 className="animate-spin h-12 w-12 text-primary-start" />
    </div>
  );
  
  if (error || !docDetails) return (
    <div className="text-danger-start text-center py-20 glass-panel rounded-2xl mx-4 border border-main">
      {error || t('documentView.notFound')}
    </div>
  );

  const statusInfo = getStatusInfo(docDetails.status);
  const isProcessed = docDetails.status.toUpperCase() === 'READY' || docDetails.status.toUpperCase() === 'COMPLETED';

  return (
    <motion.div 
        className="space-y-6 h-full p-1 bg-canvas" 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        transition={{ duration: 0.3 }}
    >
      {/* Header - Glass Style */}
      <div className="glass-panel p-6 rounded-2xl border border-main flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 sm:gap-0">
        <div className="flex flex-col w-full sm:w-auto">
            <Link to={`/case/${caseId}`} className="text-sm text-text-secondary hover:text-text-primary transition-colors mb-2 flex items-center space-x-2 group">
              <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" /> <span>{t('documentView.backToCase')}</span>
            </Link>
            <h1 className="text-2xl sm:text-3xl font-bold text-text-primary flex items-center space-x-3 break-all">
              <div className="p-2 bg-primary-start/20 rounded-lg">
                <FileText className="flex-shrink-0 h-6 w-6 sm:h-8 sm:w-8 text-primary-start" /> 
              </div>
              <span className="truncate">{docDetails.file_name}</span>
            </h1>
        </div>
        
        <div className="flex items-center space-x-3 w-full sm:w-auto justify-between sm:justify-end">
            <span className={`text-xs sm:text-sm font-bold px-3 py-1.5 rounded-lg flex items-center space-x-1.5 ${statusInfo.color}`}>
              {statusInfo.icon} <span>{statusInfo.label}</span>
            </span>
            <motion.button 
                onClick={handleDownload}
                disabled={isDownloading}
                className="btn-secondary text-white font-bold py-2.5 px-5 rounded-xl transition-all duration-300 shadow-lg disabled:opacity-50 flex items-center justify-center hover:-translate-y-0.5"
                whileTap={{ scale: 0.95 }}
                title={t('documentView.exportPdfTooltip')}
            >
                {isDownloading ? <Loader2 className="animate-spin h-5 w-5" /> : <Download size={20} />}
            </motion.button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100%-140px)]">
        {/* Sidebar: Details & Summary */}
        <div className="col-span-1 space-y-6 overflow-y-auto custom-scrollbar pr-1">
            <div className="glass-panel p-6 rounded-2xl border border-main">
                <h3 className="text-lg font-bold text-text-primary mb-4 border-b border-main pb-2">{t('documentView.details')}</h3>
                <div className="space-y-3">
                    <p className="text-sm text-text-secondary break-words flex flex-col">
                        <span className="text-xs font-bold uppercase tracking-wider text-text-muted mb-1">{t('documentView.fileName')}</span>
                        <span className="text-text-primary font-medium">{docDetails.file_name}</span>
                    </p>
                    <p className="text-sm text-text-secondary flex flex-col">
                        <span className="text-xs font-bold uppercase tracking-wider text-text-muted mb-1">{t('documentView.uploadedAt')}</span>
                        <span className="text-text-primary font-medium">{moment(docDetails.created_at).format('DD MMM YYYY, HH:mm')}</span>
                    </p>
                    <p className="text-sm text-text-secondary flex flex-col">
                        <span className="text-xs font-bold uppercase tracking-wider text-text-muted mb-1">{t('documentView.fileType')}</span>
                        <span className="text-text-primary font-medium uppercase">{docDetails.mime_type?.split('/')[1] || 'FILE'}</span>
                    </p>
                </div>
            </div>
            
            <div className="glass-panel p-6 rounded-2xl flex-1 border border-main">
                <h3 className="text-lg font-bold text-text-primary mb-4 border-b border-main pb-2">{t('documentView.summary')}</h3>
                <div className="min-h-[150px] text-text-secondary text-sm sm:text-base leading-relaxed">
                    {isProcessed && docDetails.summary ? (
                        <span className="italic">{docDetails.summary}</span>
                    ) : (
                        <span className="text-text-muted italic flex items-center justify-center h-32 bg-surface/20 rounded-xl border border-dashed border-main">
                            {isProcessed ? t('documentView.summaryPlaceholder') : t('documentView.notProcessed')}
                        </span>
                    )}
                </div>
            </div>
        </div>

        {/* Content Area */}
        <div className="col-span-1 lg:col-span-2 h-[500px] lg:h-full glass-panel rounded-2xl overflow-hidden flex flex-col border border-main">
            <div className="p-4 border-b border-main bg-surface/20 backdrop-blur-sm">
                <h3 className="text-lg font-bold text-text-primary">{t('documentView.extractedContent')}</h3>
            </div>
            <div className="p-6 overflow-y-auto flex-1 custom-scrollbar bg-canvas/20">
                <div className="text-text-primary whitespace-pre-wrap font-mono text-xs sm:text-sm leading-relaxed">
                    {content ? content : (
                        <div className="flex flex-col items-center justify-center h-full text-text-secondary opacity-50 py-20">
                            {isProcessed ? (
                                <>
                                    <FileText size={48} className="mb-4 text-text-muted" />
                                    <p>{t('documentView.noContentFound')}</p>
                                </>
                            ) : (
                                <>
                                    <Loader2 size={48} className="mb-4 animate-spin text-primary-start" />
                                    <p>{t('documentView.contentProcessing')}</p>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
      </div>
    </motion.div>
  );
};

export default DocumentViewPage;