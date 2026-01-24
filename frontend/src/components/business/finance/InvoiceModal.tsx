// FILE: src/components/business/finance/InvoiceModal.tsx
import React, { useState, useEffect } from 'react';
import { X, User, FileText, Trash2, Plus, Loader2 } from 'lucide-react';
import { Invoice, InvoiceItem, Case } from '../../../data/types';
import { apiService } from '../../../services/api';
import { useTranslation } from 'react-i18next';

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
                // Reset
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
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="glass-high w-full max-w-2xl max-h-[90vh] overflow-y-auto p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200 custom-finance-scroll">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-white">{editingInvoice ? t('finance.editInvoice') : t('finance.createInvoice')}</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={24} /></button>
                </div>
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-4">
                        <h3 className="text-xs font-bold text-primary-start uppercase tracking-wider flex items-center gap-2 mb-4"><User size={16} /> {t('caseCard.client')}</h3>
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel', "Lënda e Lidhur")}</label>
                            <select value={formData.related_case_id} onChange={e => setFormData({...formData, related_case_id: e.target.value})} className="glass-input w-full px-4 py-2.5 rounded-xl">
                                <option value="">-- {t('finance.noCase', 'Pa Lëndë')} --</option>
                                {cases.map(c => <option key={c.id} value={c.id} className="bg-gray-900">{c.title}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.clientName', 'Emri')}</label>
                            <input required type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.client_name} onChange={e => setFormData({...formData, client_name: e.target.value})} />
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.publicEmail')}</label><input type="email" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.client_email} onChange={e => setFormData({...formData, client_email: e.target.value})} /></div>
                            <div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.phone')}</label><input type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.client_phone} onChange={e => setFormData({...formData, client_phone: e.target.value})} /></div>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.city')}</label><input type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.client_city} onChange={e => setFormData({...formData, client_city: e.target.value})} /></div>
                            <div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.taxId')}</label><input type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.client_tax_id} onChange={e => setFormData({...formData, client_tax_id: e.target.value})} /></div>
                        </div>
                        <div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.address')}</label><input type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={formData.client_address} onChange={e => setFormData({...formData, client_address: e.target.value})} /></div>
                        <div className="flex items-center gap-3 bg-white/5 p-3 rounded-xl border border-white/10">
                            <input type="checkbox" id="vatToggle" checked={includeVat} onChange={(e) => setIncludeVat(e.target.checked)} className="w-4 h-4 text-primary-start rounded border-gray-300 focus:ring-primary-start" />
                            <label htmlFor="vatToggle" className="text-sm text-gray-300 cursor-pointer select-none">Apliko TVSH (18%)</label>
                        </div>
                    </div>
                    
                    <div className="space-y-3 pt-6 border-t border-white/10">
                        <h3 className="text-xs font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><FileText size={16} /> {t('finance.services')}</h3>
                        {lineItems.map((item, index) => (
                            <div key={index} className="flex flex-col sm:flex-row gap-2 items-center">
                                <input type="text" placeholder={t('finance.description')} className="flex-1 w-full glass-input px-3 py-2 rounded-xl" value={item.description} onChange={e => updateLineItem(index, 'description', e.target.value)} required />
                                <input type="number" placeholder={t('finance.qty')} className="w-full sm:w-20 glass-input px-3 py-2 rounded-xl" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', parseFloat(e.target.value))} min="1" />
                                <input type="number" placeholder={t('finance.price')} className="w-full sm:w-24 glass-input px-3 py-2 rounded-xl" value={item.unit_price} onChange={e => updateLineItem(index, 'unit_price', parseFloat(e.target.value))} min="0" />
                                <button type="button" onClick={() => removeLineItem(index)} className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg self-end sm:self-center"><Trash2 size={18} /></button>
                            </div>
                        ))}
                        <button type="button" onClick={addLineItem} className="text-sm text-primary-start hover:underline flex items-center gap-1 font-medium"><Plus size={14} /> {t('finance.addLine')}</button>
                    </div>

                    <div className="flex justify-end gap-3 pt-4">
                        <button type="button" onClick={onClose} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10 transition-colors">{t('general.cancel')}</button>
                        <button type="submit" disabled={loading} className="px-8 py-2.5 bg-gradient-to-r from-success-start to-success-end text-white rounded-xl font-bold shadow-lg shadow-success-start/20 hover:scale-[1.02] transition-transform flex items-center gap-2">
                            {loading && <Loader2 size={18} className="animate-spin"/>}
                            {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};