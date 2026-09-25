// FILE: src/components/chat/ChatHeader.tsx
// PHOENIX PROTOCOL - CHAT HEADER V46.4 (SYNTHESIS REMOVED)
// V46.4: SYNTHESIS REMOVED — Hequr butoni "Analizo Rastin" (fallback për ADMIN
//        pa dokument të zgjedhur). Tani butoni "Analizo Dokumentin" shfaqet
//        VETËM kur ka dokument të zgjedhur. U hoq SYNTHESIS_ALLOWED_ROLES,
//        canAnalyzeSynthesis, dhe importi Sparkles. Prop `user` mbetet në
//        interface për kompatibilitet me parent, por nuk përdoret.
// V46.3: MUTUAL EXCLUSION — butoni "Verifiko Draftin" fshihet plotësisht
//        kur audit-i është duke xhiruar (isAuditGenerating=true).
//        Kjo parandalon konfuzionin e dy treguesve paralel.
// V46.2: VERIFY COLOR UNIFIED — primary-start.
// V46.1: MOBILE VERIFY FIX.
// V46.0: VERIFY DRAFT PROGRESS.

import React, { useEffect, useState, useRef } from 'react';
import {
  Download, Trash2, FileText, Maximize2, Minimize2,
  ShieldCheck, ChevronDown,
} from 'lucide-react';
import { TFunction } from 'i18next';

const VERIFY_DOC_TYPES: Array<{ value: string; label: string }> = [
  { value: 'padi_civile',         label: 'Padi Civile' },
  { value: 'pergjigje_padi',      label: 'Përgjigje në Padi' },
  { value: 'kallzim_penal',       label: 'Kallëzim Penal' },
  { value: 'kontrate',            label: 'Kontratë' },
  { value: 'kerkese_propozim',    label: 'Kërkesë / Propozim' },
  { value: 'ankese_kundershtim',  label: 'Ankesë / Kundërshtim' },
  { value: 'tjeter',              label: 'Tjetër' },
];

interface ChatUser {
  role?: string;
  id?: string;
  email?: string;
}

