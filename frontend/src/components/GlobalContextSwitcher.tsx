// FILE: src/components/GlobalContextSwitcher.tsx
// PHOENIX PROTOCOL - COMPONENT V2.0 (FLEXBOX FIX)
// 1. FIX: Added 'min-w-0' to the inner flex container.
// 2. LOGIC: Allows the inner span to truncate correctly when the parent shrinks.

import React, { useState, useRef, useEffect, ReactNode } from 'react';
import { ChevronDown, Briefcase, FileText, Check } from 'lucide-react';
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
  const wrapperRef = useRef<HTMLDivElement>(null);

  const contextItems: ContextItem[] = [
    { id: 'general', label: 'E Gjithë Dosja', icon: <Briefcase size={16} className="text-amber-400" /> },
    ...documents.map(doc => ({
      id: doc.id,
      label: doc.file_name,
      icon: <FileText size={16} className="text-blue-400" />,
    })),
  ];

  const selectedItem = contextItems.find(item => item.id === activeContextId) || contextItems[0];

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && wrapperRef.current.contains(event.target as Node)) {
          return;
      }
      setIsOpen(false);
    };
    
    if (isOpen) {
        document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleSelect = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    onContextChange(id);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`} ref={wrapperRef}>
        {/* Trigger Button */}
        <button
            onClick={() => setIsOpen(!isOpen)}
            className="relative z-20 flex items-center w-full h-full justify-between gap-3 px-4 py-2 rounded-xl bg-black/20 hover:bg-black/40 border border-white/10 text-gray-200 text-sm font-medium transition-all"
            type="button"
        >
            {/* PHOENIX FIX: Added 'min-w-0' to this container */}
            <div className="flex items-center gap-3 min-w-0">
                {selectedItem.icon}
                <span className="truncate">{selectedItem.label}</span>
            </div>
            <ChevronDown size={16} className={`transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Dropdown Menu - Positioned Absolutely relative to the parent div */}
        {isOpen && (
            <div 
                className="absolute top-full left-0 mt-2 w-full min-w-[240px] max-h-80 overflow-y-auto custom-scrollbar bg-gray-900 border border-white/20 rounded-xl shadow-2xl z-50 origin-top-left"
            >
                <div className="py-1">
                    {contextItems.length === 0 ? (
                        <div className="px-4 py-3 text-sm text-gray-500">No options available</div>
                    ) : (
                        contextItems.map(item => {
                            const isActive = item.id === activeContextId;
                            return (
                                <button
                                    key={item.id}
                                    onClick={(e) => handleSelect(e, item.id)}
                                    className={`w-full text-left flex items-center gap-3 px-4 py-3 text-sm transition-colors border-b border-white/5 last:border-0 ${isActive ? 'bg-white/10 text-white' : 'text-gray-300 hover:bg-white/5'}`}
                                    type="button"
                                >
                                    {item.icon}
                                    <span className="truncate flex-1">{item.label}</span>
                                    {isActive && <Check size={14} className="text-green-400" />}
                                </button>
                            );
                        })
                    )}
                </div>
            </div>
        )}
    </div>
  );
};

export default GlobalContextSwitcher;