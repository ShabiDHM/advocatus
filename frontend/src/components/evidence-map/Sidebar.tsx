// FILE: frontend/src/components/evidence-map/Sidebar.tsx
// PHOENIX PROTOCOL - FIX V11.3 (MOBILE DRAWER INTEGRITY)
// 1. FIX: Changed width to 'w-80' and 'max-w-[85vw]' to prevent screen takeover.
// 2. UI: Added a solid dark background for mobile readability.

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Filter, Search, XCircle, BrainCircuit, X } from 'lucide-react';

export interface IFilters {
  hideUnconnected: boolean;
  highlightContradictions: boolean;
}

interface SidebarProps {
  filters: IFilters;
  onFilterChange: <K extends keyof IFilters>(key: K, value: IFilters[K]) => void;
  searchTerm: string;
  onSearchChange: (term: string) => void;
  onOpenImportModal: () => void;
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  filters,
  onFilterChange,
  searchTerm,
  onSearchChange,
  onClose,
}) => {
  const { t } = useTranslation();

  return (
    // PHOENIX FIX: Constrained width and added shadow for professional drawer look
    <div className="h-full w-80 max-w-[85vw] flex flex-col gap-6 bg-background-dark md:bg-background-light/95 md:backdrop-blur-md p-5 border-l border-white/10 shadow-[-10px_0_30px_rgba(0,0,0,0.5)]">
      
      {/* Header with Close Button */}
      <div className="flex justify-between items-center pb-4 border-b border-white/10 flex-shrink-0">
          <div className="flex items-center gap-2 text-primary-start">
             <BrainCircuit size={20} />
             <h3 className="text-lg font-bold text-white uppercase tracking-tight">KONTROLLI</h3>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
          >
              <X size={24} />
          </button>
      </div>
      
      {/* Search Section */}
      <div className="flex-shrink-0">
        <h3 className="flex items-center gap-2 text-xs font-black text-gray-500 uppercase tracking-widest mb-3">
          <Search size={14} />
          <span>{t('evidenceMap.sidebar.searchTitle', 'Gjej Kartelë')}</span>
        </h3>
        <div className="relative group">
          <input
            type="text"
            placeholder={t('evidenceMap.sidebar.searchPlaceholder', 'Kërko titullin...')}
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full bg-black/40 border border-white/10 rounded-xl pl-4 pr-10 py-3 text-sm text-text-main focus:ring-2 focus:ring-primary-start focus:outline-none transition-all group-hover:border-white/20"
          />
          {searchTerm && (
            <button onClick={() => onSearchChange('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-white transition-colors">
              <XCircle size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Filter Section */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <h3 className="flex items-center gap-2 text-xs font-black text-gray-500 uppercase tracking-widest mb-3">
          <Filter size={14} />
          <span>{t('evidenceMap.sidebar.filterTitle', 'Filtro Pamjen')}</span>
        </h3>
        <div className="space-y-2">
          <label className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 cursor-pointer hover:bg-white/10 transition-colors group">
            <span className="text-sm text-text-secondary group-hover:text-white transition-colors">Fshih të Palidhura</span>
            <input
              type="checkbox"
              checked={filters.hideUnconnected}
              onChange={(e) => onFilterChange('hideUnconnected', e.target.checked)}
              className="h-5 w-5 rounded bg-background-dark border-white/20 text-primary-start focus:ring-primary-start transition-all"
            />
          </label>
          <label className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 cursor-pointer hover:bg-white/10 transition-colors group">
            <span className="text-sm text-text-secondary group-hover:text-white transition-colors">Thekso Konfliktet</span>
            <input
              type="checkbox"
              checked={filters.highlightContradictions}
              onChange={(e) => onFilterChange('highlightContradictions', e.target.checked)}
              className="h-5 w-5 rounded bg-background-dark border-white/20 text-primary-start focus:ring-primary-start transition-all"
            />
          </label>
        </div>
      </div>

      {/* Sidebar Footer info */}
      <div className="mt-auto pt-4 border-t border-white/5 text-[10px] text-gray-600 text-center uppercase tracking-widest font-bold">
          Juristi AI v1.0 • Evidence Map
      </div>
    </div>
  );
};

export default Sidebar;