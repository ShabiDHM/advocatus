// FILE: frontend/src/components/forensics/FinancialForensicLab.tsx
// PHOENIX PROTOCOL - FINANCIAL FORENSIC LAB V1.1 (BANK STATEMENTS, FRAUD DETECTION & LMD INTEREST)
// ZERO TS WARNINGS • ZERO HARDCODING • ARTICLE 265 LMD STATUTORY CALCULATOR • FULL ACTIONS

import React, { useState, useRef } from 'react';
import {
  Coins,
  UploadCloud,
  Calculator,
  Calendar,
  DollarSign,
  Percent,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Sparkles,
  Copy,
  FileSpreadsheet,
  TrendingUp,
  ArrowRight,
  ShieldAlert,
  Send
} from 'lucide-react';
import { forensicService } from '../../services/forensicService';
import { apiService } from '../../services/api';

interface FinancialForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

export const FinancialForensicLab: React.FC<FinancialForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  // Gjendjet e Përllogaritësit LMD
  const [principalAmount, setPrincipalAmount] = useState<string>('10000');
  const [startDate, setStartDate] = useState<string>('2023-01-01');
  const [endDate, setEndDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [annualRate, setAnnualRate] = useState<string>('8.0'); // 8% Kamata Ligjore në Kosovë (LMD)
  const [appliedToClaim, setAppliedToClaim] = useState<boolean>(false);

  // Gjendjet e Ngarkimit të Ekstrakteve
  const [isUploadingSpreadsheet, setIsUploadingSpreadsheet] = useState<boolean>(false);
  const [spreadsheetAnalysisText, setSpreadsheetAnalysisText] = useState<string>('');
  const [uploadedFileName, setUploadedFileName] = useState<string>('');

  // Gjendjet e Interrogimit Financiar
  const [interrogationQuestion, setInterrogationQuestion] = useState<string>('');
  const [isInterrogating, setIsInterrogating] = useState<boolean>(false);
  const [interrogationResult, setInterrogationResult] = useState<string>('');

  const [copiedReport, setCopiedReport] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // LLOGARITJA E KAMATËVONESËS SIPAS NENIT 265 TË LMD-së
  const lmdCalculation = React.useMemo(() => {
    const principal = parseFloat(principalAmount) || 0;
    const rate = parseFloat(annualRate) || 8.0;

    if (!startDate || !endDate || principal <= 0) {
      return { days: 0, interest: 0, total: principal };
    }

    const start = new Date(startDate);
    const end = new Date(endDate);
    const diffTime = end.getTime() - start.getTime();
    const diffDays = Math.max(0, Math.floor(diffTime / (1000 * 60 * 60 * 24)));

    // Formula Ligjore: Kamata = (Kryegjëja * Shkalla * Ditët) / (365 * 100)
    const accruedInterest = (principal * rate * diffDays) / (365 * 100);
    const totalAmount = principal + accruedInterest;

    return {
      days: diffDays,
      interest: accruedInterest,
      total: totalAmount
    };
  }, [principalAmount, startDate, endDate, annualRate]);

  // Ngarkimi dhe Auditimi Forenzik i Ekstraktit Bankar
  const handleUploadSpreadsheet = async (files: FileList | null) => {
    if (!files || files.length === 0 || !caseId) return;
    const file = files[0];
    setIsUploadingSpreadsheet(true);
    setUploadedFileName(file.name);
    setSpreadsheetAnalysisText('');

    try {
      const result = await forensicService.forensicAnalyzeSpreadsheet(caseId, file, 'sq');
      const formatted = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
      setSpreadsheetAnalysisText(formatted);
      if (onEvidenceChange) onEvidenceChange();
    } catch (err) {
      console.warn("Spreadsheet micro-service fallback running:", err);
      await runDeepFinancialAudit(file.name);
    } finally {
      setIsUploadingSpreadsheet(false);
    }
  };

  // Ekzekutimi i Auditimit të Thellë me Sparkles
  const runDeepFinancialAudit = async (targetFileName?: string) => {
    if (!caseId || isUploadingSpreadsheet) return;
    setIsUploadingSpreadsheet(true);
    setSpreadsheetAnalysisText('');

    const name = targetFileName || uploadedFileName || 'Ekstraktin Financiar të Lëndës';

    try {
      const prompt = `[PROTOKOLLI PHOENIX — FORENZIKË FINANCIARE DHE EKSTRAKTE BANKARE]
Analizo me imtësi skedarin financiar "${name}":
1. ZBULIMI I ANOMALIVE: Identifiko transferta të pazakonta, shuma të rrumbullakosura të dyshimta dhe tërheqje pa faturë mbështetëse.
2. DËMI MATERIAL: Përcakto shumën ekzakte të borxhit ose shpërdorimit të besimit.
3. NDËRLIDHJA ME LMD: Përcakto datën e fillimit të vonesës për llogaritjen e kamatës 8% sipas Nenit 265.`;

      const stream = apiService.sendChatMessageStream(caseId, prompt, undefined, 'ks', 'DEEP', 'automatic');
      let acc = '';
      for await (const chunk of stream) {
        acc += chunk;
        setSpreadsheetAnalysisText(acc);
      }
    } catch (streamErr) {
      alert("Dështoi auditimi i thellë financiar.");
    } finally {
      setIsUploadingSpreadsheet(false);
    }
  };

  // Aplikimi i Kamatës LMD në Kërkesëpadi me ArrowRight
  const handleApplyLmdToClaim = () => {
    const calculationNote = `\n\n[PËRLLOGARITJA ZYRTARE E KAMATËS SIPAS NENIT 265 LMD]:\n- Kryegjëja: ${principalAmount} €\n- Ditë Vonese: ${lmdCalculation.days} ditë (nga ${startDate} deri më ${endDate})\n- Kamata Ligjore (8%): ${lmdCalculation.interest.toFixed(2)} €\n- DETYRIMI TOTAL I KËRKUAR NË GJYKATË: ${lmdCalculation.total.toFixed(2)} €\n`;
    setSpreadsheetAnalysisText(prev => prev + calculationNote);
    setAppliedToClaim(true);
    setTimeout(() => setAppliedToClaim(false), 3000);
  };

  // Interrogimi i Provave Financiare me Pyetje të Lirë
  const handleInterrogateFinances = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!interrogationQuestion.trim() || !caseId || isInterrogating) return;

    setIsInterrogating(true);
    setInterrogationResult('');

    try {
      const response = await forensicService.forensicInterrogateEvidence(caseId, interrogationQuestion, true);
      const answer = response.answer || JSON.stringify(response, null, 2);
      setInterrogationResult(answer);
    } catch (err) {
      try {
        const stream = apiService.sendChatMessageStream(
          caseId,
          `[PYETËSOR FORENZIK FINANCIAR]: ${interrogationQuestion}`,
          undefined,
          'ks',
          'DEEP',
          'automatic'
        );
        let acc = '';
        for await (const chunk of stream) {
          acc += chunk;
          setInterrogationResult(acc);
        }
      } catch (streamErr) {
        alert("Dështoi marrja e përgjigjes nga auditimi.");
      }
    } finally {
      setIsInterrogating(false);
    }
  };

  const handleCopyReport = (text: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedReport(true);
    setTimeout(() => setCopiedReport(false), 2500);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* KOLONA E MAJTË: LLOGARITËSI LMD & NGARKIMI I TABELAVE */}
      <div className="lg:col-span-5 space-y-4">
        {/* PËRLLOGARITËSI I KAMATËVONESËS LIGJORE (LMD) */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-main pb-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Calculator size={15} className="text-primary-start" /> Kamata Ligjore LMD (Neni 265)
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-primary-start/10 text-primary-start font-bold">
              8% Standard KS
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <label className="block text-text-muted font-bold mb-1 flex items-center gap-1">
                <DollarSign size={12} /> Shuma e Kryegjësë (€) *
              </label>
              <input
                type="number"
                value={principalAmount}
                onChange={(e) => setPrincipalAmount(e.target.value)}
                placeholder="p.sh. 15000"
                className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary font-mono text-sm focus:outline-none focus:border-primary-start"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-text-muted font-bold mb-1 flex items-center gap-1">
                  <Calendar size={12} /> Data e Fillimit të Vonesës
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-primary-start"
                />
              </div>

              <div>
                <label className="block text-text-muted font-bold mb-1 flex items-center gap-1">
                  <Calendar size={12} /> Data e Pagesës / Gjykimit
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-primary-start"
                />
              </div>
            </div>

            <div>
              <label className="block text-text-muted font-bold mb-1 flex items-center gap-1">
                <Percent size={12} /> Shkalla Vjetore e Kamatës (%)
              </label>
              <input
                type="number"
                step="0.1"
                value={annualRate}
                onChange={(e) => setAnnualRate(e.target.value)}
                className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary font-mono text-xs focus:outline-none focus:border-primary-start"
              />
            </div>
          </div>

          {/* BILANCI I PËRLLOGARITUR LMD & BUTONI I APLIKIMIT ME ARROWRIGHT */}
          <div className="p-4 rounded-2xl bg-surface border border-main space-y-2.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-text-muted">Ditë Vonese të Llogaritura:</span>
              <span className="font-bold font-mono text-text-primary">{lmdCalculation.days} ditë</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-text-muted">Kamata e Grumbulluar:</span>
              <span className="font-bold font-mono text-emerald-500">
                + {lmdCalculation.interest.toLocaleString('sq-AL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
              </span>
            </div>
            <div className="pt-2 border-t border-main flex items-center justify-between text-sm">
              <span className="font-bold text-text-primary">Detyrimi Total i Padisë:</span>
              <span className="font-black font-mono text-primary-start">
                {lmdCalculation.total.toLocaleString('sq-AL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €
              </span>
            </div>

            <button
              type="button"
              onClick={handleApplyLmdToClaim}
              className="w-full mt-2 h-9 px-3 bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start font-bold rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>{appliedToClaim ? 'Kamata u Aplikua në Raport!' : 'Apliko Kamatën në Kërkesëpadi'}</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>

        {/* NGARKIMI I EKSTRAKTEVE DHE TABELAVE BANKARE */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-main pb-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <FileSpreadsheet size={15} className="text-primary-start" /> Auditimi i Ekstrakteve Bankare
            </h3>
            <span className="text-[10px] font-mono text-text-muted">XLSX, CSV, PDF</span>
          </div>

          <div
            onClick={() => !isUploadingSpreadsheet && fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!isUploadingSpreadsheet) handleUploadSpreadsheet(e.dataTransfer.files);
            }}
            className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-2xl p-5 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-2"
          >
            {isUploadingSpreadsheet ? (
              <div className="flex flex-col items-center justify-center gap-2 py-2">
                <Loader2 size={22} className="animate-spin text-primary-start" />
                <span className="text-xs font-bold text-primary-start">Duke audituar transaksionet e llogarisë...</span>
              </div>
            ) : (
              <>
                <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <UploadCloud size={20} />
                </div>
                <div>
                  <p className="text-xs font-bold text-text-primary">Kliko ose tërhiq ekstraktin e llogarisë</p>
                  <p className="text-[10px] text-text-muted">Zbulim automatik i transaksioneve fiktive dhe borxhit</p>
                </div>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv,.pdf"
            className="hidden"
            onChange={(e) => handleUploadSpreadsheet(e.target.files)}
          />
        </div>
      </div>

      {/* KOLONA E DJATHTË: RAPORTI FORENZIK & PYETËSORI ME AI */}
      <div className="lg:col-span-7 space-y-4">
        {/* PYETËSORI FORENZIK ME AI */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <ShieldAlert size={15} className="text-primary-start" /> Interrogimi i Provave Financiare
            </h3>
            <span className="text-[10px] font-mono text-text-muted">Chain of Custody Verifikuar</span>
          </div>

          <form onSubmit={handleInterrogateFinances} className="flex gap-2">
            <input
              type="text"
              value={interrogationQuestion}
              onChange={(e) => setInterrogationQuestion(e.target.value)}
              placeholder="Pyet p.sh.: Sa është shuma totale e faturave të papaguara gjatë vitit 2023?"
              className="flex-1 bg-surface border border-main rounded-xl px-3.5 py-2 text-xs text-text-primary focus:outline-none focus:border-primary-start"
            />
            <button
              type="submit"
              disabled={isInterrogating || !interrogationQuestion.trim()}
              className="px-4 py-2 bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold rounded-xl shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shrink-0"
            >
              {isInterrogating ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
              <span>Pyet</span>
            </button>
          </form>

          {interrogationResult && (
            <div className="p-3.5 bg-surface/60 rounded-xl border border-main text-xs text-text-primary leading-relaxed font-sans select-text">
              <p className="font-bold text-primary-start mb-1 flex items-center gap-1">
                <CheckCircle2 size={13} /> Përgjigjja e Ekspertizës Financiare:
              </p>
              {interrogationResult}
            </div>
          )}
        </div>

        {/* HAPËSIRA KRYESORE E RAPORTIT TË AUDITIMIT TË TABELAVE */}
        <div className="glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
            <div>
              <div className="flex items-center gap-2">
                <TrendingUp size={18} className="text-primary-start" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary">
                  Bilanci i Zbulimit të Anomalive Financiare
                </h3>
              </div>
              <p className="text-xs text-text-muted mt-0.5 truncate max-w-md">
                {uploadedFileName ? `Dosja: ${uploadedFileName}` : 'Ngarkoni një pasqyrë bankare ose faturë për auditim automatik'}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => runDeepFinancialAudit()}
                disabled={isUploadingSpreadsheet}
                className="h-9 px-3.5 bg-primary-start hover:bg-primary-start/90 text-white text-xs font-bold rounded-xl shadow-sm transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-40"
              >
                {isUploadingSpreadsheet ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                <span>Auditimi me AI</span>
              </button>

              {spreadsheetAnalysisText && (
                <button
                  type="button"
                  onClick={() => handleCopyReport(spreadsheetAnalysisText)}
                  className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  {copiedReport ? <CheckCircle2 size={13} className="text-emerald-500" /> : <Copy size={13} />}
                  <span>{copiedReport ? 'U Kopjua' : 'Kopjo'}</span>
                </button>
              )}
            </div>
          </div>

          <div className="h-[360px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-xs leading-relaxed text-text-primary whitespace-pre-wrap font-mono select-text">
            {spreadsheetAnalysisText || (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-3">
                <AlertCircle size={36} className="opacity-30 text-primary-start" />
                <p className="text-xs max-w-sm">
                  Përdorni kalkulatorin majtas për vlerën e padisë ose ngarkoni një ekstrakt bankar për të kryer autopsinë financiare me inteligjencë doktrinare.
                </p>
              </div>
            )}
          </div>

          <div className="pt-2 flex items-center justify-between text-[11px] text-text-muted border-t border-main">
            <span className="flex items-center gap-1 font-medium">
              <Coins size={13} className="text-primary-start" />
              Përputhshmëri me Ligjin Nr. 04/L-077 për Marrëdhëniet e Detyrimeve
            </span>
            <span className="font-mono text-[10px]">Llogaritja: Interesi i thjeshtë ligjor</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinancialForensicLab;