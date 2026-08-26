// FILE: src/components/case/CaseHeaderBar.tsx
// PHOENIX PROTOCOL - CASE HEADER BAR V19.0 (DOCUMENT & TOTAL PAGE COUNT METRICS)

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Case, Document } from '../../data/types';
import {
  Briefcase,
  Calendar,
  Shield,
  Swords,
  Scale,
  FileText
} from 'lucide-react';

interface CaseHeaderBarProps {
  caseDetails: Case;
  documents: Document[];
  onOpenRoleModal?: () => void;
}

export const CaseHeaderBar: React.FC<CaseHeaderBarProps> = ({
  caseDetails,
  documents = [],
}) => {
  const clientPosition = (caseDetails as any).client_position || 'DEFENDANT';
  const rawTitle = caseDetails.title || (caseDetails as any).name || 'Rast pa Titull';

  const roleLabel =
    clientPosition === 'DEFENDANT'
      ? 'ROLI: I PADITUR / I DENONCUAR'
      : clientPosition === 'PLAINTIFF'
      ? 'ROLI: PADITËS / KALLËZUES'
      : 'ROLI: NEUTRAL';

  // Llogaritja e numrit total të faqeve nga të gjitha dokumentet e lëndës
  const totalPages = useMemo(() => {
    return documents.reduce((acc, doc) => {
      const count = 
        (doc as any).page_count || 
        (doc as any).pages || 
        (doc as any).total_pages || 
        (doc as any).num_pages || 
        0;
      return acc + (typeof count === 'number' ? count : parseInt(String(count), 10) || 0);
    }, 0);
  }, [documents]);

  return (
    <motion.div
      className="relative mb-4 sm:mb-5 z-[30]"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      {/* SHIRITI I IDENTITETIT TË LËNDËS */}
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

            <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-[11px] sm:text-xs text-text-muted mt-1 font-medium">
              <span className="flex items-center gap-1">
                <Calendar size={12} className="text-primary-start/70" />
                {new Date(caseDetails.created_at).toLocaleDateString()}
              </span>

              <span>•</span>
              <span className="font-mono text-text-secondary flex items-center gap-1">
                <FileText size={12} className="text-text-muted" />
                {documents.length} Dok
              </span>

              {totalPages > 0 && (
                <>
                  <span>•</span>
                  <span className="font-mono text-text-secondary font-semibold">
                    {totalPages} Faqe
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* DJATHAS: Badge Statik Read-Only (I Pandryshueshëm) */}
        <div className="flex items-center justify-end shrink-0 select-none">
          <div
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-[10px] sm:text-[11px] font-black uppercase tracking-wider border shadow-xs cursor-default ${
              clientPosition === 'DEFENDANT'
                ? 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30'
                : clientPosition === 'PLAINTIFF'
                ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30'
                : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
            }`}
          >
            {clientPosition === 'DEFENDANT' ? (
              <Shield size={13} className="shrink-0" />
            ) : clientPosition === 'PLAINTIFF' ? (
              <Swords size={13} className="shrink-0" />
            ) : (
              <Scale size={13} className="shrink-0" />
            )}
            <span>{roleLabel}</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default CaseHeaderBar;