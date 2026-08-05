// FILE: src/components/analysis/AnalysisModalHeader.tsx
import React from 'react';
import { Gavel, Swords, Shield, ZoomIn, ZoomOut, Minimize2, Maximize2, X } from 'lucide-react';
import { TFunction } from 'i18next';
import { RenderRiskBadge, RenderSuccessBadge } from './AnalysisBadges';

interface AnalysisModalHeaderProps {
  clientPosition: string;
  riskLevel: string;
  successProbability: string | null;
  zoomLevel: 'normal' | 'large' | 'xlarge';
  onToggleZoom: () => void;
  isFullScreen: boolean;
  onToggleFullScreen: () => void;
  onClose: () => void;
  t: TFunction;
}

export const AnalysisModalHeader: React.FC<AnalysisModalHeaderProps> = ({
  clientPosition,
  riskLevel,
  successProbability,
  zoomLevel,
  onToggleZoom,
  isFullScreen,
  onToggleFullScreen,
  onClose,
  t,
}) => {
  return (
    <>
      <div className="p-4 sm:p-5 border-b border-main flex flex-wrap justify-between items-center bg-surface shrink-0 gap-4">
        <div className="flex items-center gap-4 min-w-0">
          <div className="w-10 h-10 bg-primary-start text-white rounded-xl flex items-center justify-center shadow-accent-glow shrink-0">
            <Gavel size={20} />
          </div>
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight truncate">
                {t('analysis.title', 'Strategjia Ligjore')}
              </span>

              <span className="px-2.5 py-0.5 rounded-md bg-primary-start/10 text-primary-start border border-primary-start/30 text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5">
                {clientPosition === 'PLAINTIFF' ? <Swords size={12} /> : <Shield size={12} />}
                <span>{clientPosition === 'PLAINTIFF' ? 'Roli: Paditës' : 'Roli: I Paditur'}</span>
              </span>
            </div>

            <div className="hidden sm:flex items-center mt-1 gap-2">
              <RenderRiskBadge level={riskLevel} t={t} />
              <RenderSuccessBadge prob={successProbability} t={t} />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onToggleZoom}
            className="p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-lg transition-all focus:outline-none"
            title={
              zoomLevel === 'normal'
                ? t('analysis.zoomIn', 'Agrandoni tekstin')
                : zoomLevel === 'large'
                ? t('analysis.zoomMore', 'Më i madh')
                : t('analysis.zoomOut', 'Teksti standard')
            }
          >
            {zoomLevel === 'normal' ? <ZoomIn size={18} /> : zoomLevel === 'large' ? <ZoomIn size={18} /> : <ZoomOut size={18} />}
          </button>

          <button
            type="button"
            onClick={onToggleFullScreen}
            className="p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-lg transition-all focus:outline-none"
            title={isFullScreen ? 'Zvogëlo' : 'Zmadho në Ekran të Plotë'}
          >
            {isFullScreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>

          <button
            type="button"
            onClick={onClose}
            className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 focus:outline-none"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      <div className="sm:hidden px-6 py-3 bg-surface border-b border-main flex flex-col sm:flex-row gap-2">
        <RenderRiskBadge level={riskLevel} t={t} />
        <RenderSuccessBadge prob={successProbability} t={t} />
      </div>
    </>
  );
};