// FILE: src/components/PDFViewerModal.tsx

import React, { useState, useEffect } from 'react';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { AxiosError } from 'axios';

import { apiService } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader, AlertTriangle, ChevronLeft, ChevronRight, Download, RefreshCw } from 'lucide-react';

// --- PHOENIX PROTOCOL CURE: VERCEL-OPTIMIZED PDF WORKER CONFIGURATION ---
// CORRECTION: The workerVersion has been updated to match the exact version
// required by the react-pdf library, as reported by the browser's runtime error.
// This resolves the "API version does not match Worker version" failure.
const configurePdfWorker = () => {
  // Use CDN version that matches the running react-pdf's pdfjs-dist dependency.
  const workerVersion = '5.4.296';
  const cdnWorkerUrl = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${workerVersion}/pdf.worker.min.js`;
  
  console.log(`Configuring PDF worker from CDN: ${cdnWorkerUrl}`);
  pdfjs.GlobalWorkerOptions.workerSrc = cdnWorkerUrl;
};

// Configure PDF worker on module load
configurePdfWorker();

interface PDFViewerModalProps {
  documentData: Document;
  caseId: string;
  onClose: () => void;
  t: (key: string) => string;
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ documentData, caseId, onClose, t }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [isDownloading, setIsDownloading] = useState(false);
  const [pdfLoadError, setPdfLoadError] = useState<string | null>(null);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
    setPdfLoadError(null);
  };

  const goToPrevPage = () => setPageNumber(prevPageNumber => Math.max(prevPageNumber - 1, 1));
  const goToNextPage = () => setPageNumber(prevPageNumber => Math.min(prevPageNumber + 1, numPages || 1));

  const fetchDocumentPreview = async () => {
    setIsLoading(true);
    setError(null);
    setPdfLoadError(null);
    
    if (fileUrl) {
      URL.revokeObjectURL(fileUrl);
      setFileUrl(null);
    }
    
    try {
      const blob = await apiService.getPreviewDocument(caseId, documentData.id);
      const url = URL.createObjectURL(blob);
      setFileUrl(url);
    } catch (err) {
      console.error("Failed to fetch document preview:", err);
      if ((err as AxiosError)?.response?.status === 404) {
        setError(t('pdfViewer.errorPreviewNotReady'));
      } else {
        setError(t('pdfViewer.errorFetch'));
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  useEffect(() => {
    fetchDocumentPreview();
    
    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [caseId, documentData.id, t]);

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
      const blob = await apiService.getOriginalDocument(caseId, documentData.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = documentData.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (downloadError) {
      console.error("Failed to download original document:", downloadError);
      setError(t('pdfViewer.errorDownload'));
    } finally {
      setIsDownloading(false);
    }
  };
  
  const renderErrorState = () => (
    <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-4">
      <AlertTriangle className="h-10 w-10 text-red-400 mb-4" />
      <p className="text-red-300 font-semibold mb-2">{t('pdfViewer.errorTitle')}</p>
      <p className="text-red-300/80 text-sm mb-6">{error || pdfLoadError}</p>
      {(error === t('pdfViewer.errorPreviewNotReady') || pdfLoadError) && (
        <button
          onClick={fetchDocumentPreview}
          className="px-4 py-2 bg-primary-start hover:bg-primary-end text-white rounded-md transition duration-200 flex items-center gap-2"
        >
          <RefreshCw size={16} />
          {t('caseView.tryAgain')}
        </button>
      )}
    </div>
  );

  const handlePdfLoadError = (err: Error) => {
    console.error("react-pdf onLoadError:", err);
    setPdfLoadError(t('pdfViewer.errorLoad'));
  };

  const handlePdfRenderError = (err: Error) => {
    console.error("react-pdf render error:", err);
    setPdfLoadError(t('pdfViewer.errorRender'));
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.9, y: 20 }}
          className="bg-background-main w-full h-full max-w-4xl max-h-[95vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-glass-edge"
          onClick={(e) => e.stopPropagation()}
        >
          <header className="flex items-center justify-between p-4 bg-background-light border-b border-glass-edge flex-shrink-0">
            <h2 className="text-lg font-bold text-text-primary truncate" title={documentData.file_name}>
              {documentData.file_name}
            </h2>
            <div className="flex items-center gap-4">
              <button 
                onClick={handleDownloadOriginal} 
                disabled={isDownloading} 
                className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors disabled:opacity-50" 
                title={t('pdfViewer.download')}
              >
                {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />}
              </button>
              <button 
                onClick={onClose} 
                className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors" 
                title={t('pdfViewer.close')}
              >
                <X size={20} />
              </button>
            </div>
          </header>

          <div className="flex-grow relative bg-black/20 overflow-auto">
            {isLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-text-secondary">
                <Loader className="animate-spin h-8 w-8 mb-2" />
                <p>{t('pdfViewer.loading')}</p>
              </div>
            )}
            {(error || pdfLoadError) && renderErrorState()}
            {fileUrl && !error && !pdfLoadError && (
              <div className="p-4 flex justify-center">
                <PdfDocument
                  file={fileUrl}
                  onLoadSuccess={onDocumentLoadSuccess}
                  onLoadError={handlePdfLoadError}
                  loading=""
                >
                  <Page 
                    pageNumber={pageNumber} 
                    width={800} 
                    onRenderError={handlePdfRenderError}
                    loading=""
                  />
                </PdfDocument>
              </div>
            )}
          </div>

          {numPages && numPages > 1 && !error && !pdfLoadError && (
            <footer className="flex items-center justify-center p-3 bg-background-light border-t border-glass-edge flex-shrink-0">
              <div className="flex items-center gap-4 text-text-primary">
                <button onClick={goToPrevPage} disabled={pageNumber <= 1} className="p-2 disabled:opacity-50 hover:bg-white/10 rounded-full transition-colors">
                  <ChevronLeft size={20} />
                </button>
                <span>{`${t('pdfViewer.pageLabel')} ${pageNumber} / ${numPages}`}</span>
                <button onClick={goToNextPage} disabled={pageNumber >= numPages} className="p-2 disabled:opacity-50 hover:bg-white/10 rounded-full transition-colors">
                  <ChevronRight size={20} />
                </button>
              </div>
            </footer>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default PDFViewerModal;