// FILE: src/components/business/finance/ExpenseModal.tsx
// PHOENIX PROTOCOL - EXPENSE MODAL V2.3 (DATETIME FIX + UI FIX)
// 1. FIX: Mobile scanning datetime serialization error
// 2. FIX: Long case titles and "ZGJIDHNI RASTIN" properly constrained
// 3. PROTOCOL: Robust datetime handling with JSON-safe serialization

import React, { useState, useRef, useEffect } from 'react';
import { X, MinusCircle, UploadCloud, QrCode, ChevronLeft, Loader2, CheckCircle, Paperclip, Sparkles, Camera, Link as LinkIcon, AlertCircle, ShieldCheck, Calendar } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Expense, Case } from '../../../data/types';
import { apiService } from '../../../services/api';
import { useTranslation } from 'react-i18next';
import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { sq, enUS } from 'date-fns/locale';

const DatePicker = (ReactDatePicker as any).default;

interface ExpenseModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: (expense: Expense, isUpdate: boolean) => void;
    cases: Case[];
    editingExpense: Expense | null;
}

// PROTOCOL: JSON-Safe Datetime Handling
const DateTimeProtocol = {
    serializeDate: (date: Date | null): string | null => {
        if (!date) return null;
        return date.toISOString().split('T')[0]; // YYYY-MM-DD format
    },
    
    parseDate: (dateString: string | Date | null): Date | null => {
        if (!dateString) return null;
        if (dateString instanceof Date) return dateString;
        
        try {
            const date = new Date(dateString);
            return isNaN(date.getTime()) ? null : date;
        } catch (e) {
            console.warn('[DATETIME-PROTOCOL] Failed to parse date:', dateString);
            return null;
        }
    },
    
    isValidJSONDate: (date: any): boolean => {
        if (!date) return false;
        if (date instanceof Date) {
            try {
                JSON.stringify({ test: date.toISOString() });
                return true;
            } catch {
                return false;
            }
        }
        return typeof date === 'string';
    }
};

// PROTOCOL: UI Layout Verification
const UILayoutProtocol = {
    VERIFY_CONTAINMENT: true,
    MAX_DISPLAY_LENGTH: 35,
    TRUNCATION_MARKER: '...',
    ENFORCE_BOUNDARIES: true
};

