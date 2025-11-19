// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - CLEANED UNIVERSAL VIEWER
// 1. Removed unused imports (FileText, ImageIcon).
// 2. Zero TypeScript warnings.

import React, { useState, useEffect } from 'react';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader, AlertTriangle, ChevronLeft, ChevronRight, Download, RefreshCw } from 'lucide-react';
import pdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?url';

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;

interface PDFViewerModalProps {
  documentData: Document;
  caseId: string;
  onClose: () => void;
  t: (key: string) => string;
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ documentData, caseId, onClose, t }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [isDownloading, setIsDownloading] = useState(false);
  const [actualViewerMode, setActualViewerMode] = useState<'PDF' | 'TEXT' | 'IMAGE' | 'DOWNLOAD'>('PDF');

  const getTargetMode = (mimeType: string) => {
    const m = mimeType.toLowerCase();
    if (m.startsWith('text/') || m === 'application/json') return 'TEXT';
    return 'PDF_PREVIEW';
  };

  const fetchDocument = async () => {
    setIsLoading(true);
    setError(null);
    
    const targetMode = getTargetMode(documentData.mime_type || '');

    try {
      let blob: Blob;

      if (targetMode === 'PDF_PREVIEW') {
         try {
             blob = await apiService.getPreviewDocument(caseId, documentData.id);
             setActualViewerMode('PDF');
         } catch (e) {
             console.warn("Preview fetch failed, checking fallback...", e);
             if (documentData.mime_type?.startsWith('image/')) {
                 blob = await apiService.getOriginalDocument(caseId, documentData.id);
                 setActualViewerMode('IMAGE');
             } else if (documentData.mime_type === 'application/pdf') {
                 blob = await apiService.getOriginalDocument(caseId, documentData.id);
                 setActualViewerMode('PDF');
             } else {
                 setActualViewerMode('DOWNLOAD');
                 throw new Error("PREVIEW_UNAVAILABLE");
             }
         }
      } else {
         blob = await apiService.getOriginalDocument(caseId, documentData.id);
         setActualViewerMode('TEXT');
      }

      if (actualViewerMode === 'TEXT' || (targetMode === 'TEXT')) {
          const text = await blob.text();
          setTextContent(text);
      } else if (actualViewerMode !== 'DOWNLOAD') {
          const url = URL.createObjectURL(blob);
          setFileUrl(url);
      }

    } catch (err: any) {
      if (err.message === "PREVIEW_UNAVAILABLE") {
          // Handled by renderContent
      } else {
          console.error("Viewer Error:", err);
          setError(t('pdfViewer.errorFetch'));
      }
    } finally {
      setIsLoading(false);
    }
  };
  
  useEffect(() => {
    fetchDocument();
    return () => { if (fileUrl) URL.revokeObjectURL(fileUrl); };
  }, [caseId, documentData.id]);

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
    } catch (e) { console.error(e); } finally { setIsDownloading(false); }
  };

  const renderContent = () => {
    if (isLoading) return <div className="flex flex-col items-center justify-center h-full text-text-secondary"><Loader className="animate-spin h-10 w-10 mb-3 text-primary-start" /><p>{t('pdfViewer.loading')}</p></div>;

    if (actualViewerMode === 'DOWNLOAD') {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="bg-white/5 p-6 rounded-full mb-6"><Download size={64} className="text-gray-400" /></div>
            <h3 className="text-xl font-bold text-white mb-2">{t('pdfViewer.previewNotAvailable')}</h3>
            <p className="text-gray-400 mb-8 max-w-md">{t('pdfViewer.downloadToViewMessage')}</p>
            <button onClick={handleDownloadOriginal} disabled={isDownloading} className="px-6 py-3 bg-primary-start hover:bg-primary-end text-white font-semibold rounded-xl shadow-lg transition-all flex items-center gap-2">
                {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />} {t('pdfViewer.downloadOriginal')}
            </button>
          </div>
        );
    }

    if (error) return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <AlertTriangle className="h-12 w-12 text-red-400 mb-4" />
            <p className="text-red-300 mb-6">{error}</p>
            <button onClick={fetchDocument} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white flex items-center gap-2"><RefreshCw size={16} /> {t('caseView.tryAgain')}</button>
        </div>
    );

    switch (actualViewerMode) {
      case 'PDF':
        return (
          <div className="flex justify-center p-4 min-h-full">
             <PdfDocument file={fileUrl} onLoadSuccess={({ numPages }) => { setNumPages(numPages); setPageNumber(1); }} loading="">
                 <Page pageNumber={pageNumber} width={800} renderTextLayer={false} renderAnnotationLayer={false} />
             </PdfDocument>
          </div>
        );
      case 'TEXT':
        return <div className="p-8 w-full max-w-4xl mx-auto bg-white shadow-sm min-h-full"><pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 overflow-auto">{textContent}</pre></div>;
      case 'IMAGE':
        return <div className="flex items-center justify-center h-full p-4"><img src={fileUrl!} alt="Doc" className="max-w-full max-h-full object-contain rounded-lg" /></div>;
      default: return null;
    }
  };

  return (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="bg-background-main w-full h-full max-w-6xl max-h-[95vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-glass-edge" onClick={(e) => e.stopPropagation()}>
          <header className="flex items-center justify-between p-4 bg-background-light/80 border-b border-glass-edge backdrop-blur-sm z-10">
            <h2 className="text-lg font-bold text-text-primary truncate">{documentData.file_name}</h2>
            <div className="flex items-center gap-3">
              <button onClick={handleDownloadOriginal} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full"><Download size={20} /></button>
              <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full"><X size={24} /></button>
            </div>
          </header>
          <div className="flex-grow relative bg-[#1a1a1a] overflow-auto flex flex-col">{renderContent()}</div>
          {actualViewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="flex items-center justify-center p-3 bg-background-light/80 border-t border-glass-edge backdrop-blur-sm z-10">
              <div className="flex items-center gap-4 bg-black/40 px-4 py-2 rounded-full border border-white/5">
                <button onClick={() => setPageNumber(p => Math.max(1, p - 1))} disabled={pageNumber <= 1} className="p-1 text-gray-400 hover:text-white disabled:opacity-30"><ChevronLeft size={20} /></button>
                <span className="text-sm font-medium text-gray-200 w-24 text-center">{pageNumber} / {numPages}</span>
                <button onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} disabled={pageNumber >= numPages} className="p-1 text-gray-400 hover:text-white disabled:opacity-30"><ChevronRight size={20} /></button>
              </div>
            </footer>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default PDFViewerModal;