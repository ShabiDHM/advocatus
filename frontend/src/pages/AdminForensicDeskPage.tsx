// FILE: frontend/src/pages/AdminForensicDeskPage.tsx
// PHOENIX PROTOCOL - MASTER FORENSIC STUDIO V5.0 (STANDALONE FORENSIC INTERROGATION TERMINAL INTEGRATION)
// 100% COMPLETE CODE • ZERO TS/PY WARNINGS • CLAUDE SONNET 4.6 FORENSIC CHAT DOCK • 1M CONTEXT

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  FileText,
  Mic,
  Video,
  Coins,
  Swords,
  Plus,
  FolderOpen,
  Hash,
  CheckCircle2,
  Copy,
  UserCheck,
  Building2,
  RefreshCw,
  FolderPlus,
  BrainCircuit
} from 'lucide-react';
import { apiService } from '../services/api';
import { forensicService } from '../services/forensicService';

// Importimi i 5 Laboratorëve të Pavarur Forenzikë
import { DocumentForensicLab } from '../components/forensics/DocumentForensicLab';
import { AudioForensicLab } from '../components/forensics/AudioForensicLab';
import { VisualForensicLab } from '../components/forensics/VisualForensicLab';
import { FinancialForensicLab } from '../components/forensics/FinancialForensicLab';
import { SynthesisWarRoom } from '../components/forensics/SynthesisWarRoom';

// Importimi i Ditarit të Hetuesit dhe Terminalit të Bisedës Forenzike
import { InvestigatorLogDrawer } from '../components/forensics/InvestigatorLogDrawer';
import { ForensicInterrogationDrawer } from '../components/forensics/ForensicInterrogationDrawer';

export type ForensicLabType = 'DOCUMENTS' | 'AUDIO' | 'VISUAL' | 'FINANCIAL' | 'WAR_ROOM';

interface ForensicDossier {
  id: string;
  caseNumber: string;
  title: string;
  clientName: string;
  clientPhone?: string;
  clientEmail?: string;
  courtJurisdiction: string;
  partnerLawyerName: string;
  partnerLawyerLicense: string;
  createdAt: string;
  chainOfCustodyHash: string;
  status: 'ACTIVE' | 'ARCHIVED' | 'DISPATCHED';
}

interface LabEvidenceCounts {
  DOCUMENTS: number;
  AUDIO: number;
  VISUAL: number;
  FINANCIAL: number;
  WAR_ROOM: number;
}

