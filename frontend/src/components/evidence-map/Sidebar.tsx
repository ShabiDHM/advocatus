// FILE: frontend/src/components/evidence-map/Sidebar.tsx (COMPLETE REPLACEMENT)
// PHOENIX PROTOCOL - FIX V6.0.1 (MOBILE RESPONSIBLE SIDEBAR)
// 1. FIX: Implemented 'fixed' position and 'w-full sm:w-80 md:w-64' for responsive off-canvas behavior.
// 2. FEAT: Added mobile close button and required 'onClose' prop.

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Filter, Search, XCircle, BrainCircuit, X } from 'lucide-react'; // PHOENIX FIX: Added X icon

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
  onClose: () => void; // PHOENIX FIX: Added onClose handler for mobile
}

const Sidebar: React.FC<SidebarProps> = ({
  filters,
  onFilterChange,
  searchTerm,
  onSearchChange,
  onOpenImportModal,
  onClose, // Destructured
}) => {
  const { t } = useTranslation();

  return (
    // PHOENIX FIX: Added fixed positioning and responsive width/z-index for off-canvas effect
    <div className="fixed top-0 right-0 z-40 h-full w-full sm:w-80 md:w-64 bg-background-light/80 backdrop-blur-md p-4 border-l border-white/10 flex flex-col gap-6 shadow-2xl transition-transform duration-300 transform translate-x-0">
      
      {/* PHOENIX FIX: Mobile Header with Close Button */}
      <div className="flex justify-between items-center pb-3 border-b border-white/10 flex-shrink-0">
          <h3 className="flex items-center gap-2 text-lg font-bold text-white">
             <BrainCircuit size={18} className="text-primary-start" />
             {t('evidenceMap.sidebar.aiTitle', 'Ndihmës i AI')}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors md:hidden">
              <X size={24} />
          </button>
      </div>
      
      {/* AI Import Section */}
      <div className="flex-shrink-0">
          <button 
            onClick={onOpenImportModal}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start rounded-md text-sm transition-colors font-semibold"
          >
            {t('evidenceMap.sidebar.importButton', 'Importo Entitetet')}
          </button>
      </div>

      {/* Search Section */}
      <div className="flex-shrink-0">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-text-primary mb-3">
          <Search size={16} className="text-primary-start" />
          <span>{t('evidenceMap.sidebar.searchTitle', 'Gjej Kartelë')}</span>
        </h3>
        <div className="relative">
          <input
            type="text"
            placeholder={t('evidenceMap.sidebar.searchPlaceholder', 'Shkruaj titullin...')}
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full bg-background-dark border border-white/10 rounded-md px-3 py-1.5 text-sm text-text-main focus:ring-2 focus:ring-primary-start focus:outline-none"
          />
          {searchTerm && (
            <button onClick={() => onSearchChange('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-white">
              <XCircle size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Filter Section */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-text-primary mb-3">
          <Filter size={16} className="text-primary-start" />
          <span>{t('evidenceMap.sidebar.filterTitle', 'Filtro Pamjen')}</span>
        </h3>
        <div className="space-y-3">
          <label className="flex items-center justify-between text-sm text-text-secondary cursor-pointer">
            <span>{t('evidenceMap.sidebar.hideUnconnected', 'Fshih Provat e Palidhura')}</span>
            <input
              type="checkbox"
              checked={filters.hideUnconnected}
              onChange={(e) => onFilterChange('hideUnconnected', e.target.checked)}
              className="h-4 w-4 rounded bg-background-dark border-white/20 text-primary-start focus:ring-primary-start"
            />
          </label>
          <label className="flex items-center justify-between text-sm text-text-secondary cursor-pointer">
            <span>{t('evidenceMap.sidebar.highlightContradictions', 'Thekso Kundërthëniet')}</span>
            <input
              type="checkbox"
              checked={filters.highlightContradictions}
              onChange={(e) => onFilterChange('highlightContradictions', e.target.checked)}
              className="h-4 w-4 rounded bg-background-dark border-white/20 text-primary-start focus:ring-primary-start"
            />
          </label>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;