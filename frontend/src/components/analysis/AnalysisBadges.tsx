// FILE: src/components/analysis/AnalysisBadges.tsx
import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ShieldAlert, ShieldCheck, Percent } from 'lucide-react';
import { TFunction } from 'i18next';

export const SpinnerStyles: React.FC = () => (
  <style>{`
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    .spinner-robust {
      animation: spin 1s linear infinite !important;
    }
  `}</style>
);

export const Spinner: React.FC<{ size?: string }> = ({ size = 'w-20 h-20' }) => (
  <div className={`${size} border-4 border-primary-start border-t-transparent rounded-full spinner-robust`} />
);

export const SuccessTooltip: React.FC<{ children: React.ReactNode; t: TFunction }> = ({ children, t }) => {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => setShow(true), 400);
  };
  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setShow(false);
  };

  return (
    <div className="relative inline-block" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      {children}
      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-1/2 transform -translate-x-1/2 mt-3 w-56 p-4 bg-surface text-[12px] font-medium text-text-secondary rounded-xl border border-main shadow-2xl z-[100] text-center leading-relaxed"
          >
            {t('analysis.success_tooltip', 'Probabiliteti i suksesit i vlerësuar nga AI bazuar në faktet dhe ligjin.')}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const RenderRiskBadge: React.FC<{ level: string; t: TFunction }> = ({ level, t }) => {
  const l = level?.toUpperCase() || 'MEDIUM';
  let styles = 'bg-warning-start/10 text-warning-start border-warning-start/20';
  let icon = <Shield size={14} />;
  let label = t('analysis.risk_medium', 'I MESËM');

  if (l.includes('HIGH')) {
    styles = 'bg-danger-start/10 text-danger-start border-danger-start/20';
    icon = <ShieldAlert size={14} />;
    label = t('analysis.risk_high', 'I LARTË');
  } else if (l.includes('LOW')) {
    styles = 'bg-success-start/10 text-success-start border-success-start/20';
    icon = <ShieldCheck size={14} />;
    label = t('analysis.risk_low', 'I ULËT');
  }

  return (
    <div className={`flex items-center justify-center gap-2 px-3 py-1.5 rounded-full border ${styles} shadow-sm w-full sm:w-auto`}>
      {icon}
      <div className="flex items-center gap-1.5 text-[11px] font-black tracking-widest uppercase">
        <span className="opacity-70">{t('analysis.risk_label', 'RREZIKU')}</span>
        <span className="w-1 h-1 rounded-full bg-current opacity-50" />
        <span>{label}</span>
      </div>
    </div>
  );
};

export const RenderSuccessBadge: React.FC<{ prob: string | null; t: TFunction }> = ({ prob, t }) => {
  if (!prob) return null;
  return (
    <SuccessTooltip t={t}>
      <div className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-full border bg-primary-start/10 text-primary-start border-primary-start/20 shadow-sm w-full sm:w-auto cursor-help">
        <Percent size={14} />
        <div className="flex items-center gap-1.5 text-[11px] font-black tracking-widest uppercase">
          <span className="opacity-70">SUKSESI</span>
          <span className="w-1 h-1 rounded-full bg-current opacity-50" />
          <span>{prob}</span>
        </div>
      </div>
    </SuccessTooltip>
  );
};