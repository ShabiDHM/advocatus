// FILE: src/components/DocumentSelector.tsx
// PHOENIX PROTOCOL - DOCUMENT SELECTOR V8.0 (CONSISTENT TYPOGRAPHY)
// 1. FIXED: Corrected dropdown background and borders to use V6.0 Design System tokens.
// 2. FIXED: Enhanced Z-Index to ensure the menu always floats over Workspace panels.
// 3. TYPOGRAPHY: Standardized text sizes for better readability
// 4. RETAINED: Multi-select logic and click-outside closing.

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, FileText, CheckSquare, Square } from 'lucide-react';

interface DocumentSelectorProps {
  documents: Array<{ id: string; file_name: string }>;
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  className?: string;
  disabled?: boolean;
}

export const DocumentSelector: React.FC<DocumentSelectorProps> = ({
  documents,
  selectedIds,
  onChange,
  className = '',
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleDocument = (docId: string) => {
    if (selectedIds.includes(docId)) {
      onChange(selectedIds.filter(id => id !== docId));
    } else {
      onChange([...selectedIds, docId]);
    }
  };

  const selectAll = () => {
    if (selectedIds.length === documents.length) {
      onChange([]);
    } else {
      onChange(documents.map(d => d.id));
    }
  };

  const allSelected = documents.length > 0 && selectedIds.length === documents.length;
  const noneSelected = selectedIds.length === 0;
  
  const buttonLabel = noneSelected
    ? 'E gjithë dosja'
    : `${selectedIds.length} Dokumente`;

  return (
    <div className={`relative w-full h-full ${className}`} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="w-full h-full flex items-center justify-between gap-3 px-6 rounded-xl bg-surface border border-border-main shadow-sm transition-all duration-300 hover:border-primary/50 disabled:opacity-40 disabled:cursor-not-allowed group"
      >
        <span className="flex items-center gap-3 truncate">
          <FileText size={16} className="text-primary opacity-70 group-hover:opacity-100 transition-opacity" />
          <span className="text-xs font-semibold uppercase tracking-wide text-text-secondary truncate">
            {buttonLabel}
          </span>
        </span>
        <ChevronDown size={14} className={`text-text-muted transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            className="absolute top-full left-0 mt-2 w-full min-w-[280px] bg-glass backdrop-blur-xl border border-border-main rounded-2xl shadow-lg z-[100] overflow-hidden py-2"
          >
            {documents.length === 0 ? (
              <div className="px-6 py-8 text-center flex flex-col items-center gap-3 opacity-40">
                <FileText size={32} className="text-text-muted" />
                <p className="text-xs font-medium uppercase tracking-wide text-text-muted">Nuk ka dokumente në këtë lëndë</p>
              </div>
            ) : (
              <>
                {/* Header: Bulk Actions */}
                <div className="px-3 pb-2 mb-2 border-b border-border-main/50">
                  <button
                    onClick={selectAll}
                    className="w-full flex items-center justify-center gap-2 py-2 rounded-lg bg-canvas hover:bg-primary/5 text-xs font-semibold uppercase tracking-wide text-primary transition-all"
                  >
                    {allSelected ? 'Çzgjidh të gjitha' : 'Zgjidh të gjitha'}
                  </button>
                </div>

                {/* List: Document Selection */}
                <div className="max-h-72 overflow-y-auto custom-scrollbar px-2 space-y-1">
                  {documents.map(doc => {
                    const isSelected = selectedIds.includes(doc.id);
                    return (
                        <label
                            key={doc.id}
                            className={`flex items-center gap-3 p-3 rounded-xl transition-all cursor-pointer border ${isSelected ? 'bg-primary/5 border-primary/20' : 'bg-transparent border-transparent hover:bg-hover'}`}
                        >
                            <div className="shrink-0 transition-transform active:scale-90">
                                {isSelected ? <CheckSquare size={16} className="text-primary" /> : <Square size={16} className="text-text-muted" />}
                                <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleDocument(doc.id)}
                                    className="hidden"
                                />
                            </div>
                            <span className={`text-sm font-medium truncate ${isSelected ? 'text-text-primary' : 'text-text-secondary'}`}>
                                {doc.file_name}
                            </span>
                        </label>
                    );
                  })}
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};