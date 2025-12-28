// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - PDF VIEWER V5.2 (MOBILE FIX)
// 1. MOBILE: Title now truncates properly without overlapping buttons.
// 2. SCALE: Auto-detects mobile (Scale 1.0) vs Desktop (Scale 0.7) on load.
// 3. LAYOUT: Adjusted container width calculation for better mobile fit.

import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, ZoomIn, ZoomOut, Maximize, Minus, FileText
} from 'lucide-react';
import { TFunction } from 'i18next';

// Ensure exact version match for worker
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
  
  // PHOENIX FIX: Initial scale based on screen width
  const [scale, setScale] = useState(window.innerWidth < 640 ? 1.0 : 0.7);
  
  const [containerWidth, setContainerWidth] = useState<number>(0); 
  const containerRef = useRef<HTMLDivElement>(null);

  const [actualViewerMode, setActualViewerMode] = useState<'PDF' | 'TEXT' | 'IMAGE' | 'DOWNLOAD'>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);

  // Responsive Layout Handler
  useEffect(() => {
      const handleResize = () => {
          if (containerRef.current) {
              // PHOENIX FIX: Subtract padding (32px) to prevent overflow
              setContainerWidth(containerRef.current.clientWidth - 32); 
          }
          
          // Auto-adjust scale logic if moving between desktop/mobile
          if (window.innerWidth < 640) {
              setScale(1.0); // Fit width on mobile
          }
      };

      // Initial calculation
      handleResize();

      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
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
  const zoomReset = () => setScale(window.innerWidth < 640 ? 1.0 : 0.7);

  const renderContent = () => {
    if (actualViewerMode === 'DOWNLOAD') {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="bg-white/5 p-6 rounded-full mb-6 border border-white/10"><Download size={64} className="text-gray-500" /></div>
            <h3 className="text-xl font-bold text-white mb-2">{t('pdfViewer.previewNotAvailable', { defaultValue: 'Pamja paraprake nuk është në dispozicion' })}</h3>
            {error && <p className="text-red-400 text-sm mb-6 font-mono bg-red-500/10 p-3 rounded-xl max-w-md break-words border border-red-500/20">{error}</p>}
            <button onClick={handleDownloadOriginal} disabled={isDownloading} className="px-8 py-3 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg text-white font-bold rounded-xl transition-all flex items-center gap-2 active:scale-95">
                {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />} {t('pdfViewer.downloadOriginal', { defaultValue: 'Shkarko Origjinalin' })}
            </button>
          </div>
        );
    }

    if (error) return (
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="bg-red-500/10 p-6 rounded-full mb-4"><AlertTriangle className="h-12 w-12 text-red-400" /></div>
            <p className="text-red-300 font-medium">{error}</p>
        </div>
    );

    switch (actualViewerMode) {
      case 'PDF':
        return (
          <div className="flex flex-col items-center w-full min-h-full bg-black/40 overflow-auto pt-8 pb-20" ref={containerRef}>
             {isLoading && (
                 <div className="absolute inset-0 flex items-center justify-center z-10 bg-black/60 backdrop-blur-sm">
                     <Loader className="animate-spin h-10 w-10 text-primary-start" />
                 </div>
             )}
             <div className="flex justify-center w-full px-4">
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
                        width={containerWidth > 0 ? containerWidth : 300} 
                        scale={scale}
                        renderTextLayer={false} 
                        renderAnnotationLayer={false}
                        className="shadow-2xl mb-4 border border-white/5 rounded-lg overflow-hidden" 
                     />
                 </PdfDocument>
             </div>
          </div>
        );
      case 'TEXT':
        return (
          <div className="flex justify-center p-6 sm:p-8 min-h-full bg-black/40">
            <div className="glass-panel p-8 min-h-[600px] w-full max-w-4xl rounded-xl">
                <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm text-gray-300 leading-relaxed">{textContent}</pre>
            </div>
          </div>
        );
      case 'IMAGE':
        return (
            <div className="flex items-center justify-center h-full p-4 overflow-auto bg-black/40">
                <img src={imageSource!} alt="Doc" className="max-w-full max-h-full object-contain rounded-lg shadow-2xl border border-white/10" />
            </div>
        );
      default: return null;
    }
  };

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-background-dark/90 backdrop-blur-xl z-[9999] flex items-center justify-center p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="glass-high w-full h-full sm:max-w-6xl sm:max-h-[95vh] rounded-none sm:rounded-3xl shadow-2xl flex flex-col overflow-hidden border border-white/10" onClick={(e) => e.stopPropagation()}>
          
          {/* Header */}
          <header className="flex items-center justify-between p-4 border-b border-white/5 bg-white/5 backdrop-blur-md z-20 gap-3 shrink-0">
            {/* Left: Icon & Title */}
            <div className="flex items-center gap-3 min-w-0 flex-1 overflow-hidden">
                <div className="p-2 bg-primary-start/20 rounded-lg border border-primary-start/30 flex-shrink-0">
                    <FileText className="text-primary-start w-5 h-5" />
                </div>
                <div className="min-w-0 flex-1 flex flex-col">
                    {/* PHOENIX FIX: Truncate title properly on mobile */}
                    <h2 className="text-sm sm:text-base font-bold text-white truncate w-full">
                        {documentData.file_name}
                    </h2>
                    <span className="text-[10px] font-mono text-text-secondary uppercase tracking-widest truncate">
                        {actualViewerMode} VIEW
                    </span>
                </div>
                
                {/* Desktop Zoom Controls */}
                {actualViewerMode === 'PDF' && (
                    <div className="hidden md:flex items-center gap-1 bg-black/40 rounded-lg p-1 border border-white/10 ml-4 flex-shrink-0">
                        <button onClick={zoomOut} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors"><ZoomOut size={16} /></button>
                        <span className="text-[10px] font-bold text-white w-10 text-center">{Math.round(scale * 100)}%</span>
                        <button onClick={zoomIn} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors"><ZoomIn size={16} /></button>
                        <div className="w-px h-4 bg-white/10 mx-1"></div>
                        <button onClick={zoomReset} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors" title="Reset"><Maximize size={16} /></button>
                    </div>
                )}
            </div>
            
            {/* Right: Actions */}
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              <button onClick={handleDownloadOriginal} className="p-2 text-primary-300 bg-primary-500/10 hover:bg-primary-500/20 hover:text-white rounded-xl border border-primary-500/20 transition-colors" title="Shkarko">
                  <Download size={20} />
              </button>
              
              {onMinimize && (
                <button onClick={onMinimize} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-xl transition-colors" title="Minimizo">
                    <Minus size={24} />
                </button>
              )}

              <button onClick={onClose} className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-colors" title="Mbyll">
                  <X size={24} />
              </button>
            </div>
          </header>
          
          {/* Main Content */}
          <div className="flex-grow relative bg-black/20 overflow-auto flex flex-col custom-scrollbar touch-pan-y">
              {renderContent()}
          </div>
          
          {/* Footer Controls */}
          {actualViewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="flex items-center justify-center p-4 border-t border-white/5 bg-white/5 backdrop-blur-md z-20 shrink-0">
              <div className="flex items-center gap-4 bg-black/60 px-6 py-2 rounded-full border border-white/10 shadow-lg backdrop-blur-xl">
                <button onClick={() => setPageNumber(p => Math.max(1, p - 1))} disabled={pageNumber <= 1} className="p-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"><ChevronLeft size={20} /></button>
                <span className="text-sm font-bold text-white w-24 text-center font-mono">{pageNumber} / {numPages}</span>
                <button onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} disabled={pageNumber >= numPages} className="p-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"><ChevronRight size={20} /></button>
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