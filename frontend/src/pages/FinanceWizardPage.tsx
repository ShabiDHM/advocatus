// FILE: src/pages/FinanceWizardPage.tsx
// PHOENIX PROTOCOL - FINANCE WIZARD UI v1.4 (DATE LOCALIZATION FIX)
// 1. FIX: Uses 'date-fns' with 'sq' locale to enforce Albanian month names.
// 2. CONSISTENCY: Matches the date behavior of BusinessPage.

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
    Loader2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiService, WizardState, AuditIssue, TaxCalculation } from '../services/api';

// PHOENIX: Date Localization Imports
import { format } from 'date-fns';
import { sq, enUS } from 'date-fns/locale';

// --- COMPONENTS ---

const StepIndicator = ({ currentStep }: { currentStep: number }) => {
    const { t } = useTranslation();
    
    const steps = [
        { id: 1, label: t('finance.wizard.stepAudit'), icon: ShieldAlert },
        { id: 2, label: t('finance.wizard.stepTax'), icon: Calculator },
        { id: 3, label: t('finance.wizard.stepFinalize'), icon: FileText },
    ];

    return (
        <div className="flex items-center justify-center space-x-4 mb-8">
            {steps.map((step, index) => (
                <div key={step.id} className="flex items-center">
                    <div 
                        className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all ${
                            currentStep >= step.id 
                                ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg shadow-indigo-500/30' 
                                : 'bg-gray-800 border-gray-600 text-gray-400'
                        }`}
                    >
                        <step.icon size={18} />
                    </div>
                    <span className={`ml-2 text-sm font-medium hidden md:block ${
                        currentStep >= step.id ? 'text-white' : 'text-gray-500'
                    }`}>
                        {step.label}
                    </span>
                    {index < steps.length - 1 && (
                        <div className={`w-12 h-1 mx-4 rounded ${
                            currentStep > step.id ? 'bg-indigo-600' : 'bg-gray-700'
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
            <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-8 text-center">
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="text-green-400" size={32} />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">{t('finance.wizard.cleanRecordTitle')}</h3>
                <p className="text-gray-400">{t('finance.wizard.cleanRecordDesc')}</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {critical.length > 0 && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                    <h3 className="flex items-center text-red-400 font-bold mb-3">
                        <ShieldAlert className="mr-2" size={20} />
                        {t('finance.wizard.criticalIssues')} ({critical.length})
                        <span className="ml-auto text-xs bg-red-500/20 px-2 py-1 rounded text-red-300">{t('finance.wizard.mustFix')}</span>
                    </h3>
                    <div className="space-y-2">
                        {critical.map(issue => (
                            <div key={issue.id} className="bg-gray-900/50 p-3 rounded-lg flex items-start">
                                <span className="w-1.5 h-1.5 bg-red-500 rounded-full mt-2 mr-2 flex-shrink-0" />
                                <p className="text-sm text-gray-300">{issue.message}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {warnings.length > 0 && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
                    <h3 className="flex items-center text-yellow-400 font-bold mb-3">
                        <AlertTriangle className="mr-2" size={20} />
                        {t('finance.wizard.warnings')} ({warnings.length})
                        <span className="ml-auto text-xs bg-yellow-500/20 px-2 py-1 rounded text-yellow-300">{t('finance.wizard.recommended')}</span>
                    </h3>
                    <div className="space-y-2">
                        {warnings.map(issue => (
                            <div key={issue.id} className="bg-gray-900/50 p-3 rounded-lg flex items-start">
                                <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full mt-2 mr-2 flex-shrink-0" />
                                <p className="text-sm text-gray-300">{issue.message}</p>
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

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Box 10 & 30 equivalents */}
            <div className="space-y-4">
                <div className="bg-gray-800/50 border border-gray-700 p-4 rounded-xl">
                    <p className="text-sm text-gray-400 mb-1">{t('finance.wizard.totalSales')}</p>
                    <p className="text-2xl font-bold text-white">€{data.total_sales_gross.toFixed(2)}</p>
                    <div className="mt-2 text-xs text-green-400 flex items-center">
                        <span className="bg-green-500/20 px-1.5 py-0.5 rounded mr-2">{t('finance.wizard.vatCollected')}</span>
                        €{data.vat_collected.toFixed(2)}
                    </div>
                </div>

                <div className="bg-gray-800/50 border border-gray-700 p-4 rounded-xl">
                    <p className="text-sm text-gray-400 mb-1">{t('finance.wizard.totalPurchases')}</p>
                    <p className="text-2xl font-bold text-white">€{data.total_purchases_gross.toFixed(2)}</p>
                    <div className="mt-2 text-xs text-red-400 flex items-center">
                        <span className="bg-red-500/20 px-1.5 py-0.5 rounded mr-2">{t('finance.wizard.vatDeductible')}</span>
                        €{data.vat_deductible.toFixed(2)}
                    </div>
                </div>
            </div>

            {/* The Result Card */}
            <div className={`p-6 rounded-xl border-2 flex flex-col justify-center items-center text-center ${
                isPayable 
                    ? 'bg-red-500/10 border-red-500/30' 
                    : 'bg-green-500/10 border-green-500/30'
            }`}>
                <h3 className="text-lg font-medium text-gray-300 mb-2">
                    {isPayable ? t('finance.wizard.netPayable') : t('finance.wizard.netCredit')}
                </h3>
                <span className={`text-4xl font-bold mb-4 ${isPayable ? 'text-red-400' : 'text-green-400'}`}>
                    €{Math.abs(data.net_obligation).toFixed(2)}
                </span>
                <p className="text-sm text-gray-400">
                    {isPayable 
                        ? t('finance.wizard.payableHint') 
                        : t('finance.wizard.creditHint')}
                </p>
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

    // PHOENIX: Localization Logic (Matches BusinessPage)
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

    const handleNext = () => {
        if (step < 3) setStep(step + 1);
    };

    const handlePrev = () => {
        if (step > 1) setStep(step - 1);
    };

    return (
        <div className="flex h-screen bg-[#030711] text-white overflow-hidden font-sans">
             <div className="flex-1 flex flex-col overflow-hidden relative">
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/20 via-transparent to-blue-900/10 pointer-events-none" />
                
                {/* Header Navigation */}
                <div className="p-6 border-b border-white/5 flex items-center justify-between bg-[#030711]/80 backdrop-blur-md z-10">
                    <button 
                        onClick={() => navigate('/business')} 
                        className="flex items-center text-gray-400 hover:text-white transition-colors"
                    >
                        <ArrowLeft size={20} className="mr-2" />
                        {t('finance.wizard.back')}
                    </button>
                    <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                        {t('finance.monthlyClose')}
                    </h1>
                    <div className="w-24" />
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 md:p-12">
                    <div className="max-w-4xl mx-auto">
                        
                        {/* Month Selector - STRICTLY LOCALIZED */}
                        <div className="flex justify-center mb-8">
                            <select 
                                value={selectedMonth}
                                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                                className="bg-gray-800 border border-gray-700 text-white rounded-l-lg px-4 py-2 focus:outline-none capitalize"
                            >
                                {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
                                    <option key={m} value={m}>
                                        {/* PHOENIX: Uses date-fns with 'sq' locale to guarantee 'Nëntor' */}
                                        {format(new Date(2024, m - 1, 1), 'MMMM', { locale: currentLocale })}
                                    </option>
                                ))}
                            </select>
                            <select 
                                value={selectedYear}
                                onChange={(e) => setSelectedYear(Number(e.target.value))}
                                className="bg-gray-800 border border-gray-700 text-white rounded-r-lg px-4 py-2 border-l-0 focus:outline-none"
                            >
                                <option value={2024}>2024</option>
                                <option value={2025}>2025</option>
                            </select>
                        </div>

                        <StepIndicator currentStep={step} />

                        {loading ? (
                            <div className="flex justify-center py-20">
                                <Loader2 className="animate-spin text-indigo-500 w-12 h-12" />
                            </div>
                        ) : errorMsg ? (
                            <div className="flex flex-col items-center justify-center py-20 text-center">
                                <div className="bg-red-500/10 p-4 rounded-full mb-4">
                                    <AlertTriangle className="text-red-500 w-10 h-10" />
                                </div>
                                <p className="text-red-400 text-lg mb-2">{errorMsg}</p>
                                <button onClick={fetchData} className="px-6 py-2 bg-gray-800 rounded-lg text-white hover:bg-gray-700 transition-colors">
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
                                    className="bg-gray-900/50 backdrop-blur-sm border border-white/10 rounded-2xl p-6 md:p-10 shadow-xl"
                                >
                                    {step === 1 && (
                                        <div>
                                            <h2 className="text-2xl font-bold mb-6">{t('finance.wizard.stepAudit')}</h2>
                                            <AuditStep issues={state.issues} />
                                        </div>
                                    )}

                                    {step === 2 && (
                                        <div>
                                            <h2 className="text-2xl font-bold mb-6">{t('finance.wizard.stepTax')} (ATK)</h2>
                                            <TaxStep data={state.calculation} />
                                        </div>
                                    )}

                                    {step === 3 && (
                                        <div className="text-center py-10">
                                            <div className="w-20 h-20 bg-indigo-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                                                <FileText className="text-indigo-400" size={40} />
                                            </div>
                                            <h2 className="text-2xl font-bold mb-2">{t('finance.wizard.readyToFile')}</h2>
                                            <p className="text-gray-400 max-w-md mx-auto mb-8">
                                                {t('finance.wizard.readyDesc')}
                                            </p>
                                            <button 
                                                onClick={handleDownloadReport}
                                                disabled={downloading}
                                                className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-3 rounded-lg font-medium flex items-center mx-auto transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                {downloading ? <Loader2 className="animate-spin mr-2" size={20} /> : <Download className="mr-2" size={20} />}
                                                {downloading ? t('general.loading') : t('finance.wizard.downloadReport')}
                                            </button>
                                        </div>
                                    )}

                                    {/* Action Buttons */}
                                    <div className="flex justify-between mt-10 pt-6 border-t border-gray-800">
                                        <button 
                                            onClick={handlePrev}
                                            disabled={step === 1}
                                            className={`px-6 py-2 rounded-lg transition-colors ${
                                                step === 1 ? 'text-gray-600 cursor-not-allowed' : 'text-gray-300 hover:bg-gray-800'
                                            }`}
                                        >
                                            {t('general.cancel')}
                                        </button>
                                        
                                        {step < 3 && (
                                            <button 
                                                onClick={handleNext}
                                                disabled={step === 1 && !state.ready_to_close}
                                                className={`flex items-center px-6 py-2 rounded-lg font-medium transition-all ${
                                                    step === 1 && !state.ready_to_close
                                                        ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                                                        : 'bg-white text-black hover:bg-gray-200'
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