// FILE: src/components/FileViewerModal.tsx
// PHOENIX PROTOCOL - FILE VIEWER MODAL V10.0 (MOBILE-OPTIMIZED PDF FALLBACK & EXECUTIVE VIEW)

import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, ZoomIn, ZoomOut, Maximize, Minus, FileText, Table as TableIcon, ExternalLink
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
}

type ViewerMode = 'PDF' | 'TEXT' | 'IMAGE' | 'CSV' | 'DOWNLOAD';

const FileViewerModal: React.FC<FileViewerModalProps> = ({ 
  documentData, 
  caseId, 
  onClose, 
  onMinimize, 
  t, 
  directUrl, 
  isAuth = false 
}) => {
  const [fileSource, setFileSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [csvContent, setCsvContent] = useState<string[][] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0); 
  const [containerWidth, setContainerWidth] = useState<number>(0); 
  const containerRef = useRef<HTMLDivElement>(null);
  const [viewerMode, setViewerMode] = useState<ViewerMode>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);

  useLockBodyScroll(true);

  // Detect mobile device to bypass flaky mobile PDF web workers & Android Chrome iframe traps
  const isMobile = typeof window !== 'undefined' && (/Mobi|Android|iPhone|iPad/i.test(navigator.userAgent) || window.innerWidth < 768);

  const isLegalDraft = (documentData?.category === 'DRAFT' || 
                        documentData?.file_name?.toLowerCase().includes('draft') ||
                        documentData?.file_name?.toLowerCase().includes('kontrat') ||
                        (textContent && textContent.includes('# ')));

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const updateWidth = () => {
      const padding = window.innerWidth < 640 ? 16 : 40;
      const measured = el.clientWidth - padding;
      if (measured > 0) setContainerWidth(measured);
    };
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(el);
    return () => observer.disconnect();
  }, [viewerMode]);

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
      } else { 
          const url = URL.createObjectURL(blob);
          setFileSource(url);
          setViewerMode(mode);
      }
      setIsLoading(false);
  };

  const handleOpenInNewTab = () => {
    if (fileSource && typeof fileSource === 'string') {
        window.open(fileSource, '_blank');
    } else if (directUrl) {
        window.open(directUrl, '_blank');
    } else {
        handleDownloadOriginal();
    }
  };

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
      let blob: Blob;
      let filename = documentData?.file_name || documentData?.title || 'dokument.pdf';

      if (directUrl) {
          if (directUrl.startsWith('blob:')) {
              const res = await fetch(directUrl);
              blob = await res.blob();
          } else if (isAuth) {
              const res = await apiService.axiosInstance.get(directUrl, { responseType: 'blob' });
              blob = res.data;
          } else {
              const res = await fetch(directUrl);
              blob = await res.blob();
          }
      } else if (caseId && documentData?.id) {
          blob = await apiService.getOriginalDocument(caseId, documentData.id);
      } else { throw new Error("No source"); }

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (e) { 
        console.error("Download failed", e);
    } finally { setIsDownloading(false); }
  };

  useEffect(() => {
    setError(null);
    setIsLoading(true);
    const targetMode = getTargetMode(documentData?.mime_type || '', documentData?.file_name || documentData?.title || '');
    setViewerMode(targetMode);

    const loadContent = async () => {
        try {
            if (directUrl && directUrl.startsWith('blob:')) {
                if (targetMode === 'PDF') {
                    setFileSource(directUrl);
                    setIsLoading(false);
                    return;
                }
                const response = await fetch(directUrl);
                if (!response.ok) throw new Error("Blob fetch failed");
                const blob = await response.blob();
                await handleBlobContent(blob, targetMode);
                return;
            }

            if (targetMode === 'PDF' && directUrl && !isAuth) {
                setFileSource(directUrl);
                setIsLoading(false);
                return; 
            }
            if (directUrl) {
                if (isAuth) {
                    const response = await apiService.axiosInstance.get(directUrl, { responseType: 'blob' });
                    await handleBlobContent(response.data, targetMode);
                } else {
                    const response = await fetch(directUrl);
                    if (!response.ok) throw new Error("Fetch failed");
                    const blob = await response.blob();
                    await handleBlobContent(blob, targetMode);
                }
            } else if (caseId && documentData?.id) {
                const blob = await apiService.getOriginalDocument(caseId, documentData.id);
                await handleBlobContent(blob, targetMode);
            } else {
                setIsLoading(false);
            }
        } catch (err: any) {
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
    if (viewerMode === 'DOWNLOAD' || error) {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 sm:p-8 bg-canvas">
            <AlertTriangle size={56} className="text-amber-500/70 mb-4 animate-pulse" />
            <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-2 max-w-md">
              {documentData?.file_name || documentData?.title || t('pdfViewer.previewNotAvailable')}
            </h3>
            <p className="text-xs text-text-muted mb-6 max-w-sm">
              Shfletuesi celular kërkon hapjen e dokumentit në një skedë të re për ta shfaqur pa gabime.
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button 
                onClick={handleOpenInNewTab} 
                className="btn-primary px-6 py-3 rounded-xl flex items-center justify-center gap-2 font-medium transition-all text-xs sm:text-sm shadow-lg"
                style={{ minHeight: '44px' }}
              >
                <ExternalLink size={18} /> Hap Dokumentin
              </button>
              <button 
                onClick={handleDownloadOriginal} 
                disabled={isDownloading} 
                className="px-6 py-3 rounded-xl bg-surface hover:bg-hover border border-main text-text-primary flex items-center justify-center gap-2 font-medium transition-all text-xs sm:text-sm"
                style={{ minHeight: '44px' }}
              >
                {isDownloading ? <Loader size={18} className="animate-spin" /> : <Download size={18} />} {t('pdfViewer.downloadOriginal')}
              </button>
            </div>
          </div>
        );
    }

    if (viewerMode === 'PDF') {
        // ON MOBILE DEVICES: Render clean executive action view to prevent Android Chrome iframe/pdf fallback bug
        if (isMobile) {
            return (
                <div className="flex flex-col items-center justify-center h-full text-center p-6 sm:p-8 bg-canvas">
                    <div className="w-16 h-16 rounded-2xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center mb-4">
                        <FileText size={32} className="text-primary-start" />
                    </div>
                    <h3 className="text-base sm:text-lg font-bold text-text-primary mb-2 max-w-sm truncate">
                      {documentData?.file_name || documentData?.title || 'Dokument PDF'}
                    </h3>
                    <p className="text-xs text-text-muted mb-6 max-w-xs">
                      Përvojë optimale në pajisjet celulare. Klikoni më poshtë për ta hapur direkt ose shkarkuar.
                    </p>
                    <div className="flex flex-col gap-3 w-full max-w-xs">
                      <button 
                        onClick={handleOpenInNewTab} 
                        className="btn-primary px-6 py-3.5 rounded-xl flex items-center justify-center gap-2 font-medium transition-all text-sm shadow-lg"
                        style={{ minHeight: '48px' }}
                      >
                        <ExternalLink size={18} /> Hap PDF në Shfletues
                      </button>
                      <button 
                        onClick={handleDownloadOriginal} 
                        disabled={isDownloading} 
                        className="px-6 py-3.5 rounded-xl bg-surface hover:bg-hover border border-main text-text-primary flex items-center justify-center gap-2 font-medium transition-all text-sm"
                        style={{ minHeight: '48px' }}
                      >
                        {isDownloading ? <Loader size={18} className="animate-spin" /> : <Download size={18} />} {t('pdfViewer.downloadOriginal')}
                      </button>
                    </div>
                </div>
            );
        }

        // ON DESKTOP: Render canvas PDF viewer
        return (
            <div className="flex flex-col items-center w-full h-full bg-canvas/20 overflow-auto pt-6 pb-24 custom-finance-scroll" ref={containerRef}>
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
                      }} 
                      onLoadError={(err) => {
                        console.error("PDF Render Error:", err);
                        setError("Nuk mund të ngarkohej pamja e PDF.");
                        setViewerMode('DOWNLOAD');
                        setIsLoading(false);
                      }}
                      loading=""
                    >
                        <Page 
                          pageNumber={pageNumber} 
                          width={containerWidth > 0 ? containerWidth : undefined} 
                          scale={scale} 
                          renderTextLayer={true}
                          renderAnnotationLayer={true}
                          className="shadow-2xl mb-4 rounded-lg overflow-hidden border border-main max-w-full" 
                        />
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

  const modalUI = (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} 
        animate={{ opacity: 1 }} 
        exit={{ opacity: 0 }} 
        className="fixed inset-0 bg-black/80 backdrop-blur-md z-[9999] flex items-center justify-center p-2 sm:p-4" 
        onClick={onClose}
      >
        {/* STANDARDIZED EXECUTIVE SIZE: 95VW x 92VH */}
        <motion.div 
          initial={{ scale: 0.98, opacity: 0, y: 10 }} 
          animate={{ scale: 1, opacity: 1, y: 0 }} 
          transition={{ duration: 0.2 }}
          className="glass-panel w-[95vw] max-w-7xl h-[92vh] rounded-3xl shadow-2xl flex flex-col border border-main bg-canvas overflow-hidden" 
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
                      <button onClick={() => setScale(s => Math.max(s - 0.2, 0.5))} className="p-1.5 text-text-muted hover:text-text-primary" title="Zoom Out"><ZoomOut size={16} /></button>
                      <button onClick={() => setScale(1.0)} className="p-1.5 text-text-muted hover:text-text-primary" title="Reset Zoom"><Maximize size={16} /></button>
                      <button onClick={() => setScale(s => Math.min(s + 0.2, 3.0))} className="p-1.5 text-text-muted hover:text-text-primary" title="Zoom In"><ZoomIn size={16} /></button>
                  </div>
              )}

              <button 
                onClick={handleOpenInNewTab} 
                className="flex items-center justify-center w-10 h-10 text-text-muted hover:text-text-primary hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                title="Hape ne tab te ri"
              >
                <ExternalLink size={18} />
              </button>
              
              <button 
                onClick={handleDownloadOriginal} 
                disabled={isDownloading} 
                className="flex items-center justify-center w-10 h-10 text-primary-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                title="Download"
              >
                {isDownloading ? <Loader className="animate-spin" size={20} /> : <Download size={20} />}
              </button>

              {onMinimize && (
                <button 
                  onClick={onMinimize} 
                  className="flex items-center justify-center w-10 h-10 text-text-muted hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                  title="Minimize"
                >
                  <Minus size={20} />
                </button>
              )}

              <button 
                onClick={onClose} 
                className="flex items-center justify-center w-10 h-10 text-text-muted hover:text-danger-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                title="Close"
              >
                <X size={22} />
              </button>
            </div>
          </header>

          <div className="flex-grow relative overflow-hidden bg-canvas">{renderContent()}</div>

          {!isMobile && viewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-surface px-5 py-2 rounded-full border border-main flex items-center gap-4 backdrop-blur-xl z-[100] shadow-xl">
              <button onClick={() => setPageNumber(p => Math.max(1, p - 1))} disabled={pageNumber <= 1} className="w-11 h-11 flex items-center justify-center text-text-primary disabled:opacity-30"><ChevronLeft size={20} /></button>
              <span className="text-xs font-bold text-text-primary font-mono select-none">{pageNumber} / {numPages}</span>
              <button onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} disabled={pageNumber >= numPages} className="w-11 h-11 flex items-center justify-center text-text-primary disabled:opacity-30"><ChevronRight size={20} /></button>
            </footer>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalUI, document.body);
};

export default FileViewerModal;