// FILE: src/components/FileViewerModal.tsx
// PHOENIX PROTOCOL - FILE VIEWER MODAL V9.0 (MOBILE & DESKTOP FULL-SPECTRUM COMPATIBILITY)

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

// Import essential react-pdf styles to ensure interactive text overlay alignments
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

// Standardized highly reliable CDN worker source to bypass mobile CORS/MIME blocks
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

  // Lock the outer window viewport scroll to eliminate dragging layout bugs
  useLockBodyScroll(true);

  const isLegalDraft = (documentData?.category === 'DRAFT' || 
                        documentData?.file_name?.toLowerCase().includes('draft') ||
                        documentData?.file_name?.toLowerCase().includes('kontrat') ||
                        (textContent && textContent.includes('# ')));

  // Instant & ResizeObserver responsive width observer for immediate mobile scaling
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const updateWidth = () => {
      const padding = window.innerWidth < 640 ? 16 : 40;
      const measured = el.clientWidth - padding;
      if (measured > 0) {
        setContainerWidth(measured);
      }
    };

    updateWidth();

    const observer = new ResizeObserver(() => {
      updateWidth();
    });
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
      let filename = documentData.file_name || documentData.title || 'dokument.txt';

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
      } else if (caseId) {
          blob = await apiService.getOriginalDocument(caseId, documentData.id);
      } else { throw new Error("No source"); }

      if (isLegalDraft && textContent) {
          const htmlContent = `
            <!DOCTYPE html>
            <html lang="sq">
            <head>
                <meta charset="UTF-8">
                <title>${filename}</title>
                <style>
                    body { background: #f4f4f7; padding: 50px; font-family: "Times New Roman", Times, serif; color: black; line-height: 1.6; }
                    .a4-page { background: white; width: 210mm; min-height: 297mm; margin: 0 auto; padding: 25mm; box-shadow: 0 0 10px rgba(0,0,0,0.1); box-sizing: border-box; }
                    h1 { text-align: center; font-size: 18pt; text-transform: uppercase; margin-bottom: 30px; }
                    h2 { text-align: center; font-size: 14pt; text-transform: uppercase; margin-top: 25px; margin-bottom: 15px; }
                    p { text-align: justify; margin-bottom: 15px; font-size: 11pt; }
                    .placeholder { background: #fef3c7; border: 1px solid #fcd34d; padding: 0 4px; font-weight: bold; border-radius: 2px; }
                    @media print { body { background: white; padding: 0; } .a4-page { box-shadow: none; margin: 0; width: 100%; } }
                </style>
            </head>
            <body>
                <div class="a4-page">
                    ${textContent
                        .replace(/^# (.*$)/gim, '<h1>$1</h1>')
                        .replace(/^## (.*$)/gim, '<h2>$1</h2>')
                        .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
                        .replace(/\[([^\]]+)\]/g, '<span class="placeholder">[$1]</span>')
                        .split('\n\n').map(p => p.trim().startsWith('<h') ? p : `<p>${p}</p>`).join('')}
                </div>
            </body>
            </html>
          `;
          blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
          filename = filename.replace('.txt', '.html');
          if (!filename.endsWith('.html')) filename += '.html';
      }

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
                if (!response.ok) throw new Error("Local blob fetch failed");
                const blob = await response.blob();
                await handleBlobContent(blob, targetMode);
                return;
            }

            if (targetMode === 'PDF' && directUrl && !isAuth) {
                setFileSource(directUrl);
                return; 
            }
            if (directUrl) {
                if (isAuth) {
                    const response = await apiService.axiosInstance.get(directUrl, { responseType: 'blob' });
                    await handleBlobContent(response.data, targetMode);
                } else {
                    const response = await fetch(directUrl);
                    if (!response.ok) throw new Error("Network Response Fail");
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
              Formati ose shfletuesi celular nuk mbështet shikimin direk. Mund ta hapni ose shkarkoni me poshtë.
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
        return (
            <div className="flex flex-col items-center w-full h-full bg-canvas/20 overflow-auto pt-4 sm:pt-6 pb-20 sm:pb-24 custom-finance-scroll" ref={containerRef}>
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
          <div className="p-3 sm:p-10 h-full overflow-auto bg-canvas/40 flex justify-center custom-finance-scroll">
            {isLegalDraft ? (
               <div className="w-full max-w-[21cm] bg-white text-black p-6 sm:p-16 shadow-2xl rounded-sm min-h-[29.7cm] border border-main">
                  <DraftResultRenderer text={textContent || ''} t={t} />
               </div>
            ) : (
                <div className="glass-panel p-4 sm:p-10 rounded-2xl border border-main w-full bg-surface">
                    <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm text-text-secondary leading-relaxed">{textContent}</pre>
                </div>
            )}
          </div>
        );
      case 'CSV':
        return (
            <div className="p-3 sm:p-8 h-full overflow-auto bg-canvas/40 custom-finance-scroll">
                <div className="glass-panel p-0 rounded-2xl border border-main overflow-hidden shadow-2xl bg-surface">
                    <div className="overflow-x-auto custom-finance-scroll">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-surface/20">
                                <tr>
                                    {csvContent?.[0]?.map((header, i) => (
                                        <th key={i} className="p-3 sm:p-4 text-[10px] sm:text-xs font-bold text-text-primary uppercase tracking-widest border-b border-main whitespace-nowrap">{header}</th>
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
            <div className="flex items-center justify-center h-full p-3 sm:p-10 bg-canvas/40">
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
          className="glass-panel w-[95vw] max-w-7xl h-[92vh] rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col border border-main bg-canvas overflow-hidden" 
          onClick={e => e.stopPropagation()}
        >
          <header className="flex items-center justify-between p-3 sm:p-4 border-b border-main bg-surface shrink-0">
            <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
                <div className="p-2 bg-hover rounded-lg border border-main flex items-center justify-center shrink-0">
                    {viewerMode === 'CSV' ? <TableIcon className="text-primary-start w-4 h-4 sm:w-5 sm:h-5" /> : <FileText className="text-primary-start w-4 h-4 sm:w-5 sm:h-5" />}
                </div>
                <div className="min-w-0">
                    <h2 className="text-xs sm:text-sm font-bold text-text-primary truncate max-w-[150px] sm:max-w-md">{documentData?.file_name || documentData?.title}</h2>
                    <span className="text-[9px] font-mono text-text-muted uppercase tracking-widest block truncate">{isLegalDraft ? 'LEGAL DRAFT MODE' : `${viewerMode} MODE`}</span>
                </div>
            </div>

            <div className="flex items-center gap-1 sm:gap-2">
              {viewerMode === 'PDF' && (
                  <div className="hidden sm:flex items-center gap-1 bg-surface rounded-lg p-1 border border-main mr-1">
                      <button 
                        onClick={() => setScale(s => Math.max(s - 0.2, 0.5))} 
                        className="p-1.5 text-text-muted hover:text-text-primary focus:outline-none"
                        title="Zoom Out"
                        aria-label="Zoom Out"
                      >
                        <ZoomOut size={16} />
                      </button>
                      <button 
                        onClick={() => setScale(1.0)} 
                        className="p-1.5 text-text-muted hover:text-text-primary focus:outline-none"
                        title="Reset Zoom"
                        aria-label="Reset Zoom"
                      >
                        <Maximize size={16} />
                      </button>
                      <button 
                        onClick={() => setScale(s => Math.min(s + 0.2, 3.0))} 
                        className="p-1.5 text-text-muted hover:text-text-primary focus:outline-none"
                        title="Zoom In"
                        aria-label="Zoom In"
                      >
                        <ZoomIn size={16} />
                      </button>
                  </div>
              )}

              <button 
                onClick={handleOpenInNewTab} 
                className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:text-text-primary hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                title="Hape ne tab te ri"
                aria-label="Open in new tab"
              >
                <ExternalLink size={18} />
              </button>
              
              <button 
                onClick={handleDownloadOriginal} 
                disabled={isDownloading} 
                className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-primary-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                title="Download"
                aria-label="Download document"
              >
                {isDownloading ? <Loader className="animate-spin" size={18} /> : <Download size={18} />}
              </button>

              {onMinimize && (
                <button 
                  onClick={onMinimize} 
                  className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                  title="Minimize"
                  aria-label="Minimize document preview"
                >
                  <Minus size={18} />
                </button>
              )}

              <button 
                onClick={onClose} 
                className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:text-danger-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                title="Close"
                aria-label="Close modal"
              >
                <X size={20} />
              </button>
            </div>
          </header>

          <div className="flex-grow relative overflow-hidden bg-canvas">{renderContent()}</div>

          {viewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="absolute bottom-3 sm:bottom-6 left-1/2 -translate-x-1/2 bg-surface/90 px-4 sm:px-5 py-1.5 sm:py-2 rounded-full border border-main flex items-center gap-3 sm:gap-4 backdrop-blur-xl z-[100] shadow-2xl">
              <button 
                onClick={() => setPageNumber(p => Math.max(1, p - 1))} 
                disabled={pageNumber <= 1} 
                className="flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 text-text-primary disabled:opacity-30 focus:outline-none"
                aria-label="Previous page"
              >
                <ChevronLeft size={18} />
              </button>
              <span className="text-[10px] sm:text-xs font-bold text-text-primary font-mono select-none">{pageNumber} / {numPages}</span>
              <button 
                onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} 
                disabled={pageNumber >= numPages} 
                className="flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 text-text-primary disabled:opacity-30 focus:outline-none"
                aria-label="Next page"
              >
                <ChevronRight size={18} />
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