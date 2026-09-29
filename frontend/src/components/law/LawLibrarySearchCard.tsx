// FILE: src/components/law/LawLibrarySearchCard.tsx
// PHOENIX PROTOCOL - LAW LIBRARY SEARCH CARD V2.0
//
// V2.0: Shtuar warning për ligje të shfuqizuara në dropdown.
//   - T42: Shfaqet ⚠️ për ligje të shfuqizuara
//   - Tipizim i pastër (pa any)

import React from 'react';
import { Filter, ChevronDown, X, Search, Loader2, AlertTriangle } from 'lucide-react';

interface LawLibrarySearchCardProps {
  selectedLaw: string;
  onSelectedLawChange: (val: string) => void;
  availableLaws: string[];
  repealedTitles?: Set<string>;
  query: string;
  onQueryChange: (val: string) => void;
  onSearch: () => void;
  loading: boolean;
  isAuthenticated: boolean;
}

export const LawLibrarySearchCard: React.FC<LawLibrarySearchCardProps> = ({
  selectedLaw,
  onSelectedLawChange,
  availableLaws,
  repealedTitles,
  query,
  onQueryChange,
  onSearch,
  loading,
  isAuthenticated,
}) => {
  const isSelectedRepealed = !!(selectedLaw && repealedTitles?.has(selectedLaw));

  return (
    <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-main bg-surface shadow-sm mb-10">
      <div className="flex flex-col gap-4">
        {/* Law Selector */}
        <div className="relative flex items-center">
          <Filter size={18} className="absolute left-4 text-primary-start pointer-events-none z-10" />

          <select
            value={selectedLaw}
            onChange={(e) => onSelectedLawChange(e.target.value)}
            disabled={!isAuthenticated}
            className="w-full pl-12 pr-12 py-4 bg-canvas border border-main hover:border-primary-start/60 rounded-2xl shadow-sm text-xs sm:text-sm font-bold text-text-primary focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 appearance-none cursor-pointer transition-all disabled:opacity-50"
          >
            <option value="" className="bg-surface text-text-primary font-bold py-2">
              Zgjidh një ligj (Të gjitha ligjet)
            </option>
            {availableLaws.map((lawName, idx) => {
              const isRepealed = repealedTitles?.has(lawName);
              return (
                <option
                  key={idx}
                  value={lawName}
                  className={`bg-surface py-2 font-medium ${isRepealed ? 'text-warning-start' : 'text-text-primary'}`}
                >
                  {isRepealed ? '⚠️ ' : ''}{lawName}
                </option>
              );
            })}
          </select>

          <div className="absolute right-4 flex items-center gap-2 pointer-events-none z-10">
            {selectedLaw && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectedLawChange('');
                }}
                className="pointer-events-auto p-1 hover:bg-hover rounded-lg text-text-muted hover:text-danger-start transition-colors"
                title="Hiq filtrin"
              >
                <X size={16} />
              </button>
            )}
            <ChevronDown size={18} className="text-text-muted" />
          </div>
        </div>

        {/* Warning për ligj të zgjedhur shfuqizuar */}
        {isSelectedRepealed && (
          <div className="flex items-start gap-2 bg-warning-start/10 border border-warning-start/30 rounded-xl p-3 text-xs">
            <AlertTriangle size={14} className="text-warning-start shrink-0 mt-0.5" />
            <p className="text-warning-start font-bold">
              ⚠️ Ligji i zgjedhur është i shfuqizuar. Rezultatet mund të mos jenë të vlefshme.
            </p>
          </div>
        )}

        {/* Search Bar */}
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
            <Search
              className={`h-5 w-5 transition-colors ${
                loading
                  ? 'text-primary-start animate-pulse'
                  : 'text-primary-start/60 group-focus-within:text-primary-start'
              }`}
            />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onSearch()}
            placeholder="Kërko nene, fjalë kyçe, koncepte juridike..."
            disabled={!isAuthenticated}
            className="w-full pl-13 pr-36 py-4 bg-canvas border border-main rounded-2xl shadow-sm text-sm sm:text-base text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <div className="absolute inset-y-0 right-2.5 flex items-center">
            <button
              type="button"
              onClick={onSearch}
              disabled={loading || !isAuthenticated || !query.trim()}
              className="h-10 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider disabled:opacity-30 transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : 'KËRKO'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LawLibrarySearchCard;