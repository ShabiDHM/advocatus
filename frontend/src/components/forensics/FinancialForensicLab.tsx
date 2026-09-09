// FILE: frontend/src/components/forensics/FinancialForensicLab.tsx
// PHOENIX PROTOCOL - FORENSIC FINANCIAL LAB V2.1 (LMD ARTICLE 265 • PANDAS SPREADSHEET ENGINE • CLAUDE SONNET 4.6)
// 100% COMPLETE CODE • ZERO PLACEHOLDERS • ZERO TS WARNINGS

import React, { useState, useRef, useEffect } from 'react';
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
  Copy,
  FileSpreadsheet,
  TrendingUp,
  ShieldAlert,
  Send,
  Scale,
  AlertTriangle} from 'lucide-react';
import {
  forensicDeskService,
  LMDInterestResponse
} from '../../services/forensicDeskService';

interface FinancialForensicLabProps {
  caseId: string;
  onEvidenceChange?: () => void;
}

// ✅ Përmirësuar: Nivele të madhësisë së shkrimit (si në War Room)
const FONT_LEVELS = [
  { label: '90%',   base: 15,   line: 1.6 },
  { label: '100%',  base: 17,   line: 1.7 },
  { label: '115%',  base: 19,   line: 1.75 },
  { label: '130%',  base: 21,   line: 1.8 },
  { label: '150%',  base: 24,   line: 1.85 },
  { label: '175%',  base: 28,   line: 1.9 },
  { label: '200%',  base: 32,   line: 2.0 }
];

