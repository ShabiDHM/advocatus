// FILE: src/components/FileViewerModal.tsx
// PHOENIX PROTOCOL - FILE VIEWER MODAL V63.1
//
// V63.1: FIX worker — CDN jsdelivr me version dinamik.
//   - Hequr import `pdfjs-dist/build/pdf.worker.min.mjs?url` (file nuk ekziston në v3.x)
//   - Përdoret `pdfjs.version` (dinamik) për CDN URL
//   - jsdelivr (më i qëndrueshëm se unpkg)
//
// V63.0: Content-Type validation + fallback + console logs.
// V62.1: FIX TS2353 — article_number + fusha opsionale.
// V62.0: FIX download → stream (blob fetch).

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ReactDOM from 'react-dom';
import { Document as PdfDocument, Page, pdfjs } from 'react-pdf';
import { apiService } from '../services/api';
import { AnimatePresence } from 'framer-motion';
import {
  X, Loader, AlertTriangle, ChevronLeft, ChevronRight,
  ZoomIn, ZoomOut, Maximize2, Minus, FileText, Table as TableIcon,
} from 'lucide-react';
import type { TFunction } from 'i18next';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

// ═══════════════════════════════════════════════════════════════════════════
// PDF.JS WORKER — V63.1 (CDN jsdelivr me version dinamik)
// ═══════════════════════════════════════════════════════════════════════════
// `pdfjs.version` vjen nga react-pdf dhe përputhet automatikisht me versionin
// e pdfjs-dist që react-pdf pret. jsdelivr është CDN e qëndrueshme, mbështet
// versionim të saktë dhe nuk ka downtime të shpeshtë si unpkg.

