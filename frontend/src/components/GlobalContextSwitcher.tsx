// FILE: src/components/GlobalContextSwitcher.tsx
// PHOENIX PROTOCOL - COMPONENT V1.7 (FINAL)
// 1. FIX: Removed render blocking conditions.
// 2. LOGIC: Uses useLayoutEffect for instant, flicker-free positioning.
// 3. STATUS: Complete and Production-ready.

import React, { useState, useRef, useLayoutEffect, useEffect, ReactNode } from 'react';
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
  
  // Initialize with innocuous defaults to prevent render crashes
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0, width: 200 });

  const contextItems: ContextItem[] = [
    { id: 'general', label: 'E Gjithë Dosja', icon: <Briefcase size={16} className="text-amber-400" /> },
    ...documents.map(doc => ({
      id: doc.id,
      label: doc.file_name,
      icon: <FileText size={16} className="text-blue-400" />,
    })),
  ];

  const selectedItem = contextItems.find(item => item.id === activeContextId) || contextItems[0];

  // useLayoutEffect runs synchronously after DOM mutations but before paint.
  // This prevents the "flash" of the menu at the wrong position.
  useLayoutEffect(() => {
    if (isOpen && dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom,
        left: rect.left,
        width: rect.width,
      });
    }
  }, [isOpen]);

  // Handle Scroll/Resize to keep the menu attached if the user scrolls while it's open
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

      window.addEventListener('scroll', handleUpdate, true); // true = capture phase
      window.addEventListener('resize', handleUpdate);
      
      return () => {
          window.removeEventListener('scroll', handleUpdate, true);
          window.removeEventListener('resize', handleUpdate);
      }
  }, [isOpen]);

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      // If clicking inside the trigger button, let the button handler manage it
      if (dropdownRef.current && dropdownRef.current.contains(event.target as Node)) {
          return;
      }
      setIsOpen(false);
    };
    
    if (isOpen) {
        document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

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
                type="button"
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
                transition={{ duration: 0.15 }}
                className="fixed max-h-80 overflow-y-auto custom-scrollbar bg-background-dark border border-white/10 rounded-xl shadow-2xl z-[9999]"
                style={{
                    top: menuPosition.top + 8, // slight offset for breathing room
                    left: menuPosition.left,
                    width: menuPosition.width,
                    minWidth: '200px'
                }}
                onMouseDown={(e) => e.stopPropagation()}
            >
                {contextItems.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-gray-500">No options available</div>
                ) : (
                    contextItems.map(item => (
                        <button
                            key={item.id}
                            onClick={() => handleSelect(item.id)}
                            className="w-full text-left flex items-center gap-3 px-4 py-3 text-sm hover:bg-white/5 text-gray-200 transition-colors border-b border-white/5 last:border-0"
                            type="button"
                        >
                            {item.icon}
                            <span className="truncate">{item.label}</span>
                        </button>
                    ))
                )}
            </motion.div>,
            document.body
        )}
        </AnimatePresence>
    </>
  );
};

export default GlobalContextSwitcher;