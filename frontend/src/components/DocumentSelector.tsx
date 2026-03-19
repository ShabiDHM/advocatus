// FILE: src/components/DocumentSelector.tsx
// PHOENIX PROTOCOL - DOCUMENT SELECTOR V1.2 (THEME VARIABLES)
// 1. REPLACED: hardcoded colors with theme variables.
// 2. RETAINED: Multi‑select checkbox functionality.

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, FileText } from 'lucide-react';

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
    : `${selectedIds.length} dokumente`;

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="glass-input w-full h-12 md:h-11 rounded-xl flex items-center justify-between gap-2 px-4 py-2 text-sm font-medium text-text-primary hover:bg-background-light/10 transition-colors disabled:opacity-50"
      >
        <span className="flex items-center gap-2 truncate">
          <FileText size={16} className="text-primary-start shrink-0" />
          <span className="truncate">{buttonLabel}</span>
        </span>
        <ChevronDown size={16} className={`shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-0 mt-1 w-64 max-h-64 overflow-y-auto glass-panel border border-glass-edge rounded-lg shadow-xl z-50 p-2"
          >
            {documents.length === 0 ? (
              <div className="text-xs text-text-secondary/70 p-2">Nuk ka dokumente</div>
            ) : (
              <>
                <div className="flex items-center gap-2 p-1 border-b border-glass-edge mb-1">
                  <button
                    onClick={selectAll}
                    className="text-xs text-primary-start hover:underline"
                  >
                    {allSelected ? 'Çzgjidh të gjitha' : 'Zgjidh të gjitha'}
                  </button>
                </div>
                {documents.map(doc => (
                  <label
                    key={doc.id}
                    className="flex items-center gap-2 p-1 hover:bg-background-light/10 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(doc.id)}
                      onChange={() => toggleDocument(doc.id)}
                      className="rounded border-glass-edge bg-background-light text-primary-start checked:bg-primary-start checked:border-transparent focus:ring-primary-start"
                    />
                    <span className="text-xs text-text-secondary truncate">{doc.file_name}</span>
                  </label>
                ))}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};