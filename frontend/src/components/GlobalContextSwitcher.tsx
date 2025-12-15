// FILE: src/components/GlobalContextSwitcher.tsx
// PHOENIX PROTOCOL - COMPONENT V1.2 (PORTAL FIX)
// 1. FIX: Uses ReactDOM.createPortal to escape the stacking context.
// 2. LOGIC: Dropdown now renders at the document root, guaranteeing it appears on top.
// 3. STATUS: Final fix for the z-index issue.

import React, { useState, useRef, useEffect, ReactNode } from 'react';
import ReactDOM from 'react-dom';
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
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0, width: 0 });

  const contextItems: ContextItem[] = [
    { id: 'general', label: 'E Gjithë Dosja', icon: <Briefcase size={16} className="text-amber-400" /> },
    ...documents.map(doc => ({
      id: doc.id,
      label: doc.file_name,
      icon: <FileText size={16} className="text-blue-400" />,
    })),
  ];

  const selectedItem = contextItems.find(item => item.id === activeContextId) || contextItems[0];

  // Calculate position of the dropdown
  useEffect(() => {
    if (isOpen && dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom + window.scrollY,
        left: rect.left + window.scrollX,
        width: rect.width,
      });
    }
  }, [isOpen]);

  // Close when clicking outside
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

  const DropdownMenu = () => (
    <AnimatePresence>
      {isOpen && ReactDOM.createPortal(
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          className="fixed max-h-80 overflow-y-auto custom-scrollbar bg-background-dark border border-white/10 rounded-xl shadow-2xl z-[9999]"
          style={{
            top: menuPosition.top + 8, // Add a small gap
            left: menuPosition.left,
            width: menuPosition.width,
          }}
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
        </motion.div>,
        document.body
      )}
    </AnimatePresence>
  );

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center w-full justify-between gap-3 px-4 py-2 rounded-xl bg-black/20 hover:bg-black/40 border border-white/10 text-gray-200 text-sm font-medium transition-all"
      >
        <div className="flex items-center gap-3 truncate">
            {selectedItem.icon}
            <span className="truncate">{selectedItem.label}</span>
        </div>
        <ChevronDown size={16} className={`transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <DropdownMenu />
    </div>
  );
};

export default GlobalContextSwitcher;