// FILE: src/components/FileViewerModal.tsx
// PHOENIX PROTOCOL - FILE VIEWER MODAL V40.0 (CLEAN 0-WARNING TYPESCRIPT & LIGHTNING FAST PDF STREAMING)

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { AnimatePresence, motion } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    ZoomIn, ZoomOut, Maximize2, Minus, FileText, Table as TableIcon
} from 'lucide-react';
import { TFunction } from 'i18next';
import { DraftResultRenderer } from '../drafting/components/DraftResultRenderer';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

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

type ViewerMode = 'PDF' | 'TEXT' | 'IMAGE' | 'CSV' | 'ERROR';

const FileViewerModal: React.FC<FileViewerModalProps> = ({ 
  documentData, 
  caseId, 
  onClose, 
  onMinimize, 
  t, 
  directUrl, 
  isAuth: _isAuth = false,
  initialPage = 1
}) => {
  const [fileSource, setFileSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [csvContent, setCsvContent] = useState<string[][] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);

  const targetInitialPage = useMemo(() => {
    const candidate = initialPage || 
                      documentData?.initialPage || 
                      documentData?.page_number || 
                      documentData?.pageNumber ||
                      documentData?.page || 
                      documentData?.chunk_page || 
                      documentData?.target_page || 1;
    const parsed = parseInt(String(candidate), 10);
    return !isNaN(parsed) && parsed > 0 ? parsed : 1;
  }, [initialPage, documentData]);

  const [pageNumber, setPageNumber] = useState<number>(targetInitialPage);
  const [jumpInput, setJumpInput] = useState<string>(String(targetInitialPage));
  const [isEditingPage, setIsEditingPage] = useState(false);
  const [scale, setScale] = useState(1.0); 

  const effectiveWidth = useMemo(() => {
    if (typeof window === 'undefined') return 800;
    const w = window.innerWidth;
    if (w < 640) return w - 24;
    if (w <= 1024) return w - 48;
    return Math.min(w - 96, 850);
  }, []);

  const estimatedPageHeight = useMemo(() => effectiveWidth * 1.414 + 16, [effectiveWidth]);

  const containerRef = useRef<HTMLDivElement>(null);
  const [viewerMode, setViewerMode] = useState<ViewerMode>('PDF');
  const [isMinimized, setIsMinimized] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const jumpDirectToPage = useCallback((targetPageNum: number) => {
    if (targetPageNum <= 0) return;
    setPageNumber(targetPageNum);
    setJumpInput(String(targetPageNum));

    const container = containerRef.current;
    if (container) {
      const scrollPos = (targetPageNum - 1) * estimatedPageHeight;
      container.scrollTop = Math.max(0, scrollPos);
    }
  }, [estimatedPageHeight]);

  useEffect(() => {
    if (targetInitialPage > 0) {
      jumpDirectToPage(targetInitialPage);
    }
  }, [targetInitialPage, jumpDirectToPage]);

  useLockBodyScroll(!isMinimized);

  const isLegalDraft = (documentData?.category === 'DRAFT' || 
                        documentData?.file_name?.toLowerCase().includes('draft') ||
                        documentData?.file_name?.toLowerCase().includes('kontrat') ||
                        (textContent && textContent.includes('# ')));

  const getTargetMode = (mimeType: string, fileName: string): ViewerMode => {
    const m = mimeType?.toLowerCase() || '';
    const f = fileName?.toLowerCase() || '';
    if (m.startsWith('image/') || ['.png', '.jpg', '.jpeg', '.webp'].some(ext => f.endsWith(ext))) return 'IMAGE';
    if (m === 'application/pdf' || f.endsWith('.pdf')) return 'PDF';
    if (f.endsWith('.csv') || m.includes('csv')) return 'CSV';
    if (f.endsWith('.txt') || f.endsWith('.json') || m.startsWith('text/')) return 'TEXT';
    return 'PDF';
  };

  const processBlob = useCallback(async (blob: Blob, targetMode: ViewerMode) => {
    if (targetMode === 'TEXT' || targetMode === 'CSV') {
        const text = await blob.text();
        if (targetMode === 'CSV') {
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
        const objectUrl = URL.createObjectURL(blob);
        setFileSource(objectUrl);
        setViewerMode(targetMode);
        setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    setErrorMsg(null);
    setIsLoading(true);

    const targetMode = getTargetMode(
      documentData?.mime_type || '', 
      documentData?.file_name || documentData?.title || ''
    );
    setViewerMode(targetMode);

    let activeUrl = directUrl;

    const loadData = async () => {
      try {
        if (activeUrl && targetMode === 'PDF') {
          setFileSource({
            url: activeUrl,
            withCredentials: true
          });
          setIsLoading(false);
          return;
        }

        if (activeUrl && activeUrl.startsWith('blob:')) {
          if (targetMode === 'PDF' || targetMode === 'IMAGE') {
            setFileSource(activeUrl);
            setIsLoading(false);
          } else {
            const res = await window.fetch(activeUrl);
            const blob = await res.blob();
            await processBlob(blob, targetMode);
          }
          return;
        }

        if (caseId && documentData?.id) {
          const blob = await apiService.getPreviewDocument(caseId, documentData.id);
          await processBlob(blob, targetMode);
          return;
        }

        if (documentData?.id && !caseId) {
          const blob = await apiService.getArchiveFileBlob(documentData.id);
          await processBlob(blob, targetMode);
          return;
        }

        if (activeUrl) {
          setFileSource(activeUrl);
          setIsLoading(false);
          return;
        }

        setIsLoading(false);
      } catch (err: any) {
        console.error("Document preview load error:", err);
        setErrorMsg(err?.message || "Nuk mund të ngarkohej pamja.");
        setViewerMode('ERROR');
        setIsLoading(false);
      }
    };

    loadData();

    return () => {
      if (fileSource && typeof fileSource === 'string' && fileSource.startsWith('blob:') && fileSource !== directUrl) {
        URL.revokeObjectURL(fileSource);
      }
    };
  }, [caseId, documentData?.id, directUrl, processBlob]);

  const handleMinimizeAction = () => {
    setIsMinimized(true);
    if (onMinimize) {
      onMinimize();
    }
  };

  const handlePageChange = (newPage: number) => {
    if (!numPages) return;
    const clamped = Math.max(1, Math.min(numPages, newPage));
    jumpDirectToPage(clamped);
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

  const handleScrollUpdate = useCallback(() => {
    const container = containerRef.current;
    if (!container || !estimatedPageHeight) return;
    const currentScroll = container.scrollTop;
    const computedPage = Math.floor(currentScroll / estimatedPageHeight) + 1;
    if (computedPage > 0 && (!numPages || computedPage <= numPages) && computedPage !== pageNumber) {
      setPageNumber(computedPage);
      setJumpInput(String(computedPage));
    }
  }, [estimatedPageHeight, numPages, pageNumber]);

  const renderContent = () => {
    if (viewerMode === 'ERROR') {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-6 sm:p-8 bg-canvas">
          <AlertTriangle size={56} className="text-amber-500/70 mb-4 animate-pulse" />
          <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-2 max-w-md">
            {documentData?.file_name || documentData?.title || t('pdfViewer.previewNotAvailable', 'Pamja nuk është e disponueshme')}
          </h3>
          <p className="text-xs text-text-muted mb-6 max-w-sm">
            {errorMsg || 'Dokumenti nuk mund të ngarkohej në këtë çast.'}
          </p>
        </div>
      );
    }

    if (isLoading && !fileSource) {
      return (
        <div className="flex flex-col items-center justify-center h-full bg-canvas gap-3">
          <Loader className="animate-spin h-10 w-10 text-primary-start" />
          <p className="text-xs font-mono text-text-muted animate-pulse">Po hapet dokumenti...</p>
        </div>
      );
    }

    if (viewerMode === 'PDF') {
      return (
        <div 
          className="flex flex-col items-center w-full h-full bg-canvas/20 overflow-x-hidden overflow-y-auto pt-4 sm:pt-6 pb-36 custom-finance-scroll" 
          ref={containerRef}
          onScroll={handleScrollUpdate}
        >
          <style>{`
            .react-pdf__Page__textLayer {
              text-align: left !important;
              word-spacing: normal !important;
              letter-spacing: normal !important;
            }
            .react-pdf__Page__textLayer span {
              word-spacing: normal !important;
              letter-spacing: normal !important;
            }
            .react-pdf__Page__canvas {
              max-width: 100% !important;
              height: auto !important;
              margin: 0 auto !important;
            }
          `}</style>
          {fileSource && (
            <PdfDocument 
              file={fileSource} 
              onLoadSuccess={(pdf) => { 
                const total = pdf.numPages;
                setNumPages(total); 
                setIsLoading(false); 
                
                let targetPage = targetInitialPage > 0 && targetInitialPage <= total ? targetInitialPage : 1;
                jumpDirectToPage(targetPage);
              }} 
              onLoadError={(err) => {
                console.error("PDF.js Stream Error:", err);
                setIsLoading(false);
                setErrorMsg("Gabim gjatë leximit të PDF-së.");
                setViewerMode('ERROR');
              }}
              loading={
                <div className="flex flex-col items-center justify-center p-12 gap-3">
                  <Loader className="animate-spin text-primary-start" size={32} />
                  <p className="text-xs font-mono text-text-muted">Duke hapur faqen e kërkuar...</p>
                </div>
              }
              className="flex flex-col items-center w-full px-1 sm:px-0 text-left max-w-full"
            >
              {numPages && Array.from(new Array(numPages), (_, index) => {
                const pageIdx = index + 1;
                const isNearCurrentPage = Math.abs(pageIdx - pageNumber) <= 2;

                return (
                  <div 
                    key={`pdf_page_wrap_${pageIdx}`} 
                    id={`pdf_page_${pageIdx}`} 
                    style={{ height: `${estimatedPageHeight}px` }}
                    className="flex flex-col items-center w-full py-2 shrink-0"
                  >
                    {isNearCurrentPage ? (
                      <Page 
                        pageNumber={pageIdx} 
                        width={effectiveWidth} 
                        scale={scale} 
                        renderTextLayer={true}
                        renderAnnotationLayer={true}
                        loading={
                          <div 
                            style={{ width: effectiveWidth, height: estimatedPageHeight - 16 }} 
                            className="bg-white rounded-lg border border-main shadow-md flex items-center justify-center text-xs text-text-muted font-mono"
                          >
                            Duke vizatuar faqen {pageIdx}...
                          </div>
                        }
                        className="shadow-2xl rounded-lg overflow-hidden border border-main max-w-full bg-white text-left" 
                      />
                    ) : (
                      <div 
                        style={{ width: effectiveWidth, height: estimatedPageHeight - 16 }} 
                        className="bg-canvas/40 rounded-lg border border-main/20 flex items-center justify-center text-xs text-text-muted/40 font-mono"
                      >
                        Faqja {pageIdx}
                      </div>
                    )}
                  </div>
                );
              })}
            </PdfDocument>
          )}
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
                <div className="glass-panel p-6 sm:p-10 rounded-2xl border border-main w-full bg-surface text-left">
                    <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm text-text-secondary leading-relaxed text-left">{textContent}</pre>
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

  if (isMinimized) {
    return ReactDOM.createPortal(
      <AnimatePresence>
        <motion.div 
          initial={{ opacity: 0, y: 30, scale: 0.9 }} 
          animate={{ opacity: 1, y: 0, scale: 1 }} 
          exit={{ opacity: 0, y: 30, scale: 0.9 }} 
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

  const modalUI = (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-[9999] flex items-center justify-center p-0 sm:p-4" onClick={onClose}>
      <div 
        className={
          isFullscreen 
            ? "fixed inset-0 w-screen h-screen rounded-none z-[9999] bg-canvas flex flex-col overflow-hidden border-0" 
            : "glass-panel w-full sm:w-[95vw] max-w-7xl h-full sm:h-[92vh] rounded-none sm:rounded-3xl shadow-2xl flex flex-col border-0 sm:border border-main bg-canvas overflow-hidden"
        } 
        onClick={e => e.stopPropagation()}
      >
        <header className="flex items-center justify-between p-3 sm:p-4 border-b border-main bg-surface shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <div className="p-2 bg-hover rounded-lg border border-main flex items-center justify-center shrink-0">
                  {viewerMode === 'CSV' ? <TableIcon className="text-primary-start w-4 h-4 sm:w-5 sm:h-5" /> : <FileText className="text-primary-start w-4 h-4 sm:w-5 sm:h-5" />}
              </div>
              <div className="min-w-0">
                  <h2 className="text-xs sm:text-sm font-bold text-text-primary truncate max-w-[140px] sm:max-w-md">{documentData?.file_name || documentData?.title}</h2>
                  <span className="text-[9px] font-mono text-text-muted uppercase tracking-widest block truncate">{isLegalDraft ? 'LEGAL DRAFT MODE' : `${viewerMode} MODE`}</span>
              </div>
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            {viewerMode === 'PDF' && (
                <div className="flex items-center gap-1 bg-surface rounded-lg p-1 border border-main mr-2">
                    <button onClick={() => setScale(s => Math.max(s - 0.2, 0.5))} className="p-1.5 text-text-muted hover:text-text-primary cursor-pointer" title="Zoom Out"><ZoomOut size={16} /></button>
                    <button onClick={() => setScale(1.0)} className="px-2 py-0.5 text-xs font-mono font-bold text-text-secondary hover:text-text-primary cursor-pointer" title="Reset Zoom">{Math.round(scale * 100)}%</button>
                    <button onClick={() => setScale(s => Math.min(s + 0.2, 3.0))} className="p-1.5 text-text-muted hover:text-text-primary cursor-pointer" title="Zoom In"><ZoomIn size={16} /></button>
                </div>
            )}

            <button 
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)} 
              className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:text-text-primary hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
              title={isFullscreen ? "Restauro Madhësinë" : "Ekrani i Plotë"}
            >
              <Maximize2 size={18} />
            </button>

            <button 
              type="button"
              onClick={handleMinimizeAction} 
              className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
              title="Minimizo"
            >
              <Minus size={18} />
            </button>

            <button 
              type="button"
              onClick={onClose} 
              className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:text-danger-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
              title="Mbyll"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="flex-grow relative overflow-hidden bg-canvas">{renderContent()}</div>

        {viewerMode === 'PDF' && numPages && numPages > 1 && (
          <footer className="absolute bottom-4 sm:bottom-6 left-1/2 -translate-x-1/2 bg-slate-900/95 text-white px-4 sm:px-5 py-2 sm:py-2.5 rounded-full border border-slate-700/80 flex items-center gap-2 sm:gap-3 backdrop-blur-2xl z-[100] shadow-2xl">
            <button 
              type="button"
              onClick={() => handlePageChange(pageNumber - 1)} 
              disabled={pageNumber <= 1} 
              className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-800 rounded-full disabled:opacity-20 cursor-pointer transition-all"
              title="Faqja e mëparshme"
            >
              <ChevronLeft size={18} />
            </button>
            
            {isEditingPage ? (
              <form onSubmit={handlePageJumpSubmit} className="flex items-center">
                <input
                  type="number"
                  value={jumpInput}
                  onChange={(e) => setJumpInput(e.target.value)}
                  onBlur={handlePageJumpSubmit}
                  className="w-12 sm:w-14 bg-slate-800 text-white font-mono font-bold text-xs text-center border border-sky-500 rounded-md py-1 focus:outline-none"
                  autoFocus
                />
                <span className="text-xs font-mono text-slate-400 ml-1">/ {numPages}</span>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setIsEditingPage(true)}
                className="px-2.5 sm:px-3 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-xs font-bold text-sky-400 font-mono tracking-wider border border-slate-700/60 hover:border-sky-500/50 transition-all cursor-pointer"
                title="Kliko për të kërcyer në faqe"
              >
                Faqja {pageNumber} <span className="text-slate-400 font-normal">/ {numPages}</span>
              </button>
            )}

            <button 
              type="button"
              onClick={() => handlePageChange(pageNumber + 1)} 
              disabled={pageNumber >= numPages} 
              className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-800 rounded-full disabled:opacity-20 cursor-pointer transition-all"
              title="Faqja tjetër"
            >
              <ChevronRight size={18} />
            </button>
          </footer>
        )}
      </div>
    </div>
  );

  return ReactDOM.createPortal(modalUI, document.body);
};

export default FileViewerModal;
export { FileViewerModal };