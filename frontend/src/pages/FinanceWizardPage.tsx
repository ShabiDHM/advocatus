// FILE: src/pages/FinanceWizardPage.tsx
// PHOENIX PROTOCOL - FINANCE WIZARD V13.0 (GLASS & GLOWS)
// 1. VISUALS: Full Glassmorphism adoption (glass-panel, glass-input).
// 2. LAYOUT: Added ambient background glows and refined step indicators.
// 3. UX: Enhanced data presentation with cleaner glass cards.

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
        <div className="bg-white/5 border border-white/10 p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between group hover:bg-white/10 hover:border-primary-start/30 transition-all gap-3 sm:gap-0">
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                    <span className="bg-black/40 text-white text-xs font-bold px-2 py-0.5 rounded border border-white/10 flex-shrink-0 font-mono">
                        [{number}]
                    </span>
                    <span className="text-gray-400 text-sm font-medium truncate" title={label}>
                        {label}
                    </span>
                </div>
                <div className="text-xl font-mono font-bold text-white pl-1">
                    {value.toFixed(2)} <span className="text-xs text-gray-500 font-sans">{currency}</span>
                </div>
            </div>
            <button 
                onClick={handleCopy}
                className={`w-full sm:w-auto px-4 py-3 sm:p-3 rounded-lg transition-all flex items-center justify-center gap-2 ${
                    copied 
                        ? 'bg-green-500/20 text-green-400 border border-green-500/50' 
                        : 'bg-white/5 text-gray-400 hover:bg-white/20 hover:text-white border border-transparent'
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
                                ? 'bg-gradient-to-br from-primary-start to-primary-end border-primary-start text-white shadow-lg shadow-primary-start/30' 
                                : 'bg-white/5 border-white/10 text-gray-500'
                        }`}
                    >
                        <step.icon size={16} />
                    </div>
                    <span className={`ml-2 text-xs sm:text-sm font-bold hidden md:block ${
                        currentStep >= step.id ? 'text-white' : 'text-gray-500'
                    }`}>
                        {step.label}
                    </span>
                    {index < steps.length - 1 && (
                        <div className={`w-8 sm:w-12 h-0.5 mx-2 sm:mx-4 rounded ${
                            currentStep > step.id ? 'bg-primary-start' : 'bg-white/10'
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
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-8 text-center backdrop-blur-sm">
                <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-500/10">
                    <CheckCircle className="text-emerald-400" size={32} />
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-white mb-2">{t('finance.wizard.cleanRecordTitle')}</h3>
                <p className="text-sm sm:text-base text-emerald-200/70">{t('finance.wizard.cleanRecordDesc')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {critical.length > 0 && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-5 backdrop-blur-sm">
                    <h3 className="flex items-center text-red-400 font-bold mb-4 text-sm sm:text-base">
                        <ShieldAlert className="mr-2" size={20} />
                        {t('finance.wizard.criticalIssues')} ({critical.length})
                        <span className="ml-auto text-xs bg-red-500/20 border border-red-500/20 px-2 py-1 rounded text-red-200">{t('finance.wizard.mustFix')}</span>
                    </h3>
                    <div className="space-y-2">
                        {critical.map(issue => (
                            <div key={issue.id} className="bg-black/40 border border-white/5 p-3 rounded-lg flex items-start">
                                <span className="w-1.5 h-1.5 bg-red-500 rounded-full mt-1.5 mr-2 flex-shrink-0 shadow-[0_0_5px_rgba(239,68,68,0.5)]" />
                                <p className="text-xs sm:text-sm text-gray-300 break-words">{issue.message}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {warnings.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-5 backdrop-blur-sm">
                    <h3 className="flex items-center text-amber-400 font-bold mb-4 text-sm sm:text-base">
                        <AlertTriangle className="mr-2" size={20} />
                        {t('finance.wizard.warnings')} ({warnings.length})
                        <span className="ml-auto text-xs bg-amber-500/20 border border-amber-500/20 px-2 py-1 rounded text-amber-200">{t('finance.wizard.recommended')}</span>
                    </h3>
                    <div className="space-y-2">
                        {warnings.map(issue => (
                            <div key={issue.id} className="bg-black/40 border border-white/5 p-3 rounded-lg flex items-start">
                                <span className="w-1.5 h-1.5 bg-amber-500 rounded-full mt-1.5 mr-2 flex-shrink-0 shadow-[0_0_5px_rgba(245,158,11,0.5)]" />
                                <p className="text-xs sm:text-sm text-gray-300 break-words">{issue.message}</p>
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
                <div className="bg-gradient-to-r from-primary-start/20 to-primary-end/10 border border-primary-start/30 p-4 rounded-xl mb-4">
                    <p className="text-xs text-primary-200 font-bold uppercase tracking-wider">
                        {isSmallBusiness ? t('finance.wizard.regimeSmall') : t('finance.wizard.regimeVat')}
                    </p>
                    <p className="text-sm text-white mt-1 font-medium">
                        {isSmallBusiness ? t('finance.wizard.rate9') : t('finance.wizard.rate18')}
                    </p>
                </div>

                <div className="bg-white/5 border border-white/10 p-4 rounded-xl">
                    <p className="text-xs text-gray-400 mb-1 uppercase tracking-wider font-bold">{t('finance.wizard.totalSales')}</p>
                    <p className="text-2xl font-bold text-white font-mono">€{data.total_sales_gross.toFixed(2)}</p>
                    {!isSmallBusiness && (
                        <div className="mt-2 text-xs text-emerald-400 flex items-center bg-emerald-500/10 w-fit px-2 py-1 rounded border border-emerald-500/20">
                            <span className="font-bold mr-2">{t('finance.wizard.vatCollected')}:</span>
                            €{data.vat_collected.toFixed(2)}
                        </div>
                    )}
                </div>

                {isSmallBusiness ? (
                    <div className="bg-white/5 border border-white/10 p-4 rounded-xl opacity-60">
                        <p className="text-xs text-gray-400 mb-1 uppercase tracking-wider font-bold">{t('finance.wizard.operationalExpenses')}</p>
                        <p className="text-2xl font-bold text-gray-300 font-mono">€{data.total_purchases_gross.toFixed(2)}</p>
                        <div className="mt-2 text-xs text-gray-500 flex items-center">
                            <span className="bg-white/10 px-1.5 py-0.5 rounded mr-2">{t('finance.wizard.noTaxEffect')}</span>
                        </div>
                    </div>
                ) : (
                    <div className="bg-white/5 border border-white/10 p-4 rounded-xl">
                        <p className="text-xs text-gray-400 mb-1 uppercase tracking-wider font-bold">{t('finance.wizard.totalPurchases')}</p>
                        <p className="text-2xl font-bold text-white font-mono">€{data.total_purchases_gross.toFixed(2)}</p>
                        <div className="mt-2 text-xs text-red-400 flex items-center bg-red-500/10 w-fit px-2 py-1 rounded border border-red-500/20">
                            <span className="font-bold mr-2">{t('finance.wizard.vatDeductible')}:</span>
                            €{data.vat_deductible.toFixed(2)}
                        </div>
                    </div>
                )}
            </div>

            {/* The Result Card */}
            <div className={`p-8 rounded-2xl border flex flex-col justify-center items-center text-center shadow-2xl backdrop-blur-md ${
                isPayable 
                    ? 'bg-red-500/10 border-red-500/30' 
                    : 'bg-emerald-500/10 border-emerald-500/30'
            }`}>
                <h3 className="text-lg font-medium text-gray-200 mb-4 opacity-80">
                    {data.description}
                </h3>
                <span className={`text-5xl font-bold mb-6 font-mono tracking-tight drop-shadow-lg ${isPayable ? 'text-red-400' : 'text-emerald-400'}`}>
                    €{Math.abs(data.net_obligation).toFixed(2)}
                </span>
                <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${isPayable ? 'bg-red-500/20 border-red-500/30 text-red-200' : 'bg-emerald-500/20 border-emerald-500/30 text-emerald-200'}`}>
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
        <div className="flex h-screen bg-background-dark text-white overflow-hidden font-sans relative selection:bg-primary-start/30">
             
             {/* Ambient Background */}
            <div className="fixed inset-0 pointer-events-none z-0">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary-start/10 rounded-full blur-[120px] opacity-40"></div>
                <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-secondary-start/10 rounded-full blur-[100px] opacity-30"></div>
            </div>

             <div className="flex-1 flex flex-col overflow-hidden relative z-10">
                {/* Header - Glass Style */}
                <div className="p-4 sm:p-6 border-b border-white/5 flex items-center justify-between bg-background-dark/80 backdrop-blur-xl z-20">
                    <button 
                        onClick={() => navigate('/business')} 
                        className="flex items-center text-gray-400 hover:text-white transition-colors group"
                    >
                        <ArrowLeft size={20} className="mr-2 group-hover:-translate-x-1 transition-transform" />
                        <span className="hidden sm:inline font-medium">{t('finance.wizard.back')}</span>
                        <span className="sm:hidden">{t('general.cancel')}</span>
                    </button>
                    <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight">
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
                                className="glass-input px-6 py-2.5 rounded-xl cursor-pointer capitalize text-sm sm:text-base font-medium min-w-[150px]"
                            >
                                {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                                    <option key={m} value={m} className="bg-gray-900 text-white">
                                        {format(new Date(2024, m - 1, 1), 'MMMM', { locale: currentLocale })}
                                    </option>
                                ))}
                            </select>
                            <select 
                                value={selectedYear}
                                onChange={(e) => setSelectedYear(Number(e.target.value))}
                                className="glass-input px-6 py-2.5 rounded-xl cursor-pointer text-sm sm:text-base font-medium"
                            >
                                <option value={2024} className="bg-gray-900 text-white">2024</option>
                                <option value={2025} className="bg-gray-900 text-white">2025</option>
                            </select>
                        </div>

                        <StepIndicator currentStep={step} />

                        {loading ? (
                            <div className="flex justify-center py-20">
                                <Loader2 className="animate-spin text-primary-start w-12 h-12" />
                            </div>
                        ) : errorMsg ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center glass-panel rounded-2xl p-8">
                                <div className="bg-red-500/10 p-4 rounded-full mb-4 border border-red-500/20">
                                    <AlertTriangle className="text-red-500 w-10 h-10" />
                                </div>
                                <p className="text-red-300 text-lg mb-4 font-medium">{errorMsg}</p>
                                <button onClick={fetchData} className="px-6 py-2 bg-white/10 rounded-lg text-white hover:bg-white/20 transition-colors border border-white/5">
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
                                    className="glass-high rounded-3xl p-6 sm:p-10 shadow-2xl"
                                >
                                    {step === 1 && (
                                        <div>
                                            <h2 className="text-xl sm:text-2xl font-bold mb-6 text-white">{t('finance.wizard.stepAudit')}</h2>
                                            <AuditStep issues={state.issues} />
                                        </div>
                                    )}

                                    {step === 2 && (
                                        <div>
                                            <h2 className="text-xl sm:text-2xl font-bold mb-6 text-white">{t('finance.wizard.stepTax')}</h2>
                                            <TaxStep data={state.calculation} />
                                        </div>
                                    )}

                                    {step === 3 && (
                                        <div>
                                            <div className="flex justify-between items-center mb-6">
                                                <h2 className="text-xl sm:text-2xl font-bold text-white">{t('finance.wizard.readyToFile')}</h2>
                                                <button 
                                                    onClick={handleOpenATK}
                                                    className="text-primary-300 hover:text-white text-sm font-bold flex items-center bg-primary-500/10 px-3 py-1.5 rounded-lg border border-primary-500/20 transition-colors"
                                                >
                                                    {t('finance.wizard.atk.openEdi')} <ExternalLink size={14} className="ml-2" />
                                                </button>
                                            </div>

                                            <div className="bg-black/20 rounded-2xl p-6 sm:p-8 border border-white/5 mb-8">
                                                <p className="text-gray-400 mb-6 text-sm font-medium">
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
                                                    className="bg-white/5 hover:bg-white/10 hover:text-white text-gray-300 px-8 py-3 rounded-xl font-bold flex items-center transition-all disabled:opacity-50 border border-white/10"
                                                >
                                                    {downloading ? <Loader2 className="animate-spin mr-2" size={20} /> : <Download className="mr-2" size={20} />}
                                                    {downloading ? t('general.loading') : t('finance.wizard.downloadReport')}
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    <div className="flex justify-between mt-10 pt-6 border-t border-white/10">
                                        <button 
                                            onClick={handlePrev}
                                            disabled={step === 1}
                                            className={`px-6 py-2.5 rounded-xl transition-colors font-medium ${
                                                step === 1 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-400 hover:text-white hover:bg-white/5'
                                            }`}
                                        >
                                            {t('general.cancel')}
                                        </button>
                                        
                                        {step < 3 && (
                                            <button 
                                                onClick={handleNext}
                                                disabled={step === 1 && !state.ready_to_close}
                                                className={`flex items-center px-6 py-2.5 rounded-xl font-bold transition-all shadow-lg shadow-primary-start/20 ${
                                                    step === 1 && !state.ready_to_close
                                                        ? 'bg-gray-800 text-gray-500 cursor-not-allowed shadow-none'
                                                        : 'bg-gradient-to-r from-primary-start to-primary-end text-white hover:opacity-90 active:scale-95'
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