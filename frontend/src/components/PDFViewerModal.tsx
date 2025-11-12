// FILE: /home/user/advocatus-frontend/src/components/PDFViewerModal.tsx

import React, { useState, useEffect, useCallback } from 'react';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

import { apiService } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader, AlertTriangle, ChevronLeft, ChevronRight, Download } from 'lucide-react';

// Configure the worker to load PDF.js from a CDN
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PDFViewerModalProps {
  document: Document;
  caseId: string;
  onClose: () => void;
  t: (key: string) => string;
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ document, caseId, onClose, t }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
  };

  const goToPrevPage = () => setPageNumber(prevPageNumber => Math.max(prevPageNumber - 1, 1));
  const goToNextPage = () => setPageNumber(prevPageNumber => Math.min(prevPageNumber + 1, numPages || 1));

  useEffect(() => {
    const fetchDocument = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const blob = await apiService.getOriginalDocument(caseId, document.id);
        const url = URL.createObjectURL(blob);
        setFileUrl(url);
      } catch (err) {
        console.error("Failed to fetch original document:", err);
        setError(t('pdfViewer.errorFetch'));
      } finally {
        setIsLoading(false);
      }
    };

    fetchDocument();

    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [caseId, document.id, t]);

  const handleDownload = () => {
    if (fileUrl) {
      const link = document.createElement('a');
      link.href = fileUrl;
      link.download = document.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
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
          {/* Header */}
          <header className="flex items-center justify-between p-4 bg-background-light border-b border-glass-edge flex-shrink-0">
            <h2 className="text-lg font-bold text-text-primary truncate" title={document.file_name}>
              {document.file_name}
            </h2>
            <div className="flex items-center gap-4">
              {fileUrl && (
                  <button onClick={handleDownload} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors">
                      <Download size={20} />
                  </button>
              )}
              <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors">
                <X size={20} />
              </button>
            </div>
          </header>

          {/* Body (Viewer) */}
          <div className="flex-grow relative bg-black/20 overflow-auto">
            {isLoading && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-text-secondary">
                <Loader className="animate-spin h-8 w-8 mb-2" />
                <p>{t('pdfViewer.loading')}</p>
              </div>
            )}
            {error && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-red-400">
                <AlertTriangle className="h-8 w-8 mb-2" />
                <p>{error}</p>
              </div>
            )}
            {fileUrl && !error && (
              <div className="p-4 flex justify-center">
                 <PdfDocument
                    file={fileUrl}
                    onLoadSuccess={onDocumentLoadSuccess}
                    onLoadError={(err) => setError(t('pdfViewer.errorLoad'))}
                    loading="" // Handled by our own loader
                 >
                    <Page pageNumber={pageNumber} width={800} />
                 </PdfDocument>
              </div>
            )}
          </div>

          {/* Footer (Controls) */}
          {numPages && numPages > 1 && (
            <footer className="flex items-center justify-center p-3 bg-background-light border-t border-glass-edge flex-shrink-0">
              <div className="flex items-center gap-4 text-text-primary">
                <button onClick={goToPrevPage} disabled={pageNumber <= 1} className="p-2 disabled:opacity-50 hover:bg-white/10 rounded-full transition-colors">
                  <ChevronLeft size={20} />
                </button>
                <span>{t('pdfViewer.page', { pageNumber, numPages })}</span>
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