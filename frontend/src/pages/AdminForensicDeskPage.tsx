// FILE: frontend/src/pages/AdminForensicDeskPage.tsx
// PHOENIX PROTOCOL - ADMIN FORENSIC COCKPIT V1.1 (ZERO TS WARNINGS • PRODUCTION-READY CLEAN BUILD)

import React, { useState, useRef, useMemo } from 'react';
import { 
  ShieldCheck, Upload, FileText, Send, Sparkles, 
  Copy, CheckCircle2, Loader2, ArrowRight, User, Phone, 
  Mail, MapPin, Scale, FolderArchive, FileCheck
} from 'lucide-react';
import { apiService } from '../services/api';

interface ManagedClientOrder {
  clientName: string;
  clientPhone: string;
  clientEmail: string;
  caseDomain: string;
  courtJurisdiction: string;
  notes: string;
  partnerLawyerName: string;
  partnerLawyerLicense: string;
}

type OperationalTab = 'INTAKE' | 'AUDIT' | 'DRAFTING' | 'DISPATCH';

export const AdminForensicDeskPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<OperationalTab>('INTAKE');

  // Formularët e Klientit
  const [clientData, setClientData] = useState<ManagedClientOrder>({
    clientName: '',
    clientPhone: '',
    clientEmail: '',
    caseDomain: 'AUTOMATIC',
    courtJurisdiction: 'Gjykata Themelore Prishtinë',
    notes: '',
    partnerLawyerName: 'Av. Zyra Partner e Licencuar OAK',
    partnerLawyerLicense: 'OAK-2026-KS'
  });

  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [createdCaseId, setCreatedCaseId] = useState<string | null>(null);
  const [isProcessingIntake, setIsProcessingIntake] = useState<boolean>(false);
  const [intakeProgressText, setIntakeProgressText] = useState<string>('');

  // Gjendja e Auditimit
  const [auditText, setAuditText] = useState<string>('');
  const [isAuditing, setIsAuditing] = useState<boolean>(false);

  // Gjendja e Shkresave të Hartuara
  const [selectedActType, setSelectedActType] = useState<string>('KALLËZIM_PENAL');
  const [draftedActText, setDraftedActText] = useState<string>('');
  const [isDrafting, setIsDrafting] = useState<boolean>(false);

  // Gjendja e Dispatch-it (Dërgimit)
  const [copiedWhatsAppMsg, setCopiedWhatsAppMsg] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileDrop = (files: FileList | null) => {
    if (!files) return;
    const valid = Array.from(files).filter(f => !f.name.startsWith('.'));
    setUploadedFiles(prev => [...prev, ...valid]);
  };

  // 1. INTAKE OPERATIV — Krijimi i lëndës së menaxhuar dhe ngarkimi i skedarëve
  const handleExecuteIntake = async () => {
    if (!clientData.clientName.trim() || uploadedFiles.length === 0) {
      alert("Ju lutem shënoni emrin e klientit dhe shtoni të paktën 1 dokument/foto.");
      return;
    }

    setIsProcessingIntake(true);
    setIntakeProgressText("Duke krijuar dosjen e menaxhuar...");

    try {
      const newCase = await apiService.createCase({
        title: `Lënda e Menaxhuar: ${clientData.clientName}`,
        client_name: clientData.clientName,
        case_number: `ADM-${Date.now().toString().slice(-6)}`,
        case_domain: clientData.caseDomain === 'AUTOMATIC' ? undefined : clientData.caseDomain,
        client_position: 'PLAINTIFF'
      } as any);

      const targetCaseId = newCase.id;
      setCreatedCaseId(targetCaseId);

      for (let i = 0; i < uploadedFiles.length; i++) {
        const file = uploadedFiles[i];
        setIntakeProgressText(`Duke ngarkuar dhe bërë OCR për: ${file.name} (${i + 1}/${uploadedFiles.length})...`);
        await apiService.uploadDocument(targetCaseId, file);
      }

      setIntakeProgressText("Intake përfundoi me sukses! Dosja u krijua dhe shkresat u indeksuan.");
      setTimeout(() => {
        setIsProcessingIntake(false);
        setActiveTab('AUDIT');
      }, 1500);
    } catch (err: any) {
      console.error("Intake failure:", err);
      alert(err?.response?.data?.detail || "Dështoi krijimi i dosjes operative.");
      setIsProcessingIntake(false);
    }
  };

  // 2. AUDITIMI FORENZIK ME MODELIN ELITAR CLAUDE SONNET
  const handleRunForensicAudit = async () => {
    if (!createdCaseId || isAuditing) return;

    setIsAuditing(true);
    setAuditText('');

    try {
      const prompt = `[DIREKTIVË E KONSULENCËS SË GJYKATËS SUPREME]
Kryej auditimin e plotë doktrinar dhe autopsinë forenzike të fashikullit të klientit ${clientData.clientName} sipas të 8 seksioneve të plota pa asnjë shkurtime. Përcakto saktësisht të gjitha shkeljet procedurale, veprat penale dhe shanset e fitores.`;

      const stream = apiService.sendChatMessageStream(createdCaseId, prompt, undefined, 'ks', 'DEEP', 'automatic');

      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setAuditText(acc);
      }
    } catch (err) {
      console.error("Audit error:", err);
      alert("Dështoi ekzekutimi i auditimit.");
    } finally {
      setIsAuditing(false);
    }
  };

  // 3. HARTIMI AUTOMATIK I SHKRESËS GJYQËSORE
  const handleGenerateJudicialAct = async () => {
    if (!createdCaseId || isDrafting) return;

    setIsDrafting(true);
    setDraftedActText('');

    try {
      const draftingPrompts: Record<string, string> = {
        KALLËZIM_PENAL: `Harto Kallëzimin Penal të plotë, solemn dhe të detyrueshëm proceduralisht për Prokurorinë Kompetente, duke përfshirë të gjitha provat e administruara në dosje për klientin ${clientData.clientName}.`,
        ANKESË_CIVILE: `Harto Ankesën zyrtare kundër vendimit të atakuar drejtuar Gjykatës së Apelit, me të gjitha shkaqet e ankesës (neni 182 LPK, vërtetimi i gabuar i gjendjes faktike dhe zbatimi i gabuar i ligjit).`,
        MASË_EMERGJENTE: `Harto Kërkesën për Lëshimin e Masës Emergjente të Mbrojtjes brenda 24 orëve sipas Neneve 188 dhe 221 të KPPRK-së për të ndërprerë dëmin e pariparueshëm.`,
        PRAPËSIM_PADI: `Harto Përgjigjen në Padi (Prapësimin) të plotë duke kundërshtuar bazën juridike dhe lartësinë e kërkesëpadisë së palës kundërshtare.`
      };

      const selectedPrompt = draftingPrompts[selectedActType] || draftingPrompts['KALLËZIM_PENAL'];
      const stream = apiService.sendChatMessageStream(createdCaseId, selectedPrompt, undefined, 'ks', 'DEEP', 'automatic');

      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setDraftedActText(acc);
      }
    } catch (err) {
      console.error("Drafting error:", err);
      alert("Dështoi hartimi i aktit procedural.");
    } finally {
      setIsDrafting(false);
    }
  };

  // 4. MESAZHI I GATSHËM PËR WHATSAPP
  const whatsAppMessage = useMemo(() => {
    return (
      `Përshëndetje ${clientData.clientName},\n\n` +
      `Zyra jonë ligjore ka përmbyllur me sukses Auditimin Doktrinar dhe Përgatitjen e Dosjes suaj Gjyqësore.\n\n` +
      `📌 LËNDA: ${clientData.clientName}\n` +
      `🏛️ GJYKATA/ORGANI: ${clientData.courtJurisdiction}\n` +
      `⚖️ AVOKATI PARTNER: ${clientData.partnerLawyerName} (Licenca: ${clientData.partnerLawyerLicense})\n\n` +
      `Raporti juaj Master përmban 8 Seksione të plota të autopsisë së provave dhe shkeljeve procedurale, së bashku me shkresat e gatshme procedurale.\n\n` +
      `Dosja e plotë e përgatitur në format zyrtar PDF po ju bashkëngjitet këtij mesazhi.\n\n` +
      `Me respekt,\n` +
      `Juristi AI — Qendra Operative e Inteligjencës Ligjore`
    );
  }, [clientData]);

  const handleCopyWhatsApp = () => {
    navigator.clipboard.writeText(whatsAppMessage);
    setCopiedWhatsAppMsg(true);
    setTimeout(() => setCopiedWhatsAppMsg(false), 3000);
  };

  return (
    <div className="w-full min-h-screen bg-canvas text-text-primary p-3 sm:p-6 lg:p-10 max-w-7xl mx-auto select-none">
      {/* KOKA E ZYRËS OPERATIVE */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-main">
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary-start to-indigo-700 text-white flex items-center justify-center shadow-lg shadow-primary-start/20">
            <ShieldCheck size={26} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg sm:text-2xl font-black uppercase tracking-tight text-text-primary">
                Zyra Operative Forenzike
              </h1>
              <span className="px-2.5 py-0.5 rounded-full bg-rose-500/15 text-rose-500 border border-rose-500/30 font-mono text-[10px] font-bold uppercase tracking-wider">
                Admin Exclusive
              </span>
            </div>
            <p className="text-xs sm:text-sm text-text-muted font-medium mt-0.5">
              Intake i Porosive të Jashtme (WhatsApp/Email) • Inteligjencë e Thellë Doktrinare • Shkresa Gjyqësore
            </p>
          </div>
        </div>

        {/* Shirit Navigimi Operativ mes 4 Fazave */}
        <div className="flex items-center bg-surface border border-main rounded-2xl p-1 shadow-inner gap-1 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('INTAKE')}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer ${
              activeTab === 'INTAKE' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Upload size={14} /> 1. Intake
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('AUDIT')}
            disabled={!createdCaseId}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed ${
              activeTab === 'AUDIT' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Scale size={14} /> 2. Auditim
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('DRAFTING')}
            disabled={!createdCaseId}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed ${
              activeTab === 'DRAFTING' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <FileText size={14} /> 3. Shkresat
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('DISPATCH')}
            disabled={!createdCaseId}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed ${
              activeTab === 'DISPATCH' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary hover:bg-hover'
            }`}
          >
            <Send size={14} /> 4. Pakoja
          </button>
        </div>
      </header>

      {/* TRUPI OPERATIV I PANELIT */}
      <main className="py-6">
        {/* FAZA 1: INTAKE I POROSISË SË JASHTME */}
        {activeTab === 'INTAKE' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-5 space-y-4 glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm">
              <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2 border-b border-main pb-3">
                <User size={16} className="text-primary-start" /> Të Dhënat e Klientit të Jashtëm
              </h3>

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-text-muted font-bold mb-1">Emri dhe Mbiemri i Klientit *</label>
                  <input
                    type="text"
                    value={clientData.clientName}
                    onChange={(e) => setClientData({ ...clientData, clientName: e.target.value })}
                    placeholder="p.sh. Shaban Bala"
                    className="w-full bg-surface border border-main rounded-xl px-3.5 py-2.5 text-text-primary font-medium focus:outline-none focus:border-primary-start"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-text-muted font-bold mb-1">Telefoni / WhatsApp</label>
                    <div className="relative">
                      <Phone size={14} className="absolute left-3 top-3 text-text-muted" />
                      <input
                        type="text"
                        value={clientData.clientPhone}
                        onChange={(e) => setClientData({ ...clientData, clientPhone: e.target.value })}
                        placeholder="+383 44 ..."
                        className="w-full bg-surface border border-main rounded-xl pl-9 pr-3 py-2.5 text-text-primary font-medium focus:outline-none focus:border-primary-start"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-text-muted font-bold mb-1">Email</label>
                    <div className="relative">
                      <Mail size={14} className="absolute left-3 top-3 text-text-muted" />
                      <input
                        type="email"
                        value={clientData.clientEmail}
                        onChange={(e) => setClientData({ ...clientData, clientEmail: e.target.value })}
                        placeholder="klienti@..."
                        className="w-full bg-surface border border-main rounded-xl pl-9 pr-3 py-2.5 text-text-primary font-medium focus:outline-none focus:border-primary-start"
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <label className="block text-text-muted font-bold mb-1">Gjykata / Organi Përgjegjës</label>
                  <div className="relative">
                    <MapPin size={14} className="absolute left-3 top-3 text-text-muted" />
                    <input
                      type="text"
                      value={clientData.courtJurisdiction}
                      onChange={(e) => setClientData({ ...clientData, courtJurisdiction: e.target.value })}
                      placeholder="Gjykata Themelore Prishtinë"
                      className="w-full bg-surface border border-main rounded-xl pl-9 pr-3 py-2.5 text-text-primary font-medium focus:outline-none focus:border-primary-start"
                    />
                  </div>
                </div>

                <div className="pt-2 border-t border-main">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-text-muted mb-2">Vulosja me Avokat Partner (OAK)</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="text"
                      value={clientData.partnerLawyerName}
                      onChange={(e) => setClientData({ ...clientData, partnerLawyerName: e.target.value })}
                      placeholder="Emri i Avokatit"
                      className="bg-surface border border-main rounded-xl px-3 py-2 text-text-primary"
                    />
                    <input
                      type="text"
                      value={clientData.partnerLawyerLicense}
                      onChange={(e) => setClientData({ ...clientData, partnerLawyerLicense: e.target.value })}
                      placeholder="Nr. Licence OAK"
                      className="bg-surface border border-main rounded-xl px-3 py-2 text-text-primary font-mono"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Dropzone i Skedarëve */}
            <div className="lg:col-span-7 space-y-4 glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm flex flex-col justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary flex items-center justify-between border-b border-main pb-3 mb-4">
                  <span className="flex items-center gap-2">
                    <Upload size={16} className="text-primary-start" /> Ngarkimi i Shkresave (Foto WhatsApp / PDF / Skanime)
                  </span>
                  <span className="text-xs font-mono font-bold text-primary-start">
                    {uploadedFiles.length} skedarë
                  </span>
                </h3>

                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => { e.preventDefault(); handleFileDrop(e.dataTransfer.files); }}
                  className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-2xl p-8 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-2"
                >
                  <div className="w-12 h-12 rounded-full bg-primary-start/10 text-primary-start flex items-center justify-center">
                    <Upload size={22} />
                  </div>
                  <p className="text-xs font-bold text-text-primary">
                    Tërhiqni fotot dhe PDF-të këtu, ose klikoni për t'i përzgjedhur
                  </p>
                  <p className="text-[11px] text-text-muted">
                    Pranon foto nga WhatsApp (JPG, PNG), dokumente të skanuara dhe PDF
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => handleFileDrop(e.target.files)}
                  />
                </div>

                {/* Lista e Skedarëve të Zgjedhur */}
                {uploadedFiles.length > 0 && (
                  <div className="mt-4 max-h-48 overflow-y-auto space-y-1.5 custom-finance-scroll pr-1">
                    {uploadedFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl bg-surface border border-main text-xs">
                        <div className="flex items-center gap-2 truncate">
                          <FileText size={14} className="text-primary-start shrink-0" />
                          <span className="truncate font-medium text-text-primary">{file.name}</span>
                        </div>
                        <span className="text-[10px] font-mono text-text-muted shrink-0 ml-2">
                          {(file.size / 1024).toFixed(0)} KB
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Butoni i Ekzekutimit të Intake */}
              <div className="pt-4 border-t border-main">
                {isProcessingIntake ? (
                  <div className="flex items-center gap-3 p-3 bg-primary-start/10 border border-primary-start/20 rounded-2xl text-xs font-bold text-primary-start">
                    <Loader2 size={16} className="animate-spin" />
                    <span>{intakeProgressText}</span>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleExecuteIntake}
                    className="w-full h-11 bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider rounded-2xl shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <span>Krijo Dosjen & Fillo Përpunimin</span>
                    <ArrowRight size={15} />
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* FAZA 2: AUDITIMI DOKTRINAR SUPREM */}
        {activeTab === 'AUDIT' && (
          <div className="glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-main pb-4">
              <div>
                <h3 className="text-base font-bold text-text-primary uppercase tracking-tight">
                  Auditimi Doktrinar Suprem — {clientData.clientName}
                </h3>
                <p className="text-xs text-text-muted mt-0.5">
                  Autopsia e plotë e të gjitha shkresave të ngarkuara për këtë klient
                </p>
              </div>
              <button
                type="button"
                onClick={handleRunForensicAudit}
                disabled={isAuditing}
                className="h-10 px-5 bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow-sm transition-all flex items-center gap-2 disabled:opacity-40 cursor-pointer"
              >
                {isAuditing ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                <span>{auditText ? 'Ri-Ekzekuto Auditimin' : 'Fillo Auditimin Suprem'}</span>
              </button>
            </div>

            <div className="h-[620px] overflow-y-auto custom-finance-scroll p-6 bg-surface/40 rounded-2xl border border-main select-text text-text-primary text-xs sm:text-sm leading-relaxed whitespace-pre-wrap font-sans">
              {auditText || (
                <div className="h-full flex flex-col items-center justify-center text-text-muted gap-3">
                  <Scale size={40} className="opacity-40 text-primary-start" />
                  <p className="text-xs">Shtypni butonin lart për të ekzekutuar analizën e thellë forenzike.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* FAZA 3: HARTIMI I AKTEVE GJYQËSORE */}
        {activeTab === 'DRAFTING' && (
          <div className="glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
              <div>
                <h3 className="text-base font-bold text-text-primary uppercase tracking-tight">
                  Motori i Prodhimit të Shkresave Gjyqësore
                </h3>
                <p className="text-xs text-text-muted mt-0.5">
                  Gjeneroni aktin konkret procedural gati për dorëzim në organet e drejtësisë
                </p>
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={selectedActType}
                  onChange={(e) => setSelectedActType(e.target.value)}
                  className="h-10 bg-surface border border-main rounded-xl px-3 text-xs font-bold text-text-primary focus:outline-none"
                >
                  <option value="KALLËZIM_PENAL">Kallëzim Penal (PSRK / Themelore)</option>
                  <option value="ANKESË_CIVILE">Ankesë në Gjykatën e Apelit</option>
                  <option value="MASË_EMERGJENTE">Kërkesë për Masë Emergiente (Nenet 188/221)</option>
                  <option value="PRAPËSIM_PADI">Përgjigje në Padi (Prapësim)</option>
                </select>

                <button
                  type="button"
                  onClick={handleGenerateJudicialAct}
                  disabled={isDrafting}
                  className="h-10 px-5 bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold uppercase tracking-wider rounded-xl shadow-sm transition-all flex items-center gap-2 disabled:opacity-40 cursor-pointer shrink-0"
                >
                  {isDrafting ? <Loader2 size={15} className="animate-spin" /> : <FileCheck size={15} />}
                  <span>Harto Shkresën</span>
                </button>
              </div>
            </div>

            <div className="h-[620px] overflow-y-auto custom-finance-scroll p-6 bg-surface/40 rounded-2xl border border-main select-text text-text-primary text-xs sm:text-sm leading-relaxed whitespace-pre-wrap font-mono">
              {draftedActText || (
                <div className="h-full flex flex-col items-center justify-center text-text-muted gap-3">
                  <FileText size={40} className="opacity-40 text-primary-start" />
                  <p className="text-xs font-sans">Zgjidhni llojin e shkresës lart dhe klikoni "Harto Shkresën".</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* FAZA 4: PAKOJA PËRFUNDIMTARE & DISPATCH ME WHATSAPP */}
        {activeTab === 'DISPATCH' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7 glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-main pb-3">
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                  <Send size={16} className="text-primary-start" /> Mesazhi i Gatshëm për Klientin (WhatsApp)
                </h3>
                <button
                  type="button"
                  onClick={handleCopyWhatsApp}
                  className="px-3.5 py-1.5 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-primary-start flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  {copiedWhatsAppMsg ? <CheckCircle2 size={14} className="text-status-success" /> : <Copy size={14} />}
                  <span>{copiedWhatsAppMsg ? 'U Kopjua!' : 'Kopjo për WhatsApp'}</span>
                </button>
              </div>

              <textarea
                readOnly
                value={whatsAppMessage}
                rows={12}
                className="w-full bg-surface/50 border border-main rounded-2xl p-4 text-xs sm:text-sm text-text-primary leading-relaxed font-sans focus:outline-none resize-none select-text"
              />
            </div>

            <div className="lg:col-span-5 glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-5 flex flex-col justify-between">
              <div className="space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2 border-b border-main pb-3">
                  <FolderArchive size={16} className="text-primary-start" /> Pakoja e Dorëzimit (Dossier)
                </h3>

                <div className="space-y-2.5 text-xs">
                  <div className="flex items-center justify-between p-3 rounded-xl bg-surface border border-main">
                    <span className="text-text-muted font-medium">Statusi i Auditimit:</span>
                    <span className="font-bold text-status-success flex items-center gap-1">
                      <CheckCircle2 size={13} /> {auditText ? 'I Përfunduar' : 'Në Pritje'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-xl bg-surface border border-main">
                    <span className="text-text-muted font-medium">Shkresa Procedurale:</span>
                    <span className="font-bold text-text-primary">
                      {draftedActText ? selectedActType : 'E Papërgatitur'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-xl bg-surface border border-main">
                    <span className="text-text-muted font-medium">Skedarë të Administruar:</span>
                    <span className="font-bold font-mono text-primary-start">{uploadedFiles.length} Shkresa</span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-xl bg-surface border border-main">
                    <span className="text-text-muted font-medium">Vulosur nga:</span>
                    <span className="font-bold text-text-primary truncate max-w-[150px]">{clientData.partnerLawyerName}</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2.5 pt-4 border-t border-main">
                <button
                  type="button"
                  onClick={() => {
                    if (createdCaseId && auditText) {
                      apiService.archiveForensicReport(createdCaseId, `Pakoja Zyrtare: ${clientData.clientName}`, auditText);
                      alert("Pakoja u ruajt me sukses në Arkivën e Sistemit!");
                    } else {
                      alert("Ju lutem kryeni auditimin paraprakisht.");
                    }
                  }}
                  className="w-full h-11 bg-surface hover:bg-hover border border-main text-text-primary font-bold text-xs uppercase tracking-wider rounded-2xl transition-all flex items-center justify-center gap-2 cursor-pointer shadow-sm"
                >
                  <FolderArchive size={15} className="text-primary-start" />
                  <span>Ruaj Dosjen në Arkivën Zyrtare</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default AdminForensicDeskPage;