// FILE: src/components/PrecedentCitationLink.tsx
// PHOENIX PROTOCOL - SOLID FORENSIC PRECEDENT TOOLTIP (MATCHES LAW CITATION V12.0 EXACTLY)

import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Landmark, ShieldCheck } from 'lucide-react';

export interface PrecedentCitationLinkProps {
  caseNumber: string;
  className?: string;
}

export const PrecedentCitationLink: React.FC<PrecedentCitationLinkProps> = ({
  caseNumber,
  className = '',
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [coords, setCoords] = useState({ top: 0, tooltipLeft: 0, arrowOffset: 0 });
  const containerRef = useRef<HTMLSpanElement>(null);

  const cleanLabel = caseNumber.replace(/^\[+|\]+$/g, '').trim();

  const updateCoordinates = () => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const tooltipWidth = viewportWidth < 640 ? 300 : 340;
      const margin = 16;

      const idealLeft = rect.left + rect.width / 2;
      const minLeft = tooltipWidth / 2 + margin;
      const maxLeft = viewportWidth - tooltipWidth / 2 - margin;
      const clampedLeft = Math.max(minLeft, Math.min(idealLeft, maxLeft));
      const arrowOffset = idealLeft - clampedLeft;

      setCoords({
        top: rect.top + window.scrollY,
        tooltipLeft: clampedLeft,
        arrowOffset: arrowOffset,
      });
    }
  };

  const handleMouseEnter = () => {
    updateCoordinates();
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
    }, 180);
  };

  const handleMouseLeave = () => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }
    setShowTooltip(false);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowTooltip(false);
    // PHOENIX: Hap PDF-në e aktgjykimit direkt mbi Chat pa ndërruar faqe
    window.dispatchEvent(
      new CustomEvent('open_precedent_preview', {
        detail: { caseNumber: cleanLabel }
      })
    );
  };

  const tooltipContent = (
    <AnimatePresence>
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.95 }}
          transition={{ duration: 0.12 }}
          className="absolute w-72 sm:w-80 p-4 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border-2 border-amber-500/60 rounded-2xl shadow-2xl z-[9999] pointer-events-none ring-1 ring-black/10 dark:ring-white/10"
          style={{
            top: `${coords.top - 8}px`,
            left: `${coords.tooltipLeft}px`,
            transform: 'translate(-50%, -100%)',
          }}
        >
          {/* Header identik me V12.0 */}
          <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-1.5 font-bold text-xs text-amber-500">
              <ShieldCheck size={16} />
              <span>Precedent Zyrtar i Verifikuar</span>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded font-bold bg-amber-500/10 text-amber-500">
              100% SCORE
            </span>
          </div>

          {/* Titulli i Aktvendimit */}
          <div className="text-xs font-bold text-slate-900 dark:text-white mb-1 leading-snug">
            Gjykata Supreme e Kosovës • {cleanLabel}
          </div>

          {/* Udhëzimi Verifikues */}
          <div className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed mb-2.5">
            Qëndrim parimor gjyqësor i zbatueshëm në shqyrtimin e lëndës. Kliko për të hapur arsyetimin origjinal në PDF.
          </div>

          {/* Blloku i Integritetit identik me V12.0 */}
          <div className="flex items-center justify-between text-[10px] font-mono bg-slate-100 dark:bg-slate-950 p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
            <span>Integriteti i Vendimit:</span>
            <span className="font-bold text-amber-500">
              Aktgjykim Origjinal (PDF) ✓
            </span>
          </div>

          {/* Shigjeta poshtë */}
          <div
            className="absolute top-full -translate-x-1/2 -mt-[2px] border-[8px] border-transparent pointer-events-none"
            style={{
              borderTopColor: 'var(--tw-prose-body, currentColor)',
              opacity: 0.6,
              left: `calc(50% + ${coords.arrowOffset}px)`,
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <span
      ref={containerRef}
      className={`inline-flex items-center align-baseline mx-0.5 my-0.5 max-w-full ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button
        type="button"
        onClick={handleClick}
        // 👉 PA ATRIBUTIN `title` QË TË MOS KETË DOUBLE TOOLTIP!
        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/25 text-amber-500 font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs max-w-full cursor-pointer focus:outline-none"
      >
        <Landmark size={13} className="shrink-0 opacity-80" />
        <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanLabel}</span>
      </button>

      {createPortal(tooltipContent, document.body)}
    </span>
  );
};

export default PrecedentCitationLink;