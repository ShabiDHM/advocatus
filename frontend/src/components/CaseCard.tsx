// FILE: src/components/CaseCard.tsx
// PHOENIX PROTOCOL – COMPACT CARD REFIT V10.0 (CLEAN LOWERCASE EMAIL & METADATA GUARD)

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Case } from '../data/types';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Trash2, FileText, AlertTriangle, CalendarDays, User, Mail, Phone, ChevronRight } from 'lucide-react';

interface CaseCardProps {
  caseData: Case;
  onDelete: (caseId: string) => void;
}

const safeDate = (dateVal: any): string => {
  if (!dateVal) return 'N/A';
  try {
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) return 'N/A';
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    }).replace(/\//g, '.');
  } catch {
    return 'N/A';
  }
};

const safeString = (val: any): string => {
  if (!val) return '';
  if (typeof val === 'string') return val.trim();
  try {
    return JSON.stringify(val).trim();
  } catch {
    return String(val).trim();
  }
};

const CaseCard: React.FC<CaseCardProps> = ({ caseData, onDelete }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleCardClick = () => {
    if (caseData?.id) {
      navigate(`/cases/${caseData.id}`);
    }
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (caseData?.id) {
      onDelete(caseData.id);
    }
  };

  const handleCalendarNav = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate('/calendar');
  };

  const formattedDate = safeDate(caseData?.created_at);

  const rawTitle = safeString(caseData?.title);
  const hasTitle = rawTitle !== '';
  const displayTitle = hasTitle ? rawTitle : (t('caseView.unnamedCase') || 'Rast pa Emër');

  // Intelligent Name & Email Normalization
  let rawClientName = safeString(caseData?.client?.name || (caseData as any)?.client_name);
  let rawClientEmail = safeString(caseData?.client?.email || (caseData as any)?.client_email);
  const clientPhone = safeString(caseData?.client?.phone || (caseData as any)?.client_phone);

  // If the name field contains an email address and email field is a name, swap them
  if (rawClientName.includes('@') && !rawClientEmail.includes('@') && rawClientEmail.length > 0) {
    const temp = rawClientName;
    rawClientName = rawClientEmail;
    rawClientEmail = temp;
  }

  // Force email to be lowercase
  const cleanEmail = rawClientEmail ? rawClientEmail.toLowerCase() : '';
  const cleanName = rawClientName ? rawClientName : (cleanEmail ? cleanEmail : t('general.notAvailable', 'N/A'));

  return (
    <motion.div 
      onClick={handleCardClick}
      className="glass-panel group relative flex flex-col justify-between h-full p-5 rounded-2xl hover-lift cursor-pointer border border-main bg-card shadow-sm"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      whileTap={{ scale: 0.985 }}
    >
      {/* Background dynamic hover glow */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary-start/5 to-secondary-end/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

      <div className="relative z-10 flex-grow flex flex-col justify-between">
        {/* Title and Date */}
        <div className="flex flex-col mb-4">
          <h2 className={`text-xl font-bold line-clamp-2 leading-tight tracking-tight mb-1 transition-colors duration-200 ${
            !hasTitle ? 'text-text-secondary italic' : 'text-text-primary group-hover:text-primary-start'
          }`}>
            {displayTitle}
          </h2>
          <div className="text-xs font-mono text-text-muted">
            {formattedDate}
          </div>
        </div>
        
        {/* Client Details Section */}
        <div className="flex flex-col mb-5 bg-surface/50 border border-main p-3.5 rounded-xl transition-colors duration-200 group-hover:bg-surface/80">
          <div className="flex items-center gap-2 mb-2.5 pb-2 border-b border-main">
            <User className="w-3.5 h-3.5 text-primary-start" />
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">
              {t('caseCard.clientLabel', 'Klienti')}
            </span>
          </div>
          
          <div className="space-y-1.5 pl-0.5">
            <p className="text-sm sm:text-base font-bold text-text-primary truncate">
              {cleanName}
            </p>
            
            {cleanEmail && (
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <Mail className="w-3.5 h-3.5 text-text-muted shrink-0" />
                <span className="truncate font-mono lowercase text-xs">{cleanEmail}</span>
              </div>
            )}
            {clientPhone && (
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <Phone className="w-3.5 h-3.5 text-text-muted shrink-0" />
                <span className="truncate font-mono text-xs">{clientPhone}</span>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Controls & Metadata statistics */}
      <div className="relative z-10 shrink-0">
        <div className="pt-4 border-t border-main flex flex-wrap items-center gap-2">
          {/* Chip: Document Counter */}
          <div 
            className="flex items-center gap-1.5 bg-surface border border-main px-2.5 py-1 rounded-xl shadow-xs" 
            title={`${caseData?.document_count || 0} Dokumente`}
          >
            <FileText className="h-3.5 w-3.5 text-primary-start" />
            <span className="text-xs font-semibold text-text-secondary font-mono">{caseData?.document_count || 0}</span>
          </div>

          {/* Chip: Alert Counter */}
          <button 
            type="button"
            onClick={handleCalendarNav}
            className="flex items-center gap-1.5 bg-surface hover:bg-hover border border-main px-2.5 py-1 rounded-xl transition-all focus:outline-none shadow-xs" 
            title={`${caseData?.alert_count || 0} Afate`}
          >
            <AlertTriangle className="h-3.5 w-3.5 text-status-warning" />
            <span className="text-xs font-semibold text-text-secondary font-mono">{caseData?.alert_count || 0}</span>
          </button>

          {/* Chip: Event Counter */}
          <button 
            type="button"
            onClick={handleCalendarNav}
            className="flex items-center gap-1.5 bg-surface hover:bg-hover border border-main px-2.5 py-1 rounded-xl transition-all focus:outline-none shadow-xs" 
            title={`${caseData?.event_count || 0} Ngjarje`}
          >
            <CalendarDays className="h-3.5 w-3.5 text-secondary-start" />
            <span className="text-xs font-semibold text-text-secondary font-mono">{caseData?.event_count || 0}</span>
          </button>
        </div>

        {/* Footer Actions */}
        <div className="mt-4 pt-4 border-t border-main flex items-center justify-between">
          <span className="text-xs font-bold text-primary-start group-hover:text-primary-end transition-colors flex items-center gap-0.5 select-none">
            {t('general.view', 'Shiko')} {t('archive.details', 'Detajet')}
            <ChevronRight className="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform" />
          </span>
          
          <motion.button
            type="button"
            onClick={handleDeleteClick}
            className="flex items-center justify-center w-9 h-9 rounded-xl text-text-muted hover:text-rose-600 hover:bg-rose-500/10 transition-colors z-20 relative focus:outline-none"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title={t('general.delete', 'Fshij')}
            aria-label="Delete case"
          >
            <Trash2 className="h-4 w-4" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};

export default CaseCard;