export const ExpenseModal: React.FC<ExpenseModalProps> = ({ isOpen, onClose, onSuccess, cases, editingExpense }) => {
    const { t, i18n } = useTranslation();
    const [uploadMode, setUploadMode] = useState<'initial' | 'direct' | 'mobile'>('initial');
    const [isScanningReceipt, setIsScanningReceipt] = useState(false);
    const [expenseReceipt, setExpenseReceipt] = useState<File | null>(null);
    
    const fileInputRef = useRef<HTMLInputElement>(null);
    const cameraInputRef = useRef<HTMLInputElement>(null);
    
    const [loading, setLoading] = useState(false);
    const [uiProtocolActive, setUiProtocolActive] = useState(true);
    const [datetimeProtocolActive, setDatetimeProtocolActive] = useState(true);

    const [qrContent, setQrContent] = useState<string | null>(null);
    const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
    const [isMobileDevice, setIsMobileDevice] = useState(false);
    const [qrLoadError, setQrLoadError] = useState(false);

    const [expenseDate, setExpenseDate] = useState<Date | null>(new Date());
    const [formData, setFormData] = useState({ category: '', amount: 0, description: '', related_case_id: '' });

    const localeMap: { [key: string]: any } = { sq, al: sq, en: enUS };
    const currentLocale = localeMap[i18n.language] || enUS;

    // PROTOCOL: Smart text truncation
    const truncateCaseTitle = (title: string, maxLength: number = UILayoutProtocol.MAX_DISPLAY_LENGTH): string => {
        if (!title) return title;
        if (title.length <= maxLength) return title;
        
        const truncated = title.substring(0, maxLength - 3) + UILayoutProtocol.TRUNCATION_MARKER;
        
        if (uiProtocolActive && title.length > maxLength) {
            console.warn(`[UI-PROTOCOL] Truncated case title: "${title}" → "${truncated}"`);
        }
        
        return truncated;
    };

    // PROTOCOL: Format "No Case" option
    const formatNoCaseOption = (): string => {
        const noCaseText = `-- ${t('finance.noCase', 'Pa Lëndë')} --`;
        return noCaseText;
    };

    // PROTOCOL: Verify UI layout
    const verifyUILayout = (): boolean => {
        if (!uiProtocolActive) return true;
        
        const issues: string[] = [];
        
        cases.forEach(caseItem => {
            if (caseItem.title.length > UILayoutProtocol.MAX_DISPLAY_LENGTH) {
                issues.push(`Case "${caseItem.title}" exceeds ${UILayoutProtocol.MAX_DISPLAY_LENGTH} chars`);
            }
        });
        
        if (formData.category.length > 50) issues.push(`Category field exceeds 50 chars`);
        if (formData.description.length > 200) issues.push(`Description field exceeds 200 chars`);
        
        if (issues.length > 0) {
            console.warn('[UI-PROTOCOL] Layout issues detected:', issues);
            return false;
        }
        
        console.log('[UI-PROTOCOL] All UI elements within boundaries ✓');
        return true;
    };

    // PROTOCOL: Safe AI result processing
    const processAIResult = (aiResult: any): Partial<typeof formData> & { date?: Date | null } => {
        const processed: Partial<typeof formData> & { date?: Date | null } = {};
        
        if (!aiResult) return processed;
        
        // Handle category
        if (aiResult.category && typeof aiResult.category === 'string') {
            processed.category = aiResult.category.substring(0, 50); // Enforce max length
        }
        
        // Handle amount
        if (aiResult.amount !== undefined && aiResult.amount !== null) {
            const amount = parseFloat(aiResult.amount);
            if (!isNaN(amount)) {
                processed.amount = amount;
            }
        }
        
        // Handle description
        if (aiResult.description && typeof aiResult.description === 'string') {
            processed.description = aiResult.description.substring(0, 200);
        }
        
        // PROTOCOL: Safe datetime handling
        if (aiResult.date) {
            if (datetimeProtocolActive) {
                console.log('[DATETIME-PROTOCOL] Processing AI date:', aiResult.date);
                
                // Handle various date formats
                if (aiResult.date instanceof Date) {
                    if (DateTimeProtocol.isValidJSONDate(aiResult.date)) {
                        processed.date = aiResult.date;
                    } else {
                        // Convert to ISO string first
                        processed.date = DateTimeProtocol.parseDate(aiResult.date.toISOString());
                    }
                } else if (typeof aiResult.date === 'string') {
                    processed.date = DateTimeProtocol.parseDate(aiResult.date);
                }
                
                if (processed.date && isNaN(processed.date.getTime())) {
                    console.warn('[DATETIME-PROTOCOL] Invalid date parsed, using current date');
                    processed.date = null;
                }
            } else {
                // Fallback parsing
                try {
                    const date = new Date(aiResult.date);
                    processed.date = isNaN(date.getTime()) ? null : date;
                } catch (e) {
                    console.warn('[DATETIME-PROTOCOL] Fallback parsing failed:', e);
                    processed.date = null;
                }
            }
        }
        
        // Log protocol results
        if (datetimeProtocolActive) {
            console.log('[DATETIME-PROTOCOL] Processed AI result:', {
                originalDate: aiResult.date,
                processedDate: processed.date,
                type: typeof aiResult.date
            });
        }
        
        return processed;
    };

    useEffect(() => {
        const checkMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        setIsMobileDevice(checkMobile);

        if (isOpen) {
            if (editingExpense) {
                setFormData({
                    category: editingExpense.category,
                    amount: editingExpense.amount,
                    description: editingExpense.description || '',
                    related_case_id: editingExpense.related_case_id || ''
                });
                setExpenseDate(DateTimeProtocol.parseDate(editingExpense.date));
            } else {
                setFormData({ category: '', amount: 0, description: '', related_case_id: '' });
                setExpenseDate(new Date());
                setExpenseReceipt(null);
                setUploadMode('initial');
                setQrContent(null);
                setQrLoadError(false);
            }
            
            if (uiProtocolActive) {
                setTimeout(() => verifyUILayout(), 100);
            }
        }
    }, [isOpen, editingExpense]);

    useEffect(() => {
        return () => {
            if (pollingInterval) clearInterval(pollingInterval);
        };
    }, [pollingInterval]);
    
    const handleMobileAction = () => {
        if (isMobileDevice) {
            cameraInputRef.current?.click();
        } else {
            startMobileSession();
        }
    };

    const startMobileSession = async () => {
        try {
            setUploadMode('mobile');
            setQrContent(null);
            setQrLoadError(false);
            
            const response = await apiService.createMobileUploadSession(formData.related_case_id || undefined);
            const token = (response as any).token || response.upload_url.split('/').pop();

            if (token) {
                const frontendUrl = `${window.location.origin}/mobile-upload/${token}`;
                setQrContent(frontendUrl);

                const interval = setInterval(async () => {
                    try {
                        const status = await apiService.checkMobileUploadStatus(token);
                        if (status.status === 'complete') {
                            clearInterval(interval);
                            await handleMobileUploadComplete(token);
                        }
                    } catch (e) {
                        console.error("Polling error", e);
                    }
                }, 2000);
                setPollingInterval(interval);
            }
        } catch (error) {
            console.error("Failed to start mobile session", error);
            alert(t('error.generic'));
            setUploadMode('initial');
        }
    };

    const handleMobileUploadComplete = async (token: string) => {
        try {
            const { blob, filename } = await apiService.getMobileSessionFile(token);
            const file = new File([blob], filename, { type: blob.type });
            await handleReceiptUpload(file, true);
            setUploadMode('direct'); 
        } catch (error) {
            console.error("Failed to retrieve mobile file", error);
            alert(t('error.generic'));
        }
    };

    const handleReceiptUpload = async (file: File, shouldScan: boolean = false) => {
        if (!file) return;
        setExpenseReceipt(file);
        
        if (shouldScan && !editingExpense) {
            setIsScanningReceipt(true);
            try {
                const aiResult = await apiService.analyzeExpenseReceipt(file);
                console.log('[DATETIME-PROTOCOL] AI Analysis Result:', aiResult);
                
                // Use protocol-safe processing
                const processedResult = processAIResult(aiResult);
                
                setFormData(prev => ({
                    ...prev,
                    category: processedResult.category || prev.category,
                    amount: processedResult.amount !== undefined ? processedResult.amount : prev.amount,
                    description: processedResult.description || prev.description
                }));
                
                if (processedResult.date !== undefined) {
                    setExpenseDate(processedResult.date);
                }
                
            } catch (err) {
                console.error('[DATETIME-PROTOCOL] AI Scan failed:', err);
                console.warn("Falling back to manual entry");
            } finally {
                setIsScanningReceipt(false);
            }
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (uiProtocolActive && !verifyUILayout()) {
            console.warn('[UI-PROTOCOL] Submission blocked due to layout issues');
            alert(t('error.uiLayoutIssue', 'Please check form field lengths before saving.'));
            return;
        }
        
        setLoading(true);
        try {
            // PROTOCOL: Safe date serialization
            const dateString = DateTimeProtocol.serializeDate(expenseDate) || 
                              new Date().toISOString().split('T')[0];
            
            const payload = {
                ...formData,
                date: dateString
            };

            console.log('[DATETIME-PROTOCOL] Submitting payload:', payload);

            let result: Expense;
            if (editingExpense) {
                result = await apiService.updateExpense(editingExpense.id, payload);
                if (expenseReceipt && result.id) {
                    await apiService.uploadExpenseReceipt(result.id, expenseReceipt);
                    result.receipt_url = `updated/${Date.now()}`;
                }
                onSuccess(result, true);
            } else {
                result = await apiService.createExpense(payload);
                if (expenseReceipt && result.id) {
                    await apiService.uploadExpenseReceipt(result.id, expenseReceipt);
                    result.receipt_url = `uploaded/${Date.now()}`;
                }
                onSuccess(result, false);
            }

            onClose();
        } catch (error) {
            console.error('Submit error:', error);
            alert(t('error.generic'));
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="glass-high w-full max-w-md max-h-[90vh] overflow-y-auto custom-finance-scroll p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200">
                {/* Protocol Headers */}
                <div className="mb-4 -mt-2 space-y-2">
                    {uiProtocolActive && (
                        <div className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-1.5 border border-primary-start/20">
                            <div className="flex items-center gap-2">
                                <ShieldCheck size={14} className="text-primary-start" />
                                <span className="text-xs font-bold text-primary-300">UI PROTOCOL ACTIVE</span>
                            </div>
                            <button 
                                onClick={() => setUiProtocolActive(!uiProtocolActive)}
                                className="text-[10px] text-gray-400 hover:text-white transition-colors"
                            >
                                {uiProtocolActive ? 'Disable' : 'Enable'}
                            </button>
                        </div>
                    )}
                    
                    {datetimeProtocolActive && (
                        <div className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-1.5 border border-blue-500/20">
                            <div className="flex items-center gap-2">
                                <Calendar size={14} className="text-blue-500" />
                                <span className="text-xs font-bold text-blue-400">DATETIME PROTOCOL ACTIVE</span>
                            </div>
                            <button 
                                onClick={() => setDatetimeProtocolActive(!datetimeProtocolActive)}
                                className="text-[10px] text-gray-400 hover:text-white transition-colors"
                            >
                                {datetimeProtocolActive ? 'Disable' : 'Enable'}
                            </button>
                        </div>
                    )}
                </div>

                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <MinusCircle size={20} className="text-rose-500" /> {editingExpense ? t('finance.editExpense') : t('finance.addExpense')}
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={24} /></button>
                </div>

                {/* Hidden Inputs */}
                <input type="file" ref={fileInputRef} className="hidden" accept="image/*,.pdf" onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                        setUploadMode('direct');
                        handleReceiptUpload(file, false);
                    }
                }} />
                <input type="file" ref={cameraInputRef} className="hidden" accept="image/*" capture="environment" onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                        setUploadMode('direct');
                        handleReceiptUpload(file, true);
                    }
                }} />

                <div className="mb-6">
                    <AnimatePresence mode="wait">
                        {uploadMode === 'initial' && (
                            <motion.div key="initial" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                                <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.receipt', 'Fatura')}</label>
                                <div className="grid grid-cols-2 gap-3">
                                    <button type="button" onClick={() => fileInputRef.current?.click()} className="w-full py-3 border border-dashed border-white/20 rounded-xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:bg-white/5 hover:text-white hover:border-white/40 transition-all text-xs font-bold">
                                        <UploadCloud size={20} />
                                        <span>{t('finance.uploadDirectly', 'Ngarko Skedar')}</span>
                                    </button>
                                    
                                    <button type="button" onClick={handleMobileAction} className="w-full py-3 border border-dashed border-white/20 rounded-xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:bg-white/5 hover:text-white hover:border-white/40 transition-all text-xs font-bold">
                                        {isMobileDevice ? <Camera size={20} /> : <QrCode size={20} />}
                                        <span>{isMobileDevice ? t('finance.takePhoto', 'Bëj Foto') : t('finance.scanWithMobile', 'Skano me Celular')}</span>
                                    </button>
                                </div>
                            </motion.div>
                        )}

                        {uploadMode === 'direct' && (
                            <motion.div key="direct" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="block text-xs text-gray-400 font-bold uppercase">{t('finance.uploadDirectly', 'Ngarko Skedar')}</label>
                                    <button type="button" onClick={() => { setUploadMode('initial'); setExpenseReceipt(null); }} className="text-xs flex items-center gap-1 text-gray-400 hover:text-white"> <ChevronLeft size={14}/> {t('general.back', 'Kthehu')} </button>
                                </div>
                                
                                <button 
                                    onClick={() => fileInputRef.current?.click()} 
                                    disabled={isScanningReceipt}
                                    className={`w-full py-4 border border-dashed rounded-xl flex items-center justify-center gap-2 transition-all 
                                        ${expenseReceipt ? 'bg-primary-start/10 border-primary-start text-primary-300' : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'}
                                        ${isScanningReceipt ? 'cursor-wait opacity-80' : ''}`}
                                >
                                    {isScanningReceipt ? (
                                        <><Loader2 size={18} className="animate-spin" /> {t('finance.scanning', 'Analizimi me AI...')}</>
                                    ) : expenseReceipt ? (
                                        <><CheckCircle size={18} /> 
                                            <span className="max-w-[200px] truncate" title={expenseReceipt.name}>
                                                {expenseReceipt.name}
                                            </span>
                                        </>
                                    ) : (
                                        <><Paperclip size={18} /> {t('finance.attachReceiptOptional', 'Bashkangjit Faturën (Opcionale)')}</>
                                    )}
                                </button>
                                {isScanningReceipt && (
                                    <p className="text-center text-[10px] text-gray-500 mt-2 flex items-center justify-center gap-1">
                                        <Sparkles size={10} className="text-primary-start"/> 
                                        {t('finance.extractingData', 'Duke nxjerrë të dhënat...')}
                                        {datetimeProtocolActive && ' (Protocol Active)'}
                                    </p>
                                )}
                            </motion.div>
                        )}
                        
                        {uploadMode === 'mobile' && (
                            <motion.div key="mobile" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="block text-xs text-gray-400 font-bold uppercase">{t('finance.scanWithMobile', 'Skano me Celular')}</label>
                                    <button type="button" onClick={() => { setUploadMode('initial'); if(pollingInterval) clearInterval(pollingInterval); }} className="text-xs flex items-center gap-1 text-gray-400 hover:text-white"> <ChevronLeft size={14}/> {t('general.back', 'Kthehu')} </button>
                                </div>
                                
                                <div className="bg-white rounded-lg p-4 flex items-center justify-center aspect-square relative">
                                    {!qrContent ? (
                                        <Loader2 className="animate-spin text-gray-400" size={32} />
                                    ) : qrLoadError ? (
                                        <div className="flex flex-col items-center justify-center text-center p-2">
                                            <AlertCircle size={32} className="text-red-400 mb-2" />
                                            <p className="text-xs text-gray-600 mb-3">{t('finance.qrFailed', 'QR Code nuk mund të shfaqet.')}</p>
                                            <a href={qrContent} target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-blue-500 text-white rounded-lg text-xs font-bold flex items-center gap-2 hover:bg-blue-600">
                                                <LinkIcon size={12} /> Linku i Ngarkimit
                                            </a>
                                        </div>
                                    ) : (
                                        <img 
                                            src={`https://quickchart.io/qr?text=${encodeURIComponent(qrContent)}&size=300&margin=1`} 
                                            alt="QR Code" 
                                            className="w-full h-full object-contain"
                                            onError={() => setQrLoadError(true)}
                                        />
                                    )}
                                </div>
                                <p className="text-center text-xs text-gray-400 mt-3 animate-pulse">
                                    {t('finance.scanInstructions', 'Skano këtë kod me celularin për të ngarkuar faturën.')}
                                </p>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel', "Lënda e Lidhur")}</label>
                        <select 
                            value={formData.related_case_id} 
                            onChange={e => setFormData({...formData, related_case_id: e.target.value})} 
                            className="glass-input w-full px-4 py-2.5 rounded-xl truncate"
                            style={{ 
                                maxWidth: '100%',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                            }}
                        >
                            <option value="" className="bg-gray-900 truncate" title={formatNoCaseOption()}>
                                {formatNoCaseOption()}
                            </option>
                            {cases.map(c => (
                                <option 
                                    key={c.id} 
                                    value={c.id} 
                                    className="bg-gray-900 truncate"
                                    title={c.title}
                                >
                                    {truncateCaseTitle(c.title)}
                                </option>
                            ))}
                        </select>
                        {!formData.related_case_id && (
                            <p className="text-[10px] text-gray-500 mt-1 flex items-center gap-1">
                                {t('finance.generalUpload', 'Pa lëndë: Do të regjistrohet si shpenzim i përgjithshëm.')}
                            </p>
                        )}
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.expenseCategory')}</label>
                        <input 
                            required 
                            type="text" 
                            className="glass-input w-full px-4 py-2.5 rounded-xl truncate"
                            maxLength={50}
                            value={formData.category} 
                            onChange={e => setFormData({...formData, category: e.target.value})} 
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.amount')}</label>
                        <input required type="number" step="0.01" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.amount} onChange={e => setFormData({...formData, amount: parseFloat(e.target.value)})} />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.date')}</label>
                        <DatePicker 
                            selected={expenseDate} 
                            onChange={(date: Date | null) => setExpenseDate(date)} 
                            locale={currentLocale} 
                            dateFormat="dd/MM/yyyy" 
                            className="glass-input w-full px-4 py-2.5 rounded-xl" 
                            required 
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.description')}</label>
                        <textarea 
                            rows={2} 
                            className="glass-input w-full px-4 py-2.5 rounded-xl resize-none"
                            maxLength={200}
                            value={formData.description} 
                            onChange={e => setFormData({...formData, description: e.target.value})} 
                        />
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                        <button type="button" onClick={onClose} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10 transition-colors">{t('general.cancel')}</button>
                        <button type="submit" disabled={loading} className="px-8 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-bold shadow-lg shadow-rose-500/20 flex items-center gap-2">
                            {loading && <Loader2 size={18} className="animate-spin"/>}
                            {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};