// FILE: frontend/src/components/forensics/FinancialForensicLab.tsx
// PHOENIX PROTOCOL - FORENSIC FINANCIAL LAB V3.1 (ZERO TS WARNINGS & PURE FORENSIC ACCOUNTING)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS • MOBILE & TABLET READY

import React, { useState, useRef, useEffect } from 'react';
import {
  Coins,
  UploadCloud,
  Calculator,
  Calendar,
  DollarSign,
  Percent,
  Loader2,
  Copy,
  FileSpreadsheet,
  TrendingUp,
  Send,
  Scale,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Check,
  FileText
} from 'lucide-react';
import {
  forensicDeskService,
  LMDInterestResponse
} from '../../services/forensicDeskService';

interface FinancialForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

const FONT_LEVELS = [
  { label: '90%',   base: 14,   line: 1.55 },
  { label: '100%',  base: 16,   line: 1.65 },
  { label: '115%',  base: 18,   line: 1.7 },
  { label: '130%',  base: 20,   line: 1.75 },
  { label: '150%',  base: 22,   line: 1.8 }
];

export const FinancialForensicLab: React.FC<FinancialForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  // Gjendjet e Llogaritësit LMD
  const [principalAmount, setPrincipalAmount] = useState<string>('10000');
  const [startDate, setStartDate] = useState<string>('2023-01-01');
  const [endDate, setEndDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [annualRate, setAnnualRate] = useState<string>('8.0');
  const [isCalculatingLmd, setIsCalculatingLmd] = useState<boolean>(false);
  const [lmdResult, setLmdResult] = useState<LMDInterestResponse | null>(null);
  const [copiedFormula, setCopiedFormula] = useState<boolean>(false);

  // Gjendjet e Auditimit Tabelor (Pandas)
  const [isUploadingSpreadsheet, setIsUploadingSpreadsheet] = useState<boolean>(false);
  const [spreadsheetData, setSpreadsheetData] = useState<any | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>('');
  const [copiedAuditSummary, setCopiedAuditSummary] = useState<boolean>(false);

  // Gjendjet e Pyetësorit Financiar
  const [interrogationQuestion, setInterrogationQuestion] = useState<string>('');
  const [isInterrogating, setIsInterrogating] = useState<boolean>(false);
  const [interrogationResult, setInterrogationResult] = useState<string>('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Kontrolli i zmadhimit të shkrimit
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_financial_forensic_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1;
    } catch {
      return 1;
    }
  });
  const activeFont = FONT_LEVELS[fontLevelIndex];

  const handleIncreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.min(FONT_LEVELS.length - 1, prev + 1);
      try { localStorage.setItem('juristi_financial_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleDecreaseFont = () => {
    setFontLevelIndex(prev => {
      const next = Math.max(0, prev - 1);
      try { localStorage.setItem('juristi_financial_forensic_font_size', String(next)); } catch {}
      return next;
    });
  };

  const handleResetFont = () => {
    setFontLevelIndex(1);
    try { localStorage.setItem('juristi_financial_forensic_font_size', '1'); } catch {}
  };

  // Ngarkon rezultatet e fundit nga MongoDB në montim
  useEffect(() => {
    const loadPersistedData = async () => {
      if (!caseId) return;
      try {
        const records = await forensicDeskService.getFinancialRecords(caseId);
        if (Array.isArray(records) && records.length > 0) {
          const latestLmd = records.find(r => r.record_type === 'LMD_CALCULATION');
          if (latestLmd?.result) {
            setLmdResult(latestLmd.result);
          }

          const latestSpreadsheet = records.find(r => r.record_type === 'SPREADSHEET_ANALYSIS');
          if (latestSpreadsheet) {
            setSpreadsheetData(latestSpreadsheet.spreadsheet_analysis ? latestSpreadsheet : latestSpreadsheet);
            setUploadedFileName(latestSpreadsheet.filename || '');
          }
        }
      } catch (err) {
        console.warn("Nuk u ngarkuan të dhënat financiare:", err);
      }
    };

    loadPersistedData();
  }, [caseId]);

  // 1. LLOGARITJA E KAMATËS STATUTORE (LMD 265)
  const handleCalculateLmdInterest = async () => {
    const principal = parseFloat(principalAmount);
    if (isNaN(principal) || principal <= 0) {
      alert("Ju lutem shënoni një shumë të vlefshme të kryegjësë.");
      return;
    }

    setIsCalculatingLmd(true);
    try {
      const res = await forensicDeskService.calculateLegalInterest({
        principal,
        startDate,
        endDate,
        ratePercent: parseFloat(annualRate) || 8.0,
        caseId
      });
      setLmdResult(res);
      if (onEvidenceChange) onEvidenceChange();
    } catch (err: any) {
      console.error("Dështoi llogaritja e kamatës LMD:", err);
      alert(err?.response?.data?.detail || "Dështoi llogaritja ligjore e kamatës.");
    } finally {
      setIsCalculatingLmd(false);
    }
  };

  // 2. NGARKIMI DHE AUDITIMI I PASQYRAVE ME PANDAS
  const handleUploadSpreadsheet = async (files: FileList | null) => {
    if (!files || files.length === 0 || !caseId) return;
    const file = files[0];
    setIsUploadingSpreadsheet(true);
    setUploadedFileName(file.name);

    try {
      const claimed = parseFloat(principalAmount) || undefined;
      const res = await forensicDeskService.analyzeSpreadsheet(
        caseId,
        file,
        claimed,
        `Ekspertizë financiare gjyqësore mbi pretendimin e padisë (${principalAmount} €)`
      );
      setSpreadsheetData(res);
      if (onEvidenceChange) onEvidenceChange();
    } catch (err: any) {
      console.error("Dështoi analiza e pasqyrës financiare:", err);
      alert(err?.response?.data?.detail || "Dështoi leximi dhe auditimi i skedarit Excel/CSV.");
    } finally {
      setIsUploadingSpreadsheet(false);
    }
  };

  // 3. PYETJE MBI PROVAT FINANCIARE
  const handleInterrogateFinances = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!interrogationQuestion.trim() || !caseId || isInterrogating) return;

    setIsInterrogating(true);
    setInterrogationResult('');

    try {
      const res = await forensicDeskService.sendChatMessage(
        caseId,
        `[PYETJE MBI PROVAT FINANCIARE DHE KAMATËN LMD]: ${interrogationQuestion}`,
        `Kryegjëja e kërkuar: ${principalAmount} €, Kamata LMD e llogaritur: ${lmdResult?.interest_amount || 0} €`
      );
      setInterrogationResult(res.content || "Nuk pati përgjigje nga motori hetimor.");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi marrja e përgjigjes nga auditimi.");
    } finally {
      setIsInterrogating(false);
    }
  };

  const handleCopyFormula = () => {
    if (!lmdResult) return;
    const text = `=== LLOGARITJA E KAMATËVONESËS LIGJORE (LMD NENI 265 & 277) ===
Kryegjëja: ${lmdResult.principal.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
Periudha e Vonesës: ${lmdResult.start_date} deri më ${lmdResult.end_date} (${lmdResult.days_elapsed} ditë)
Norma Vjetore: ${lmdResult.interest_rate_annual}%
Kamata Ditore: ${lmdResult.daily_accrual} € / ditë
Kamata e Grumbulluar: ${lmdResult.interest_amount.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
Detyrimi Total: ${lmdResult.total_obligation.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
Baza Juridike: ${lmdResult.legal_basis}`;

    navigator.clipboard.writeText(text);
    setCopiedFormula(true);
    setTimeout(() => setCopiedFormula(false), 2500);
  };

  const handleCopyAuditSummary = () => {
    if (!spreadsheetData) return;
    const opinion = spreadsheetData.forensic_opinion;
    const analysis = spreadsheetData.spreadsheet_analysis;
    const disc = analysis?.discrepancy_with_claim;

    const text = `=== RAPORTI I EKSPERTIZËS FINANCIARE FORENZIKE ===
Skedari i Audituar: ${uploadedFileName}
Verdikti i Auditimit: ${opinion?.financial_audit_verdict || 'I AUDITUAR'}

REZULTATI KONTABËL:
- Hyrjet Totale (Kredi): ${analysis?.total_inflows?.toLocaleString('sq-AL', { minimumFractionDigits: 2 }) || '0.00'} €
- Daljet Totale (Debi): ${analysis?.total_outflows?.toLocaleString('sq-AL', { minimumFractionDigits: 2 }) || '0.00'} €
- Fluksi Neto Monetar: ${analysis?.net_cash_flow?.toLocaleString('sq-AL', { minimumFractionDigits: 2 }) || '0.00'} €
- Shuma e Dokumentuar: ${analysis?.total_documented_amount?.toLocaleString('sq-AL', { minimumFractionDigits: 2 }) || '0.00'} €

KRAHASIMI ME PADINË:
- Pretendimi në Padi: ${disc?.claimed_in_suit?.toLocaleString('sq-AL', { minimumFractionDigits: 2 }) || 'N/A'} €
- Provuar me Pasqyrë: ${disc?.documented_in_sheet?.toLocaleString('sq-AL', { minimumFractionDigits: 2 }) || 'N/A'} €
- Diferenca (Delta): ${disc?.delta?.toLocaleString('sq-AL', { minimumFractionDigits: 2 }) || 'N/A'} €
- Statusi: ${disc?.status || 'N/A'}

KONKLUZIONI I EKSPERTIT:
${opinion?.expert_concluding_summary || ''}`;

    navigator.clipboard.writeText(text);
    setCopiedAuditSummary(true);
    setTimeout(() => setCopiedAuditSummary(false), 2500);
  };

  const analysis = spreadsheetData?.spreadsheet_analysis;
  const opinion = spreadsheetData?.forensic_opinion;
  const discrepancy = analysis?.discrepancy_with_claim;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 select-none">
      
      {/* KOLONA E MAJTË: LLOGARITËSI LMD & NGARKIMI I TABELAVE */}
      <div className="lg:col-span-5 space-y-4">
        
        {/* PËRLLOGARITËSI STATUTOR I KAMATËVONESËS LIGJORE (LMD 265) */}
        <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3.5">
          <div className="flex items-center justify-between border-b border-main pb-2.5">
            <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Calculator size={15} className="text-primary-start" /> Kamata Ligjore LMD (Neni 265)
            </h3>
            <span className="text-[10px] sm:text-xs font-mono px-2 py-0.5 rounded-full bg-primary-start/15 text-primary-start font-bold">
              8% Statutore
            </span>
          </div>

          <div className="space-y-3 text-xs sm:text-sm">
            <div>
              <label className="block text-text-muted font-bold mb-1 flex items-center gap-1 text-xs">
                <DollarSign size={13} className="text-primary-start" /> Shuma e Kryegjësë (€) *
              </label>
              <input
                type="number"
                value={principalAmount}
                onChange={(e) => setPrincipalAmount(e.target.value)}
                placeholder="p.sh. 15000"
                className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary font-mono text-sm sm:text-base font-bold focus:outline-none focus:border-primary-start"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <div>
                <label className="block text-text-muted font-bold mb-1 flex items-center gap-1 text-xs">
                  <Calendar size={13} className="text-primary-start" /> Fillimi i Vonesës
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary text-xs focus:outline-none focus:border-primary-start"
                />
              </div>

              <div>
                <label className="block text-text-muted font-bold mb-1 flex items-center gap-1 text-xs">
                  <Calendar size={13} className="text-primary-start" /> Data e Përfundimit
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
              <label className="block text-text-muted font-bold mb-1 flex items-center gap-1 text-xs">
                <Percent size={13} className="text-primary-start" /> Shkalla Vjetore e Kamatës (%)
              </label>
              <input
                type="number"
                step="0.1"
                value={annualRate}
                onChange={(e) => setAnnualRate(e.target.value)}
                className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary font-mono text-xs focus:outline-none focus:border-primary-start font-medium"
              />
            </div>

            <button
              type="button"
              onClick={handleCalculateLmdInterest}
              disabled={isCalculatingLmd}
              className="w-full h-10 bg-primary-start hover:bg-primary-start/90 text-white font-bold rounded-xl text-xs uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer shadow-sm transition-all"
            >
              {isCalculatingLmd ? <Loader2 size={15} className="animate-spin" /> : <Calculator size={15} />}
              <span>Llogarit Kamatën Ligjore</span>
            </button>
          </div>

          {/* PASQYRA STATUTORE E LLOGARITJES */}
          {lmdResult && (
            <div className="p-3.5 sm:p-4 rounded-xl sm:rounded-2xl bg-surface border border-main space-y-3">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-xl bg-card border border-main">
                  <span className="text-text-muted text-[10px] block font-bold uppercase">Ditë Vonese:</span>
                  <span className="font-mono font-bold text-sm text-text-primary">{lmdResult.days_elapsed} ditë</span>
                </div>
                <div className="p-2.5 rounded-xl bg-card border border-main">
                  <span className="text-text-muted text-[10px] block font-bold uppercase">Kamata Ditore:</span>
                  <span className="font-mono font-bold text-xs sm:text-sm text-text-muted">{lmdResult.daily_accrual} €</span>
                </div>
                <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                  <span className="text-emerald-500 text-[10px] block font-bold uppercase">Kamata (8%):</span>
                  <span className="font-mono font-bold text-xs sm:text-sm text-emerald-500">
                    +{lmdResult.interest_amount.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-primary-start/10 border border-primary-start/20">
                  <span className="text-primary-start text-[10px] block font-bold uppercase">Detyrimi Total:</span>
                  <span className="font-mono font-black text-xs sm:text-sm text-primary-start">
                    {lmdResult.total_obligation.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1 border-t border-main text-xs">
                <span className="text-[10px] text-text-muted truncate max-w-[200px]">Neni 265 & 277 LMD</span>
                <button
                  type="button"
                  onClick={handleCopyFormula}
                  className="px-2.5 py-1 rounded-lg bg-surface hover:bg-hover border border-main text-text-primary text-[11px] font-bold flex items-center gap-1 cursor-pointer transition-colors"
                >
                  {copiedFormula ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                  <span>{copiedFormula ? 'U Kopjua!' : 'Kopjo Përllogaritjen'}</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* NGARKIMI I DOKUMENTIT TABELOR PËR PANDAS AUDIT */}
        <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-main pb-2">
            <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <FileSpreadsheet size={15} className="text-primary-start" /> Auditimi i Pasqyrave Financiare
            </h3>
            <span className="text-[10px] font-mono text-primary-start font-bold">Pandas Engine</span>
          </div>

          <div
            onClick={() => !isUploadingSpreadsheet && fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!isUploadingSpreadsheet) handleUploadSpreadsheet(e.dataTransfer.files);
            }}
            className="border-2 border-dashed border-main hover:border-primary-start/50 bg-surface/50 rounded-xl sm:rounded-2xl p-4 sm:p-5 text-center cursor-pointer transition-all hover:bg-surface flex flex-col items-center justify-center gap-2"
          >
            {isUploadingSpreadsheet ? (
              <div className="flex flex-col items-center justify-center gap-2 py-2">
                <Loader2 size={22} className="animate-spin text-primary-start" />
                <span className="text-xs sm:text-sm font-bold text-primary-start">Duke audituar me motorin Pandas...</span>
              </div>
            ) : (
              <>
                <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <UploadCloud size={20} />
                </div>
                <div>
                  <p className="text-xs sm:text-sm font-bold text-text-primary">Ngarko Pasqyrë Bankare (Excel / CSV)</p>
                  <p className="text-[11px] text-text-muted mt-0.5">Analizë e hyrjeve, daljeve dhe ballafaqim me padinë</p>
                </div>
              </>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => handleUploadSpreadsheet(e.target.files)}
          />
        </div>
      </div>

      {/* KOLONA E DJATHTË: PASQYRA DHE EKSPERTIZA FINANCIARE FORENZIKE */}
      <div className="lg:col-span-7 space-y-4">
        
        {/* PYETËSORI FORENZIK MBI SHIFRAT */}
        <div className="glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h3 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-1.5">
              <Coins size={15} className="text-primary-start" /> Pyetje mbi Provat Financiare
            </h3>
            
            {/* Kontrolli i Fontit me Buton të Vërtetë Reset */}
            <div className="flex items-center gap-1 rounded-xl border border-main bg-surface p-0.5" aria-label="Madhësia e shkrimit">
              <button
                type="button"
                onClick={handleDecreaseFont}
                disabled={fontLevelIndex === 0}
                className="h-6 w-6 rounded text-xs font-bold text-text-muted hover:bg-hover text-center disabled:opacity-30 cursor-pointer"
                title="Zvogëlo shkrimin"
              >
                A−
              </button>
              <button
                type="button"
                onClick={handleResetFont}
                title="Rivendos madhësinë e shkrimit në 100%"
                className="min-w-7 text-[10px] font-bold text-text-muted hover:bg-hover rounded text-center cursor-pointer px-1"
              >
                {activeFont.label}
              </button>
              <button
                type="button"
                onClick={handleIncreaseFont}
                disabled={fontLevelIndex === FONT_LEVELS.length - 1}
                className="h-6 w-6 rounded text-xs font-bold text-text-muted hover:bg-hover text-center disabled:opacity-30 cursor-pointer"
                title="Zmadho shkrimin"
              >
                A+
              </button>
            </div>
          </div>

          <form onSubmit={handleInterrogateFinances} className="flex gap-2">
            <input
              type="text"
              value={interrogationQuestion}
              onChange={(e) => setInterrogationQuestion(e.target.value)}
              placeholder="Pyet p.sh.: Sa është diferenca mes padisë dhe pasqyrës?"
              className="flex-1 bg-surface border border-main rounded-xl px-3 py-2 text-xs sm:text-sm text-text-primary focus:outline-none focus:border-primary-start"
            />
            <button
              type="submit"
              disabled={isInterrogating || !interrogationQuestion.trim()}
              className="px-3.5 sm:px-4 py-2 bg-primary-start hover:bg-primary-start/90 text-white text-xs sm:text-sm font-bold rounded-xl shadow-xs transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shrink-0"
            >
              {isInterrogating ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              <span>Pyet</span>
            </button>
          </form>

          {interrogationResult && (
            <div 
              className="p-3 bg-surface/60 rounded-xl border border-main text-text-primary leading-relaxed select-text text-xs sm:text-sm font-medium"
              style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
            >
              {interrogationResult}
            </div>
          )}
        </div>

        {/* PASQYRA KRYESORE E KONTABILITETIT FORENZIK */}
        <div className="glass-panel p-4 sm:p-6 rounded-2xl sm:rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-main pb-3">
            <div>
              <h3 className="text-xs sm:text-base font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
                <TrendingUp size={16} className="text-primary-start" /> Ekspertiza Financiare e Pasqyrave
              </h3>
              <p className="text-[11px] sm:text-xs text-text-muted mt-0.5 truncate max-w-sm sm:max-w-md">
                {uploadedFileName ? `Dokumenti: ${uploadedFileName}` : 'Ngarkoni një skedar Excel/CSV për auditim automatik'}
              </p>
            </div>

            {spreadsheetData && (
              <button
                type="button"
                onClick={handleCopyAuditSummary}
                className="h-8 sm:h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary flex items-center gap-1.5 cursor-pointer self-end sm:self-auto"
              >
                {copiedAuditSummary ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
                <span>{copiedAuditSummary ? 'U Kopjua' : 'Kopjo Raportin'}</span>
              </button>
            )}
          </div>

          <div
            className="min-h-[320px] max-h-[580px] overflow-y-auto custom-finance-scroll p-3 sm:p-5 bg-surface/40 rounded-xl sm:rounded-2xl border border-main text-text-primary select-text space-y-4"
            style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
          >
            {spreadsheetData ? (
              <div className="space-y-4">
                
                {/* Verdikti i Ekspertizës */}
                <div className="flex items-center justify-between p-3 rounded-xl bg-surface border border-main flex-wrap gap-2">
                  <span className="text-xs font-bold uppercase text-text-muted">Verdikti Kontabël:</span>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase ${
                    opinion?.financial_audit_verdict?.includes('FRYRJE') || opinion?.financial_audit_verdict?.includes('ANOMALI')
                      ? 'bg-rose-500/20 text-rose-500 border border-rose-500/30'
                      : 'bg-emerald-500/20 text-emerald-500 border border-emerald-500/30'
                  }`}>
                    {opinion?.financial_audit_verdict || 'I AUDITUAR'}
                  </span>
                </div>

                {/* Pasqyra e Pajtimit Kontabël (Reconciliation Cards) */}
                {analysis && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="p-3 rounded-xl bg-card border border-main">
                      <span className="text-text-muted text-[10px] block font-bold uppercase flex items-center gap-1">
                        <ArrowDownRight size={12} className="text-emerald-500" /> Hyrje (Kredit)
                      </span>
                      <span className="font-mono font-bold text-xs sm:text-sm text-emerald-500">
                        {analysis.total_inflows?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-card border border-main">
                      <span className="text-text-muted text-[10px] block font-bold uppercase flex items-center gap-1">
                        <ArrowUpRight size={12} className="text-rose-500" /> Dalje (Debi)
                      </span>
                      <span className="font-mono font-bold text-xs sm:text-sm text-rose-500">
                        {analysis.total_outflows?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-card border border-main">
                      <span className="text-text-muted text-[10px] block font-bold uppercase">
                        Fluksi Neto
                      </span>
                      <span className={`font-mono font-bold text-xs sm:text-sm ${analysis.net_cash_flow >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                        {analysis.net_cash_flow?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-primary-start/10 border border-primary-start/20">
                      <span className="text-primary-start text-[10px] block font-bold uppercase">
                        I Dokumentuar
                      </span>
                      <span className="font-mono font-black text-xs sm:text-sm text-primary-start">
                        {analysis.total_documented_amount?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                      </span>
                    </div>
                  </div>
                )}

                {/* Krahasimi me Padinë (Delta / Discrepancy) */}
                {discrepancy && (
                  <div className="p-3.5 rounded-xl bg-card border border-main space-y-2">
                    <h4 className="font-bold text-xs sm:text-sm text-text-primary flex items-center gap-1.5 uppercase">
                      <Scale size={14} className="text-primary-start" /> Krahasimi i Padisë me Transaksionet Reale:
                    </h4>
                    
                    <div className="grid grid-cols-3 gap-2 font-mono text-xs pt-1">
                      <div className="p-2 rounded-lg bg-surface border border-main">
                        <span className="text-[10px] text-text-muted block">Pretendimi:</span>
                        <span className="font-bold">{discrepancy.claimed_in_suit?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €</span>
                      </div>
                      <div className="p-2 rounded-lg bg-surface border border-main">
                        <span className="text-[10px] text-text-muted block">Dokumentuar:</span>
                        <span className="font-bold text-emerald-500">{discrepancy.documented_in_sheet?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €</span>
                      </div>
                      <div className="p-2 rounded-lg bg-surface border border-main">
                        <span className="text-[10px] text-text-muted block">Diferenca (Delta):</span>
                        <span className={`font-bold ${discrepancy.delta > 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                          {discrepancy.delta?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                        </span>
                      </div>
                    </div>

                    <p className="text-[11px] text-text-muted font-medium pt-1">
                      <span className="font-bold text-amber-500">Vlerësimi Procedural:</span> {discrepancy.audit_explanation || discrepancy.status}
                    </p>
                  </div>
                )}

                {/* Flamujt e Kuq (Red Flags & Tërheqje Kesh) */}
                {analysis?.red_flags?.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 space-y-2">
                    <h4 className="font-bold text-xs sm:text-sm text-rose-500 flex items-center gap-1.5 uppercase">
                      <AlertTriangle size={14} /> Flamuj të Kuq Kontabël ({analysis.red_flags.length}):
                    </h4>
                    <div className="space-y-1.5 text-xs">
                      {analysis.red_flags.map((rf: any, i: number) => (
                        <div key={i} className="p-2 rounded-lg bg-surface border border-rose-500/30 flex items-center justify-between gap-2 flex-wrap">
                          <div className="min-w-0">
                            <span className="font-mono text-[10px] text-text-muted mr-2">{rf.date}</span>
                            <span className="font-bold text-text-primary">{rf.description || 'Tërheqje'}</span>
                          </div>
                          <div className="font-mono font-bold text-rose-500 text-xs shrink-0">
                            {rf.amount?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Mostra e Transaksioneve Kryesore të Audituara */}
                {analysis?.top_transactions_sample?.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-surface border border-main space-y-2">
                    <h4 className="font-bold text-xs sm:text-sm text-text-primary uppercase flex items-center gap-1.5">
                      <FileText size={14} className="text-primary-start" /> Mostra e Transaksioneve Kryesore:
                    </h4>
                    <div className="overflow-x-auto scrollbar-none">
                      <table className="w-full text-left text-xs font-mono">
                        <thead>
                          <tr className="border-b border-main text-text-muted text-[10px] uppercase">
                            <th className="py-1.5 pr-2">Data</th>
                            <th className="py-1.5 pr-2">Përshkrimi</th>
                            <th className="py-1.5 text-right">Vlera</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-main">
                          {analysis.top_transactions_sample.map((row: any, i: number) => (
                            <tr key={i} className="hover:bg-hover/50">
                              <td className="py-1.5 pr-2 text-text-muted whitespace-nowrap">{row.date}</td>
                              <td className="py-1.5 pr-2 truncate max-w-[200px] text-text-primary">{row.description}</td>
                              <td className="py-1.5 text-right font-bold text-text-primary whitespace-nowrap">{row.amount?.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Konkluzioni i Ekspertit Financiar Forenzik */}
                {opinion?.expert_concluding_summary && (
                  <div className="p-3.5 rounded-xl bg-card border border-main space-y-1.5">
                    <h4 className="font-bold text-xs uppercase text-text-primary">
                      Përmbledhja Ekzekutive për Gjykatën:
                    </h4>
                    <p className="text-xs leading-relaxed text-text-primary whitespace-pre-wrap font-medium">
                      {opinion.expert_concluding_summary}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-2.5 py-16">
                <Coins size={36} className="text-primary-start/30" />
                <p className="text-xs sm:text-sm max-w-xs">
                  Ngarkoni një pasqyrë bankare majtas ose llogarisni kamatën për të parë ekspertizën forenzike me shifra reale.
                </p>
              </div>
            )}
          </div>

          <div className="pt-2 flex items-center justify-between text-[11px] text-text-muted border-t border-main">
            <span>Ligji Nr. 04/L-077 për Marrëdhëniet e Detyrimeve (LMD)</span>
            <span className="font-mono text-[10px]">Standardi: Nenet 265 & 277</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinancialForensicLab;