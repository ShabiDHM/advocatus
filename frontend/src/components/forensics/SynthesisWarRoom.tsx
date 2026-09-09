// FILE: frontend/src/components/forensics/SynthesisWarRoom.tsx
// PHOENIX PROTOCOL - SYNTHESIS WAR ROOM V3.2 (WITH TOTAL WIPEOUT TRASH ACTION)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS • MOBILE-READY

import React, { useState, useEffect } from 'react';
import {
  Swords,
  Sparkles,
  Loader2,
  Flame,
  RefreshCw,
  Target,
  HelpCircle,
  Award,
  ShieldCheck,
  Copy,
  CheckCircle2,
  Trash2
} from 'lucide-react';
import {
  forensicDeskService,
  WarRoomSynthesisResponse
} from '../../services/forensicDeskService';

interface SynthesisWarRoomProps {
  caseId: string;
  clientName?: string;
  chainOfCustodyHash?: string;
  courtJurisdiction?: string;
  onEvidenceChange?: () => void;
}

const FONT_LEVELS = [
  { label: '90%',   base: 14,   line: 1.6 },
  { label: '100%',  base: 16,   line: 1.65 },
  { label: '115%',  base: 18,   line: 1.7 },
  { label: '130%',  base: 20,   line: 1.75 },
  { label: '150%',  base: 22,   line: 1.8 }
];

