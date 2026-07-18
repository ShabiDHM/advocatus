// FILE: src/components/business/finance/ExpenseModal.tsx
// PHOENIX PROTOCOL - EXPENSE MODAL V6.2 (EXECUTIVE DESIGN SYSTEM)
// 1. FIX: Updated scanInputRef to accept="image/*,.pdf" to allow PDF invoices to be selectable during AI OCR scans.
// 2. POLISH: Integrated background scroll locks, high-contrast inputs, touch target sizing, and responsive layouts.

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { X, MinusCircle, ChevronLeft, Loader2, CheckCircle, Paperclip, Sparkles, ScanLine, AlertCircle, Lock } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Expense, Case } from '../../../data/types';
import { apiService } from '../../../services/api';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../../context/AuthContext';
import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { sq, enUS } from 'date-fns/locale';
import { useLockBodyScroll } from '../../../hooks/useLockBodyScroll';

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
    const { user } = useAuth();
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

    // Apply viewport body scroll restriction dynamically while modal is active
    useLockBodyScroll(isOpen);

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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto custom-finance-scroll">
            <div className="glass-panel border border-main bg-canvas w-full max-w-lg max-h-[90vh] overflow-y-auto custom-finance-scroll p-6 sm:p-8 rounded-3xl shadow-2xl flex flex-col justify-between animate-in fade-in zoom-in-95 duration-200">
                
                {/* Header Title with 44px Close Hitbox */}
                <div className="flex justify-between items-center mb-6 shrink-0">
                    <h2 className="text-lg sm:text-xl font-bold text-text-primary flex items-center gap-2">
                        <MinusCircle size={20} className="text-danger-start" /> 
                        {editingExpense ? t('finance.editExpense') : t('finance.addExpense')}
                    </h2>
                    <button 
                        onClick={onClose} 
                        className="flex items-center justify-center w-11 h-11 rounded-xl text-text-muted hover:text-text-primary hover:bg-hover transition-colors focus:outline-none"
                        aria-label="Close form"
                    >
                        <X size={22} />
                    </button>
                </div>

                {/* Scan input parameters */}
                <input type="file" ref={scanInputRef} className="hidden" accept="image/*,.pdf" capture="environment" onChange={handleFileSelection} />
                <input type="file" ref={attachInputRef} className="hidden" accept="image/*,.pdf" onChange={handleFileSelection} />

                {/* OCR scanning components */}
                <div className="mb-6 shrink-0">
                    <AnimatePresence mode="wait">
                        {!isDirectUpload && !expenseReceipt ? (
                            <motion.div key="initial" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                                <label className="block text-xs text-text-secondary mb-1.5 font-bold uppercase tracking-wider">{t('finance.receipt', 'Fatura')}</label>
                                
                                <div className="grid grid-cols-2 gap-3">
                                    {/* Option 1: AI Scan */}
                                    <button 
                                        type="button" 
                                        onClick={() => triggerUpload('scan')} 
                                        disabled={!isPro}
                                        className={`py-5 border border-dashed rounded-xl flex flex-col items-center justify-center gap-3 transition-all group relative overflow-hidden focus:outline-none
                                        ${!isPro 
                                            ? 'border-main bg-surface/30 cursor-not-allowed opacity-70' 
                                            : 'border-danger-start/30 bg-danger-start/5 text-danger-start hover:bg-danger-start/10 hover:border-danger-start/50'
                                        }`}
                                        style={{ minHeight: '110px' }}
                                    >
                                        {!isPro && (
                                            <div className="absolute inset-0 flex items-center justify-center bg-black/40 z-10">
                                                <Lock size={20} className="text-text-primary" />
                                            </div>
                                        )}
                                        <div className={`p-2.5 rounded-full transition-transform ${isPro ? 'bg-danger-start/10 group-hover:scale-110' : 'bg-surface/30'}`}>
                                            <ScanLine size={20} className={isPro ? "text-danger-start" : "text-text-muted"} />
                                        </div>
                                        <div className="text-center px-1">
                                            <span className={`block text-xs font-bold ${isPro ? "text-text-primary" : "text-text-secondary"}`}>{t('finance.scanAI', 'Skano me AI')}</span>
                                            <span className="text-[9px] text-text-muted block mt-0.5">OCR & Auto-Fill</span>
                                        </div>
                                    </button>

                                    {/* Option 2: Simple Attach */}
                                    <button 
                                        type="button" 
                                        onClick={() => triggerUpload('attach')} 
                                        className="py-5 border border-dashed border-main bg-surface/10 rounded-xl flex flex-col items-center justify-center gap-3 text-text-secondary hover:bg-hover hover:text-text-primary hover:border-primary-start/30 transition-all group focus:outline-none"
                                        style={{ minHeight: '110px' }}
                                    >
                                        <div className="p-2.5 bg-hover rounded-full group-hover:scale-110 transition-transform">
                                            <Paperclip size={20} />
                                        </div>
                                        <div className="text-center px-1">
                                            <span className="block text-xs font-bold">{t('finance.attachOnly', 'Bashkangjit')}</span>
                                            <span className="text-[9px] text-text-muted block mt-0.5">PDF, JPG, PNG</span>
                                        </div>
                                    </button>
                                </div>
                            </motion.div>
                        ) : (
                            <motion.div key="direct" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}>
                                <div className="flex justify-between items-center mb-2">
                                    <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('finance.uploadDirectly', 'Ngarko Skedar')}</label>
                                    <button 
                                        type="button" 
                                        onClick={() => { setIsDirectUpload(false); setExpenseReceipt(null); setScanError(null); }} 
                                        className="text-xs flex items-center gap-1 text-text-muted hover:text-text-primary h-9 px-2 rounded-lg hover:bg-hover focus:outline-none"
                                    > 
                                        <ChevronLeft size={14} /> {t('general.back', 'Kthehu')} 
                                    </button>
                                </div>

                                <button
                                    type="button"
                                    onClick={() => triggerUpload(uploadIntent.current)}
                                    disabled={isScanningReceipt}
                                    className={`w-full h-11 border border-dashed rounded-xl flex items-center justify-center gap-2 transition-all text-sm font-medium focus:outline-none
                                    ${expenseReceipt ? 'bg-primary-start/10 border-primary-start text-primary-start' : 'bg-surface border-main text-text-secondary hover:bg-hover'}
                                    ${isScanningReceipt ? 'cursor-wait opacity-80' : ''}`}
                                >
                                    {isScanningReceipt ? (
                                        <><Loader2 size={16} className="animate-spin text-primary-start" /> {t('finance.scanning', 'Analizimi me AI...')}</>
                                    ) : expenseReceipt ? (
                                        <><CheckCircle size={16} className="text-status-success" />
                                            <span className="max-w-[200px] truncate" title={expenseReceipt.name}>
                                                {expenseReceipt.name}
                                            </span>
                                        </>
                                    ) : (
                                        <><Paperclip size={16} /> {t('finance.changeFile', 'Ndrysho Skedarin')}</>
                                    )}
                                </button>
                                
                                {isScanningReceipt && <p className="text-center text-[10px] text-text-muted mt-2 flex items-center justify-center gap-1"><Sparkles size={10} className="text-primary-start" /> {t('finance.extractingData', 'Duke nxjerrë të dhënat...')}</p>}
                                
                                {scanError && (
                                    <motion.div initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} className="mt-2 p-3 bg-danger-start/15 border border-danger-start/20 rounded-xl flex items-center gap-2 text-danger-start text-xs">
                                        <AlertCircle size={14} className="shrink-0" />
                                        <span>{scanError}</span>
                                    </motion.div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Form Elements */}
                <form onSubmit={handleSubmit} className="flex-1 space-y-4">
                    {/* Input: Case Selection - Truncated option labels and high-contrast options */}
                    <div className="space-y-1.5">
                        <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('drafting.selectCaseLabel', "Lënda e Lidhur")}</label>
                        <div className="relative">
                            <select
                                value={formData.related_case_id}
                                onChange={(e) => setFormData({ ...formData, related_case_id: e.target.value })}
                                className="w-full pl-4 pr-10 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start appearance-none truncate transition-all"
                            >
                                <option value="" className="bg-canvas text-text-primary">
                                    -- {t('finance.noCase', 'Pa Lëndë')} --
                                </option>
                                {cases.map(c => (
                                    <option 
                                        key={c.id} 
                                        value={c.id} 
                                        className="bg-canvas text-text-primary" 
                                        title={c.title}
                                    >
                                        {truncateText(c.title)}
                                    </option>
                                ))}
                            </select>
                            <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-text-muted">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </div>
                        </div>
                        {!formData.related_case_id && (
                            <p className="text-[10px] text-text-muted flex items-center gap-1">
                                {t('finance.generalUpload', 'Pa lëndë: Do të regjistrohet si shpenzim i përgjithshëm.')}
                            </p>
                        )}
                    </div>

                    {/* Input: Category */}
                    <div className="space-y-1.5">
                        <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('finance.expenseCategory')}</label>
                        <input 
                            required 
                            type="text" 
                            className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                            maxLength={50} 
                            value={formData.category} 
                            onChange={(e) => setFormData({ ...formData, category: e.target.value })} 
                        />
                    </div>

                    {/* Responsive Grid Panel: Amount & Processing Date */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('finance.amount')}</label>
                            <input 
                                required 
                                type="number" 
                                step="0.01" 
                                className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                value={formData.amount} 
                                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })} 
                            />
                        </div>

                        <div className="space-y-1.5 flex flex-col justify-end">
                            <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('finance.date')}</label>
                            <div className="relative w-full">
                                <DatePicker 
                                    selected={expenseDate} 
                                    onChange={(date: Date | null) => setExpenseDate(date)} 
                                    locale={currentLocale} 
                                    dateFormat="dd/MM/yyyy" 
                                    className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                    required 
                                />
                            </div>
                        </div>
                    </div>

                    {/* Input: Notes/Description */}
                    <div className="space-y-1.5">
                        <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('finance.description')}</label>
                        <textarea 
                            rows={2} 
                            className="w-full p-4 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all resize-none" 
                            maxLength={200} 
                            value={formData.description} 
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })} 
                        />
                    </div>

                    {/* Form Action Controls with 44px Minimum heights */}
                    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-4 border-t border-main">
                        <button 
                            type="button" 
                            onClick={onClose} 
                            className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-all focus:outline-none"
                        >
                            {t('general.cancel')}
                        </button>
                        <button 
                            type="submit" 
                            disabled={loading} 
                            className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-semibold bg-danger-start hover:bg-opacity-90 text-white shadow-lg shadow-danger-start/15 hover:shadow-danger-start/20 transition-all flex items-center justify-center gap-2 focus:outline-none"
                        >
                            {loading && <Loader2 size={16} className="animate-spin" />}
                            {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};