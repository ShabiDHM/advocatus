// FILE: src/components/FileViewerModal.tsx
// PHOENIX PROTOCOL - FILE VIEWER MODAL V20.0 (NATIVE FETCH BLOB PRE-LOADING FOR FAST PDF RENDERING)

import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService, API_V1_URL } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    ZoomIn, ZoomOut, Maximize, Maximize2, Minus, FileText, Table as TableIcon
} from 'lucide-react';
import { TFunction } from 'i18next';
import { DraftResultRenderer } from '../drafting/components/DraftResultRenderer';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface FileViewerModalProps {
  documentData: any;
  caseId?: string; 
  onClose: () => void;
  onMinimize?: () => void;
  t: TFunction; 
  directUrl?: string | null; 
  isAuth?: boolean;
  initialPage?: number;
}

type ViewerMode = 'PDF' | 'TEXT' | 'IMAGE' | 'CSV' | 'DOWNLOAD';

const FileViewerModal: React.FC<FileViewerModalProps> = ({ 
  documentData, 
  caseId, 
  onClose, 
  onMinimize, 
  t, 
  directUrl, 
  isAuth = false,
  initialPage = 1
}) => {
  const [fileSource, setFileSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [csvContent, setCsvContent] = useState<string[][] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(initialPage || 1);
  const [jumpInput, setJumpInput] = useState<string>(String(initialPage || 1));
  const [isEditingPage, setIsEditingPage] = useState(false);
  const [scale, setScale] = useState(1.0); 
  const [containerWidth, setContainerWidth] = useState<number>(0); 
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewerMode, setViewerMode] = useState<ViewerMode>('PDF');
  const [isMinimized, setIsMinimized] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (initialPage && initialPage > 0) {
      setPageNumber(initialPage);
      setJumpInput(String(initialPage));
    }
  }, [initialPage]);

  useLockBodyScroll(!isMinimized);

  const isMobile = typeof window !== 'undefined' && (/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || window.innerWidth < 768);

  const isLegalDraft = (documentData?.category === 'DRAFT' || 
                        documentData?.file_name?.toLowerCase().includes('draft') ||
                        documentData?.file_name?.toLowerCase().includes('kontrat') ||
                        (textContent && textContent.includes('# ')));

  useEffect(() => {
    if (isMinimized) return;
    const el = containerRef.current;
    if (!el) return;
    const updateWidth = () => {
      const padding = window.innerWidth < 640 ? 16 : 40;
      const measured = el.clientWidth - padding;
      if (measured > 0 && measured !== containerWidth) setContainerWidth(measured);
    };
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(el);
    return () => observer.disconnect();
  }, [isMinimized, isFullscreen]);

  const getTargetMode = (mimeType: string, fileName: string): ViewerMode => {
    const m = mimeType?.toLowerCase() || '';
    const f = fileName?.toLowerCase() || '';
    if (m.startsWith('image/') || ['.png', '.jpg', '.jpeg', '.webp'].some(ext => f.endsWith(ext))) return 'IMAGE';
    if (m === 'application/pdf' || f.endsWith('.pdf')) return 'PDF';
    if (f.endsWith('.csv') || m.includes('csv')) return 'CSV';
    if (f.endsWith('.txt') || f.endsWith('.json') || m.startsWith('text/')) return 'TEXT';
    return 'PDF';
  };
  
  const handleBlobContent = async (blob: Blob, mode: ViewerMode) => {
      if (mode === 'TEXT' || mode === 'CSV') {
          const text = await blob.text();
          if (mode === 'CSV') {
              const rows = text.split(/\r?\n/).filter(r => r.trim().length > 0);
              const data = rows.map(row => row.split(',').map(cell => cell.trim().replace(/^"|"$/g, '')));
              setCsvContent(data);
              setViewerMode('CSV');
          } else {
              setTextContent(text);
              setViewerMode('TEXT');
          }
          setIsLoading(false);
      } else { 
          const url = URL.createObjectURL(blob);
          setFileSource(url);
          setViewerMode(mode);
          setIsLoading(false);
      }
  };

  const handleMinimizeAction = () => {
    setIsMinimized(true);
    if (onMinimize) {
      onMinimize();
    }
  };

  const handlePageChange = (newPage: number) => {
    if (!numPages) return;
    const clamped = Math.max(1, Math.min(numPages, newPage));
    setPageNumber(clamped);
    setJumpInput(String(clamped));
  };

  const handlePageJumpSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsEditingPage(false);
    const parsed = parseInt(jumpInput, 10);
    if (!isNaN(parsed) && numPages) {
      handlePageChange(parsed);
    } else {
      setJumpInput(String(pageNumber));
    }
  };

  // NATIVE FETCH BLOB PRE-LOADING
  useEffect(() => {
    setError(null);
    setIsLoading(true);
    const targetMode = getTargetMode(documentData?.mime_type || '', documentData?.file_name || documentData?.title || '');
    setViewerMode(targetMode);

    const loadContent = async () => {
        try {
            let pdfStreamUrl = directUrl;
            if (!pdfStreamUrl && caseId && documentData?.id) {
                pdfStreamUrl = `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/preview`;
            }

            if (pdfStreamUrl && pdfStreamUrl.startsWith('blob:')) {
                const response = await fetch(pdfStreamUrl);
                if (!response.ok) throw new Error("Blob fetch failed");
                const blob = await response.blob();
                await handleBlobContent(blob, targetMode);
                return;
            }

            if (pdfStreamUrl) {
                // Native Fetch forces the browser to stream the bytes super fast without Axios bloat
                const token = apiService.getToken();
                const headers: any = {};
                if (token && isAuth) {
                    headers['Authorization'] = `Bearer ${token}`;
                }

                const response = await fetch(pdfStreamUrl, { headers });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const blob = await response.blob();
                await handleBlobContent(blob, targetMode);
            } else {
                setIsLoading(false);
            }
        } catch (err: any) {
            console.error("Native Fetch Failed:", err);
            setError(err?.message || t('pdfViewer.errorFetch'));
            setViewerMode('DOWNLOAD');
            setIsLoading(false);
        }
    };

    loadContent();

    return () => {
        if (typeof fileSource === 'string' && fileSource.startsWith('blob:')) {
            URL.revokeObjectURL(fileSource);
        }
    };
  }, [caseId, documentData?.id, directUrl, isAuth, t]);

  const renderContent = () => {
    if (viewerMode === 'DOWNLOAD') {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 sm:p-8 bg-canvas">
            <AlertTriangle size={56} className="text-amber-500/70 mb-4 animate-pulse" />
            <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-2 max-w-md">
              {documentData?.file_name || documentData?.title || t('pdfViewer.previewNotAvailable')}
            </h3>
            <p className="text-xs text-text-muted mb-6 max-w-sm">
              Pamja e dokumentit nuk mund të ngarkohej direkt.
            </p>
          </div>
        );
    }

    if (viewerMode === 'PDF') {
        return (
            <div className="flex flex-col items-center w-full h-full bg-canvas/20 overflow-auto pt-2 sm:pt-6 pb-28 custom-finance-scroll" ref={containerRef}>
                {isLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-canvas/60 backdrop-blur-xs z-10">
                    <Loader className="animate-spin text-primary-start" size={36} />
                  </div>
                )}
                {fileSource && (
                    <PdfDocument 
                      file={fileSource} 
                      onLoadSuccess={({ numPages }) => { 
                        setNumPages(numPages); 
                        setIsLoading(false); 
                        if (initialPage && initialPage > 0 && initialPage <= numPages) {
                          setPageNumber(initialPage);
                          setJumpInput(String(initialPage));
                        }
                      }} 
                      onLoadError={(err) => {
                        console.error("PDF Render Error:", err);
                        setError("Nuk mund të ngarkohej pamja e PDF.");
                        setViewerMode('DOWNLOAD');
                        setIsLoading(false);
                      }}
                      loading={
                        <div className="flex items-center justify-center p-12">
                          <Loader className="animate-spin text-primary-start" size={32} />
                        </div>
                      }
                      className="flex flex-col items-center w-full px-2 sm:px-0"
                    >
                      {isMobile ? (
                        numPages && Array.from(new Array(numPages), (_, index) => (
                          <Page 
                            key={`page_${index + 1}`}
                            pageNumber={index + 1} 
                            width={containerWidth > 0 ? containerWidth : undefined} 
                            scale={scale} 
                            renderTextLayer={true}
                            renderAnnotationLayer={true}
                            className="shadow-2xl mb-4 rounded-lg overflow-hidden border border-main max-w-full bg-white" 
                          />
                        ))
                      ) : (
                        <Page 
                          pageNumber={pageNumber} 
                          width={containerWidth > 0 ? containerWidth : undefined} 
                          scale={scale} 
                          renderTextLayer={true}
                          renderAnnotationLayer={true}
                          className="shadow-2xl mb-4 rounded-lg overflow-hidden border border-main max-w-full bg-white" 
                        />
                      )}
                    </PdfDocument>
                )}
            </div>
        );
    }

    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-full bg-canvas">
          <Loader className="animate-spin h-10 w-10 text-primary-start" />
        </div>
      );
    }

    switch (viewerMode) {
      case 'TEXT':
        return (
          <div className="p-4 sm:p-10 h-full overflow-auto bg-canvas/40 flex justify-center custom-finance-scroll">
            {isLegalDraft ? (
               <div className="w-full max-w-[21cm] bg-white text-black p-8 sm:p-16 shadow-2xl rounded-sm min-h-[29.7cm] border border-main">
                  <DraftResultRenderer text={textContent || ''} t={t} />
               </div>
            ) : (
                <div className="glass-panel p-6 sm:p-10 rounded-2xl border border-main w-full bg-surface">
                    <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm text-text-secondary leading-relaxed">{textContent}</pre>
                </div>
            )}
          </div>
        );
      case 'CSV':
        return (
            <div className="p-4 sm:p-8 h-full overflow-auto bg-canvas/40 custom-finance-scroll">
                <div className="glass-panel p-0 rounded-2xl border border-main overflow-hidden shadow-2xl bg-surface">
                    <div className="overflow-x-auto custom-finance-scroll">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-surface/20">
                                <tr>
                                    {csvContent?.[0]?.map((header, i) => (
                                        <th key={i} className="p-4 text-[10px] sm:text-xs font-bold text-text-primary uppercase tracking-widest border-b border-main whitespace-nowrap">{header}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-main bg-canvas">
                                {csvContent?.slice(1).map((row, i) => (
                                    <tr key={i} className="hover:bg-hover transition-colors">
                                        {row.map((cell, j) => (
                                          <td key={j} className="p-3 sm:p-4 text-xs sm:text-sm text-text-secondary whitespace-nowrap">{cell}</td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        );
      case 'IMAGE':
        return (
            <div className="flex items-center justify-center h-full p-4 sm:p-10 bg-canvas/40">
                <img src={fileSource!} alt="Preview" className="max-w-full max-h-full object-contain rounded-xl shadow-2xl border border-main" />
            </div>
        );
      default: return null;
    }
  };

  // RENDER MINIMIZED FLOATING PILL
  if (isMinimized) {
    return ReactDOM.createPortal(
      <AnimatePresence>
        <motion.div 
          initial={{ opacity: 0, y: 30, scale: 0.9 }} 
          animate={{ opacity: 1, y: 0, scale: 1 }} 
          exit={{ opacity: 0, y: 30, scale: 0.9 }} 
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="fixed bottom-6 right-6 z-[9999] flex items-center gap-3 px-4 py-3 bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 shadow-2xl rounded-2xl text-white max-w-sm sm:max-w-md cursor-pointer hover:border-sky-500/50 hover:shadow-sky-500/10 transition-all group"
          onClick={() => setIsMinimized(false)}
        >
          <div className="w-10 h-10 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            {viewerMode === 'CSV' ? <TableIcon className="text-sky-400 w-5 h-5" /> : <FileText className="text-sky-400 w-5 h-5" />}
          </div>
          
          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold text-slate-100 truncate">{documentData?.file_name || documentData?.title || 'Dokument'}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-[10px] font-mono text-sky-400/90 font-medium uppercase tracking-wider">
                {isLegalDraft ? 'LEGAL DRAFT' : viewerMode} • I MINIMIZUAR
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0 ml-2 border-l border-slate-700/60 pl-2">
            <button 
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsMinimized(false);
              }} 
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-all cursor-pointer"
              title="Zmadho Dokumentin"
            >
              <Maximize2 size={16} />
            </button>
            
            <button 
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }} 
              className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-xl transition-all cursor-pointer"
              title="Mbyll"
            >
              <X size={16} />
            </button>
          </div>
        </motion.div>
      </AnimatePresence>,
      document.body
    );
  }

  // RENDER FULL DOCUMENT MODAL
  const modalUI = (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }} 
        className="fixed inset-0 bg-black/80 backdrop-blur-md z-[9999] flex items-center justify-center p-0 sm:p-4" 
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.98, opacity: 0, y: 10 }} 
          animate={{ scale: 1, opacity: 1, y: 0 }} 
          transition={{ duration: 0.2 }}
          className={
            isFullscreen 
              ? "fixed inset-0 w-screen h-screen rounded-none z-[9999] bg-canvas flex flex-col overflow-hidden border-0" 
              : "glass-panel w-[95vw] max-w-7xl h-[92vh] rounded-3xl shadow-2xl flex flex-col border border-main bg-canvas overflow-hidden"
          } 
          onClick={e => e.stopPropagation()}
        >
          <header className="flex items-center justify-between p-4 border-b border-main bg-surface shrink-0">
            <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 bg-hover rounded-lg border border-main flex items-center justify-center shrink-0">
                    {viewerMode === 'CSV' ? <TableIcon className="text-primary-start w-5 h-5" /> : <FileText className="text-primary-start w-5 h-5" />}
                </div>
                <div className="min-w-0">
                    <h2 className="text-xs sm:text-sm font-bold text-text-primary truncate max-w-[180px] sm:max-w-md">{documentData?.file_name || documentData?.title}</h2>
                    <span className="text-[9px] font-mono text-text-muted uppercase tracking-widest block truncate">{isLegalDraft ? 'LEGAL DRAFT MODE' : `${viewerMode} MODE`}</span>
                </div>
            </div>

            <div className="flex items-center gap-2">
              {!isMobile && viewerMode === 'PDF' && (
                  <div className="flex items-center gap-1 bg-surface rounded-lg p-1 border border-main mr-2">
                      <button onClick={() => setScale(s => Math.max(s - 0.2, 0.5))} className="p-1.5 text-text-muted hover:text-text-primary cursor-pointer" title="Zoom Out"><ZoomOut size={16} /></button>
                      <button 
                        type="button"
                        onClick={() => setIsFullscreen(!isFullscreen)} 
                        className="p-1.5 text-text-muted hover:text-text-primary cursor-pointer transition-colors" 
                        title={isFullscreen ? "Restauro Madhësinë" : "Ekrani i Plotë (Fullscreen)"}
                      >
                        {isFullscreen ? <Maximize2 size={16} /> : <Maximize size={16} />}
                      </button>
                      <button onClick={() => setScale(s => Math.min(s + 0.2, 3.0))} className="p-1.5 text-text-muted hover:text-text-primary cursor-pointer" title="Zoom In"><ZoomIn size={16} /></button>
                  </div>
              )}

              {/* FULLSCREEN EXPAND TOGGLE BUTTON */}
              <button 
                type="button"
                onClick={() => setIsFullscreen(!isFullscreen)} 
                className="flex items-center justify-center w-10 h-10 text-text-muted hover:text-text-primary hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
                title={isFullscreen ? "Restauro Madhësinë" : "Ekrani i Plotë"}
              >
                {isFullscreen ? <Maximize2 size={18} /> : <Maximize size={18} />}
              </button>

              <button 
                type="button"
                onClick={handleMinimizeAction} 
                className="flex items-center justify-center w-10 h-10 text-text-muted hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
                title="Minimizo"
              >
                <Minus size={20} />
              </button>

              <button 
                type="button"
                onClick={onClose} 
                className="flex items-center justify-center w-10 h-10 text-text-muted hover:text-danger-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
                title="Mbyll"
              >
                <X size={22} />
              </button>
            </div>
          </header>

          <div className="flex-grow relative overflow-hidden bg-canvas">{renderContent()}</div>

          {/* HIGH-CONTRAST DARK GLASSMORPHIC PAGE INDICATOR CONTROL BAR */}
          {!isMobile && viewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-slate-900/95 text-white px-5 py-2.5 rounded-full border border-slate-700/80 flex items-center gap-3 backdrop-blur-2xl z-[100] shadow-2xl">
              <button 
                type="button"
                onClick={() => handlePageChange(pageNumber - 1)} 
                disabled={pageNumber <= 1} 
                className="w-9 h-9 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-800 rounded-full disabled:opacity-20 cursor-pointer transition-all"
                title="Faqja e mëparshme"
              >
                <ChevronLeft size={20} />
              </button>
              
              {isEditingPage ? (
                <form onSubmit={handlePageJumpSubmit} className="flex items-center">
                  <input
                    type="number"
                    value={jumpInput}
                    onChange={(e) => setJumpInput(e.target.value)}
                    onBlur={handlePageJumpSubmit}
                    className="w-14 bg-slate-800 text-white font-mono font-bold text-xs text-center border border-sky-500 rounded-md py-1 focus:outline-none"
                    autoFocus
                  />
                  <span className="text-xs font-mono text-slate-400 ml-1">/ {numPages}</span>
                </form>
              ) : (
                <button
                  type="button"
                  onClick={() => setIsEditingPage(true)}
                  className="px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-xs font-bold text-sky-400 font-mono tracking-wider border border-slate-700/60 hover:border-sky-500/50 transition-all cursor-pointer"
                  title="Kliko për të kërcyer në faqe"
                >
                  Faqja {pageNumber} <span className="text-slate-400 font-normal">/ {numPages}</span>
                </button>
              )}

              <button 
                type="button"
                onClick={() => handlePageChange(pageNumber + 1)} 
                disabled={pageNumber >= numPages} 
                className="w-9 h-9 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-800 rounded-full disabled:opacity-20 cursor-pointer transition-all"
                title="Faqja tjetër"
              >
                <ChevronRight size={20} />
              </button>
            </footer>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalUI, document.body);
};

export default FileViewerModal;
export { FileViewerModal };