const WORKER_VERSION = pdfjs.version;
pdfjs.GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${WORKER_VERSION}/build/pdf.worker.min.mjs`;

console.log('[FileViewerModal] pdf.js version =', WORKER_VERSION);
console.log('[FileViewerModal] pdf.js worker =', pdfjs.GlobalWorkerOptions.workerSrc);

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

type ViewerMode = 'PDF' | 'TEXT' | 'IMAGE' | 'CSV' | 'ERROR';

interface FileViewerDocumentData {
  file_name?: string;
  title?: string;
  mime_type?: string;
  id?: string;
  _id?: string;
  article_number?: string;
  page_number?: number | null;
  page?: number | null;
  initialPage?: number | null;
  pageNumber?: number | null;
  chunk_page?: number | null;
  target_page?: number | null;
}

interface FileViewerModalProps {
  documentData: FileViewerDocumentData;
  caseId?: string;
  onClose: () => void;
  onMinimize?: () => void;
  t: TFunction;
  directUrl?: string | null;
  isAuth?: boolean;
  initialPage?: number | null;
}

// ═══════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.bmp', '.tiff'];
const PRESIGNED_PATTERNS = ['X-Amz-', 'backblazeb2.com', 'Signature=', 'r2.cloudflarestorage.com'];

function getTargetMode(mimeType: string, fileName: string): ViewerMode {
  const m = (mimeType || '').toLowerCase();
  const f = (fileName || '').toLowerCase();

  if (m.startsWith('image/') || IMAGE_EXTENSIONS.some((ext) => f.endsWith(ext))) {
    return 'IMAGE';
  }
  if (m === 'application/pdf' || f.endsWith('.pdf')) {
    return 'PDF';
  }
  if (f.endsWith('.csv') || m.includes('csv')) {
    return 'CSV';
  }
  if (f.endsWith('.txt') || f.endsWith('.json') || m.startsWith('text/')) {
    return 'TEXT';
  }
  return 'PDF';
}

function isPresignedUrl(url: string): boolean {
  return PRESIGNED_PATTERNS.some((p) => url.includes(p));
}

function isPdfContentType(contentType: string): boolean {
  const ct = (contentType || '').toLowerCase();
  return ct.includes('pdf') || ct.includes('octet-stream');
}

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

const FileViewerModal: React.FC<FileViewerModalProps> = ({
  documentData,
  caseId,
  onClose,
  onMinimize,
  t,
  directUrl,
  isAuth: _isAuth = false,
  initialPage,
}) => {
  const [fileSource, setFileSource] = useState<any>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [csvContent, setCsvContent] = useState<string[][] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [viewerMode, setViewerMode] = useState<ViewerMode>('PDF');

  const [fallbackUrl, setFallbackUrl] = useState<string | null>(null);
  const [fallbackHeaders, setFallbackHeaders] = useState<Record<string, string> | null>(null);

  const targetInitialPage = useMemo<number | null>(() => {
    const candidates = [initialPage, documentData?.page_number, documentData?.page];
    for (const c of candidates) {
      const parsed = typeof c === 'number' ? c : parseInt(String(c ?? ''), 10);
      if (!isNaN(parsed) && parsed > 0) return parsed;
    }
    return null;
  }, [initialPage, documentData?.page_number, documentData?.page]);

  const [pageNumber, setPageNumber] = useState<number>(targetInitialPage ?? 1);
  const [jumpInput, setJumpInput] = useState<string>(String(targetInitialPage ?? 1));
  const [isEditingPage, setIsEditingPage] = useState(false);
  const [scale, setScale] = useState(1.0);

  const effectiveWidth = useMemo(() => {
    if (typeof window === 'undefined') return 800;
    const w = window.innerWidth;
    if (w < 640) return w - 24;
    if (w <= 1024) return w - 48;
    return Math.min(w - 96, 850);
  }, []);

  const internalBlobUrlRef = useRef<string | null>(null);
  const fetchAbortRef = useRef<AbortController | null>(null);

  const [isMinimized, setIsMinimized] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (targetInitialPage !== null && targetInitialPage > 0) {
      setPageNumber(targetInitialPage);
      setJumpInput(String(targetInitialPage));
    }
  }, [targetInitialPage]);

  useLockBodyScroll(!isMinimized);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isMinimized) {
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, isMinimized]);

  // ═══════════════════════════════════════════════════════════════════════
  // BLOB PROCESSING
  // ═══════════════════════════════════════════════════════════════════════

  const processBlob = useCallback(async (blob: Blob, targetMode: ViewerMode) => {
    if (targetMode === 'TEXT' || targetMode === 'CSV') {
      const text = await blob.text();
      if (targetMode === 'CSV') {
        const rows = text.split(/\r?\n/).filter((r) => r.trim().length > 0);
        const data = rows.map((row) =>
          row.split(',').map((cell) => cell.trim().replace(/^"|"$/g, '')),
        );
        setCsvContent(data);
        setViewerMode('CSV');
      } else {
        setTextContent(text);
        setViewerMode('TEXT');
      }
      setIsLoading(false);
    } else {
      const objectUrl = URL.createObjectURL(blob);
      internalBlobUrlRef.current = objectUrl;
      setFileSource(objectUrl);
      setViewerMode(targetMode);
      setIsLoading(false);
    }
  }, []);

  // ═══════════════════════════════════════════════════════════════════════
  // LOAD DOCUMENT
  // ═══════════════════════════════════════════════════════════════════════

  useEffect(() => {
    setErrorMsg(null);
    setIsLoading(true);
    setFileSource(null);
    setTextContent(null);
    setCsvContent(null);
    setFallbackUrl(null);
    setFallbackHeaders(null);

    const targetMode = getTargetMode(
      documentData?.mime_type || '',
      documentData?.file_name || documentData?.title || '',
    );
    setViewerMode(targetMode);

    fetchAbortRef.current?.abort();
    const abortController = new AbortController();
    fetchAbortRef.current = abortController;

    const loadData = async () => {
      try {
        const token = apiService.getToken();

        // CASE 1: Blob URL
        if (directUrl && directUrl.startsWith('blob:')) {
          if (targetMode === 'TEXT' || targetMode === 'CSV') {
            const res = await fetch(directUrl, { signal: abortController.signal });
            const blob = await res.blob();
            if (abortController.signal.aborted) return;
            await processBlob(blob, targetMode);
          } else {
            setFileSource(directUrl);
            setIsLoading(false);
          }
          return;
        }

        // CASE 2: HTTP/HTTPS URL
        if (
          directUrl &&
          (directUrl.startsWith('http://') ||
            directUrl.startsWith('https://') ||
            directUrl.startsWith('/'))
        ) {
          if (isPresignedUrl(directUrl)) {
            setFileSource(directUrl);
            setIsLoading(false);
            return;
          }

          const headers: Record<string, string> = {};
          if (token) {
            headers['Authorization'] = `Bearer ${token}`;
          }

          setFallbackUrl(directUrl);
          setFallbackHeaders(headers);

          const res = await fetch(directUrl, {
            method: 'GET',
            headers,
            signal: abortController.signal,
          });

          if (abortController.signal.aborted) return;

          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
          }

          const contentType = res.headers.get('content-type') || '';
          const contentLength = res.headers.get('content-length') || '?';

          console.log('[FileViewerModal] Response:', {
            url: directUrl,
            status: res.status,
            contentType,
            contentLength,
          });

          if (!isPdfContentType(contentType)) {
            const preview = await res.clone().text().catch(() => '');
            console.error('[FileViewerModal] Non-PDF response:', preview.slice(0, 500));
            throw new Error(
              `Serveri ktheu '${contentType}' në vend të PDF. ` +
              `Kontrollo që dokumenti ekziston në server.`,
            );
          }

          const blob = await res.blob();
          if (abortController.signal.aborted) return;

          console.log('[FileViewerModal] Blob size:', blob.size, 'type:', blob.type);

          await processBlob(blob, targetMode);
          return;
        }

        // CASE 3: Fetch nga ID
        const docId = documentData?.id || documentData?._id;
        if (caseId && docId) {
          const blob = await apiService.getPreviewDocument(caseId, docId);
          if (abortController.signal.aborted) return;
          await processBlob(blob, targetMode);
          return;
        }

        if (docId && !caseId) {
          const blob = await apiService.getArchiveFileBlob(docId);
          if (abortController.signal.aborted) return;
          await processBlob(blob, targetMode);
          return;
        }

        setIsLoading(false);
      } catch (err: any) {
        if (err?.name === 'AbortError') return;
        console.error('[FileViewerModal] Load error:', err);
        if (!abortController.signal.aborted) {
          setErrorMsg(err?.message || 'Nuk mund të ngarkohej pamja.');
          setViewerMode('ERROR');
          setIsLoading(false);
        }
      }
    };

    loadData();

    return () => {
      abortController.abort();
    };
  }, [
    caseId,
    documentData?.id,
    documentData?._id,
    documentData?.mime_type,
    documentData?.file_name,
    documentData?.title,
    directUrl,
    processBlob,
  ]);

  useEffect(() => {
    return () => {
      if (internalBlobUrlRef.current) {
        URL.revokeObjectURL(internalBlobUrlRef.current);
        internalBlobUrlRef.current = null;
      }
    };
  }, []);

  // ═══════════════════════════════════════════════════════════════════════
  // HANDLERS
  // ═══════════════════════════════════════════════════════════════════════

  const handleMinimizeAction = () => {
    setIsMinimized(true);
    if (onMinimize) onMinimize();
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

  const handlePdfLoadError = useCallback(
    (err: any) => {
      console.error('[FileViewerModal] PDF.js error:', err);

      if (fallbackUrl && fallbackHeaders && internalBlobUrlRef.current) {
        console.log('[FileViewerModal] Fallback në direct URL');

        URL.revokeObjectURL(internalBlobUrlRef.current);
        internalBlobUrlRef.current = null;

        setFileSource({
          url: fallbackUrl,
          httpHeaders: fallbackHeaders,
          withCredentials: true,
        });
        return;
      }

      setIsLoading(false);
      const detail = err?.message ? ` (${err.message})` : '';
      setErrorMsg(`Gabim gjatë leximit të PDF-së.${detail}`);
      setViewerMode('ERROR');
    },
    [fallbackUrl, fallbackHeaders],
  );

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER: Content
  // ═══════════════════════════════════════════════════════════════════════

  const renderContent = () => {
    if (viewerMode === 'ERROR') {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center p-6 sm:p-8 bg-canvas">
          <AlertTriangle size={56} className="text-amber-500/70 mb-4 animate-pulse" />
          <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-2 max-w-md break-all">
            {documentData?.file_name || documentData?.title || t('pdfViewer.previewNotAvailable', 'Pamja nuk është e disponueshme')}
          </h3>
          <p className="text-xs text-text-muted mb-6 max-w-md break-words">
            {errorMsg || 'Dokumenti nuk mund të ngarkohej në këtë çast.'}
          </p>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold cursor-pointer"
          >
            {t('general.close', 'Mbyll')}
          </button>
        </div>
      );
    }

    if (isLoading && !fileSource) {
      return (
        <div className="flex flex-col items-center justify-center h-full bg-canvas gap-3">
          <Loader className="animate-spin h-10 w-10 text-primary-start" />
          <p className="text-xs font-mono text-text-muted animate-pulse">
            {t('pdfViewer.loadingDoc', 'Po hapet dokumenti...')}
          </p>
        </div>
      );
    }

    if (viewerMode === 'PDF') {
      return (
        <div className="flex flex-col items-center justify-start w-full h-full bg-canvas/20 overflow-y-auto pt-4 sm:pt-6 pb-28 custom-finance-scroll">
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
                console.log('[FileViewerModal] PDF loaded, pages:', pdf.numPages);
                const total = pdf.numPages;
                setNumPages(total);
                setIsLoading(false);

                const target =
                  targetInitialPage !== null &&
                  targetInitialPage > 0 &&
                  targetInitialPage <= total
                    ? targetInitialPage
                    : 1;
                setPageNumber(target);
                setJumpInput(String(target));
              }}
              onLoadError={handlePdfLoadError}
              loading={
                <div className="flex flex-col items-center justify-center p-12 gap-3">
                  <Loader className="animate-spin text-primary-start" size={32} />
                  <p className="text-xs font-mono text-text-muted">
                    {t('pdfViewer.loadingPdf', 'Duke hapur PDF-in...')}
                  </p>
                </div>
              }
              className="flex flex-col items-center w-full px-1 sm:px-0 text-left max-w-full"
            >
              <div className="shadow-2xl rounded-lg overflow-hidden border border-main bg-white text-left max-w-full my-2">
                <Page
                  pageNumber={pageNumber}
                  width={effectiveWidth}
                  scale={scale}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                  loading={
                    <div
                      style={{ width: effectiveWidth, height: effectiveWidth * 1.414 }}
                      className="bg-white rounded-lg border border-main shadow-md flex items-center justify-center text-xs text-text-muted font-mono"
                    >
                      {t('pdfViewer.rendering', 'Duke vizatuar faqen')} {pageNumber}...
                    </div>
                  }
                />
              </div>
            </PdfDocument>
          )}
        </div>
      );
    }

    switch (viewerMode) {
      case 'TEXT':
        return (
          <div className="p-4 sm:p-10 h-full overflow-auto bg-canvas/40 flex justify-center custom-finance-scroll">
            <div className="glass-panel p-6 sm:p-10 rounded-2xl border border-main w-full bg-surface text-left">
              <pre className="whitespace-pre-wrap font-mono text-xs sm:text-sm text-text-secondary leading-relaxed text-left">
                {textContent}
              </pre>
            </div>
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
                        <th
                          key={i}
                          className="p-4 text-[10px] sm:text-xs font-bold text-text-primary uppercase tracking-widest border-b border-main whitespace-nowrap"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-main bg-canvas">
                    {csvContent?.slice(1).map((row, i) => (
                      <tr key={i} className="hover:bg-hover transition-colors">
                        {row.map((cell, j) => (
                          <td
                            key={j}
                            className="p-3 sm:p-4 text-xs sm:text-sm text-text-secondary whitespace-nowrap"
                          >
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
          <div className="flex items-center justify-center h-full p-4 sm:p-10 bg-canvas/40">
            <img
              src={fileSource!}
              alt={t('pdfViewer.imagePreview', 'Preview')}
              className="max-w-full max-h-full object-contain rounded-xl shadow-2xl border border-main"
            />
          </div>
        );
      default:
        return null;
    }
  };

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER: Minimized
  // ═══════════════════════════════════════════════════════════════════════

  if (isMinimized) {
    return ReactDOM.createPortal(
      <AnimatePresence>
        <div
          className="fixed bottom-6 right-6 z-[9999] flex items-center gap-3 px-4 py-3 bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 shadow-2xl rounded-2xl text-white max-w-sm sm:max-w-md cursor-pointer hover:border-sky-500/50 hover:shadow-sky-500/10 transition-all group"
          onClick={() => setIsMinimized(false)}
        >
          <div className="w-10 h-10 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            {viewerMode === 'CSV' ? (
              <TableIcon className="text-sky-400 w-5 h-5" />
            ) : (
              <FileText className="text-sky-400 w-5 h-5" />
            )}
          </div>

          <div className="min-w-0 flex-1">
            <p className="text-xs font-bold text-slate-100 truncate">
              {documentData?.file_name || documentData?.title || 'Dokument'}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-[10px] font-mono text-sky-400/90 font-medium uppercase tracking-wider">
                {viewerMode} • I MINIMIZUAR
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
              title={t('pdfViewer.expand', 'Zmadho Dokumentin')}
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
              title={t('general.close', 'Mbyll')}
            >
              <X size={16} />
            </button>
          </div>
        </div>
      </AnimatePresence>,
      document.body,
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // RENDER: Full modal
  // ═══════════════════════════════════════════════════════════════════════

  const modalUI = (
    <div
      className="fixed inset-0 bg-black/80 backdrop-blur-md z-[9999] flex items-center justify-center p-0 sm:p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="file-viewer-title"
    >
      <div
        className={
          isFullscreen
            ? 'fixed inset-0 w-screen h-screen rounded-none z-[9999] bg-canvas flex flex-col overflow-hidden border-0'
            : 'glass-panel w-full sm:w-[95vw] max-w-7xl h-full sm:h-[92vh] rounded-none sm:rounded-3xl shadow-2xl flex flex-col border-0 sm:border border-main bg-canvas overflow-hidden'
        }
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between p-3 sm:p-4 border-b border-main bg-surface shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <div className="p-2 bg-hover rounded-lg border border-main flex items-center justify-center shrink-0">
              {viewerMode === 'CSV' ? (
                <TableIcon className="text-primary-start w-4 h-4 sm:w-5 sm:h-5" />
              ) : (
                <FileText className="text-primary-start w-4 h-4 sm:w-5 sm:h-5" />
              )}
            </div>
            <div className="min-w-0">
              <h2
                id="file-viewer-title"
                className="text-xs sm:text-sm font-bold text-text-primary truncate max-w-[140px] sm:max-w-md"
              >
                {documentData?.file_name || documentData?.title}
              </h2>
              <span className="text-[9px] font-mono text-text-muted uppercase tracking-widest block truncate">
                {viewerMode} MODE
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            {viewerMode === 'PDF' && (
              <div className="flex items-center gap-1 bg-surface rounded-lg p-1 border border-main mr-2">
                <button
                  onClick={() => setScale((s) => Math.max(s - 0.2, 0.5))}
                  className="p-1.5 text-text-muted hover:text-text-primary cursor-pointer"
                  title={t('pdfViewer.zoomOut', 'Zoom Out')}
                >
                  <ZoomOut size={16} />
                </button>
                <button
                  onClick={() => setScale(1.0)}
                  className="px-2 py-0.5 text-xs font-mono font-bold text-text-secondary hover:text-text-primary cursor-pointer"
                  title={t('pdfViewer.resetZoom', 'Reset Zoom')}
                >
                  {Math.round(scale * 100)}%
                </button>
                <button
                  onClick={() => setScale((s) => Math.min(s + 0.2, 3.0))}
                  className="p-1.5 text-text-muted hover:text-text-primary cursor-pointer"
                  title={t('pdfViewer.zoomIn', 'Zoom In')}
                >
                  <ZoomIn size={16} />
                </button>
              </div>
            )}

            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:text-text-primary hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
              title={
                isFullscreen
                  ? t('pdfViewer.restore', 'Restauro Madhësinë')
                  : t('pdfViewer.fullscreen', 'Ekrani i Plotë')
              }
            >
              <Maximize2 size={18} />
            </button>

            <button
              type="button"
              onClick={handleMinimizeAction}
              className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
              title={t('pdfViewer.minimize', 'Minimizo')}
            >
              <Minus size={18} />
            </button>

            <button
              type="button"
              onClick={onClose}
              className="flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 text-text-muted hover:text-danger-start hover:bg-hover border border-main sm:border-transparent rounded-xl transition-all focus:outline-none cursor-pointer"
              title={t('general.close', 'Mbyll')}
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
              title={t('pdfViewer.prevPage', 'Faqja e mëparshme')}
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
                title={t('pdfViewer.jumpToPage', 'Kliko për të kërcyer në faqe')}
              >
                {t('pdfViewer.page', 'Faqja')} {pageNumber}{' '}
                <span className="text-slate-400 font-normal">/ {numPages}</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => handlePageChange(pageNumber + 1)}
              disabled={pageNumber >= numPages}
              className="w-8 h-8 sm:w-9 sm:h-9 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-800 rounded-full disabled:opacity-20 cursor-pointer transition-all"
              title={t('pdfViewer.nextPage', 'Faqja tjetër')}
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