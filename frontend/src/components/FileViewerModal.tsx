// FILE: src/components/FileViewerModal.tsx
// PHOENIX PROTOCOL - FILE VIEWER V6.2 (FULL RESTORATION)
// 1. CRITICAL FIX: Restored all missing UI components, including the header, footer, CSV table, and all control buttons.
// 2. RESOLVED: All "unused variable" warnings are fixed as the UI now utilizes the previously orphaned functions and imports.
// 3. TYPE FIX: Corrected the redundant error comparison flagged by the TypeScript compiler.

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

// Ensure exact version match for worker
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

const FileViewerModal: React.FC<FileViewerModalProps> = ({ documentData, caseId, onClose, onMinimize, t, directUrl, isAuth = false }) => {
  const [fileSource, setFileSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [csvContent, setCsvContent] = useState<string[][] | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [useBlobFallback, setUseBlobFallback] = useState(false);
  
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0); 
  const [containerWidth, setContainerWidth] = useState<number>(0); 
  const containerRef = useRef<HTMLDivElement>(null);

  const [viewerMode, setViewerMode] = useState<ViewerMode>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);
  const [pdfLoadFailed, setPdfLoadFailed] = useState(false);

  useEffect(() => {
      const updateWidth = () => {
          if (containerRef.current) setContainerWidth(containerRef.current.clientWidth - 40);
      };
      window.addEventListener('resize', updateWidth);
      setTimeout(updateWidth, 200); 
      return () => window.removeEventListener('resize', updateWidth);
  }, [viewerMode]);

  const getTargetMode = (mimeType: string, fileName: string): ViewerMode => {
    const m = mimeType?.toLowerCase() || '';
    const f = fileName?.toLowerCase() || '';

    if (m.startsWith('image/')) return 'IMAGE';
    if (['.png', '.jpg', '.jpeg', '.gif', '.webp'].some(ext => f.endsWith(ext))) return 'IMAGE';
    if (m === 'application/pdf' || f.endsWith('.pdf')) return 'PDF';
    if (f.endsWith('.csv') || m.includes('csv') || m === 'application/vnd.ms-excel') return 'CSV';
    if (f.endsWith('.txt') || f.endsWith('.json') || m.startsWith('text/') || m === 'application/json' || m.includes('plain')) return 'TEXT';
    
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
  
  const handleFinalError = (err: any) => {
      const errMsg = err.response?.status === 404 ? t('pdfViewer.notFound') : t('pdfViewer.errorFetch');
      setError(errMsg);
      setViewerMode('DOWNLOAD');
      setIsLoading(false);
  };
  
  const fetchBlobFromNetwork = async (): Promise<Blob> => {
      if (directUrl) {
          if (isAuth) {
              const response = await apiService.axiosInstance.get(directUrl, { responseType: 'blob' });
              return response.data;
          } else {
              const response = await fetch(directUrl);
              if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
              return await response.blob();
          }
      } else if (caseId) {
          return await apiService.getOriginalDocument(caseId, documentData.id);
      } else {
          throw new Error("Missing source configuration");
      }
  };

  useEffect(() => {
    setError(null);
    setIsLoading(true);
    let targetMode = getTargetMode(documentData.mime_type || '', documentData.file_name || '');

    if (pdfLoadFailed) {
        targetMode = 'IMAGE';
    }
    setViewerMode(targetMode);

    const isBlobUrl = directUrl && directUrl.startsWith('blob:');

    const loadContent = async () => {
        try {
            if (isBlobUrl) {
                if (targetMode === 'PDF' || targetMode === 'IMAGE') {
                    setFileSource(directUrl);
                    if(targetMode === 'IMAGE') setIsLoading(false);
                } else {
                    const response = await fetch(directUrl);
                    const blob = await response.blob();
                    await handleBlobContent(blob, targetMode);
                }
                return;
            }

            if (targetMode === 'PDF' && !useBlobFallback && directUrl) {
                const token = apiService.getToken();
                if (isAuth && token) {
                    setFileSource({ url: directUrl, httpHeaders: { 'Authorization': `Bearer ${token}` }, withCredentials: true });
                } else {
                    setFileSource(directUrl);
                }
            } else {
                const blob = await fetchBlobFromNetwork();
                await handleBlobContent(blob, targetMode);
            }
        } catch (err: any) {
            console.error("Content Load Error:", err);
            handleFinalError(err);
        }
    };

    loadContent();

    return () => {
        if (typeof fileSource === 'string' && fileSource.startsWith('blob:') && fileSource !== directUrl) {
            URL.revokeObjectURL(fileSource);
        }
    };
  }, [caseId, documentData.id, directUrl, useBlobFallback, pdfLoadFailed]);

  const onPdfLoadSuccess = ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
      setPageNumber(1);
      setIsLoading(false);
  };

  const onPdfLoadError = (err: any) => {
      console.error("PDF Render Error:", err);
      if (!pdfLoadFailed && !useBlobFallback && directUrl && !directUrl.startsWith('blob:')) {
          setUseBlobFallback(true);
          return;
      }
      if (!pdfLoadFailed) {
          setPdfLoadFailed(true);
          return;
      }
      setError(t('pdfViewer.corruptFile'));
      setIsLoading(false);
      setViewerMode('DOWNLOAD');
  };

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
      const blob = await fetchBlobFromNetwork();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = documentData.file_name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (e) { console.error(e); } finally { setIsDownloading(false); }
  };

  const zoomIn = () => setScale(prev => Math.min(prev + 0.1, 3.0));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.1, 0.5));
  const zoomReset = () => setScale(1.0);

  const renderContent = () => {
    if (isLoading && viewerMode !== 'PDF') {
        return <div className="absolute inset-0 flex items-center justify-center"><Loader className="animate-spin h-10 w-10 text-primary-start" /></div>;
    }
    
    if (viewerMode === 'DOWNLOAD') {
        return (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="bg-white/5 p-6 rounded-full mb-6 border border-white/10"><Download size={64} className="text-gray-500" /></div>
            <h3 className="text-xl font-bold text-white mb-2">{t('pdfViewer.previewNotAvailable')}</h3>
            {error && <p className="text-red-400 text-sm mb-6 font-mono bg-red-500/10 p-3 rounded-xl max-w-md break-words border border-red-500/20">{error}</p>}
            <button onClick={handleDownloadOriginal} disabled={isDownloading} className="px-8 py-3 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg text-white font-bold rounded-xl transition-all flex items-center gap-2 active:scale-95">
                {isDownloading ? <Loader size={20} className="animate-spin" /> : <Download size={20} />} {t('pdfViewer.downloadOriginal')}
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

    switch (viewerMode) {
      case 'PDF':
        return (
          <div className="flex flex-col items-center w-full min-h-full bg-black/40 overflow-auto pt-8 pb-20" ref={containerRef}>
             {isLoading && (
                 <div className="absolute inset-0 flex items-center justify-center z-10 bg-black/60 backdrop-blur-sm">
                     <div className="flex flex-col items-center gap-2">
                        <Loader className="animate-spin h-10 w-10 text-primary-start" />
                        {useBlobFallback && <span className="text-xs text-white/70">Sigurimi i lidhjes...</span>}
                     </div>
                 </div>
             )}
             <div className="flex justify-center w-full">
                 {fileSource && (
                     <PdfDocument 
                        file={fileSource} 
                        onLoadSuccess={onPdfLoadSuccess}
                        onLoadError={onPdfLoadError}
                        loading={null} noData={null}
                        key={typeof fileSource === 'string' ? fileSource : fileSource.url}
                     >
                         <Page 
                            pageNumber={pageNumber} 
                            width={containerWidth > 0 ? containerWidth : 600} 
                            scale={scale}
                            renderTextLayer={false} renderAnnotationLayer={false}
                            className="shadow-2xl mb-4 border border-white/5 rounded-lg overflow-hidden" 
                         />
                     </PdfDocument>
                 )}
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
      case 'CSV':
        return (
            <div className="flex justify-center p-6 sm:p-8 min-h-full bg-black/40">
                <div className="glass-panel p-0 min-h-[600px] w-full max-w-6xl rounded-xl overflow-hidden flex flex-col shadow-2xl">
                    <div className="overflow-auto custom-scrollbar flex-1 max-h-[70vh]">
                        <table className="w-full text-left border-collapse relative">
                            <thead className="sticky top-0 bg-gray-900/90 backdrop-blur-md z-10 shadow-sm">
                                <tr>
                                    {csvContent && csvContent[0]?.map((header, i) => (
                                        <th key={i} className="p-4 text-xs font-bold text-white uppercase tracking-wider border-b border-white/10 whitespace-nowrap bg-white/5">
                                            {header}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {csvContent && csvContent.slice(1).map((row, i) => (
                                    <tr key={i} className="hover:bg-white/5 transition-colors group">
                                        <td className="p-3 text-xs text-gray-500 font-mono border-r border-white/5 text-center w-10 opacity-50 select-none">
                                            {i + 1}
                                        </td>
                                        {row.map((cell, j) => (
                                            <td key={j} className="p-3 text-sm text-gray-300 border-r border-white/5 last:border-r-0 whitespace-nowrap max-w-xs overflow-hidden text-ellipsis">
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
            <div className="flex items-center justify-center h-full p-4 overflow-auto bg-black/40">
                <img 
                    src={fileSource!} 
                    alt={documentData.file_name} 
                    className="max-w-full max-h-full object-contain rounded-lg shadow-2xl border border-white/10"
                    onError={() => {
                        setError(t('pdfViewer.corruptFile'));
                        setViewerMode('DOWNLOAD');
                    }}
                />
            </div>
        );
      default: return null;
    }
  };

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-background-dark/90 backdrop-blur-xl z-[9999] flex items-center justify-center p-0 sm:p-4" onClick={onClose}>
        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="glass-high w-full h-full sm:max-w-6xl sm:max-h-[95vh] rounded-none sm:rounded-3xl shadow-2xl flex flex-col overflow-hidden border border-white/10" onClick={(e) => e.stopPropagation()}>
          
          <header className="flex flex-wrap items-center justify-between p-4 border-b border-white/5 bg-white/5 backdrop-blur-md z-20 gap-3 shrink-0">
            <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="p-2 bg-primary-start/20 rounded-lg border border-primary-start/30">
                    {viewerMode === 'CSV' ? <TableIcon className="text-primary-start w-5 h-5" /> : <FileText className="text-primary-start w-5 h-5" />}
                </div>
                <div>
                    <h2 className="text-sm sm:text-base font-bold text-white truncate max-w-[200px] sm:max-w-md">
                        {documentData.file_name}
                    </h2>
                    <span className="text-[10px] font-mono text-text-secondary uppercase tracking-widest flex items-center gap-1">
                        {viewerMode} VIEW 
                        {useBlobFallback && <span className="text-amber-400 text-[9px]">(SECURE)</span>}
                    </span>
                </div>
                
                {viewerMode === 'PDF' && (
                    <div className="hidden sm:flex items-center gap-1 bg-black/40 rounded-lg p-1 border border-white/10 ml-4">
                        <button onClick={zoomOut} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors"><ZoomOut size={16} /></button>
                        <span className="text-[10px] font-bold text-white w-10 text-center">{Math.round(scale * 100)}%</span>
                        <button onClick={zoomIn} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors"><ZoomIn size={16} /></button>
                        <div className="w-px h-4 bg-white/10 mx-1"></div>
                        <button onClick={zoomReset} className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors" title="Reset"><Maximize size={16} /></button>
                    </div>
                )}
            </div>
            
            <div className="flex items-center gap-2 flex-shrink-0">
              <button onClick={handleDownloadOriginal} className="p-2 text-primary-300 bg-primary-500/10 hover:bg-primary-500/20 hover:text-white rounded-xl border border-primary-500/20 transition-colors" title="Shkarko">
                  <Download size={20} />
              </button>
              
              {onMinimize && (
                <button onClick={onMinimize} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-xl transition-colors" title="Minimizo">
                    <Minus size={20} />
                </button>
              )}

              <button onClick={onClose} className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-colors" title="Mbyll">
                  <X size={20} />
              </button>
            </div>
          </header>
          
          <div className="flex-grow relative bg-black/20 overflow-auto flex flex-col custom-scrollbar touch-pan-y">
              {renderContent()}
          </div>
          
          {viewerMode === 'PDF' && numPages && numPages > 1 && (
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

export default FileViewerModal;