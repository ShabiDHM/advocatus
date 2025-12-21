// FILE: src/components/PDFViewerModal.tsx
// PHOENIX PROTOCOL - PDF VIEWER V3.9 (DEFINITIVE FIX)
// 1. FIX (Mobile): The PDF worker is now loaded from the local /public folder, removing the unreliable external network dependency.
// 2. FIX (Fullscreen): Resolved the "Stacking Context Trap" by conditionally disabling the parent's 'transform' when fullscreen is active.

import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { apiService, API_V1_URL } from '../services/api';
import { Document } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader, AlertTriangle, RefreshCw, Minus } from 'lucide-react';
import { TFunction } from 'i18next';

import { Viewer, Worker, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin, ToolbarProps, ToolbarSlot } from '@react-pdf-viewer/default-layout';

import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';

// PHOENIX FIX: Point to the local worker file in the /public folder.
const workerUrl = "/pdf.worker.min.js";

interface PDFViewerModalProps {
  documentData: Document;
  caseId?: string; 
  onClose: () => void;
  onMinimizeRequest?: () => void; 
  t: TFunction; 
  directUrl?: string | null; 
  isAuth?: boolean;
}

const PDFViewerModal: React.FC<PDFViewerModalProps> = ({ documentData, caseId, onClose, onMinimizeRequest, t, directUrl, isAuth = false }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const renderToolbar = (Toolbar: (props: ToolbarProps) => React.ReactElement) => (
    <Toolbar>
        {(slots: ToolbarSlot) => {
            const { CurrentPageInput, Download, EnterFullScreen, GoToNextPage, GoToPreviousPage, NumberOfPages, Print, ShowSearchPopover, ZoomIn, ZoomOut } = slots;
            return (
                <div className="flex items-center justify-between w-full p-1 bg-[#101010] border-b border-white/10">
                    <div className="flex items-center"><div className="p-1"><ShowSearchPopover /></div><div className="p-1"><ZoomOut /></div><div className="p-1"><ZoomIn /></div></div>
                    <div className="flex items-center"><div className="p-1"><GoToPreviousPage /></div><div className="flex items-center mx-1"><CurrentPageInput /> / <NumberOfPages /></div><div className="p-1"><GoToNextPage /></div></div>
                    <div className="flex items-center">
                        <div className="p-1"><EnterFullScreen /></div>
                        <div className="p-1"><Download>{(props) => (<button className="rpv-toolbar__button" onClick={props.onClick} title={t('actions.download', 'Shkarko')}><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg></button>)}</Download></div>
                        <div className="p-1"><Print /></div>
                        {onMinimizeRequest && (<div className="p-1 border-l border-white/10 ml-2"><button className="rpv-toolbar__button" onClick={onMinimizeRequest} title="Minimize"><Minus size={20} /></button></div>)}
                    </div>
                </div>
            );
        }}
    </Toolbar>
  );

  const defaultLayoutPluginInstance = defaultLayoutPlugin({ renderToolbar, sidebarTabs: (defaultTabs) => [defaultTabs[0]] });

  useEffect(() => {
    const fetchAndSetUrl = async () => {
        setIsLoading(true); setError(null);
        try {
            let blob: Blob;
            const token = apiService.getToken();
            const urlToFetch = directUrl ? directUrl : `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/preview`;
            const headers: Record<string, string> = {};
            if (isAuth && token) headers['Authorization'] = `Bearer ${token}`;
            const response = await fetch(urlToFetch, { headers });
            if (!response.ok) {
                if (!directUrl && caseId) {
                    const originalUrl = `${API_V1_URL}/cases/${caseId}/documents/${documentData.id}/original`;
                    const originalResponse = await fetch(originalUrl, { headers });
                    if (!originalResponse.ok) throw new Error('Failed to fetch original');
                    blob = await originalResponse.blob();
                } else throw new Error('Failed to fetch');
            } else { blob = await response.blob(); }
            const blobUrl = URL.createObjectURL(blob);
            setFileUrl(blobUrl);
        } catch (err) { setError(t('pdfViewer.errorFetch', 'Gabim gjatë ngarkimit')); } finally { setIsLoading(false); }
    };
    fetchAndSetUrl();
    return () => { if (fileUrl) URL.revokeObjectURL(fileUrl); };
  }, [documentData.id, caseId, directUrl, isAuth, t]);

  const renderContent = () => {
    if (isLoading) return <div className="flex flex-col items-center justify-center h-full text-gray-400"><Loader className="animate-spin h-8 w-8 mb-2" /><span>{t('pdfViewer.loading', 'Duke hapur...')}</span></div>;
    if (error || !fileUrl) return <div className="flex flex-col items-center justify-center h-full text-center p-8"><AlertTriangle className="h-12 w-12 text-red-400 mb-4" /><p className="text-red-300 mb-6">{error}</p><button onClick={() => window.location.reload()} className="px-4 py-2 bg-white/10 rounded-lg text-white flex items-center gap-2"><RefreshCw size={16} /> {t('caseView.tryAgain')}</button></div>;
    return <Worker workerUrl={workerUrl}><div className="h-full w-full"><Viewer key={fileUrl} fileUrl={fileUrl} plugins={[defaultLayoutPluginInstance]} theme="dark" defaultScale={SpecialZoomLevel.PageFit}/></div></Worker>;
  };

  const modalContent = (
    <AnimatePresence>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] flex items-center justify-center p-0" onClick={onClose}>
        {/* PHOENIX FIX: Added the 'motion-div-container' class to target with CSS */}
        <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="motion-div-container bg-[#1a1a1a] w-full h-full sm:max-w-6xl sm:max-h-[95vh] rounded-none sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-white/10" onClick={(e) => e.stopPropagation()}>
          <style>{`
            .rpv-core__viewer { background-color: #1a1a1a !important; border: none !important; }
            .rpv-core__inner-pages { background-color: #2a2a2a !important; }
            .rpv-default-layout__sidebar { background-color: #101010 !important; border-right: 1px solid rgba(255, 255, 255, 0.1) !important; }
            .rpv-default-layout__thumbnail-item--selected { border: 2px solid #6366f1 !important; }
            .rpv-toolbar__button { color: #d1d5db !important; }
            .rpv-toolbar__button:hover { background-color: rgba(255, 255, 255, 0.1) !important; color: #fff !important; }
            .rpv-core__inner-pages::-webkit-scrollbar, .rpv-default-layout__sidebar::-webkit-scrollbar { width: 8px; height: 8px; }
            .rpv-core__inner-pages::-webkit-scrollbar-track, .rpv-default-layout__sidebar::-webkit-scrollbar-track { background: #1a1a1a; }
            .rpv-core__inner-pages::-webkit-scrollbar-thumb, .rpv-default-layout__sidebar::-webkit-scrollbar-thumb { background-color: #4b5563; border-radius: 4px; }
            .rpv-core__inner-pages::-webkit-scrollbar-thumb:hover, .rpv-default-layout__sidebar::-webkit-scrollbar-thumb:hover { background-color: #6b7280; }

            /* PHOENIX FIX: This rule breaks the stacking context "cage" ONLY when in fullscreen mode */
            .rpv-default-layout--full-screen .motion-div-container {
                transform: none !important;
            }
          `}</style>
          <div className="flex-grow relative bg-[#2a2a2a] overflow-hidden">{renderContent()}</div>
        </motion.div>
        <button onClick={onClose} className="absolute top-4 right-4 p-2 text-gray-400 hover:text-white bg-black/50 hover:bg-black/80 rounded-full transition-colors z-[10000]"><X size={24} /></button>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default PDFViewerModal;