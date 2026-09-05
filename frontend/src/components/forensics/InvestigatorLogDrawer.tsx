// FILE: frontend/src/components/forensics/InvestigatorLogDrawer.tsx
// PHOENIX PROTOCOL - THE INVESTIGATOR'S LOG / FORENSIC SENTINEL V1.0
// ZERO TS WARNINGS • ZERO HARDCODING • MULTI-STATE EXPANDABLE DRAWER (50% / 85%)

import React, { useState, useEffect } from 'react';
import {
  X,
  Maximize2,
  Minimize2,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Copy,
  FileText,
  RefreshCw,
  Loader2,
  Filter,
  ArrowRight,
  Search,
  Flame
} from 'lucide-react';
import { apiService } from '../../services/api';

export type FindingSeverity = 'CRITICAL' | 'SUSPICIOUS' | 'SMOKING_GUN';

export interface ForensicFindingItem {
  id: string;
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
  chainOfCustodyHash = 'SHA256-000000'
}) => {
  // Gjendja e Madhësisë së Dritares (50% apo 85%)
  const [isWidescreen, setIsWidescreen] = useState<boolean>(false);

  // Gjendjet e Skanimit & Gjetjeve
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [findings, setFindings] = useState<ForensicFindingItem[]>([]);
  const [activeFilter, setActiveFilter] = useState<'ALL' | FindingSeverity>('ALL');
  const [searchFilter, setSearchFilter] = useState<string>('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Mbyllja me tastin Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Ekzekutimi i Skanimit Autonom të Hetuesit
  const handleRunAutonomousInvestigation = async () => {
    if (!caseId || isScanning) return;
    setIsScanning(true);

    try {
      const prompt = `[DIREKTIVË HETIMORE SUPREME — PROTOKOLLI PHOENIX: DITARI I HETUESIT]
LËNDA: ${clientName}
HASH: ${chainOfCustodyHash}

Vepro si Kryehetuesi Forenzik dhe zbulo të gjitha kontradiktat, alibitë e rreme dhe shkeljet e fshehura në këtë dosje.
RREPTËSISHT: Përgjigju duke listuar incidentet në këtë format të saktë me numra:

INCIDENTI 1:
TITULLI: [Titulli i shkurtër i përplasjes]
NIVELI: [KRITIKE ose DYSHIM ose SMOKING_GUN]
PROVA_A: [Dokumenti ose Audioja A me faqe/sekondë]
PROVA_B: [Dokumenti, Videoja ose Fatura B me faqe/sekondë]
KONTRADIKTA: [Përshkrimi i saktë i përplasjes mes tyre]
NENI: [Neni përkatës i LPK, KPPRK ose KPRK]
TAKTIKA: [Pyetja kurth ose veprimi për avokatin në seancë]

(Vazhdo me INCIDENTI 2, INCIDENTI 3, etj.)`;

      const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic');
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
      }

      // Parser i strukturuar për të nxjerrë kartat e hetuesit
      const parsedFindings = parseInvestigatorStream(acc);
      setFindings(parsedFindings);
    } catch (err) {
      console.error("Autonomous investigator error:", err);
      alert("Dështoi skanimi i hetuesit autonom.");
    } finally {
      setIsScanning(false);
    }
  };

  // Funksion ndihmës për kthimin e tekstit të modelit në objekte të strukturuara
  const parseInvestigatorStream = (text: string): ForensicFindingItem[] => {
    const items: ForensicFindingItem[] = [];
    const blocks = text.split(/INCIDENTI\s+\d+:/i).filter(b => b.trim().length > 0);

    blocks.forEach((block, index) => {
      const getField = (tag: string) => {
        const match = block.match(new RegExp(`${tag}:\\s*([^\\n]+(?:\\n(?!TITULLI|NIVELI|PROVA_A|PROVA_B|KONTRADIKTA|NENI|TAKTIKA)[^\\n]+)*)`, 'i'));
        return match ? match[1].trim() : '';
      };

      const rawLevel = getField('NIVELI').toUpperCase();
      let level: FindingSeverity = 'SUSPICIOUS';
      if (rawLevel.includes('KRITIKE') || rawLevel.includes('FATAL') || rawLevel.includes('CRITICAL')) {
        level = 'CRITICAL';
      } else if (rawLevel.includes('SMOKING') || rawLevel.includes('FORTE') || rawLevel.includes('GUN')) {
        level = 'SMOKING_GUN';
      }

      items.push({
        id: `finding-${Date.now()}-${index}`,
        level,
        title: getField('TITULLI') || `Gjetje Hetimore #${index + 1}`,
        sourceA: getField('PROVA_A') || 'Dokumenti i parë në fashikull',
        sourceB: getField('PROVA_B') || 'Dëshmia ose prova materiale përballë',
        contradictionDetails: getField('KONTRADIKTA') || block.trim().slice(0, 300),
        legalArticles: getField('NENI') || 'Nenet e LPK / KPPRK',
        tacticalAdvice: getField('TAKTIKA') || 'Kërkoni ballafaqim të drejtpërdrejtë në seancën e radhës.'
      });
    });

    return items;
  };

  const handleCopyFinding = (finding: ForensicFindingItem) => {
    const text = `[GJETJE HETIMORE NGA DITARI I HETUESIT]:\nTitulli: ${finding.title}\nNiveli: ${finding.level}\nBurimi 1: ${finding.sourceA}\nBurimi 2: ${finding.sourceB}\nPërplasja: ${finding.contradictionDetails}\nBaza Ligjore: ${finding.legalArticles}\nTaktika e Rekomanduar: ${finding.tacticalAdvice}`;
    navigator.clipboard.writeText(text);
    setCopiedId(finding.id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  if (!isOpen) return null;

  // Filtrimi i Gjetjeve
  const filteredFindings = findings.filter(f => {
    const matchesCategory = activeFilter === 'ALL' || f.level === activeFilter;
    const matchesSearch = f.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
                          f.contradictionDetails.toLowerCase().includes(searchFilter.toLowerCase()) ||
                          f.legalArticles.toLowerCase().includes(searchFilter.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const criticalCount = findings.filter(f => f.level === 'CRITICAL').length;
  const suspiciousCount = findings.filter(f => f.level === 'SUSPICIOUS').length;
  const smokingCount = findings.filter(f => f.level === 'SMOKING_GUN').length;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end transition-all">
      <aside
        className={`bg-card border-l border-main h-full shadow-2xl flex flex-col transition-all duration-300 ease-in-out ${
          isWidescreen ? 'w-full lg:w-[85%]' : 'w-full sm:w-[90%] md:w-[75%] lg:w-[50%]'
        }`}
      >
        {/* KOKA E DITARIT TË HETUESIT */}
        <header className="p-5 border-b border-main flex items-center justify-between gap-3 bg-surface/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-rose-600 via-amber-600 to-primary-start text-white flex items-center justify-center shadow-lg shadow-rose-600/20 shrink-0">
              <ShieldAlert size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-black uppercase tracking-tight text-text-primary">
                  Ditari i Hetuesit
                </h2>
                <span className="px-2 py-0.5 rounded-full bg-rose-600/15 text-rose-500 border border-rose-600/30 text-[10px] font-mono font-bold uppercase">
                  Forensic Sentinel
                </span>
              </div>
              <p className="text-xs text-text-muted mt-0.5 truncate max-w-sm">
                Skanimi i vazhdueshëm për alibi të rreme, shkelje procedurale dhe kontradikta
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Butoni i Zgjerimit (50% / 85%) */}
            <button
              type="button"
              onClick={() => setIsWidescreen(!isWidescreen)}
              title={isWidescreen ? 'Kthe në pamje standarde (50%)' : 'Zgjero në madhësi të plotë (85%)'}
              className="p-2 rounded-xl bg-surface hover:bg-hover border border-main text-text-muted hover:text-text-primary transition-colors cursor-pointer"
            >
              {isWidescreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>

            {/* Butoni i Mbylljes */}
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-xl bg-surface hover:bg-rose-500/10 border border-main text-text-muted hover:text-rose-500 transition-colors cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>
        </header>

        {/* SHIRITI I VEPRIMIT & FILTRAT */}
        <div className="p-4 border-b border-main bg-surface/20 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3.5 top-3 text-text-muted" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filtro gjetjet e hetuesit..."
                className="w-full bg-surface border border-main rounded-xl pl-9 pr-3.5 py-2 text-xs text-text-primary focus:outline-none focus:border-primary-start"
              />
            </div>

            <button
              type="button"
              onClick={handleRunAutonomousInvestigation}
              disabled={isScanning}
              className="h-9 px-4 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-sm transition-all cursor-pointer disabled:opacity-40 shrink-0"
            >
              {isScanning ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              <span>{findings.length > 0 ? 'Ri-Skano Dosjen' : 'Nis Hetimin e Thellë'}</span>
            </button>
          </div>

          {/* Butonat e Filtrimit sipas Shkallës së Rrezikut */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs custom-finance-scroll">
            <button
              type="button"
              onClick={() => setActiveFilter('ALL')}
              className={`px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                activeFilter === 'ALL'
                  ? 'bg-primary-start text-white shadow-sm'
                  : 'bg-surface hover:bg-hover text-text-muted border border-main'
              }`}
            >
              <Filter size={12} />
              <span>Të Gjitha</span>
              <span className="font-mono text-[10px] ml-0.5">({findings.length})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveFilter('CRITICAL')}
              className={`px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                activeFilter === 'CRITICAL'
                  ? 'bg-rose-600 text-white shadow-sm'
                  : 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border border-rose-500/20'
              }`}
            >
              <Flame size={12} />
              <span>Kritike</span>
              <span className="font-mono text-[10px] ml-0.5">({criticalCount})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveFilter('SUSPICIOUS')}
              className={`px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                activeFilter === 'SUSPICIOUS'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 border border-amber-500/20'
              }`}
            >
              <AlertTriangle size={12} />
              <span>Dyshime</span>
              <span className="font-mono text-[10px] ml-0.5">({suspiciousCount})</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveFilter('SMOKING_GUN')}
              className={`px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                activeFilter === 'SMOKING_GUN'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 border border-emerald-500/20'
              }`}
            >
              <CheckCircle2 size={12} />
              <span>Smoking Guns</span>
              <span className="font-mono text-[10px] ml-0.5">({smokingCount})</span>
            </button>
          </div>
        </div>

        {/* TRUPI I DITARIT: LISTA E GJETJEVE */}
        <main className="flex-1 overflow-y-auto custom-finance-scroll p-5 space-y-4">
          {filteredFindings.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-text-muted text-center p-8 gap-3">
              <ShieldAlert size={48} className="opacity-25 text-rose-500" />
              <div className="max-w-md space-y-1">
                <p className="text-sm font-bold text-text-primary">
                  {isScanning ? 'Hetuesi po skanon të 31 shkresat dhe provat...' : 'Ditari i Hetuesit është i pastër'}
                </p>
                <p className="text-xs">
                  Shtypni <span className="font-bold text-text-primary">"Nis Hetimin e Thellë"</span> për të kërkuar automatikisht përplasjet midis procesverbaleve, audios dhe vendimeve gjyqësore.
                </p>
              </div>
            </div>
          ) : (
            <div className={`grid gap-4 ${isWidescreen ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1'}`}>
              {filteredFindings.map((item) => {
                const isCritical = item.level === 'CRITICAL';
                const isSmoking = item.level === 'SMOKING_GUN';

                return (
                  <article
                    key={item.id}
                    className={`p-5 rounded-2xl border transition-all space-y-3.5 bg-card shadow-sm ${
                      isCritical
                        ? 'border-rose-500/40 hover:border-rose-500 shadow-rose-500/5'
                        : isSmoking
                        ? 'border-emerald-500/40 hover:border-emerald-500'
                        : 'border-amber-500/40 hover:border-amber-500'
                    }`}
                  >
                    {/* Koka e Kartës së Incidentit */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase ${
                              isCritical
                                ? 'bg-rose-500/15 text-rose-500 border border-rose-500/30'
                                : isSmoking
                                ? 'bg-emerald-500/15 text-emerald-500 border border-emerald-500/30'
                                : 'bg-amber-500/15 text-amber-500 border border-amber-500/30'
                            }`}
                          >
                            {isCritical ? '🔴 Kontradiktë Fatale' : isSmoking ? '🟢 Smoking Gun' : '🟡 Dyshim Procedural'}
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-text-primary leading-snug">{item.title}</h4>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleCopyFinding(item)}
                        title="Kopjo incidentin për shkresë gjyqësore"
                        className="p-1.5 rounded-lg bg-surface hover:bg-hover border border-main text-text-muted hover:text-text-primary transition-colors cursor-pointer shrink-0"
                      >
                        {copiedId === item.id ? <CheckCircle2 size={14} className="text-emerald-500" /> : <Copy size={14} />}
                      </button>
                    </div>

                    {/* Burimet e Përplasjes: Prova A kundër Provës B */}
                    <div className="p-3 rounded-xl bg-surface/70 border border-main text-xs space-y-1.5 font-mono">
                      <div className="flex items-center gap-2 text-text-muted truncate">
                        <FileText size={13} className="text-primary-start shrink-0" />
                        <span className="font-bold text-text-primary truncate">A:</span>
                        <span className="truncate">{item.sourceA}</span>
                      </div>
                      <div className="flex items-center gap-2 text-rose-500 font-bold text-[10px] uppercase">
                        <ArrowRight size={12} className="rotate-90 sm:rotate-0" />
                        <span>Bie ndesh drejtpërdrejt me:</span>
                      </div>
                      <div className="flex items-center gap-2 text-text-muted truncate">
                        <FileText size={13} className="text-rose-500 shrink-0" />
                        <span className="font-bold text-text-primary truncate">B:</span>
                        <span className="truncate">{item.sourceB}</span>
                      </div>
                    </div>

                    {/* Detajet e Përplasjes */}
                    <div className="text-xs text-text-primary leading-relaxed select-text font-sans">
                      <p className="font-bold text-text-muted uppercase text-[10px] tracking-wider mb-1">
                        Zbardhja e Hetuesit:
                      </p>
                      <p className="whitespace-pre-wrap">{item.contradictionDetails}</p>
                    </div>

                    {/* Neni i Shkelur & Taktika e Avokatit */}
                    <div className="pt-2 border-t border-main grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      <div className="p-2.5 rounded-xl bg-surface border border-main space-y-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">Neni i Shkelur:</span>
                        <p className="font-mono font-bold text-primary-start truncate">{item.legalArticles}</p>
                      </div>

                      <div className="p-2.5 rounded-xl bg-primary-start/5 border border-primary-start/20 space-y-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-primary-start">Këshilla Taktike:</span>
                        <p className="text-text-primary text-[11px] truncate">{item.tacticalAdvice}</p>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </main>

        {/* FOOTER I DITARIT */}
        <footer className="p-4 border-t border-main bg-surface/30 flex items-center justify-between text-xs text-text-muted">
          <span className="flex items-center gap-1.5 font-medium">
            <RefreshCw size={12} className={isScanning ? 'animate-spin text-primary-start' : ''} />
            {isScanning ? 'Hetuesi po punon në sfond...' : `${findings.length} incidente të analizuara`}
          </span>
          <span className="font-mono text-[10px]">Modeli: Claude Sonnet 4.6 (1M Token Core)</span>
        </footer>
      </aside>
    </div>
  );
};

export default InvestigatorLogDrawer;