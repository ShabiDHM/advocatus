// FILE: src/components/law/RepealedWarning.tsx
// PHOENIX PROTOCOL - REPEALED WARNING COMPONENT V1.0
//
// Komponent i ripërdorshëm për shfaqjen e warning-ut të ligjeve të shfuqizuara.
// Përdoret në: LawArticlePage, LawOverviewPage, LawLibraryResultCard, etj.
//
// Dy mode:
//   - Normal (default): banner i plotë me detaje
//   - Compact: badge i vogël (për headers/list)

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import type { RepealedInfo } from './lawArticleTypes';

interface RepealedWarningProps {
  info?: RepealedInfo | null;
  warning?: string;
  compact?: boolean;
}

export const RepealedWarning: React.FC<RepealedWarningProps> = ({
  info,
  warning,
  compact = false,
}) => {
  // Nuk shfaqem asgjë nëse nuk ka info shfuqizimi
  if (!info?.is_repealed && !warning) return null;

  const message =
    warning ||
    info?.warning_message ||
    '⚠️ Ky ligj është shfuqizuar.';

  const successor = info?.repealed_by || '';
  const date = info?.repealed_date || '';
  const source = info?.source || '';
  const reason = info?.reason || '';

  // Compact mode — badge i vogël
  if (compact) {
    return (
      <div
        role="status"
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-warning-start/15 border border-warning-start/30 text-warning-start text-[11px] font-bold uppercase tracking-wider"
        title={message}
      >
        <AlertTriangle size={12} />
        <span>Shfuqizuar</span>
      </div>
    );
  }

  // Normal mode — banner i plotë
  return (
    <div
      role="alert"
      aria-label="Paralajmërim ligj i shfuqizuar"
      className="bg-warning-start/10 border-l-4 border-warning-start rounded-xl p-4 sm:p-5 flex flex-col gap-3 shadow-sm"
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-xl bg-warning-start/20 text-warning-start shrink-0">
          <AlertTriangle size={20} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-black text-warning-start text-sm uppercase tracking-wider mb-1">
            Ky ligj është shfuqizuar
          </h4>
          <p className="text-text-primary text-xs sm:text-sm leading-relaxed">
            {message}
          </p>
        </div>
      </div>

      {(successor || date || source) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs bg-surface/60 border border-main rounded-xl p-3">
          {successor && (
            <div className="sm:col-span-2">
              <span className="text-text-muted block mb-0.5">Zëvendësuar me:</span>
              <strong className="text-text-primary">{successor}</strong>
            </div>
          )}
          {date && (
            <div>
              <span className="text-text-muted block mb-0.5">Data:</span>
              <strong className="text-text-primary">{date}</strong>
            </div>
          )}
          {source && (
            <div>
              <span className="text-text-muted block mb-0.5">Burimi:</span>
              <strong className="text-text-primary font-mono text-[11px]">{source}</strong>
            </div>
          )}
        </div>
      )}

      {reason && (
        <p className="text-[11px] text-text-muted italic leading-relaxed">
          {reason}
        </p>
      )}
    </div>
  );
};

export default RepealedWarning;