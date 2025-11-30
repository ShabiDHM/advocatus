// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - UNIFIED VIEWER (BLOB & TEXT FIX)
// 1. FIX: correctly handles 'directUrl' for non-PDF types (Text/Image).
// 2. LOGIC: Fetches text content from blob URL if mode is TEXT.

import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, RefreshCw, ZoomIn, ZoomOut, Maximize, ExternalLink, FileText 
} from 'lucide-react';
import pdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?url';

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;

interface PDFViewerModalProps {
  documentData: Document;
  caseId?: string; // Optional: Business docs might not have caseId
  onClose: () => void;
  t: (key: string) => string;
  directUrl?: string | null; 
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ documentData, caseId, onClose, t, directUrl }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(directUrl || null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(!directUrl);
  const [error, setError] = useState<string | null>(null);
  
  // Viewer State
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0); 
  const [actualViewerMode, setActualViewerMode] = useState<'PDF' | 'TEXT' | 'IMAGE' | 'DOWNLOAD'>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);

  const getTargetMode = (mimeType: string) => {
    const m = mimeType?.toLowerCase() || '';
    if (m.startsWith('text/') || m === 'application/json' || m.includes('plain')) return 'TEXT';
    return 'PDF_PREVIEW';
  };

  const fetchDocument = async () => {
    // 1. Calculate mode based on MIME type first
    const targetMode = getTargetMode(documentData.mime_type || '');

    // 2. Handle Direct URL (Blob) Scenario
    if (directUrl) {
        if (targetMode === 'TEXT') {
             try {
                 const r = await fetch(directUrl);
                 const text = await r.text();
                 setTextContent(text);
                 setActualViewerMode('TEXT');
             } catch (e) {
                 console.error("Failed to read text blob", e);
                 setActualViewerMode('DOWNLOAD');
             }
        } else if (documentData.mime_type?.startsWith('image/')) {
             setActualViewerMode('IMAGE');
        } else {
             // Default to PDF for everything else
             setActualViewerMode('PDF');
        }
        
        setIsLoading(false);
        return;
    }

    if (!caseId) { return; }

    setIsLoading(true);
    setError(null);

    try {
      let blob: Blob;

      if (targetMode === 'PDF_PREVIEW') {
         try {
             // TS FIX: Cast caseId to string (guaranteed by !caseId check above)
             blob = await apiService.getPreviewDocument(caseId as string, documentData.id);
             setActualViewerMode('PDF');
         } catch (e) {
             console.warn("Preview fetch failed, checking fallback...", e);
             if (documentData.mime_type?.startsWith('image/')) {
                 blob = await apiService.getOriginalDocument(caseId as string, documentData.id);
                 setActualViewerMode('IMAGE');
             } else if (documentData.mime_type === 'application/pdf') {
                 blob = await apiService.getOriginalDocument(caseId as string, documentData.id);
                 setActualViewerMode('PDF');
             } else {
                 setActualViewerMode('DOWNLOAD');
                 throw new Error("PREVIEW_UNAVAILABLE");
             }
         }
      } else {
         blob = await apiService.getOriginalDocument(caseId as string, documentData.id);
         setActualViewerMode('TEXT');
      }

      if (actualViewerMode === 'TEXT' || (targetMode === 'TEXT')) {
          const text = await blob.text();
          setTextContent(text);
          setActualViewerMode('TEXT');
      } else if (actualViewerMode !== 'DOWNLOAD') {
          const url = URL.createObjectURL(blob);
          setFileUrl(url);
      }

    } catch (err: any) {
      if (err.message === "PREVIEW_UNAVAILABLE") {
          // Handled
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
    document.body.style.overflow = 'hidden';
    
    return () => { 
        if (fileUrl && !directUrl) URL.revokeObjectURL(fileUrl);
        document.body.style.overflow = 'unset';
    };
  }, [caseId, documentData.id, directUrl]);

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
      let blob;
      if (directUrl) {
          const r = await fetch(directUrl);
          blob = await r.blob();
      } else if (caseId) {
          blob = await apiService.getOriginalDocument(caseId, documentData.id);
      }
      
      if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = documentData.file_name;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
      }
    } catch (e) { console.error(e); } finally { setIsDownloading(false); }
  };

  const zoomIn = () => setScale(prev => Math.min(prev + 0.1, 3.0));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.1, 0.5));
  const zoomReset = () => setScale(1.0);

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
          <div className="flex flex-col items-center justify-center w-full h-full bg-[#0f0f0f] relative">
             <div className="md:hidden flex flex-col items-center text-center text-gray-400 p-6">
                  <FileText size={64} className="text-primary-start mb-4" />
                  <h4 className="text-xl font-bold mb-2 text-white">{t('pdfViewer.mobileViewTitle')}</h4>
                  <p className="mb-6 text-sm max-w-xs">{t('pdfViewer.mobileViewDesc')}</p>
                  <a 
                      href={fileUrl!} 
                      target="_blank" 
                      rel="noreferrer" 
                      className="px-8 py-4 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold shadow-xl flex items-center gap-2 transition-transform active:scale-95"
                  >
                      <ExternalLink size={20} />
                      {t('pdfViewer.openNow')}
                  </a>
             </div>

             <div className="hidden md:flex justify-center p-4 min-h-full w-full overflow-auto">
                 <PdfDocument 
                    file={fileUrl} 
                    onLoadSuccess={({ numPages }) => { setNumPages(numPages); setPageNumber(1); }} 
                    loading={<Loader className="animate-spin text-white" />}
                    error={<div className="text-white text-center mt-10"><p>Failed to load PDF component.</p><a href={fileUrl!} target="_blank" className="underline text-primary-start">Open directly</a></div>}
                 >
                     <Page 
                        pageNumber={pageNumber} 
                        scale={scale} 
                        renderTextLayer={false} 
                        renderAnnotationLayer={false}
                        className="shadow-2xl" 
                     />
                 </PdfDocument>
             </div>
          </div>
        );
      case 'TEXT':
        return (
          <div className="flex justify-center p-4 sm:p-8 min-h-full">
            <div 
                className="bg-white text-gray-900 shadow-2xl p-6 sm:p-12 min-h-[600px] sm:min-h-[800px] w-full max-w-3xl transition-transform origin-top rounded-sm sm:rounded-md"
                style={{ transform: `scale(${scale})` }}
            >
                <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm leading-relaxed overflow-x-hidden">
                    {textContent}
                </pre>
            </div>
          </div>
        );
      case 'IMAGE':
        return (
            <div className="flex items-center justify-center h-full p-4 overflow-auto touch-pinch-zoom">
                <img 
                    src={fileUrl!} 
                    alt="Doc" 
                    style={{ transform: `scale(${scale})`, transition: 'transform 0.1s' }}
                    className="max-w-full max-h-full object-contain rounded-lg shadow-lg origin-center" 
                />
            </div>
        );
      default: return null;
    }
  };

  const modalContent = (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }} 
        className="fixed inset-0 bg-black/95 backdrop-blur-md z-[9999] flex items-center justify-center p-0 sm:p-4" 
        onClick={onClose}
      >
        <motion.div 
            initial={{ scale: 0.95, opacity: 0 }} 
            animate={{ scale: 1, opacity: 1 }} 
            exit={{ scale: 0.95, opacity: 0 }} 
            className="bg-[#1a1a1a] w-full h-full sm:max-w-6xl sm:max-h-[95vh] rounded-none sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-glass-edge" 
            onClick={(e) => e.stopPropagation()}
        >
          <header className="flex flex-wrap items-center justify-between p-3 sm:p-4 bg-background-light/95 border-b border-glass-edge backdrop-blur-xl z-20 gap-2 shrink-0">
            <div className="flex items-center gap-3 min-w-0 flex-1">
                <h2 className="text-sm sm:text-lg font-bold text-gray-200 truncate max-w-[150px] sm:max-w-md">{documentData.file_name}</h2>
                {(actualViewerMode !== 'DOWNLOAD') && (
                    <div className="flex items-center gap-1 bg-white/5 rounded-lg p-1 border border-white/10 ml-2">
                        <button onClick={zoomOut} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded active:scale-95 transition-transform"><ZoomOut size={16} /></button>
                        <span className="text-[10px] sm:text-xs text-gray-400 w-8 text-center hidden sm:inline-block">{Math.round(scale * 100)}%</span>
                        <button onClick={zoomIn} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded active:scale-95 transition-transform"><ZoomIn size={16} /></button>
                        <button onClick={zoomReset} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded ml-1 active:scale-95 transition-transform" title="Reset"><Maximize size={16} /></button>
                    </div>
                )}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {fileUrl && (
                  <a href={fileUrl} target="_blank" rel="noreferrer" className="p-2 text-gray-200 bg-white/10 hover:bg-white/20 rounded-lg transition-colors md:hidden" title={t('pdfViewer.openNow')}><ExternalLink size={20} /></a>
              )}
              <button onClick={handleDownloadOriginal} className="p-2 text-gray-200 bg-primary-start/20 hover:bg-primary-start hover:text-white rounded-lg transition-colors border border-primary-start/30 hidden md:block" title={t('pdfViewer.downloadOriginal')}><Download size={20} /></button>
              <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"><X size={24} /></button>
            </div>
          </header>
          <div className="flex-grow relative bg-[#0f0f0f] overflow-auto flex flex-col custom-scrollbar touch-pan-y">{renderContent()}</div>
          {actualViewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="hidden md:flex items-center justify-center p-3 bg-background-light/95 border-t border-glass-edge backdrop-blur-xl z-20 shrink-0">
              <div className="flex items-center gap-4 bg-black/40 px-4 py-2 rounded-full border border-white/5">
                <button onClick={() => setPageNumber(p => Math.max(1, p - 1))} disabled={pageNumber <= 1} className="p-2 text-gray-400 hover:text-white disabled:opacity-30"><ChevronLeft size={24} /></button>
                <span className="text-sm font-medium text-gray-200 w-20 text-center">{pageNumber} / {numPages}</span>
                <button onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} disabled={pageNumber >= numPages} className="p-2 text-gray-400 hover:text-white disabled:opacity-30"><ChevronRight size={24} /></button>
              </div>
            </footer>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default PDFViewerModal;