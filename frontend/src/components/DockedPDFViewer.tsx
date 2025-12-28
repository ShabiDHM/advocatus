// FILE: src/components/DockedPDFViewer.tsx
// PHOENIX PROTOCOL - REUSABLE DOCKED VIEWER (GLASS STYLE)
// 1. STYLE: Upgraded to 'glass-high' for visual consistency with other UI elements.
// 2. UX: Refined icon styles and hover effects.

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, Maximize2, X } from 'lucide-react';
import { Document } from '../data/types';

interface DockedPDFViewerProps {
    document: Document;
    onExpand: () => void;
    onClose: () => void;
}

const DockedPDFViewer: React.FC<DockedPDFViewerProps> = ({ document, onExpand, onClose }) => {
    if (!document) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ y: "100%", opacity: 0 }}
                animate={{ y: "0%", opacity: 1 }}
                exit={{ y: "100%", opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="fixed bottom-4 right-4 z-[9998] w-[calc(100vw-2rem)] sm:w-80 glass-high p-3 rounded-2xl shadow-2xl flex items-center justify-between"
            >
                <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 bg-primary-start/10 rounded-lg border border-primary-start/20">
                        <FileText className="h-5 w-5 text-primary-start flex-shrink-0" />
                    </div>
                    <p className="text-sm font-medium text-white truncate">{document.file_name}</p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={onExpand} className="p-2 hover:bg-white/10 rounded-lg text-text-secondary hover:text-white transition-colors" title="Expand">
                        <Maximize2 size={16} />
                    </button>
                    <button onClick={onClose} className="p-2 hover:bg-red-500/10 rounded-lg text-text-secondary hover:text-red-400 transition-colors" title="Close">
                        <X size={16} />
                    </button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
};

export default DockedPDFViewer;