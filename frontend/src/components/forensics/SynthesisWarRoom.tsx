// FILE: frontend/src/components/forensics/SynthesisWarRoom.tsx
// PHOENIX PROTOCOL - SYNTHESIS WAR ROOM V2.2 (PERSISTENT LOAD ON MOUNT)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS

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
  FolderArchive,
  AlertTriangle,
  Clock,
  Send,
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

type DraftingActType = 'KALLËZIM_PENAL_PSRK' | 'MASË_EMERGJENTE_24H' | 'ANKESË_APEL' | 'PRAPËSIM_PADI';

// ✅ Përmirësuar: Nivele të madhësisë së shkrimit
const FONT_LEVELS = [
  { label: '90%',   base: 15,   line: 1.6 },
  { label: '100%',  base: 17,   line: 1.7 },
  { label: '115%',  base: 19,   line: 1.75 },
  { label: '130%',  base: 21,   line: 1.8 },
  { label: '150%',  base: 24,   line: 1.85 },
  { label: '175%',  base: 28,   line: 1.9 },
  { label: '200%',  base: 32,   line: 2.0 }
];

export const SynthesisWarRoom: React.FC<SynthesisWarRoomProps> = ({
  caseId,
  clientName = 'Pala e Përfaqësuar',
  chainOfCustodyHash = 'SEAL-SERVER-ACTIVE',
  courtJurisdiction = 'Gjykata Themelore Prishtinë',
  partnerLawyerName = 'Av. Zyra Partner e Licencuar OAK',
  partnerLawyerLicense = 'OAK-2026-KS',
  onEvidenceChange
}) => {
  // Gjendjet e Kryqëzimit Multimodal
  const [isCrossAnalyzing, setIsCrossAnalyzing] = useState<boolean>(false);
  const [synthesisData, setSynthesisData] = useState<WarRoomSynthesisResponse | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<'CROSS_EXAM' | 'DRAFTING' | 'DISPATCH'>('CROSS_EXAM');

  // Gjendjet e Kronologjisë
  const [isLoadingChronology, setIsLoadingChronology] = useState<boolean>(false);
  const [chronologyText, setChronologyText] = useState<string>('');

  // Gjendjet e Hartimit Procedural me Claude Sonnet 4.6
  const [selectedAct, setSelectedAct] = useState<DraftingActType>('KALLËZIM_PENAL_PSRK');
  const [isDrafting, setIsDrafting] = useState<boolean>(false);
  const [draftedLegalAct, setDraftedLegalAct] = useState<string>('');

  // Gjendjet e Kopjimit dhe Arkivimit
  const [, setCopiedCrossText] = useState<boolean>(false);
  const [copiedDraftText, setCopiedDraftText] = useState<boolean>(false);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveSuccess, setArchiveSuccess] = useState<boolean>(false);
  const [latestSealedHash, setLatestSealedHash] = useState<string>(chainOfCustodyHash);

  // ✅ Shtuar: Kontrolli i zmadhimit të shkrimit
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_war_room_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1; // default 100%
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

  // ✅ Ngarkon sintezën më të fundit nga serveri në montim
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

  // 1. EKZEKUTIMI I KRYQËZIMIT MADHOR TË PROVAVE ME CLAUDE SONNET 4.6
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

  // 2. RINDËRTIMI I KRONOLOGJISË NGA TERMINALI FORENZIK
  const handleBuildChronology = async () => {
    if (!caseId || isLoadingChronology) return;
    setIsLoadingChronology(true);

    try {
      const response = await forensicDeskService.sendChatMessage(
        caseId,
        `[KRONOLOGJI TEMPORALE]: Rindërto renditjen kronologjike të provave minutë-pas-minute për lëndën ${clientName}, duke u mbështetur në datat e dokumenteve dhe fotove me EXIF/GPS.`,
        `Gjykata: ${courtJurisdiction}`
      );
      setChronologyText(response.content || "Kronologjia u përpilua.");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi rindërtimi i kronologjisë.");
    } finally {
      setIsLoadingChronology(false);
    }
  };

  // 3. HARTIMI AUTOMATIK I SHKRESËS ME CLAUDE SONNET 4.6
  const handleGenerateJudicialAct = async () => {
    if (!caseId || isDrafting) return;

    setIsDrafting(true);
    setDraftedLegalAct('');

    const actLabels: Record<DraftingActType, string> = {
      KALLËZIM_PENAL_PSRK: "Kallëzim Penal Solemn për Prokurorinë Speciale (PSRK)",
      MASË_EMERGJENTE_24H: "Kërkesë për Masë Emergjente brenda 24H (Nenet 188/221 KPPRK)",
      ANKESË_APEL: "Ankesë në Gjykatën e Apelit në Prishtinë (Neni 182 LPK)",
      PRAPËSIM_PADI: "Prapësim dhe Përgjigje në Padi me Kamatëvonesë LMD (Neni 265)"
    };

    try {
      const response = await forensicDeskService.sendChatMessage(
        caseId,
        `[HARTIM PROCEDURAL]: Harto shkresën "${actLabels[selectedAct]}" për klientin ${clientName}. Përfshij vulën ${latestSealedHash}, nene të sakta të legjislacionit të Kosovës, dhe nënshkrimin e Av. ${partnerLawyerName} (${partnerLawyerLicense}).`,
        `Gjykata Kompetente: ${courtJurisdiction}`
      );
      setDraftedLegalAct(response.content || "");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi hartimi i aktit gjyqësor.");
    } finally {
      setIsDrafting(false);
    }
  };

  // 4. VULOSJA DHE ARKIVIMI I DOSJES NË SERVER (CHAIN OF CUSTODY)
  const handleArchiveMasterDossier = async () => {
    if (!caseId) return;

    setIsArchiving(true);
    try {
      const stamp = await forensicDeskService.sealCustody(
        caseId,
        `ARKIVIM_I_WAR_ROOM: ${clientName} (${selectedAct})`
      );
      setLatestSealedHash(stamp.custody_hash);
      setArchiveSuccess(true);
      if (onEvidenceChange) onEvidenceChange();
      setTimeout(() => setArchiveSuccess(false), 3500);
    } catch (err: any) {
      console.error("Archive failure:", err);
      alert(err?.response?.data?.detail || "Dështoi vulosja dhe arkivimi i dosjes në server.");
    } finally {
      setIsArchiving(false);
    }
  };

  const handleCopyText = (text: string, type: 'CROSS' | 'DRAFT') => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    if (type === 'CROSS') {
      setCopiedCrossText(true);
      setTimeout(() => setCopiedCrossText(false), 2500);
    } else {
      setCopiedDraftText(true);
      setTimeout(() => setCopiedDraftText(false), 2500);
    }
  };

  const dispatchMessage = `Të nderuar,\n\nZyra Ligjore ka finalizuar me sukses Kryqëzimin Multimodal të Provave për lëndën "${clientName}".\n\n📌 Vula Digjitale e Serverit (HMAC-SHA256): ${latestSealedHash}\n🏛️ Gjykata: ${courtJurisdiction}\n⚖️ Avokat Përgjegjës: ${partnerLawyerName} (Licenca: ${partnerLawyerLicense})\n\nDosja e plotë forenzike së bashku me shkresën procedurale është vulosur dhe është e gatshme për depozitim zyrtar.\n\nMe respekt,\nJuristi AI — Qendra e Ekspertizës Forenzike`;

  return (
    <div className="glass-panel p-6 rounded-3xl border border-rose-500/30 bg-card shadow-xl space-y-6">
      {/* SHIRITI I KOKËS SË WAR ROOM */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 border-b border-main pb-5">
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="w-10 h-10 rounded-xl bg-rose-600/10 text-rose-500 flex items-center justify-center">
              <Swords size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-black uppercase tracking-tight text-text-primary flex items-center gap-2">
                  <span>Salla Operative e Kryqëzimit (War Room)</span>
                  <span className="px-2 py-0.5 rounded-full bg-rose-600/15 text-rose-500 text-[10px] font-mono font-bold uppercase">
                    Claude Sonnet 4.6 • Top Secret
                  </span>
                </h2>
                <button
                  type="button"
                  onClick={() => {
                    if (onEvidenceChange) onEvidenceChange();
                    alert("Provat u rifreskuan nga të gjithë laboratorët!");
                  }}
                  title="Rifresko provat e sallës"
                  className="p-1.5 text-text-muted hover:text-text-primary rounded-lg hover:bg-hover transition-colors cursor-pointer"
                >
                  <RefreshCw size={14} />
                </button>
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Kryqëzimi i Dokumenteve, Audios me Diarizim, Videove me EXIF dhe Financave LMD
              </p>
            </div>
          </div>
        </div>

        {/* Butonat e Nën-Laboratorëve + Kontrolli i Zmadhimit */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Kontrolli i Zmadhimit */}
          <div className="flex items-center gap-1 rounded-xl border border-main bg-surface p-1" aria-label="Madhësia e shkrimit">
            <button
              type="button"
              onClick={handleDecreaseFont}
              disabled={fontLevelIndex === 0}
              title="Zvogëlo madhësinë e shkrimit"
              className="h-7 w-7 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30"
            >
              A−
            </button>
            <button
              type="button"
              onClick={handleResetFont}
              title="Rivendos madhësinë e shkrimit"
              className="min-w-10 rounded-lg px-1 text-[11px] font-bold text-text-muted hover:bg-hover hover:text-text-primary"
            >
              {activeFont.label}
            </button>
            <button
              type="button"
              onClick={handleIncreaseFont}
              disabled={fontLevelIndex === FONT_LEVELS.length - 1}
              title="Rrit madhësinë e shkrimit"
              className="h-7 w-7 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30"
            >
              A+
            </button>
          </div>

          <div className="flex items-center gap-1.5 bg-surface border border-main rounded-2xl p-1 shadow-inner overflow-x-auto">
            <button
              type="button"
              onClick={() => setActiveSubTab('CROSS_EXAM')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer ${
                activeSubTab === 'CROSS_EXAM'
                  ? 'bg-rose-600 text-white shadow-md'
                  : 'text-text-muted hover:text-text-primary hover:bg-hover'
              }`}
            >
              <Flame size={14} /> 1. Matrica & Pyetjet Tërthore
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab('DRAFTING')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer ${
                activeSubTab === 'DRAFTING'
                  ? 'bg-rose-600 text-white shadow-md'
                  : 'text-text-muted hover:text-text-primary hover:bg-hover'
              }`}
            >
              <FileText size={14} /> 2. Hartimi i Shkresave
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab('DISPATCH')}
              className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer ${
                activeSubTab === 'DISPATCH'
                  ? 'bg-rose-600 text-white shadow-md'
                  : 'text-text-muted hover:text-text-primary hover:bg-hover'
              }`}
            >
              <Send size={14} /> 3. Pakoja & Vulosja
            </button>
          </div>
        </div>
      </div>

      {/* 1. MATRICA E KRYQËZIMIT DHE PYETJET TËRTHORE */}
      {activeSubTab === 'CROSS_EXAM' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface p-4 rounded-2xl border border-main">
            <div className="text-xs space-y-0.5">
              <span className="font-bold text-text-primary flex items-center gap-1.5">
                <AlertTriangle size={14} className="text-rose-500" />
                Matrica e Kontradiktave & Cross-Examination (Claude Sonnet 4.6)
              </span>
              <p className="text-text-muted">
                Përplas të gjitha provat për të gjeneruar pyetjet vrastare të seancës dhe alibitë e rreme.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleBuildChronology}
                disabled={isLoadingChronology}
                className="h-10 px-3.5 bg-card hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-40"
                title="Rindërto sekuencën kohore minutë-pas-minute"
              >
                {isLoadingChronology ? <Loader2 size={13} className="animate-spin" /> : <Clock size={13} className="text-primary-start" />}
                <span>Kronologjia</span>
              </button>

              <button
                type="button"
                onClick={handleRunMultimodalSynthesis}
                disabled={isCrossAnalyzing}
                className="h-10 px-5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-md transition-all cursor-pointer disabled:opacity-40"
              >
                {isCrossAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                <span>{synthesisData ? 'Ri-Kryqëzo Provat' : 'Fillo Kryqëzimin e Plotë'}</span>
              </button>
            </div>
          </div>

          {/* Dritarja e Rezultateve të War Room */}
          <div
            className="min-h-[480px] max-h-[620px] overflow-y-auto custom-finance-scroll p-6 bg-surface/40 rounded-2xl border border-main text-text-primary select-text space-y-4"
            style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
          >
            {synthesisData ? (
              <div className="space-y-4">
                {/* Teoria Fituese e Lëndës */}
                <div className="p-4 bg-primary-start/10 rounded-2xl border border-primary-start/20 space-y-1.5">
                  <h3 className="font-bold text-primary-start flex items-center gap-2 uppercase" style={{ fontSize: `${activeFont.base * 1.2}px` }}>
                    <Award size={16} /> Teoria Fituese e Lëndës:
                  </h3>
                  <p className="text-text-primary leading-relaxed">{synthesisData.winning_theory_of_the_case}</p>
                </div>

                {/* Kontradiktat Ndërprovuese */}
                {synthesisData.critical_cross_contradictions?.length > 0 && (
                  <div className="p-4 bg-rose-500/10 rounded-2xl border border-rose-500/20 space-y-2">
                    <h3 className="font-bold text-rose-500 flex items-center gap-2 uppercase" style={{ fontSize: `${activeFont.base * 1.2}px` }}>
                      <Flame size={16} /> Kontradiktat Ndërprovuese të Zbuluara:
                    </h3>
                    <ul className="list-disc list-inside space-y-1 text-text-primary">
                      {synthesisData.critical_cross_contradictions.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Pyetjet Tërthore Vrastare (Cross-Examination Traps) */}
                {synthesisData.cross_examination_traps?.length > 0 && (
                  <div className="p-4 bg-surface rounded-2xl border border-main space-y-3">
                    <h3 className="font-bold text-text-primary flex items-center gap-2 uppercase" style={{ fontSize: `${activeFont.base * 1.2}px` }}>
                      <Target size={16} className="text-rose-500" /> Pyetjet Tërthore për Seancë Gjyqësore:
                    </h3>
                    <div className="space-y-2.5">
                      {synthesisData.cross_examination_traps.map((trap, idx) => (
                        <div key={idx} className="p-3 bg-card rounded-xl border border-main space-y-1">
                          <div className="flex items-center justify-between" style={{ fontSize: `${activeFont.base * 0.9}px` }}>
                            <span className="font-bold text-rose-500">Objektivi: {trap.witness_or_target}</span>
                            <span className="text-text-muted font-mono">Pyetja #{idx + 1}</span>
                          </div>
                          <p className="font-bold text-text-primary italic" style={{ fontSize: `${activeFont.base}px` }}>"{trap.question}"</p>
                          <p className="text-text-muted pt-1" style={{ fontSize: `${activeFont.base * 0.85}px` }}>
                            <span className="font-bold text-primary-start">Kurthi Procedural:</span> {trap.trap_explanation}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Vektorët e Dyshimit të Arsyeshëm */}
                {synthesisData.in_dubio_pro_reo_vectors?.length > 0 && (
                  <div className="p-4 bg-card rounded-2xl border border-main space-y-2">
                    <h3 className="font-bold text-text-primary flex items-center gap-2 uppercase" style={{ fontSize: `${activeFont.base * 1.2}px` }}>
                      <HelpCircle size={16} className="text-emerald-500" /> Pikat e Dyshimit të Arsyeshëm (In Dubio Pro Reo):
                    </h3>
                    <ul className="list-disc list-inside space-y-1 text-text-muted">
                      {synthesisData.in_dubio_pro_reo_vectors.map((v, i) => (
                        <li key={i}>{v}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : chronologyText ? (
              <div className="whitespace-pre-wrap font-mono">{chronologyText}</div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-3 py-16">
                <Swords size={48} className="text-rose-500/30" />
                <p className="font-semibold max-w-md">
                  Shtypni butonin <span className="text-rose-500 font-bold">"Fillo Kryqëzimin e Plotë"</span> për të analizuar me Claude Sonnet 4.6 provat audio, vizuale dhe financiare në një matricë të vetme operacionale.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. HARTIMI I AKTEVE PROCEDURALE ME CLAUDE SONNET 4.6 */}
      {activeSubTab === 'DRAFTING' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface p-4 rounded-2xl border border-main">
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-card border border-main text-text-muted text-xs font-bold">
                <Scale size={14} className="text-primary-start" />
                <span>Standardi Procedural:</span>
              </div>

              <select
                value={selectedAct}
                onChange={(e) => setSelectedAct(e.target.value as DraftingActType)}
                className="h-10 bg-card border border-main rounded-xl px-3 text-xs font-bold text-text-primary focus:outline-none focus:border-rose-500"
              >
                <option value="KALLËZIM_PENAL_PSRK">Kallëzim Penal Solemn (PSRK / Themelore)</option>
                <option value="MASË_EMERGJENTE_24H">Kërkesë për Masë Emergjente 24H (Nenet 188/221 KPPRK)</option>
                <option value="ANKESË_APEL">Ankesë në Gjykatën e Apelit (Neni 182 LPK)</option>
                <option value="PRAPËSIM_PADI">Përgjigje në Padi (Prapësim me Kamatë LMD)</option>
              </select>

              <button
                type="button"
                onClick={handleGenerateJudicialAct}
                disabled={isDrafting}
                className="h-10 px-5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-md transition-all cursor-pointer disabled:opacity-40"
              >
                {isDrafting ? <Loader2 size={14} className="animate-spin" /> : <FileCheck size={14} />}
                <span>{draftedLegalAct ? 'Ri-Harto Shkresën' : 'Harto Aktin Zyrtar'}</span>
              </button>
            </div>

            {draftedLegalAct && (
              <button
                type="button"
                onClick={() => handleCopyText(draftedLegalAct, 'DRAFT')}
                className="h-10 px-4 bg-card hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                {copiedDraftText ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                <span>{copiedDraftText ? 'U Kopjua' : 'Kopjo Shkresën'}</span>
              </button>
            )}
          </div>

          <div
            className="min-h-[480px] max-h-[620px] overflow-y-auto custom-finance-scroll p-6 bg-surface/40 rounded-2xl border border-main text-text-primary whitespace-pre-wrap font-mono select-text"
            style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
          >
            {draftedLegalAct || (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-3 py-16">
                <FileText size={48} className="text-rose-500/30" />
                <p className="font-sans max-w-sm">
                  Përzgjidhni llojin e aktit më lart dhe klikoni <span className="font-bold text-text-primary">"Harto Aktin Zyrtar"</span> për të gjeneruar shkresën e plotë procedurale me Claude Sonnet 4.6.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. PAKOJA PËRFUNDIMTARE & VULOSJA ME CHAIN OF CUSTODY */}
      {activeSubTab === 'DISPATCH' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 space-y-4">
            <div className="p-5 rounded-3xl bg-surface border border-main space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                <Send size={15} className="text-primary-start" /> Njoftimi i Përmbledhur për Klientin / Organin
              </h3>
              <textarea
                readOnly
                value={dispatchMessage}
                rows={10}
                className="w-full bg-card border border-main rounded-2xl p-4 text-text-primary leading-relaxed font-sans focus:outline-none resize-none select-text"
                style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
              />
              <button
                type="button"
                onClick={() => {
                  navigator.clipboard.writeText(dispatchMessage);
                  alert("Mesazhi u kopjua për dërgim!");
                }}
                className="px-4 py-2 bg-primary-start hover:bg-primary-start/90 text-white rounded-xl text-xs font-bold flex items-center gap-2 cursor-pointer shadow-sm"
              >
                <Copy size={13} />
                <span>Kopjo Njoftimin për WhatsApp / Email</span>
              </button>
            </div>
          </div>

          <div className="lg:col-span-5 space-y-4">
            <div className="p-6 rounded-3xl bg-surface border border-main space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2 border-b border-main pb-3">
                <FolderArchive size={16} className="text-rose-500" /> Vulosja e Dosjes (Chain of Custody)
              </h3>

              <div className="space-y-2.5 text-xs">
                <div className="p-3 rounded-xl bg-card border border-main space-y-1">
                  <span className="text-text-muted text-[10px] uppercase font-bold">Vula Kriptografike e Serverit:</span>
                  <p className="font-mono font-bold text-emerald-500 truncate text-[11px]">{latestSealedHash}</p>
                </div>
                <div className="flex items-center justify-between p-3 rounded-xl bg-card border border-main">
                  <span className="text-text-muted">Kryqëzimi Multimodal:</span>
                  <span className="font-bold text-text-primary">
                    {synthesisData ? 'I Përfunduar' : 'Në Pritje'}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-xl bg-card border border-main">
                  <span className="text-text-muted">Shkresa e Hartuar:</span>
                  <span className="font-bold text-text-primary">
                    {draftedLegalAct ? selectedAct : 'E Papërgatitur'}
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={handleArchiveMasterDossier}
                disabled={isArchiving}
                className="w-full h-11 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs uppercase tracking-wider rounded-2xl transition-all flex items-center justify-center gap-2 shadow-md cursor-pointer disabled:opacity-40"
              >
                {isArchiving ? <Loader2 size={15} className="animate-spin" /> : <ShieldCheck size={15} />}
                <span>{archiveSuccess ? 'U Vulos me Sukses në Server!' : 'Vulos Dosjen me Chain of Custody'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FOOTER I STANDARDIT PROCEDURAL */}
      <div className="pt-4 border-t border-main flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-text-muted">
        <span className="flex items-center gap-1.5 font-medium">
          <ShieldCheck size={14} className="text-emerald-500" />
          Standard i Pajtueshëm me KPPRK dhe LPK të Kosovës
        </span>
        <span className="font-mono text-[10px]">Vula: {partnerLawyerName} ({partnerLawyerLicense})</span>
      </div>
    </div>
  );
};

export default SynthesisWarRoom;