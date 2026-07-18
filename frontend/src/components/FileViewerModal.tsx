// FILE: src/components/FileViewerModal.tsx
// PHOENIX PROTOCOL - FORMATTED LEGAL EXPORT V6.6
// 1. FIX: Intercepts client-side 'blob:' URLs in loadContent and handleDownloadOriginal to prevent Axios prefixing network leaks.
// 2. POLISH: Integrated useLockBodyScroll, standardized on design tokens, and refined mobile touch targets.

import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, ZoomIn, ZoomOut, Maximize, Minus, FileText, Table as TableIcon
} from 'lucide-react';
import { TFunction } from 'i18next';
import { DraftResultRenderer } from '../drafting/components/DraftResultRenderer';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

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

  // Lock the outer window viewport scroll to eliminate mobile dragging layout bugs
  useLockBodyScroll(true);

  const isLegalDraft = (documentData.category === 'DRAFT' || 
                        documentData.file_name?.toLowerCase().includes('draft') ||
                        documentData.file_name?.toLowerCase().includes('kontrat') ||
                        (textContent && textContent.includes('# ')));

  useEffect(() => {
      const updateWidth = () => {
          if (containerRef.current) {
              const padding = window.innerWidth < 640 ? 20 : 40;
              setContainerWidth(containerRef.current.clientWidth - padding);
          }
      };
      window.addEventListener('resize', updateWidth);
      setTimeout(updateWidth, 300); 
      return () => window.removeEventListener('resize', updateWidth);
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

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
      let blob: Blob;
      let filename = documentData.file_name || documentData.title || 'dokument.txt';

      // 1. Fetch the data - Intercept local browser memory URLs to prevent prefixing
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

      // 2. If it's a legal draft, package it as a styled HTML document
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
    const targetMode = getTargetMode(documentData.mime_type || '', documentData.file_name || documentData.title || '');
    setViewerMode(targetMode);

    const loadContent = async () => {
        try {
            // Bypass remote network requests completely if url is already in local browser memory
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
            } else if (caseId) {
                const blob = await apiService.getOriginalDocument(caseId, documentData.id);
                await handleBlobContent(blob, targetMode);
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
  }, [caseId, documentData.id, directUrl, isAuth, t]);

  const renderContent = () => {
    if (viewerMode === 'DOWNLOAD' || error) {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-8 bg-canvas">
            <AlertTriangle size={64} className="text-danger-start/50 mb-6" />
            <h3 className="text-xl font-bold text-text-primary mb-2">{t('pdfViewer.previewNotAvailable')}</h3>
            <button 
              onClick={handleDownloadOriginal} 
              disabled={isDownloading} 
              className="btn-primary px-8 py-3 rounded-xl flex items-center gap-2 transition-all focus:outline-none"
              style={{ minHeight: '44px' }}
            >
              {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />} {t('pdfViewer.downloadOriginal')}
            </button>
          </div>
        );
    }

    if (viewerMode === 'PDF') {
        return (
            <div className="flex flex-col items-center w-full h-full bg-canvas/20 overflow-auto pt-6 pb-24" ref={containerRef}>
                {isLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-canvas/50 z-10">
                    <Loader className="animate-spin text-primary-start" size={32} />
                  </div>
                )}
                {fileSource && (
                    <PdfDocument file={fileSource} onLoadSuccess={({ numPages }) => { setNumPages(numPages); setIsLoading(false); }} loading="">
                        <Page 
                          pageNumber={pageNumber} 
                          width={containerWidth > 0 ? containerWidth : undefined} 
                          scale={scale} 
                          renderTextLayer={false} 
                          renderAnnotationLayer={false} 
                          className="shadow-2xl mb-4 rounded-lg overflow-hidden border border-main" 
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
        className="fixed inset-0 bg-canvas/95 backdrop-blur-xl z-[9999] flex items-center justify-center p-0 sm:p-4" 
        onClick={onClose}
      >
        <motion.div 
          initial={{ y: 20, opacity: 0 }} 
          animate={{ y: 0, opacity: 1 }} 
          className="glass-panel w-full h-full sm:max-w-6xl sm:max-h-[95vh] sm:rounded-3xl shadow-2xl flex flex-col border border-main bg-canvas" 
          onClick={e => e.stopPropagation()}
        >
          <header className="flex items-center justify-between p-4 border-b border-main bg-surface shrink-0">
            <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 bg-hover rounded-lg hidden sm:block border border-main">
                    {viewerMode === 'CSV' ? <TableIcon className="text-primary-start w-5 h-5" /> : <FileText className="text-primary-start w-5 h-5" />}
                </div>
                <div className="min-w-0">
                    <h2 className="text-xs sm:text-sm font-bold text-text-primary truncate max-w-[150px] sm:max-w-md">{documentData.file_name || documentData.title}</h2>
                    <span className="text-[9px] font-mono text-text-muted uppercase tracking-widest">{isLegalDraft ? 'LEGAL DRAFT MODE' : `${viewerMode} MODE`}</span>
                </div>
            </div>

            <div className="flex items-center gap-1.5 sm:gap-2">
              {viewerMode === 'PDF' && (
                  <div className="hidden sm:flex items-center gap-1 bg-surface rounded-lg p-1 border border-main mr-2">
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
              
              {/* Interactive control elements mapped cleanly to 44px touch-safe zones */}
              <button 
                onClick={handleDownloadOriginal} 
                disabled={isDownloading} 
                className="flex items-center justify-center w-11 h-11 sm:w-10 sm:h-10 text-primary-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                title="Download"
                aria-label="Download document"
              >
                {isDownloading ? <Loader className="animate-spin" size={20} /> : <Download size={20} />}
              </button>

              {onMinimize && (
                <button 
                  onClick={onMinimize} 
                  className="flex items-center justify-center w-11 h-11 sm:w-10 sm:h-10 text-text-muted hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                  title="Minimize"
                  aria-label="Minimize document preview"
                >
                  <Minus size={20} />
                </button>
              )}

              <button 
                onClick={onClose} 
                className="flex items-center justify-center w-11 h-11 sm:w-10 sm:h-10 text-text-muted hover:text-danger-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none"
                title="Close"
                aria-label="Close modal"
              >
                <X size={22} />
              </button>
            </div>
          </header>

          <div className="flex-grow relative overflow-hidden bg-canvas">{renderContent()}</div>

          {viewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-surface px-5 py-2 rounded-full border border-main flex items-center gap-4 backdrop-blur-xl z-[100] shadow-xl">
              <button 
                onClick={() => setPageNumber(p => Math.max(1, p - 1))} 
                disabled={pageNumber <= 1} 
                className="flex items-center justify-center w-11 h-11 text-text-primary disabled:opacity-30 focus:outline-none"
                aria-label="Previous page"
              >
                <ChevronLeft size={20} />
              </button>
              <span className="text-[10px] sm:text-xs font-bold text-text-primary font-mono select-none">{pageNumber} / {numPages}</span>
              <button 
                onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} 
                disabled={pageNumber >= numPages} 
                className="flex items-center justify-center w-11 h-11 text-text-primary disabled:opacity-30 focus:outline-none"
                aria-label="Next page"
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