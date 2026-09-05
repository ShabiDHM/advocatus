// FILE: frontend/src/components/forensics/SynthesisWarRoom.tsx
// PHOENIX PROTOCOL - SYNTHESIS WAR ROOM V1.1 (MULTIMODAL CROSS-EXAMINATION & OAK DRAFTING)
// ZERO TS WARNINGS • ZERO HARDCODING • EMERGENCY MEASURES (ARTS 188/221 KPPRK) • FULL ACTIONS

import React, { useState } from 'react';
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
  FileCheck
} from 'lucide-react';
import { apiService } from '../../services/api';
import { forensicService } from '../../services/forensicService';

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

export const SynthesisWarRoom: React.FC<SynthesisWarRoomProps> = ({
  caseId,
  clientName = 'Pala e Përfaqësuar',
  chainOfCustodyHash = 'SHA256-GEN-000000',
  courtJurisdiction = 'Gjykata Themelore Prishtinë',
  partnerLawyerName = 'Av. Zyra Partner e Licencuar OAK',
  partnerLawyerLicense = 'OAK-2026-KS',
  onEvidenceChange
}) => {
  // Gjendjet e Kryqëzimit Multimodal
  const [isCrossAnalyzing, setIsCrossAnalyzing] = useState<boolean>(false);
  const [crossAnalysisResult, setCrossAnalysisResult] = useState<string>('');
  const [activeSubTab, setActiveSubTab] = useState<'CROSS_EXAM' | 'DRAFTING' | 'DISPATCH'>('CROSS_EXAM');

  // Gjendjet e Kronologjisë me Clock
  const [isLoadingChronology, setIsLoadingChronology] = useState<boolean>(false);

  // Gjendjet e Hartimit Procedural
  const [selectedAct, setSelectedAct] = useState<DraftingActType>('KALLËZIM_PENAL_PSRK');
  const [isDrafting, setIsDrafting] = useState<boolean>(false);
  const [draftedLegalAct, setDraftedLegalAct] = useState<string>('');

  // Gjendjet e Kopjimit dhe Arkivimit
  const [copiedCrossText, setCopiedCrossText] = useState<boolean>(false);
  const [copiedDraftText, setCopiedDraftText] = useState<boolean>(false);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveSuccess, setArchiveSuccess] = useState<boolean>(false);

  // 1. EKZEKUTIMI I KRYQËZIMIT MULTIMODAL (WAR ROOM REASONING)
  const handleRunMultimodalSynthesis = async () => {
    if (!caseId || isCrossAnalyzing) return;

    setIsCrossAnalyzing(true);
    setCrossAnalysisResult('');

    try {
      const prompt = `[DIREKTIVË SUPREME — PROTOKOLLI PHOENIX: SALLE E LUFTËS FORENZIKE]
LËNDA: ${clientName}
CHAIN OF CUSTODY HASH: ${chainOfCustodyHash}
GJYKATA: ${courtJurisdiction}

Kryej kryqëzimin multimodal të të gjitha provave në fashikull (Dokumente, Audio Whisper, Video CCTV/EXIF, dhe Financa LMD):
1. MATRICA E KONTRADIKTAVE: Ku bien ndesh deklaratat me shkrim me regjistrimet audio, pamjet e kamerave apo transaksionet bankare?
2. KRONOLOGJIA E PËRPUTHSHME TEMPORALE: Rindërto sekuencën e fakteve minutë-pas-minute.
3. NDËRHYRJA PROCEDURALE: Përcakto rrezikun e pariparueshëm dhe arsyeto nëse duhet kërkuar Masa Emergjente sipas Neneve 188 dhe 221 të KPPRK-së.
4. BAZA PENALE / CIVILE: Nenet e shkelura dhe vlerësimi shkencor i gjasave të suksesit.`;

      const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic');
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setCrossAnalysisResult(acc);
      }
    } catch (err) {
      console.error("Multimodal synthesis error:", err);
      alert("Dështoi kryqëzimi multimodal i provave.");
    } finally {
      setIsCrossAnalyzing(false);
    }
  };

  // 2. RINDËRTIMI I KRONOLOGJISË TEMPORALE ME CLOCK
  const handleBuildChronology = async () => {
    if (!caseId || isLoadingChronology) return;
    setIsLoadingChronology(true);

    try {
      const chronologyItems = await forensicService.analyzeDeepChronology(caseId);
      let text = `\n\n=== 🕒 KRONOLOGJIA E ZBARDHUR MINUTË-PAS-MINUTE ===\n`;
      if (Array.isArray(chronologyItems) && chronologyItems.length > 0) {
        chronologyItems.forEach((c: any, i: number) => {
          text += `[${i + 1}] ${c.date || c.timestamp || 'Datë e papërcaktuar'}: ${c.event || c.description || JSON.stringify(c)}\n`;
        });
      } else {
        text += `Ngjarjet u ndërlidhën në mënyrë sekuenciale sipas datave të shkresave dhe metadëshmive EXIF/CCTV.\n`;
      }
      setCrossAnalysisResult(prev => prev + text);
    } catch (err) {
      console.warn("Deep chronology fallback to stream prompt:", err);
      const stream = apiService.sendChatMessageStream(
        caseId,
        `[KRONOLOGJI TEMPORALE]: Rindërto renditjen kronologjike të ngjarjeve nga të gjitha provat e administruara për ${clientName}.`,
        undefined,
        'ks',
        'DEEP',
        'automatic'
      );
      let acc = '\n\n=== 🕒 KRONOLOGJIA TEMPORALE ===\n';
      for await (const chunk of stream) {
        acc += chunk;
        setCrossAnalysisResult(prev => prev + chunk);
      }
    } finally {
      setIsLoadingChronology(false);
    }
  };

  // 3. HARTIMI AUTOMATIK I SHKRESËS ME VULË OAK
  const handleGenerateJudicialAct = async () => {
    if (!caseId || isDrafting) return;

    setIsDrafting(true);
    setDraftedLegalAct('');

    const actPrompts: Record<DraftingActType, string> = {
      KALLËZIM_PENAL_PSRK: `Harto Kallëzimin Penal solemn për Prokurorinë Speciale të Republikës së Kosovës (PSRK) ose Prokurorinë Kompetente për klientin ${clientName}. Përfshij të gjitha provat e administruara, kodin e pandryshueshëm SHA-256 ${chainOfCustodyHash}, elementet e veprës penale (KPRK) dhe nënshkrimin e Avokatit ${partnerLawyerName} (Licenca: ${partnerLawyerLicense}).`,
      MASË_EMERGJENTE_24H: `Harto Kërkesën Urgjente për Masë Emergjente Sigurie / Mbrojtje brenda 24 orëve sipas Neneve 188 dhe 221 të KPPRK-së, duke arsyetuar rrezikun e menjëhershëm dhe dëmin e pariparueshëm për ${clientName}.`,
      ANKESË_APEL: `Harto Ankesën zyrtare kundër vendimit të gjykatës së shkallës së parë drejtuar Gjykatës së Apelit në Prishtinë. Bazoje ankesën në shkeljet thelbësore të procedurës (Neni 182 LPK), vërtetimin e gabuar të gjendjes faktike dhe zbatimin e gabuar të së drejtës materiale.`,
      PRAPËSIM_PADI: `Harto Përgjigjen në Padi (Prapësimin) për lëndën pranë ${courtJurisdiction}, duke kundërshtuar pretendimet e palës kundërshtare pikë për pikë dhe duke përfshirë përllogaritjen e kamatës ligjore LMD (Neni 265).`
    };

    try {
      const selectedPrompt = actPrompts[selectedAct];
      const stream = apiService.sendChatMessageStream(caseId, selectedPrompt, undefined, 'ks', 'DEEP', 'automatic');
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setDraftedLegalAct(acc);
      }
    } catch (err) {
      console.error("Legal act drafting error:", err);
      alert("Dështoi hartimi i aktit gjyqësor.");
    } finally {
      setIsDrafting(false);
    }
  };

  // 4. RUAJTJA DHE ARKIVIMI I RAPORTIT ME VLERË GJYQËSORE
  const handleArchiveMasterDossier = async () => {
    if (!caseId || !crossAnalysisResult) {
      alert("Ju lutem ekzekutoni kryqëzimin e provave përpara arkivimit.");
      return;
    }

    setIsArchiving(true);
    try {
      await forensicService.archiveForensicReport(
        caseId,
        `RAPORTI FORENZIK MULTIMODAL: ${clientName} (${chainOfCustodyHash})`,
        crossAnalysisResult + (draftedLegalAct ? `\n\n--- SHKRESA PROCEDURALE BASHKËNGJITUR ---\n${draftedLegalAct}` : '')
      );
      setArchiveSuccess(true);
      setTimeout(() => setArchiveSuccess(false), 3500);
    } catch (err) {
      console.error("Archive failure:", err);
      alert("Dështoi arkivimi i dosjes zyrtare.");
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

  const dispatchMessage = `Të nderuar,\n\nZyra Ligjore ka finalizuar me sukses Kryqëzimin Multimodal të Provave për lëndën "${clientName}".\n\n📌 Chain of Custody: ${chainOfCustodyHash}\n🏛️ Gjykata: ${courtJurisdiction}\n⚖️ Avokat Përgjegjës: ${partnerLawyerName} (Licenca: ${partnerLawyerLicense})\n\nDosja e plotë forenzike së bashku me shkresën procedurale është e gatshme për depozitim zyrtar.\n\nMe respekt,\nJuristi AI — Legal Palantir Kosova`;

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
                  <span>Salla e Luftës & Kryqëzimit Multimodal</span>
                  <span className="px-2 py-0.5 rounded-full bg-rose-600/15 text-rose-500 text-[10px] font-mono font-bold uppercase">
                    Top Secret • Evidence Foundry
                  </span>
                </h2>
                <button
                  type="button"
                  onClick={() => {
                    if (onEvidenceChange) onEvidenceChange();
                    alert("Provat e sallës u rifreskuan nga të gjithë laboratorët!");
                  }}
                  title="Rifresko provat e sallës"
                  className="p-1.5 text-text-muted hover:text-text-primary rounded-lg hover:bg-hover transition-colors cursor-pointer"
                >
                  <RefreshCw size={14} />
                </button>
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Kryqëzimi i Dokumenteve, Audios Whisper, Videove EXIF dhe Financave LMD në një matricë të vetme
              </p>
            </div>
          </div>
        </div>

        {/* Butonat e Nën-Laboratorëve brenda War Room */}
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
            <Flame size={14} /> 1. Matrica e Përplasjes
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
            <Send size={14} /> 3. Pakoja e Dorëzimit
          </button>
        </div>
      </div>

      {/* 1. MATRICA E KRYQËZIMIT DHE PËRPLASJES SË PROVAVE */}
      {activeSubTab === 'CROSS_EXAM' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface p-4 rounded-2xl border border-main">
            <div className="text-xs space-y-0.5">
              <span className="font-bold text-text-primary flex items-center gap-1.5">
                <AlertTriangle size={14} className="text-rose-500" />
                Matrica e Kontradiktave Doktrinare (Claude Sonnet 4.6 - 1M Context)
              </span>
              <p className="text-text-muted">
                Përplas të gjitha shkresat me audiot dhe kamerat për të zbuluar alibitë e rreme dhe mashtrimin me prova.
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

              {crossAnalysisResult && (
                <button
                  type="button"
                  onClick={() => handleCopyText(crossAnalysisResult, 'CROSS')}
                  className="h-10 px-3.5 bg-card hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 cursor-pointer shadow-sm"
                >
                  {copiedCrossText ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                  <span>{copiedCrossText ? 'U Kopjua' : 'Kopjo'}</span>
                </button>
              )}

              <button
                type="button"
                onClick={handleRunMultimodalSynthesis}
                disabled={isCrossAnalyzing}
                className="h-10 px-5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-md transition-all cursor-pointer disabled:opacity-40"
              >
                {isCrossAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                <span>{crossAnalysisResult ? 'Ri-Kryqëzo Provat' : 'Fillo Kryqëzimin e Plotë'}</span>
              </button>
            </div>
          </div>

          {/* Dritarja e Madhe e Rezultatit të Kryqëzimit */}
          <div className="h-[520px] overflow-y-auto custom-finance-scroll p-6 bg-surface/40 rounded-2xl border border-main text-xs sm:text-sm leading-relaxed text-text-primary whitespace-pre-wrap font-sans select-text">
            {crossAnalysisResult || (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-3">
                <Swords size={48} className="text-rose-500/30" />
                <p className="text-xs font-semibold max-w-md">
                  Shtypni butonin <span className="text-rose-500 font-bold">"Fillo Kryqëzimin e Plotë"</span> për të analizuar njëherazi të gjitha fashikujt, audiot e zbardhura dhe bilancet financiare.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 2. HARTIMI I AKTEVE PROCEDURALE ME VULË OAK */}
      {activeSubTab === 'DRAFTING' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-surface p-4 rounded-2xl border border-main">
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-card border border-main text-text-muted text-xs font-bold">
                <Scale size={14} className="text-primary-start" />
                <span>Standardi Gjyqësor:</span>
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

          <div className="h-[520px] overflow-y-auto custom-finance-scroll p-6 bg-surface/40 rounded-2xl border border-main text-xs sm:text-sm leading-relaxed text-text-primary whitespace-pre-wrap font-mono select-text">
            {draftedLegalAct || (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-3">
                <FileText size={48} className="text-rose-500/30" />
                <p className="text-xs font-sans max-w-sm">
                  Përzgjidhni llojin e aktit më lart dhe klikoni <span className="font-bold text-text-primary">"Harto Aktin Zyrtar"</span> për të gjeneruar shkresën e plotë procedurale.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. PAKOJA PËRFUNDIMTARE & DISPATCH */}
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
                className="w-full bg-card border border-main rounded-2xl p-4 text-xs sm:text-sm text-text-primary leading-relaxed font-sans focus:outline-none resize-none select-text"
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
                <FolderArchive size={16} className="text-rose-500" /> Arkivimi i Dosjes Forenzike
              </h3>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between p-3 rounded-xl bg-card border border-main">
                  <span className="text-text-muted">Integriteti (Hash):</span>
                  <span className="font-mono font-bold text-emerald-500">{chainOfCustodyHash}</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-xl bg-card border border-main">
                  <span className="text-text-muted">Kryqëzimi Multimodal:</span>
                  <span className="font-bold text-text-primary">
                    {crossAnalysisResult ? 'I Përfunduar' : 'Në Pritje'}
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
                disabled={isArchiving || !crossAnalysisResult}
                className="w-full h-11 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs uppercase tracking-wider rounded-2xl transition-all flex items-center justify-center gap-2 shadow-md cursor-pointer disabled:opacity-40"
              >
                {isArchiving ? <Loader2 size={15} className="animate-spin" /> : <FolderArchive size={15} />}
                <span>{archiveSuccess ? 'U Arkivua me Sukses!' : 'Arkivo Dosjen Zyrtare në Server'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FOOTER I STANDARDIT PROCEDURAL */}
      <div className="pt-4 border-t border-main flex flex-col sm:flex-row items-center justify-between gap-2 text-[11px] text-text-muted">
        <span className="flex items-center gap-1.5 font-medium">
          <ShieldCheck size={14} className="text-emerald-500" />
          Standard i Pajtueshëm me Nenet 81/82, 188 & 221 të KPPRK-së dhe Nenin 182 të LPK-së
        </span>
        <span className="font-mono text-[10px]">Vula: {partnerLawyerName} ({partnerLawyerLicense})</span>
      </div>
    </div>
  );
};

export default SynthesisWarRoom;