// FILE: src/components/business/finance/ExpenseModal.tsx
// PHOENIX PROTOCOL - EXPENSE MODAL V3.0 (OCR GATEKEEPER)
// 1. FEAT: Implemented 'isPro' check to lock AI OCR scanning for Basic users.
// 2. UI: Added visual Lock indicator and disabled state for the Scan button.
// 3. UX: Manual attachment remains fully accessible for all tiers.

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { X, MinusCircle, ChevronLeft, Loader2, CheckCircle, Paperclip, Sparkles, ScanLine, AlertCircle, Lock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Expense, Case } from '../../../data/types';
import { apiService } from '../../../services/api';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../../context/AuthContext'; // PHOENIX: Imported Auth Hook
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

// Protocol to handle Python datetime objects from backend
const DateTimeProtocol = {
    safeDateToString: (date: any): string => {
        if (!date) return new Date().toISOString().split('T')[0];
        if (date instanceof Date) return date.toISOString().split('T')[0];
        if (typeof date === 'object' && date !== null) {
            try {
                if (date.toISOString && typeof date.toISOString === 'function') return date.toISOString().split('T')[0];
                const dateStr = JSON.stringify(date);
                const parsed = new Date(dateStr);
                if (!isNaN(parsed.getTime())) return parsed.toISOString().split('T')[0];
            } catch (e) {
                console.warn('Failed to convert object to date:', e);
            }
        }
        if (typeof date === 'string') {
            const parsed = new Date(date);
            if (!isNaN(parsed.getTime())) return parsed.toISOString().split('T')[0];
        }
        return new Date().toISOString().split('T')[0];
    },
    extractDate: (value: any): Date | null => {
        if (!value) return null;
        if (value instanceof Date) return isNaN(value.getTime()) ? null : value;
        if (typeof value === 'string') {
            const date = new Date(value);
            return isNaN(date.getTime()) ? null : date;
        }
        if (typeof value === 'object') {
            try {
                const dateStr = value.iso || value.isoformat?.() || JSON.stringify(value);
                const date = new Date(dateStr);
                return isNaN(date.getTime()) ? null : date;
            } catch (e) { return null; }
        }
        return null;
    }
};

// COMPRESSION UTILITY
const compressImage = async (file: File): Promise<File> => {
    if (!file.type.startsWith('image/')) return file;
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target?.result as string;
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const MAX_WIDTH = 1920;
                const MAX_HEIGHT = 1920;
                let width = img.width;
                let height = img.height;
                if (width > height) { if (width > MAX_WIDTH) { height *= MAX_WIDTH / width; width = MAX_WIDTH; } } 
                else { if (height > MAX_HEIGHT) { width *= MAX_HEIGHT / height; height = MAX_HEIGHT; } }
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx?.drawImage(img, 0, 0, width, height);
                canvas.toBlob((blob) => {
                    if (blob) { const newFile = new File([blob], file.name, { type: 'image/jpeg', lastModified: Date.now() }); resolve(newFile); } 
                    else { reject(new Error('Compression failed')); }
                }, 'image/jpeg', 0.8);
            };
            img.onerror = (err) => reject(err);
        };
        reader.onerror = (err) => reject(err);
    });
};

