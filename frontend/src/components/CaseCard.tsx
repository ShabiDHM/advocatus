import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Case } from '../data/types';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Trash2, FileText, AlertTriangle, CalendarDays } from 'lucide-react';

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

  return (
    <MotionLink 
      // PHOENIX FIX: Changed path from '/case/' to '/cases/' to match the router definition in App.tsx.
      to={`/cases/${caseData.id}`}
      className="p-4 sm:p-6 rounded-2xl shadow-lg transition-all duration-300 cursor-pointer 
                 bg-background-light/50 backdrop-blur-sm border border-glass-edge
                 flex flex-col justify-between h-full"
      whileHover={{ 
        scale: 1.02, 
        boxShadow: '0 0 15px rgba(59, 130, 246, 0.3)'
      }}
      whileTap={{ scale: 0.98 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div>
        {/* Header Section */}
        <div className="flex flex-col mb-3 sm:mb-4">
          <h2 className="text-lg sm:text-xl font-bold text-text-primary compact-line-clamp-2 pr-2 break-words">
            {caseData.case_name}
          </h2>
          <p className="text-xs text-text-secondary/70 mt-1">
            {t('caseCard.createdOn')}: {formattedDate}
          </p>
        </div>
        
        {/* Client Details Section */}
        <div className="flex flex-col space-y-1 mb-4">
          <p className="text-sm sm:text-base font-bold text-text-primary border-b border-glass-edge/50 pb-2 mb-2">
            {t('caseCard.client')}
          </p>
          <div className="flex flex-col space-y-1 pl-1">
              <p className="text-sm text-text-secondary truncate">{caseData.client?.name || 'N/A'}</p>
              {caseData.client?.email && (
                  <p className="text-xs text-text-secondary/80 truncate">E-mail: {caseData.client.email}</p>
              )}
              {caseData.client?.phone && (
                  <p className="text-xs text-text-secondary/80 truncate">Tel: {caseData.client.phone}</p>
              )}
          </div>
        </div>
      </div>
      
      <div>
        {/* Statistics Section - Interactive Icons */}
        <div className="pt-3 sm:pt-4 border-t border-glass-edge/50 flex items-center justify-start space-x-4 text-text-secondary">
          {/* Documents - Static (Part of Case View) */}
          <div className="flex items-center space-x-1" title={`${caseData.document_count} ${t('caseCard.documents')}`}>
            <FileText className="h-4 w-4 text-primary-start" />
            <span className="text-xs sm:text-sm font-medium">{caseData.document_count}</span>
          </div>

          {/* Alerts - Clickable -> Calendar */}
          <button 
            onClick={handleCalendarNav}
            className="flex items-center space-x-1 hover:text-accent-start transition-colors group" 
            title={`${caseData.alert_count} ${t('caseCard.alerts')}`}
          >
            <AlertTriangle className="h-4 w-4 text-accent-start group-hover:scale-110 transition-transform" />
            <span className="text-xs sm:text-sm font-medium">{caseData.alert_count}</span>
          </button>

          {/* Events - Clickable -> Calendar */}
          <button 
            onClick={handleCalendarNav}
            className="flex items-center space-x-1 hover:text-purple-400 transition-colors group" 
            title={`${caseData.event_count} ${t('caseCard.events')}`}
          >
            <CalendarDays className="h-4 w-4 text-purple-400 group-hover:scale-110 transition-transform" />
            <span className="text-xs sm:text-sm font-medium">{caseData.event_count}</span>
          </button>
        </div>

        {/* Footer: Actions */}
        <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t border-glass-edge/50 flex items-center justify-between text-xs text-text-secondary/70">
          <div className="text-primary-start hover:text-primary-end transition-colors font-medium flex items-center">
            {t('caseCard.viewDetails')} <span className="ml-1">→</span>
          </div>
          
          <motion.button
            onClick={handleDeleteClick}
            className="p-2 -m-2 text-red-500 hover:text-red-400 transition-colors"
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            title={t('caseCard.deleteCase')}
          >
            <Trash2 className="h-5 w-5" />
          </motion.button>
        </div>
      </div>
    </MotionLink>
  );
};

export default CaseCard;