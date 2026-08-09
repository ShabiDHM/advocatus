// FILE: frontend/src/components/FinancialAnalystModal.tsx
// PHOENIX PROTOCOL - FINANCIAL ANALYST MODAL V11.0 (OPAQUE TASKBAR MINIMIZATION DOCK)

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, X, Maximize2, Minimize2, Minus, Save, CheckCircle2, RefreshCw } from 'lucide-react';
import SpreadsheetAnalyst from './SpreadsheetAnalyst';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';
import { apiService } from '../services/api';

interface FinancialAnalystModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  caseTitle?: string;
}

const getCache = () => { 
  try { 
    const raw = localStorage.getItem('juristi_analyst_cache'); 
    return raw ? JSON.parse(raw) : {}; 
  } catch { 
    return {}; 
  } 
};

export const FinancialAnalystModal: React.FC<FinancialAnalystModalProps> = ({
  isOpen,
  onClose,
  caseId,
  caseTitle,
}) => {
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [archiveSuccess, setArchiveSuccess] = useState(false);
  const [reportSummary, setReportSummary] = useState<string>('');
  const [reportFileName, setReportFileName] = useState<string>('');

  useLockBodyScroll(isOpen && !isMinimized);

  const handleReportLoaded = (summaryText: string, fileNameText: string) => {
    if (summaryText) setReportSummary(summaryText);
    if (fileNameText) setReportFileName(fileNameText);
  };

  const handleArchiveReport = async () => {
    if (isArchiving) return;
    setIsArchiving(true);

    const cache = getCache();
    const caseCache = cache[caseId] || cache[String(caseId)];
    
    const activeSummary = 
      (window as any).__LATEST_FORENSIC_SUMMARY__ || 
      reportSummary || 
      caseCache?.report?.executive_summary || 
      '';

    const activeFileName = 
      (window as any).__LATEST_FORENSIC_FILENAME__ || 
      reportFileName || 
      caseCache?.fileName || 
      'Pasqyra_Financiare';

    if (!activeSummary) {
      alert('Nuk ka të dhëna financiare të analizuara për të arkivuar. Ju lutem ngarkoni së pari një skedar Excel/CSV.');
      setIsArchiving(false);
      return;
    }

    const fullContent = `## MEMORANDUMI I GJETJEVE FINANCIARE\n\n**LËNDA:** ${caseTitle || 'Rast'}\n**SKEDARI I HULUMTUAR:** ${activeFileName}\n\n---\n\n${activeSummary}`;

    try {
      await apiService.archiveForensicReport(
        caseId,
        `RAPORTI I ANALIZËS FINANCIARE — ${caseTitle || 'Rast'}`,
        fullContent
      );
      setArchiveSuccess(true);
      setTimeout(() => setArchiveSuccess(false), 3000);
      alert('Raporti Financiar u ruajt me sukses në Arkivin e Lëndës!');
    } catch {
      alert('Dështoi ruajtja e raportit në arkiv.');
    } finally {
      setIsArchiving(false);
    }
  };

  const handleResetAnalysis = () => {
    delete (window as any).__LATEST_FORENSIC_SUMMARY__;
    delete (window as any).__LATEST_FORENSIC_FILENAME__;
    const c = getCache();
    delete c[caseId];
    localStorage.setItem('juristi_analyst_cache', JSON.stringify(c));
    setReportSummary('');
    setReportFileName('');
    window.location.reload();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      {/* SOLID OPAQUE HIGH-CONTRAST FLOATING TASKBAR DOCKED BAR (BOTTOM RIGHT) */}
      {isMinimized ? (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.9 }}
          className="fixed bottom-4 right-4 z-[300] flex items-center gap-3 bg-surface border-2 border-primary-start px-4 py-2.5 rounded-2xl shadow-2xl text-text-primary cursor-pointer hover:border-primary-start opacity-100 backdrop-blur-xl"
          onClick={() => setIsMinimized(false)}
        >
          <div className="w-8 h-8 rounded-xl bg-primary-start/15 text-primary-start flex items-center justify-center border border-primary-start/30 shrink-0">
            <Activity size={16} />
          </div>
          <div className="flex flex-col text-left min-w-0 pr-2">
            <span className="text-xs font-black uppercase text-text-primary truncate">
              Analisti Financiar Forenzik
            </span>
            <span className="text-[10px] text-text-muted font-medium truncate">
              {caseTitle || 'Lënda e minimizuar'}
            </span>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setIsMinimized(false);
            }}
            className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-colors"
            title="Zmadho përsëri"
          >
            <Maximize2 size={15} />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
              setIsMinimized(false);
            }}
            className="p-1.5 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors"
            title="Mbyll"
          >
            <X size={15} />
          </button>
        </motion.div>
      ) : (
        /* FULL MAIN MODAL OVERLAY */
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[200] p-2 sm:p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2 }}
            className={`glass-panel w-[95vw] rounded-3xl shadow-2xl border border-main bg-canvas flex flex-col overflow-hidden transition-all duration-300 ${
              isFullScreen ? 'w-full h-full max-w-none rounded-none' : 'max-w-7xl h-[92vh]'
            }`}
          >
            {/* MODAL HEADER */}
            <div className="p-4 sm:p-5 border-b border-main bg-surface flex flex-wrap items-center justify-between gap-3 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20 shrink-0">
                  <Activity size={20} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight truncate">
                    Analisti Financiar Forenzik
                  </h3>
                  {caseTitle && (
                    <p className="text-xs text-text-muted font-medium truncate mt-0.5">
                      Lënda: {caseTitle}
                    </p>
                  )}
                </div>
              </div>

              {/* Header Controls */}
              <div className="flex items-center gap-1 sm:gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsFullScreen(!isFullScreen)}
                  className="p-1.5 sm:p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-all focus:outline-none"
                  title={isFullScreen ? 'Zvogëlo ekranin' : 'Zmadho në ekran të plotë'}
                >
                  {isFullScreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
                </button>

                <button
                  type="button"
                  onClick={() => setIsMinimized(true)}
                  className="p-1.5 sm:p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 focus:outline-none"
                  title="Minimizo në taskbar"
                >
                  <Minus size={18} />
                </button>

                <button
                  type="button"
                  onClick={onClose}
                  className="p-1.5 sm:p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 focus:outline-none"
                  aria-label="Mbyll"
                  title="Mbyll"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            {/* MODAL BODY (SPREADSHEET ANALYST) */}
            <div className="flex-1 overflow-y-auto p-2 sm:p-4 bg-canvas">
              <SpreadsheetAnalyst caseId={caseId} onReportAvailable={handleReportLoaded} />
            </div>

            {/* MODAL FOOTER */}
            <div className="p-3.5 sm:p-4 border-t border-main bg-surface flex flex-col sm:flex-row items-center justify-between gap-3 shrink-0">
              <button
                type="button"
                onClick={handleArchiveReport}
                disabled={isArchiving || archiveSuccess}
                className={`w-full sm:w-auto h-10 px-5 rounded-xl text-xs uppercase tracking-wider font-bold transition-all flex items-center justify-center gap-2 border focus:outline-none ${
                  archiveSuccess
                    ? 'bg-status-success text-white border-status-success'
                    : 'bg-status-success/15 text-status-success border-status-success/20 hover:bg-status-success/20 active:scale-95'
                }`}
              >
                {isArchiving ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : archiveSuccess ? (
                  <CheckCircle2 size={15} />
                ) : (
                  <Save size={15} />
                )}
                {archiveSuccess ? 'Arkivuar me Sukses!' : 'Ruaj Raportin në Arkiv'}
              </button>

              <button
                type="button"
                onClick={handleResetAnalysis}
                className="w-full sm:w-auto h-10 px-5 rounded-xl text-xs uppercase tracking-wider font-bold transition-all flex items-center justify-center gap-2 border border-main bg-canvas hover:bg-hover text-text-secondary hover:text-text-primary focus:outline-none"
              >
                <RefreshCw size={14} />
                Rianalizo / Skedar i Ri
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default FinancialAnalystModal;