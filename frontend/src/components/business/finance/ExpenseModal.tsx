// FILE: src/components/business/finance/ExpenseModal.tsx
// PHOENIX PROTOCOL - EXPENSE MODAL V2.8 (SPLIT UPLOAD ACTIONS)
// 1. ADDED: Split buttons for "AI Scan" vs "Simple Attach"
// 2. LOGIC: uploadIntent ref determines if OCR runs
// 3. UI: 2-column grid for upload actions

import React, { useState, useRef, useEffect } from 'react';
import { X, MinusCircle, ChevronLeft, Loader2, CheckCircle, Paperclip, Sparkles, ScanLine } from 'lucide-react';
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

export const ExpenseModal: React.FC<ExpenseModalProps> = ({ isOpen, onClose, onSuccess, cases, editingExpense }) => {
    const { t, i18n } = useTranslation();
    const [isDirectUpload, setIsDirectUpload] = useState(false);
    const [isScanningReceipt, setIsScanningReceipt] = useState(false);
    const [expenseReceipt, setExpenseReceipt] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    
    // Track intent: 'scan' (AI) or 'attach' (Manual)
    const uploadIntent = useRef<'scan' | 'attach'>('scan');

    const [loading, setLoading] = useState(false);
    const [expenseDate, setExpenseDate] = useState<Date | null>(new Date());
    const [formData, setFormData] = useState({ category: '', amount: 0, description: '', related_case_id: '' });

    const localeMap: { [key: string]: any } = { sq, al: sq, en: enUS };
    const currentLocale = localeMap[i18n.language] || enUS;

    const truncateText = (text: string, maxLength: number = 30): string => {
        if (!text) return text;
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    };

    useEffect(() => {
        if (isOpen) {
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

    const handleFileSelection = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setIsDirectUpload(true);
            setExpenseReceipt(file);
            
            // Only trigger AI if the intent was specifically 'scan'
            if (uploadIntent.current === 'scan' && !editingExpense) {
                handleAiScan(file);
            }
        }
    };

    const handleAiScan = async (file: File) => {
        setIsScanningReceipt(true);
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
        } finally {
            setIsScanningReceipt(false);
        }
    };

    const triggerUpload = (mode: 'scan' | 'attach') => {
        uploadIntent.current = mode;
        fileInputRef.current?.click();
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
        } catch (error) {
            console.error('Receipt analysis failed:', error);
            throw error;
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const payload = {
                ...formData,
                date: DateTimeProtocol.safeDateToString(expenseDate)
            };

            let result: Expense;
            if (editingExpense) {
                result = await apiService.updateExpense(editingExpense.id, payload);
                if (expenseReceipt && result.id) {
                    await apiService.uploadExpenseReceipt(result.id, expenseReceipt);
                }
                onSuccess(result, true);
            } else {
                result = await apiService.createExpense(payload);
                if (expenseReceipt && result.id) {
                    await apiService.uploadExpenseReceipt(result.id, expenseReceipt);
                }
                onSuccess(result, false);
            }
            onClose();
        } catch (error) {
            console.error(error);
            alert(t('error.generic'));
        } finally {
            setLoading(false);
        }
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

                {/* Hidden Input */}
                <input type="file" ref={fileInputRef} className="hidden" accept="image/*,.pdf" onChange={handleFileSelection} />

                <div className="mb-6">
                    <AnimatePresence mode="wait">
                        {!isDirectUpload && !expenseReceipt ? (
                            <motion.div key="initial" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-3">
                                <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.receipt', 'Fatura')}</label>
                                
                                <div className="grid grid-cols-2 gap-3">
                                    {/* Option 1: AI Scan */}
                                    <button 
                                        type="button" 
                                        onClick={() => triggerUpload('scan')} 
                                        className="py-6 border border-dashed border-rose-500/30 bg-rose-500/5 rounded-xl flex flex-col items-center justify-center gap-3 text-rose-300 hover:bg-rose-500/10 hover:border-rose-500/50 transition-all group"
                                    >
                                        <div className="p-3 bg-rose-500/10 rounded-full group-hover:scale-110 transition-transform">
                                            <ScanLine size={24} />
                                        </div>
                                        <div className="text-center px-2">
                                            <span className="block text-sm font-bold">{t('finance.scanAI', 'Skano me AI')}</span>
                                            <span className="text-[9px] opacity-60 block mt-1">OCR & Auto-Fill</span>
                                        </div>
                                    </button>

                                    {/* Option 2: Simple Attach */}
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
                                    <button type="button" onClick={() => { setIsDirectUpload(false); setExpenseReceipt(null); }} className="text-xs flex items-center gap-1 text-gray-400 hover:text-white"> <ChevronLeft size={14} /> {t('general.back', 'Kthehu')} </button>
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
                            style={{
                                maxWidth: '100%',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                            }}
                        >
                            <option value="" className="bg-gray-900 truncate">
                                -- {t('finance.noCase', 'Pa Lëndë')} --
                            </option>
                            {cases.map(c => (
                                <option
                                    key={c.id}
                                    value={c.id}
                                    className="bg-gray-900 truncate"
                                    title={c.title}
                                >
                                    {truncateText(c.title)}
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
                            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                        />
                    </div>
                    <div>
                        <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.amount')}</label>
                        <input required type="number" step="0.01" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) })} />
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
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        />
                    </div>
                    <div className="flex justify-end gap-3 pt-4">
                        <button type="button" onClick={onClose} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10 transition-colors">{t('general.cancel')}</button>
                        <button type="submit" disabled={loading} className="px-8 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-bold shadow-lg shadow-rose-500/20 flex items-center gap-2">
                            {loading && <Loader2 size={18} className="animate-spin" />}
                            {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};