// FILE: src/components/FindingsModal.tsx
// PHOENIX PROTOCOL - FINDINGS MODAL V2.0 (MARKDOWN RENDERER)
// 1. UI: Replaced raw text output with <ReactMarkdown>.
// 2. STYLE: Added specific Tailwind classes for headers, bold text, and lists.
// 3. STATUS: Visuals are now professional and structured.

import React, { useEffect } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Lightbulb, FileText, ExternalLink } from 'lucide-react';
import { Finding } from '../data/types';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface FindingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  findings: Finding[];
}

// Custom Scrollbar for the modal content
const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
`;

const FindingsModal: React.FC<FindingsModalProps> = ({ isOpen, onClose, findings }) => {
  const { t } = useTranslation();

  // Prevent background scrolling when modal is open
  useEffect(() => {
    if (isOpen) { document.body.style.overflow = 'hidden'; } 
    else { document.body.style.overflow = 'unset'; }
    return () => { document.body.style.overflow = 'unset'; };
  }, [isOpen]);

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-[9999] p-0 sm:p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.95, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.95, opacity: 0, y: 20 }}
          className="bg-background-dark w-full h-full sm:h-auto sm:max-h-[85vh] sm:max-w-4xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-glass-edge sm:border-opacity-50"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 sm:p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/90 backdrop-blur-md flex-shrink-0">
            <h2 className="text-xl sm:text-2xl font-bold text-text-primary flex items-center gap-3">
              <Lightbulb className="text-amber-400 h-6 w-6" />
              <span>{t('caseView.findingsTitle')}</span>
              <span className="bg-white/10 text-gray-300 text-xs px-2.5 py-1 rounded-full font-mono">{findings.length}</span>
            </h2>
            <button onClick={onClose} className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-full transition-colors">
                <X size={24} />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 sm:p-6 overflow-y-auto space-y-4 flex-1 custom-scrollbar bg-background-dark/50">
            <style>{scrollbarStyles}</style>
            
            {findings.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                    <p>{t('caseView.noFindings')}</p>
                </div>
            ) : (
                findings.map((finding) => (
                    <motion.div 
                        key={finding.id} 
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="bg-black/20 border border-white/5 p-5 rounded-xl hover:bg-black/30 transition-colors group relative overflow-hidden"
                    >
                        {/* Left Accent Bar */}
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber-500/50 group-hover:bg-amber-500 transition-colors"></div>
                        
                        <div className="pl-3">
                            {/* MARKDOWN RENDERER */}
                            <div className="text-gray-200 text-sm leading-relaxed mb-3 markdown-content">
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                        // Headers (e.g. ### Main Text Extraction)
                                        h1: ({node, ...props}) => <h1 className="text-lg font-bold text-primary-400 mt-3 mb-2 uppercase tracking-wide" {...props} />,
                                        h2: ({node, ...props}) => <h2 className="text-base font-bold text-primary-400 mt-3 mb-2" {...props} />,
                                        h3: ({node, ...props}) => <h3 className="text-sm font-bold text-amber-400 mt-2 mb-1 uppercase tracking-wider" {...props} />,
                                        
                                        // Paragraphs
                                        p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                                        
                                        // Bold Text (**text**)
                                        strong: ({node, ...props}) => <span className="font-bold text-white bg-white/5 px-1 rounded" {...props} />,
                                        
                                        // Lists
                                        ul: ({node, ...props}) => <ul className="list-disc pl-5 space-y-1 my-2 text-gray-300" {...props} />,
                                        ol: ({node, ...props}) => <ol className="list-decimal pl-5 space-y-1 my-2 text-gray-300" {...props} />,
                                        li: ({node, ...props}) => <li className="pl-1" {...props} />,
                                        
                                        // Blockquotes
                                        blockquote: ({node, ...props}) => <blockquote className="border-l-2 border-gray-600 pl-3 italic text-gray-400 my-2" {...props} />
                                    }}
                                >
                                    {finding.finding_text}
                                </ReactMarkdown>
                            </div>

                            {/* Meta Info */}
                            <div className="flex flex-wrap items-center gap-4 mt-3 pt-3 border-t border-white/5 text-xs text-gray-500">
                                <div className="flex items-center gap-1.5 text-amber-500/80">
                                    <FileText size={12} />
                                    <span className="font-medium">{t('caseView.findingSource')}: </span>
                                    <span className="text-gray-400 italic truncate max-w-[200px]">{finding.document_name || 'N/A'}</span>
                                </div>
                                <div className="flex items-center gap-1.5 ml-auto">
                                    <ExternalLink size={12} className="text-gray-600" />
                                    <span>Q {finding.confidence_score ? Math.round(finding.confidence_score * 100) : 100}%</span>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                ))
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center flex-shrink-0">
              <button onClick={onClose} className="w-full sm:w-auto px-8 py-2.5 bg-secondary-start hover:bg-secondary-end text-white rounded-xl font-bold transition-all shadow-lg glow-secondary">
                  {t('general.close')}
              </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default FindingsModal;