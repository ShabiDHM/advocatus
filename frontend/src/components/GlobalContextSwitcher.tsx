// FILE: src/components/GlobalContextSwitcher.tsx
// PHOENIX PROTOCOL - NEW COMPONENT V1.0
// 1. UI: A reusable dropdown to select Case vs a specific Document.
// 2. LOGIC: Centralizes the "active context" for the entire page.

import React, { useState, useRef, useEffect, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Briefcase, FileText } from 'lucide-react';
import { Document } from '../data/types';

interface ContextItem {
  id: string;
  label: string;
  icon: ReactNode;
}

interface GlobalContextSwitcherProps {
  documents: Document[];
  activeContextId: string; // 'general' or a document ID
  onContextChange: (id: string) => void;
  className?: string;
}

const GlobalContextSwitcher: React.FC<GlobalContextSwitcherProps> = ({
  documents,
  activeContextId,
  onContextChange,
  className,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const contextItems: ContextItem[] = [
    { id: 'general', label: 'E Gjithë Dosja', icon: <Briefcase size={16} className="text-amber-400" /> },
    ...documents.map(doc => ({
      id: doc.id,
      label: doc.file_name,
      icon: <FileText size={16} className="text-blue-400" />,
    })),
  ];

  const selectedItem = contextItems.find(item => item.id === activeContextId) || contextItems[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (id: string) => {
    onContextChange(id);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-4 py-2 rounded-xl bg-black/20 hover:bg-black/40 border border-white/10 text-gray-200 text-sm font-medium transition-all"
      >
        {selectedItem.icon}
        <span className="truncate max-w-[200px]">{selectedItem.label}</span>
        <ChevronDown size={16} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute right-0 top-full mt-2 w-72 max-h-80 overflow-y-auto custom-scrollbar bg-background-dark border border-white/10 rounded-xl shadow-2xl z-50"
          >
            {contextItems.map(item => (
              <button
                key={item.id}
                onClick={() => handleSelect(item.id)}
                className="w-full text-left flex items-center gap-3 px-4 py-3 text-sm hover:bg-white/5 text-gray-200 transition-colors"
              >
                {item.icon}
                <span className="truncate">{item.label}</span>
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default GlobalContextSwitcher;