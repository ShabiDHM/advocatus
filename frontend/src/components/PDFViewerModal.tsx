// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - PDF VIEWER V3.0 (PERFORMANCE & UI UPGRADE)
// 1. UPGRADE: Replaced 'react-pdf' with professional '@react-pdf-viewer' library.
// 2. FEATURE: Restored thumbnail sidebar ("Minimizer") using defaultLayoutPlugin.
// 3. PERFORMANCE: Fixes "extra spinning" by using a more optimized engine.

import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { apiService, API_V1_URL } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader, AlertTriangle, Download, RefreshCw } from 'lucide-react';
import { TFunction } from 'i18next';

// PHOENIX: Import the new viewer and layout components
import { Viewer, Worker } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';

// PHOENIX: Import styles for the new viewer
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';

// The worker URL is critical for the new library
const workerUrl = `https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js`;

interface PDFViewerModalProps {
  documentData: Document;
  caseId?: string; 
  onClose: () => void;
  t: TFunction; 
  directUrl?: string | null; 
  isAuth?: boolean;
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ documentData, caseId, onClose, t, directUrl, isAuth = false }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  // Create the layout plugin instance
  const defaultLayoutPluginInstance = defaultLayoutPlugin();

  useEffect(() => {
    const fetchAndSetUrl = async () => {
        setIsLoading(true);
        setError(null);
        try {
            let blob: Blob;
            const token = apiService.getToken();
            
            // Determine the URL to fetch from
            const urlToFetch = directUrl 
                ? directUrl 
                : `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/preview`;

            const headers: Record<string, string> = {};
            if (isAuth && token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            const response = await fetch(urlToFetch, { headers });
            if (!response.ok) {
                // If preview fails, try original for non-direct URLs
                if (!directUrl && caseId) {
                    const originalUrl = `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/original`;
                    const originalResponse = await fetch(originalUrl, { headers });
                    if (!originalResponse.ok) throw new Error('Failed to fetch original document');
                    blob = await originalResponse.blob();
                } else {
                    throw new Error('Failed to fetch document');
                }
            } else {
                blob = await response.blob();
            }

            // Create a blob URL for the viewer
            const blobUrl = URL.createObjectURL(blob);
            setFileUrl(blobUrl);
        } catch (err) {
            console.error("Viewer Error:", err);
            setError(t('pdfViewer.errorFetch', 'Gabim gjatë ngarkimit të dokumentit'));
        } finally {
            setIsLoading(false);
        }
    };
    
    fetchAndSetUrl();

    // Cleanup blob URL on component unmount
    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [caseId, documentData.id, directUrl, isAuth, t]);

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
        if (fileUrl) {
            const link = document.createElement('a');
            link.href = fileUrl;
            link.download = documentData.file_name;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    } catch (e) { console.error(e); } finally { setIsDownloading(false); }
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-400">
          <Loader className="animate-spin h-8 w-8 mb-2 text-primary-start" />
          <span>{t('pdfViewer.loading', 'Duke hapur dokumentin...')}</span>
        </div>
      );
    }

    if (error || !fileUrl) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
          <AlertTriangle className="h-12 w-12 text-red-400 mb-4" />
          <p className="text-red-300 mb-6">{error}</p>
          <button onClick={() => window.location.reload()} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white flex items-center gap-2">
            <RefreshCw size={16} /> {t('caseView.tryAgain', 'Provo Përsëri')}
          </button>
        </div>
      );
    }
    
    // PHOENIX: The new Viewer component
    return (
        <Worker workerUrl={workerUrl}>
            <div className="h-full w-full">
                <Viewer 
                    fileUrl={fileUrl} 
                    plugins={[defaultLayoutPluginInstance]}
                    theme="dark"
                />
            </div>
        </Worker>
    );
  };

  const modalContent = (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }} 
        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-0" 
        onClick={onClose}
      >
        <motion.div 
            initial={{ scale: 0.95, opacity: 0 }} 
            animate={{ scale: 1, opacity: 1 }} 
            exit={{ scale: 0.95, opacity: 0 }} 
            className="bg-[#1a1a1a] w-full h-full sm:max-w-6xl sm:max-h-[95vh] rounded-none sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-white/10" 
            onClick={(e) => e.stopPropagation()}
        >
          {/* PHOENIX: Custom styles to override viewer theme */}
          <style>{`
            .rpv-core__viewer { background-color: #1a1a1a !important; border: none !important; }
            .rpv-core__inner-pages { background-color: #2a2a2a !important; }
            .rpv-toolbar { background-color: #101010 !important; border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important; }
            .rpv-toolbar__button { color: #d1d5db !important; }
            .rpv-toolbar__button:hover { background-color: rgba(255, 255, 255, 0.1) !important; }
            .rpv-default-layout__sidebar { background-color: #101010 !important; border-right: 1px solid rgba(255, 255, 255, 0.1) !important; }
            .rpv-default-layout__thumbnail-item--selected { border: 2px solid #6366f1 !important; }
          `}</style>

          <header className="flex items-center justify-between p-3 sm:p-4 bg-[#101010] border-b border-white/10 z-20 shrink-0">
            <div className="flex items-center gap-3 min-w-0 flex-1">
                <h2 className="text-sm sm:text-lg font-bold text-gray-200 truncate">{documentData.file_name}</h2>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button onClick={handleDownloadOriginal} disabled={isDownloading} className="p-2 sm:px-4 sm:py-2 text-gray-200 bg-primary-start/20 hover:bg-primary-start hover:text-white rounded-lg transition-colors border border-primary-start/30 flex items-center gap-2">
                  {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />}
                  <span className="hidden sm:inline text-sm font-medium">{t('pdfViewer.downloadOriginalShort', 'Shkarko')}</span>
              </button>
              <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"><X size={24} /></button>
            </div>
          </header>
          
          <div className="flex-grow relative bg-[#2a2a2a] overflow-hidden">
              {renderContent()}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default PDFViewerModal;