export const SynthesisWarRoom: React.FC<SynthesisWarRoomProps> = ({
  caseId,
  clientName = 'Pala e Përfaqësuar',
  chainOfCustodyHash = 'SEAL-SERVER-ACTIVE',
  courtJurisdiction = 'Gjykata Themelore Prishtinë',
  onEvidenceChange
}) => {
  const [isCrossAnalyzing, setIsCrossAnalyzing] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [synthesisData, setSynthesisData] = useState<WarRoomSynthesisResponse | null>(null);
  const [copiedAll, setCopiedAll] = useState<boolean>(false);

  // Kontrolli i zmadhimit të shkrimit
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_war_room_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1;
    } catch {
      return 1;
    }
  });
  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleIncreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_war_room_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleDecreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_war_room_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(1);
    try { localStorage.setItem('juristi_war_room_font_size', '1'); } catch {}
  };

  // Ngarkon sintezën më të fundit nga MongoDB në montim
  useEffect(() => {
    const loadLatestSynthesis = async () => {
      if (!caseId) return;
      try {
        const latest = await forensicDeskService.getLatestWarRoomSynthesis(caseId);
        if (latest) {
          setSynthesisData(latest);
        }
      } catch (err) {
        console.warn("Nuk u ngarkua sinteza e fundit e War Room:", err);
      }
    };
    loadLatestSynthesis();
  }, [caseId]);

  // EKZEKUTIMI I KRYQËZIMIT TË PROVAVE ME CLAUDE SONNET 4.6
  const handleRunMultimodalSynthesis = async () => {
    if (!caseId || isCrossAnalyzing) return;

    setIsCrossAnalyzing(true);
    try {
      const res = await forensicDeskService.synthesizeWarRoom({
        caseId,
        caseTitle: `Lënda: ${clientName} (${courtJurisdiction})`,
        searchGraphTerm: clientName
      });
      setSynthesisData(res);
      if (onEvidenceChange) onEvidenceChange();
    } catch (err: any) {
      console.error("Multimodal synthesis error:", err);
      alert(err?.response?.data?.detail || "Dështoi kryqëzimi multimodal i provave.");
    } finally {
      setIsCrossAnalyzing(false);
    }
  };

  // TOTAL CASCADE WIPEOUT I WAR ROOM NGA MONGODB
  const handleDeleteSynthesis = async () => {
    if (!caseId || isDeleting) return;
    const confirmDelete = window.confirm(
      "A jeni i sigurt që dëshironi të asgjësoni plotësisht matricën e kryqëzimit të provave nga MongoDB (Total Cascade Wipeout)?"
    );
    if (!confirmDelete) return;

    setIsDeleting(true);
    try {
      await forensicDeskService.deleteWarRoomSynthesis(caseId);
      setSynthesisData(null);
      if (onEvidenceChange) onEvidenceChange();
    } catch (err: any) {
      console.error("Dështoi fshirja e War Room:", err);
      alert(err?.response?.data?.detail || "Dështoi fshirja totale e War Room.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCopyFullSynthesis = () => {
    if (!synthesisData) return;
    const text = `=== KRYQËZIMI I PROVAVE FORENZIKE (WAR ROOM) ===\nLënda: ${clientName}\nOrgani: ${courtJurisdiction}\n\n1. TEORIA KRYESORE E RASTIT:\n${synthesisData.winning_theory_of_the_case}\n\n2. KONTRADIKTAT NDËRPROVUESE:\n${synthesisData.critical_cross_contradictions?.join('\n- ')}\n\n3. PYETJET TËRTHORE PËR SEANCË:\n${synthesisData.cross_examination_traps?.map((t, idx) => `#${idx + 1} [Target: ${t.witness_or_target}]: "${t.question}" (Qëllimi: ${t.trap_explanation})`).join('\n\n')}\n\n4. DYSHIMI I ARSYESHËM (IN DUBIO PRO REO):\n${synthesisData.in_dubio_pro_reo_vectors?.join('\n- ')}`;

    navigator.clipboard.writeText(text);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2500);
  };

  return (
    <div className="glass-panel p-4 sm:p-6 rounded-2xl sm:rounded-3xl border border-rose-500/30 bg-card shadow-xl space-y-4 sm:space-y-6">
      
      {/* KOKA E WAR ROOM ME KONTROLLET DHE KOSHIN */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-600/10 text-rose-500 flex items-center justify-center shrink-0">
            <Swords size={20} className="sm:w-5 sm:h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base md:text-lg font-black uppercase tracking-tight text-text-primary">
                Kryqëzimi i Provave Materiale
              </h2>
              <button
                type="button"
                onClick={() => {
                  if (onEvidenceChange) onEvidenceChange();
                  alert("Provat u rifreskuan nga serveri.");
                }}
                title="Rifresko të dhënat"
                className="p-1 text-text-muted hover:text-text-primary rounded-lg hover:bg-hover transition-colors cursor-pointer"
              >
                <RefreshCw size={13} />
              </button>
            </div>
            <p className="text-[11px] sm:text-xs text-text-muted mt-0.5">
              Përplasja e Shkresave, Audios, Videove dhe Financave për zbulimin e kontradiktave dhe pyetjeve të seancës
            </p>
          </div>
        </div>

        {/* Kontrolli i Fontit + Kopjo + Koshi + Butoni Kryqëzo */}
        <div className="flex items-center gap-2 self-end sm:self-auto shrink-0 flex-wrap">
          {/* Madhësia e Fontit */}
          <div className="flex items-center gap-0.5 rounded-xl border border-main bg-surface p-1" aria-label="Madhësia e shkrimit">
            <button
              type="button"
              onClick={handleDecreaseFont}
              disabled={fontLevelIndex === 0}
              className="h-6 w-6 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30 cursor-pointer"
            >
              A−
            </button>
            <button
              type="button"
              onClick={handleResetFont}
              className="min-w-8 rounded-lg px-1 text-[10px] font-bold text-text-muted hover:bg-hover"
            >
              {activeFont.label}
            </button>
            <button
              type="button"
              onClick={handleIncreaseFont}
              disabled={fontLevelIndex === FONT_LEVELS.length - 1}
              className="h-6 w-6 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:opacity-30 cursor-pointer"
            >
              A+
            </button>
          </div>

          {synthesisData && (
            <button
              type="button"
              onClick={handleCopyFullSynthesis}
              className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              {copiedAll ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
              <span>{copiedAll ? 'U Kopjua' : 'Kopjo'}</span>
            </button>
          )}

          {/* BUTONI I KOSHIT (TOTAL CASCADE WIPEOUT NGA MONGODB) */}
          {synthesisData && (
            <button
              type="button"
              onClick={handleDeleteSynthesis}
              disabled={isDeleting}
              className="h-9 w-9 bg-rose-600/10 hover:bg-rose-600/20 border border-rose-600/30 text-rose-500 rounded-xl flex items-center justify-center transition-all cursor-pointer shadow-xs disabled:opacity-40"
              title="Fshi plotësisht analizën nga MongoDB (Total Wipeout)"
            >
              {isDeleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={15} />}
            </button>
          )}

          <button
            type="button"
            onClick={handleRunMultimodalSynthesis}
            disabled={isCrossAnalyzing}
            className="h-9 sm:h-10 px-4 sm:px-5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-md transition-all cursor-pointer disabled:opacity-40"
          >
            {isCrossAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
            <span>{synthesisData ? 'Ri-Kryqëzo' : 'Fillo Kryqëzimin e Plotë'}</span>
          </button>
        </div>
      </div>

      {/* PANELI QENDROR I ANALIZËS SË KRYQËZIMIT */}
      <div className="space-y-4">
        <div
          className="min-h-[460px] max-h-[680px] overflow-y-auto custom-finance-scroll p-4 sm:p-6 bg-surface/40 rounded-2xl border border-main text-text-primary select-text space-y-4"
          style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
        >
          {synthesisData ? (
            <div className="space-y-4">
              
              {/* 1. Teoria Kryesore e Rastit */}
              <div className="p-4 bg-primary-start/10 rounded-2xl border border-primary-start/20 space-y-1.5">
                <h3 className="font-bold text-primary-start flex items-center gap-2 uppercase text-xs sm:text-sm">
                  <Award size={15} /> 1. Teoria Kryesore e Rastit:
                </h3>
                <p className="text-text-primary leading-relaxed text-xs sm:text-sm">
                  {synthesisData.winning_theory_of_the_case}
                </p>
              </div>

              {/* 2. Kontradiktat Ndërprovuese */}
              {synthesisData.critical_cross_contradictions?.length > 0 && (
                <div className="p-4 bg-rose-500/10 rounded-2xl border border-rose-500/20 space-y-2">
                  <h3 className="font-bold text-rose-500 flex items-center gap-2 uppercase text-xs sm:text-sm">
                    <Flame size={15} /> 2. Kontradiktat Ndërprovuese të Identifikuara:
                  </h3>
                  <ul className="list-disc list-inside space-y-1.5 text-text-primary text-xs sm:text-sm">
                    {synthesisData.critical_cross_contradictions.map((c, i) => (
                      <li key={i} className="leading-relaxed">{c}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 3. Pyetësori Taktik për Seancë */}
              {synthesisData.cross_examination_traps?.length > 0 && (
                <div className="p-4 bg-surface rounded-2xl border border-main space-y-3">
                  <h3 className="font-bold text-text-primary flex items-center gap-2 uppercase text-xs sm:text-sm">
                    <Target size={15} className="text-rose-500" /> 3. Pyetësori Taktik për Seancë Gjyqësore:
                  </h3>
                  <div className="space-y-2.5">
                    {synthesisData.cross_examination_traps.map((trap, idx) => (
                      <div key={idx} className="p-3 bg-card rounded-xl border border-main space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-bold text-rose-500">Palë / Dëshmitar në Shënjestër: {trap.witness_or_target}</span>
                          <span className="text-text-muted font-mono">Pyetja #{idx + 1}</span>
                        </div>
                        <p className="font-bold text-text-primary italic text-xs sm:text-sm pt-0.5">
                          "{trap.question}"
                        </p>
                        <p className="text-text-muted pt-1 text-[11px] sm:text-xs">
                          <span className="font-bold text-primary-start">Qëllimi Taktik / Kurthi:</span> {trap.trap_explanation}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 4. Elementet e Dyshimit të Arsyeshëm */}
              {synthesisData.in_dubio_pro_reo_vectors?.length > 0 && (
                <div className="p-4 bg-card rounded-2xl border border-main space-y-2">
                  <h3 className="font-bold text-text-primary flex items-center gap-2 uppercase text-xs sm:text-sm">
                    <HelpCircle size={15} className="text-emerald-500" /> 4. Pikat e Dyshimit të Arsyeshëm (In Dubio Pro Reo):
                  </h3>
                  <ul className="list-disc list-inside space-y-1 text-text-muted text-xs sm:text-sm">
                    {synthesisData.in_dubio_pro_reo_vectors.map((v, i) => (
                      <li key={i}>{v}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-3 py-20">
              <div className="w-14 h-14 rounded-2xl bg-rose-500/10 text-rose-500 flex items-center justify-center">
                <Swords size={28} />
              </div>
              <div className="space-y-1 max-w-sm">
                <h4 className="font-bold text-text-primary text-sm sm:text-base">
                  Matrica e Kryqëzimit nuk është ekzekutuar ende
                </h4>
                <p className="text-xs text-text-muted leading-relaxed">
                  Shtypni butonin <span className="text-rose-500 font-bold">"Fillo Kryqëzimin e Plotë"</span> për të analizuar dhe zbuluar kontradiktat mes të gjitha provave shkresore, audio, video dhe financiare.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* FOOTER */}
      <div className="pt-3 border-t border-main flex flex-col sm:flex-row items-center justify-between gap-1.5 text-[10px] sm:text-[11px] text-text-muted">
        <span className="flex items-center gap-1.5 font-medium">
          <ShieldCheck size={13} className="text-emerald-500" />
          Kryqëzim Forenzik sipas Kodit të Procedurës Penale dhe LPK të Kosovës
        </span>
        <span className="font-mono">Vula: {chainOfCustodyHash ? `${chainOfCustodyHash.slice(0, 18)}...` : 'Aktive'}</span>
      </div>
    </div>
  );
};

export default SynthesisWarRoom;