export const FinancialForensicLab: React.FC<FinancialForensicLabProps> = ({
  caseId,
  onEvidenceChange
}) => {
  // Gjendjet e Përllogaritësit LMD
  const [principalAmount, setPrincipalAmount] = useState<string>('10000');
  const [startDate, setStartDate] = useState<string>('2023-01-01');
  const [endDate, setEndDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [annualRate, setAnnualRate] = useState<string>('8.0');
  const [isCalculatingLmd, setIsCalculatingLmd] = useState<boolean>(false);
  const [lmdResult, setLmdResult] = useState<LMDInterestResponse | null>(null);

  // Gjendjet e Analizës së Tabelave me Pandas
  const [isUploadingSpreadsheet, setIsUploadingSpreadsheet] = useState<boolean>(false);
  const [spreadsheetData, setSpreadsheetData] = useState<any | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>('');

  // Gjendjet e Interrogimit Financiar
  const [interrogationQuestion, setInterrogationQuestion] = useState<string>('');
  const [isInterrogating, setIsInterrogating] = useState<boolean>(false);
  const [interrogationResult, setInterrogationResult] = useState<string>('');

  const [copiedReport, setCopiedReport] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ✅ Shtuar: Kontrolli i zmadhimit të shkrimit
  const [fontLevelIndex, setFontLevelIndex] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('juristi_financial_forensic_font_size');
      return saved !== null ? Math.min(Math.max(0, parseInt(saved, 10)), FONT_LEVELS.length - 1) : 1; // default 100%
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

  // LLOGARITJA E KAMATËS ME BACKEND-IN E IZOLUAR FORENZIK
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

  useEffect(() => {
    handleCalculateLmdInterest();
  }, [caseId]);

  // Ngarkimi dhe Auditimi i Pasqyrës me Pandas & Claude Sonnet 4.6
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
        `Ekspertizë financiare mbi pretendimin e padisë (${principalAmount} €)`
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

  // Interrogimi i Provave me Claude Sonnet 4.6
  const handleInterrogateFinances = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!interrogationQuestion.trim() || !caseId || isInterrogating) return;

    setIsInterrogating(true);
    setInterrogationResult('');

    try {
      const res = await forensicDeskService.sendChatMessage(
        caseId,
        `[PYETJE MBI PROVAT FINANCIARE DHE KAMATËN LMD]: ${interrogationQuestion}`,
        `Kryegjëja: ${principalAmount} €, Kamata LMD: ${lmdResult?.interest_amount || 0} €`
      );
      setInterrogationResult(res.content || "Nuk pati përgjigje nga motori hetimor.");
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Dështoi marrja e përgjigjes nga auditimi.");
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
        {/* PËRLLOGARITËSI STATUTOR I KAMATËVONESËS LIGJORE (LMD NENI 265) */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-main pb-2.5">
            <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <Calculator size={16} className="text-primary-start" /> Kamata Ligjore LMD (Neni 265)
            </h3>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-primary-start/10 text-primary-start font-bold">
              8% Standard Kosovë
            </span>
          </div>

          <div className="space-y-3 text-sm">
            <div>
              <label className="block text-text-muted font-bold mb-1 flex items-center gap-1">
                <DollarSign size={14} /> Shuma e Kryegjësë (€) *
              </label>
              <input
                type="number"
                value={principalAmount}
                onChange={(e) => setPrincipalAmount(e.target.value)}
                placeholder="p.sh. 15000"
                className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary font-mono text-base focus:outline-none focus:border-primary-start"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-text-muted font-bold mb-1 flex items-center gap-1">
                  <Calendar size={14} /> Data e Fillimit të Vonesës
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-primary-start"
                />
              </div>

              <div>
                <label className="block text-text-muted font-bold mb-1 flex items-center gap-1">
                  <Calendar size={14} /> Data e Pagesës / Gjykimit
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-primary-start"
                />
              </div>
            </div>

            <div>
              <label className="block text-text-muted font-bold mb-1 flex items-center gap-1">
                <Percent size={14} /> Shkalla Vjetore e Kamatës (%)
              </label>
              <input
                type="number"
                step="0.1"
                value={annualRate}
                onChange={(e) => setAnnualRate(e.target.value)}
                className="w-full bg-surface border border-main rounded-xl px-3 py-2 text-text-primary font-mono text-sm focus:outline-none focus:border-primary-start"
              />
            </div>

            <button
              type="button"
              onClick={handleCalculateLmdInterest}
              disabled={isCalculatingLmd}
              className="w-full h-10 bg-primary-start hover:bg-primary-start/90 text-white font-bold rounded-xl text-sm uppercase tracking-wider flex items-center justify-center gap-2 cursor-pointer shadow-sm transition-all"
            >
              {isCalculatingLmd ? <Loader2 size={16} className="animate-spin" /> : <Calculator size={16} />}
              <span>Llogarit & Vulos në Server</span>
            </button>
          </div>

          {/* BILANCI I PËRLLOGARITUR LMD NGA SERVERI */}
          {lmdResult && (
            <div className="p-4 rounded-2xl bg-surface border border-main space-y-2.5 text-sm" style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Ditë Vonese të Verifikuara:</span>
                <span className="font-bold font-mono text-text-primary">{lmdResult.days_elapsed} ditë</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Interesi Ditor:</span>
                <span className="font-mono text-text-muted">{lmdResult.daily_accrual} € / ditë</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-muted">Kamata e Grumbulluar (8%):</span>
                <span className="font-bold font-mono text-emerald-500">
                  + {lmdResult.interest_amount.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                </span>
              </div>
              <div className="pt-2 border-t border-main flex items-center justify-between text-base">
                <span className="font-bold text-text-primary">Detyrimi Total i Padisë:</span>
                <span className="font-black font-mono text-primary-start">
                  {lmdResult.total_obligation.toLocaleString('sq-AL', { minimumFractionDigits: 2 })} €
                </span>
              </div>
              <p className="text-xs text-text-muted font-mono italic text-center pt-1">
                Baza: {lmdResult.legal_basis}
              </p>
            </div>
          )}
        </div>

        {/* NGARKIMI I EKSTRAKTEVE ME PANDAS AUDIT */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between border-b border-main pb-2.5">
            <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <FileSpreadsheet size={16} className="text-primary-start" /> Auditimi i Pasqyrave Financiare
            </h3>
            <span className="text-xs font-mono text-primary-start font-bold">Pandas + Claude Sonnet 4.6</span>
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
                <span className="text-sm font-bold text-primary-start">Duke analizuar me Pandas & Claude Sonnet 4.6...</span>
              </div>
            ) : (
              <>
                <div className="w-10 h-10 rounded-xl bg-primary-start/10 text-primary-start flex items-center justify-center">
                  <UploadCloud size={20} />
                </div>
                <div>
                  <p className="text-sm font-bold text-text-primary">Kliko ose tërhiq skedar (XLSX, CSV)</p>
                  <p className="text-xs text-text-muted">Krahasim automatik i pretendimit të padisë me transaksionet reale</p>
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

      {/* KOLONA E DJATHTË: RAPORTI FORENZIK PANDAS & INTERROGIMI */}
      <div className="lg:col-span-7 space-y-4">
        {/* PYETËSORI FORENZIK ME CLAUDE SONNET 4.6 */}
        <div className="glass-panel p-5 rounded-3xl border border-main bg-card shadow-sm space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h3 className="text-sm font-bold uppercase tracking-wider text-text-primary flex items-center gap-2">
              <ShieldAlert size={16} className="text-primary-start" /> Interrogimi i Provave Financiare
            </h3>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-emerald-500 font-bold">Verifikim Ligjor Aktiv</span>
              {/* Kontrolli i Zmadhimit */}
              <div className="flex items-center gap-1 rounded-xl border border-main bg-surface p-1" aria-label="Madhësia e shkrimit">
                <button
                  type="button"
                  onClick={handleDecreaseFont}
                  disabled={fontLevelIndex === 0}
                  title="Zvogëlo madhësinë e shkrimit"
                  className="h-7 w-7 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30"
                >
                  A−
                </button>
                <button
                  type="button"
                  onClick={handleResetFont}
                  title="Rivendos madhësinë e shkrimit"
                  className="min-w-10 rounded-lg px-1 text-[11px] font-bold text-text-muted hover:bg-hover hover:text-text-primary"
                >
                  {activeFont.label}
                </button>
                <button
                  type="button"
                  onClick={handleIncreaseFont}
                  disabled={fontLevelIndex === FONT_LEVELS.length - 1}
                  title="Rrit madhësinë e shkrimit"
                  className="h-7 w-7 rounded-lg text-xs font-bold text-text-muted hover:bg-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30"
                >
                  A+
                </button>
              </div>
            </div>
          </div>

          <form onSubmit={handleInterrogateFinances} className="flex gap-2">
            <input
              type="text"
              value={interrogationQuestion}
              onChange={(e) => setInterrogationQuestion(e.target.value)}
              placeholder="Pyet p.sh.: A ka elemente të dëmtimit të kreditorëve sipas KPK?"
              className="flex-1 bg-surface border border-main rounded-xl px-3.5 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-start"
            />
            <button
              type="submit"
              disabled={isInterrogating || !interrogationQuestion.trim()}
              className="px-4 py-2 bg-primary-start hover:bg-primary-start/90 text-white text-sm font-bold rounded-xl shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-40 cursor-pointer shrink-0"
            >
              {isInterrogating ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              <span>Pyet</span>
            </button>
          </form>

          {interrogationResult && (
            <div className="p-3.5 bg-surface/60 rounded-xl border border-main text-text-primary leading-relaxed font-sans select-text" style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}>
              <p className="font-bold text-primary-start mb-1 flex items-center gap-1" style={{ fontSize: `${activeFont.base * 1.1}px` }}>
                <CheckCircle2 size={16} /> Përgjigjja e Ekspertizës Financiare:
              </p>
              {interrogationResult}
            </div>
          )}
        </div>

        {/* HAPËSIRA KRYESORE E RAPORTIT TË AUDITIMIT ME PANDAS */}
        <div className="glass-panel p-6 rounded-3xl border border-main bg-card shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-main pb-4">
            <div>
              <div className="flex items-center gap-2">
                <TrendingUp size={18} className="text-primary-start" />
                <h3 className="text-base font-bold uppercase tracking-wider text-text-primary">
                  Ekspertiza Financiare e Pasqyrave
                </h3>
              </div>
              <p className="text-sm text-text-muted mt-0.5 truncate max-w-md">
                {uploadedFileName ? `Skedari: ${uploadedFileName}` : 'Ngarkoni një skedar Excel/CSV për llogaritje automatike'}
              </p>
            </div>

            {spreadsheetData?.forensic_opinion?.expert_concluding_summary && (
              <button
                type="button"
                onClick={() => handleCopyReport(spreadsheetData.forensic_opinion.expert_concluding_summary)}
                className="h-9 px-3 bg-surface hover:bg-hover border border-main rounded-xl text-sm font-bold text-text-primary flex items-center gap-1.5 transition-all cursor-pointer"
              >
                {copiedReport ? <CheckCircle2 size={16} className="text-emerald-500" /> : <Copy size={16} />}
                <span>{copiedReport ? 'U Kopjua' : 'Kopjo Ekspertizën'}</span>
              </button>
            )}
          </div>

          <div
            className="min-h-[280px] max-h-[420px] overflow-y-auto custom-finance-scroll p-4 bg-surface/50 rounded-2xl border border-main text-text-primary select-text space-y-3"
            style={{ fontSize: `${activeFont.base}px`, lineHeight: activeFont.line }}
          >
            {spreadsheetData ? (
              <div className="space-y-3">
                {/* Statusi dhe Verdikti Financiar */}
                <div className="flex items-center justify-between p-3 bg-surface rounded-xl border border-main">
                  <span className="font-bold">Verdikti i Auditimit:</span>
                  <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase ${spreadsheetData.forensic_opinion?.financial_audit_verdict?.includes('ANOMALI') ? 'bg-rose-500/20 text-rose-500 border border-rose-500/30' : 'bg-emerald-500/20 text-emerald-500 border border-emerald-500/30'}`}>
                    {spreadsheetData.forensic_opinion?.financial_audit_verdict || 'I AUDITUAR'}
                  </span>
                </div>

                {/* Krahasimi me Padinë (Discrepancy) */}
                {spreadsheetData.spreadsheet_analysis?.discrepancy_with_claim && (
                  <div className="p-3 bg-card rounded-xl border border-main space-y-1">
                    <h4 className="font-bold text-text-primary flex items-center gap-1.5" style={{ fontSize: `${activeFont.base * 1.1}px` }}>
                      <Scale size={16} className="text-primary-start" /> Krahasimi i Padisë me Transaksionet Reale:
                    </h4>
                    <div className="grid grid-cols-3 gap-2 pt-1 font-mono" style={{ fontSize: `${activeFont.base * 0.9}px` }}>
                      <div>Pretendimi: <span className="font-bold">{spreadsheetData.spreadsheet_analysis.discrepancy_with_claim.claimed_in_suit} €</span></div>
                      <div>Provuar me Tabelë: <span className="font-bold text-emerald-500">{spreadsheetData.spreadsheet_analysis.discrepancy_with_claim.documented_in_sheet} €</span></div>
                      <div>Diferenca: <span className="font-bold text-rose-500">{spreadsheetData.spreadsheet_analysis.discrepancy_with_claim.delta} €</span></div>
                    </div>
                    <p className="text-amber-500 font-bold pt-1" style={{ fontSize: `${activeFont.base * 0.85}px` }}>
                      Statusi: {spreadsheetData.spreadsheet_analysis.discrepancy_with_claim.status}
                    </p>
                  </div>
                )}

                {/* Anomalitë Kontabël */}
                {spreadsheetData.forensic_opinion?.accounting_irregularities?.length > 0 && (
                  <div className="p-3 bg-rose-500/10 rounded-xl border border-rose-500/20 space-y-1">
                    <h4 className="font-bold text-rose-500 flex items-center gap-1.5 uppercase" style={{ fontSize: `${activeFont.base * 1.1}px` }}>
                      <AlertTriangle size={16} /> Parregullsi të Zbuluara:
                    </h4>
                    <ul className="list-disc list-inside text-text-primary">
                      {spreadsheetData.forensic_opinion.accounting_irregularities.map((irr: string, i: number) => (
                        <li key={i}>{irr}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Këshillë Taktike e Mbrojtjes */}
                {spreadsheetData.forensic_opinion?.tactical_litigation_advice && (
                  <div className="p-3 bg-primary-start/10 rounded-xl border border-primary-start/20 space-y-1">
                    <h4 className="font-bold text-primary-start flex items-center gap-1.5 uppercase" style={{ fontSize: `${activeFont.base * 1.1}px` }}>
                      Këshillë Taktike për Seancë Gjyqësore:
                    </h4>
                    <p className="text-text-primary">{spreadsheetData.forensic_opinion.tactical_litigation_advice}</p>
                  </div>
                )}

                {/* Përmbledhja e Ekspertit */}
                <div className="p-3 bg-surface rounded-xl border border-main space-y-1">
                  <h4 className="font-bold text-text-primary uppercase" style={{ fontSize: `${activeFont.base * 1.1}px` }}>Konkluzioni Formal:</h4>
                  <p className="text-text-muted whitespace-pre-wrap">{spreadsheetData.forensic_opinion?.expert_concluding_summary}</p>
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-text-muted text-center gap-3 py-10">
                <AlertCircle size={36} className="opacity-30 text-primary-start" />
                <p className="max-w-sm">
                  Përdorni kalkulatorin majtas për vlerën e padisë ose ngarkoni një ekstrakt bankar/tabelë Excel për auditim me Pandas dhe Claude Sonnet 4.6.
                </p>
              </div>
            )}
          </div>

          <div className="pt-2 flex items-center justify-between text-sm text-text-muted border-t border-main">
            <span className="flex items-center gap-1 font-medium">
              <Coins size={16} className="text-primary-start" />
              Përputhshmëri me Ligjin Nr. 04/L-077 për Marrëdhëniet e Detyrimeve (LMD)
            </span>
            <span className="font-mono text-xs">Llogaritja: Neni 265 (8% vjetore)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinancialForensicLab;