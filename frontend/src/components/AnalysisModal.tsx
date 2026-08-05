// FILE: src/components/AnalysisModal.tsx
// PHOENIX PROTOCOL - ANALYSIS MODAL V32.0 (DECOUPLED & MODULARIZED ATOMIC ARCHITECTURE)

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale, Swords, CheckCircle2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CaseAnalysisResult, DeepAnalysisResult } from '../data/types';
import { apiService } from '../services/api';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

import { SpinnerStyles } from './analysis/AnalysisBadges';
import { AnalysisModalHeader } from './analysis/AnalysisModalHeader';
import { LegalAnalysisTab } from './analysis/LegalAnalysisTab';
import { WarRoomTab } from './analysis/WarRoomTab';

export interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: CaseAnalysisResult;
  caseId: string;
  isLoading?: boolean;
}

type ZoomLevel = 'normal' | 'large' | 'xlarge';

const AnalysisModal: React.FC<AnalysisModalProps> = ({ isOpen, onClose, result, caseId, isLoading = false }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<'legal' | 'war_room'>('legal');
  const [zoomLevel, setZoomLevel] = useState<ZoomLevel>('normal');
  const [isFullScreen, setIsFullScreen] = useState(false);

  const clientPosition = ((result as any)?.client_position || 'DEFENDANT').toUpperCase();

  const [deepResult, setDeepResult] = useState<DeepAnalysisResult | null>(null);
  const [isSimLoading, setIsSimLoading] = useState(false);
  const [isChronLoading, setIsChronLoading] = useState(false);
  const [isContradictLoading, setIsContradictLoading] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);

  useLockBodyScroll(isOpen);

  useEffect(() => {
    if (isOpen) {
      setActiveTab('legal');
      const existingDeep =
        (result as any)?.latest_deep_analysis || (result as any)?.deep_analysis || (result as any)?.deep_result;
      if (existingDeep && (existingDeep.adversarial_simulation || existingDeep.chronology || existingDeep.contradictions)) {
        setDeepResult(existingDeep);
      }
    }
  }, [isOpen, result]);

  const handleWarRoomEntry = async () => {
    setActiveTab('war_room');

    const existingDeep =
      deepResult || (result as any)?.latest_deep_analysis || (result as any)?.deep_analysis || (result as any)?.deep_result;

    if (existingDeep && (existingDeep.adversarial_simulation || existingDeep.chronology || existingDeep.contradictions)) {
      if (!deepResult) setDeepResult(existingDeep);
      return;
    }

    if (!deepResult && !isSimLoading && !isChronLoading && !isContradictLoading) {
      setIsSimLoading(true);
      setIsChronLoading(true);
      setIsContradictLoading(true);

      apiService
        .analyzeDeepChronology(caseId)
        .then((data) => {
          setDeepResult((prev) => ({
            ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }),
            chronology: data,
          }));
          setIsChronLoading(false);
        })
        .catch(() => setIsChronLoading(false));

      apiService
        .analyzeDeepSimulation(caseId, clientPosition as any)
        .then((data) => {
          setDeepResult((prev) => ({
            ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }),
            adversarial_simulation: data,
          }));
          setIsSimLoading(false);
        })
        .catch(() => setIsSimLoading(false));

      apiService
        .analyzeDeepContradictions(caseId)
        .then((data) => {
          setDeepResult((prev) => ({
            ...(prev || { adversarial_simulation: { opponent_strategy: '', weakness_attacks: [], counter_claims: [] }, chronology: [], contradictions: [] }),
            contradictions: data,
          }));
          setIsContradictLoading(false);
        })
        .catch(() => setIsContradictLoading(false));
    }
  };

  const handleArchiveStrategy = async () => {
    if (!deepResult || isArchiving) return;
    setIsArchiving(true);
    try {
      await apiService.archiveStrategyReport(caseId, result, deepResult);
      alert(t('analysis.archive_success', 'Strategjia u ruajt me sukses në dosjen e rastit në Arkiv!'));
    } catch {
      alert(t('analysis.archive_error', 'Dështoi ruajtja në arkiv.'));
    } finally {
      setIsArchiving(false);
    }
  };

  const toggleZoom = () => {
    setZoomLevel((prev) => (prev === 'normal' ? 'large' : prev === 'large' ? 'xlarge' : 'normal'));
  };

  const getFontSize = () => {
    switch (zoomLevel) {
      case 'large':
        return '1rem';
      case 'xlarge':
        return '1.125rem';
      default:
        return '0.9375rem';
    }
  };

  const {
    summary = result?.summary || (result as any)?.executive_summary || (result as any)?.citizen_summary || (result as any)?.citizenText || '',
    key_issues = [],
    legal_basis = [],
    strategic_analysis = '',
    weaknesses = [],
    action_plan = [],
    risk_level = 'MEDIUM',
    success_probability = null,
    burden_of_proof = '',
    missing_evidence = [],
  } = result || {};

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[200] p-2 sm:p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.98, opacity: 0, y: 10 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.98, opacity: 0, y: 10 }}
          transition={{ duration: 0.2 }}
          className={`glass-panel w-[95vw] rounded-3xl shadow-2xl border border-main bg-canvas flex flex-col overflow-hidden transition-all duration-300 ${
            isFullScreen ? 'w-full h-full max-w-none rounded-none' : 'max-w-7xl h-[92vh]'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <SpinnerStyles />

          <AnalysisModalHeader
            clientPosition={clientPosition}
            riskLevel={risk_level}
            successProbability={success_probability}
            zoomLevel={zoomLevel}
            onToggleZoom={toggleZoom}
            isFullScreen={isFullScreen}
            onToggleFullScreen={() => setIsFullScreen(!isFullScreen)}
            onClose={onClose}
            t={t}
          />

          {!isLoading && (
            <>
              <div className="flex border-b border-main px-6 bg-canvas shrink-0 overflow-x-auto no-scrollbar gap-6">
                <button
                  type="button"
                  onClick={() => setActiveTab('legal')}
                  className={`py-3 text-[11px] font-black uppercase tracking-widest flex items-center gap-2 border-b-2 transition-all whitespace-nowrap focus:outline-none ${
                    activeTab === 'legal' ? 'border-primary-start text-primary-start' : 'border-transparent text-text-secondary hover:text-text-primary'
                  }`}
                >
                  <Scale size={15} /> {t('analysis.tab_legal', 'Analiza Ligjore')}
                </button>
                <button
                  type="button"
                  onClick={handleWarRoomEntry}
                  className={`py-3 text-[11px] font-black uppercase tracking-widest flex items-center gap-2 border-b-2 transition-all whitespace-nowrap focus:outline-none ${
                    activeTab === 'war_room' ? 'border-primary-start text-primary-start' : 'border-transparent text-text-secondary hover:text-primary-start'
                  }`}
                >
                  <Swords size={15} /> {t('analysis.tab_war_room', 'Dhoma e Luftës')}
                </button>
              </div>

              <div
                className="flex-1 overflow-y-auto p-4 sm:p-8 custom-finance-scroll text-text-primary bg-canvas"
                style={{ fontSize: getFontSize() }}
              >
                <div className={`mx-auto space-y-6 transition-all duration-300 ${isFullScreen ? 'max-w-none px-4 sm:px-12' : 'max-w-6xl'}`}>
                  {activeTab === 'legal' && (
                    <LegalAnalysisTab
                      summary={summary}
                      burden_of_proof={burden_of_proof}
                      missing_evidence={missing_evidence}
                      key_issues={key_issues}
                      legal_basis={legal_basis}
                      t={t}
                    />
                  )}

                  {activeTab === 'war_room' && (
                    <WarRoomTab
                      deepResult={deepResult}
                      strategicAnalysis={strategic_analysis}
                      weaknesses={weaknesses}
                      actionPlan={action_plan}
                      isSimLoading={isSimLoading}
                      isChronLoading={isChronLoading}
                      isContradictLoading={isContradictLoading}
                      t={t}
                    />
                  )}
                </div>
              </div>
            </>
          )}

          <div className="p-3.5 sm:p-4 border-t border-main bg-surface flex flex-col sm:flex-row gap-3 justify-between items-center shrink-0">
            <button
              type="button"
              onClick={handleArchiveStrategy}
              disabled={isArchiving || !deepResult}
              className={`w-full sm:w-auto h-10 px-5 rounded-xl text-xs uppercase tracking-wider font-bold transition-all flex items-center justify-center gap-2 border focus:outline-none ${
                isArchiving || !deepResult
                  ? 'bg-canvas text-text-disabled border-main cursor-not-allowed'
                  : 'bg-status-success/15 text-status-success border-status-success/20 hover:bg-status-success/20 active:scale-95'
              }`}
            >
              {isArchiving ? (
                <div className="w-4 h-4 border-2 border-status-success border-t-transparent rounded-full spinner-robust" />
              ) : (
                <CheckCircle2 size={15} />
              )}
              {t('analysis.btn_archive', 'Ruaj Strategjinë në Arkiv')}
            </button>

            <button
              type="button"
              onClick={onClose}
              className="h-10 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider shadow-md shadow-primary-start/15 transition-all w-full sm:w-auto"
            >
              {t('general.close', 'Përfundo Analizën')}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default AnalysisModal;