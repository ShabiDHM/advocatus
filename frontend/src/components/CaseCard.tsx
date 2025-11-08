// FILE: /home/user/advocatus-frontend/src/components/CaseCard.tsx
// DEFINITIVE VERSION 2.19 (PHOENIX PROTOCOL FIX: Data Contract Alignment)
// Corrected the use of 'case_name' to 'name' to align with the central 'Case' interface in types.ts.

import React from 'react';
import { Link } from 'react-router-dom';
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

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onDelete(caseData.id);
  };

  const formattedDate = new Date(caseData.created_at).toLocaleDateString(undefined, {
    year: 'numeric', month: '2-digit', day: '2-digit'
  });

  return (
    <MotionLink 
      to={`/case/${caseData.id}`}
      className="p-6 rounded-2xl shadow-lg transition-all duration-300 cursor-pointer 
                 bg-background-light/50 backdrop-blur-sm border border-glass-edge
                 flex flex-col justify-between"
      whileHover={{ 
        scale: 1.03, 
        boxShadow: '0 0 15px rgba(59, 130, 246, 0.4)'
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div>
        {/* 1. Header Section */}
        <div className="flex flex-col mb-4">
          <h2 className="text-xl font-bold text-text-primary compact-line-clamp-2 pr-4">
            {caseData.name} {/* PHOENIX FIX: Changed caseData.case_name to caseData.name */}
          </h2>
          {/* PHOENIX PROTOCOL FIX: Use the correct translation key */}
          <p className="text-xs text-text-secondary/70 mt-1">
            {t('caseCard.createdOn')}: {formattedDate}
          </p>
        </div>
        
        {/* 2. Client Details Section */}
        <div className="flex flex-col space-y-1 mb-4">
          <p className="text-base font-bold text-text-primary border-b border-glass-edge/50 pb-2 mb-2">
            {t('caseCard.client')}
          </p>
          <div className="flex flex-col space-y-1 pl-1">
              <p className="text-sm text-text-secondary">{caseData.client?.name || 'N/A'}</p>
              {caseData.client?.email && (
                  <p className="text-xs text-text-secondary/80">E-mail: {caseData.client.email}</p>
              )}
              {caseData.client?.phone && (
                  <p className="text-xs text-text-secondary/80">Tel: {caseData.client.phone}</p>
              )}
          </div>
        </div>
      </div>
      
      <div>
        {/* 3. Case Statistics Section */}
        <div className="pt-4 border-t border-glass-edge/50 flex items-center justify-start space-x-4 text-text-secondary">
          <div className="flex items-center space-x-1" title={`${caseData.document_count} ${t('caseCard.documents')}`}>
            <FileText className="h-4 w-4 text-primary-start" />
            <span className="text-sm font-medium">{caseData.document_count}</span>
          </div>
          <div className="flex items-center space-x-1" title={`${caseData.alert_count} ${t('caseCard.alerts')}`}>
            <AlertTriangle className="h-4 w-4 text-accent-start" />
            <span className="text-sm font-medium">{caseData.alert_count}</span>
          </div>
          <div className="flex items-center space-x-1" title={`${caseData.event_count} ${t('caseCard.events')}`}>
            <CalendarDays className="h-4 w-4 text-purple-400" />
            <span className="text-sm font-medium">{caseData.event_count}</span>
          </div>
        </div>

        {/* 4. Footer: Actions */}
        <div className="mt-4 pt-4 border-t border-glass-edge/50 flex items-center justify-between text-xs text-text-secondary/70">
          {/* PHOENIX PROTOCOL FIX: Moved View Details link to the left and hid the ID */}
          <div className="text-primary-start hover:text-primary-end transition-colors font-medium">
            {t('caseCard.viewDetails')} →
          </div>
          
          <motion.button
            onClick={handleDeleteClick}
            className="text-red-500 hover:text-red-400 transition-colors"
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