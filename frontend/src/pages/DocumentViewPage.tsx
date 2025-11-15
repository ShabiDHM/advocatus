// FILE: /home/user/advocatus-frontend/src/pages/DocumentViewPage.tsx


import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Document } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import moment from 'moment';
import { motion } from 'framer-motion';
import { FileText, Download, Clock, Zap, ArrowLeft } from 'lucide-react';

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
      
      const isReady = metadata.status === 'READY';

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
    switch (status.toUpperCase()) {
      case 'READY':
        return { color: 'bg-success-start text-white', icon: <Zap size={16} />, label: t('documentView.statusReady') };
      case 'PENDING':
        return { color: 'bg-yellow-500 text-white', icon: <Clock size={16} />, label: t('documentView.statusPending') };
      case 'FAILED':
        return { color: 'bg-red-500 text-white', icon: <Zap size={16} />, label: t('documentView.statusFailed') };
      default:
        return { color: 'bg-gray-500 text-white', icon: <FileText size={16} />, label: status };
    }
  };


  if (isLoading) return <div className="text-center py-10 text-text-primary">{t('loading')}...</div>;
  if (error || !docDetails) return <div className="text-red-500 text-center py-10">{error || t('documentView.notFound')}</div>;

  const statusInfo = getStatusInfo(docDetails.status);
  const isProcessed = docDetails.status.toUpperCase() === 'READY';

  return (
    <motion.div className="space-y-6 p-6 bg-background-dark rounded-2xl shadow-xl h-full overflow-y-auto" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.3 }}>
      <div className="flex justify-between items-start border-b border-glass-edge pb-4">
        <div className="flex flex-col">
            <Link to={`/case/${caseId}`} className="text-sm text-primary-start hover:text-primary-end transition-colors mb-2 flex items-center space-x-2">
              <ArrowLeft size={16} /> <span>{t('documentView.backToCase')}</span>
            </Link>
            <h1 className="text-3xl font-bold text-text-primary flex items-center space-x-3">
              <FileText size={30} /> 
              <span>{docDetails.file_name}</span>
            </h1>
        </div>
        <div className="flex items-center space-x-3 flex-shrink-0">
            <span className={`text-sm font-semibold px-3 py-1 rounded-full flex items-center space-x-1 ${statusInfo.color}`}>
              {statusInfo.icon} <span>{statusInfo.label}</span>
            </span>
            <motion.button 
                onClick={handleDownload}
                disabled={isDownloading}
                className="bg-secondary-start text-white font-semibold py-2 px-4 rounded-xl transition-all duration-300 shadow-lg glow-secondary disabled:opacity-50"
                whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
                title={t('documentView.exportPdfTooltip')}
            >
                {isDownloading ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : <Download size={18} />}
            </motion.button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-1 space-y-4">
            <h3 className="text-lg font-semibold text-text-primary">{t('documentView.details')}</h3>
            <div className="bg-background-light/50 p-4 rounded-xl space-y-2">
                <p className="text-sm text-text-secondary"><strong>{t('documentView.fileName')}:</strong> <span className="text-text-primary">{docDetails.file_name}</span></p>
                <p className="text-sm text-text-secondary"><strong>{t('documentView.uploadedAt')}:</strong> <span className="text-text-primary">{moment(docDetails.created_at).format('YYYY-MM-DD HH:mm')}</span></p>
                <p className="text-sm text-text-secondary"><strong>{t('documentView.fileType')}:</strong> <span className="text-text-primary">{docDetails.mime_type}</span></p>
                {/* --- PHOENIX PROTOCOL FIX: Document ID field has been removed --- */}
            </div>
            
            <h3 className="text-lg font-semibold text-text-primary">{t('documentView.summary')}</h3>
            <div className="bg-background-light/50 p-4 rounded-xl min-h-[150px] text-text-primary">
                {/* --- PHOENIX PROTOCOL FIX: Correctly display summary or placeholder --- */}
                {isProcessed && docDetails.summary ? (
                    <span className="italic">{docDetails.summary}</span>
                ) : (
                    <span className="text-text-secondary italic">
                        {isProcessed ? t('documentView.summaryPlaceholder') : t('documentView.notProcessed')}
                    </span>
                )}
            </div>
        </div>

        <div className="col-span-2 space-y-4">
            <h3 className="text-lg font-semibold text-text-primary">{t('documentView.extractedContent')}</h3>
            <div className="bg-background-light/50 p-4 rounded-xl h-[70vh] overflow-y-auto text-text-primary whitespace-pre-wrap font-mono text-sm">
                {content ? content : (
                    <div className="text-center text-text-secondary py-10">
                        {isProcessed ? t('documentView.noContentFound') : t('documentView.contentProcessing')}
                    </div>
                )}
            </div>
        </div>
      </div>
    </motion.div>
  );
};

export default DocumentViewPage;