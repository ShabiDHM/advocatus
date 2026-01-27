// FILE: src/components/evidence-map/Sidebar.tsx
// PHOENIX PROTOCOL - PHASE 6: AI INTEGRATION TRIGGER
// 1. FEAT: Added an "Import from AI" button to the sidebar.
// 2. LOGIC: The button's onClick handler is passed up to the parent page.

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Filter, Search, XCircle, BrainCircuit } from 'lucide-react';

export interface IFilters {
  hideUnconnected: boolean;
  highlightContradictions: boolean;
}

interface SidebarProps {
  filters: IFilters;
  onFilterChange: <K extends keyof IFilters>(key: K, value: IFilters[K]) => void;
  searchTerm: string;
  onSearchChange: (term: string) => void;
  onOpenImportModal: () => void; // New prop for Phase 6
}

const Sidebar: React.FC<SidebarProps> = ({
  filters,
  onFilterChange,
  searchTerm,
  onSearchChange,
  onOpenImportModal, // New prop
}) => {
  const { t } = useTranslation();

  return (
    <div className="w-64 h-full bg-background-light/80 backdrop-blur-md p-4 border-l border-white/10 flex flex-col gap-6">
      {/* AI Import Section */}
      <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-text-primary mb-3">
              <BrainCircuit size={16} className="text-primary-start" />
              <span>{t('evidenceMap.sidebar.aiTitle', 'Ndihmës i AI')}</span>
          </h3>
          <button 
            onClick={onOpenImportModal}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start rounded-md text-sm transition-colors"
          >
            {t('evidenceMap.sidebar.importButton', 'Importo Entitetet')}
          </button>
      </div>

      {/* Search Section */}
      <div>
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
      <div>
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