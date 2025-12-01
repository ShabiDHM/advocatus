// FILE: src/components/PDFViewerModal.tsx
import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService, API_V1_URL } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, RefreshCw, ZoomIn, ZoomOut, Maximize, FileText 
} from 'lucide-react';
import pdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?url';
import { TFunction } from 'i18next';

pdfjs.GlobalWorkerOptions.workerSrc = pdfWorker;

interface PDFViewerModalProps {
  documentData: Document;
  caseId?: string; 
  onClose: () => void;
  t: TFunction; 
  directUrl?: string | null; 
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ documentData, caseId, onClose, t, directUrl }) => {
  // We use 'any' for source because react-pdf accepts { url, httpHeaders } object
  const [pdfSource, setPdfSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [imageSource, setImageSource] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(!directUrl);
  const [error, setError] = useState<string | null>(null);
  const [retryOriginal, setRetryOriginal] = useState(false);
  
  // Viewer State
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0); 
  const [actualViewerMode, setActualViewerMode] = useState<'PDF' | 'TEXT' | 'IMAGE' | 'DOWNLOAD'>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);

  const getTargetMode = (mimeType: string) => {
    const m = mimeType?.toLowerCase() || '';
    if (m.startsWith('text/') || m === 'application/json' || m.includes('plain')) return 'TEXT';
    if (m.startsWith('image/')) return 'IMAGE';
    return 'PDF';
  };

  const fetchDocument = async () => {
    const targetMode = getTargetMode(documentData.mime_type || '');

    // 1. Direct URL (Newly Uploaded File)
    if (directUrl) {
        if (targetMode === 'TEXT') {
             try {
                 const r = await fetch(directUrl);
                 const text = await r.text();
                 setTextContent(text);
                 setActualViewerMode('TEXT');
             } catch (e) {
                 setActualViewerMode('DOWNLOAD');
             }
        } else if (targetMode === 'IMAGE') {
             setImageSource(directUrl);
             setActualViewerMode('IMAGE');
        } else {
             setPdfSource(directUrl);
             setActualViewerMode('PDF');
        }
        setIsLoading(false);
        return;
    }

    if (!caseId) return;

    // 2. Optimized Streaming for PDFs (Remote)
    if (targetMode === 'PDF') {
        const token = localStorage.getItem('jwtToken');
        const baseUrl = retryOriginal 
            ? `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/original`
            : `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/preview`;
            
        // PHOENIX SPEED HACK: Pass URL + Auth Headers directly to PDF.js
        // This allows streaming (render page 1 while downloading rest)
        setPdfSource({
            url: baseUrl,
            httpHeaders: { 'Authorization': `Bearer ${token}` },
            withCredentials: true
        });
        setActualViewerMode('PDF');
        // We do NOT set isLoading(false) here; react-pdf handles the spinner via 'loading' prop
        return;
    }

    // 3. Fallback Blob Fetch for Text/Images (Cannot stream easily into <img> tag with Auth headers)
    setIsLoading(true);
    setError(null);

    try {
      let blob: Blob;
      // For images, try original (previews might not be generated yet or same size)
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
  
  // Effect to trigger load or retry
  useEffect(() => {
    fetchDocument();
    
    // Cleanup
    return () => { 
        if (imageSource && !directUrl) URL.revokeObjectURL(imageSource);
    };
  }, [caseId, documentData.id, directUrl, retryOriginal]);

  // Handle PDF Load Error (Fallback to Original if Preview fails)
  const onPdfLoadError = (err: any) => {
      if (!retryOriginal && !directUrl) {
          console.warn("Preview failed (likely 404), switching to Original...", err);
          setRetryOriginal(true); // Triggers useEffect -> fetchDocument with original URL
      } else {
          console.error("PDF Load Failed:", err);
          setIsLoading(false);
          // If PDF completely fails, fallback to download button
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
          <div className="flex flex-col items-center justify-center w-full h-full bg-[#0f0f0f] relative">
             <div className="md:hidden flex flex-col items-center text-center text-gray-400 p-6">
                  <FileText size={64} className="text-primary-start mb-4" />
                  <h4 className="text-xl font-bold mb-2 text-white">{t('pdfViewer.mobileViewTitle', { defaultValue: 'Shiko Dokumentin' })}</h4>
                  <a href={directUrl || '#'} onClick={handleDownloadOriginal} className="px-8 py-4 bg-primary-start text-white rounded-xl font-bold shadow-xl flex items-center gap-2 mt-4">
                      <Download size={20} /> {t('pdfViewer.downloadOriginal')}
                  </a>
             </div>

             <div className="hidden md:flex justify-center p-4 min-h-full w-full overflow-auto">
                 {/* PHOENIX OPTIMIZATION: React-PDF handles the fetch internally */}
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
        if (isLoading) return <div className="flex justify-center items-center h-full"><Loader className="animate-spin text-primary-start" /></div>;
        return (
            <div className="flex items-center justify-center h-full p-4 overflow-auto touch-pinch-zoom">
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
              <button onClick={handleDownloadOriginal} className="p-2 text-gray-200 bg-primary-start/20 hover:bg-primary-start hover:text-white rounded-lg transition-colors border border-primary-start/30 hidden md:block" title={t('pdfViewer.downloadOriginal', { defaultValue: 'Shkarko Origjinalin' })}><Download size={20} /></button>
              <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-colors"><X size={24} /></button>
            </div>
          </header>
          
          <div className="flex-grow relative bg-[#0f0f0f] overflow-auto flex flex-col custom-scrollbar touch-pan-y">
              {renderContent()}
          </div>
          
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