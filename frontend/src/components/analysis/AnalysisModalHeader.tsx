// FILE: src/components/analysis/AnalysisModalHeader.tsx
import React from 'react';
import { Swords, Shield, ZoomIn, ZoomOut, Minimize2, Maximize2, Minus, X } from 'lucide-react';
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
      <div className="p-3 sm:p-5 border-b border-main flex justify-between items-center bg-surface shrink-0 gap-2 sm:gap-4">
        <div className="flex items-center gap-2 sm:gap-3.5 min-w-0">
          <div className="flex flex-col gap-0.5 sm:gap-1 min-w-0">
            <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
              <span className="text-sm sm:text-lg font-black text-text-primary uppercase tracking-wider truncate">
                {t('analysis.title', 'Analiza e Rastit')}
              </span>

              <span className="px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-lg bg-primary-start/10 text-primary-start border border-primary-start/30 text-[9px] sm:text-[10px] font-black uppercase tracking-widest flex items-center gap-1 shadow-sm shrink-0">
                {clientPosition === 'PLAINTIFF' ? <Swords size={11} /> : <Shield size={11} />}
                <span>{clientPosition === 'PLAINTIFF' ? 'Roli: Paditës' : 'Roli: I Paditur'}</span>
              </span>
            </div>

            <div className="hidden sm:flex items-center mt-1 gap-2.5">
              <RenderRiskBadge level={riskLevel} t={t} />
              <RenderSuccessBadge prob={successProbability} t={t} />
            </div>
          </div>
        </div>

        {/* Action Controls Header Bar with Minimize Icon right next to Close X */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          <button
            type="button"
            onClick={onToggleZoom}
            className="p-1.5 sm:p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-all focus:outline-none"
            title={
              zoomLevel === 'normal'
                ? t('analysis.zoomIn', 'Zmadho tekstin')
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
            className="p-1.5 sm:p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-all focus:outline-none"
            title={isFullScreen ? 'Zvogëlo ekranin' : 'Zmadho në ekran të plotë'}
          >
            {isFullScreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 sm:p-2 text-text-secondary hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 focus:outline-none"
            title="Zvogëlo dritaren"
          >
            <Minus size={18} />
          </button>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 sm:p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-all shrink-0 focus:outline-none"
            aria-label="Close modal"
            title="Mbyll"
          >
            <X size={20} />
          </button>
        </div>
      </div>

      <div className="sm:hidden px-3.5 py-2 bg-surface/80 border-b border-main flex items-center justify-between gap-2 overflow-x-auto no-scrollbar">
        <RenderRiskBadge level={riskLevel} t={t} />
        <RenderSuccessBadge prob={successProbability} t={t} />
      </div>
    </>
  );
};