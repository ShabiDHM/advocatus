// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - PDF VIEWER V2.3 (SCROLL & MOBILE FIX)
// 1. FIX: Injected specific styles for dark-theme scrollbars (custom-pdf-scroll).
// 2. UI: Mobile optimizations - hidden text labels on small screens, adjusted spacing.
// 3. FEATURE: Supports Minimize button (visuals prepared, requires parent handler).

import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService, API_V1_URL } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, RefreshCw, ZoomIn, ZoomOut, Maximize, Minus 
} from 'lucide-react';
import pdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?url';
import { TFunction } from 'i18next';

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;

interface PDFViewerModalProps {
  documentData: Document;
  caseId?: string; 
  onClose: () => void;
  onMinimize?: () => void; // PHOENIX: Minimize handler
  t: TFunction; 
  directUrl?: string | null; 
  isAuth?: boolean;
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ documentData, caseId, onClose, onMinimize, t, directUrl, isAuth = false }) => {
  const [pdfSource, setPdfSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [imageSource, setImageSource] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(!directUrl);
  const [error, setError] = useState<string | null>(null);
  const [retryOriginal, setRetryOriginal] = useState(false);
  
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0); 
  const [containerWidth, setContainerWidth] = useState<number>(0); 
  const containerRef = useRef<HTMLDivElement>(null);

  const [actualViewerMode, setActualViewerMode] = useState<'PDF' | 'TEXT' | 'IMAGE' | 'DOWNLOAD'>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
      const updateWidth = () => {
          if (containerRef.current) {
              setContainerWidth(containerRef.current.clientWidth - 32); 
          }
      };
      
      window.addEventListener('resize', updateWidth);
      updateWidth(); 
      setTimeout(updateWidth, 100);

      return () => window.removeEventListener('resize', updateWidth);
  }, [actualViewerMode]);

  const getTargetMode = (mimeType: string) => {
    const m = mimeType?.toLowerCase() || '';
    if (m.startsWith('text/') || m === 'application/json' || m.includes('plain')) return 'TEXT';
    if (m.startsWith('image/')) return 'IMAGE';
    return 'PDF';
  };

  const fetchDocument = async () => {
    const targetMode = getTargetMode(documentData.mime_type || '');
    const token = apiService.getToken();

    if (directUrl) {
        if (targetMode === 'PDF') {
             if (isAuth && token) {
                 setPdfSource({
                    url: directUrl,
                    httpHeaders: { 'Authorization': `Bearer ${token}` },
                    withCredentials: true
                 });
             } else {
                 setPdfSource(directUrl);
             }
             setActualViewerMode('PDF');
        } else {
             try {
                 let blob: Blob;
                 if (isAuth && token) {
                     const headers: Record<string, string> = {};
                     headers['Authorization'] = `Bearer ${token}`;
                     
                     const response = await fetch(directUrl, { headers });
                     if (!response.ok) throw new Error('Fetch failed');
                     blob = await response.blob();
                 } else {
                     const response = await fetch(directUrl);
                     blob = await response.blob();
                 }

                 if (targetMode === 'TEXT') {
                     const text = await blob.text();
                     setTextContent(text);
                     setActualViewerMode('TEXT');
                 } else {
                     const url = URL.createObjectURL(blob);
                     setImageSource(url);
                     setActualViewerMode('IMAGE');
                 }
             } catch (e) {
                 console.error(e);
                 setActualViewerMode('DOWNLOAD');
             }
             setIsLoading(false);
        }
        return;
    }

    if (!caseId) return;

    if (targetMode === 'PDF') {
        const baseUrl = retryOriginal 
            ? `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/original`
            : `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/preview`;
            
        setPdfSource({
            url: baseUrl,
            httpHeaders: { 'Authorization': `Bearer ${token}` },
            withCredentials: true
        });
        setActualViewerMode('PDF');
        return;
    }

    setIsLoading(true);
    setError(null);

    try {
      let blob: Blob;
      blob = await apiService.getOriginalDocument(caseId as string, documentData.id);

      if (targetMode === 'TEXT') {
          const text = await blob.text();
          setTextContent(text);
          setActualViewerMode('TEXT');
      } else {
          const url = URL.createObjectURL(blob);
          setImageSource(url);
          setActualViewerMode('IMAGE');
      }
    } catch (err: any) {
        console.error("Viewer Error:", err);
        setError(t('pdfViewer.errorFetch', { defaultValue: 'Gabim gjatë ngarkimit të dokumentit' }));
    } finally {
      setIsLoading(false);
    }
  };
  
  useEffect(() => {
    fetchDocument();
    return () => { 
        if (imageSource && !directUrl) URL.revokeObjectURL(imageSource);
    };
  }, [caseId, documentData.id, directUrl, retryOriginal]);

  const onPdfLoadError = (err: any) => {
      if (!retryOriginal && !directUrl) {
          setRetryOriginal(true);
      } else {
          console.error("PDF Load Failed:", err);
          setIsLoading(false);
          setActualViewerMode('DOWNLOAD');
      }
  };

  const onPdfLoadSuccess = ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
      setPageNumber(1);
      setIsLoading(false);
  };

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
      let blob;
      const token = apiService.getToken();
      
      if (directUrl) {
          const headers: Record<string, string> = {};
          if (isAuth && token) {
              headers['Authorization'] = `Bearer ${token}`;
          }
          const r = await fetch(directUrl, { headers });
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
    if (actualViewerMode === 'DOWNLOAD') {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="bg-white/5 p-6 rounded-full mb-6"><Download size={64} className="text-gray-400" /></div>
            <h3 className="text-xl font-bold text-white mb-2">{t('pdfViewer.previewNotAvailable', { defaultValue: 'Pamja paraprake nuk është në dispozicion' })}</h3>
            <p className="text-gray-400 mb-8 max-w-md">{t('pdfViewer.downloadToViewMessage', { defaultValue: 'Shkarkoni dokumentin për ta parë.' })}</p>
            <button onClick={handleDownloadOriginal} disabled={isDownloading} className="px-6 py-3 bg-primary-start hover:bg-primary-end text-white font-semibold rounded-xl shadow-lg transition-all flex items-center gap-2">
                {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />} {t('pdfViewer.downloadOriginal', { defaultValue: 'Shkarko Origjinalin' })}
            </button>
          </div>
        );
    }

    if (error) return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <AlertTriangle className="h-12 w-12 text-red-400 mb-4" />
            <p className="text-red-300 mb-6">{error}</p>
            <button onClick={() => { setRetryOriginal(false); fetchDocument(); }} className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white flex items-center gap-2"><RefreshCw size={16} /> {t('caseView.tryAgain', { defaultValue: 'Provo Përsëri' })}</button>
        </div>
    );

    switch (actualViewerMode) {
      case 'PDF':
        return (
          <div className="flex flex-col items-center w-full min-h-full bg-[#2a2a2a] overflow-auto pt-4 pb-20 custom-pdf-scroll" ref={containerRef}>
             <div className="flex justify-center w-full">
                 <PdfDocument 
                    file={pdfSource} 
                    onLoadSuccess={onPdfLoadSuccess}
                    onLoadError={onPdfLoadError}
                    loading={
                        <div className="flex flex-col items-center text-gray-400 mt-20">
                            <Loader className="animate-spin h-8 w-8 mb-2 text-primary-start" />
                            <span className="text-sm">Duke hapur dokumentin...</span>
                        </div>
                    }
                    error={<div className="text-red-400 mt-10">Gabim gjatë hapjes së PDF.</div>}
                 >
                     <Page 
                        pageNumber={pageNumber} 
                        width={containerWidth > 0 ? Math.min(containerWidth, 800) : undefined} 
                        scale={scale}
                        renderTextLayer={false} 
                        renderAnnotationLayer={false}
                        className="shadow-2xl mb-4" 
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
        if (isLoading) return <div className="flex justify-center items-center h-full"><Loader className="animate-spin text-primary-start" /></div>;
        return (
            <div className="flex items-center justify-center h-full p-4 overflow-auto touch-pinch-zoom custom-pdf-scroll">
                <img 
                    src={imageSource!} 
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
          {/* FIX: Injected Custom Scrollbar Styles */}
          <style>{`
            .custom-pdf-scroll::-webkit-scrollbar { width: 8px; height: 8px; }
            .custom-pdf-scroll::-webkit-scrollbar-track { background: #1a1a1a; }
            .custom-pdf-scroll::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 4px; }
            .custom-pdf-scroll::-webkit-scrollbar-thumb:hover { background: #6b7280; }
          `}</style>

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
              {/* FIX: Hide text on mobile */}
              <button onClick={handleDownloadOriginal} className="p-2 sm:px-4 sm:py-2 text-gray-200 bg-primary-start/20 hover:bg-primary-start hover:text-white rounded-lg transition-colors border border-primary-start/30 flex items-center gap-2" title={t('pdfViewer.downloadOriginal', { defaultValue: 'Shkarko Origjinalin' })}>
                  <Download size={20} />
                  <span className="hidden sm:inline text-sm font-medium">{t('pdfViewer.downloadOriginalShort', { defaultValue: 'Shkarko' })}</span>
              </button>
              
              {/* Minimize Button */}
              {onMinimize && (
                  <button onClick={onMinimize} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors" title={t('pdfViewer.minimize', { defaultValue: 'Minimizo' })}>
                      <Minus size={24} />
                  </button>
              )}

              <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"><X size={24} /></button>
            </div>
          </header>
          
          <div className="flex-grow relative bg-[#0f0f0f] overflow-auto flex flex-col custom-pdf-scroll touch-pan-y">
              {renderContent()}
          </div>
          
          {actualViewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="flex items-center justify-center p-3 bg-background-light/95 border-t border-glass-edge backdrop-blur-xl z-20 shrink-0 absolute bottom-0 w-full sm:relative">
              <div className="flex items-center gap-4 bg-black/80 px-4 py-2 rounded-full border border-white/10 shadow-lg">
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