interface ChatHeaderProps {
  connectionStatus: string;
  activeContextId?: string;
  onClearChat: () => void;
  onExportChat?: () => void;
  t?: TFunction;
  isPro?: boolean;
  onAnalyzeDocument?: () => void;
  onVerifyDraft?: (docType: string) => void;
  selectedDocName?: string;
  documents?: any[];
  selectedDocumentIds?: string[];
  onDocumentSelectionChange?: (ids: string[]) => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  isAuditGenerating?: boolean;
  auditProgressText?: string;
  auditProgressPercent?: number;
  auditPhaseLabel?: string;
  auditStartTime?: number | null;
  isVerifyGenerating?: boolean;
  verifyProgressPercent?: number;
  verifyPhaseLabel?: string;
  verifyStartTime?: number | null;
  // V46.4: `user` mbahet për kompatibilitet me parent — nuk përdoret më.
  user?: ChatUser | null;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  connectionStatus,
  onClearChat,
  onExportChat,
  onAnalyzeDocument,
  onVerifyDraft,
  selectedDocName,
  isFullscreen = false,
  onToggleFullscreen,
  isAuditGenerating = false,
  auditProgressPercent = 0,
  auditPhaseLabel = '',
  auditStartTime = null,
  isVerifyGenerating = false,
  verifyProgressPercent = 0,
  verifyPhaseLabel = '',
  verifyStartTime = null,
  // user — V46.4: nuk përdoret më (hequr synthesis).
}) => {
  const hasSelectedDoc = !!selectedDocName && selectedDocName.trim().length > 0;
  const [elapsed, setElapsed] = useState(0);
  const [verifyElapsed, setVerifyElapsed] = useState(0);

  const [showVerifyDropdown, setShowVerifyDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement | null>(null);

  // V46.4: Butoni "Analizo Dokumentin" shfaqet VETËM me dokument të zgjedhur.
  const showAnalyzeButton = hasSelectedDoc;
  const showVerifyButton = hasSelectedDoc && !!onVerifyDraft;

  // Audit timer
  useEffect(() => {
    if (!isAuditGenerating || !auditStartTime) {
      setElapsed(0);
      return;
    }
    setElapsed(Math.floor((Date.now() - auditStartTime) / 1000));
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - auditStartTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [isAuditGenerating, auditStartTime]);

  // Verify timer
  useEffect(() => {
    if (!isVerifyGenerating || !verifyStartTime) {
      setVerifyElapsed(0);
      return;
    }
    setVerifyElapsed(Math.floor((Date.now() - verifyStartTime) / 1000));
    const interval = setInterval(() => {
      setVerifyElapsed(Math.floor((Date.now() - verifyStartTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [isVerifyGenerating, verifyStartTime]);

  // Close dropdown on click outside
  useEffect(() => {
    if (!showVerifyDropdown) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowVerifyDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showVerifyDropdown]);

  const formatElapsed = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const safePercent = Math.min(100, Math.max(0, Math.round(auditProgressPercent)));
  const safeVerifyPercent = Math.min(100, Math.max(0, Math.round(verifyProgressPercent)));

  const ringRadius = 7;
  const ringCircumference = 2 * Math.PI * ringRadius;
  const ringOffset = ringCircumference * (1 - safePercent / 100);
  const verifyRingOffset = ringCircumference * (1 - safeVerifyPercent / 100);

  const handleVerifySelect = (docType: string) => {
    setShowVerifyDropdown(false);
    if (onVerifyDraft) onVerifyDraft(docType);
  };

  return (
    <div className="flex flex-row items-center justify-between px-2 sm:px-5 py-2.5 border-b border-main bg-surface z-30 shrink-0 h-13 min-h-[52px] w-full gap-1.5 sm:gap-2 select-none shadow-xs">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${
            connectionStatus === 'CONNECTED'
              ? 'bg-success-start shadow-md shadow-success-start/50 animate-pulse'
              : 'bg-danger-start animate-pulse'
          }`}
        />

        {isAuditGenerating ? (
          <span className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-primary-start/10 border border-primary-start/30 text-[11px] font-bold text-primary-start max-w-[140px] sm:max-w-[400px] truncate">
            <span className="truncate">{auditPhaseLabel || 'Duke analizuar...'}</span>
            <span className="text-[10px] font-mono text-primary-start/70 shrink-0">{formatElapsed(elapsed)}</span>
          </span>
        ) : isVerifyGenerating ? (
          <span className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-primary-start/10 border border-primary-start/30 text-[11px] font-bold text-primary-start max-w-[140px] sm:max-w-[400px] truncate">
            <span className="truncate">{verifyPhaseLabel || 'Duke verifikuar...'}</span>
            <span className="text-[10px] font-mono text-primary-start/70 shrink-0">{formatElapsed(verifyElapsed)}</span>
          </span>
        ) : selectedDocName ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface border border-main text-[11px] font-medium text-text-secondary max-w-[130px] sm:max-w-[300px] truncate">
            <FileText size={12} className="text-primary-start shrink-0" />
            <span className="truncate">{selectedDocName}</span>
          </span>
        ) : (
          <span className="text-xs font-bold text-text-muted hidden sm:inline">Biseda e Lëndës</span>
        )}
      </div>

      <div className="flex items-center gap-1 sm:gap-1.5 shrink-0 ml-auto">
        {/* ANALIZO DOKUMENTIN — V46.4: vetëm me dokument të zgjedhur */}
        {onAnalyzeDocument && showAnalyzeButton && (
          <button
            type="button"
            onClick={onAnalyzeDocument}
            disabled={isAuditGenerating || isVerifyGenerating}
            className={`h-8 px-2 sm:px-3 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1 sm:gap-1.5 transition-all whitespace-nowrap focus:outline-none border cursor-pointer ${
              isAuditGenerating
                ? 'bg-primary-start/15 border-primary-start/30 text-primary-start cursor-wait'
                : 'bg-surface hover:bg-hover text-primary-start hover:text-primary-end border-main hover:border-primary-start/40'
            }`}
          >
            {isAuditGenerating ? (
              <>
                <svg className="w-4 h-4 shrink-0 -rotate-90" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r={ringRadius} stroke="currentColor" strokeWidth="2" className="opacity-20" />
                  <circle cx="10" cy="10" r={ringRadius} stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                    strokeDasharray={ringCircumference} strokeDashoffset={ringOffset}
                    className="transition-all duration-300 ease-out" />
                </svg>
                <span className="tabular-nums font-black text-[11px] min-w-[28px] text-right">{safePercent}%</span>
              </>
            ) : (
              <>
                <FileText size={14} className="shrink-0 text-primary-start" />
                <span className="hidden sm:inline">Analizo Dokumentin</span>
              </>
            )}
          </button>
        )}

        {/* VERIFIKO DRAFTIN — V46.3: mutual exclusion gjatë audit */}
        {showVerifyButton && !isAuditGenerating && (
          <div className="relative" ref={dropdownRef}>
            {isVerifyGenerating ? (
              <button
                type="button"
                disabled
                className="h-8 px-2 sm:px-3 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1 sm:gap-1.5 whitespace-nowrap border bg-primary-start/15 border-primary-start/30 text-primary-start cursor-wait"
                title={verifyPhaseLabel || 'Duke verifikuar...'}
              >
                <svg className="w-4 h-4 shrink-0 -rotate-90" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="10" r={ringRadius} stroke="currentColor" strokeWidth="2" className="opacity-20" />
                  <circle cx="10" cy="10" r={ringRadius} stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                    strokeDasharray={ringCircumference} strokeDashoffset={verifyRingOffset}
                    className="transition-all duration-300 ease-out" />
                </svg>
                <span className="tabular-nums font-black text-[11px] min-w-[28px] text-right">{safeVerifyPercent}%</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setShowVerifyDropdown((v) => !v)}
                className={`h-8 px-2 sm:px-3 rounded-xl font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center justify-center gap-1 sm:gap-1.5 transition-all whitespace-nowrap focus:outline-none border cursor-pointer ${
                  showVerifyDropdown
                    ? 'bg-primary-start/15 border-primary-start/50 text-primary-start'
                    : 'bg-surface hover:bg-primary-start/10 text-primary-start border-main hover:border-primary-start/40'
                }`}
                title={`Verifiko draftin: ${selectedDocName}`}
              >
                <ShieldCheck size={14} className="shrink-0" />
                <span className="hidden sm:inline">Verifiko Draftin</span>
                <ChevronDown size={10} className={`hidden sm:inline shrink-0 transition-transform ${showVerifyDropdown ? 'rotate-180' : ''}`} />
              </button>
            )}

            {showVerifyDropdown && !isVerifyGenerating && (
              <div className="absolute right-0 top-full mt-1 w-56 bg-surface border border-main rounded-xl shadow-lg z-50 py-1 overflow-hidden">
                <div className="px-3 py-2 border-b border-main">
                  <p className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Zgjidh llojin e draftit</p>
                </div>
                {VERIFY_DOC_TYPES.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleVerifySelect(opt.value)}
                    className="w-full text-left px-3 py-2 text-xs text-text-primary hover:bg-primary-start/10 hover:text-primary-start transition-colors flex items-center gap-2 cursor-pointer"
                  >
                    <ShieldCheck size={11} className="shrink-0 text-primary-start/70" />
                    <span>{opt.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Fullscreen */}
        {onToggleFullscreen && (
          <button
            type="button"
            onClick={onToggleFullscreen}
            className={`flex items-center justify-center w-8 h-8 shrink-0 rounded-lg transition-all focus:outline-none cursor-pointer ${
              isFullscreen
                ? 'bg-primary-start text-white hover:bg-primary-start/90 shadow-xs'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
            title={isFullscreen ? "Zvogëlo dritaren (ESC)" : "Zgjero dritaren"}
          >
            {isFullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
        )}

        {/* Export */}
        {onExportChat && (
          <button
            type="button"
            onClick={onExportChat}
            className="hidden sm:flex items-center justify-center w-8 h-8 shrink-0 text-text-muted hover:text-primary-start hover:bg-hover rounded-lg transition-all focus:outline-none cursor-pointer"
            title="Shkarko Bisedën"
          >
            <Download size={15} />
          </button>
        )}

        {/* Clear */}
        <button
          type="button"
          onClick={onClearChat}
          className="flex items-center justify-center w-8 h-8 shrink-0 text-text-muted hover:text-danger-start hover:bg-danger-start/10 rounded-lg transition-all focus:outline-none cursor-pointer"
          title="Pastro Bisedën"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
};

export default ChatHeader;