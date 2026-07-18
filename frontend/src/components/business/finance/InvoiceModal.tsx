// FILE: src/components/business/finance/InvoiceModal.tsx
// PHOENIX PROTOCOL - INVOICE MODAL V6.1 (EXECUTIVE DESIGN SYSTEM)
// 1. FIX: Integrated useLockBodyScroll, applied responsive grid configurations, and standardized contrast selects.
// 2. Buttons use btn-primary for success actions, btn-secondary for cancel.
// 3. Preserved all line calculations, VAT configurations, and database triggers.

import React, { useState, useEffect } from 'react';
import { X, User, FileText, Trash2, Plus, Loader2 } from 'lucide-react';
import { Invoice, InvoiceItem, Case } from '../../../data/types';
import { apiService } from '../../../services/api';
import { useTranslation } from 'react-i18next';
import { useLockBodyScroll } from '../../../hooks/useLockBodyScroll';

interface InvoiceModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: (invoice: Invoice, isUpdate: boolean) => void;
    cases: Case[];
    editingInvoice: Invoice | null;
}

export const InvoiceModal: React.FC<InvoiceModalProps> = ({ isOpen, onClose, onSuccess, cases, editingInvoice }) => {
    const { t } = useTranslation();
    const [loading, setLoading] = useState(false);
    const [includeVat, setIncludeVat] = useState(true);
    const [lineItems, setLineItems] = useState<InvoiceItem[]>([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);
    
    const [formData, setFormData] = useState({ 
        client_name: '', client_email: '', client_phone: '', client_address: '', 
        client_city: '', client_tax_id: '', client_website: '', 
        tax_rate: 18, notes: '', status: 'PAID', related_case_id: '' 
    });

    // Apply viewport body scroll lock dynamically while invoice panel is deployed
    useLockBodyScroll(isOpen);

    useEffect(() => {
        if (isOpen) {
            if (editingInvoice) {
                setFormData({ 
                    client_name: editingInvoice.client_name, 
                    client_email: editingInvoice.client_email || '', 
                    client_address: editingInvoice.client_address || '', 
                    client_phone: (editingInvoice as any).client_phone || '', 
                    client_city: (editingInvoice as any).client_city || '', 
                    client_tax_id: (editingInvoice as any).client_tax_id || '', 
                    client_website: (editingInvoice as any).client_website || '', 
                    tax_rate: editingInvoice.tax_rate, 
                    notes: editingInvoice.notes || '', 
                    status: editingInvoice.status,
                    related_case_id: (editingInvoice as any).related_case_id || '' 
                });
                setIncludeVat(editingInvoice.tax_rate > 0);
                setLineItems(editingInvoice.items);
            } else {
                // Reset form values to default state
                setFormData({ 
                    client_name: '', client_email: '', client_phone: '', client_address: '', 
                    client_city: '', client_tax_id: '', client_website: '', 
                    tax_rate: 18, notes: '', status: 'PAID', related_case_id: '' 
                });
                setIncludeVat(true);
                setLineItems([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);
            }
        }
    }, [isOpen, editingInvoice]);

    useEffect(() => {
        if (!includeVat) {
            setFormData(prev => ({ ...prev, tax_rate: 0 }));
        } else if (formData.tax_rate === 0) {
            setFormData(prev => ({ ...prev, tax_rate: 18 }));
        }
    }, [includeVat]);

    const addLineItem = () => setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0, total: 0 }]);
    const removeLineItem = (i: number) => lineItems.length > 1 && setLineItems(lineItems.filter((_, idx) => idx !== i));
    const updateLineItem = (i: number, f: keyof InvoiceItem, v: any) => { 
        const n = [...lineItems]; 
        n[i] = { ...n[i], [f]: v }; 
        n[i].total = n[i].quantity * n[i].unit_price; 
        setLineItems(n); 
    };

    const truncateText = (text: string, maxLength: number = 32): string => {
        if (!text) return text;
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength - 3) + '...';
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            const payload = { 
                ...formData,
                items: lineItems, 
                tax_rate: includeVat ? formData.tax_rate : 0
            };

            let result;
            if (editingInvoice) {
                result = await apiService.updateInvoice(editingInvoice.id, payload);
                onSuccess(result, true);
            } else {
                result = await apiService.createInvoice(payload);
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto custom-finance-scroll">
            <div className="glass-panel border border-main bg-canvas w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 sm:p-8 rounded-3xl shadow-2xl flex flex-col justify-between animate-in fade-in zoom-in-95 duration-200 custom-finance-scroll">
                
                {/* Header Section with 44px Close Hitbox */}
                <div className="flex justify-between items-center mb-6 shrink-0">
                    <h2 className="text-xl sm:text-2xl font-bold text-text-primary">
                        {editingInvoice ? t('finance.editInvoice') : t('finance.createInvoice')}
                    </h2>
                    <button 
                        onClick={onClose} 
                        className="flex items-center justify-center w-11 h-11 rounded-xl text-text-muted hover:text-text-primary hover:bg-hover transition-colors focus:outline-none"
                        aria-label="Close form"
                    >
                        <X size={22} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="flex-grow space-y-6">
                    
                    {/* Section 1: Client Metadata Details */}
                    <div className="space-y-4">
                        <h3 className="text-xs font-bold text-primary-start uppercase tracking-wider flex items-center gap-2 mb-2 select-none">
                            <User size={15} /> {t('caseCard.client')}
                        </h3>
                        
                        {/* Input: Case Linkage Select with Truncation & High Contrast Options */}
                        <div className="space-y-1.5">
                            <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('drafting.selectCaseLabel', "Lënda e Lidhur")}</label>
                            <div className="relative">
                                <select 
                                    value={formData.related_case_id} 
                                    onChange={e => setFormData({...formData, related_case_id: e.target.value})} 
                                    className="w-full pl-4 pr-10 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start appearance-none truncate transition-all"
                                >
                                    <option value="" className="bg-canvas text-text-primary">-- {t('finance.noCase', 'Pa Lëndë')} --</option>
                                    {cases.map(c => (
                                        <option key={c.id} value={c.id} className="bg-canvas text-text-primary" title={c.title}>
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
                        </div>

                        {/* Input: Client Name */}
                        <div className="space-y-1.5">
                            <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('business.clientName', 'Emri')}</label>
                            <input 
                                required 
                                type="text" 
                                className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                value={formData.client_name} 
                                onChange={e => setFormData({...formData, client_name: e.target.value})} 
                            />
                        </div>

                        {/* Grid Panel: Contact Metadata (Email & Phone) */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('business.publicEmail')}</label>
                                <input 
                                    type="email" 
                                    className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                    value={formData.client_email} 
                                    onChange={e => setFormData({...formData, client_email: e.target.value})} 
                                />
                            </div>
                            <div className="space-y-1.5">
                                <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('business.phone')}</label>
                                <input 
                                    type="text" 
                                    className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                    value={formData.client_phone} 
                                    onChange={e => setFormData({...formData, client_phone: e.target.value})} 
                                />
                            </div>
                        </div>

                        {/* Grid Panel: City & Tax Identifier */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="space-y-1.5">
                                <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('business.city')}</label>
                                <input 
                                    type="text" 
                                    className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                    value={formData.client_city} 
                                    onChange={e => setFormData({...formData, client_city: e.target.value})} 
                                />
                            </div>
                            <div className="space-y-1.5">
                                <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('business.taxId')}</label>
                                <input 
                                    type="text" 
                                    className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                    value={formData.client_tax_id} 
                                    onChange={e => setFormData({...formData, client_tax_id: e.target.value})} 
                                />
                            </div>
                        </div>

                        {/* Input: Detailed Address */}
                        <div className="space-y-1.5">
                            <label className="block text-xs text-text-secondary font-bold uppercase tracking-wider">{t('business.address')}</label>
                            <input 
                                type="text" 
                                className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                value={formData.client_address} 
                                onChange={e => setFormData({...formData, client_address: e.target.value})} 
                            />
                        </div>

                        {/* Vat Toggle Checkbox Box with 44px target parameters */}
                        <div className="flex items-center gap-3 bg-surface border border-main p-3.5 rounded-xl">
                            <input 
                                type="checkbox" 
                                id="vatToggle" 
                                checked={includeVat} 
                                onChange={(e) => setIncludeVat(e.target.checked)} 
                                className="w-4 h-4 text-primary-start rounded border-main bg-canvas focus:ring-primary-start" 
                            />
                            <label htmlFor="vatToggle" className="text-sm font-semibold text-text-secondary cursor-pointer select-none">
                                Apliko TVSH (18%)
                            </label>
                        </div>
                    </div>
                    
                    {/* Section 2: Services / Line Items Array */}
                    <div className="space-y-3 pt-6 border-t border-main">
                        <h3 className="text-xs font-bold text-primary-start uppercase tracking-wider flex items-center gap-2 mb-1 select-none">
                            <FileText size={15} /> {t('finance.services')}
                        </h3>
                        
                        <div className="space-y-3">
                            {lineItems.map((item, index) => (
                                <div key={index} className="flex flex-col sm:flex-row gap-3 items-center bg-surface/30 sm:bg-transparent p-3 sm:p-0 rounded-xl border border-main sm:border-transparent">
                                    <div className="w-full sm:flex-1">
                                        <input 
                                            type="text" 
                                            placeholder={t('finance.description')} 
                                            className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                            value={item.description} 
                                            onChange={e => updateLineItem(index, 'description', e.target.value)} 
                                            required 
                                        />
                                    </div>
                                    <div className="w-full sm:w-20">
                                        <input 
                                            type="number" 
                                            placeholder={t('finance.qty')} 
                                            className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                            value={item.quantity} 
                                            onChange={e => updateLineItem(index, 'quantity', parseFloat(e.target.value) || 0)} 
                                            min="1" 
                                        />
                                    </div>
                                    <div className="w-full sm:w-28">
                                        <input 
                                            type="number" 
                                            placeholder={t('finance.price')} 
                                            className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all" 
                                            value={item.unit_price} 
                                            onChange={e => updateLineItem(index, 'unit_price', parseFloat(e.target.value) || 0)} 
                                            min="0" 
                                        />
                                    </div>
                                    <div className="flex justify-end w-full sm:w-auto">
                                        <button 
                                            type="button" 
                                            onClick={() => removeLineItem(index)} 
                                            disabled={lineItems.length <= 1}
                                            className="flex items-center justify-center w-11 h-11 text-danger-start hover:bg-danger-start/10 hover:border-danger-start/20 border border-transparent disabled:opacity-40 rounded-xl transition-all focus:outline-none"
                                            title="Delete Row"
                                            aria-label="Remove item"
                                        >
                                            <Trash2 size={18} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Add Line Target Trigger */}
                        <button 
                            type="button" 
                            onClick={addLineItem} 
                            className="inline-flex items-center gap-1.5 h-10 px-3 text-sm text-primary-start hover:bg-hover rounded-lg font-semibold transition-colors focus:outline-none"
                        >
                            <Plus size={14} /> {t('finance.addLine')}
                        </button>
                    </div>

                    {/* Action Controls Frame with 44px Tap targets */}
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
                            className="w-full sm:w-auto px-8 h-11 rounded-xl text-sm font-bold bg-primary-start text-white shadow-lg shadow-primary-start/15 hover:shadow-primary-start/25 hover:scale-[1.01] transition-all flex items-center justify-center gap-2 focus:outline-none"
                        >
                            {loading && <Loader2 size={16} className="animate-spin"/>}
                            {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};