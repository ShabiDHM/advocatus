// FILE: frontend/src/pages/AdminForensicDeskPage.tsx
// PHOENIX PROTOCOL - MASTER FORENSIC STUDIO V7.4 (MINIMALIST UI HEADER CLEANUP)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • SERVER-SIDE CUSTODY INTEGRATION

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
  ShieldCheck,
  Trash2,
  Loader2,
  X,
  User,
  Phone,
  Mail,
  Scale
} from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import {
  forensicDeskService,
  ForensicDossier,
  LabEvidenceCounts
} from '../services/forensicDeskService';

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

export const AdminForensicDeskPage: React.FC = () => {
  const { user } = useAuth();
  
  const isSuperAdmin = React.useMemo(() => {
    if (!user) return false;
    const role = String(user.role || (user as any).user_role || '').toUpperCase();
    return role === 'SUPERADMIN' || role === 'ADMIN';
  }, [user]);

  const [activeLab, setActiveLab] = useState<ForensicLabType>('DOCUMENTS');
  const [activeDossier, setActiveDossier] = useState<ForensicDossier | null>(null);
  
  const [loadingCases, setLoadingCases] = useState<boolean>(false);
  const [dossiersList, setDossiersList] = useState<ForensicDossier[]>([]);
  
  const [showNewDossierModal, setShowNewDossierModal] = useState<boolean>(false);
  const [showInvestigatorDrawer, setShowInvestigatorDrawer] = useState<boolean>(false);
  const [showChatDrawer, setShowChatDrawer] = useState<boolean>(false);
  const [deletingDossierId, setDeletingDossierId] = useState<string | null>(null);

  const [labCounts, setLabCounts] = useState<LabEvidenceCounts>({
    DOCUMENTS: 0, AUDIO: 0, VISUAL: 0, FINANCIAL: 0, WAR_ROOM: 0
  });

  const [newDossierForm, setNewDossierForm] = useState({
    clientName: '',
    clientPhone: '',
    clientEmail: '',
    courtJurisdiction: 'Gjykata Themelore Prishtinë'
  });

  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  const loadExistingDossiers = useCallback(async () => {
    setLoadingCases(true);
    const { mappedDossiers } = await forensicDeskService.loadAllDossiers();
    setDossiersList(mappedDossiers);
    
    if (mappedDossiers.length > 0) {
      setActiveDossier(prev => prev ? (mappedDossiers.find(d => d.id === prev.id) || mappedDossiers[0]) : mappedDossiers[0]);
    } else {
      setActiveDossier(null);
    }
    setLoadingCases(false);
  }, []);

  useEffect(() => {
    loadExistingDossiers();
  }, [loadExistingDossiers]);

  const refreshEvidenceCounts = useCallback(async () => {
    if (!activeDossier?.id) return;
    const counts = await forensicDeskService.getEvidenceCounts(activeDossier.id);
    setLabCounts(counts);
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
      const created = await forensicDeskService.createDossier({
        clientName: newDossierForm.clientName,
        courtJurisdiction: newDossierForm.courtJurisdiction
      });

      setActiveDossier(created);
      setShowNewDossierModal(false);
      setNewDossierForm({
        clientName: '',
        clientPhone: '',
        clientEmail: '',
        courtJurisdiction: 'Gjykata Themelore Prishtinë'
      });
      await loadExistingDossiers();
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi krijimi i dosjes zyrtare forenzike.");
    }
  };

  const handleDeleteDossier = async (caseId: string, clientName: string) => {
    if (!caseId) return;
    const confirmDelete = window.confirm(
      `A jeni absolutisht i sigurt që dëshironi të fshini dosjen "${clientName}" dhe TË GJITHA provat, dokumentet, audiot, videot, financat, war room, chat dhe hetuesin e lidhur? Ky veprim është i pakthyeshëm.`
    );
    if (!confirmDelete) return;

    setDeletingDossierId(caseId);
    try {
      await forensicDeskService.deleteDossier(caseId);
      await loadExistingDossiers();
      setActiveDossier(null);
      setLabCounts({ DOCUMENTS: 0, AUDIO: 0, VISUAL: 0, FINANCIAL: 0, WAR_ROOM: 0 });
    } catch (err: any) {
      console.error("Dështoi fshirja e dosjes:", err);
      alert(err?.response?.data?.detail || "Dështoi fshirja totale e dosjes.");
    } finally {
      setDeletingDossierId(null);
    }
  };

  const handleCopyHash = () => {
    if (!activeDossier?.chainOfCustodyHash) return;
    navigator.clipboard.writeText(activeDossier.chainOfCustodyHash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2500);
  };

  return (
    <div className="w-full min-h-screen bg-canvas text-text-primary p-3 sm:p-6 lg:p-8 max-w-[1750px] mx-auto transition-colors select-none">
      
      {/* KOKA SUPREME: IDENTITETI DHE STATUSI I DOSJES FORENZIKE */}
      <header className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 sm:gap-5 pb-5 border-b border-main">
        <div className="flex items-start sm:items-center gap-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-br from-rose-600 via-indigo-700 to-primary-start text-white flex items-center justify-center shadow-lg shadow-rose-600/20 shrink-0 mt-1 sm:mt-0">
            <ShieldAlert size={22} className="sm:w-[26px] sm:h-[26px]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-sm sm:text-xl md:text-2xl font-black uppercase tracking-tight text-text-primary leading-tight">
                Laboratori Forenzik
              </h1>
              
              {/* Vula e Thjeshtëzuar: Vetëm ikona + Vula + Kopjo */}
              {activeDossier && (
                <button
                  type="button"
                  onClick={handleCopyHash}
                  className="px-2.5 py-1 rounded-full bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-500 border border-emerald-500/30 font-mono text-[10px] font-bold flex items-center gap-1.5 transition-colors cursor-pointer mt-0.5"
                  title={`Chain of Custody Hash: ${activeDossier.chainOfCustodyHash} (Kliko për ta kopjuar)`}
                >
                  <Hash size={11} className="shrink-0" />
                  <span>{copiedHash ? 'U Kopjua!' : 'Vula'}</span>
                  {copiedHash ? <CheckCircle2 size={11} className="text-emerald-500 shrink-0" /> : <Copy size={11} className="shrink-0" />}
                </button>
              )}
            </div>
            <p className="text-[10px] sm:text-xs text-text-muted font-medium mt-1 leading-snug">
              Qendra Administrative e Ekspertizës dhe Verifikimit Forenzik të Provave
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-2.5 flex-wrap">
          {/* Butoni Chat (vetëm Chat) */}
          {isSuperAdmin && activeDossier && (
            <button
              type="button"
              onClick={() => setShowChatDrawer(true)}
              className="h-9 sm:h-10 px-3 sm:px-3.5 rounded-xl sm:rounded-2xl bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start font-bold text-[11px] sm:text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer shadow-sm shrink-0"
              title="Terminali i Sigurt i Bisedës Forenzike"
            >
              <ShieldCheck size={16} className="text-primary-start" />
              <span>Chat</span>
            </button>
          )}

          {/* Butoni Hetuesi (vetëm Ikona) */}
          {activeDossier && (
            <button
              type="button"
              onClick={() => setShowInvestigatorDrawer(true)}
              className="h-9 sm:h-10 w-9 sm:w-10 rounded-xl sm:rounded-2xl bg-rose-600/10 hover:bg-rose-600/20 border border-rose-600/30 text-rose-500 flex items-center justify-center transition-all cursor-pointer shadow-sm shrink-0"
              title="Ditari i Hetuesit Autonom"
            >
              <span className="text-base sm:text-lg select-none">🕵️</span>
            </button>
          )}

          {/* Zgjedhësi i Dosjeve */}
          <div className="relative flex items-center bg-surface border border-main rounded-xl sm:rounded-2xl px-2.5 sm:px-3 py-1 sm:py-1.5 shadow-sm min-w-[140px] flex-1 sm:flex-initial">
            <FolderOpen size={14} className="text-primary-start mr-1.5 sm:mr-2 shrink-0" />
            <select
              value={activeDossier?.id || ''}
              onChange={(e) => {
                const found = dossiersList.find(d => d.id === e.target.value);
                if (found) setActiveDossier(found);
              }}
              className="bg-transparent text-[11px] sm:text-xs font-bold text-text-primary focus:outline-none pr-4 sm:pr-6 cursor-pointer w-full truncate"
              disabled={loadingCases}
            >
              {dossiersList.length === 0 ? (
                <option value="">Nuk ka dosje forenzike</option>
              ) : (
                dossiersList.map(d => (
                  <option key={d.id} value={d.id} className="bg-card text-text-primary">
                    {d.caseNumber}: {d.clientName}
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

          {/* Butoni Fshirjes (vetëm Koshi) */}
          {activeDossier && (
            <button
              type="button"
              onClick={() => handleDeleteDossier(activeDossier.id, activeDossier.clientName)}
              disabled={deletingDossierId === activeDossier.id}
              className="h-9 sm:h-10 w-9 sm:w-10 rounded-xl sm:rounded-2xl bg-rose-600/10 hover:bg-rose-600/20 border border-rose-600/30 text-rose-500 flex items-center justify-center transition-all cursor-pointer shadow-sm shrink-0 disabled:opacity-40"
              title="Fshi Dosjen dhe të Gjitha Provat (Total Cascade Wipeout)"
            >
              {deletingDossierId === activeDossier.id ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
            </button>
          )}

          {/* Butoni Shto (vetëm Plus) */}
          <button
            type="button"
            onClick={() => setShowNewDossierModal(true)}
            className="h-9 sm:h-10 w-9 sm:w-10 rounded-xl sm:rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white flex items-center justify-center shadow-sm transition-all cursor-pointer shrink-0"
            title="Hap Dosje të Re Forenzike"
          >
            <Plus size={16} />
          </button>
        </div>
      </header>

      {/* SHIRITI I NAVIGIMIT MES 5 LABORATORËVE */}
      <nav className="my-4 sm:my-5 w-full">
        <div className="flex items-center bg-surface border border-main rounded-xl sm:rounded-2xl p-1.5 shadow-inner gap-1.5 overflow-x-auto custom-finance-scroll snap-x">
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
            <span className="whitespace-nowrap">2. Audio (Diarizim)</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[20px]">
              {labCounts.AUDIO}
            </span>
          </button>

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
                Përzgjidhni një dosje ekzistuese në menunë sipër ose klikoni butonin plus (+) për të filluar administrimin e provave.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowNewDossierModal(true)}
              className="h-9 sm:h-10 px-4 sm:px-5 rounded-xl sm:rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white text-[11px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all cursor-pointer mt-2"
            >
              <Plus size={16} />
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

      {/* 🏛️ TERMINALI FORENZIK */}
      {isSuperAdmin && activeDossier && (
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

      {/* MODALI I DOSJES SË RE ME CHAIN OF CUSTODY (THEME-AWARE DHE SOLID) */}
      {showNewDossierModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-md flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
          <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden transition-all animate-in fade-in zoom-in-95 duration-200 my-auto">
            
            {/* Header i Modalit */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/80">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-primary-start/10 dark:bg-primary-start/20 text-primary-start flex items-center justify-center">
                  <FolderOpen size={20} />
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-black uppercase tracking-wider text-slate-900 dark:text-slate-100">
                    Regjistrimi i Dosjes Forenzike
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                    Hapja zyrtare e dëshmisë me vërtetim hash dhe zinxhir ruajtjeje
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowNewDossierModal(false)}
                className="w-9 h-9 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                title="Mbyll"
              >
                <X size={18} />
              </button>
            </div>

            {/* Trupi i Formularit */}
            <form onSubmit={handleCreateNewDossier} className="p-6 sm:p-8 space-y-5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
                  <User size={14} className="text-primary-start" />
                  Emri i Plotë i Klientit / Palës <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newDossierForm.clientName}
                  onChange={(e) => setNewDossierForm({ ...newDossierForm, clientName: e.target.value })}
                  placeholder="p.sh. Agim Krasniqi"
                  className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-4 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
                    <Phone size={14} className="text-primary-start" />
                    Telefoni / WhatsApp
                  </label>
                  <input
                    type="text"
                    value={newDossierForm.clientPhone}
                    onChange={(e) => setNewDossierForm({ ...newDossierForm, clientPhone: e.target.value })}
                    placeholder="+383 44 123 456"
                    className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-4 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
                    <Mail size={14} className="text-primary-start" />
                    Adresa e Email-it
                  </label>
                  <input
                    type="email"
                    value={newDossierForm.clientEmail}
                    onChange={(e) => setNewDossierForm({ ...newDossierForm, clientEmail: e.target.value })}
                    placeholder="klienti@shembull.ks"
                    className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-4 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-1.5">
                  <Scale size={14} className="text-primary-start" />
                  Gjykata / Prokuroria Kompetente
                </label>
                <input
                  type="text"
                  value={newDossierForm.courtJurisdiction}
                  onChange={(e) => setNewDossierForm({ ...newDossierForm, courtJurisdiction: e.target.value })}
                  placeholder="Gjykata Themelore Prishtinë"
                  className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-4 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                />
              </div>

              {/* Veprimet / Butonat */}
              <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-col-reverse sm:flex-row items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowNewDossierModal(false)}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors"
                >
                  Anulo
                </button>
                <button
                  type="submit"
                  className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider shadow-lg shadow-primary-start/20 cursor-pointer transition-all hover-lift"
                >
                  Hap Dosjen Zyrtare Forenzike
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