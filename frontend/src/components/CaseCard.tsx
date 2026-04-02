// FILE: src/components/CaseCard.tsx
// PHOENIX PROTOCOL – COMPACT CASE CARD (smaller, cleaner)

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Case } from '../data/types';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Trash2, FileText, AlertTriangle, CalendarDays, User, Mail, Phone } from 'lucide-react';

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
      className="glass-panel group relative flex flex-col justify-between h-full p-4 rounded-xl hover-lift cursor-pointer border-border-main"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      whileTap={{ scale: 0.99 }}
    >
      <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-primary-start/5 to-secondary-end/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

      <div>
        {/* Title and Date */}
        <div className="flex flex-col mb-3 relative z-10">
          <h2 className={`text-base font-bold line-clamp-2 leading-tight tracking-tight mb-1 ${
            !hasTitle ? 'text-text-secondary italic' : 'text-text-primary group-hover:text-primary-start transition-colors'
          }`}>
            {displayTitle}
          </h2>
          <div className="text-[10px] text-text-muted">
            {formattedDate}
          </div>
        </div>
        
        {/* Client Details Section (simplified, smaller) */}
        <div className="flex flex-col mb-3 relative z-10">
          <div className="flex items-center gap-1.5 mb-2 pb-1.5 border-b border-border-main">
            <User className="w-3 h-3 text-primary-start" />
            <span className="text-[9px] font-bold text-text-secondary uppercase tracking-wider">
              {t('caseCard.clientLabel', 'Klienti')}
            </span>
          </div>
          
          <div className="space-y-1 pl-1">
            <p className="text-xs font-medium text-text-primary truncate">
              {caseData.client?.name || t('general.notAvailable', 'N/A')}
            </p>
            
            {caseData.client?.email && (
              <div className="flex items-center gap-1.5 text-[10px] text-text-secondary">
                <Mail className="w-2.5 h-2.5" />
                <span className="truncate">{caseData.client.email}</span>
              </div>
            )}
            {caseData.client?.phone && (
              <div className="flex items-center gap-1.5 text-[10px] text-text-secondary">
                <Phone className="w-2.5 h-2.5" />
                <span className="truncate">{caseData.client.phone}</span>
              </div>
            )}
          </div>
        </div>
      </div>
      
      <div className="relative z-10">
        {/* Statistics Section */}
        <div className="pt-3 border-t border-border-main flex items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            {/* Documents */}
            <div className="flex items-center gap-1" title={`${caseData.document_count || 0} Dokumente`}>
              <FileText className="h-3 w-3 text-primary-start" />
              <span className="text-[11px] font-medium text-text-secondary">{caseData.document_count || 0}</span>
            </div>

            {/* Alerts */}
            <button 
              onClick={handleCalendarNav}
              className="flex items-center gap-1 group/icon hover:bg-hover px-1 py-0.5 rounded transition-colors" 
              title={`${caseData.alert_count || 0} Afate`}
            >
              <AlertTriangle className="h-3 w-3 text-status-warning group-hover/icon:text-warning-start/80 transition-colors" />
              <span className="text-[11px] font-medium text-text-secondary group-hover/icon:text-text-primary">{caseData.alert_count || 0}</span>
            </button>

            {/* Events */}
            <button 
              onClick={handleCalendarNav}
              className="flex items-center gap-1 group/icon hover:bg-hover px-1 py-0.5 rounded transition-colors" 
              title={`${caseData.event_count || 0} Ngjarje`}
            >
              <CalendarDays className="h-3 w-3 text-secondary-start group-hover/icon:text-secondary-start/80 transition-colors" />
              <span className="text-[11px] font-medium text-text-secondary group-hover/icon:text-text-primary">{caseData.event_count || 0}</span>
            </button>
          </div>
        </div>

        {/* Footer: Actions */}
        <div className="mt-3 pt-3 border-t border-border-main flex items-center justify-between">
          <span className="text-[10px] font-bold text-primary-start group-hover:text-primary-end transition-colors flex items-center gap-1">
            {t('general.view', 'Shiko')} {t('archive.details', 'Detajet')}
          </span>
          
          <motion.button
            onClick={handleDeleteClick}
            className="p-1.5 -mr-1.5 rounded-md text-text-secondary hover:text-status-danger hover:bg-danger-start/10 transition-colors z-20 relative"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title={t('general.delete', 'Fshij')}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
};

export default CaseCard;