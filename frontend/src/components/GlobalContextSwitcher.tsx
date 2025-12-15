// FILE: src/components/GlobalContextSwitcher.tsx
// PHOENIX PROTOCOL - COMPONENT V1.3 (COORDINATE FIX)
// 1. FIX: Removed window.scrollY from calculation (Fixed positioning is viewport-relative).
// 2. STATUS: Dropdown should now appear exactly under the button.

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
  activeContextId: string; 
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

  // Calculate position (Viewport Relative for Fixed Positioning)
  useEffect(() => {
    if (isOpen && dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom, // No scrollY needed for fixed
        left: rect.left,  // No scrollX needed for fixed
        width: rect.width,
      });
    }
  }, [isOpen]);

  // Handle Resize/Scroll to keep menu attached
  useEffect(() => {
      if (!isOpen) return;
      const handleUpdate = () => {
          if (dropdownRef.current) {
              const rect = dropdownRef.current.getBoundingClientRect();
              setMenuPosition({
                  top: rect.bottom,
                  left: rect.left,
                  width: rect.width,
              });
          }
      };
      window.addEventListener('scroll', handleUpdate, true); // true for capture
      window.addEventListener('resize', handleUpdate);
      return () => {
          window.removeEventListener('scroll', handleUpdate, true);
          window.removeEventListener('resize', handleUpdate);
      }
  }, [isOpen]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // Check if click is inside the button
      if (dropdownRef.current && dropdownRef.current.contains(event.target as Node)) {
          return;
      }
      // Note: We can't easily check if click is inside the portal content here 
      // without a ref to the portal, but usually closing on any outside click is fine 
      // as long as the menu items stop propagation.
      setIsOpen(false);
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (id: string) => {
    onContextChange(id);
    setIsOpen(false);
  };

  return (
    <>
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
        </div>

        <AnimatePresence>
        {isOpen && ReactDOM.createPortal(
            <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="fixed max-h-80 overflow-y-auto custom-scrollbar bg-background-dark border border-white/10 rounded-xl shadow-2xl z-[9999]"
            style={{
                top: menuPosition.top + 8,
                left: menuPosition.left,
                width: menuPosition.width,
                minWidth: '200px' // Ensure it's not too thin on mobile
            }}
            onMouseDown={(e) => e.stopPropagation()} // Prevent outside click listener from firing immediately
            >
            {contextItems.map(item => (
                <button
                key={item.id}
                onClick={() => handleSelect(item.id)}
                className="w-full text-left flex items-center gap-3 px-4 py-3 text-sm hover:bg-white/5 text-gray-200 transition-colors border-b border-white/5 last:border-0"
                >
                {item.icon}
                <span className="truncate">{item.label}</span>
                </button>
            ))}
            </motion.div>,
            document.body
        )}
        </AnimatePresence>
    </>
  );
};

export default GlobalContextSwitcher;