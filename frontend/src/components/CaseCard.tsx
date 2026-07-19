// FILE: src/components/CaseCard.tsx
// PHOENIX PROTOCOL – COMPACT CARD REFIT (Polished layout, standardized tokens, custom chips)

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

const CaseCard: React.FC<CaseCardProps> = ({ caseData, onDelete }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleCardClick = () => {
    navigate(`/cases/${caseData.id}`);
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(caseData.id);
  };

  const handleCalendarNav = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigate('/calendar');
  };

  const formattedDate = new Date(caseData.created_at).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).replace(/\//g, '.');

  const hasTitle = caseData.title && caseData.title.trim() !== '';
  const displayTitle = hasTitle ? caseData.title : (t('caseView.unnamedCase') || 'Rast pa Emër');

  return (
    <motion.div 
      onClick={handleCardClick}
      className="glass-panel group relative flex flex-col justify-between h-full p-5 rounded-2xl hover-lift cursor-pointer border border-main bg-canvas"
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      whileTap={{ scale: 0.985 }}
    >
      {/* Subtle background dynamic glow hover effect */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary-start/5 to-secondary-end/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

      <div className="relative z-10 flex-grow flex flex-col justify-between">
        {/* Title and Date */}
        <div className="flex flex-col mb-4">
          <h2 className={`text-xl font-bold line-clamp-2 leading-tight tracking-tight mb-1 transition-colors duration-250 ${
            !hasTitle ? 'text-text-secondary italic' : 'text-text-primary group-hover:text-primary-start'
          }`}>
            {displayTitle}
          </h2>
          <div className="text-xs font-mono text-text-muted">
            {formattedDate}
          </div>
        </div>
        
        {/* Client Details Section - Nested inside a beautiful inset container */}
        <div className="flex flex-col mb-5 bg-surface/40 border border-main/60 p-3.5 rounded-xl transition-colors duration-200 group-hover:bg-surface/60">
          <div className="flex items-center gap-2 mb-2.5 pb-2 border-b border-main">
            <User className="w-3.5 h-3.5 text-primary-start" />
            <span className="text-[10px] font-bold text-text-secondary uppercase tracking-widest">
              {t('caseCard.clientLabel', 'Klienti')}
            </span>
          </div>
          
          <div className="space-y-1.5 pl-0.5">
            <p className="text-base font-semibold text-text-primary truncate">
              {caseData.client?.name || t('general.notAvailable', 'N/A')}
            </p>
            
            {caseData.client?.email && (
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <Mail className="w-3.5 h-3.5 text-text-muted" />
                <span className="truncate">{caseData.client.email}</span>
              </div>
            )}
            {caseData.client?.phone && (
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <Phone className="w-3.5 h-3.5 text-text-muted" />
                <span className="truncate">{caseData.client.phone}</span>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Interactive Controls & Metadata statistics */}
      <div className="relative z-10 shrink-0">
        {/* Statistics Section - Standardized on semantic chips */}
        <div className="pt-4 border-t border-main flex flex-wrap items-center gap-2">
          {/* Chip: Document Counter */}
          <div 
            className="flex items-center gap-1.5 bg-surface/60 border border-main px-2.5 py-1 rounded-xl" 
            title={`${caseData.document_count || 0} Dokumente`}
          >
            <FileText className="h-3.5 w-3.5 text-primary-start" />
            <span className="text-xs font-semibold text-text-secondary font-mono">{caseData.document_count || 0}</span>
          </div>

          {/* Chip: Alert / Deadline Counter */}
          <button 
            type="button"
            onClick={handleCalendarNav}
            className="flex items-center gap-1.5 bg-surface/60 hover:bg-hover border border-main px-2.5 py-1 rounded-xl transition-all focus:outline-none" 
            title={`${caseData.alert_count || 0} Afate`}
          >
            <AlertTriangle className="h-3.5 w-3.5 text-status-warning" />
            <span className="text-xs font-semibold text-text-secondary font-mono">{caseData.alert_count || 0}</span>
          </button>

          {/* Chip: Event Counter */}
          <button 
            type="button"
            onClick={handleCalendarNav}
            className="flex items-center gap-1.5 bg-surface/60 hover:bg-hover border border-main px-2.5 py-1 rounded-xl transition-all focus:outline-none" 
            title={`${caseData.event_count || 0} Ngjarje`}
          >
            <CalendarDays className="h-3.5 w-3.5 text-secondary-start" />
            <span className="text-xs font-semibold text-text-secondary font-mono">{caseData.event_count || 0}</span>
          </button>
        </div>

        {/* Footer actions with optimized tap zones */}
        <div className="mt-4 pt-4 border-t border-main flex items-center justify-between">
          <span className="text-xs font-bold text-primary-start group-hover:text-primary-end transition-colors flex items-center gap-0.5 select-none">
            {t('general.view', 'Shiko')} {t('archive.details', 'Detajet')}
            <ChevronRight className="w-3.5 h-3.5 transform group-hover:translate-x-0.5 transition-transform" />
          </span>
          
          <motion.button
            type="button"
            onClick={handleDeleteClick}
            className="flex items-center justify-center w-11 h-11 -mr-3 rounded-xl text-text-muted hover:text-danger-start hover:bg-danger-start/10 transition-colors z-20 relative focus:outline-none"
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