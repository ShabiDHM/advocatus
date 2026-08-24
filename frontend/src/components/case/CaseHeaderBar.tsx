// FILE: src/components/case/CaseHeaderBar.tsx
// PHOENIX PROTOCOL - CASE HEADER BAR V17.0 (PURE MINIMALIST IDENTITY & RIGHT-ALIGNED ROLE PILL)

import React from 'react';
import { motion } from 'framer-motion';
import { Case, Document } from '../../data/types';
import {
  Briefcase,
  Calendar,
  Shield,
  Swords,
  Scale
} from 'lucide-react';

interface CaseHeaderBarProps {
  caseDetails: Case;
  documents: Document[];
  onOpenRoleModal: () => void;
}

export const CaseHeaderBar: React.FC<CaseHeaderBarProps> = ({
  caseDetails,
  documents,
  onOpenRoleModal,
}) => {
  const clientPosition = (caseDetails as any).client_position || 'DEFENDANT';
  const rawTitle = caseDetails.title || (caseDetails as any).name || 'Rast pa Titull';

  const roleLabel =
    clientPosition === 'DEFENDANT'
      ? 'ROLI: I PADITUR'
      : clientPosition === 'PLAINTIFF'
      ? 'ROLI: PADITËS'
      : 'ROLI: NEUTRAL';

  return (
    <motion.div
      className="relative mb-4 sm:mb-5 z-[30]"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      {/* SHIRITI I VETËM DHE I PASTAR I IDENTITETIT TË LËNDËS */}
      <div className="bg-surface border border-main rounded-2xl p-3.5 sm:p-4 shadow-sm flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4">
        
        {/* MAJTAS: Identiteti i Lëndës dhe Statistikat */}
        <div className="flex items-center gap-3.5 min-w-0 flex-1">
          <div className="p-2.5 sm:p-3 bg-primary-start/10 text-primary-start border border-primary-start/20 rounded-2xl shrink-0">
            <Briefcase size={20} className="sm:w-5 sm:h-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-base sm:text-lg md:text-xl font-bold text-text-primary tracking-tight truncate leading-tight">
              {rawTitle}
            </h1>

            <div className="flex items-center gap-2 sm:gap-3 text-[11px] sm:text-xs text-text-muted mt-1 font-medium">
              <span className="flex items-center gap-1">
                <Calendar size={12} className="text-primary-start/70" />
                {new Date(caseDetails.created_at).toLocaleDateString()}
              </span>
              <span>•</span>
              <span className="font-mono text-text-secondary">{documents.length} Dok</span>
            </div>
          </div>
        </div>

        {/* DJATHAS: Zgjedhësi i Rolit Procedural */}
        <div className="flex items-center justify-end shrink-0">
          <button
            type="button"
            onClick={onOpenRoleModal}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-[10px] sm:text-[11px] font-bold uppercase tracking-wider border transition-all shadow-xs cursor-pointer ${
              clientPosition === 'DEFENDANT'
                ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30 hover:bg-blue-500/20'
                : clientPosition === 'PLAINTIFF'
                ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30 hover:bg-purple-500/20'
                : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
            }`}
            title="Kliko për të ndryshuar rolin procedural të klientit"
          >
            {clientPosition === 'DEFENDANT' ? (
              <Shield size={12} className="shrink-0" />
            ) : clientPosition === 'PLAINTIFF' ? (
              <Swords size={12} className="shrink-0" />
            ) : (
              <Scale size={12} className="shrink-0" />
            )}
            <span>{roleLabel}</span>
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default CaseHeaderBar;