// FILE: frontend/src/components/case/AuditProgressToast.tsx
// PHOENIX PROTOCOL - AUDIT PROGRESS TOAST V2.0 (MINIMAL)
// Version kompakt — vetëm një pill i vogël me spinner + përqindje.
// Zë shumë pak hapësirë, jo-intrusive.

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface AuditProgressToastProps {
  isVisible: boolean;
  phaseLabel: string;
  subLabel: string;
  progressPercent: number;
  isDocumentMode: boolean;
  startTime: number | null;
}

export const AuditProgressToast: React.FC<AuditProgressToastProps> = ({
  isVisible,
  phaseLabel,
  progressPercent,
  startTime,
}) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isVisible || !startTime) {
      setElapsed(0);
      return;
    }
    setElapsed(Math.floor((Date.now() - startTime) / 1000));
    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, [isVisible, startTime]);

  const formatElapsed = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    if (m > 0) return `${m}:${s.toString().padStart(2, '0')}`;
    return `0:${s.toString().padStart(2, '0')}`;
  };

  const safePercent = Math.min(100, Math.max(0, Math.round(progressPercent)));

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.95 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          className="fixed bottom-4 right-3 sm:bottom-6 sm:right-6 z-[300] pointer-events-none"
        >
          <div className="glass-panel bg-card border border-primary-start/40 rounded-full shadow-2xl overflow-hidden backdrop-blur-md pointer-events-auto">
            <div className="flex items-center gap-2.5 pl-3 pr-3 py-2">
              {/* Spinner */}
              <Loader2 size={14} className="animate-spin text-primary-start shrink-0" />

              {/* Përqindja */}
              <span className="text-xs font-bold text-primary-start tabular-nums min-w-[34px]">
                {safePercent}%
              </span>

              {/* Faza — e shkurtër */}
              <span
                className="text-[11px] text-text-secondary truncate max-w-[140px] font-medium"
                title={phaseLabel}
              >
                {phaseLabel || 'Duke analizuar...'}
              </span>

              {/* Koha */}
              <span className="text-[10px] text-text-muted font-mono tabular-nums shrink-0">
                {formatElapsed(elapsed)}
              </span>
            </div>

            {/* Thin progress bar në fund */}
            <div className="h-[2px] bg-surface/50 relative overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-primary-start to-primary-end"
                initial={{ width: 0 }}
                animate={{ width: `${safePercent}%` }}
                transition={{ duration: 0.4, ease: 'easeOut' }}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AuditProgressToast;