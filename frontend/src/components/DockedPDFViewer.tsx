// FILE: src/components/DockedPDFViewer.tsx
// PHOENIX PROTOCOL - DOCKED PDF VIEWER V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: glass-panel, border-main, text-text-primary, text-text-secondary, text-text-muted.
// 2. Icon container uses primary-start/10 with primary-start border.
// 3. Preserved animations and interactions.

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
                className="fixed bottom-4 right-4 z-[9998] w-[calc(100vw-2rem)] sm:w-80 glass-panel border border-main p-3 rounded-2xl shadow-2xl flex items-center justify-between"
            >
                <div className="flex items-center gap-3 min-w-0">
                    <div className="p-2 bg-primary-start/10 rounded-lg border border-primary-start/20">
                        <FileText className="h-5 w-5 text-primary-start flex-shrink-0" />
                    </div>
                    <p className="text-sm font-medium text-text-primary truncate">{document.file_name}</p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={onExpand} className="p-2 hover:bg-surface/50 rounded-lg text-text-secondary hover:text-text-primary transition-colors" title="Expand">
                        <Maximize2 size={16} />
                    </button>
                    <button onClick={onClose} className="p-2 hover:bg-danger-start/10 rounded-lg text-text-secondary hover:text-danger-start transition-colors" title="Close">
                        <X size={16} />
                    </button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
};

export default DockedPDFViewer;