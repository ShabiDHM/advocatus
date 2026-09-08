// FILE: frontend/src/components/forensics/InvestigatorLogDrawer.tsx
// PHOENIX PROTOCOL - THE INVESTIGATOR'S LOG V5.0 (3-ROLE FORENSIC COLLEGIATE • CLAUDE SONNET 4.6)
// 100% COMPLETE CODE • ZERO DUPLICATIONS • ZERO TS WARNINGS

import React, { useState, useEffect } from 'react';
import {
  X,
  Maximize2,
  Minimize2,
  ShieldAlert,
  CheckCircle2,
  Copy,
  FileText,
  RefreshCw,
  Loader2,
  Filter,
  ArrowRight,
  Search,
  Flame,
  Scale,
  Briefcase,
  Shield
} from 'lucide-react';
import { forensicDeskService } from '../../services/forensicDeskService';

export type FindingSeverity = 'CRITICAL' | 'SUSPICIOUS' | 'SMOKING_GUN';
export type ForensicRolePerspective = 'ALL' | 'POLICE' | 'PROSECUTOR' | 'SUPREME_JUDGE';

export interface ForensicFindingItem {
  id: string;
  role: 'POLICE' | 'PROSECUTOR' | 'SUPREME_JUDGE';
  jurisdictionSubtype?: 'THEMELORE' | 'PSRK' | 'CIVIL_LPK' | 'CRIMINAL_KPPRK';
  level: FindingSeverity;
  title: string;
  sourceA: string;
  sourceB: string;
  contradictionDetails: string;
  legalArticles: string;
  tacticalAdvice: string;
}

interface InvestigatorLogDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  clientName?: string;
  chainOfCustodyHash?: string;
}

