// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - PDF VIEWER V4.2 (VERSION SYNC FIX)
// 1. FIX: Points workerSrc to CDN with 'pdfjs.version' to ensure exact match (5.x).
// 2. LOGIC: Uses '.mjs' extension required for PDF.js v5+.
// 3. STATUS: Resolves "Version Mismatch" crash.

import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, ZoomIn, ZoomOut, Maximize, Minus 
} from 'lucide-react';
import { TFunction } from 'i18next';

// PHOENIX CRITICAL FIX: Use CDN to fetch the EXACT matching version.
// Version 5.x requires .mjs extension.
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PDFViewerModalProps {
  documentData: Document;
  caseId?: string; 
  onClose: () => void;
  onMinimize?: () => void;
  t: TFunction; 
  directUrl?: string | null; 
  isAuth?: boolean;
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ documentData, caseId, onClose, onMinimize, t, directUrl, isAuth = false }) => {
  const [pdfSource, setPdfSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [imageSource, setImageSource] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0); 
  const [containerWidth, setContainerWidth] = useState<number>(0); 
  const containerRef = useRef<HTMLDivElement>(null);

  const [actualViewerMode, setActualViewerMode] = useState<'PDF' | 'TEXT' | 'IMAGE' | 'DOWNLOAD'>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);

  // Resize handler
  useEffect(() => {
      const updateWidth = () => {
          if (containerRef.current) {
              setContainerWidth(containerRef.current.clientWidth - 40); 
          }
      };
      window.addEventListener('resize', updateWidth);
      setTimeout(updateWidth, 200); 
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
                     const headers: Record<string, string> = { 'Authorization': `Bearer ${token}` };
                     const response = await fetch(directUrl, { headers });
                     if (!response.ok) throw new Error('Fetch failed');
                     blob = await response.blob();
                 } else {
                     const response = await fetch(directUrl);
                     blob = await response.blob();
                 }
                 handleBlobContent(blob, targetMode);
             } catch (e) {
                 console.error(e);
                 setActualViewerMode('DOWNLOAD');
                 setIsLoading(false);
             }
        }
        return;
    }

    if (caseId) {
        setIsLoading(true);
        try {
            const blob = await apiService.getOriginalDocument(caseId, documentData.id);
            if (targetMode === 'PDF') {
                const url = URL.createObjectURL(blob);
                setPdfSource(url);
                setActualViewerMode('PDF');
            } else {
                handleBlobContent(blob, targetMode);
            }
        } catch (err) {
            console.error("Viewer Error:", err);
            setError(t('pdfViewer.errorFetch', { defaultValue: 'Gabim gjatë ngarkimit.' }));
            setIsLoading(false);
        }
        return;
    }
  };

  const handleBlobContent = async (blob: Blob, mode: string) => {
      if (mode === 'TEXT') {
          const text = await blob.text();
          setTextContent(text);
          setActualViewerMode('TEXT');
      } else {
          const url = URL.createObjectURL(blob);
          setImageSource(url);
          setActualViewerMode('IMAGE');
      }
      setIsLoading(false);
  };
  
  useEffect(() => {
    fetchDocument();
    return () => { 
        if (imageSource) URL.revokeObjectURL(imageSource);
        if (typeof pdfSource === 'string' && pdfSource.startsWith('blob:')) URL.revokeObjectURL(pdfSource);
    };
  }, [caseId, documentData.id, directUrl]);

  const onPdfLoadSuccess = ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
      setPageNumber(1);
      setIsLoading(false);
  };

  const onPdfLoadError = (err: any) => {
      console.error("PDF Render Error Detailed:", err);
      setError(err.message || "PDF Failed to Render. Check Worker.");
      setIsLoading(false);
      setActualViewerMode('DOWNLOAD');
  };

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
      let blob;
      const token = apiService.getToken();
      
      if (directUrl) {
          const headers: Record<string, string> = isAuth && token ? { 'Authorization': `Bearer ${token}` } : {};
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
          window.URL.revokeObjectURL(url);
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
            {error && <p className="text-red-400 text-sm mb-4 font-mono bg-black/50 p-2 rounded max-w-md break-words">{error}</p>}
            <button onClick={handleDownloadOriginal} disabled={isDownloading} className="px-6 py-3 bg-primary-start hover:bg-primary-end text-white font-semibold rounded-xl shadow-lg transition-all flex items-center gap-2 mt-4">
                {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />} {t('pdfViewer.downloadOriginal', { defaultValue: 'Shkarko Origjinalin' })}
            </button>
          </div>
        );
    }

    if (error) return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <AlertTriangle className="h-12 w-12 text-red-400 mb-4" />
            <p className="text-red-300 mb-6">{error}</p>
        </div>
    );

    switch (actualViewerMode) {
      case 'PDF':
        return (
          <div className="flex flex-col items-center w-full min-h-full bg-[#1a1a1a] overflow-auto pt-8 pb-20" ref={containerRef}>
             {isLoading && (
                 <div className="absolute inset-0 flex items-center justify-center bg-[#1a1a1a] z-10">
                     <Loader className="animate-spin h-10 w-10 text-primary-start" />
                 </div>
             )}
             <div className="flex justify-center w-full">
                 <PdfDocument 
                    file={pdfSource} 
                    onLoadSuccess={onPdfLoadSuccess}
                    onLoadError={onPdfLoadError}
                    loading={null} 
                    noData={null}
                    key={typeof pdfSource === 'string' ? pdfSource : pdfSource?.url}
                 >
                     <Page 
                        pageNumber={pageNumber} 
                        width={containerWidth > 0 ? containerWidth : 600} 
                        scale={scale}
                        renderTextLayer={false} 
                        renderAnnotationLayer={false}
                        className="shadow-2xl mb-4 border border-white/5" 
                     />
                 </PdfDocument>
             </div>
          </div>
        );
      case 'TEXT':
        return (
          <div className="flex justify-center p-4 sm:p-8 min-h-full">
            <div className="bg-white text-gray-900 shadow-2xl p-6 sm:p-12 min-h-[600px] w-full max-w-3xl rounded-sm">
                <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm">{textContent}</pre>
            </div>
          </div>
        );
      case 'IMAGE':
        return (
            <div className="flex items-center justify-center h-full p-4 overflow-auto">
                <img src={imageSource!} alt="Doc" className="max-w-full max-h-full object-contain rounded-lg shadow-lg" />
            </div>
        );
      default: return null;
    }
  };

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/95 backdrop-blur-md z-[9999] flex items-center justify-center p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="bg-[#1a1a1a] w-full h-full sm:max-w-6xl sm:max-h-[95vh] rounded-none sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-glass-edge" onClick={(e) => e.stopPropagation()}>
          
          <header className="flex flex-wrap items-center justify-between p-3 sm:p-4 bg-background-light/95 border-b border-glass-edge backdrop-blur-xl z-20 gap-2 shrink-0">
            <div className="flex items-center gap-3 min-w-0 flex-1">
                <h2 className="text-sm sm:text-lg font-bold text-gray-200 truncate max-w-[200px]">
                    {documentData.file_name} <span className="text-[10px] text-gray-500 font-normal">(Phoenix View)</span>
                </h2>
                
                {actualViewerMode === 'PDF' && (
                    <div className="flex items-center gap-1 bg-white/5 rounded-lg p-1 border border-white/10 ml-2">
                        <button onClick={zoomOut} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded"><ZoomOut size={16} /></button>
                        <span className="text-[10px] text-gray-400 w-8 text-center">{Math.round(scale * 100)}%</span>
                        <button onClick={zoomIn} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded"><ZoomIn size={16} /></button>
                        <button onClick={zoomReset} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded ml-1" title="Reset"><Maximize size={16} /></button>
                    </div>
                )}
            </div>
            
            <div className="flex items-center gap-2 flex-shrink-0">
              <button onClick={handleDownloadOriginal} className="p-2 text-gray-200 bg-primary-start/20 hover:bg-primary-start hover:text-white rounded-lg border border-primary-start/30"><Download size={20} /></button>
              
              {onMinimize && (
                <button onClick={onMinimize} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full" title="Minimizo">
                    <Minus size={24} />
                </button>
              )}

              <button onClick={onClose} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full"><X size={24} /></button>
            </div>
          </header>
          
          <div className="flex-grow relative bg-[#0f0f0f] overflow-auto flex flex-col custom-scrollbar touch-pan-y">
              {renderContent()}
          </div>
          
          {actualViewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="flex items-center justify-center p-3 bg-background-light/95 border-t border-glass-edge backdrop-blur-xl z-20 shrink-0">
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