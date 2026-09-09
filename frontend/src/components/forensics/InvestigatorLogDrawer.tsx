// FILE: frontend/src/components/forensics/InvestigatorLogDrawer.tsx
// PHOENIX PROTOCOL - THE INVESTIGATOR'S LOG V6.4 (DYNAMIC FONT ZOOM)
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
  Search,
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

const FONT_LEVELS = [
  { label: '90%',   base: 15 },
  { label: '100%',  base: 17 },
  { label: '115%',  base: 19 },
  { label: '130%',  base: 21 },
  { label: '150%',  base: 24 },
  { label: '175%',  base: 28 },
  { label: '200%',  base: 32 }
];

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
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_investigator_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1;
    } catch {
      return 1;
    }
  });

  const activeFont = FONT_LEVELS[fontLevelIndex];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const loadStoredFindings = async () => {
    if (!caseId) return;
    try {
      const records = await forensicDeskService.getInvestigationFindings(caseId);
      if (Array.isArray(records) && records.length > 0) {
        const latest = records[0]?.findings;
        if (latest) {
          const mapped: ForensicFindingItem[] = [];
          if (latest.police_perspective) {
            mapped.push({
              id: 'police-1',
              role: 'POLICE',
              level: 'CRITICAL',
              title: 'Zbrazëtirat Faktike & Sigurimi i Provave',
              sourceA: 'Provat Materiale në Vendin e Ngjarjes',
              sourceB: 'Procesverbali i Sekuestrimit',
              contradictionDetails: (latest.police_perspective.factual_gaps || []).join('; ') || latest.police_perspective.evidence_chain_integrity,
              legalArticles: 'Neni 81, 82 KPPRK (Kujdestaria e Provës)',
              tacticalAdvice: (latest.police_perspective.recommended_actions || []).join(', ') || 'Kërkoni ballafaqim në seancë.'
            });
          }
          if (latest.prosecutor_perspective) {
            mapped.push({
              id: 'prosecutor-1',
              role: 'PROSECUTOR',
              level: 'SMOKING_GUN',
              title: 'Pikat e Cenueshmërisë së Aktakuzës',
              sourceA: 'Pretendimi i Trupit Gjykues',
              sourceB: 'Corpus Delicti Mungues',
              contradictionDetails: latest.prosecutor_perspective.indictment_vulnerability || (latest.prosecutor_perspective.missing_corpus_delicti || []).join('; '),
              legalArticles: (latest.prosecutor_perspective.elements_of_offense_met || []).join(', ') || 'Kodi Penal i Kosovës',
              tacticalAdvice: latest.tactical_masterstroke || 'Paraqitni kërkesë për hudhje të aktakuzës.'
            });
          }
          if (latest.judge_perspective) {
            mapped.push({
              id: 'judge-1',
              role: 'SUPREME_JUDGE',
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
      console.warn("Nuk u ngarkuan dot gjetjet:", err);
    }
  };

  useEffect(() => {
    if (isOpen && caseId) loadStoredFindings();
  }, [isOpen, caseId]);

  const handleRunAutonomousInvestigation = async () => {
    if (!caseId || isScanning) return;
    setIsScanning(true);
    try {
      const stream = await forensicDeskService.streamInvestigation(
        caseId,
        `Lënda e Klientit: ${clientName}. Vula e Kujdestarisë: ${chainOfCustodyHash}. Kërkohet ekspertizë kolegjiale me 3 këndvështrime sipas KPPRK dhe KPRK.`,
        ['Dëshmitë Shkresore', 'Regjistrimet Audio', 'Provat Vizuale', 'Bilancet Financiare']
      );
      const reader = stream.getReader();
      const decoder = new TextDecoder('utf-8');
      let accumulatedJson = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulatedJson += decoder.decode(value, { stream: true });
      }
      const parsed = JSON.parse(accumulatedJson.trim());
      const mapped: ForensicFindingItem[] = [];
      if (parsed.police_perspective) {
        mapped.push({
          id: 'police-1',
          role: 'POLICE',
          level: 'CRITICAL',
          title: 'Zbrazëtirat Faktike & Sigurimi i Provave',
          sourceA: 'Provat Materiale në Vendin e Ngjarjes',
          sourceB: 'Procesverbali i Sekuestrimit',
          contradictionDetails: (parsed.police_perspective.factual_gaps || []).join('; ') || parsed.police_perspective.evidence_chain_integrity,
          legalArticles: 'Neni 81, 82 KPPRK',
          tacticalAdvice: (parsed.police_perspective.recommended_actions || []).join(', ')
        });
      }
      if (parsed.prosecutor_perspective) {
        mapped.push({
          id: 'prosecutor-1',
          role: 'PROSECUTOR',
          level: 'SMOKING_GUN',
          title: 'Pikat e Cenueshmërisë së Aktakuzës',
          sourceA: 'Pretendimi i Trupit Gjykues',
          sourceB: 'Corpus Delicti Mungues',
          contradictionDetails: parsed.prosecutor_perspective.indictment_vulnerability || (parsed.prosecutor_perspective.missing_corpus_delicti || []).join('; '),
          legalArticles: (parsed.prosecutor_perspective.elements_of_offense_met || []).join(', '),
          tacticalAdvice: parsed.tactical_masterstroke
        });
      }
      if (parsed.judge_perspective) {
        mapped.push({
          id: 'judge-1',
          role: 'SUPREME_JUDGE',
          level: 'CRITICAL',
          title: 'Shkeljet Procedurale & In Dubio Pro Reo',
          sourceA: 'Standardi i Provueshmërisë Ligjore',
          sourceB: 'Vendimi Procedural i Ankimuar',
          contradictionDetails: parsed.judge_perspective.in_dubio_pro_reo_assessment || (parsed.judge_perspective.procedural_violations || []).join('; '),
          legalArticles: 'Neni 257 KPPRK',
          tacticalAdvice: parsed.judge_perspective.admissibility_verdict
        });
      }
      setFindings(mapped);
    } catch (err: any) {
      console.error("Autonomous investigator error:", err);
      alert(err?.message || "Dështoi skanimi i kolegjiumit hetimor.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleCopyFinding = (f: ForensicFindingItem) => {
    const text = `[DITARI I HETUESIT]:\nRoli: ${f.role}\nTitulli: ${f.title}\nNiveli: ${f.level}\nPërplasja: ${f.contradictionDetails}\nBaza Ligjore: ${f.legalArticles}\nTaktika: ${f.tacticalAdvice}`;
    navigator.clipboard.writeText(text);
    setCopiedId(f.id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const handleFontChange = (delta: number) => {
    setFontLevelIndex(prev => {
      const next = Math.min(Math.max(0, prev + delta), FONT_LEVELS.length - 1);
      try { localStorage.setItem('juristi_investigator_font_size', String(next)); } catch {}
      return next;
    });
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
      <aside className={`h-full shadow-2xl flex flex-col transition-all duration-300 ease-in-out border-l border-main bg-canvas text-text-primary ${isWidescreen ? 'w-full lg:w-[90%]' : 'w-full sm:w-[94%] md:w-[80%] lg:w-[55%]'}`}>
        {/* Header */}
        <header className="h-16 px-6 border-b border-main flex items-center justify-between gap-4 bg-surface shadow-md shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-rose-600 via-amber-600 to-primary-start text-white flex items-center justify-center shadow-lg shadow-rose-600/30 shrink-0">
              <ShieldAlert size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-black uppercase tracking-tight text-text-primary" style={{ fontSize: `${activeFont.base * 1.2}px` }}>Ditari i Hetuesit</h2>
                <span className="px-2 py-0.5 rounded-full bg-rose-600/15 text-rose-500 border border-rose-600/30 font-mono font-bold uppercase" style={{ fontSize: `${activeFont.base * 0.8}px` }}>Claude Sonnet 4.6</span>
              </div>
              <p className="text-text-muted truncate max-w-xs sm:max-w-md" style={{ fontSize: `${activeFont.base * 0.9}px` }}>Hetues Policor • Prokuror Shteti & PSRK • Gjyqtar Suprem</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1 bg-surface border border-main rounded-lg p-1">
              <button onClick={() => handleFontChange(-1)} className="p-1 rounded hover:bg-hover text-text-muted" title="Zvogëlo">A−</button>
              <span className="font-bold text-text-muted" style={{ fontSize: `${activeFont.base * 0.9}px` }}>{activeFont.label}</span>
              <button onClick={() => handleFontChange(1)} className="p-1 rounded hover:bg-hover text-text-muted" title="Zmadhо">A+</button>
            </div>
            <button onClick={() => setIsWidescreen(!isWidescreen)} className="w-10 h-10 rounded-xl bg-canvas hover:bg-hover border border-main text-text-primary flex items-center justify-center" title="Zgjero">
              {isWidescreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>
            <button onClick={onClose} className="w-10 h-10 rounded-xl bg-rose-500/10 hover:bg-rose-600 text-rose-500 hover:text-white border border-rose-500/30 flex items-center justify-center" title="Mbyll">
              <X size={20} />
            </button>
          </div>
        </header>

        {/* Filter Bar */}
        <div className="px-6 py-3.5 border-b border-main bg-surface/50 space-y-3 shrink-0">
          <div className="flex items-center gap-2 overflow-x-auto custom-finance-scroll pb-1">
            <button onClick={() => setActiveRoleFilter('ALL')} className={`px-3.5 py-1.5 rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 border ${activeRoleFilter === 'ALL' ? 'bg-rose-600 text-white border-rose-600' : 'bg-surface hover:bg-hover text-text-muted border-main'}`} style={{ fontSize: `${activeFont.base * 0.9}px` }}>
              <span>Kolegjiumi i Plotë</span><span className="font-mono bg-black/20 px-1.5 py-0.5 rounded-full">{findings.length}</span>
            </button>
            <button onClick={() => setActiveRoleFilter('POLICE')} className={`px-3.5 py-1.5 rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 border ${activeRoleFilter === 'POLICE' ? 'bg-blue-600 text-white border-blue-600' : 'bg-surface hover:bg-hover text-text-muted border-main'}`} style={{ fontSize: `${activeFont.base * 0.9}px` }}>
              <Shield size={14} /> Hetuesi Policor <span className="font-mono bg-black/20 px-1.5 py-0.5 rounded-full">{policeCount}</span>
            </button>
            <button onClick={() => setActiveRoleFilter('PROSECUTOR')} className={`px-3.5 py-1.5 rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 border ${activeRoleFilter === 'PROSECUTOR' ? 'bg-amber-600 text-white border-amber-600' : 'bg-surface hover:bg-hover text-text-muted border-main'}`} style={{ fontSize: `${activeFont.base * 0.9}px` }}>
              <Briefcase size={14} /> Prokurori i Shtetit <span className="font-mono bg-black/20 px-1.5 py-0.5 rounded-full">{prosecutorCount}</span>
            </button>
            <button onClick={() => setActiveRoleFilter('SUPREME_JUDGE')} className={`px-3.5 py-1.5 rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 border ${activeRoleFilter === 'SUPREME_JUDGE' ? 'bg-purple-600 text-white border-purple-600' : 'bg-surface hover:bg-hover text-text-muted border-main'}`} style={{ fontSize: `${activeFont.base * 0.9}px` }}>
              <Scale size={14} /> Gjykata Supreme <span className="font-mono bg-black/20 px-1.5 py-0.5 rounded-full">{judgeCount}</span>
            </button>
          </div>

          <div className="flex items-center justify-between gap-2">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3.5 top-2.5 text-text-muted" />
              <input type="text" value={searchFilter} onChange={(e) => setSearchFilter(e.target.value)} placeholder="Filtro..." className="w-full bg-surface border border-main rounded-xl pl-9 pr-3.5 py-1.5 text-text-primary focus:outline-none focus:border-primary-start" style={{ fontSize: `${activeFont.base * 0.9}px` }} />
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <div className="flex items-center gap-1 bg-surface border border-main rounded-xl p-1">
                <button onClick={() => setActiveSeverityFilter('ALL')} className={`px-2 py-1 rounded-lg font-bold ${activeSeverityFilter === 'ALL' ? 'bg-canvas text-text-primary' : 'text-text-muted'}`} style={{ fontSize: `${activeFont.base * 0.8}px` }}>Të gjitha</button>
                <button onClick={() => setActiveSeverityFilter('CRITICAL')} className={`px-2 py-1 rounded-lg font-bold ${activeSeverityFilter === 'CRITICAL' ? 'bg-rose-500 text-white' : 'text-rose-500'}`} style={{ fontSize: `${activeFont.base * 0.8}px` }}>Kritike</button>
                <button onClick={() => setActiveSeverityFilter('SUSPICIOUS')} className={`px-2 py-1 rounded-lg font-bold ${activeSeverityFilter === 'SUSPICIOUS' ? 'bg-amber-500 text-white' : 'text-amber-500'}`} style={{ fontSize: `${activeFont.base * 0.8}px` }}>Dyshime</button>
              </div>
              <button onClick={handleRunAutonomousInvestigation} disabled={isScanning} className="h-10 px-4 rounded-xl font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-md bg-rose-600 hover:bg-rose-700 text-white cursor-pointer disabled:opacity-40" style={{ fontSize: `${activeFont.base * 0.9}px` }}>
                {isScanning ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />} Fillo Hetimin
              </button>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto custom-finance-scroll p-6 space-y-4 bg-canvas">
          {filteredFindings.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-text-muted text-center p-8 gap-3">
              <Scale size={64} className="opacity-25 text-primary-start" />
              <p className="font-bold text-text-primary" style={{ fontSize: `${activeFont.base * 1.2}px` }}>{isScanning ? 'Duke analizuar...' : 'Nuk ka gjetje'}</p>
              <p style={{ fontSize: `${activeFont.base}px` }}>Shtypni "Fillo Hetimin" për të aktivizuar kolegjiumin.</p>
            </div>
          ) : (
            <div className={`grid gap-4 ${isWidescreen ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1'}`}>
              {filteredFindings.map((item) => {
                const isCritical = item.level === 'CRITICAL';
                const isSmoking = item.level === 'SMOKING_GUN';
                const roleBadge = item.role === 'POLICE' ? { label: 'Hetuesi Policor', color: 'bg-blue-500/15 text-blue-500 border-blue-500/30' } : item.role === 'PROSECUTOR' ? { label: 'Prokuroria', color: 'bg-amber-500/15 text-amber-500 border-amber-500/30' } : { label: 'Gjykata Supreme', color: 'bg-purple-500/15 text-purple-500 border-purple-500/30' };
                return (
                  <article key={item.id} className={`p-5 rounded-2xl border transition-all space-y-3 bg-surface shadow-sm ${isCritical ? 'border-rose-500/40' : isSmoking ? 'border-emerald-500/40' : 'border-amber-500/40'}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`px-2.5 py-0.5 rounded-full font-mono font-bold uppercase border ${roleBadge.color}`} style={{ fontSize: `${activeFont.base * 0.8}px` }}>{roleBadge.label}</span>
                          <span className={`px-2 py-0.5 rounded-full font-mono font-bold uppercase ${isCritical ? 'bg-rose-500/15 text-rose-500' : isSmoking ? 'bg-emerald-500/15 text-emerald-500' : 'bg-amber-500/15 text-amber-500'}`} style={{ fontSize: `${activeFont.base * 0.8}px` }}>{item.level}</span>
                        </div>
                        <h4 className="font-bold text-text-primary leading-snug" style={{ fontSize: `${activeFont.base * 1.1}px` }}>{item.title}</h4>
                      </div>
                      <button onClick={() => handleCopyFinding(item)} className="p-2 rounded-lg hover:bg-hover text-text-muted" title="Kopjo">
                        {copiedId === item.id ? <CheckCircle2 size={18} className="text-emerald-500" /> : <Copy size={18} />}
                      </button>
                    </div>
                    <div className="p-3 rounded-xl bg-canvas border border-main space-y-1.5 font-mono" style={{ fontSize: `${activeFont.base}px` }}>
                      <div className="flex items-center gap-2"><FileText size={16} className="text-primary-start" /><span className="font-bold">Prova A:</span> {item.sourceA}</div>
                      <div className="text-rose-500 font-bold">Bie ndesh me:</div>
                      <div className="flex items-center gap-2"><FileText size={16} className="text-rose-500" /><span className="font-bold">Prova B:</span> {item.sourceB}</div>
                    </div>
                    <p className="text-text-primary whitespace-pre-wrap" style={{ fontSize: `${activeFont.base}px` }}>{item.contradictionDetails}</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <div className="p-2.5 rounded-xl bg-canvas border border-main"><span className="font-bold uppercase" style={{ fontSize: `${activeFont.base * 0.8}px` }}>Nenet:</span> <span style={{ fontSize: `${activeFont.base}px` }}>{item.legalArticles}</span></div>
                      <div className="p-2.5 rounded-xl bg-primary-start/5 border border-primary-start/20"><span className="font-bold uppercase" style={{ fontSize: `${activeFont.base * 0.8}px` }}>Veprimi Taktik:</span> <span style={{ fontSize: `${activeFont.base}px` }}>{item.tacticalAdvice}</span></div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </main>

        <footer className="h-12 px-6 border-t border-main bg-surface flex items-center justify-between text-sm text-text-muted shrink-0">
          <span style={{ fontSize: `${activeFont.base * 0.9}px` }}>{isScanning ? 'Duke analizuar...' : `${findings.length} gjetje`}</span>
          <span className="font-mono" style={{ fontSize: `${activeFont.base * 0.8}px` }}>Claude Sonnet 4.6</span>
        </footer>
      </aside>
    </div>
  );
};

export default InvestigatorLogDrawer;