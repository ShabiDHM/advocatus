// FILE: src/components/CaseCard.tsx
// PHOENIX PROTOCOL - CASE CARD V5.0 (GLASS STYLE)
// 1. VISUALS: Full Glassmorphism adoption (glass-panel).
// 2. UX: Enhanced hover states with gradient overlays and smooth lifting animation.
// 3. COLORS: Standardized icon colors using system variables (primary-start, accent-start, etc.).

import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Case } from '../data/types';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Trash2, FileText, AlertTriangle, CalendarDays, User, Mail, Phone } from 'lucide-react';

const MotionLink = motion(Link);

interface CaseCardProps {
  caseData: Case;
  onDelete: (caseId: string) => void;
}

const CaseCard: React.FC<CaseCardProps> = ({ caseData, onDelete }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDelete(caseData.id);
  };

  const handleCalendarNav = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    navigate('/calendar');
  };

  const formattedDate = new Date(caseData.created_at).toLocaleDateString(undefined, {
    year: 'numeric', month: '2-digit', day: '2-digit'
  });

  const hasTitle = caseData.title && caseData.title.trim() !== '';
  const displayTitle = hasTitle ? caseData.title : t('caseCard.untitled');

  return (
    <MotionLink 
      to={`/cases/${caseData.id}`}
      className="glass-panel group relative flex flex-col justify-between h-full p-6 rounded-2xl transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl"
      whileTap={{ scale: 0.98 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Gradient Overlay on Hover */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-primary-start/5 to-secondary-end/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

      <div>
        {/* Header Section */}
        <div className="flex flex-col mb-4 relative z-10">
          <div className="flex justify-between items-start gap-2">
            <div className="flex flex-col">
                <h2 className={`text-xl font-bold line-clamp-2 leading-tight tracking-tight ${!hasTitle ? 'text-text-secondary italic' : 'text-white group-hover:text-primary-start transition-colors'}`}>
                    {displayTitle}
                </h2>
            </div>
          </div>
          
          <div className="flex items-center gap-2 mt-3">
            <p className="text-sm text-text-secondary font-medium">
                {t('caseCard.createdOn')}: <span className="text-gray-300">{formattedDate}</span>
            </p>
          </div>
        </div>
        
        {/* Client Details Section */}
        <div className="flex flex-col mb-6 relative z-10">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/5">
             <User className="w-3.5 h-3.5 text-primary-start" />
             <span className="text-xs font-bold text-text-secondary uppercase tracking-wider">{t('caseCard.client')}</span>
          </div>
          
          <div className="space-y-1.5 pl-1">
              <p className="text-base font-medium text-white truncate">
                {caseData.client?.name || t('general.notAvailable')}
              </p>
              
              {caseData.client?.email && (
                  <div className="flex items-center gap-2 text-sm text-text-secondary">
                      <Mail className="w-3.5 h-3.5" />
                      <span className="truncate">{caseData.client.email}</span>
                  </div>
              )}
              {caseData.client?.phone && (
                  <div className="flex items-center gap-2 text-sm text-text-secondary">
                      <Phone className="w-3.5 h-3.5" />
                      <span className="truncate">{caseData.client.phone}</span>
                  </div>
              )}
          </div>
        </div>
      </div>
      
      <div className="relative z-10">
        {/* Statistics Section - Interactive Icons */}
        <div className="pt-4 border-t border-white/5 flex items-center justify-between gap-2">
          
          <div className="flex items-center gap-4">
              {/* Documents */}
              <div className="flex items-center gap-1.5" title={`${caseData.document_count || 0} ${t('caseCard.documents')}`}>
                <FileText className="h-4 w-4 text-blue-400" />
                <span className="text-sm font-medium text-text-secondary">{caseData.document_count || 0}</span>
              </div>

              {/* Alerts */}
              <button 
                onClick={handleCalendarNav}
                className="flex items-center gap-1.5 group/icon hover:bg-white/5 px-1.5 py-0.5 rounded transition-colors" 
                title={`${caseData.alert_count || 0} ${t('caseCard.alerts')}`}
              >
                <AlertTriangle className="h-4 w-4 text-accent-start group-hover/icon:text-accent-end transition-colors" />
                <span className="text-sm font-medium text-text-secondary group-hover/icon:text-white">{caseData.alert_count || 0}</span>
              </button>

              {/* Events */}
              <button 
                onClick={handleCalendarNav}
                className="flex items-center gap-1.5 group/icon hover:bg-white/5 px-1.5 py-0.5 rounded transition-colors" 
                title={`${caseData.event_count || 0} ${t('caseCard.events')}`}
              >
                <CalendarDays className="h-4 w-4 text-secondary-start group-hover/icon:text-secondary-end transition-colors" />
                <span className="text-sm font-medium text-text-secondary group-hover/icon:text-white">{caseData.event_count || 0}</span>
              </button>
          </div>
        </div>

        {/* Footer: Actions */}
        <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
          <span className="text-sm font-bold text-primary-start group-hover:text-primary-end transition-colors flex items-center gap-1 cursor-pointer">
            {t('caseCard.viewDetails')} 
          </span>
          
          <motion.button
            onClick={handleDeleteClick}
            className="p-2 -mr-2 rounded-lg text-text-secondary hover:text-red-400 hover:bg-red-500/10 transition-colors"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            title={t('caseCard.deleteCase')}
          >
            <Trash2 className="h-4 w-4" />
          </motion.button>
        </div>
      </div>
    </MotionLink>
  );
};

export default CaseCard;