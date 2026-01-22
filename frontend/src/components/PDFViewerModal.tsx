// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - PDF VIEWER V5.5 (CSV SUPPORT ADDED)
// 1. FEATURE: Added 'CSV' mode for tabular data preview.
// 2. LOGIC: Enhanced MIME detection to catch .csv extensions.
// 3. UI: Added table rendering logic with sticky headers.

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
  // pdfSource can be a string (Blob URL) or an object (Direct URL + Headers)
  const [pdfSource, setPdfSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [csvContent, setCsvContent] = useState<string[][] | null>(null);
  const [imageSource, setImageSource] = useState<string | null>(null);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [useBlobFallback, setUseBlobFallback] = useState(false);
  
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0); 
  const [containerWidth, setContainerWidth] = useState<number>(0); 
  const containerRef = useRef<HTMLDivElement>(null);

  const [actualViewerMode, setActualViewerMode] = useState<'PDF' | 'TEXT' | 'IMAGE' | 'CSV' | 'DOWNLOAD'>('PDF');
  const [isDownloading, setIsDownloading] = useState(false);

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

  const getTargetMode = (mimeType: string, fileName: string) => {
    const m = mimeType?.toLowerCase() || '';
    const f = fileName?.toLowerCase() || '';

    if (m.includes('csv') || f.endsWith('.csv') || m === 'application/vnd.ms-excel') return 'CSV';
    if (m.startsWith('text/') || m === 'application/json' || m.includes('plain')) return 'TEXT';
    if (m.startsWith('image/')) return 'IMAGE';
    return 'PDF';
  };

  // --- FETCHING LOGIC ---

  // 1. The Slow but Secure Way (Blob via Axios)
  // Used for non-PDF files OR as a fallback if the fast PDF path fails
  const fetchAsBlob = async (targetMode: string) => {
      try {
          setIsLoading(true);
          let blob: Blob;

          if (directUrl) {
              if (isAuth) {
                  const response = await apiService.axiosInstance.get(directUrl, { responseType: 'blob' });
                  blob = response.data;
              } else {
                  const response = await fetch(directUrl);
                  if (!response.ok) throw new Error(`Fetch failed: ${response.status}`);
                  blob = await response.blob();
              }
          } else if (caseId) {
              blob = await apiService.getOriginalDocument(caseId, documentData.id);
          } else {
              throw new Error("Missing source configuration");
          }

          if (targetMode === 'PDF') {
              const url = URL.createObjectURL(blob);
              setPdfSource(url); // Passing string forces react-pdf to treat as local file
          } else {
              await handleBlobContent(blob, targetMode);
          }
          
          if (targetMode !== 'PDF') setIsLoading(false);

      } catch (err: any) {
          console.error("Blob Fetch Error:", err);
          handleFinalError(err);
      }
  };

  // 2. The Fast Way (Direct URL + Headers)
  // Used primarily for PDFs to enable streaming
  const initFastPath = () => {
      const targetMode = getTargetMode(documentData.mime_type || '', documentData.file_name || '');
      // Temporary state set, usually overridden by blob content handler or PDF load
      if (targetMode !== 'PDF') {
          // Non-PDFs always go through Blob fetch to ensure we can render text/images/csv securely
          fetchAsBlob(targetMode);
          return;
      }
      
      setActualViewerMode('PDF');

      // If we are already in fallback mode or don't have a direct URL, use Blob
      if (useBlobFallback || !directUrl) {
          fetchAsBlob('PDF');
          return;
      }

      // FAST PATH: Provide URL + Token directly to PDF.js
      // This allows streaming (showing page 1 while downloading page 10)
      const token = apiService.getToken();
      if (isAuth && token) {
          setPdfSource({
              url: directUrl,
              httpHeaders: { 'Authorization': `Bearer ${token}` },
              withCredentials: true
          });
      } else {
          setPdfSource(directUrl);
      }
      // Note: We leave isLoading=true. onLoadSuccess clears it.
  };

  const handleFinalError = (err: any) => {
      const errMsg = err.response?.status === 404 
          ? t('pdfViewer.notFound', { defaultValue: 'Dokumenti nuk u gjet.' })
          : t('pdfViewer.errorFetch', { defaultValue: 'Gabim gjatë ngarkimit.' });
      setError(errMsg);
      setActualViewerMode('DOWNLOAD');
      setIsLoading(false);
  };

  const handleBlobContent = async (blob: Blob, mode: string) => {
      if (mode === 'TEXT' || mode === 'CSV') {
          const text = await blob.text();
          if (mode === 'CSV') {
              // Simple CSV Parser for display purposes
              const rows = text.split(/\r?\n/).filter(r => r.trim().length > 0);
              const data = rows.map(row => {
                  // Basic split handling. For complex CSVs with quoted commas, a more robust parser would be needed,
                  // but this suffices for basic previewing.
                  return row.split(',').map(cell => cell.trim().replace(/^"|"$/g, ''));
              });
              setCsvContent(data);
              setActualViewerMode('CSV');
          } else {
              setTextContent(text);
              setActualViewerMode('TEXT');
          }
      } else {
          const url = URL.createObjectURL(blob);
          setImageSource(url);
          setActualViewerMode('IMAGE');
      }
  };
  
  // Initial Load & Reset on props change
  useEffect(() => {
    setError(null);
    setIsLoading(true);
    setUseBlobFallback(false); // Reset fallback logic
    
    // Tiny timeout to ensure state clears before starting fresh
    const tId = setTimeout(initFastPath, 0);

    return () => { 
        clearTimeout(tId);
        if (imageSource) URL.revokeObjectURL(imageSource);
        if (typeof pdfSource === 'string' && pdfSource.startsWith('blob:')) URL.revokeObjectURL(pdfSource);
    };
  }, [caseId, documentData.id, directUrl]);

  // Effect to trigger Blob Fetch if Fallback is activated
  useEffect(() => {
      if (useBlobFallback && actualViewerMode === 'PDF') {
          console.log("Switching to Blob Fallback for PDF...");
          fetchAsBlob('PDF');
      }
  }, [useBlobFallback]);

  const onPdfLoadSuccess = ({ numPages }: { numPages: number }) => {
      setNumPages(numPages);
      setPageNumber(1);
      setIsLoading(false);
  };

  const onPdfLoadError = (err: any) => {
      console.error("PDF Render Error (Fast Path):", err);
      
      // CRITICAL: If Fast Path fails (likely 401 or CORS), switch to Blob Fallback
      if (!useBlobFallback) {
          setUseBlobFallback(true);
          return;
      }

      // If we failed even in fallback mode, show error
      setError(t('pdfViewer.corruptFile', { defaultValue: 'Skedari nuk mund të shfaqet.' }));
      setIsLoading(false);
      setActualViewerMode('DOWNLOAD');
  };

  const handleDownloadOriginal = async () => {
    setIsDownloading(true);
    try {
      let blob;
      if (directUrl) {
          if (isAuth) {
             const r = await apiService.axiosInstance.get(directUrl, { responseType: 'blob' });
             blob = r.data;
          } else {
             const r = await fetch(directUrl);
             blob = await r.blob();
          }
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
    } catch (e) { 
        console.error(e); 
    } finally { 
        setIsDownloading(false); 
    }
  };

  const zoomIn = () => setScale(prev => Math.min(prev + 0.1, 3.0));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.1, 0.5));
  const zoomReset = () => setScale(1.0);

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
                     <div className="flex flex-col items-center gap-2">
                        <Loader className="animate-spin h-10 w-10 text-primary-start" />
                        {useBlobFallback && <span className="text-xs text-white/70">Sigurimi i lidhjes...</span>}
                     </div>
                 </div>
             )}
             <div className="flex justify-center w-full">
                 {pdfSource && (
                     <PdfDocument 
                        file={pdfSource} 
                        onLoadSuccess={onPdfLoadSuccess}
                        onLoadError={onPdfLoadError}
                        loading={null} 
                        noData={null}
                        // Force remount when switching source types to avoid internal caching issues
                        key={typeof pdfSource === 'string' ? pdfSource : pdfSource.url}
                     >
                         <Page 
                            pageNumber={pageNumber} 
                            width={containerWidth > 0 ? containerWidth : 600} 
                            scale={scale}
                            renderTextLayer={false} 
                            renderAnnotationLayer={false}
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
                    <div className="p-4 bg-white/5 border-b border-white/10 flex justify-between items-center">
                        <span className="text-xs font-mono text-primary-300 uppercase tracking-widest">CSV Preview</span>
                        <span className="text-xs text-gray-500">{csvContent?.length || 0} rows found</span>
                    </div>
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
          
          <header className="flex flex-wrap items-center justify-between p-4 border-b border-white/5 bg-white/5 backdrop-blur-md z-20 gap-3 shrink-0">
            <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="p-2 bg-primary-start/20 rounded-lg border border-primary-start/30">
                    {actualViewerMode === 'CSV' ? <TableIcon className="text-primary-start w-5 h-5" /> : <FileText className="text-primary-start w-5 h-5" />}
                </div>
                <div>
                    <h2 className="text-sm sm:text-base font-bold text-white truncate max-w-[200px] sm:max-w-md">
                        {documentData.file_name}
                    </h2>
                    <span className="text-[10px] font-mono text-text-secondary uppercase tracking-widest flex items-center gap-1">
                        {actualViewerMode} VIEW 
                        {useBlobFallback && <span className="text-amber-400 text-[9px]">(SECURE)</span>}
                    </span>
                </div>
                
                {actualViewerMode === 'PDF' && (
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
                    <Minus size={24} />
                </button>
              )}

              <button onClick={onClose} className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-xl transition-colors" title="Mbyll">
                  <X size={24} />
              </button>
            </div>
          </header>
          
          <div className="flex-grow relative bg-black/20 overflow-auto flex flex-col custom-scrollbar touch-pan-y">
              {renderContent()}
          </div>
          
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