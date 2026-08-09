// FILE: src/components/graph/GraphToolbar.tsx
// PHOENIX PROTOCOL - GRAPH TOOLBAR V66.0 (THEME AWARE, RUAJ PILL, CIRCLE REFRESH ICON)

import React from 'react';
import { Search, RefreshCw, Sparkles, Filter, LayoutGrid, Clock, Network } from 'lucide-react';
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
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between px-4 py-2.5 bg-surface border-b border-main gap-3 z-10 shrink-0">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            type="button"
            onClick={onToggleSimplified}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-black uppercase border transition-all shadow-sm ${
              simplifiedView
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                : 'bg-canvas text-text-secondary border-main hover:text-text-primary'
            }`}
          >
            <Sparkles size={14} className={simplifiedView ? 'text-amber-400 animate-pulse' : ''} />
            <span>{simplifiedView ? '⚡ Provat Kryesore' : '🌐 Pamja e Plotë'}</span>
          </button>

          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-text-muted" />
            <input
              type="text"
              placeholder="Kërko entitetin ose fjalën kyçe..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full bg-canvas border border-main rounded-xl pl-9 pr-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-start"
            />
          </div>

          <div className="hidden md:flex items-center gap-2 bg-canvas px-3 py-1.5 rounded-xl border border-main text-xs font-bold shrink-0 shadow-sm">
            <Filter size={13} className="text-primary-start" />
            <select
              value={activeFilter}
              onChange={(e) => onFilterChange(e.target.value)}
              className="bg-canvas text-text-primary focus:outline-none cursor-pointer uppercase font-bold text-xs"
            >
              <option value="ALL" className="bg-surface text-text-primary">
                Gjithë Entitetet ({filteredCount})
              </option>
              {(Object.keys(ENTITY_CONFIG) as EntityType[]).map((type) => {
                const count = nodes.filter((n) => n.type === type).length || 0;
                if (count === 0) return null;
                return (
                  <option key={type} value={type} className="bg-surface text-text-primary">
                    {ENTITY_CONFIG[type].albanianLabel} ({count})
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 shrink-0">
          {/* Ruaj Pill Button */}
          <button
            type="button"
            onClick={onExportCourtReport}
            disabled={exporting}
            className="px-4 py-1.5 bg-primary-start hover:bg-primary-start/90 text-white rounded-full text-xs font-black uppercase tracking-wider shadow-sm transition-all focus:outline-none disabled:opacity-50"
          >
            {exporting ? '...' : 'Ruaj'}
          </button>

          {/* Circle Refresh Icon Only */}
          <button
            type="button"
            onClick={onRebuildGraph}
            disabled={rebuilding}
            className="p-2 bg-surface hover:bg-hover border border-main text-text-primary rounded-full transition-all focus:outline-none"
            title="Rirregullo Grafikun"
            aria-label="Rirregullo Grafikun"
          >
            <RefreshCw className={`w-4 h-4 ${rebuilding ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {isMobile && (
        <div className="flex items-center justify-around bg-surface border-b border-main p-1.5 gap-1 shrink-0">
          <button
            type="button"
            onClick={() => onMobileTabChange('entities')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold uppercase ${
              mobileTab === 'entities' ? 'bg-primary-start text-white shadow' : 'text-text-muted'
            }`}
          >
            <LayoutGrid size={15} /> <span>👥 Entitetet ({filteredCount})</span>
          </button>
          <button
            type="button"
            onClick={() => onMobileTabChange('timeline')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold uppercase ${
              mobileTab === 'timeline' ? 'bg-primary-start text-white shadow' : 'text-text-muted'
            }`}
          >
            <Clock size={15} /> <span>🕒 Kronologjia ({timelineCount})</span>
          </button>
          <button
            type="button"
            onClick={() => onMobileTabChange('graph')}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold uppercase ${
              mobileTab === 'graph' ? 'bg-primary-start text-white shadow' : 'text-text-muted'
            }`}
          >
            <Network size={15} /> <span>🗺️ Grafiku</span>
          </button>
        </div>
      )}
    </>
  );
};