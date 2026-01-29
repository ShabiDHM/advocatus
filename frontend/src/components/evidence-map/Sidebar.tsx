// FILE: frontend/src/components/evidence-map/Sidebar.tsx
// PHOENIX PROTOCOL - FIX V11.2 (SIDEBAR POLISH)
// 1. UI: Synced the AI Import button style to match the global application style (Gradient + Bold).
// 2. UI: Refined padding and text contrast for dark mode.

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
  onOpenImportModal,
  onClose,
}) => {
  const { t } = useTranslation();

  return (
    <div className="h-full w-full flex flex-col gap-6 bg-gray-900 md:bg-background-light/90 md:backdrop-blur-md p-5 border-l border-white/10 shadow-2xl">
      
      {/* Header */}
      <div className="flex justify-between items-center pb-3 border-b border-white/10 flex-shrink-0">
          <h3 className="flex items-center gap-2 text-lg font-bold text-white">
             <BrainCircuit size={18} className="text-primary-start" />
             {t('evidenceMap.sidebar.aiTitle', 'Ndihmës i AI')}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors md:hidden">
              <X size={24} />
          </button>
      </div>
      
      {/* PHOENIX FIX: Upgraded button to match the primary gradient style */}
      <div className="flex-shrink-0">
          <button 
            onClick={onOpenImportModal}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white rounded-xl text-sm transition-all shadow-lg active:scale-95 font-bold"
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
            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-text-main focus:ring-2 focus:ring-primary-start focus:outline-none transition-all"
          />
          {searchTerm && (
            <button onClick={() => onSearchChange('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-white transition-colors">
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
        <div className="space-y-3 bg-black/30 p-4 rounded-xl border border-white/5">
          <label className="flex items-center justify-between text-sm text-text-secondary cursor-pointer hover:text-white transition-colors">
            <span>{t('evidenceMap.sidebar.hideUnconnected', 'Fshih Provat e Palidhura')}</span>
            <input
              type="checkbox"
              checked={filters.hideUnconnected}
              onChange={(e) => onFilterChange('hideUnconnected', e.target.checked)}
              className="h-5 w-5 rounded bg-background-dark border-white/20 text-primary-start focus:ring-primary-start transition-all"
            />
          </label>
          <div className="h-px bg-white/5 my-2"></div>
          <label className="flex items-center justify-between text-sm text-text-secondary cursor-pointer hover:text-white transition-colors">
            <span>{t('evidenceMap.sidebar.highlightContradictions', 'Thekso Kundërthëniet')}</span>
            <input
              type="checkbox"
              checked={filters.highlightContradictions}
              onChange={(e) => onFilterChange('highlightContradictions', e.target.checked)}
              className="h-5 w-5 rounded bg-background-dark border-white/20 text-primary-start focus:ring-primary-start transition-all"
            />
          </label>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;