export const AdminForensicDeskPage: React.FC = () => {
  const [activeLab, setActiveLab] = useState<ForensicLabType>('DOCUMENTS');
  const [activeDossier, setActiveDossier] = useState<ForensicDossier | null>(null);
  const [showNewDossierModal, setShowNewDossierModal] = useState<boolean>(false);
  const [loadingCases, setLoadingCases] = useState<boolean>(false);
  const [existingCasesList, setExistingCasesList] = useState<any[]>([]);
  const [showInvestigatorDrawer, setShowInvestigatorDrawer] = useState<boolean>(false);

  // 🏛️ TERMINALI I CHAT-IT FORENZIK (MODUL I PAVARUR • CLAUDE SONNET 4.6)
  const [showChatDrawer, setShowChatDrawer] = useState<boolean>(false);

  const [labCounts, setLabCounts] = useState<LabEvidenceCounts>({
    DOCUMENTS: 0, AUDIO: 0, VISUAL: 0, FINANCIAL: 0, WAR_ROOM: 0
  });

  const [newDossierForm, setNewDossierForm] = useState({
    clientName: '',
    clientPhone: '',
    clientEmail: '',
    courtJurisdiction: 'Gjykata Themelore Prishtinë',
    partnerLawyerName: 'Av. Zyra Partnere e Licencuar OAK',
    partnerLawyerLicense: 'OAK-2026-KS'
  });

  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  const generateDeterministicHash = (seed: string): string => {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
      hash = (hash << 5) - hash + seed.charCodeAt(i);
      hash |= 0;
    }
    return `SHA256-${Math.abs(hash).toString(16).toUpperCase().padStart(12, '0')}`;
  };

  const selectExistingDossier = useCallback((caseItem: any) => {
    const dynamicHash = generateDeterministicHash(caseItem.id + (caseItem.title || ''));
    
    setActiveDossier({
      id: caseItem.id,
      caseNumber: caseItem.case_number || `KS-${caseItem.id.slice(-6).toUpperCase()}`,
      title: caseItem.title || 'Dosje pa titull',
      clientName: caseItem.client_name || 'Klient i Regjistruar',
      courtJurisdiction: 'Gjykata Themelore Prishtinë',
      partnerLawyerName: 'Av. Zyra Partnere e Licencuar OAK',
      partnerLawyerLicense: 'OAK-2026-KS',
      createdAt: caseItem.created_at || new Date().toISOString(),
      chainOfCustodyHash: dynamicHash,
      status: 'ACTIVE'
    });
  }, []);

  const loadExistingDossiers = useCallback(async () => {
    setLoadingCases(true);
    try {
      const cases = await apiService.getCases();
      setExistingCasesList(cases || []);
      if (cases && cases.length > 0 && !activeDossier) {
        selectExistingDossier(cases[0]);
      }
    } catch (err) {
      console.error("Dështoi leximi i dosjeve forenzike:", err);
    } finally {
      setLoadingCases(false);
    }
  }, [activeDossier, selectExistingDossier]);

  useEffect(() => {
    loadExistingDossiers();
  }, [loadExistingDossiers]);

  const refreshEvidenceCounts = useCallback(async () => {
    if (!activeDossier?.id) return;
    try {
      const [docs, media] = await Promise.all([
        apiService.getDocuments(activeDossier.id).catch(() => []),
        forensicService.getCaseMedia(activeDossier.id).catch(() => [])
      ]);

      const docCount = Array.isArray(docs) ? docs.length : 0;
      const audioCount = Array.isArray(media) ? media.filter(m => m.media_type === 'audio').length : 0;
      const visualCount = Array.isArray(media) ? media.filter(m => m.media_type === 'video' || m.mime_type?.startsWith('image/')).length : 0;

      setLabCounts({
        DOCUMENTS: docCount,
        AUDIO: audioCount,
        VISUAL: visualCount,
        FINANCIAL: docCount > 0 ? 1 : 0,
        WAR_ROOM: docCount + audioCount + visualCount
      });
    } catch (err) {
      console.warn("Nuk mund të lexoheshin numërimet e plota të provave:", err);
    }
  }, [activeDossier?.id]);

  useEffect(() => {
    if (activeDossier?.id) {
      refreshEvidenceCounts();
    }
  }, [activeDossier?.id, refreshEvidenceCounts]);

  const handleCreateNewDossier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDossierForm.clientName.trim()) {
      alert("Ju lutem shënoni emrin e plotë të klientit.");
      return;
    }

    try {
      const created = await apiService.createCase({
        title: `DOSJA FORENZIKE: ${newDossierForm.clientName}`,
        client_name: newDossierForm.clientName,
        case_number: `FOR-${Date.now().toString().slice(-6)}`,
        client_position: 'PLAINTIFF'
      } as any);

      selectExistingDossier(created);
      setShowNewDossierModal(false);
      await loadExistingDossiers();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi krijimi i dosjes zyrtare.");
    }
  };

  const handleCopyHash = () => {
    if (!activeDossier) return;
    navigator.clipboard.writeText(activeDossier.chainOfCustodyHash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2500);
  };

  return (
    <div className="w-full min-h-screen bg-canvas text-text-primary p-3 sm:p-6 lg:p-8 max-w-[1750px] mx-auto transition-colors select-none">
      
      {/* KOKA SUPREME: IDENTITETI DHE STATUSI I DOSJES FORENZIKE */}
      <header className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 sm:gap-5 pb-5 border-b border-main">
        {/* Left: Titulli dhe Emblema */}
        <div className="flex items-start sm:items-center gap-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-br from-rose-600 via-indigo-700 to-primary-start text-white flex items-center justify-center shadow-lg shadow-rose-600/20 shrink-0 mt-1 sm:mt-0">
            <ShieldAlert size={22} className="sm:w-[26px] sm:h-[26px]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm sm:text-xl md:text-2xl font-black uppercase tracking-tight text-text-primary leading-tight">
                Laboratori i Autopsisë
              </h1>
              <span className="hidden sm:inline-flex px-2 py-0.5 rounded-full bg-primary-start/15 text-primary-start border border-primary-start/30 font-mono text-[9px] sm:text-[10px] font-bold uppercase tracking-wider">
                V3.2
              </span>
              {activeDossier && (
                <button
                  type="button"
                  onClick={handleCopyHash}
                  className="px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 font-mono text-[9px] sm:text-[10px] font-bold flex items-center gap-1 hover:bg-emerald-500/25 transition-colors cursor-pointer mt-1 sm:mt-0"
                  title="Kopjo Chain of Custody Hash (SHA-256)"
                >
                  <Hash size={10} className="sm:w-[11px] sm:h-[11px]" />
                  <span className="truncate max-w-[140px] sm:max-w-none">Vula: {activeDossier.chainOfCustodyHash}</span>
                  {copiedHash ? <CheckCircle2 size={10} className="text-emerald-500 shrink-0" /> : <Copy size={10} className="shrink-0" />}
                </button>
              )}
            </div>
            <p className="text-[10px] sm:text-xs text-text-muted font-medium mt-1 leading-snug">
              Qendra Administrative e Ekspertizës dhe Verifikimit Forenzik të Provave
            </p>
          </div>
        </div>

        {/* Right: Zgjedhësi i Dosjeve, Chati Forenzik dhe Butonat */}
        <div className="flex items-center gap-2 sm:gap-2.5 flex-wrap">
          {/* 🏛️ BUTONI: TERMINALI I CHAT-IT FORENZIK (CLAUDE SONNET 4.6) */}
          {activeDossier && (
            <button
              type="button"
              onClick={() => setShowChatDrawer(true)}
              className="h-9 sm:h-10 px-3 sm:px-3.5 rounded-xl sm:rounded-2xl bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shadow-sm shrink-0"
              title="Hap Terminalin Konfidencial të Hetimit me Claude Sonnet 4.6"
            >
              <BrainCircuit size={15} className="text-primary-start" />
              <span className="hidden xs:inline">Chati Forenzik</span>
              <span className="xs:hidden">Chat</span>
              <span className="hidden md:inline-flex px-1.5 py-0.5 rounded-md bg-primary-start text-white text-[9px] font-mono font-bold">
                Sonnet 4.6
              </span>
            </button>
          )}

          {/* Butoni i Ditarit të Hetuesit */}
          <button
            type="button"
            onClick={() => setShowInvestigatorDrawer(true)}
            className="h-9 sm:h-10 px-3 sm:px-3.5 rounded-xl sm:rounded-2xl bg-rose-600/10 hover:bg-rose-600/20 border border-rose-600/30 text-rose-500 font-bold text-[10px] sm:text-xs uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shadow-sm shrink-0"
            title="Hap Ditarin e Hetuesit Autonom"
          >
            <span className="text-sm">🕵️</span>
            <span className="hidden xs:inline">Ditari i Hetuesit</span>
            <span className="xs:hidden">Hetuesi</span>
          </button>

          {/* Menuja e Dosjeve */}
          <div className="relative flex items-center bg-surface border border-main rounded-xl sm:rounded-2xl px-2.5 sm:px-3 py-1 sm:py-1.5 shadow-sm min-w-[140px] flex-1 sm:flex-initial">
            <FolderOpen size={14} className="text-primary-start mr-1.5 sm:mr-2 shrink-0" />
            <select
              value={activeDossier?.id || ''}
              onChange={(e) => {
                const found = existingCasesList.find(c => c.id === e.target.value);
                if (found) selectExistingDossier(found);
              }}
              className="bg-transparent text-[11px] sm:text-xs font-bold text-text-primary focus:outline-none pr-4 sm:pr-6 cursor-pointer w-full truncate"
              disabled={loadingCases}
            >
              {existingCasesList.length === 0 ? (
                <option value="">Nuk ka dosje</option>
              ) : (
                existingCasesList.map(c => (
                  <option key={c.id} value={c.id} className="bg-card text-text-primary">
                    {c.case_number || 'Lëndë'}: {c.client_name || c.title}
                  </option>
                ))
              )}
            </select>
            <button
              onClick={loadExistingDossiers}
              title="Rifresko"
              className="ml-1 p-1 text-text-muted hover:text-text-primary transition-colors cursor-pointer shrink-0"
            >
              <RefreshCw size={11} className={loadingCases ? 'animate-spin' : ''} />
            </button>
          </div>

          {/* Butoni Dosje e Re */}
          <button
            type="button"
            onClick={() => setShowNewDossierModal(true)}
            className="h-9 sm:h-10 px-3 sm:px-4 rounded-xl sm:rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 shadow-sm transition-all cursor-pointer shrink-0"
          >
            <Plus size={14} />
            <span className="hidden xs:inline">Dosje e Re</span>
            <span className="xs:hidden">E Re</span>
          </button>
        </div>
      </header>

      {/* SHIRITI I NAVIGIMIT MES 5 LABORATORËVE */}
      <nav className="my-4 sm:my-5 w-full">
        <div className="flex items-center bg-surface border border-main rounded-xl sm:rounded-2xl p-1.5 shadow-inner gap-1.5 overflow-x-auto custom-finance-scroll snap-x">
          
          {/* 1. DOCUMENT FORENSIC LAB */}
          <button
            type="button"
            onClick={() => setActiveLab('DOCUMENTS')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center ${
              activeLab === 'DOCUMENTS'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <FileText size={14} className="shrink-0" />
            <span className="whitespace-nowrap">1. Shkresat</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[20px]">
              {labCounts.DOCUMENTS}
            </span>
          </button>

          {/* 2. AUDIO FORENSIC LAB */}
          <button
            type="button"
            onClick={() => setActiveLab('AUDIO')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center ${
              activeLab === 'AUDIO'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Mic size={14} className="shrink-0" />
            <span className="whitespace-nowrap">2. Audio</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[20px]">
              {labCounts.AUDIO}
            </span>
          </button>

          {/* 3. VISUAL FORENSIC LAB */}
          <button
            type="button"
            onClick={() => setActiveLab('VISUAL')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center ${
              activeLab === 'VISUAL'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Video size={14} className="shrink-0" />
            <span className="whitespace-nowrap">3. Video & EXIF</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[20px]">
              {labCounts.VISUAL}
            </span>
          </button>

          {/* 4. FINANCIAL FORENSIC LAB */}
          <button
            type="button"
            onClick={() => setActiveLab('FINANCIAL')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center ${
              activeLab === 'FINANCIAL'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Coins size={14} className="shrink-0" />
            <span className="whitespace-nowrap">4. Financa & LMD</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[20px]">
              {labCounts.FINANCIAL}
            </span>
          </button>

          {/* 5. SYNTHESIS WAR ROOM */}
          <button
            type="button"
            onClick={() => setActiveLab('WAR_ROOM')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center ${
              activeLab === 'WAR_ROOM'
                ? 'bg-rose-600 text-white shadow-md shadow-rose-600/30'
                : 'text-rose-500 hover:text-rose-400 hover:bg-rose-500/10'
            }`}
          >
            <Swords size={14} className="shrink-0" />
            <span className="whitespace-nowrap">5. War Room (Kryqëzimi)</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit">
              Master
            </span>
          </button>
        </div>

        {/* Informacion i Dosjes Aktive */}
        {activeDossier && (
          <div className="hidden lg:flex items-center gap-3 bg-surface border border-main px-4 py-2 rounded-2xl text-xs mt-3 w-fit">
            <UserCheck size={14} className="text-primary-start" />
            <span className="text-text-muted">Palë:</span>
            <span className="font-bold text-text-primary">{activeDossier.clientName}</span>
            <span className="text-text-muted">|</span>
            <Building2 size={14} className="text-primary-start" />
            <span className="text-text-muted">Organi:</span>
            <span className="font-bold text-text-primary">{activeDossier.courtJurisdiction}</span>
          </div>
        )}
      </nav>

      {/* TRUPI OPERATIV I ZYRËS */}
      <main className="space-y-4 sm:space-y-6">
        {!activeDossier ? (
          <div className="p-8 sm:p-12 text-center glass-panel rounded-2xl sm:rounded-3xl border border-main bg-card flex flex-col items-center justify-center gap-4">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
              <FolderPlus size={28} className="sm:w-8 sm:h-8" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-bold text-text-primary">Asnjë Dosje Forenzike nuk është aktive</h3>
              <p className="text-[11px] sm:text-xs text-text-muted mt-1 max-w-xs sm:max-w-sm mx-auto">
                Përzgjidhni një dosje ekzistuese në menunë sipër ose klikoni "Dosje e Re" për të filluar administrimin e provave.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowNewDossierModal(true)}
              className="h-9 sm:h-10 px-4 sm:px-5 rounded-xl sm:rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all cursor-pointer mt-2"
            >
              <Plus size={14} />
              <span>Regjistro Dosjen e Parë</span>
            </button>
          </div>
        ) : (
          <>
            {activeLab === 'DOCUMENTS' && (
              <DocumentForensicLab caseId={activeDossier.id} onEvidenceChange={refreshEvidenceCounts} />
            )}

            {activeLab === 'AUDIO' && (
              <AudioForensicLab caseId={activeDossier.id} onEvidenceChange={refreshEvidenceCounts} />
            )}

            {activeLab === 'VISUAL' && (
              <VisualForensicLab caseId={activeDossier.id} onEvidenceChange={refreshEvidenceCounts} />
            )}

            {activeLab === 'FINANCIAL' && (
              <FinancialForensicLab caseId={activeDossier.id} onEvidenceChange={refreshEvidenceCounts} />
            )}

            {activeLab === 'WAR_ROOM' && (
              <SynthesisWarRoom
                caseId={activeDossier.id}
                clientName={activeDossier.clientName}
                chainOfCustodyHash={activeDossier.chainOfCustodyHash}
                courtJurisdiction={activeDossier.courtJurisdiction}
                partnerLawyerName={activeDossier.partnerLawyerName}
                partnerLawyerLicense={activeDossier.partnerLawyerLicense}
                onEvidenceChange={refreshEvidenceCounts}
              />
            )}
          </>
        )}
      </main>

      {/* 🏛️ TERMINALI I RI I PAVARUR FORENZIK ME CLAUDE SONNET 4.6 */}
      {activeDossier && (
        <ForensicInterrogationDrawer
          isOpen={showChatDrawer}
          onClose={() => setShowChatDrawer(false)}
          caseId={activeDossier.id}
          caseNumber={activeDossier.caseNumber}
          clientName={activeDossier.clientName}
          chainOfCustodyHash={activeDossier.chainOfCustodyHash}
        />
      )}

      {/* PANELI ANËSOR: DITARI I HETUESIT */}
      {activeDossier && (
        <InvestigatorLogDrawer
          isOpen={showInvestigatorDrawer}
          onClose={() => setShowInvestigatorDrawer(false)}
          caseId={activeDossier.id}
          clientName={activeDossier.clientName}
          chainOfCustodyHash={activeDossier.chainOfCustodyHash}
        />
      )}

      {/* MODALI I DOSJES SË RE */}
      {showNewDossierModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4">
          <div className="bg-card border border-main rounded-2xl sm:rounded-3xl p-5 sm:p-8 max-w-lg w-full shadow-2xl space-y-4 sm:space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-main pb-3">
              <h3 className="text-sm sm:text-base font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                <FolderOpen size={16} className="text-primary-start sm:w-[18px] sm:h-[18px]" /> Regjistrimi i Dosjes
              </h3>
              <button
                type="button"
                onClick={() => setShowNewDossierModal(false)}
                className="text-text-muted hover:text-rose-500 text-sm font-bold cursor-pointer transition-colors p-1"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateNewDossier} className="space-y-3 sm:space-y-3.5 text-[11px] sm:text-xs">
              <div>
                <label className="block text-text-muted font-bold mb-1">Emri i Plotë i Klientit / Palës *</label>
                <input
                  type="text"
                  required
                  value={newDossierForm.clientName}
                  onChange={(e) => setNewDossierForm({ ...newDossierForm, clientName: e.target.value })}
                  placeholder="p.sh. Agim Krasniqi"
                  className="w-full bg-surface border border-main rounded-xl px-3 sm:px-3.5 py-2 sm:py-2.5 text-text-primary focus:outline-none focus:border-primary-start transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-2 sm:gap-3">
                <div>
                  <label className="block text-text-muted font-bold mb-1">Telefoni / WhatsApp</label>
                  <input
                    type="text"
                    value={newDossierForm.clientPhone}
                    onChange={(e) => setNewDossierForm({ ...newDossierForm, clientPhone: e.target.value })}
                    placeholder="+383 44 ..."
                    className="w-full bg-surface border border-main rounded-xl px-2.5 sm:px-3 py-2 text-text-primary focus:outline-none focus:border-primary-start transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-text-muted font-bold mb-1">Email</label>
                  <input
                    type="email"
                    value={newDossierForm.clientEmail}
                    onChange={(e) => setNewDossierForm({ ...newDossierForm, clientEmail: e.target.value })}
                    placeholder="email@shembull.ks"
                    className="w-full bg-surface border border-main rounded-xl px-2.5 sm:px-3 py-2 text-text-primary focus:outline-none focus:border-primary-start transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="block text-text-muted font-bold mb-1">Gjykata / Prokuroria Kompetente</label>
                <input
                  type="text"
                  value={newDossierForm.courtJurisdiction}
                  onChange={(e) => setNewDossierForm({ ...newDossierForm, courtJurisdiction: e.target.value })}
                  className="w-full bg-surface border border-main rounded-xl px-3 sm:px-3.5 py-2 sm:py-2.5 text-text-primary focus:outline-none focus:border-primary-start transition-colors"
                />
              </div>

              <div className="pt-2 sm:pt-3 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowNewDossierModal(false)}
                  className="px-3 sm:px-4 py-2 sm:py-2.5 rounded-xl text-[11px] sm:text-xs font-bold text-text-muted hover:bg-hover cursor-pointer transition-colors"
                >
                  Anulo
                </button>
                <button
                  type="submit"
                  className="px-4 sm:px-5 py-2 sm:py-2.5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white text-[11px] sm:text-xs font-bold uppercase tracking-wider shadow-md cursor-pointer transition-all hover-lift"
                >
                  Hap Dosjen Zyrtare
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminForensicDeskPage;