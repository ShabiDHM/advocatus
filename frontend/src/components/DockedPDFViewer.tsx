// FILE: src/components/DockedPDFViewer.tsx
// PHOENIX PROTOCOL - REUSABLE DOCKED VIEWER COMPONENT
// 1. REFACTOR: Extracted from CaseViewPage into a reusable component.
// 2. PURPOSE: Provides a consistent "minimized" document view across the application.

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
                className="fixed bottom-4 right-4 z-[9998] w-72 bg-background-light/80 backdrop-blur-xl border border-glass-edge rounded-xl shadow-2xl flex items-center justify-between p-3"
            >
                <div className="flex items-center gap-3 min-w-0">
                    <FileText className="h-5 w-5 text-primary-start flex-shrink-0" />
                    <p className="text-xs font-medium text-gray-200 truncate">{document.file_name}</p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                    <button onClick={onExpand} className="p-1.5 hover:bg-white/10 rounded-md text-gray-400 hover:text-white transition-colors" title="Expand">
                        <Maximize2 size={16} />
                    </button>
                    <button onClick={onClose} className="p-1.5 hover:bg-red-500/10 rounded-md text-gray-400 hover:text-red-400 transition-colors" title="Close">
                        <X size={16} />
                    </button>
                </div>
            </motion.div>
        </AnimatePresence>
    );
};

export default DockedPDFViewer;