export const ExpenseModal: React.FC<ExpenseModalProps> = ({ isOpen, onClose, onSuccess, cases, editingExpense }) => {
    const { t, i18n } = useTranslation();
    const { user } = useAuth(); // PHOENIX: Access user context
    const [isDirectUpload, setIsDirectUpload] = useState(false);
    const [isScanningReceipt, setIsScanningReceipt] = useState(false);
    const [scanError, setScanError] = useState<string | null>(null);
    const [expenseReceipt, setExpenseReceipt] = useState<File | null>(null);
    
    const scanInputRef = useRef<HTMLInputElement>(null);
    const attachInputRef = useRef<HTMLInputElement>(null);
    const uploadIntent = useRef<'scan' | 'attach'>('scan');

    const [loading, setLoading] = useState(false);
    const [expenseDate, setExpenseDate] = useState<Date | null>(new Date());
    const [formData, setFormData] = useState({ category: '', amount: 0, description: '', related_case_id: '' });

    const localeMap: { [key: string]: any } = { sq, al: sq, en: enUS };
    const currentLocale = localeMap[i18n.language] || enUS;

    // PHOENIX GATEKEEPER LOGIC
    const isPro = useMemo(() => {
        if (!user) return false;
        return user.subscription_tier === 'PRO' || user.role === 'ADMIN';
    }, [user]);

    const truncateText = (text: string, maxLength: number = 30): string => {
        if (!text) return text;
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    };

    useEffect(() => {
        if (isOpen) {
            setScanError(null);
            if (editingExpense) {
                setFormData({
                    category: editingExpense.category,
                    amount: editingExpense.amount,
                    description: editingExpense.description || '',
                    related_case_id: editingExpense.related_case_id || ''
                });
                setExpenseDate(DateTimeProtocol.extractDate(editingExpense.date));
                setIsDirectUpload(false);
            } else {
                setFormData({ category: '', amount: 0, description: '', related_case_id: '' });
                setExpenseDate(new Date());
                setExpenseReceipt(null);
                setIsDirectUpload(false);
            }
        }
    }, [isOpen, editingExpense]);

    const handleFileSelection = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        setScanError(null);
        if (file) {
            setIsDirectUpload(true);
            if (uploadIntent.current === 'scan') {
                try {
                    setIsScanningReceipt(true);
                    const compressedFile = await compressImage(file);
                    setExpenseReceipt(compressedFile);
                    if (!editingExpense) await handleAiScan(compressedFile);
                } catch (err) {
                    console.error("Compression/Scan error:", err);
                    setScanError("Failed to process image. Try attaching manually.");
                    setExpenseReceipt(file);
                } finally { setIsScanningReceipt(false); }
            } else {
                setExpenseReceipt(file);
            }
        }
    };

    const handleAiScan = async (file: File) => {
        try {
            const aiResult = await safeAnalyzeReceipt(file);
            if (aiResult) {
                setFormData(prev => ({
                    ...prev,
                    category: aiResult.category || prev.category,
                    amount: aiResult.amount || prev.amount,
                    description: aiResult.description || prev.description
                }));
                if (aiResult.date) {
                    const parsedDate = DateTimeProtocol.extractDate(aiResult.date);
                    if (parsedDate) setExpenseDate(parsedDate);
                }
            }
        } catch (err) {
            console.warn("AI Scan failed, falling back to manual entry", err);
            setScanError(t('finance.scanFailed', 'Skanimi dështoi. Ju lutem plotësoni fushat manualisht.'));
        }
    };

    const triggerUpload = (mode: 'scan' | 'attach') => {
        uploadIntent.current = mode;
        setScanError(null);
        if (mode === 'scan') {
            // PHOENIX: Prevent trigger if not Pro
            if (!isPro) return;
            scanInputRef.current?.click();
        } else {
            attachInputRef.current?.click();
        }
    };

    const safeAnalyzeReceipt = async (file: File): Promise<any> => {
        try {
            const result = await apiService.analyzeExpenseReceipt(file);
            return {
                category: result?.category || '',
                amount: result?.amount || 0,
                description: result?.description || '',
                date: result?.date ? DateTimeProtocol.safeDateToString(result.date) : null
            };
        } catch (error) { console.error('Receipt analysis failed:', error); throw error; }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const payload = { ...formData, date: DateTimeProtocol.safeDateToString(expenseDate) };
            let result: Expense;
            if (editingExpense) {
                result = await apiService.updateExpense(editingExpense.id, payload);
                if (expenseReceipt && result.id) await apiService.uploadExpenseReceipt(result.id, expenseReceipt);
                onSuccess(result, true);
            } else {
                result = await apiService.createExpense(payload);
                if (expenseReceipt && result.id) await apiService.uploadExpenseReceipt(result.id, expenseReceipt);
                onSuccess(result, false);
            }
            onClose();
        } catch (error) { console.error(error); alert(t('error.generic')); } finally { setLoading(false); }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="glass-high w-full max-w-md max-h-[90vh] overflow-y-auto custom-finance-scroll p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2">
                        <MinusCircle size={20} className="text-rose-500" /> {editingExpense ? t('finance.editExpense') : t('finance.addExpense')}
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={24} /></button>
                </div>

                <input type="file" ref={scanInputRef} className="hidden" accept="image/*" capture="environment" onChange={handleFileSelection} />
                <input type="file" ref={attachInputRef} className="hidden" accept="image/*,.pdf" onChange={handleFileSelection} />

                <div className="mb-6">
                    <AnimatePresence mode="wait">
                        {!isDirectUpload && !expenseReceipt ? (
                            <motion.div key="initial" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                                <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.receipt', 'Fatura')}</label>
                                
                                <div className="grid grid-cols-2 gap-3">
                                    {/* Option 1: AI Scan (LOCKED IF NOT PRO) */}
                                    <button 
                                        type="button" 
                                        onClick={() => triggerUpload('scan')} 
                                        disabled={!isPro}
                                        className={`py-6 border border-dashed rounded-xl flex flex-col items-center justify-center gap-3 transition-all group relative overflow-hidden
                                        ${!isPro 
                                            ? 'border-gray-700 bg-gray-800/50 cursor-not-allowed opacity-70' 
                                            : 'border-rose-500/30 bg-rose-500/5 text-rose-300 hover:bg-rose-500/10 hover:border-rose-500/50'
                                        }`}
                                    >
                                        {!isPro && (
                                            <div className="absolute inset-0 flex items-center justify-center bg-black/40 z-10">
                                                <Lock size={24} className="text-white/80" />
                                            </div>
                                        )}
                                        <div className={`p-3 rounded-full transition-transform ${isPro ? 'bg-rose-500/10 group-hover:scale-110' : 'bg-gray-700'}`}>
                                            <ScanLine size={24} className={isPro ? "" : "text-gray-500"} />
                                        </div>
                                        <div className="text-center px-2">
                                            <span className={`block text-sm font-bold ${isPro ? "" : "text-gray-400"}`}>{t('finance.scanAI', 'Skano me AI')}</span>
                                            <span className="text-[9px] opacity-60 block mt-1">OCR & Auto-Fill</span>
                                        </div>
                                    </button>

                                    {/* Option 2: Simple Attach (ALWAYS AVAILABLE) */}
                                    <button 
                                        type="button" 
                                        onClick={() => triggerUpload('attach')} 
                                        className="py-6 border border-dashed border-white/20 rounded-xl flex flex-col items-center justify-center gap-3 text-gray-400 hover:bg-white/5 hover:text-white hover:border-white/40 transition-all group"
                                    >
                                        <div className="p-3 bg-white/5 rounded-full group-hover:scale-110 transition-transform">
                                            <Paperclip size={24} />
                                        </div>
                                        <div className="text-center px-2">
                                            <span className="block text-sm font-bold">{t('finance.attachOnly', 'Bashkangjit')}</span>
                                            <span className="text-[9px] opacity-60 block mt-1">PDF, JPG, PNG</span>
                                        </div>
                                    </button>
                                </div>
                            </motion.div>
                        ) : (
                            <motion.div key="direct" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="block text-xs text-gray-400 font-bold uppercase">{t('finance.uploadDirectly', 'Ngarko Skedar')}</label>
                                    <button type="button" onClick={() => { setIsDirectUpload(false); setExpenseReceipt(null); setScanError(null); }} className="text-xs flex items-center gap-1 text-gray-400 hover:text-white"> <ChevronLeft size={14} /> {t('general.back', 'Kthehu')} </button>
                                </div>

                                <button
                                    onClick={() => triggerUpload(uploadIntent.current)}
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
                                        <><Paperclip size={18} /> {t('finance.changeFile', 'Ndrysho Skedarin')}</>
                                    )}
                                </button>
                                
                                {isScanningReceipt && <p className="text-center text-[10px] text-gray-500 mt-2 flex items-center justify-center gap-1"><Sparkles size={10} className="text-primary-start" /> {t('finance.extractingData', 'Duke nxjerrë të dhënat...')}</p>}
                                
                                {scanError && (
                                    <motion.div initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} className="mt-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-200 text-xs">
                                        <AlertCircle size={14} className="shrink-0" />
                                        <span>{scanError}</span>
                                    </motion.div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel', "Lënda e Lidhur")}</label>
                        <select
                            value={formData.related_case_id}
                            onChange={(e) => setFormData({ ...formData, related_case_id: e.target.value })}
                            className="glass-input w-full px-4 py-2.5 rounded-xl truncate"
                            style={{ maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                        >
                            <option value="" className="bg-gray-900 truncate">-- {t('finance.noCase', 'Pa Lëndë')} --</option>
                            {cases.map(c => (<option key={c.id} value={c.id} className="bg-gray-900 truncate" title={c.title}>{truncateText(c.title)}</option>))}
                        </select>
                        {!formData.related_case_id && (<p className="text-[10px] text-gray-500 mt-1 flex items-center gap-1">{t('finance.generalUpload', 'Pa lëndë: Do të regjistrohet si shpenzim i përgjithshëm.')}</p>)}
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.expenseCategory')}</label>
                        <input required type="text" className="glass-input w-full px-4 py-2.5 rounded-xl truncate" maxLength={50} value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.amount')}</label>
                        <input required type="number" step="0.01" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) })} />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.date')}</label>
                        <DatePicker selected={expenseDate} onChange={(date: Date | null) => setExpenseDate(date)} locale={currentLocale} dateFormat="dd/MM/yyyy" className="glass-input w-full px-4 py-2.5 rounded-xl" required />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.description')}</label>
                        <textarea rows={2} className="glass-input w-full px-4 py-2.5 rounded-xl resize-none" maxLength={200} value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                        <button type="button" onClick={onClose} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10 transition-colors">{t('general.cancel')}</button>
                        <button type="submit" disabled={loading} className="px-8 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-bold shadow-lg shadow-rose-500/20 flex items-center gap-2">{loading && <Loader2 size={18} className="animate-spin" />}{t('general.save')}</button>
                    </div>
                </form>
            </div>
        </div>
    );
};