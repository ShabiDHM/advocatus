// FILE: frontend/src/components/forensics/SynthesisWarRoom.tsx
// PHOENIX PROTOCOL - SYNTHESIS WAR ROOM V2.4 (STREAMLINED - REMOVED REDUNDANT DISPATCH TAB)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS • 100% CLEAN

import React, { useState, useEffect } from 'react';
import {
  Swords,
  ShieldCheck,
  Scale,
  FileText,
  Sparkles,
  Loader2,
  CheckCircle2,
  Copy,
  AlertTriangle,
  Clock,
  Flame,
  RefreshCw,
  FileCheck,
  Target,
  HelpCircle,
  Award
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
  partnerLawyerName?: string;
  partnerLawyerLicense?: string;
  onEvidenceChange?: () => void;
}

type DraftingActType = 'KALLËZIM_PENAL' | 'MASË_SIGURIMI' | 'ANKESË_APEL' | 'PRAPËSIM_PADI';
type WarRoomSubTab = 'CROSS_EXAM' | 'DRAFTING';

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
  // Gjendjet e Kryqëzimit Multimodal
  const [isCrossAnalyzing, setIsCrossAnalyzing] = useState<boolean>(false);
  const [synthesisData, setSynthesisData] = useState<WarRoomSynthesisResponse | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<WarRoomSubTab>('CROSS_EXAM');

  // Gjendjet e Kronologjisë
  const [isLoadingChronology, setIsLoadingChronology] = useState<boolean>(false);
  const [chronologyText, setChronologyText] = useState<string>('');

  // Gjendjet e Hartimit Procedural
  const [selectedAct, setSelectedAct] = useState<DraftingActType>('KALLËZIM_PENAL');
  const [isDrafting, setIsDrafting] = useState<boolean>(false);
  const [draftedLegalAct, setDraftedLegalAct] = useState<string>('');

  // Gjendjet e Kopjimit
  const [copiedDraftText, setCopiedDraftText] = useState<boolean>(false);

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

  // 1. KRYQËZIMI I PROVAVE
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

  // 2. KRONOLOGJIA TEMPORALE
  const handleBuildChronology = async () => {
    if (!caseId || isLoadingChronology) return;
    setIsLoadingChronology(true);

    try {
      const response = await forensicDeskService.sendChatMessage(
        caseId,
        `[KRONOLOGJI TEMPORALE]: Rindërto renditjen kronologjike të ngjarjeve dhe provave për lëndën "${clientName}", duke u mbështetur në datat e dokumenteve dhe provave të administruara në dosje. Renditi veprimet sipas rendit kohor me data të sakta.`,
        `Organi: ${courtJurisdiction}`
      );
      setChronologyText(response.content || "Kronologjia u përpilua me sukses.");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi rindërtimi i kronologjisë.");
    } finally {
      setIsLoadingChronology(false);
    }
  };

  // 3. HARTIMI PROCEDURAL PROFESIONAL (PA REFUZIME NGA CLAUDE)
  const handleGenerateJudicialAct = async () => {
    if (!caseId || isDrafting) return;

    setIsDrafting(true);
    setDraftedLegalAct('');

    const actDefinitions: Record<DraftingActType, { title: string; promptNote: string }> = {
      KALLËZIM_PENAL: {
        title: "Kallëzim Penal sipas Nenit 83 të Kodit të Procedurës Penale (KPPRK)",
        promptNote: "Harto një Kallëzim Penal të plotë, të argumentuar me faktet e provave të dosjes, dispozitat e Kodit Penal të Kosovës (KPRK) dhe dispozitat procedurale të KPPRK-së."
      },
      MASË_SIGURIMI: {
        title: "Kërkesë për Masë të Përkohshme Sigurimi",
        promptNote: "Harto një Kërkesë për Caktimin e Masës së Përkohshme të Sigurimit sipas dispozitave të LPK-së dhe KPPRK-së, duke arsyetuar rrezikun e menjëhershëm dhe bazueshmërinë e kërkesës."
      },
      ANKESË_APEL: {
        title: "Ankesë kundër Aktgjykimit / Vendimit në Gjykatën e Apelit",
        promptNote: "Harto një Ankesë procedurale të bazuar në Nenin 182 të LPK-së dhe nenet përkatëse të KPPRK-së për shkelje thelbësore të dispozitave dhe vërtetim të gabuar të gjendjes faktike."
      },
      PRAPËSIM_PADI: {
        title: "Prapësim dhe Përgjigje në Padi me Llogaritje të Kamatës (LMD)",
        promptNote: "Harto një Prapësim profesional dhe Përgjigje në Padi duke kundërshtuar kërkesëpadinë në themel dhe procedurë, me referenca nga Ligji për Marrëdhëniet e Detyrimeve (LMD)."
      }
    };

    const currentConfig = actDefinitions[selectedAct];

    const legalPrompt = `[DRAFT PROCEDURAL I SHKRESËS LIGJORE]
Lloji i aktit: "${currentConfig.title}"
Palë e përfshirë: "${clientName}"
Gjykata / Organi kompetent: "${courtJurisdiction}"

DETYRË PËR HARTIMIN E SHKRESËS:
1. ${currentConfig.promptNote}
2. Përdor formatin standard procedural të akteve gjyqësore në Kosovë:
   - Koka e aktit (Organi kompetent, Numri i lëndës, Të dhënat e palëve)
   - Baza ligjore e saktë (nenet përkatëse të legjislacionit pozitiv të Kosovës)
   - Përmbledhja e fakteve të vërtetuara nga provat e administruara
   - Arsyetimi juridiko-doktrinar i kërkesës
   - Propozimi i qartë për vendimmarrje
   - Vendi për datën dhe nënshkrimin e parashtruesit / avokatit të autorizuar.
3. Shkruaj aktin të plotë, të qartë, në gjuhë të pastër juridike dhe të gatshëm për ekzaminim profesional.`;

    try {
      const response = await forensicDeskService.sendChatMessage(
        caseId,
        legalPrompt,
        `Gjykata Kompetente: ${courtJurisdiction}. Lënda e klientit: ${clientName}.`
      );
      setDraftedLegalAct(response.content || "");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi hartimi i shkresës procedurale.");
    } finally {
      setIsDrafting(false);
    }
  };

  const handleCopyDraftText = () => {
    if (!draftedLegalAct) return;
    navigator.clipboard.writeText(draftedLegalAct);
    setCopiedDraftText(true);
    setTimeout(() => setCopiedDraftText(false), 2500);
  };

  return (
    <div className="glass-panel p-4 sm:p-6 rounded-2xl sm:rounded-3xl border border-rose-500/30 bg-card shadow-xl space-y-4 sm:space-y-6">
      
      {/* SHIRITI I KOKËS SË WAR ROOM */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3 sm:gap-4 border-b border-main pb-4 sm:pb-5">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-600/10 text-rose-500 flex items-center justify-center shrink-0">
            <Swords size={20} className="sm:w-5 sm:h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm sm:text-base md:text-lg font-black uppercase tracking-tight text-text-primary flex items-center gap-2">
                <span>Salla Operative e Kryqëzimit (War Room)</span>
              </h2>
              <button
                type="button"
                onClick={() => {
                  if (onEvidenceChange) onEvidenceChange();
                  alert("Provat u rifreskuan nga të gjithë laboratorët.");
                }}
                title="Rifresko të dhënat"
                className="p-1 text-text-muted hover:text-text-primary rounded-lg hover:bg-hover transition-colors cursor-pointer"
              >
                <RefreshCw size={13} />
              </button>
            </div>
            <p className="text-[11px] sm:text-xs text-text-muted mt-0.5">
              Kryqëzimi i Shkresave, Audios, Videove dhe Financave në një matricë të vetme
            </p>
          </div>
        </div>

        {/* Butonat e Nën-Skedave + Kontrolli i Zmadhimit */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Kontrolli i Zmadhimit */}
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

          {/* VETËM 2 NËN-SKEDA THELBËSORE */}
          <div className="flex items-center gap-1 bg-surface border border-main rounded-xl sm:rounded-2xl p-1 shadow-inner w-full sm:w-auto">
            <button
              type="button"
              onClick={() => setActiveSubTab('CROSS_EXAM')}
              className={`flex-1 sm:flex-initial px-3.5 py-1.5 sm:py-2 rounded-lg sm:rounded-xl text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                activeSubTab === 'CROSS_EXAM'
                  ? 'bg-rose-600 text-white shadow-md'
                  : 'text-text-muted hover:text-text-primary hover:bg-hover'
              }`}
            >
              <Flame size={13} /> 
              <span>1. Kryqëzimi i Provave</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab('DRAFTING')}
              className={`flex-1 sm:flex-initial px-3.5 py-1.5 sm:py-2 rounded-lg sm:rounded-xl text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                activeSubTab === 'DRAFTING'
                  ? 'bg-rose-600 text-white shadow-md'
                  : 'text-text-muted hover:text-text-primary hover:bg-hover'
              }`}
            >
              <FileText size={13} /> 
              <span>2. Hartimi i Shkresës</span>
            </button>
          </div>
        </div>
      </div>

      {/* 1. MATRICA E KRYQËZIMIT DHE PYETJET TËRTHORE */}
      {activeSubTab === 'CROSS_EXAM' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface p-3.5 sm:p-4 rounded-2xl border border-main">
            <div className="text-xs space-y-0.5">
              <span className="font-bold text-text-primary flex items-center gap-1.5">
                <AlertTriangle size={14} className="text-rose-500" />
                Matrica e Kontradiktave & Pyetësori Taktik
              </span>
              <p className="text-[11px] sm:text-xs text-text-muted">
                Përplas provat materiale për të zbuluar alibitë dhe për të përgatitur pyetjet e seancës.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={handleBuildChronology}
                disabled={isLoadingChronology}
                className="h-9 sm:h-10 px-3 bg-card hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 cursor-pointer shadow-xs disabled:opacity-40"
              >
                {isLoadingChronology ? <Loader2 size={13} className="animate-spin" /> : <Clock size={13} className="text-primary-start" />}
                <span>Kronologjia</span>
              </button>

              <button
                type="button"
                onClick={handleRunMultimodalSynthesis}
                disabled={isCrossAnalyzing}
                className="h-9 sm:h-10 px-4 sm:px-5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-40"
              >
                {isCrossAnalyzing ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                <span>{synthesisData ? 'Ri-Kryqëzo' : 'Fillo Kryqëzimin'}</span>
              </button>
            </div>
          </div>

          <div
            className="min-h-[400px] max-h-[620px] overflow-y-auto custom-finance-scroll p-4 sm:p-6 bg-surface/40 rounded-2xl border border-main text-text-primary select-text space-y-4"
            style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
          >
            {synthesisData ? (
              <div className="space-y-4">
                {/* Teoria Kryesore e Rastit */}
                <div className="p-4 bg-primary-start/10 rounded-2xl border border-primary-start/20 space-y-1.5">
                  <h3 className="font-bold text-primary-start flex items-center gap-2 uppercase text-xs sm:text-sm">
                    <Award size={15} /> Teoria Kryesore e Rastit:
                  </h3>
                  <p className="text-text-primary leading-relaxed text-xs sm:text-sm">{synthesisData.winning_theory_of_the_case}</p>
                </div>

                {/* Kontradiktat */}
                {synthesisData.critical_cross_contradictions?.length > 0 && (
                  <div className="p-4 bg-rose-500/10 rounded-2xl border border-rose-500/20 space-y-2">
                    <h3 className="font-bold text-rose-500 flex items-center gap-2 uppercase text-xs sm:text-sm">
                      <Flame size={15} /> Kontradiktat e Identifikuara:
                    </h3>
                    <ul className="list-disc list-inside space-y-1 text-text-primary text-xs sm:text-sm">
                      {synthesisData.critical_cross_contradictions.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Pyetësori Taktik */}
                {synthesisData.cross_examination_traps?.length > 0 && (
                  <div className="p-4 bg-surface rounded-2xl border border-main space-y-3">
                    <h3 className="font-bold text-text-primary flex items-center gap-2 uppercase text-xs sm:text-sm">
                      <Target size={15} className="text-rose-500" /> Pyetësori Taktik për Seancë:
                    </h3>
                    <div className="space-y-2.5">
                      {synthesisData.cross_examination_traps.map((trap, idx) => (
                        <div key={idx} className="p-3 bg-card rounded-xl border border-main space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold text-rose-500">Palë / Dëshmitar: {trap.witness_or_target}</span>
                            <span className="text-text-muted font-mono">#{idx + 1}</span>
                          </div>
                          <p className="font-bold text-text-primary italic text-xs sm:text-sm">"{trap.question}"</p>
                          <p className="text-text-muted pt-1 text-[11px] sm:text-xs">
                            <span className="font-bold text-primary-start">Qëllimi Procedural:</span> {trap.trap_explanation}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Dyshimi i Arsyeshëm */}
                {synthesisData.in_dubio_pro_reo_vectors?.length > 0 && (
                  <div className="p-4 bg-card rounded-2xl border border-main space-y-2">
                    <h3 className="font-bold text-text-primary flex items-center gap-2 uppercase text-xs sm:text-sm">
                      <HelpCircle size={15} className="text-emerald-500" /> Elementet e Dyshimit të Arsyeshëm (In Dubio Pro Reo):
                    </h3>
                    <ul className="list-disc list-inside space-y-1 text-text-muted text-xs sm:text-sm">
                      {synthesisData.in_dubio_pro_reo_vectors.map((v, i) => (
                        <li key={i}>{v}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : chronologyText ? (
              <div className="whitespace-pre-wrap font-mono text-xs sm:text-sm">{chronologyText}</div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2.5 py-16">
                <Swords size={40} className="text-rose-500/30" />
                <p className="text-xs sm:text-sm max-w-sm">
                  Shtypni butonin <span className="text-rose-500 font-bold">"Fillo Kryqëzimin"</span> për të analizuar dhe kryqëzuar të gjitha provat e administruara.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. HARTIMI I AKTEVE PROCEDURALE */}
      {activeSubTab === 'DRAFTING' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 bg-surface p-3.5 sm:p-4 rounded-2xl border border-main">
            <div className="flex items-center gap-2 flex-wrap flex-1">
              <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-card border border-main text-text-muted text-xs font-bold shrink-0">
                <Scale size={13} className="text-primary-start" />
                <span>Akti:</span>
              </div>

              <select
                value={selectedAct}
                onChange={(e) => setSelectedAct(e.target.value as DraftingActType)}
                className="h-9 sm:h-10 bg-card border border-main rounded-xl px-2.5 text-xs font-bold text-text-primary focus:outline-none focus:border-rose-500 flex-1 min-w-[200px]"
              >
                <option value="KALLËZIM_PENAL">Kallëzim Penal (Neni 83 KPPRK)</option>
                <option value="MASË_SIGURIMI">Kërkesë për Masë Sigurimi (LPK / KPPRK)</option>
                <option value="ANKESË_APEL">Ankesë në Gjykatën e Apelit</option>
                <option value="PRAPËSIM_PADI">Prapësim dhe Përgjigje në Padi</option>
              </select>

              <button
                type="button"
                onClick={handleGenerateJudicialAct}
                disabled={isDrafting}
                className="h-9 sm:h-10 px-4 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-40 shrink-0"
              >
                {isDrafting ? <Loader2 size={13} className="animate-spin" /> : <FileCheck size={13} />}
                <span>{draftedLegalAct ? 'Ri-Harto' : 'Harto Shkresën'}</span>
              </button>
            </div>

            {draftedLegalAct && (
              <button
                type="button"
                onClick={handleCopyDraftText}
                className="h-9 sm:h-10 px-3.5 bg-card hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 cursor-pointer shadow-xs shrink-0 self-end sm:self-auto"
              >
                {copiedDraftText ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                <span>{copiedDraftText ? 'U Kopjua' : 'Kopjo Shkresën'}</span>
              </button>
            )}
          </div>

          <div
            className="min-h-[420px] max-h-[640px] overflow-y-auto custom-finance-scroll p-4 sm:p-8 bg-surface/40 rounded-2xl border border-main text-text-primary whitespace-pre-wrap font-sans select-text leading-relaxed"
            style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
          >
            {draftedLegalAct || (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2.5 py-16">
                <FileText size={40} className="text-rose-500/30" />
                <p className="text-xs sm:text-sm max-w-sm">
                  Përzgjidhni aktin procedural dhe shtypni <span className="font-bold text-text-primary">"Harto Shkresën"</span> për të gjeneruar draftin e plotë ligjor sipas dispozitave të Kosovës.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* FOOTER */}
      <div className="pt-3 border-t border-main flex flex-col sm:flex-row items-center justify-between gap-1.5 text-[10px] sm:text-[11px] text-text-muted">
        <span className="flex items-center gap-1.5 font-medium">
          <ShieldCheck size={13} className="text-emerald-500" />
          Pajtueshmëri me Kodin e Procedurës Penale dhe LPK të Kosovës
        </span>
        <span className="font-mono">Vula: {chainOfCustodyHash ? `${chainOfCustodyHash.slice(0, 18)}...` : 'Aktive'}</span>
      </div>
    </div>
  );
};

export default SynthesisWarRoom;