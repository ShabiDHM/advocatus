// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - CLEANUP
// 1. FIXED: Removed unused 'ZoomIn' and 'ZoomOut' imports.
// 2. STATUS: Clean, warning-free code.

import React, { useState, useEffect } from 'react';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, RefreshCw, Maximize, Minus, Plus 
} from 'lucide-react';
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
  
  // Viewer State
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0); 
  const [actualViewerMode, setActualViewerMode] = useState<'PDF' | 'TEXT' | 'IMAGE' | 'DOWNLOAD'>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);

  // --- LOGIC ---
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
          // Handled by render logic
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

  const zoomIn = () => setScale(prev => Math.min(prev + 0.1, 3.0));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.1, 0.5));
  const zoomReset = () => setScale(1.0);

  // --- RENDER CONTENT ---
  const renderContent = () => {
    if (isLoading) return <div className="flex flex-col items-center justify-center h-full text-text-secondary"><Loader className="animate-spin h-12 w-12 mb-4 text-primary-start" /><p className="text-lg animate-pulse">{t('pdfViewer.loading')}</p></div>;

    if (actualViewerMode === 'DOWNLOAD') {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="bg-white/5 p-6 rounded-full mb-6 ring-1 ring-white/10"><Download size={64} className="text-gray-400" /></div>
            <h3 className="text-2xl font-bold text-white mb-2">{t('pdfViewer.previewNotAvailable')}</h3>
            <p className="text-gray-400 mb-8 max-w-md">{t('pdfViewer.downloadToViewMessage')}</p>
            <button onClick={handleDownloadOriginal} disabled={isDownloading} className="px-8 py-3 bg-primary-start hover:bg-primary-end text-white font-bold rounded-xl shadow-lg hover:shadow-primary-start/20 transition-all flex items-center gap-3 transform hover:scale-105">
                {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />} {t('pdfViewer.downloadOriginal')}
            </button>
          </div>
        );
    }

    if (error) return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <AlertTriangle className="h-16 w-16 text-red-400 mb-4" />
            <p className="text-red-300 mb-6 text-lg">{error}</p>
            <button onClick={fetchDocument} className="px-6 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white flex items-center gap-2 transition-all"><RefreshCw size={18} /> {t('caseView.tryAgain')}</button>
        </div>
    );

    switch (actualViewerMode) {
      case 'PDF':
        return (
          <div className="flex justify-center p-8 min-h-full">
             <PdfDocument 
                file={fileUrl} 
                onLoadSuccess={({ numPages }) => { setNumPages(numPages); setPageNumber(1); }} 
                loading={<Loader className="animate-spin text-primary-start" />}
                className="flex flex-col gap-8"
             >
                 <Page 
                    pageNumber={pageNumber} 
                    scale={scale} 
                    renderTextLayer={false} 
                    renderAnnotationLayer={false}
                    className="shadow-2xl rounded-lg overflow-hidden border border-white/10" 
                 />
             </PdfDocument>
          </div>
        );
      case 'TEXT':
        return <div className="p-8 w-full max-w-4xl mx-auto bg-white shadow-2xl min-h-full my-8 rounded-lg"><pre className="whitespace-pre-wrap font-mono text-sm text-gray-800 overflow-auto leading-relaxed">{textContent}</pre></div>;
      case 'IMAGE':
        return (
            <div className="flex items-center justify-center h-full p-4 overflow-auto touch-pinch-zoom">
                <img 
                    src={fileUrl!} 
                    alt="Doc" 
                    style={{ transform: `scale(${scale})`, transition: 'transform 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)' }}
                    className="max-w-full max-h-full object-contain rounded-lg shadow-2xl origin-center" 
                />
            </div>
        );
      default: return null;
    }
  };

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }} 
        // Z-INDEX FIX: z-[100] ensures it sits above the standard Navbar
        className="fixed inset-0 bg-black/95 backdrop-blur-md z-[100] flex items-center justify-center overflow-hidden" 
        onClick={onClose}
      >
        <motion.div 
            initial={{ scale: 0.95, opacity: 0, y: 20 }} 
            animate={{ scale: 1, opacity: 1, y: 0 }} 
            exit={{ scale: 0.95, opacity: 0, y: 20 }} 
            className="w-full h-full flex flex-col relative"
            onClick={(e) => e.stopPropagation()}
        >
          {/* HEADER: Transparent, Minimalist */}
          <header className="absolute top-0 left-0 right-0 h-16 flex items-center justify-between px-6 z-20 bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
            <div className="pointer-events-auto bg-black/40 backdrop-blur-md border border-white/10 px-4 py-1.5 rounded-full flex items-center gap-2">
                <span className="text-white font-medium text-sm truncate max-w-[200px] sm:max-w-md">{documentData.file_name}</span>
            </div>
            
            <div className="flex items-center gap-3 pointer-events-auto">
                <button 
                    onClick={handleDownloadOriginal} 
                    className="p-2.5 bg-black/40 hover:bg-white/10 text-gray-300 hover:text-white rounded-full backdrop-blur-md border border-white/10 transition-all"
                    title={t('pdfViewer.downloadOriginal')}
                >
                    <Download size={20} />
                </button>
                <button 
                    onClick={onClose} 
                    className="p-2.5 bg-red-500/80 hover:bg-red-600 text-white rounded-full backdrop-blur-md shadow-lg transition-all transform hover:scale-105"
                    title="Close"
                >
                    <X size={20} />
                </button>
            </div>
          </header>

          {/* MAIN CONTENT AREA */}
          {/* Custom Scrollbar CSS embedded via style tag */}
          <style>{`
            .custom-scrollbar::-webkit-scrollbar { width: 8px; height: 8px; }
            .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
            .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
            .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.4); }
          `}</style>
          
          <div className="flex-grow overflow-auto custom-scrollbar pt-16 pb-24 flex flex-col items-center">
            {renderContent()}
          </div>

          {/* FLOATING FLOATING TOOLBAR (Professional UI) */}
          {(actualViewerMode === 'PDF' || actualViewerMode === 'IMAGE') && (
            <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-20">
                <div className="bg-[#1e1e1e]/90 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl flex items-center p-1.5 gap-2">
                    {/* Page Navigation */}
                    {numPages && numPages > 1 && (
                        <>
                            <div className="flex items-center gap-1 pl-1">
                                <button onClick={() => setPageNumber(p => Math.max(1, p - 1))} disabled={pageNumber <= 1} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg disabled:opacity-30 transition-colors"><ChevronLeft size={20} /></button>
                                <span className="text-sm font-medium text-gray-200 min-w-[60px] text-center font-mono">{pageNumber} / {numPages}</span>
                                <button onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} disabled={pageNumber >= numPages} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg disabled:opacity-30 transition-colors"><ChevronRight size={20} /></button>
                            </div>
                            <div className="w-px h-6 bg-white/10 mx-1"></div>
                        </>
                    )}

                    {/* Zoom Controls */}
                    <div className="flex items-center gap-1 pr-1">
                        <button onClick={zoomOut} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"><Minus size={18} /></button>
                        <span className="text-sm font-medium text-gray-200 min-w-[45px] text-center font-mono">{Math.round(scale * 100)}%</span>
                        <button onClick={zoomIn} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"><Plus size={18} /></button>
                        <button onClick={zoomReset} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors ml-1" title="Reset"><Maximize size={16} /></button>
                    </div>
                </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default PDFViewerModal;