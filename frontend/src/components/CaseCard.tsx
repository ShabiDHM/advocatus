// FILE: src/components/CaseCard.tsx
import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Case } from '../data/types';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Trash2, FileText, AlertTriangle, CalendarDays, User, Mail, Phone, Lightbulb, Hash } from 'lucide-react';

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

  // PHOENIX FIX: Robust Title Handling
  // If case_name is missing, fall back to Case Number, then "Untitled Case"
  const displayTitle = caseData.case_name && caseData.case_name.trim() !== '' 
      ? caseData.case_name 
      : (caseData.case_number ? `${t('caseCard.caseNumber')} #${caseData.case_number}` : t('caseCard.untitled'));

  return (
    <MotionLink 
      to={`/cases/${caseData.id}`}
      className="group relative flex flex-col justify-between h-full p-6 rounded-2xl transition-all duration-300
                 bg-gray-900/40 backdrop-blur-md border border-white/5 shadow-xl hover:shadow-2xl hover:bg-gray-800/60"
      whileHover={{ scale: 1.01, y: -2 }}
      whileTap={{ scale: 0.99 }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      {/* Hover Glow Effect */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

      <div>
        {/* Header Section */}
        <div className="flex flex-col mb-4 relative z-10">
          <div className="flex justify-between items-start gap-2">
            <h2 className={`text-lg font-bold line-clamp-2 leading-tight tracking-tight ${!caseData.case_name ? 'text-gray-400 italic' : 'text-gray-100'}`}>
                {displayTitle}
            </h2>
            {/* Status Indicator Dot */}
            <div 
                className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    caseData.status === 'open' ? 'bg-green-400 shadow-[0_0_8px_rgba(74,222,128,0.5)]' : 'bg-gray-500'
                }`} 
                title={caseData.status} 
            />
          </div>
          
          <div className="flex items-center gap-2 mt-2">
            {!caseData.case_name && caseData.case_number && (
                 <Hash className="w-3 h-3 text-gray-600" />
            )}
            <p className="text-xs text-gray-500 font-medium">
                {t('caseCard.createdOn')}: <span className="text-gray-400">{formattedDate}</span>
            </p>
          </div>
        </div>
        
        {/* Client Details Section */}
        <div className="flex flex-col mb-6 relative z-10">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/5">
             <User className="w-3 h-3 text-indigo-400" />
             <span className="text-xs font-bold text-gray-300 uppercase tracking-wider">{t('caseCard.client')}</span>
          </div>
          
          <div className="space-y-1.5 pl-1">
              <p className="text-sm font-medium text-gray-200 truncate">
                {caseData.client?.name || t('general.notAvailable')}
              </p>
              
              {caseData.client?.email && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Mail className="w-3 h-3" />
                      <span className="truncate">{caseData.client.email}</span>
                  </div>
              )}
              {caseData.client?.phone && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Phone className="w-3 h-3" />
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
                <FileText className="h-4 w-4 text-blue-400/80" />
                <span className="text-sm font-medium text-gray-400">{caseData.document_count || 0}</span>
              </div>

              {/* Findings (Confirmed 7) */}
              <div className="flex items-center gap-1.5" title={`${caseData.finding_count || 0} AI Findings (Review needed)`}>
                <Lightbulb className="h-4 w-4 text-yellow-500/80" />
                <span className="text-sm font-medium text-gray-400">{caseData.finding_count || 0}</span>
              </div>

              {/* Alerts */}
              <button 
                onClick={handleCalendarNav}
                className="flex items-center gap-1.5 group/icon" 
                title={`${caseData.alert_count || 0} Active System Alerts`}
              >
                <AlertTriangle className="h-4 w-4 text-orange-400/80 group-hover/icon:text-orange-400 transition-colors" />
                <span className="text-sm font-medium text-gray-400 group-hover/icon:text-gray-200">{caseData.alert_count || 0}</span>
              </button>

              {/* Events */}
              <button 
                onClick={handleCalendarNav}
                className="flex items-center gap-1.5 group/icon" 
                title={`${caseData.event_count || 0} Confirmed Calendar Events`}
              >
                <CalendarDays className="h-4 w-4 text-purple-400/80 group-hover/icon:text-purple-400 transition-colors" />
                <span className="text-sm font-medium text-gray-400 group-hover/icon:text-gray-200">{caseData.event_count || 0}</span>
              </button>
          </div>
        </div>

        {/* Footer: Actions */}
        <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">
          <span className="text-xs font-medium text-indigo-400 group-hover:text-indigo-300 transition-colors flex items-center gap-1">
            {t('caseCard.viewDetails')} 
          </span>
          
          <motion.button
            onClick={handleDeleteClick}
            className="p-2 -mr-2 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-400/10 transition-colors"
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