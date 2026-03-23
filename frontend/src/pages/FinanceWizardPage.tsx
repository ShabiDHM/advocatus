// FILE: src/pages/FinanceWizardPage.tsx
// PHOENIX PROTOCOL - FINANCE WIZARD V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, border-border-main, text-text-primary, text-text-secondary, text-text-muted, btn-primary.
// 2. Preserved all functionality: month selection, audit, tax, ATK copy, report download.
// 3. Ambient glows replaced with subtle semantic gradients.
// 4. Updated shadows to shadow-sm and added hover-lift for interactive elements.
// 5. Replaced all border-main with border-border-main for consistency.

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    AlertTriangle, 
    CheckCircle, 
    Calculator, 
    FileText, 
    ChevronRight, 
    ArrowLeft,
    ShieldAlert,
    Download,
    Loader2,
    Copy,
    Check,
    ExternalLink
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiService, WizardState, AuditIssue, TaxCalculation } from '../services/api';
import { format } from 'date-fns';
import { sq, enUS } from 'date-fns/locale';

// --- HELPER COMPONENT: ATK BOX (Glass Style) ---
const ATKBox = ({ number, label, value, currency }: { number: string, label: string, value: number, currency: string }) => {
    const [copied, setCopied] = useState(false);
    const { t } = useTranslation();

    const handleCopy = () => {
        navigator.clipboard.writeText(value.toFixed(2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="bg-surface/30 border border-border-main p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between group hover:bg-surface/50 hover:border-primary-start/30 transition-all gap-3 sm:gap-0 hover-lift shadow-sm">
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <span className="bg-canvas/40 text-text-primary text-xs font-bold px-2 py-0.5 rounded border border-border-main flex-shrink-0 font-mono">
                        [{number}]
                    </span>
                    <span className="text-text-secondary text-sm font-medium truncate" title={label}>
                        {label}
                    </span>
                </div>
                <div className="text-xl font-mono font-bold text-text-primary pl-1">
                    {value.toFixed(2)} <span className="text-xs text-text-muted font-sans">{currency}</span>
                </div>
            </div>
            <button 
                onClick={handleCopy}
                className={`w-full sm:w-auto px-4 py-3 sm:p-3 rounded-lg transition-all flex items-center justify-center gap-2 hover-lift ${
                    copied 
                        ? 'bg-success-start/20 text-success-start border border-success-start/50' 
                        : 'bg-surface/30 text-text-muted hover:bg-surface/50 hover:text-text-primary border border-border-main'
                }`}
                title={t('finance.wizard.atk.copy')}
            >
                {copied ? <Check size={18} /> : <Copy size={18} />}
                <span className="sm:hidden text-sm font-medium">
                    {copied ? t('finance.wizard.atk.copied') : t('finance.wizard.atk.copy')}
                </span>
            </button>
        </div>
    );
};

// --- COMPONENTS ---

const StepIndicator = ({ currentStep }: { currentStep: number }) => {
    const { t } = useTranslation();
    
    const steps = [
        { id: 1, label: t('finance.wizard.stepAudit'), icon: ShieldAlert },
        { id: 2, label: t('finance.wizard.stepTax'), icon: Calculator },
        { id: 3, label: t('finance.wizard.stepFinalize'), icon: FileText },
    ];

    return (
        <div className="flex items-center justify-center space-x-2 sm:space-x-4 mb-8">
            {steps.map((step, index) => (
                <div key={step.id} className="flex items-center">
                    <div 
                        className={`flex items-center justify-center w-8 h-8 sm:w-10 sm:h-10 rounded-full border transition-all ${
                            currentStep >= step.id 
                                ? 'btn-primary shadow-sm' 
                                : 'bg-surface/30 border-border-main text-text-muted'
                        }`}
                    >
                        <step.icon size={16} />
                    </div>
                    <span className={`ml-2 text-xs sm:text-sm font-bold hidden md:block ${
                        currentStep >= step.id ? 'text-text-primary' : 'text-text-muted'
                    }`}>
                        {step.label}
                    </span>
                    {index < steps.length - 1 && (
                        <div className={`w-8 sm:w-12 h-0.5 mx-2 sm:mx-4 rounded ${
                            currentStep > step.id ? 'bg-primary-start' : 'bg-border-main'
                        }`} />
                    )}
                </div>
            ))}
        </div>
    );
};

const AuditStep = ({ issues }: { issues: AuditIssue[] }) => {
    const { t } = useTranslation();
    const critical = issues.filter(i => i.severity === 'CRITICAL');
    const warnings = issues.filter(i => i.severity === 'WARNING');

    if (issues.length === 0) {
        return (
            <div className="bg-success-start/10 border border-success-start/30 rounded-2xl p-8 text-center backdrop-blur-sm">
                <div className="w-16 h-16 bg-success-start/20 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm shadow-success-start/10">
                    <CheckCircle className="text-success-start" size={32} />
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-2">{t('finance.wizard.cleanRecordTitle')}</h3>
                <p className="text-sm sm:text-base text-success-start/70">{t('finance.wizard.cleanRecordDesc')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {critical.length > 0 && (
                <div className="bg-danger-start/10 border border-danger-start/20 rounded-xl p-5 backdrop-blur-sm">
                    <h3 className="flex items-center text-danger-start font-bold mb-4 text-sm sm:text-base">
                        <ShieldAlert className="mr-2" size={20} />
                        {t('finance.wizard.criticalIssues')} ({critical.length})
                        <span className="ml-auto text-xs bg-danger-start/20 border border-danger-start/20 px-2 py-1 rounded text-danger-start/90">{t('finance.wizard.mustFix')}</span>
                    </h3>
                    <div className="space-y-2">
                        {critical.map(issue => (
                            <div key={issue.id} className="bg-canvas/40 border border-border-main p-3 rounded-lg flex items-start">
                                <span className="w-1.5 h-1.5 bg-danger-start rounded-full mt-1.5 mr-2 flex-shrink-0 shadow-[0_0_5px_rgba(239,68,68,0.5)]" />
                                <p className="text-xs sm:text-sm text-text-secondary break-words">{issue.message}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {warnings.length > 0 && (
                <div className="bg-warning-start/10 border border-warning-start/20 rounded-xl p-5 backdrop-blur-sm">
                    <h3 className="flex items-center text-warning-start font-bold mb-4 text-sm sm:text-base">
                        <AlertTriangle className="mr-2" size={20} />
                        {t('finance.wizard.warnings')} ({warnings.length})
                        <span className="ml-auto text-xs bg-warning-start/20 border border-warning-start/20 px-2 py-1 rounded text-warning-start/90">{t('finance.wizard.recommended')}</span>
                    </h3>
                    <div className="space-y-2">
                        {warnings.map(issue => (
                            <div key={issue.id} className="bg-canvas/40 border border-border-main p-3 rounded-lg flex items-start">
                                <span className="w-1.5 h-1.5 bg-warning-start rounded-full mt-1.5 mr-2 flex-shrink-0 shadow-[0_0_5px_rgba(245,158,11,0.5)]" />
                                <p className="text-xs sm:text-sm text-text-secondary break-words">{issue.message}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const TaxStep = ({ data }: { data: TaxCalculation }) => {
    const { t } = useTranslation();
    const isPayable = data.net_obligation > 0;
    const isSmallBusiness = data.regime === 'SMALL_BUSINESS';

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
                {/* Header for Regime */}
                <div className="bg-gradient-to-r from-primary-start/20 to-primary-start/5 border border-primary-start/30 p-4 rounded-xl mb-4">
                    <p className="text-xs text-primary-start/80 font-bold uppercase tracking-wider">
                        {isSmallBusiness ? t('finance.wizard.regimeSmall') : t('finance.wizard.regimeVat')}
                    </p>
                    <p className="text-sm text-text-primary mt-1 font-medium">
                        {isSmallBusiness ? t('finance.wizard.rate9') : t('finance.wizard.rate18')}
                    </p>
                </div>

                <div className="bg-surface/30 border border-border-main p-4 rounded-xl">
                    <p className="text-xs text-text-muted mb-1 uppercase tracking-wider font-bold">{t('finance.wizard.totalSales')}</p>
                    <p className="text-2xl font-bold text-text-primary font-mono">€{data.total_sales_gross.toFixed(2)}</p>
                    {!isSmallBusiness && (
                        <div className="mt-2 text-xs text-success-start flex items-center bg-success-start/10 w-fit px-2 py-1 rounded border border-success-start/20">
                            <span className="font-bold mr-2">{t('finance.wizard.vatCollected')}:</span>
                            €{data.vat_collected.toFixed(2)}
                        </div>
                    )}
                </div>

                {isSmallBusiness ? (
                    <div className="bg-surface/30 border border-border-main p-4 rounded-xl opacity-60">
                        <p className="text-xs text-text-muted mb-1 uppercase tracking-wider font-bold">{t('finance.wizard.operationalExpenses')}</p>
                        <p className="text-2xl font-bold text-text-secondary font-mono">€{data.total_purchases_gross.toFixed(2)}</p>
                        <div className="mt-2 text-xs text-text-muted flex items-center">
                            <span className="bg-surface/20 px-1.5 py-0.5 rounded mr-2">{t('finance.wizard.noTaxEffect')}</span>
                        </div>
                    </div>
                ) : (
                    <div className="bg-surface/30 border border-border-main p-4 rounded-xl">
                        <p className="text-xs text-text-muted mb-1 uppercase tracking-wider font-bold">{t('finance.wizard.totalPurchases')}</p>
                        <p className="text-2xl font-bold text-text-primary font-mono">€{data.total_purchases_gross.toFixed(2)}</p>
                        <div className="mt-2 text-xs text-danger-start flex items-center bg-danger-start/10 w-fit px-2 py-1 rounded border border-danger-start/20">
                            <span className="font-bold mr-2">{t('finance.wizard.vatDeductible')}:</span>
                            €{data.vat_deductible.toFixed(2)}
                        </div>
                    </div>
                )}
            </div>

            {/* The Result Card */}
            <div className={`p-8 rounded-2xl border flex flex-col justify-center items-center text-center shadow-sm backdrop-blur-md ${
                isPayable 
                    ? 'bg-danger-start/10 border-danger-start/30' 
                    : 'bg-success-start/10 border-success-start/30'
            }`}>
                <h3 className="text-lg font-medium text-text-secondary mb-4 opacity-80">
                    {data.description}
                </h3>
                <span className={`text-5xl font-bold mb-6 font-mono tracking-tight drop-shadow-lg ${isPayable ? 'text-danger-start' : 'text-success-start'}`}>
                    €{Math.abs(data.net_obligation).toFixed(2)}
                </span>
                <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${isPayable ? 'bg-danger-start/20 border-danger-start/30 text-danger-start' : 'bg-success-start/20 border-success-start/30 text-success-start'}`}>
                    {isPayable ? t('finance.wizard.payable') : t('finance.wizard.receivable')}
                </div>
            </div>
        </div>
    );
};

// --- MAIN PAGE ---

const FinanceWizardPage = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(true);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [downloading, setDownloading] = useState(false);
    const [state, setState] = useState<WizardState | null>(null);
    
    // Default to "Previous Month"
    const today = new Date();
    const [selectedMonth, setSelectedMonth] = useState(today.getMonth() === 0 ? 12 : today.getMonth());
    const [selectedYear, setSelectedYear] = useState(today.getMonth() === 0 ? today.getFullYear() - 1 : today.getFullYear());

    const localeMap: { [key: string]: any } = { sq, al: sq, en: enUS };
    const currentLocale = localeMap[i18n.language] || enUS;

    useEffect(() => {
        fetchData();
    }, [selectedMonth, selectedYear]);

    const fetchData = async () => {
        setLoading(true);
        setErrorMsg(null);
        try {
            const data = await apiService.getWizardState(selectedMonth, selectedYear);
            setState(data);
        } catch (error: any) {
            console.error("Failed to fetch wizard state", error);
            if (error.response?.status === 500) {
                setErrorMsg(t('error.generic') + " (Server Error)");
            } else if (error.code === 'ERR_NETWORK') {
                setErrorMsg(t('drafting.errorConnectionLost'));
            } else {
                setErrorMsg(t('error.generic'));
            }
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadReport = async () => {
        setDownloading(true);
        try {
            await apiService.downloadMonthlyReport(selectedMonth, selectedYear);
        } catch (error) {
            console.error("Download failed", error);
            alert(t('error.generic'));
        } finally {
            setDownloading(false);
        }
    };

    const handleOpenATK = () => {
        window.open('https://edeklarimi.atk-ks.org/', '_blank');
    };

    const handleNext = () => {
        if (step < 3) setStep(step + 1);
    };

    const handlePrev = () => {
        if (step > 1) setStep(step - 1);
    };

    return (
        <div className="flex h-screen bg-canvas text-text-primary overflow-hidden font-sans relative selection:bg-primary-start/30">
             
             {/* Ambient Background - subtle semantic gradients */}
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary-start/5 rounded-full blur-[120px] opacity-40"></div>
                <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-secondary-start/5 rounded-full blur-[100px] opacity-30"></div>
            </div>

             <div className="flex-1 flex flex-col overflow-hidden relative z-10">
                {/* Header - Glass Style */}
                <div className="p-4 sm:p-6 border-b border-border-main flex items-center justify-between bg-canvas/80 backdrop-blur-xl z-20">
                    <button 
                        onClick={() => navigate('/business')} 
                        className="flex items-center text-text-secondary hover:text-text-primary transition-colors group hover-lift"
                    >
                        <ArrowLeft size={20} className="mr-2 group-hover:-translate-x-1 transition-transform" />
                        <span className="hidden sm:inline font-medium">{t('finance.wizard.back')}</span>
                        <span className="sm:hidden">{t('general.cancel')}</span>
                    </button>
                    <h1 className="text-lg sm:text-xl font-bold text-text-primary tracking-tight">
                        {t('finance.monthlyClose')}
                    </h1>
                    <div className="w-10 sm:w-24" />
                </div>

                <div className="flex-1 overflow-y-auto p-4 md:p-12 custom-scrollbar">
                    <div className="max-w-4xl mx-auto">
                        
                        {/* Month Selector */}
                        <div className="flex justify-center mb-8 gap-3">
                            <select 
                                value={selectedMonth}
                                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                                className="glass-input px-6 py-2.5 rounded-xl cursor-pointer capitalize text-sm sm:text-base font-medium min-w-[150px] border border-border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40"
                            >
                                {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                                    <option key={m} value={m} className="bg-surface text-text-primary">
                                        {format(new Date(2024, m - 1, 1), 'MMMM', { locale: currentLocale })}
                                    </option>
                                ))}
                            </select>
                            <select 
                                value={selectedYear}
                                onChange={(e) => setSelectedYear(Number(e.target.value))}
                                className="glass-input px-6 py-2.5 rounded-xl cursor-pointer text-sm sm:text-base font-medium border border-border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40"
                            >
                                <option value={2024} className="bg-surface text-text-primary">2024</option>
                                <option value={2025} className="bg-surface text-text-primary">2025</option>
                            </select>
                        </div>

                        <StepIndicator currentStep={step} />

                        {loading ? (
                            <div className="flex justify-center py-20">
                                <Loader2 className="animate-spin text-primary-start w-12 h-12" />
                            </div>
                        ) : errorMsg ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center glass-panel rounded-2xl p-8 border border-border-main">
                                <div className="bg-danger-start/10 p-4 rounded-full mb-4 border border-danger-start/20">
                                    <AlertTriangle className="text-danger-start w-10 h-10" />
                                </div>
                                <p className="text-danger-start text-lg mb-4 font-medium">{errorMsg}</p>
                                <button onClick={fetchData} className="px-6 py-2 bg-surface/50 rounded-lg text-text-primary hover:bg-surface/80 transition-colors border border-border-main hover-lift shadow-sm">
                                    {t('documentsPanel.reconnect')}
                                </button>
                            </div>
                        ) : state ? (
                            <AnimatePresence mode="wait">
                                <motion.div 
                                    key={step}
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -20 }}
                                    transition={{ duration: 0.3 }}
                                    className="glass-panel rounded-3xl p-6 sm:p-10 shadow-sm border border-border-main"
                                >
                                    {step === 1 && (
                                        <div>
                                            <h2 className="text-xl sm:text-2xl font-bold mb-6 text-text-primary">{t('finance.wizard.stepAudit')}</h2>
                                            <AuditStep issues={state.issues} />
                                        </div>
                                    )}

                                    {step === 2 && (
                                        <div>
                                            <h2 className="text-xl sm:text-2xl font-bold mb-6 text-text-primary">{t('finance.wizard.stepTax')}</h2>
                                            <TaxStep data={state.calculation} />
                                        </div>
                                    )}

                                    {step === 3 && (
                                        <div>
                                            <div className="flex justify-between items-center mb-6">
                                                <h2 className="text-xl sm:text-2xl font-bold text-text-primary">{t('finance.wizard.readyToFile')}</h2>
                                                <button 
                                                    onClick={handleOpenATK}
                                                    className="text-primary-start hover:text-primary-start/80 text-sm font-bold flex items-center bg-primary-start/10 px-3 py-1.5 rounded-lg border border-primary-start/20 transition-colors hover-lift"
                                                >
                                                    {t('finance.wizard.atk.openEdi')} <ExternalLink size={14} className="ml-2" />
                                                </button>
                                            </div>

                                            <div className="bg-canvas/40 rounded-2xl p-6 sm:p-8 border border-border-main mb-8">
                                                <p className="text-text-secondary mb-6 text-sm font-medium">
                                                    {t('finance.wizard.atk.copyInstruction')}
                                                </p>
                                                
                                                {state.calculation.regime === 'SMALL_BUSINESS' ? (
                                                    <div className="space-y-4">
                                                        <ATKBox 
                                                            number="9" 
                                                            label={t('finance.wizard.atk.box9')}
                                                            value={state.calculation.total_sales_gross}
                                                            currency={state.calculation.currency}
                                                        />
                                                        <ATKBox 
                                                            number="11" 
                                                            label={t('finance.wizard.atk.box11')} 
                                                            value={state.calculation.net_obligation}
                                                            currency={state.calculation.currency}
                                                        />
                                                    </div>
                                                ) : (
                                                    <div className="space-y-4">
                                                        <ATKBox 
                                                            number="10" 
                                                            label={t('finance.wizard.atk.box10')}
                                                            value={state.calculation.total_sales_gross}
                                                            currency={state.calculation.currency}
                                                        />
                                                        <ATKBox 
                                                            number="23" 
                                                            label={t('finance.wizard.atk.box23')}
                                                            value={state.calculation.total_purchases_gross}
                                                            currency={state.calculation.currency}
                                                        />
                                                        <ATKBox 
                                                            number="48" 
                                                            label={t('finance.wizard.atk.box48')}
                                                            value={state.calculation.net_obligation}
                                                            currency={state.calculation.currency}
                                                        />
                                                    </div>
                                                )}
                                            </div>

                                            <div className="flex justify-center">
                                                <button 
                                                    onClick={handleDownloadReport}
                                                    disabled={downloading}
                                                    className="btn-secondary px-8 py-3 rounded-xl font-bold flex items-center transition-all disabled:opacity-50 border border-border-main hover-lift shadow-sm"
                                                >
                                                    {downloading ? <Loader2 className="animate-spin mr-2" size={20} /> : <Download className="mr-2" size={20} />}
                                                    {downloading ? t('general.loading') : t('finance.wizard.downloadReport')}
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    <div className="flex justify-between mt-10 pt-6 border-t border-border-main">
                                        <button 
                                            onClick={handlePrev}
                                            disabled={step === 1}
                                            className={`px-6 py-2.5 rounded-xl transition-colors font-medium hover-lift ${
                                                step === 1 ? 'text-text-muted cursor-not-allowed' : 'text-text-secondary hover:text-text-primary hover:bg-surface/30'
                                            }`}
                                        >
                                            {t('general.cancel')}
                                        </button>
                                        
                                        {step < 3 && (
                                            <button 
                                                onClick={handleNext}
                                                disabled={step === 1 && !state.ready_to_close}
                                                className={`flex items-center px-6 py-2.5 rounded-xl font-bold transition-all shadow-sm shadow-primary-start/20 hover-lift ${
                                                    step === 1 && !state.ready_to_close
                                                        ? 'bg-surface/30 text-text-muted cursor-not-allowed shadow-none'
                                                        : 'btn-primary'
                                                }`}
                                            >
                                                {step === 1 && !state.ready_to_close ? t('finance.wizard.fixIssues') : t('finance.wizard.next')}
                                                <ChevronRight size={18} className="ml-2" />
                                            </button>
                                        )}
                                    </div>
                                </motion.div>
                            </AnimatePresence>
                        ) : null}
                    </div>
                </div>
             </div>
        </div>
    );
};

export default FinanceWizardPage;