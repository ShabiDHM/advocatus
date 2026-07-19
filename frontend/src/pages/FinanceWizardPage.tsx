// FILE: src/pages/FinanceWizardPage.tsx
// PHOENIX PROTOCOL - FINANCE WIZARD V6.2 (DYNAMIC YEAR RANGE)
// POLISH: Standardized controls to 44px (h-11), swapped out border tokens, and updated custom scroll containers.

import { useEffect, useState, useMemo } from 'react';
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
        <div className="bg-surface border border-main p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between group hover:bg-hover transition-all gap-3 sm:gap-0 hover-lift shadow-sm">
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                    <span className="bg-canvas text-text-primary text-xs font-bold px-2 py-0.5 rounded border border-main flex-shrink-0 font-mono">
                        [{number}]
                    </span>
                    <span className="text-text-secondary text-xs font-bold uppercase tracking-wider truncate" title={label}>
                        {label}
                    </span>
                </div>
                <div className="text-xl font-mono font-bold text-text-primary pl-1">
                    {value.toFixed(2)} <span className="text-xs text-text-muted font-sans font-normal">{currency}</span>
                </div>
            </div>
            <button 
                type="button"
                onClick={handleCopy}
                className={`w-full sm:w-auto px-4 h-11 sm:p-3 rounded-lg transition-all flex items-center justify-center gap-2 hover-lift focus:outline-none ${
                    copied 
                        ? 'bg-status-success/20 text-status-success border border-status-success/30' 
                        : 'bg-canvas text-text-muted hover:text-text-primary border border-main'
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
        <div className="flex items-center justify-center space-x-2 sm:space-x-4 mb-8 select-none">
            {steps.map((step, index) => (
                <div key={step.id} className="flex items-center">
                    <div 
                        className={`flex items-center justify-center w-9 h-9 sm:w-10 sm:h-10 rounded-full border transition-all ${
                            currentStep >= step.id 
                                ? 'btn-primary shadow-sm' 
                                : 'bg-surface border-main text-text-disabled'
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
                            currentStep > step.id ? 'bg-primary-start' : 'bg-main'
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
            <div className="bg-status-success/10 border border-status-success/20 rounded-2xl p-8 text-center backdrop-blur-sm">
                <div className="w-16 h-16 bg-status-success/20 rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm shadow-status-success/10">
                    <CheckCircle className="text-status-success" size={32} />
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-text-primary mb-2">{t('finance.wizard.cleanRecordTitle')}</h3>
                <p className="text-sm sm:text-base text-status-success/80">{t('finance.wizard.cleanRecordDesc')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {critical.length > 0 && (
                <div className="bg-danger-start/10 border border-danger-start/20 rounded-xl p-5 backdrop-blur-sm">
                    <h3 className="flex items-center text-danger-start font-bold mb-4 text-sm sm:text-base select-none">
                        <ShieldAlert className="mr-2" size={20} />
                        {t('finance.wizard.criticalIssues')} ({critical.length})
                        <span className="ml-auto text-xs bg-danger-start/20 border border-danger-start/20 px-2 py-1 rounded text-danger-start/90">{t('finance.wizard.mustFix')}</span>
                    </h3>
                    <div className="space-y-2">
                        {critical.map(issue => (
                            <div key={issue.id} className="bg-canvas border border-main p-3 rounded-lg flex items-start">
                                <span className="w-1.5 h-1.5 bg-danger-start rounded-full mt-1.5 mr-2 flex-shrink-0 shadow-[0_0_5px_rgba(239,68,68,0.5)] animate-pulse" />
                                <p className="text-xs sm:text-sm text-text-secondary break-words">{issue.message}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {warnings.length > 0 && (
                <div className="bg-warning-start/10 border border-warning-start/20 rounded-xl p-5 backdrop-blur-sm">
                    <h3 className="flex items-center text-warning-start font-bold mb-4 text-sm sm:text-base select-none">
                        <AlertTriangle className="mr-2" size={20} />
                        {t('finance.wizard.warnings')} ({warnings.length})
                        <span className="ml-auto text-xs bg-warning-start/20 border border-warning-start/20 px-2 py-1 rounded text-warning-start/90">{t('finance.wizard.recommended')}</span>
                    </h3>
                    <div className="space-y-2">
                        {warnings.map(issue => (
                            <div key={issue.id} className="bg-canvas border border-main p-3 rounded-lg flex items-start">
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
                <div className="bg-primary-start/5 border border-primary-start/20 p-4 rounded-xl mb-4 select-none">
                    <p className="text-xs text-primary-start font-bold uppercase tracking-wider">
                        {isSmallBusiness ? t('finance.wizard.regimeSmall') : t('finance.wizard.regimeVat')}
                    </p>
                    <p className="text-sm text-text-primary mt-1 font-semibold">
                        {isSmallBusiness ? t('finance.wizard.rate9') : t('finance.wizard.rate18')}
                    </p>
                </div>

                <div className="bg-surface border border-main p-4 rounded-xl">
                    <p className="text-xs text-text-muted mb-1.5 uppercase tracking-wider font-bold">{t('finance.wizard.totalSales')}</p>
                    <p className="text-2xl font-bold text-text-primary font-mono">€{data.total_sales_gross.toFixed(2)}</p>
                    {!isSmallBusiness && (
                        <div className="mt-2 text-xs text-status-success flex items-center bg-status-success/15 w-fit px-2 py-1 rounded border border-status-success/20">
                            <span className="font-bold mr-2">{t('finance.wizard.vatCollected')}:</span>
                            €{data.vat_collected.toFixed(2)}
                        </div>
                    )}
                </div>

                {isSmallBusiness ? (
                    <div className="bg-surface border border-main p-4 rounded-xl opacity-60">
                        <p className="text-xs text-text-muted mb-1.5 uppercase tracking-wider font-bold">{t('finance.wizard.operationalExpenses')}</p>
                        <p className="text-2xl font-bold text-text-secondary font-mono">€{data.total_purchases_gross.toFixed(2)}</p>
                        <div className="mt-2 text-xs text-text-muted flex items-center">
                            <span className="bg-canvas border border-main px-1.5 py-0.5 rounded mr-2">{t('finance.wizard.noTaxEffect')}</span>
                        </div>
                    </div>
                ) : (
                    <div className="bg-surface border border-main p-4 rounded-xl">
                        <p className="text-xs text-text-muted mb-1.5 uppercase tracking-wider font-bold">{t('finance.wizard.totalPurchases')}</p>
                        <p className="text-2xl font-bold text-text-primary font-mono">€{data.total_purchases_gross.toFixed(2)}</p>
                        <div className="mt-2 text-xs text-danger-start flex items-center bg-danger-start/15 w-fit px-2 py-1 rounded border border-danger-start/20">
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
                    : 'bg-status-success/10 border-status-success/30'
            }`}>
                <h3 className="text-sm font-semibold text-text-secondary mb-4 opacity-80 select-none">
                    {data.description}
                </h3>
                <span className={`text-5xl font-black mb-6 font-mono tracking-tight ${isPayable ? 'text-danger-start' : 'text-status-success'}`}>
                    €{Math.abs(data.net_obligation).toFixed(2)}
                </span>
                <div className={`px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${isPayable ? 'bg-danger-start/20 border-danger-start/30 text-danger-start' : 'bg-status-success/20 border-status-success/30 text-status-success'}`}>
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

    // Dynamic year range: from currentYear - 5 to currentYear + 1
    const currentYear = new Date().getFullYear();
    const yearOptions = useMemo(() => {
        const startYear = currentYear - 5;
        const endYear = currentYear + 1;
        return Array.from({ length: endYear - startYear + 1 }, (_, i) => startYear + i);
    }, [currentYear]);

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
                <div className="p-4 sm:p-6 border-b border-main flex items-center justify-between bg-surface backdrop-blur-xl z-20 shrink-0">
                    <button 
                        type="button"
                        onClick={() => navigate('/business')} 
                        className="flex items-center justify-center h-11 px-4 text-text-secondary hover:text-text-primary rounded-xl hover:bg-hover transition-colors focus:outline-none"
                    >
                        <ArrowLeft size={18} className="mr-2" />
                        <span className="hidden sm:inline font-semibold">{t('finance.wizard.back')}</span>
                        <span className="sm:hidden">{t('general.cancel')}</span>
                    </button>
                    <h1 className="text-lg sm:text-xl font-bold text-text-primary tracking-tight">
                        {t('finance.monthlyClose')}
                    </h1>
                    <div className="w-11 sm:w-24" />
                </div>

                {/* Main Scroll Content */}
                <div className="flex-1 overflow-y-auto p-4 md:p-12 custom-finance-scroll">
                    <div className="max-w-4xl mx-auto">
                        
                        {/* Month & Year Selector - Standardized h-11 / 44px */}
                        <div className="flex justify-center mb-8 gap-3 h-11 shrink-0">
                            <select 
                                value={selectedMonth}
                                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                                className="px-4 h-11 bg-surface border border-main rounded-xl cursor-pointer capitalize text-sm sm:text-base font-medium min-w-[150px] focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all"
                            >
                                {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                                    <option key={m} value={m} className="bg-canvas text-text-primary">
                                        {format(new Date(2024, m - 1, 1), 'MMMM', { locale: currentLocale })}
                                    </option>
                                ))}
                            </select>
                            <select 
                                value={selectedYear}
                                onChange={(e) => setSelectedYear(Number(e.target.value))}
                                className="px-4 h-11 bg-surface border border-main rounded-xl cursor-pointer text-sm sm:text-base font-medium focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all"
                            >
                                {yearOptions.map(year => (
                                    <option key={year} value={year} className="bg-canvas text-text-primary">
                                        {year}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <StepIndicator currentStep={step} />

                        {loading ? (
                            <div className="flex justify-center py-20">
                                <Loader2 className="animate-spin text-primary-start w-12 h-12" />
                            </div>
                        ) : errorMsg ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center glass-panel rounded-2xl p-8 border border-main bg-surface">
                                <div className="bg-danger-start/10 p-4 rounded-full mb-4 border border-danger-start/20 animate-pulse">
                                    <AlertTriangle className="text-danger-start w-10 h-10" />
                                </div>
                                <p className="text-danger-start text-lg mb-4 font-semibold">{errorMsg}</p>
                                <button onClick={fetchData} className="h-11 px-6 bg-canvas rounded-xl text-text-primary hover:bg-hover border border-main transition-colors focus:outline-none shadow-sm">
                                    {t('documentsPanel.reconnect')}
                                </button>
                            </div>
                        ) : state ? (
                            <AnimatePresence mode="wait">
                                <motion.div 
                                    key={step}
                                    initial={{ opacity: 0, x: 15 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    exit={{ opacity: 0, x: -15 }}
                                    transition={{ duration: 0.25 }}
                                    className="glass-panel rounded-3xl p-6 sm:p-10 shadow-sm border border-main bg-canvas"
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
                                            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 sm:gap-0 mb-6 shrink-0">
                                                <h2 className="text-xl sm:text-2xl font-bold text-text-primary">{t('finance.wizard.readyToFile')}</h2>
                                                <button 
                                                    type="button"
                                                    onClick={handleOpenATK}
                                                    className="text-primary-start hover:bg-primary-start/15 text-sm font-bold flex items-center bg-primary-start/10 px-4 h-11 rounded-xl border border-primary-start/20 transition-all focus:outline-none"
                                                >
                                                    {t('finance.wizard.atk.openEdi')} <ExternalLink size={14} className="ml-2" />
                                                </button>
                                            </div>

                                            <div className="bg-surface rounded-2xl p-6 sm:p-8 border border-main mb-8">
                                                <p className="text-text-secondary mb-6 text-sm font-medium leading-relaxed">
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
                                                    type="button"
                                                    onClick={handleDownloadReport}
                                                    disabled={downloading}
                                                    className="px-8 h-11 rounded-xl text-sm font-bold flex items-center bg-surface hover:bg-hover text-text-primary transition-all disabled:opacity-50 border border-main focus:outline-none shadow-sm"
                                                >
                                                    {downloading ? <Loader2 className="animate-spin mr-2" size={18} /> : <Download className="mr-2" size={18} />}
                                                    {downloading ? t('general.loading') : t('finance.wizard.downloadReport')}
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    <div className="flex justify-between mt-10 pt-6 border-t border-main">
                                        <button 
                                            type="button"
                                            onClick={handlePrev}
                                            disabled={step === 1}
                                            className={`px-6 h-11 rounded-xl text-sm font-semibold transition-colors flex items-center focus:outline-none ${
                                                step === 1 ? 'text-text-disabled cursor-not-allowed' : 'text-text-secondary hover:text-text-primary hover:bg-hover border border-transparent hover:border-main'
                                            }`}
                                        >
                                            {t('general.cancel')}
                                        </button>
                                        
                                        {step < 3 && (
                                            <button 
                                                type="button"
                                                onClick={handleNext}
                                                disabled={step === 1 && !state.ready_to_close}
                                                className={`flex items-center px-6 h-11 rounded-xl font-bold text-sm tracking-wide transition-all shadow-sm focus:outline-none ${
                                                    step === 1 && !state.ready_to_close
                                                        ? 'bg-surface border border-main text-text-disabled cursor-not-allowed shadow-none'
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