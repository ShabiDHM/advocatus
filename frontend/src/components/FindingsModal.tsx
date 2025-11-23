// FILE: src/components/FindingsModal.tsx
// PHOENIX PROTOCOL - ARCHITECTURAL FIX
// 1. PORTAL: Moved to document.body to fix header overlap issues.
// 2. Z-INDEX: Boosted to z-[9999].
// 3. MOBILE: Header layout hardened to ensure Close button is always clickable.

import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';
import { Finding } from '../data/types';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Lightbulb, FileText, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface FindingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  findings: Finding[];
}

const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
`;

const FindingsModal: React.FC<FindingsModalProps> = ({ isOpen, onClose, findings }) => {
  const { t } = useTranslation();

  // Handle Body Scroll Lock
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
        <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            // Z-9999 to beat the global header. Fixed inset-0 covers entire screen.
            className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[9999] p-0 sm:p-4"
            onClick={onClose}
        >
            <motion.div 
                initial={{ scale: 0.9, opacity: 0, y: 20 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.9, opacity: 0, y: 20 }}
                className="bg-background-dark w-full h-full sm:h-auto sm:max-h-[90vh] sm:max-w-3xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-glass-edge sm:border-opacity-50"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header - Hardened for Mobile */}
                <div className="p-4 sm:p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/90 backdrop-blur-md flex-shrink-0 gap-4">
                    <h2 className="text-lg sm:text-2xl font-bold text-text-primary flex items-center gap-2 min-w-0">
                        <div className="p-1.5 bg-yellow-400/10 rounded-lg flex-shrink-0">
                             <Lightbulb className="text-yellow-400 h-5 w-5 sm:h-6 sm:w-6" />
                        </div>
                        <span className="truncate">{t('caseView.findingsTitle')}</span>
                        <span className="text-xs font-medium px-2 py-1 rounded-full bg-background-dark border border-glass-edge text-text-secondary flex-shrink-0">
                            {findings.length}
                        </span>
                    </h2>
                    
                    {/* Close Button - Guaranteed Visibility */}
                    <button 
                        onClick={onClose} 
                        className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-full transition-colors flex-shrink-0"
                        title={t('general.close', 'Mbyll')}
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-4 sm:p-6 overflow-y-auto flex-1 custom-scrollbar relative bg-background-dark/50">
                    <style>{scrollbarStyles}</style>

                    {findings.length === 0 ? (
                        <div className="text-center text-text-secondary py-10">
                            <p>{t('caseView.noFindings', 'Asnjë gjetje nuk është identifikuar ende.')}</p>
                        </div>
                    ) : (
                        <div className="space-y-4 pb-4">
                            {findings.map((finding, index) => (
                                <motion.div 
                                    key={finding.id} 
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                    className="group relative p-4 sm:p-5 bg-background-dark rounded-xl border border-glass-edge/30 hover:border-primary-start/50 transition-all duration-300 shadow-sm"
                                >
                                    <div className="absolute left-0 top-4 bottom-4 w-1 bg-gradient-to-b from-yellow-400 to-orange-500 rounded-r-full opacity-70 group-hover:opacity-100 transition-opacity" />
                                    
                                    <div className="pl-3">
                                        <p className="text-sm sm:text-base text-gray-200 leading-relaxed">
                                            {finding.finding_text}
                                        </p>
                                        
                                        <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                                            <div className="flex items-center gap-2 px-2 py-1 rounded-md bg-black/20 border border-white/5 text-xs text-gray-400 w-full sm:w-auto">
                                                <FileText className="h-3 w-3 text-yellow-500 flex-shrink-0" />
                                                <span className="font-medium text-gray-300 whitespace-nowrap">{t('caseView.findingSource')}:</span>
                                                <span className="truncate max-w-full">{finding.document_name || finding.document_id}</span>
                                            </div>
                                            
                                            {finding.confidence_score !== undefined && finding.confidence_score > 0 && (
                                                <div className="flex items-center gap-1.5 self-end sm:self-auto" title={t('caseView.confidenceScore')}>
                                                    <Search className="h-3 w-3 text-accent-start" />
                                                    <span className="text-xs font-mono text-accent-start">{Math.round(finding.confidence_score * 100)}%</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}
                </div>
                
                {/* Footer */}
                <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center flex-shrink-0 safe-area-pb">
                    <button onClick={onClose} className="w-full sm:w-auto px-6 py-3 sm:py-2 bg-background-light hover:bg-white/10 border border-glass-edge text-white rounded-xl font-medium transition-all shadow-lg active:scale-95">
                        {t('general.close', 'Mbyll')}
                    </button>
                </div>
            </motion.div>
        </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default FindingsModal;