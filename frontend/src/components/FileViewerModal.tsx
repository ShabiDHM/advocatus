// FILE: src/components/FileViewerModal.tsx
// PHOENIX PROTOCOL - FILE VIEWER V7.3 (STREAMING OPTIMIZATION)
// 1. PERF: Removed unnecessary Blob download for PDF URLs. Passed direct URL to PDF.js for streaming.
// 2. FIXED: Proper handling of 'isAuth' vs 'directUrl' to prevent double-fetching.
// 3. STATUS: Instant rendering for large PDFs via backend streaming.

import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, Loader, AlertTriangle, ChevronLeft, ChevronRight, 
    Download, ZoomIn, ZoomOut, Maximize, Minus, FileText, Table as TableIcon
} from 'lucide-react';
import { TFunction } from 'i18next';

// PDFJS Worker Configuration
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface FileViewerModalProps {
  documentData: Document;
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
  // --- STATE ---
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

  // --- RESPONSIVE WIDTH CALCULATION ---
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

  // --- HELPERS ---
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
      if (directUrl) {
          if (isAuth) {
              const res = await apiService.axiosInstance.get(directUrl, { responseType: 'blob' });
              blob = res.data;
          } else {
              const res = await fetch(directUrl);
              blob = await res.blob();
          }
      } else if (caseId) {
          blob = await apiService.getOriginalDocument(caseId, documentData.id);
      } else { throw new Error("No source"); }

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = documentData.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (e) { 
        console.error("Download failed", e);
    } finally { setIsDownloading(false); }
  };

  // --- LOAD LOGIC ---
  useEffect(() => {
    setError(null);
    setIsLoading(true);
    const targetMode = getTargetMode(documentData.mime_type || '', documentData.file_name || '');
    setViewerMode(targetMode);

    const loadContent = async () => {
        try {
            // OPTIMIZATION: If it's a PDF and we have a Direct URL, use it directly!
            // Do NOT download it as a Blob first. This allows PDF.js to stream it.
            if (targetMode === 'PDF' && directUrl && !isAuth) {
                setFileSource(directUrl);
                // We don't set isLoading(false) here because PDF.js has its own onLoadSuccess
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
            console.error("Load Content Error:", err);
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

  // --- RENDER HELPERS ---
  const renderContent = () => {
    
    if (viewerMode === 'DOWNLOAD' || error) {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <AlertTriangle size={64} className="text-red-500/50 mb-6" />
            <h3 className="text-xl font-bold text-white mb-2">{t('pdfViewer.previewNotAvailable')}</h3>
            {error && <p className="text-red-400 text-xs mb-6 font-mono bg-red-500/10 px-4 py-2 rounded-lg border border-red-500/20">{error}</p>}
            <button onClick={handleDownloadOriginal} disabled={isDownloading} className="px-8 py-3 bg-primary-start text-white font-bold rounded-xl flex items-center gap-2 active:scale-95 transition-all">
                {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />} {t('pdfViewer.downloadOriginal')}
            </button>
          </div>
        );
    }

    // Special handling for PDF to allow PDF.js loading state
    if (viewerMode === 'PDF') {
        return (
            <div className="flex flex-col items-center w-full h-full bg-black/20 overflow-auto pt-6 pb-24" ref={containerRef}>
                {isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-background-dark/50 z-10">
                        <Loader className="animate-spin text-primary-start" size={32} />
                    </div>
                )}
                {fileSource && (
                    <PdfDocument 
                        file={fileSource} 
                        onLoadSuccess={({ numPages }) => { setNumPages(numPages); setIsLoading(false); }} 
                        onLoadError={() => { setError(t('pdfViewer.corruptFile')); setViewerMode('DOWNLOAD'); setIsLoading(false); }}
                        loading={""} // Suppress default loading text since we have our own spinner
                    >
                        <Page 
                            pageNumber={pageNumber} 
                            width={containerWidth > 0 ? containerWidth : undefined} 
                            scale={scale}
                            renderTextLayer={false} 
                            renderAnnotationLayer={false}
                            className="shadow-2xl mb-4 rounded-lg overflow-hidden border border-white/5" 
                        />
                    </PdfDocument>
                )}
            </div>
        );
    }

    // Default Loading for non-PDF
    if (isLoading) {
        return <div className="flex items-center justify-center h-full"><Loader className="animate-spin h-10 w-10 text-primary-start" /></div>;
    }

    switch (viewerMode) {
      case 'TEXT':
        return (
          <div className="p-6 sm:p-10 h-full overflow-auto bg-black/40">
            <div className="glass-panel p-6 sm:p-10 rounded-2xl border border-white/5">
                <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm text-gray-300 leading-relaxed">{textContent}</pre>
            </div>
          </div>
        );
      case 'CSV':
        return (
            <div className="p-4 sm:p-8 h-full overflow-auto bg-black/40">
                <div className="glass-panel p-0 rounded-2xl border border-white/5 overflow-hidden shadow-2xl">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-white/5">
                                <tr>
                                    {csvContent?.[0]?.map((header, i) => (
                                        <th key={i} className="p-4 text-[10px] sm:text-xs font-bold text-white uppercase tracking-widest border-b border-white/10 whitespace-nowrap">
                                            {header}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {csvContent?.slice(1).map((row, i) => (
                                    <tr key={i} className="hover:bg-white/5 transition-colors">
                                        {row.map((cell, j) => (
                                            <td key={j} className="p-3 sm:p-4 text-xs sm:text-sm text-gray-400 whitespace-nowrap">
                                                {cell}
                                            </td>
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
            <div className="flex items-center justify-center h-full p-4 sm:p-10 bg-black/40">
                <img src={fileSource!} alt="Preview" className="max-w-full max-h-full object-contain rounded-xl shadow-2xl border border-white/10" />
            </div>
        );
      default: return null;
    }
  };

  const modalUI = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-background-dark/95 backdrop-blur-xl z-[9999] flex items-center justify-center p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="bg-background-dark w-full h-full sm:max-w-6xl sm:max-h-[95vh] sm:rounded-3xl shadow-2xl flex flex-col border border-white/10" onClick={e => e.stopPropagation()}>
          
          <header className="flex items-center justify-between p-4 border-b border-white/5 bg-white/5 shrink-0">
            <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 bg-primary-start/20 rounded-lg hidden sm:block">
                    {viewerMode === 'CSV' ? <TableIcon className="text-primary-start w-5 h-5" /> : <FileText className="text-primary-start w-5 h-5" />}
                </div>
                <div className="min-w-0">
                    <h2 className="text-xs sm:text-sm font-bold text-white truncate max-w-[150px] sm:max-w-md">{documentData.file_name}</h2>
                    <span className="text-[9px] font-mono text-gray-500 uppercase tracking-widest">{viewerMode} MODE</span>
                </div>
            </div>
            
            <div className="flex items-center gap-1 sm:gap-2">
              {viewerMode === 'PDF' && (
                  <div className="hidden sm:flex items-center gap-1 bg-black/40 rounded-lg p-1 border border-white/10 mr-2">
                      <button onClick={() => setScale(s => Math.max(s - 0.2, 0.5))} className="p-1.5 text-gray-400 hover:text-white" title={t('actions.zoomOut')}><ZoomOut size={16} /></button>
                      <button onClick={() => setScale(1.0)} className="p-1.5 text-gray-400 hover:text-white" title={t('actions.reset')}><Maximize size={16} /></button>
                      <button onClick={() => setScale(s => Math.min(s + 0.2, 3.0))} className="p-1.5 text-gray-400 hover:text-white" title={t('actions.zoomIn')}><ZoomIn size={16} /></button>
                  </div>
              )}
              <button onClick={handleDownloadOriginal} className="p-2 text-primary-400 hover:bg-white/5 rounded-xl transition-all"><Download size={20} /></button>
              {onMinimize && <button onClick={onMinimize} className="p-2 text-gray-400 hover:bg-white/5 rounded-xl transition-all"><Minus size={20} /></button>}
              <button onClick={onClose} className="p-2 text-gray-400 hover:text-red-400 transition-all"><X size={24} /></button>
            </div>
          </header>
          
          <div className="flex-grow relative overflow-hidden">{renderContent()}</div>
          
          {viewerMode === 'PDF' && numPages && numPages > 1 && (
            <footer className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-black/80 px-5 py-2 rounded-full border border-white/10 flex items-center gap-4 backdrop-blur-xl z-[100]">
              <button onClick={() => setPageNumber(p => Math.max(1, p - 1))} disabled={pageNumber <= 1} className="p-1 text-white disabled:opacity-30"><ChevronLeft size={20} /></button>
              <span className="text-[10px] sm:text-xs font-bold text-white font-mono">{pageNumber} / {numPages}</span>
              <button onClick={() => setPageNumber(p => Math.min(numPages, p + 1))} disabled={pageNumber >= numPages} className="p-1 text-white disabled:opacity-30"><ChevronRight size={20} /></button>
            </footer>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalUI, document.body);
};

export default FileViewerModal;