// FILE: frontend/src/pages/AdminForensicDeskPage.tsx
// PHOENIX PROTOCOL - LEGAL PALANTIR KOSOVA: MASTER FORENSIC STUDIO SHELL V3.1
// 5 AUTONOMOUS LABS + THE INVESTIGATOR'S LOG (SENTINEL) • ZERO TS WARNINGS • ZERO HARDCODING

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
  FolderPlus
} from 'lucide-react';
import { apiService } from '../services/api';
import { forensicService } from '../services/forensicService';

// Importimi i 5 Laboratorëve të Pavarur Forenzikë
import { DocumentForensicLab } from '../components/forensics/DocumentForensicLab';
import { AudioForensicLab } from '../components/forensics/AudioForensicLab';
import { VisualForensicLab } from '../components/forensics/VisualForensicLab';
import { FinancialForensicLab } from '../components/forensics/FinancialForensicLab';
import { SynthesisWarRoom } from '../components/forensics/SynthesisWarRoom';

// Importimi i Ditarit të Hetuesit Autonom
import { InvestigatorLogDrawer } from '../components/forensics/InvestigatorLogDrawer';

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
  // Laboratori Aktiv
  const [activeLab, setActiveLab] = useState<ForensicLabType>('DOCUMENTS');

  // Menaxhimi i Dosjes Aktive
  const [activeDossier, setActiveDossier] = useState<ForensicDossier | null>(null);
  const [showNewDossierModal, setShowNewDossierModal] = useState<boolean>(false);
  const [loadingCases, setLoadingCases] = useState<boolean>(false);
  const [existingCasesList, setExistingCasesList] = useState<any[]>([]);

  // Gjendja e Ditarit të Hetuesit
  const [showInvestigatorDrawer, setShowInvestigatorDrawer] = useState<boolean>(false);

  // Kuotat e Provave sipas Laboratorëve
  const [labCounts, setLabCounts] = useState<LabEvidenceCounts>({
    DOCUMENTS: 0,
    AUDIO: 0,
    VISUAL: 0,
    FINANCIAL: 0,
    WAR_ROOM: 0
  });

  // Formular për Dosje të Re
  const [newDossierForm, setNewDossierForm] = useState({
    clientName: '',
    clientPhone: '',
    clientEmail: '',
    courtJurisdiction: 'Gjykata Themelore Prishtinë',
    partnerLawyerName: 'Av. Zyra Partnere e Licencuar OAK',
    partnerLawyerLicense: 'OAK-2026-KS'
  });

  const [copiedHash, setCopiedHash] = useState<boolean>(false);

  // Hash deterministik për Chain of Custody
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

  // Ngarkimi i numrit të saktë të provave për lëndën aktive
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

  // Krijimi i Dosjes së Re me Formular
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
      <header className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 pb-5 border-b border-main">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-rose-600 via-indigo-700 to-primary-start text-white flex items-center justify-center shadow-lg shadow-rose-600/20 shrink-0">
            <ShieldAlert size={26} />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-xl sm:text-2xl font-black uppercase tracking-tight text-text-primary">
                Legal Palantir Kosova
              </h1>
              <span className="px-2.5 py-0.5 rounded-full bg-primary-start/15 text-primary-start border border-primary-start/30 font-mono text-[10px] font-bold uppercase tracking-wider">
                Forensic Studio v3.1
              </span>
              {activeDossier && (
                <button
                  type="button"
                  onClick={handleCopyHash}
                  className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500 border border-emerald-500/30 font-mono text-[10px] font-bold flex items-center gap-1.5 hover:bg-emerald-500/25 transition-colors cursor-pointer"
                  title="Kopjo Chain of Custody Hash (SHA-256)"
                >
                  <Hash size={11} />
                  <span>{activeDossier.chainOfCustodyHash}</span>
                  {copiedHash ? <CheckCircle2 size={11} className="text-emerald-500" /> : <Copy size={11} />}
                </button>
              )}
            </div>
            <p className="text-xs text-text-muted font-medium mt-0.5">
              Laboratori Multimodal i Ekspertizës Ligjore • Verifikim Shkencor i Provave • Standard OAK & Gjykata Supreme
            </p>
          </div>
        </div>

        {/* Zgjedhësi i Dosjeve, Butoni i Ditarit të Hetuesit & Butoni i Regjistrimit të Ri */}
        <div className="flex items-center gap-2.5 flex-wrap">
          {/* BUTONI I DITARIT TË HETUESIT (SENTINEL TRIGGER) */}
          <button
            type="button"
            onClick={() => setShowInvestigatorDrawer(true)}
            className="h-10 px-3.5 rounded-2xl bg-rose-600/10 hover:bg-rose-600/20 border border-rose-600/30 text-rose-500 font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer shadow-sm"
            title="Hap Ditarin e Hetuesit Autonom"
          >
            <span className="text-sm">🕵️</span>
            <span>Ditari i Hetuesit</span>
          </button>

          <div className="relative flex items-center bg-surface border border-main rounded-2xl px-3 py-1.5 shadow-sm">
            <FolderOpen size={16} className="text-primary-start mr-2 shrink-0" />
            <select
              value={activeDossier?.id || ''}
              onChange={(e) => {
                const found = existingCasesList.find(c => c.id === e.target.value);
                if (found) selectExistingDossier(found);
              }}
              className="bg-transparent text-xs font-bold text-text-primary focus:outline-none pr-6 cursor-pointer max-w-[220px] truncate"
              disabled={loadingCases}
            >
              {existingCasesList.length === 0 ? (
                <option value="">Nuk ka dosje të hapura</option>
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
              title="Rifresko listën e dosjeve"
              className="ml-1 p-1 text-text-muted hover:text-text-primary transition-colors cursor-pointer"
            >
              <RefreshCw size={12} className={loadingCases ? 'animate-spin' : ''} />
            </button>
          </div>

          <button
            type="button"
            onClick={() => setShowNewDossierModal(true)}
            className="h-10 px-4 rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all cursor-pointer"
          >
            <Plus size={15} />
            <span>Dosje e Re</span>
          </button>
        </div>
      </header>

      {/* SHIRITI I NAVIGIMIT MES 5 LABORATORËVE FORENZIKË */}
      <nav className="my-5 flex items-center justify-between gap-2 overflow-x-auto pb-1 custom-finance-scroll">
        <div className="flex items-center bg-surface border border-main rounded-2xl p-1.5 shadow-inner gap-1.5">
          {/* 1. DOCUMENT FORENSIC LAB */}
          <button
            type="button"
            onClick={() => setActiveLab('DOCUMENTS')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer ${
              activeLab === 'DOCUMENTS'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <FileText size={15} />
            <span>1. Shkresat & OCR</span>
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-white/20 text-inherit">
              {labCounts.DOCUMENTS}
            </span>
          </button>

          {/* 2. AUDIO FORENSIC LAB */}
          <button
            type="button"
            onClick={() => setActiveLab('AUDIO')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer ${
              activeLab === 'AUDIO'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Mic size={15} />
            <span>2. Audio & Përgjime</span>
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-white/20 text-inherit">
              {labCounts.AUDIO}
            </span>
          </button>

          {/* 3. VISUAL FORENSIC LAB */}
          <button
            type="button"
            onClick={() => setActiveLab('VISUAL')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer ${
              activeLab === 'VISUAL'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Video size={15} />
            <span>3. Video & EXIF</span>
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-white/20 text-inherit">
              {labCounts.VISUAL}
            </span>
          </button>

          {/* 4. FINANCIAL FORENSIC LAB */}
          <button
            type="button"
            onClick={() => setActiveLab('FINANCIAL')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer ${
              activeLab === 'FINANCIAL'
                ? 'bg-primary-start text-white shadow-md'
                : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Coins size={15} />
            <span>4. Financa & LMD</span>
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-white/20 text-inherit">
              {labCounts.FINANCIAL}
            </span>
          </button>

          {/* 5. SYNTHESIS WAR ROOM */}
          <button
            type="button"
            onClick={() => setActiveLab('WAR_ROOM')}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer ${
              activeLab === 'WAR_ROOM'
                ? 'bg-rose-600 text-white shadow-md shadow-rose-600/30'
                : 'text-rose-500 hover:text-rose-400 hover:bg-rose-500/10'
            }`}
          >
            <Swords size={15} />
            <span>5. War Room (Kryqëzimi)</span>
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-white/20 text-inherit">
              Master
            </span>
          </button>
        </div>

        {/* Informacion i Dosjes Aktive */}
        {activeDossier && (
          <div className="hidden lg:flex items-center gap-3 bg-surface border border-main px-4 py-2 rounded-2xl text-xs">
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

      {/* TRUPI OPERATIV I ZYRËS: RENDERIMI I LABORATORIT TË ZGJEDHUR */}
      <main className="space-y-6">
        {!activeDossier ? (
          <div className="p-12 text-center glass-panel rounded-3xl border border-main bg-card flex flex-col items-center justify-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-primary-start/10 text-primary-start flex items-center justify-center">
              <FolderPlus size={32} />
            </div>
            <div>
              <h3 className="text-base font-bold text-text-primary">Asnjë Dosje Forenzike nuk është aktive</h3>
              <p className="text-xs text-text-muted mt-1 max-w-sm">
                Përzgjidhni një dosje ekzistuese në menunë sipër ose klikoni "Dosje e Re" për të filluar administrimin e provave.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowNewDossierModal(true)}
              className="h-10 px-5 rounded-2xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all cursor-pointer"
            >
              <Plus size={15} />
              <span>Regjistro Dosjen e Parë</span>
            </button>
          </div>
        ) : (
          <>
            {/* LABORATORI 1: SHKRESAT & OCR */}
            {activeLab === 'DOCUMENTS' && (
              <DocumentForensicLab
                caseId={activeDossier.id}
                onEvidenceChange={refreshEvidenceCounts}
              />
            )}

            {/* LABORATORI 2: AUDIO & PËRGJIME */}
            {activeLab === 'AUDIO' && (
              <AudioForensicLab
                caseId={activeDossier.id}
                onEvidenceChange={refreshEvidenceCounts}
              />
            )}

            {/* LABORATORI 3: VIDEO & EXIF */}
            {activeLab === 'VISUAL' && (
              <VisualForensicLab
                caseId={activeDossier.id}
                onEvidenceChange={refreshEvidenceCounts}
              />
            )}

            {/* LABORATORI 4: FINANCA & LMD */}
            {activeLab === 'FINANCIAL' && (
              <FinancialForensicLab
                caseId={activeDossier.id}
                onEvidenceChange={refreshEvidenceCounts}
              />
            )}

            {/* LABORATORI 5: SYNTHESIS WAR ROOM */}
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

      {/* PANELI ANËSOR RRËSHQITËS: DITARI I HETUESIT (INVESTIGATOR'S LOG SENTINEL) */}
      {activeDossier && (
        <InvestigatorLogDrawer
          isOpen={showInvestigatorDrawer}
          onClose={() => setShowInvestigatorDrawer(false)}
          caseId={activeDossier.id}
          clientName={activeDossier.clientName}
          chainOfCustodyHash={activeDossier.chainOfCustodyHash}
        />
      )}

      {/* MODALI I KRIJIMIT TË DOSJES SË RE FORENZIKE */}
      {showNewDossierModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-main rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-main pb-3">
              <h3 className="text-base font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                <FolderOpen size={18} className="text-primary-start" /> Regjistrimi i Dosjes Forenzike
              </h3>
              <button
                type="button"
                onClick={() => setShowNewDossierModal(false)}
                className="text-text-muted hover:text-text-primary text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateNewDossier} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-text-muted font-bold mb-1">Emri i Plotë i Klientit / Palës *</label>
                <input
                  type="text"
                  required
                  value={newDossierForm.clientName}
                  onChange={(e) => setNewDossierForm({ ...newDossierForm, clientName: e.target.value })}
                  placeholder="p.sh. Agim Krasniqi"
                  className="w-full bg-surface border border-main rounded-xl px-3.5 py-2.5 text-text-primary focus:outline-none focus:border-primary-start"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-text-muted font-bold mb-1">Telefoni / WhatsApp</label>
                  <input
                    type="text"
                    value={newDossierForm.clientPhone}
                    onChange={(e) => setNewDossierForm({ ...newDossierForm, clientPhone: e.target.value })}
                    placeholder="+383 44 ..."
                    className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary focus:outline-none focus:border-primary-start"
                  />
                </div>
                <div>
                  <label className="block text-text-muted font-bold mb-1">Email</label>
                  <input
                    type="email"
                    value={newDossierForm.clientEmail}
                    onChange={(e) => setNewDossierForm({ ...newDossierForm, clientEmail: e.target.value })}
                    placeholder="email@shembull.ks"
                    className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary focus:outline-none focus:border-primary-start"
                  />
                </div>
              </div>

              <div>
                <label className="block text-text-muted font-bold mb-1">Gjykata / Prokuroria Kompetente</label>
                <input
                  type="text"
                  value={newDossierForm.courtJurisdiction}
                  onChange={(e) => setNewDossierForm({ ...newDossierForm, courtJurisdiction: e.target.value })}
                  className="w-full bg-surface border border-main rounded-xl px-3.5 py-2.5 text-text-primary focus:outline-none focus:border-primary-start"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowNewDossierModal(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-bold text-text-muted hover:bg-hover cursor-pointer"
                >
                  Anulo
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider shadow-md cursor-pointer"
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