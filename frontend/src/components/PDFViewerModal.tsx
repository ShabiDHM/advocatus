// FILE: /home/user/advocatus-frontend/src/components/PDFViewerModal.tsx

// PHOENIX PROTOCOL CURE: Removed unused 'useCallback' import.
import React, { useState, useEffect } from 'react';
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
  // PHOENIX PROTOCOL CURE: Renamed prop to avoid conflict with the global 'document' object.
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
        const blob = await apiService.getOriginalDocument(caseId, documentData.id);
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
  }, [caseId, documentData.id, t]);

  const handleDownload = () => {
    if (fileUrl) {
      // PHOENIX PROTOCOL CURE: Use the global 'window.document' to avoid ambiguity.
      const link = window.document.createElement('a');
      link.href = fileUrl;
      link.download = documentData.file_name;
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
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
            <h2 className="text-lg font-bold text-text-primary truncate" title={documentData.file_name}>
              {documentData.file_name}
            </h2>
            <div className="flex items-center gap-4">
              {fileUrl && (
                  <button onClick={handleDownload} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors" title={t('pdfViewer.download')}>
                      <Download size={20} />
                  </button>
              )}
              <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors" title={t('pdfViewer.close')}>
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
                    // PHOENIX PROTOCOL CURE: Prefix unused parameter with an underscore.
                    onLoadError={(_err) => setError(t('pdfViewer.errorLoad'))}
                    loading=""
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
                {/* PHOENIX PROTOCOL CURE: Manually construct the string to satisfy the simple 't' function type. */}
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