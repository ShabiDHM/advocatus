// FILE: src/components/DocumentSelector.tsx
// PHOENIX PROTOCOL - DOCUMENT SELECTOR V1.0 (MULTI‑SELECT WITH CHECKBOXES)
// 1. Replaces old GlobalContextSwitcher.
// 2. Allows selecting multiple documents via checkboxes.

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
        className="glass-input w-full flex items-center justify-between gap-2 px-4 py-2 rounded-xl text-sm font-medium text-white hover:bg-white/5 transition-colors disabled:opacity-50"
      >
        <span className="flex items-center gap-2">
          <FileText size={16} className="text-primary-start" />
          {buttonLabel}
        </span>
        <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-full left-0 mt-1 w-64 max-h-64 overflow-y-auto glass-panel border border-white/10 rounded-lg shadow-xl z-50 p-2"
          >
            {documents.length === 0 ? (
              <div className="text-xs text-gray-400 p-2">Nuk ka dokumente</div>
            ) : (
              <>
                <div className="flex items-center gap-2 p-1 border-b border-white/10 mb-1">
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
                    className="flex items-center gap-2 p-1 hover:bg-white/5 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(doc.id)}
                      onChange={() => toggleDocument(doc.id)}
                      className="rounded border-white/20 bg-white text-primary-start checked:bg-primary-start checked:border-transparent focus:ring-primary-start"
                    />
                    <span className="text-xs text-gray-300 truncate">{doc.file_name}</span>
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