// FILE: src/components/graph/GraphToolbar.tsx
// PHOENIX PROTOCOL - GRAPH TOOLBAR V80.0 (LIGHT & DARK DUAL-THEME HIGH CONTRAST)

import React from 'react';
import { Search, RefreshCw, Sparkles, Filter, LayoutGrid, Clock, Network, X } from 'lucide-react';
import { EntityType, ENTITY_CONFIG, OntologyNode } from './graphTypes';

interface GraphToolbarProps {
  simplifiedView: boolean;
  onToggleSimplified: () => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  activeFilter: string;
  onFilterChange: (filter: string) => void;
  nodes: OntologyNode[];
  filteredCount: number;
  onExportCourtReport: () => void;
  exporting: boolean;
  onRebuildGraph: () => void;
  rebuilding: boolean;
  isMobile: boolean;
  mobileTab: 'entities' | 'timeline' | 'graph';
  onMobileTabChange: (tab: 'entities' | 'timeline' | 'graph') => void;
  timelineCount: number;
}

export const GraphToolbar: React.FC<GraphToolbarProps> = ({
  simplifiedView,
  onToggleSimplified,
  searchQuery,
  onSearchChange,
  activeFilter,
  onFilterChange,
  nodes,
  filteredCount,
  onExportCourtReport,
  exporting,
  onRebuildGraph,
  rebuilding,
  isMobile,
  mobileTab,
  onMobileTabChange,
  timelineCount,
}) => {
  return (
    <>
      <div className="flex items-center justify-between px-3 py-1.5 sm:px-4 sm:py-2 bg-surface border-b border-main gap-2 z-10 shrink-0">
        {/* Pjesa e Majtë: Pamja, Kërkimi dhe Filtri */}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Toggle Pamja e Thjeshtë / Plotë - DUAL THEME HIGH CONTRAST */}
          <button
            type="button"
            onClick={onToggleSimplified}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-black uppercase border transition-all shrink-0 shadow-sm ${
              simplifiedView
                ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-950 dark:text-amber-300 border-amber-400 dark:border-amber-500/40 font-black'
                : 'bg-canvas text-text-primary border-main hover:bg-surface'
            }`}
          >
            <Sparkles 
              size={13} 
              className={simplifiedView ? 'text-amber-700 dark:text-amber-400 animate-pulse' : 'text-text-muted'} 
            />
            <span>{simplifiedView ? 'Provat Kryesore' : 'Pamja e Plotë'}</span>
          </button>

          {/* Fusha e Kërkimit */}
          <div className="relative flex-1 max-w-xs min-w-[140px]">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-text-muted" />
            <input
              type="text"
              placeholder="Kërko entitetin..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full bg-canvas border border-main rounded-lg pl-8 pr-7 py-1 text-xs text-text-primary placeholder:text-text-muted font-medium focus:outline-none focus:ring-1 focus:ring-primary-start transition-all"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => onSearchChange('')}
                className="absolute right-2 top-2 text-text-muted hover:text-text-primary"
              >
                <X size={12} />
              </button>
            )}
          </div>

          {/* Filtri i Entiteteve */}
          <div className="hidden md:flex items-center gap-1.5 bg-canvas px-2.5 py-1 rounded-lg border border-main text-xs font-bold shrink-0">
            <Filter size={11} className="text-primary-start" />
            <select
              value={activeFilter}
              onChange={(e) => onFilterChange(e.target.value)}
              className="bg-canvas text-text-primary focus:outline-none cursor-pointer uppercase font-bold text-[11px]"
            >
              <option value="ALL" className="bg-surface text-text-primary">
                Gjithë Entitetet ({filteredCount})
              </option>
              {(Object.keys(ENTITY_CONFIG) as EntityType[]).map((type) => {
                const count = nodes.filter((n) => n.type === type).length || 0;
                if (count === 0) return null;
                return (
                  <option key={type} value={type} className="bg-surface text-text-primary font-bold">
                    {ENTITY_CONFIG[type].albanianLabel} ({count})
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        {/* Pjesa e Djathtë: Ruaj dhe Ri-sinkronizo */}
        <div className="flex items-center justify-end gap-1.5 shrink-0">
          <button
            type="button"
            onClick={onExportCourtReport}
            disabled={exporting}
            className="px-3.5 py-1 bg-primary-start hover:bg-primary-start/90 text-white rounded-lg text-xs font-black uppercase tracking-wider shadow-sm transition-all focus:outline-none disabled:opacity-50 flex items-center gap-1"
          >
            {exporting ? 'Duke ruajtur...' : 'Ruaj'}
          </button>

          <button
            type="button"
            onClick={onRebuildGraph}
            disabled={rebuilding}
            className="p-1.5 bg-canvas hover:bg-surface border border-main text-text-primary rounded-lg transition-all focus:outline-none"
            title="Ri-kalkulo dhe Rindërto Ontologjinë"
            aria-label="Ri-kalkulo dhe Rindërto Ontologjinë"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin text-primary-start' : 'text-text-primary'}`} />
          </button>
        </div>
      </div>

      {/* Navigimi në Mobile */}
      {isMobile && (
        <div className="flex items-center justify-around bg-surface border-b border-main p-1 gap-1 shrink-0">
          <button
            type="button"
            onClick={() => onMobileTabChange('entities')}
            className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-[11px] font-bold uppercase ${
              mobileTab === 'entities' ? 'bg-primary-start text-white shadow' : 'text-text-muted'
            }`}
          >
            <LayoutGrid size={13} /> <span>Entitetet ({filteredCount})</span>
          </button>
          <button
            type="button"
            onClick={() => onMobileTabChange('timeline')}
            className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-[11px] font-bold uppercase ${
              mobileTab === 'timeline' ? 'bg-primary-start text-white shadow' : 'text-text-muted'
            }`}
          >
            <Clock size={13} /> <span>Kronologjia ({timelineCount})</span>
          </button>
          <button
            type="button"
            onClick={() => onMobileTabChange('graph')}
            className={`flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg text-[11px] font-bold uppercase ${
              mobileTab === 'graph' ? 'bg-primary-start text-white shadow' : 'text-text-muted'
            }`}
          >
            <Network size={13} /> <span>Grafiku</span>
          </button>
        </div>
      )}
    </>
  );
};

export default GraphToolbar;