export const InvestigatorLogDrawer: React.FC<InvestigatorLogDrawerProps> = ({
  isOpen,
  onClose,
  caseId,
  clientName = 'Pala e Menaxhuar',
  chainOfCustodyHash = 'SEAL-CUSTODY-ACTIVE'
}) => {
  const [isWidescreen, setIsWidescreen] = useState<boolean>(false);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [findings, setFindings] = useState<ForensicFindingItem[]>([]);
  const [activeRoleFilter, setActiveRoleFilter] = useState<ForensicRolePerspective>('ALL');
  const [activeSeverityFilter, setActiveSeverityFilter] = useState<'ALL' | FindingSeverity>('ALL');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Ngarkimi i gjetjeve nga MongoDB sapo hapet dritarja
  const loadStoredFindings = async () => {
    if (!caseId) return;
    try {
      const records = await forensicDeskService.getInvestigationFindings(caseId);
      if (Array.isArray(records) && records.length > 0) {
        const latest = records[0]?.findings;
        if (latest) {
          const mapped: ForensicFindingItem[] = [];

          // 1. Hetuesi Policor
          if (latest.police_perspective) {
            mapped.push({
              id: 'police-1',
              role: 'POLICE',
              jurisdictionSubtype: 'CRIMINAL_KPPRK',
              level: 'CRITICAL',
              title: 'Zbrazëtirat Faktike & Sigurimi i Provave',
              sourceA: 'Provat Materiale në Vendin e Ngjarjes',
              sourceB: 'Procesverbali i Sekuestrimit',
              contradictionDetails: (latest.police_perspective.factual_gaps || []).join('; ') || latest.police_perspective.evidence_chain_integrity || 'Verifikim i rregullt',
              legalArticles: 'Neni 81, 82 KPPRK (Kujdestaria e Provës)',
              tacticalAdvice: (latest.police_perspective.recommended_actions || []).join(', ') || 'Kërkoni ballafaqim në seancë.'
            });
          }

          // 2. Prokurori i Shtetit
          if (latest.prosecutor_perspective) {
            mapped.push({
              id: 'prosecutor-1',
              role: 'PROSECUTOR',
              jurisdictionSubtype: 'THEMELORE',
              level: 'SMOKING_GUN',
              title: 'Pikat e Cenueshmërisë së Aktakuzës',
              sourceA: 'Pretendimi i Trupit Gjykues / Prokurorisë',
              sourceB: 'Corpus Delicti Mungues',
              contradictionDetails: latest.prosecutor_perspective.indictment_vulnerability || (latest.prosecutor_perspective.missing_corpus_delicti || []).join('; '),
              legalArticles: (latest.prosecutor_perspective.elements_of_offense_met || []).join(', ') || 'Kodi Penal i Kosovës',
              tacticalAdvice: latest.tactical_masterstroke || 'Paraqitni kërkesë për hudhje të aktakuzës.'
            });
          }

          // 3. Gjyqtari Suprem
          if (latest.judge_perspective) {
            mapped.push({
              id: 'judge-1',
              role: 'SUPREME_JUDGE',
              jurisdictionSubtype: 'CRIMINAL_KPPRK',
              level: 'CRITICAL',
              title: 'Shkeljet Procedurale & In Dubio Pro Reo',
              sourceA: 'Standardi i Provueshmërisë Ligjore',
              sourceB: 'Vendimi Procedural i Ankimuar',
              contradictionDetails: latest.judge_perspective.in_dubio_pro_reo_assessment || (latest.judge_perspective.procedural_violations || []).join('; '),
              legalArticles: 'Neni 257 KPPRK (Papranueshmëria e Provave)',
              tacticalAdvice: latest.judge_perspective.admissibility_verdict || 'Provat e paligjshme duhet të veçohen nga fashikulli.'
            });
          }

          setFindings(mapped);
        }
      }
    } catch (err) {
      console.warn("Nuk u ngarkuan dot gjetjet e mëparshme:", err);
    }
  };

  useEffect(() => {
    if (isOpen && caseId) {
      loadStoredFindings();
    }
  }, [isOpen, caseId]);

  // Ekzekutimi i Skanimit të Pavarur me Claude Sonnet 4.6
  const handleRunAutonomousInvestigation = async () => {
    if (!caseId || isScanning) return;
    setIsScanning(true);

    try {
      await forensicDeskService.runInvestigation(
        caseId,
        `Lënda e Klientit: ${clientName}. Vula e Kujdestarisë: ${chainOfCustodyHash}. Kërkohet ekspertizë kolegjiale me 3 këndvështrime sipas KPPRK dhe KPRK.`,
        ['Dëshmitë Shkresore', 'Regjistrimet Audio', 'Provat Vizuale', 'Bilancet Financiare']
      );
      await loadStoredFindings();
    } catch (err: any) {
      console.error("Autonomous investigator error:", err);
      alert(err?.response?.data?.detail || "Dështoi skanimi i kolegjiumit hetimor.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleCopyFinding = (finding: ForensicFindingItem) => {
    const text = `[DITARI I HETUESIT]:\nRoli: ${finding.role}\nTitulli: ${finding.title}\nNiveli: ${finding.level}\nPërplasja: ${finding.contradictionDetails}\nBaza Ligjore: ${finding.legalArticles}\nTaktika: ${finding.tacticalAdvice}`;
    navigator.clipboard.writeText(text);
    setCopiedId(finding.id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  if (!isOpen) return null;

  const filteredFindings = findings.filter(f => {
    const matchesRole = activeRoleFilter === 'ALL' || f.role === activeRoleFilter;
    const matchesSeverity = activeSeverityFilter === 'ALL' || f.level === activeSeverityFilter;
    const matchesSearch = f.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
                          f.contradictionDetails.toLowerCase().includes(searchFilter.toLowerCase()) ||
                          f.legalArticles.toLowerCase().includes(searchFilter.toLowerCase());
    return matchesRole && matchesSeverity && matchesSearch;
  });

  const policeCount = findings.filter(f => f.role === 'POLICE').length;
  const prosecutorCount = findings.filter(f => f.role === 'PROSECUTOR').length;
  const judgeCount = findings.filter(f => f.role === 'SUPREME_JUDGE').length;

  return (
    <div className="fixed inset-0 z-[9999] bg-black/80 backdrop-blur-md flex justify-end transition-all select-none">
      <aside
        className={`h-full shadow-2xl flex flex-col transition-all duration-300 ease-in-out border-l border-main bg-canvas text-text-primary ${
          isWidescreen ? 'w-full lg:w-[90%]' : 'w-full sm:w-[94%] md:w-[80%] lg:w-[55%]'
        }`}
      >
        {/* Header me Kontrollues Vetëm-Ikonë */}
        <header className="h-16 px-6 border-b border-main flex items-center justify-between gap-4 bg-surface shadow-md shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-rose-600 via-amber-600 to-primary-start text-white flex items-center justify-center shadow-lg shadow-rose-600/30 shrink-0">
              <ShieldAlert size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm sm:text-base font-black uppercase tracking-tight text-text-primary">
                  Ditari i Hetuesit
                </h2>
                <span className="px-2 py-0.5 rounded-full bg-rose-600/15 text-rose-500 border border-rose-600/30 text-[10px] font-mono font-bold uppercase">
                  Claude Sonnet 4.6 (3 Role)
                </span>
              </div>
              <p className="text-[11px] text-text-muted truncate max-w-xs sm:max-w-md">
                Hetues Policor • Prokuror Shteti & PSRK • Gjyqtar Suprem
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setIsWidescreen(!isWidescreen)}
              className="w-10 h-10 rounded-xl bg-canvas hover:bg-hover border border-main text-text-primary flex items-center justify-center transition-all cursor-pointer shadow-sm"
              title={isWidescreen ? 'Kthe në 55%' : 'Zgjero në 90%'}
            >
              {isWidescreen ? <Minimize2 size={16} className="text-primary-start" /> : <Maximize2 size={16} className="text-primary-start" />}
            </button>

            <button
              type="button"
              onClick={onClose}
              className="w-10 h-10 rounded-xl bg-rose-500/10 hover:bg-rose-600 text-rose-500 hover:text-white border border-rose-500/30 flex items-center justify-center transition-all cursor-pointer shadow-sm"
              title="Mbyll"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        {/* Tab-et e Pastra (VETËM TEKST DHE NUMRA) */}
        <div className="px-6 py-3.5 border-b border-main bg-surface/50 space-y-3 shrink-0">
          <div className="flex items-center gap-2 overflow-x-auto custom-finance-scroll pb-1">
            <button
              type="button"
              onClick={() => setActiveRoleFilter('ALL')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer shrink-0 border ${
                activeRoleFilter === 'ALL'
                  ? 'bg-rose-600 text-white border-rose-600 shadow-sm'
                  : 'bg-surface hover:bg-hover text-text-muted border-main'
              }`}
            >
              <span>Kolegjiumi i Plotë</span>
              <span className="font-mono text-[10px] bg-black/20 px-1.5 py-0.5 rounded-full">{findings.length}</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveRoleFilter('POLICE')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer shrink-0 border ${
                activeRoleFilter === 'POLICE'
                  ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                  : 'bg-surface hover:bg-hover text-text-muted border-main'
              }`}
            >
              <Shield size={12} />
              <span>Hetuesi Policor</span>
              <span className="font-mono text-[10px] bg-black/20 px-1.5 py-0.5 rounded-full">{policeCount}</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveRoleFilter('PROSECUTOR')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer shrink-0 border ${
                activeRoleFilter === 'PROSECUTOR'
                  ? 'bg-amber-600 text-white border-amber-600 shadow-sm'
                  : 'bg-surface hover:bg-hover text-text-muted border-main'
              }`}
            >
              <Briefcase size={12} />
              <span>Prokurori i Shtetit & PSRK</span>
              <span className="font-mono text-[10px] bg-black/20 px-1.5 py-0.5 rounded-full">{prosecutorCount}</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveRoleFilter('SUPREME_JUDGE')}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer shrink-0 border ${
                activeRoleFilter === 'SUPREME_JUDGE'
                  ? 'bg-purple-600 text-white border-purple-600 shadow-sm'
                  : 'bg-surface hover:bg-hover text-text-muted border-main'
              }`}
            >
              <Scale size={12} />
              <span>Gjykata Supreme</span>
              <span className="font-mono text-[10px] bg-black/20 px-1.5 py-0.5 rounded-full">{judgeCount}</span>
            </button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pt-1">
            <div className="relative flex-1">
              <Search size={13} className="absolute left-3.5 top-2.5 text-text-muted" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filtro sipas neneve, orës ose personave..."
                className="w-full bg-surface border border-main rounded-xl pl-9 pr-3.5 py-1.5 text-xs text-text-primary focus:outline-none focus:border-primary-start"
              />
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <div className="flex items-center bg-surface border border-main rounded-xl p-0.5 text-[11px]">
                <button
                  type="button"
                  onClick={() => setActiveSeverityFilter('ALL')}
                  className={`px-2 py-1 rounded-lg font-bold transition-all cursor-pointer ${activeSeverityFilter === 'ALL' ? 'bg-canvas text-text-primary shadow-sm' : 'text-text-muted'}`}
                >
                  Të gjitha
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSeverityFilter('CRITICAL')}
                  className={`px-2 py-1 rounded-lg font-bold transition-all cursor-pointer ${activeSeverityFilter === 'CRITICAL' ? 'bg-rose-500 text-white shadow-sm' : 'text-rose-500'}`}
                >
                  Kritike
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSeverityFilter('SUSPICIOUS')}
                  className={`px-2 py-1 rounded-lg font-bold transition-all cursor-pointer ${activeSeverityFilter === 'SUSPICIOUS' ? 'bg-amber-500 text-white shadow-sm' : 'text-amber-500'}`}
                >
                  Dyshime
                </button>
              </div>

              <button
                type="button"
                onClick={handleRunAutonomousInvestigation}
                disabled={isScanning}
                className="h-9 px-4 rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-md transition-all bg-rose-600 hover:bg-rose-700 text-white cursor-pointer disabled:opacity-40"
              >
                {isScanning ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Duke hetuar me Sonnet 4.6...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw size={13} />
                    <span>Fillo Hetimin Kolegjial</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        <main className="flex-1 overflow-y-auto custom-finance-scroll p-6 space-y-4 bg-canvas">
          {filteredFindings.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-text-muted text-center p-8 gap-3">
              <Scale size={48} className="opacity-25 text-primary-start" />
              <div className="max-w-md space-y-1">
                <p className="text-sm font-bold text-text-primary">
                  {isScanning ? 'Kolegjiumi po analizon fashikullin e lëndës...' : 'Nuk u gjet asnjë gjetje hetimore'}
                </p>
                <p className="text-xs">
                  Shtypni <span className="font-bold text-text-primary">"Fillo Hetimin Kolegjial"</span> për të aktivizuar Hetuesin Policor, Prokurorin e Shtetit dhe Gjyqtarin Suprem me Claude Sonnet 4.6.
                </p>
              </div>
            </div>
          ) : (
            <div className={`grid gap-4 ${isWidescreen ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1'}`}>
              {filteredFindings.map((item) => {
                const isCritical = item.level === 'CRITICAL';
                const isSmoking = item.level === 'SMOKING_GUN';

                const roleBadge = item.role === 'POLICE'
                  ? { label: 'Hetuesi Policor', color: 'bg-blue-500/15 text-blue-500 border-blue-500/30' }
                  : item.role === 'PROSECUTOR'
                  ? { label: item.jurisdictionSubtype === 'PSRK' ? 'Prokuroria Speciale PSRK' : 'Prokuroria Themelore', color: 'bg-amber-500/15 text-amber-500 border-amber-500/30' }
                  : { label: 'Gjykata Supreme', color: 'bg-purple-500/15 text-purple-500 border-purple-500/30' };

                return (
                  <article
                    key={item.id}
                    className={`p-5 rounded-2xl border transition-all space-y-3 bg-surface shadow-sm ${
                      isCritical
                        ? 'border-rose-500/40 hover:border-rose-500 shadow-rose-500/5'
                        : isSmoking
                        ? 'border-emerald-500/40 hover:border-emerald-500'
                        : 'border-amber-500/40 hover:border-amber-500'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase border ${roleBadge.color}`}>
                            {roleBadge.label}
                          </span>

                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                              isCritical
                                ? 'bg-rose-500/15 text-rose-500 border border-rose-500/30'
                                : isSmoking
                                ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                                : 'bg-amber-500/15 text-amber-500 border border-amber-500/30'
                            }`}
                          >
                            {isCritical ? 'Kontradiktë Fatale' : isSmoking ? 'Smoking Gun' : 'Dyshim Procedural'}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-text-primary leading-snug">{item.title}</h4>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleCopyFinding(item)}
                        title="Kopjo incidentin"
                        className="p-1.5 rounded-lg bg-canvas hover:bg-hover border border-main text-text-muted hover:text-text-primary transition-colors cursor-pointer shrink-0"
                      >
                        {copiedId === item.id ? <CheckCircle2 size={14} className="text-emerald-500" /> : <Copy size={14} />}
                      </button>
                    </div>

                    <div className="p-3 rounded-xl bg-canvas border border-main text-xs space-y-1.5 font-mono">
                      <div className="flex items-center gap-2 text-text-muted truncate">
                        <FileText size={13} className="text-primary-start shrink-0" />
                        <span className="font-bold text-text-primary shrink-0">Prova A:</span>
                        <span className="truncate">{item.sourceA}</span>
                      </div>
                      <div className="flex items-center gap-2 text-rose-500 font-bold text-[10px] uppercase">
                        <ArrowRight size={12} className="rotate-90 sm:rotate-0 shrink-0" />
                        <span>Bie ndesh me:</span>
                      </div>
                      <div className="flex items-center gap-2 text-text-muted truncate">
                        <FileText size={13} className="text-rose-500 shrink-0" />
                        <span className="font-bold text-text-primary shrink-0">Prova B:</span>
                        <span className="truncate">{item.sourceB}</span>
                      </div>
                    </div>

                    <div className="text-xs text-text-primary leading-relaxed select-text font-sans">
                      <p className="font-bold text-text-muted uppercase text-[10px] tracking-wider mb-0.5">
                        Zbardhja e Kolegjiumit:
                      </p>
                      <p className="whitespace-pre-wrap">{item.contradictionDetails}</p>
                    </div>

                    <div className="pt-2 border-t border-main grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 rounded-xl bg-canvas border border-main space-y-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted flex items-center gap-1">
                          <Filter size={11} /> Nenet e Zbatuara:
                        </span>
                        <p className="font-mono font-bold text-primary-start truncate">{item.legalArticles}</p>
                      </div>

                      <div className="p-2.5 rounded-xl bg-primary-start/5 border border-primary-start/20 space-y-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-primary-start flex items-center gap-1">
                          <Flame size={11} /> Veprimi Taktik:
                        </span>
                        <p className="text-text-primary text-[11px] truncate">{item.tacticalAdvice}</p>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </main>

        <footer className="h-12 px-6 border-t border-main bg-surface flex items-center justify-between text-xs text-text-muted shrink-0">
          <span className="flex items-center gap-1.5 font-medium">
            <RefreshCw size={12} className={isScanning ? 'animate-spin text-primary-start' : ''} />
            {isScanning ? 'Kolegjiumi po analizon...' : `${findings.length} gjetje nga të 3 rolet`}
          </span>
          <span className="font-mono text-[10px]">Modeli: Claude Sonnet 4.6 (Ekskluziv)</span>
        </footer>
      </aside>
    </div>
  );
};

export default InvestigatorLogDrawer;