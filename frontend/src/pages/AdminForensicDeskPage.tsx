// FILE: frontend/src/pages/AdminForensicDeskPage.tsx
// PHOENIX PROTOCOL - MASTER FORENSIC STUDIO V8.0 (WAR ROOM COMPLETELY ELIMINATED)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS • 4 PURE FORENSIC LABS

import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  FileText,
  Mic,
  Video,
  Coins,
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

// Importimi i 4 Laboratorëve të Pavarur Forenzikë të Provave
import { DocumentForensicLab } from '../components/forensics/DocumentForensicLab';
import { AudioForensicLab } from '../components/forensics/AudioForensicLab';
import { VisualForensicLab } from '../components/forensics/VisualForensicLab';
import { FinancialForensicLab } from '../components/forensics/FinancialForensicLab';

// Importimi i Terminalit të Bisedës Forenzike
import { ForensicInterrogationDrawer } from '../components/forensics/ForensicInterrogationDrawer';

export type ForensicLabType = 'DOCUMENTS' | 'AUDIO' | 'VISUAL' | 'FINANCIAL';

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
  const [showChatDrawer, setShowChatDrawer] = useState<boolean>(false);
  const [deletingDossierId, setDeletingDossierId] = useState<string | null>(null);

  const [labCounts, setLabCounts] = useState<LabEvidenceCounts>({
    DOCUMENTS: 0, AUDIO: 0, VISUAL: 0, FINANCIAL: 0
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
      `A jeni absolutisht i sigurt që dëshironi të fshini dosjen "${clientName}" dhe TË GJITHA provat, dokumentet, audiot, videot, financat dhe bisedat e lidhura? Ky veprim është i pakthyeshëm.`
    );
    if (!confirmDelete) return;

    setDeletingDossierId(caseId);
    try {
      await forensicDeskService.deleteDossier(caseId);
      await loadExistingDossiers();
      setActiveDossier(null);
      setLabCounts({ DOCUMENTS: 0, AUDIO: 0, VISUAL: 0, FINANCIAL: 0 });
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
    <div className="w-full min-h-screen bg-canvas text-text-primary p-2.5 sm:p-5 lg:p-8 max-w-[1750px] mx-auto transition-colors select-none">
      
      {/* KOKA SUPREME: IDENTITETI DHE KONTROLLI I DOSJES FORENZIKE */}
      <header className="flex flex-col gap-3 sm:gap-4 pb-4 sm:pb-5 border-b border-main">
        <div className="flex items-center justify-between gap-2.5">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div className="w-9 h-9 sm:w-11 sm:h-11 rounded-xl sm:rounded-2xl bg-gradient-to-br from-rose-600 via-indigo-700 to-primary-start text-white flex items-center justify-center shadow-md shrink-0">
              <ShieldAlert size={20} className="sm:w-6 sm:h-6" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-sm sm:text-lg md:text-2xl font-black uppercase tracking-tight text-text-primary leading-tight truncate">
                  Laboratori Forenzik
                </h1>
                
                {activeDossier && (
                  <button
                    type="button"
                    onClick={handleCopyHash}
                    className="px-2 py-0.5 rounded-full bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-500 border border-emerald-500/30 font-mono text-[9px] sm:text-[10px] font-bold flex items-center gap-1 transition-colors cursor-pointer shrink-0"
                    title={`Chain of Custody Hash: ${activeDossier.chainOfCustodyHash} (Kliko për ta kopjuar)`}
                  >
                    <Hash size={10} className="shrink-0" />
                    <span>{copiedHash ? 'U Kopjua!' : 'Vula'}</span>
                    {copiedHash ? <CheckCircle2 size={10} className="text-emerald-500 shrink-0" /> : <Copy size={10} className="shrink-0" />}
                  </button>
                )}
              </div>
              <p className="hidden sm:block text-[11px] sm:text-xs text-text-muted font-medium mt-0.5 truncate">
                Qendra Administrative e Ekspertizës dhe Verifikimit Forenzik të Provave
              </p>
            </div>
          </div>
        </div>

        {/* Rreshti 2: Paneli i Kontrollit (Zgjedhësi + Chat + Fshirja + Shto) */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="relative flex items-center bg-surface border border-main rounded-xl sm:rounded-2xl px-2 sm:px-3 py-1 sm:py-1.5 shadow-sm flex-1 min-w-[150px] max-w-full sm:max-w-xs">
            <FolderOpen size={14} className="text-primary-start mr-1.5 shrink-0" />
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
                  <option 
                    key={d.id} 
                    value={d.id} 
                    className="bg-card text-text-primary"
                    title={`Numri Zyrtar: ${d.caseNumber}`}
                  >
                    FOR: {d.clientName}
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

          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {isSuperAdmin && activeDossier && (
              <button
                type="button"
                onClick={() => setShowChatDrawer(true)}
                className="h-9 sm:h-10 px-2.5 sm:px-3.5 rounded-xl sm:rounded-2xl bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start font-bold text-[11px] sm:text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer shadow-sm shrink-0"
                title="Terminali i Sigurt i Bisedës Forenzike"
              >
                <ShieldCheck size={15} className="text-primary-start" />
                <span className="hidden xs:inline">Chat</span>
              </button>
            )}

            {activeDossier && (
              <button
                type="button"
                onClick={() => handleDeleteDossier(activeDossier.id, activeDossier.clientName)}
                disabled={deletingDossierId === activeDossier.id}
                className="h-9 sm:h-10 w-9 sm:w-10 rounded-xl sm:rounded-2xl bg-rose-600/10 hover:bg-rose-600/20 border border-rose-600/30 text-rose-500 flex items-center justify-center transition-all cursor-pointer shadow-sm shrink-0 disabled:opacity-40"
                title="Fshi Dosjen dhe të Gjitha Provat (Total Cascade Wipeout)"
              >
                {deletingDossierId === activeDossier.id ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
              </button>
            )}

            <button
              type="button"
              onClick={() => setShowNewDossierModal(true)}
              className="h-9 sm:h-10 w-9 sm:w-10 rounded-xl sm:rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white flex items-center justify-center shadow-sm transition-all cursor-pointer shrink-0"
              title="Hap Dosje të Re Forenzike"
            >
              <Plus size={16} />
            </button>
          </div>
        </div>
      </header>

      {/* SHIRITI I NAVIGIMIT MES 4 LABORATORËVE TË PROVAVE */}
      <nav className="my-3 sm:my-5 w-full">
        <div className="flex items-center bg-surface border border-main rounded-xl sm:rounded-2xl p-1 sm:p-1.5 shadow-inner gap-1 sm:gap-1.5 overflow-x-auto scrollbar-none snap-x touch-pan-x [-webkit-overflow-scrolling:touch]">
          <button
            type="button"
            onClick={() => setActiveLab('DOCUMENTS')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center min-h-[40px] sm:min-h-[44px] ${
              activeLab === 'DOCUMENTS'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <FileText size={14} className="shrink-0" />
            <span className="whitespace-nowrap">1. Shkresat</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[18px]">
              {labCounts.DOCUMENTS}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveLab('AUDIO')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center min-h-[40px] sm:min-h-[44px] ${
              activeLab === 'AUDIO'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Mic size={14} className="shrink-0" />
            <span className="whitespace-nowrap">2. Audio</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[18px]">
              {labCounts.AUDIO}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveLab('VISUAL')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center min-h-[40px] sm:min-h-[44px] ${
              activeLab === 'VISUAL'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Video size={14} className="shrink-0" />
            <span className="whitespace-nowrap">3. Video</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[18px]">
              {labCounts.VISUAL}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveLab('FINANCIAL')}
            className={`px-3 sm:px-4 py-2 sm:py-2.5 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center min-h-[40px] sm:min-h-[44px] ${
              activeLab === 'FINANCIAL'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Coins size={14} className="shrink-0" />
            <span className="whitespace-nowrap">4. Financa</span>
            <span className="px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-black/10 dark:bg-white/20 text-inherit flex items-center justify-center min-w-[18px]">
              {labCounts.FINANCIAL}
            </span>
          </button>
        </div>

        {activeDossier && (
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 bg-surface border border-main px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl sm:rounded-2xl text-[11px] sm:text-xs mt-2.5 w-fit">
            <div className="flex items-center gap-1.5">
              <UserCheck size={13} className="text-primary-start" />
              <span className="text-text-muted">Palë:</span>
              <span className="font-bold text-text-primary">{activeDossier.clientName}</span>
            </div>
            <span className="text-text-muted hidden sm:inline">|</span>
            <div className="flex items-center gap-1.5">
              <Building2 size={13} className="text-primary-start" />
              <span className="text-text-muted">Organi:</span>
              <span className="font-bold text-text-primary">{activeDossier.courtJurisdiction}</span>
            </div>
          </div>
        )}
      </nav>

      {/* TRUPI OPERATIV I ZYRËS - 4 LABORATORËT E PROVAVE */}
      <main className="space-y-4 sm:space-y-6">
        {!activeDossier ? (
          <div className="p-6 sm:p-12 text-center glass-panel rounded-2xl sm:rounded-3xl border border-main bg-card flex flex-col items-center justify-center gap-4">
            <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
              <FolderPlus size={24} className="sm:w-8 sm:h-8" />
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
              className="h-10 px-5 rounded-xl sm:rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all cursor-pointer mt-1"
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
          </>
        )}
      </main>

      {/* TERMINALI FORENZIK */}
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

      {/* MODALI I DOSJES SË RE */}
      {showNewDossierModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
          <div className="relative w-full max-w-lg sm:max-w-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden transition-all animate-in fade-in zoom-in-95 duration-200 my-auto max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/80 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-primary-start/10 dark:bg-primary-start/20 text-primary-start flex items-center justify-center shrink-0">
                  <FolderOpen size={18} />
                </div>
                <div>
                  <h3 className="text-sm sm:text-base font-black uppercase tracking-wider text-slate-900 dark:text-slate-100">
                    Regjistrimi i Dosjes
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                    Hapje e lëndës me vërtetim hash
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowNewDossierModal(false)}
                className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                title="Mbyll"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateNewDossier} className="p-5 sm:p-6 space-y-4 overflow-y-auto custom-finance-scroll flex-1">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                  <User size={13} className="text-primary-start" />
                  Emri i Plotë i Klientit / Palës <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={newDossierForm.clientName}
                  onChange={(e) => setNewDossierForm({ ...newDossierForm, clientName: e.target.value })}
                  placeholder="p.sh. Agim Krasniqi"
                  className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                    <Phone size={13} className="text-primary-start" />
                    Telefoni / WhatsApp
                  </label>
                  <input
                    type="text"
                    value={newDossierForm.clientPhone}
                    onChange={(e) => setNewDossierForm({ ...newDossierForm, clientPhone: e.target.value })}
                    placeholder="+383 44 ..."
                    className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                    <Mail size={13} className="text-primary-start" />
                    Adresa e Email-it
                  </label>
                  <input
                    type="email"
                    value={newDossierForm.clientEmail}
                    onChange={(e) => setNewDossierForm({ ...newDossierForm, clientEmail: e.target.value })}
                    placeholder="klienti@shembull.ks"
                    className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                  <Scale size={13} className="text-primary-start" />
                  Gjykata / Prokuroria Kompetente
                </label>
                <input
                  type="text"
                  value={newDossierForm.courtJurisdiction}
                  onChange={(e) => setNewDossierForm({ ...newDossierForm, courtJurisdiction: e.target.value })}
                  placeholder="Gjykata Themelore Prishtinë"
                  className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                />
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex flex-col-reverse sm:flex-row items-center justify-end gap-2.5 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowNewDossierModal(false)}
                  className="w-full sm:w-auto px-4 py-2.5 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors"
                >
                  Anulo
                </button>
                <button
                  type="submit"
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider shadow-md cursor-pointer transition-all hover-lift"
                >
                  Hap Dosjen
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