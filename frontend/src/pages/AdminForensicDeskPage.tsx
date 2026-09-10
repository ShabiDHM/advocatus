// FILE: frontend/src/pages/AdminForensicDeskPage.tsx
// PHOENIX PROTOCOL - MASTER FORENSIC STUDIO V11.5 (CLEAN IDENTITY BAR • UNNECESSARY NUMBER PURGED)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS • STREAMLINED STUDIO

import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Mic,
  Video,
  Plus,
  FolderOpen,
  RefreshCw,
  FolderPlus,
  Trash2,
  Loader2,
  X,
  User,
  Phone,
  Mail,
  Scale,
  Pencil
} from 'lucide-react';

import {
  forensicDeskService,
  ForensicDossier,
  LabEvidenceCounts
} from '../services/forensicDeskService';

// Importimi i 3 Laboratorëve Realë Forenzikë të Provave
import { DocumentForensicLab } from '../components/forensics/DocumentForensicLab';
import { AudioForensicLab } from '../components/forensics/AudioForensicLab';
import { VisualForensicLab } from '../components/forensics/VisualForensicLab';

export type ForensicLabType = 'DOCUMENTS' | 'AUDIO' | 'VISUAL';

export const AdminForensicDeskPage: React.FC = () => {
  const [activeLab, setActiveLab] = useState<ForensicLabType>('DOCUMENTS');
  const [activeDossier, setActiveDossier] = useState<ForensicDossier | null>(null);
  
  const [loadingCases, setLoadingCases] = useState<boolean>(false);
  const [dossiersList, setDossiersList] = useState<ForensicDossier[]>([]);
  
  const [showNewDossierModal, setShowNewDossierModal] = useState<boolean>(false);
  const [showEditDossierModal, setShowEditDossierModal] = useState<boolean>(false);
  const [isUpdatingDossier, setIsUpdatingDossier] = useState<boolean>(false);
  const [deletingDossierId, setDeletingDossierId] = useState<string | null>(null);

  const [labCounts, setLabCounts] = useState<LabEvidenceCounts>({
    DOCUMENTS: 0, AUDIO: 0, VISUAL: 0
  });

  const [newDossierForm, setNewDossierForm] = useState({
    clientName: '',
    clientPhone: '',
    clientEmail: '',
    courtJurisdiction: 'Gjykata Themelore Prishtinë'
  });

  const [editDossierForm, setEditDossierForm] = useState({
    clientName: '',
    clientPhone: '',
    clientEmail: '',
    courtJurisdiction: 'Gjykata Themelore Prishtinë',
    caseNumber: ''
  });

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
        clientPhone: newDossierForm.clientPhone,
        clientEmail: newDossierForm.clientEmail,
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

  const handleOpenEditModal = () => {
    if (!activeDossier) return;
    setEditDossierForm({
      clientName: activeDossier.clientName || '',
      clientPhone: activeDossier.clientPhone || '',
      clientEmail: activeDossier.clientEmail || '',
      courtJurisdiction: activeDossier.courtJurisdiction || 'Gjykata Themelore Prishtinë',
      caseNumber: activeDossier.caseNumber || ''
    });
    setShowEditDossierModal(true);
  };

  const handleUpdateDossier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDossier?.id || !editDossierForm.clientName.trim()) return;

    setIsUpdatingDossier(true);
    try {
      await forensicDeskService.updateDossier(activeDossier.id, {
        clientName: editDossierForm.clientName,
        clientPhone: editDossierForm.clientPhone,
        clientEmail: editDossierForm.clientEmail,
        courtJurisdiction: editDossierForm.courtJurisdiction,
        caseNumber: editDossierForm.caseNumber
      });

      setShowEditDossierModal(false);
      await loadExistingDossiers();
    } catch (err: any) {
      console.error("Dështoi përditësimi i dosjes:", err);
      alert(err?.response?.data?.detail || "Dështoi përditësimi i të dhënave të dosjes.");
    } finally {
      setIsUpdatingDossier(false);
    }
  };

  const handleDeleteDossier = async (caseId: string, clientName: string) => {
    if (!caseId) return;
    const confirmDelete = window.confirm(
      `A jeni absolutisht i sigurt që dëshironi të fshini dosjen "${clientName}" dhe TË GJITHA provat, dokumentet, audiot dhe videot e lidhura? Ky veprim është i pakthyeshëm.`
    );
    if (!confirmDelete) return;

    setDeletingDossierId(caseId);
    try {
      await forensicDeskService.deleteDossier(caseId);
      await loadExistingDossiers();
      setActiveDossier(null);
      setLabCounts({ DOCUMENTS: 0, AUDIO: 0, VISUAL: 0 });
    } catch (err: any) {
      console.error("Dështoi fshirja e dosjes:", err);
      alert(err?.response?.data?.detail || "Dështoi fshirja totale e dosjes.");
    } finally {
      setDeletingDossierId(null);
    }
  };

  return (
    <div className="w-full min-h-screen bg-canvas text-text-primary p-2.5 sm:p-5 lg:p-7 max-w-[1750px] mx-auto transition-colors select-none">
      
      {/* PASAPORTA EKZEKUTIVE E LËNDËS */}
      <header className="glass-panel p-3 sm:p-3.5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm flex flex-col gap-2.5">
        <div className="flex items-center justify-between gap-2.5 flex-wrap">
          
          {/* PJESA E MAJTË: ZGJEDHËSI I DOSJES + IDENTITETI I PASTËR I KLIENTIT */}
          <div className="flex items-center gap-2 flex-wrap flex-1 min-w-[200px]">
            
            {/* Zgjedhësi Dropdown */}
            <div className="relative flex items-center bg-surface border border-main rounded-xl px-2.5 py-1.5 shadow-xs">
              <FolderOpen size={14} className="text-primary-start mr-1.5 shrink-0" />
              <select
                value={activeDossier?.id || ''}
                onChange={(e) => {
                  const found = dossiersList.find(d => d.id === e.target.value);
                  if (found) setActiveDossier(found);
                }}
                className="bg-transparent text-xs font-bold text-text-primary focus:outline-none pr-5 cursor-pointer max-w-[180px] sm:max-w-xs truncate"
                disabled={loadingCases}
              >
                {dossiersList.length === 0 ? (
                  <option value="">Nuk ka dosje aktive</option>
                ) : (
                  dossiersList.map(d => (
                    <option key={d.id} value={d.id} className="bg-card text-text-primary">
                      {d.clientName}
                    </option>
                  ))
                )}
              </select>
              <button
                onClick={loadExistingDossiers}
                title="Rifresko"
                className="ml-1 p-0.5 text-text-muted hover:text-text-primary transition-colors cursor-pointer"
              >
                <RefreshCw size={11} className={loadingCases ? 'animate-spin' : ''} />
              </button>
            </div>

            {/* TË DHËNAT ZYRTARE TË PALËS */}
            {activeDossier && (
              <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap text-xs">
                
                {/* Emri i Palës / Klientit */}
                <div className="flex items-center gap-1.5 bg-surface border border-main px-2.5 py-1 rounded-xl shadow-xs">
                  <User size={13} className="text-primary-start shrink-0" />
                  <span className="font-bold text-text-primary">{activeDossier.clientName}</span>
                </div>

                {/* Telefoni / WhatsApp */}
                {activeDossier.clientPhone ? (
                  <a
                    href={`tel:${activeDossier.clientPhone}`}
                    className="flex items-center gap-1.5 bg-surface hover:bg-hover border border-main px-2.5 py-1 rounded-xl text-text-muted hover:text-text-primary transition-colors shadow-xs font-mono"
                    title="Telefono / WhatsApp"
                  >
                    <Phone size={12} className="text-emerald-500 shrink-0" />
                    <span>{activeDossier.clientPhone}</span>
                  </a>
                ) : (
                  <button
                    type="button"
                    onClick={handleOpenEditModal}
                    className="flex items-center gap-1 bg-surface/50 hover:bg-surface border border-dashed border-main hover:border-emerald-500/50 px-2 py-1 rounded-xl text-[11px] text-text-muted hover:text-emerald-500 transition-colors cursor-pointer"
                    title="Plotëso numrin e telefonit"
                  >
                    <Phone size={11} className="text-emerald-500" />
                    <span>+ Shto Tel</span>
                  </button>
                )}

                {/* Email */}
                {activeDossier.clientEmail ? (
                  <a
                    href={`mailto:${activeDossier.clientEmail}`}
                    className="flex items-center gap-1.5 bg-surface hover:bg-hover border border-main px-2.5 py-1 rounded-xl text-text-muted hover:text-text-primary transition-colors shadow-xs font-mono"
                    title="Dërgo Email"
                  >
                    <Mail size={12} className="text-sky-500 shrink-0" />
                    <span className="max-w-[150px] truncate">{activeDossier.clientEmail}</span>
                  </a>
                ) : (
                  <button
                    type="button"
                    onClick={handleOpenEditModal}
                    className="flex items-center gap-1 bg-surface/50 hover:bg-surface border border-dashed border-main hover:border-sky-500/50 px-2 py-1 rounded-xl text-[11px] text-text-muted hover:text-sky-500 transition-colors cursor-pointer"
                    title="Plotëso adresën e email-it"
                  >
                    <Mail size={11} className="text-sky-500" />
                    <span>+ Shto Email</span>
                  </button>
                )}

                {/* Gjykata / Organi Kompetent */}
                <div className="flex items-center gap-1.5 bg-surface border border-main px-2.5 py-1 rounded-xl text-text-muted shadow-xs">
                  <Scale size={13} className="text-primary-start shrink-0" />
                  <span className="font-medium text-text-primary truncate max-w-[220px]">{activeDossier.courtJurisdiction}</span>
                </div>

                {/* BUTONI I EDITIMIT ME LAPS (✏️) */}
                <button
                  type="button"
                  onClick={handleOpenEditModal}
                  className="p-1.5 bg-surface hover:bg-hover border border-main text-text-muted hover:text-primary-start rounded-xl transition-colors cursor-pointer shadow-xs"
                  title="Edito të dhënat e dosjes (Emrin, Telefonin, Email-in, Gjykatën)"
                >
                  <Pencil size={13} />
                </button>
              </div>
            )}
          </div>

          {/* PJESA E DJATHTË: BUTONAT E VEPRIMIT (DOSJE E RE + FSHI) */}
          <div className="flex items-center gap-1.5 shrink-0">
            {activeDossier && (
              <button
                type="button"
                onClick={() => handleDeleteDossier(activeDossier.id, activeDossier.clientName)}
                disabled={deletingDossierId === activeDossier.id}
                className="h-8 w-8 rounded-xl bg-rose-600/10 hover:bg-rose-600/20 border border-rose-600/30 text-rose-500 flex items-center justify-center transition-all cursor-pointer shadow-xs disabled:opacity-40"
                title="Fshi Dosjen dhe të Gjitha Provat"
              >
                {deletingDossierId === activeDossier.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
              </button>
            )}

            <button
              type="button"
              onClick={() => setShowNewDossierModal(true)}
              className="h-8 px-3 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider flex items-center gap-1 shadow-sm transition-all cursor-pointer"
              title="Hap Dosje të Re"
            >
              <Plus size={15} />
              <span className="hidden sm:inline">Dosje e Re</span>
            </button>
          </div>
        </div>
      </header>

      {/* SHIRITI I NAVIGIMIT MES 3 LABORATORËVE TË PROVAVE */}
      <nav className="my-3 sm:my-4 w-full">
        <div className="flex items-center bg-surface border border-main rounded-xl sm:rounded-2xl p-1 sm:p-1.5 shadow-inner gap-1 sm:gap-1.5 overflow-x-auto scrollbar-none snap-x touch-pan-x [-webkit-overflow-scrolling:touch]">
          <button
            type="button"
            onClick={() => setActiveLab('DOCUMENTS')}
            className={`px-3 sm:px-4 py-2 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center min-h-[38px] sm:min-h-[40px] ${
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
            className={`px-3 sm:px-4 py-2 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center min-h-[38px] sm:min-h-[40px] ${
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
            className={`px-3 sm:px-4 py-2 rounded-lg sm:rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 sm:gap-2 transition-all cursor-pointer shrink-0 snap-center min-h-[38px] sm:min-h-[40px] ${
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
        </div>
      </nav>

      {/* TRUPI OPERATIV I ZYRËS - 3 LABORATORËT E PROVAVE */}
      <main className="space-y-4">
        {!activeDossier ? (
          <div className="p-6 sm:p-12 text-center glass-panel rounded-2xl sm:rounded-3xl border border-main bg-card flex flex-col items-center justify-center gap-4">
            <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
              <FolderPlus size={24} className="sm:w-8 sm:h-8" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-bold text-text-primary">Asnjë Dosje nuk është aktive</h3>
              <p className="text-[11px] sm:text-xs text-text-muted mt-1 max-w-xs sm:max-w-sm mx-auto">
                Përzgjidhni një dosje ekzistuese në menunë sipër ose klikoni butonin "Dosje e Re" për të filluar administrimin e provave.
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
              <DocumentForensicLab
                caseId={activeDossier.id}
                clientName={activeDossier.clientName}
                caseNumber={activeDossier.caseNumber}
                onEvidenceChange={refreshEvidenceCounts}
              />
            )}

            {activeLab === 'AUDIO' && (
              <AudioForensicLab caseId={activeDossier.id} onEvidenceChange={refreshEvidenceCounts} />
            )}

            {activeLab === 'VISUAL' && (
              <VisualForensicLab caseId={activeDossier.id} onEvidenceChange={refreshEvidenceCounts} />
            )}
          </>
        )}
      </main>

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
                    Hapje e lëndës ligjore
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

      {/* MODALI I EDITIMIT TË DOSJES EKZISTUESE (✏️) */}
      {showEditDossierModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
          <div className="relative w-full max-w-lg sm:max-w-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden transition-all animate-in fade-in zoom-in-95 duration-200 my-auto max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/80 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-primary-start/10 dark:bg-primary-start/20 text-primary-start flex items-center justify-center shrink-0">
                  <Pencil size={18} />
                </div>
                <div>
                  <h3 className="text-sm sm:text-base font-black uppercase tracking-wider text-slate-900 dark:text-slate-100">
                    Përditëso të Dhënat e Dosjes
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                    Plotësoni telefonin, email-in apo të dhënat e tjera
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowEditDossierModal(false)}
                className="w-8 h-8 rounded-xl flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                title="Mbyll"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleUpdateDossier} className="p-5 sm:p-6 space-y-4 overflow-y-auto custom-finance-scroll flex-1">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                  <User size={13} className="text-primary-start" />
                  Emri i Plotë i Klientit / Palës <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={editDossierForm.clientName}
                  onChange={(e) => setEditDossierForm({ ...editDossierForm, clientName: e.target.value })}
                  placeholder="Emri i klientit"
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
                    value={editDossierForm.clientPhone}
                    onChange={(e) => setEditDossierForm({ ...editDossierForm, clientPhone: e.target.value })}
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
                    value={editDossierForm.clientEmail}
                    onChange={(e) => setEditDossierForm({ ...editDossierForm, clientEmail: e.target.value })}
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
                  value={editDossierForm.courtJurisdiction}
                  onChange={(e) => setEditDossierForm({ ...editDossierForm, courtJurisdiction: e.target.value })}
                  placeholder="Gjykata Themelore Prishtinë"
                  className="w-full bg-slate-50 dark:bg-slate-950/70 border border-slate-300 dark:border-slate-800 focus:border-primary-start rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all font-medium"
                />
              </div>

              <div className="pt-3 border-t border-slate-200 dark:border-slate-800 flex flex-col-reverse sm:flex-row items-center justify-end gap-2.5 shrink-0">
                <button
                  type="button"
                  onClick={() => setShowEditDossierModal(false)}
                  className="w-full sm:w-auto px-4 py-2.5 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors"
                >
                  Anulo
                </button>
                <button
                  type="submit"
                  disabled={isUpdatingDossier}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider shadow-md cursor-pointer transition-all hover-lift flex items-center justify-center gap-2 disabled:opacity-40"
                >
                  {isUpdatingDossier ? <Loader2 size={14} className="animate-spin" /> : null}
                  <span>Ruaj Ndryshimet</span>
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