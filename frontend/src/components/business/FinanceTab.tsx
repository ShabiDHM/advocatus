// FILE: src/components/business/FinanceTab.tsx
import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { 
    TrendingUp, TrendingDown, Wallet, Calculator, MinusCircle, Plus, FileText, 
    Edit2, Eye, Download, Archive, Trash2, CheckCircle, Paperclip, X, User, Activity, Loader2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiService, Expense, ExpenseCreateRequest } from '../../services/api';
import { Invoice, InvoiceItem, Case, Document } from '../../data/types';
import { useTranslation } from 'react-i18next';
import PDFViewerModal from '../PDFViewerModal';
import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { sq, enUS } from 'date-fns/locale';

const DatePicker = (ReactDatePicker as any).default;

const FinanceCard = ({ title, amount, icon, color, subtext }: { title: string, amount: string, icon: React.ReactNode, color: string, subtext?: string }) => (
    <div className="group relative overflow-hidden rounded-2xl bg-gray-900/40 backdrop-blur-md border border-white/5 p-6 hover:bg-gray-800/60 transition-all duration-300 hover:-translate-y-1 shadow-lg">
        <div className={`absolute top-0 left-0 w-1 h-full ${color}`} />
        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110">{icon}</div>
        <div className="relative z-10">
            <div className="flex items-center gap-3 mb-4"><div className={`p-2.5 rounded-xl bg-white/5 border border-white/10 ${color.replace('bg-', 'text-')}`}>{icon}</div><h3 className="text-gray-400 text-sm font-medium uppercase tracking-wider">{title}</h3></div>
            <p className="text-2xl sm:text-3xl font-bold text-white tracking-tight">{amount}</p>
            {subtext && <p className="text-xs text-gray-500 mt-2 font-mono">{subtext}</p>}
        </div>
    </div>
);

export const FinanceTab: React.FC = () => {
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const localeMap: { [key: string]: any } = { sq, al: sq, en: enUS };
    const currentLocale = localeMap[i18n.language] || enUS;

    const [loading, setLoading] = useState(true);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [cases, setCases] = useState<Case[]>([]);

    const [showInvoiceModal, setShowInvoiceModal] = useState(false);
    const [showExpenseModal, setShowExpenseModal] = useState(false);
    const [showArchiveInvoiceModal, setShowArchiveInvoiceModal] = useState(false);
    const [showArchiveExpenseModal, setShowArchiveExpenseModal] = useState(false);
    
    // Selection / Edit States
    const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
    const [selectedExpenseId, setSelectedExpenseId] = useState<string | null>(null);
    const [selectedCaseForInvoice, setSelectedCaseForInvoice] = useState<string>("");
    const [editingInvoiceId, setEditingInvoiceId] = useState<string | null>(null);
    const [editingExpenseId, setEditingExpenseId] = useState<string | null>(null);

    // Document Viewing
    const [openingDocId, setOpeningDocId] = useState<string | null>(null);
    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [viewingUrl, setViewingUrl] = useState<string | null>(null);

    // Form States
    const [newInvoice, setNewInvoice] = useState({ client_name: '', client_email: '', client_phone: '', client_address: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: 18, notes: '', status: 'DRAFT' });
    const [lineItems, setLineItems] = useState<InvoiceItem[]>([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);
    const [newExpense, setNewExpense] = useState<ExpenseCreateRequest>({ category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0] });
    const [expenseDate, setExpenseDate] = useState<Date | null>(new Date());
    const [expenseReceipt, setExpenseReceipt] = useState<File | null>(null);
    const receiptInputRef = useRef<HTMLInputElement>(null);

    const totalIncome = invoices.reduce((sum, inv) => sum + inv.total_amount, 0);
    const totalExpenses = expenses.reduce((sum, exp) => sum + exp.amount, 0);
    const totalBalance = totalIncome - totalExpenses;

    useEffect(() => {
        const loadData = async () => {
            try {
                const [inv, exp, cs] = await Promise.all([
                    apiService.getInvoices().catch(() => []),
                    apiService.getExpenses().catch(() => []),
                    apiService.getCases().catch(() => [])
                ]);
                setInvoices(inv); setExpenses(exp); setCases(cs);
            } catch (e) { console.error(e); } finally { setLoading(false); }
        };
        loadData();
    }, []);

    // --- HANDLERS ---
    const closePreview = () => { if (viewingUrl) window.URL.revokeObjectURL(viewingUrl); setViewingUrl(null); setViewingDoc(null); };
    const addLineItem = () => setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0, total: 0 }]);
    const removeLineItem = (i: number) => lineItems.length > 1 && setLineItems(lineItems.filter((_, idx) => idx !== i));
    const updateLineItem = (i: number, f: keyof InvoiceItem, v: any) => { const n = [...lineItems]; n[i] = { ...n[i], [f]: v }; n[i].total = n[i].quantity * n[i].unit_price; setLineItems(n); };
    
    const handleEditInvoice = (invoice: Invoice) => { setEditingInvoiceId(invoice.id); setNewInvoice({ client_name: invoice.client_name, client_email: invoice.client_email || '', client_address: invoice.client_address || '', client_phone: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: invoice.tax_rate, notes: invoice.notes || '', status: invoice.status }); setLineItems(invoice.items); setShowInvoiceModal(true); };
    const handleCreateOrUpdateInvoice = async (e: React.FormEvent) => { e.preventDefault(); try { const fullAddress = [newInvoice.client_address, newInvoice.client_city, newInvoice.client_phone ? `Tel: ${newInvoice.client_phone}` : '', newInvoice.client_tax_id ? `NUI: ${newInvoice.client_tax_id}` : '', newInvoice.client_website].filter(Boolean).join('\n'); const payload = { client_name: newInvoice.client_name, client_email: newInvoice.client_email, client_address: fullAddress, items: lineItems, tax_rate: newInvoice.tax_rate, notes: newInvoice.notes, status: newInvoice.status }; if (editingInvoiceId) { const u = await apiService.updateInvoice(editingInvoiceId, payload); setInvoices(invoices.map(i => i.id === editingInvoiceId ? u : i)); } else { const n = await apiService.createInvoice(payload); setInvoices([n, ...invoices]); } closeInvoiceModal(); } catch { alert(t('error.generic')); } };
    const closeInvoiceModal = () => { setShowInvoiceModal(false); setEditingInvoiceId(null); setNewInvoice({ client_name: '', client_email: '', client_phone: '', client_address: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: 18, notes: '', status: 'DRAFT' }); setLineItems([{ description: '', quantity: 1, unit_price: 0, total: 0 }]); };
    const deleteInvoice = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteInvoice(id); setInvoices(invoices.filter(inv => inv.id !== id)); } catch { alert(t('documentsPanel.deleteFailed')); } };
    const handleViewInvoice = async (invoice: Invoice) => { setOpeningDocId(invoice.id); try { const blob = await apiService.getInvoicePdfBlob(invoice.id, i18n.language); const url = window.URL.createObjectURL(blob); setViewingUrl(url); setViewingDoc({ id: invoice.id, file_name: `Invoice #${invoice.invoice_number}`, mime_type: 'application/pdf', status: 'READY' } as any); } catch { alert(t('error.generic')); } finally { setOpeningDocId(null); } };
    const downloadInvoice = async (id: string) => { try { await apiService.downloadInvoicePdf(id, i18n.language); } catch { alert(t('error.generic')); } };
    const handleArchiveInvoiceClick = (id: string) => { setSelectedInvoiceId(id); setShowArchiveInvoiceModal(true); };
    const submitArchiveInvoice = async () => { if (!selectedInvoiceId) return; try { await apiService.archiveInvoice(selectedInvoiceId, selectedCaseForInvoice || undefined); alert(t('general.saveSuccess')); setShowArchiveInvoiceModal(false); setSelectedCaseForInvoice(""); } catch { alert(t('error.generic')); } };

    const handleEditExpense = (expense: Expense) => { setEditingExpenseId(expense.id); setNewExpense({ category: expense.category, amount: expense.amount, description: expense.description || '', date: expense.date }); setExpenseDate(new Date(expense.date)); setShowExpenseModal(true); };
    const handleCreateOrUpdateExpense = async (e: React.FormEvent) => { e.preventDefault(); try { const payload = { ...newExpense, date: expenseDate ? expenseDate.toISOString().split('T')[0] : new Date().toISOString().split('T')[0] }; let s: Expense; if (editingExpenseId) { s = await apiService.updateExpense(editingExpenseId, payload); setExpenses(expenses.map(e => e.id === editingExpenseId ? s : e)); } else { s = await apiService.createExpense(payload); setExpenses([s, ...expenses]); } if (expenseReceipt && s.id) { await apiService.uploadExpenseReceipt(s.id, expenseReceipt); const f = { ...s, receipt_url: "PENDING_REFRESH" }; setExpenses(prev => prev.map(e => e.id === f.id ? f : e)); } setShowExpenseModal(false); setEditingExpenseId(null); setNewExpense({ category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0] }); setExpenseReceipt(null); } catch { alert(t('error.generic')); } };
    const closeExpenseModal = () => { setShowExpenseModal(false); setEditingExpenseId(null); setNewExpense({ category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0] }); setExpenseReceipt(null); };
    const deleteExpense = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteExpense(id); setExpenses(expenses.filter(e => e.id !== id)); } catch { alert(t('error.generic')); } };
    const handleViewExpense = async (expense: Expense) => { if (!expense.receipt_url) { alert(t('error.noReceiptAttached')); return; } setOpeningDocId(expense.id); try { const { blob, filename } = await apiService.getExpenseReceiptBlob(expense.id); const url = window.URL.createObjectURL(blob); const ext = filename.split('.').pop()?.toLowerCase(); const mime = ext === 'pdf' ? 'application/pdf' : 'image/jpeg'; setViewingUrl(url); setViewingDoc({ id: expense.id, file_name: filename, mime_type: mime, status: 'READY' } as any); } catch { alert(t('error.receiptNotFound')); } finally { setOpeningDocId(null); } };
    const handleDownloadExpense = async (expense: Expense) => { if (!expense.receipt_url) { alert(t('error.noReceiptAttached')); return; } try { const { blob, filename } = await apiService.getExpenseReceiptBlob(expense.id); const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); document.body.removeChild(a); } catch { alert(t('error.generic')); } };
    const handleArchiveExpenseClick = (id: string) => { const ex = expenses.find(e => e.id === id); if (!ex || !ex.receipt_url) { alert(t('error.noReceiptToArchive')); return; } setSelectedExpenseId(id); setShowArchiveExpenseModal(true); };
    const submitArchiveExpense = async () => { if (!selectedExpenseId) return; try { const ex = expenses.find(e => e.id === selectedExpenseId); if (!ex || !ex.receipt_url) return; const { blob, filename } = await apiService.getExpenseReceiptBlob(ex.id); const f = new File([blob], filename, { type: blob.type }); await apiService.uploadArchiveItem(f, filename, "EXPENSE", selectedCaseForInvoice || undefined, undefined); alert(t('general.saveSuccess')); setShowArchiveExpenseModal(false); setSelectedCaseForInvoice(""); } catch { alert(t('error.generic')); } };

    if (loading) return <div className="flex justify-center h-64 items-center"><Loader2 className="animate-spin text-primary-start" /></div>;

    return (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-8">
            <style>{`.custom-finance-scroll::-webkit-scrollbar { width: 6px; } .custom-finance-scroll::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); } .custom-finance-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 10px; }`}</style>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <FinanceCard title={t('finance.income')} amount={`€${totalIncome.toFixed(2)}`} icon={<TrendingUp className="w-6 h-6" />} color="bg-emerald-500" subtext={t('finance.incomeSub')} />
                <FinanceCard title={t('finance.expense')} amount={`€${totalExpenses.toFixed(2)}`} icon={<TrendingDown className="w-6 h-6" />} color="bg-rose-500" subtext={t('finance.expenseSub')} />
                <FinanceCard title={t('finance.balance')} amount={`€${totalBalance.toFixed(2)}`} icon={<Wallet className="w-6 h-6" />} color="bg-blue-500" subtext={t('finance.balanceSub')} />
            </div>
            
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <h2 className="text-2xl font-bold text-white">{t('finance.invoicesTitle')}</h2>
                <div className="flex gap-3 w-full sm:w-auto flex-wrap justify-end">
                    <button onClick={() => navigate('/finance/wizard')} className="flex-1 sm:flex-none justify-center flex items-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-lg transition-all font-medium whitespace-nowrap"><Calculator size={20} /> <span>{t('finance.monthlyClose')}</span></button>
                    <button onClick={() => setShowExpenseModal(true)} className="flex-1 sm:flex-none justify-center flex items-center gap-2 px-4 py-3 bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-lg transition-all font-medium whitespace-nowrap"><MinusCircle size={20} /> <span>{t('finance.addExpense')}</span></button>
                    <button onClick={() => setShowInvoiceModal(true)} className="flex-1 sm:flex-none justify-center flex items-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-lg transition-all font-medium whitespace-nowrap"><Plus size={20} /> <span>{t('finance.createInvoice')}</span></button>
                </div>
            </div>

            {/* PHOENIX FIX: FIXED HEIGHT SCROLLABLE CONTAINER */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* INVOICES LIST */}
                <div className="bg-background-dark/50 border border-glass-edge rounded-3xl p-1">
                    <div className="max-h-[500px] overflow-y-auto custom-finance-scroll p-4 space-y-4">
                        <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider sticky top-0 bg-background-dark/95 backdrop-blur z-10 py-2 border-b border-white/5 mb-2">{t('finance.recentInvoices', 'Recent Invoices')}</h3>
                        {invoices.length === 0 ? <p className="text-gray-500 italic text-sm text-center py-10">{t('finance.noInvoices')}</p> : invoices.map(inv => (
                            <div key={inv.id} className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-3 hover:bg-white/10 transition-colors">
                                <div className="flex justify-between items-start">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className={`p-2 rounded-lg flex-shrink-0 ${inv.status === 'PAID' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}><FileText size={20} /></div>
                                        <div className="min-w-0"><h4 className="font-bold text-white text-sm truncate">{inv.client_name}</h4><p className="text-xs text-gray-400 font-mono">#{inv.invoice_number}</p></div>
                                    </div>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase flex-shrink-0 ${inv.status === 'PAID' ? 'bg-emerald-900/30 text-emerald-400' : 'bg-amber-900/30 text-amber-400'}`}>{inv.status}</span>
                                </div>
                                <div className="flex justify-between items-center border-t border-white/5 pt-3">
                                    <p className="font-bold text-white">€{inv.total_amount.toFixed(2)}</p>
                                    <div className="flex gap-1">
                                        <button onClick={() => handleEditInvoice(inv)} className="p-1.5 hover:bg-white/10 rounded-lg text-amber-400"><Edit2 size={16} /></button>
                                        <button onClick={() => handleViewInvoice(inv)} className="p-1.5 hover:bg-white/10 rounded-lg text-blue-400">{openingDocId === inv.id ? <Loader2 className="animate-spin w-4 h-4" /> : <Eye size={16} />}</button>
                                        <button onClick={() => downloadInvoice(inv.id)} className="p-1.5 hover:bg-white/10 rounded-lg text-green-400"><Download size={16} /></button>
                                        <button onClick={() => handleArchiveInvoiceClick(inv.id)} className="p-1.5 hover:bg-white/10 rounded-lg text-indigo-400"><Archive size={16} /></button>
                                        <button onClick={() => deleteInvoice(inv.id)} className="p-1.5 hover:bg-white/10 rounded-lg text-red-400"><Trash2 size={16} /></button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* EXPENSES LIST */}
                <div className="bg-background-dark/50 border border-glass-edge rounded-3xl p-1">
                     <div className="max-h-[500px] overflow-y-auto custom-finance-scroll p-4 space-y-4">
                        <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider sticky top-0 bg-background-dark/95 backdrop-blur z-10 py-2 border-b border-white/5 mb-2">{t('finance.recentExpenses', 'Recent Expenses')}</h3>
                        {expenses.length === 0 ? <p className="text-gray-500 italic text-sm text-center py-10">{t('finance.noExpenses', 'No expenses found.')}</p> : expenses.map(exp => (
                            <div key={exp.id} className="bg-white/5 border border-white/10 rounded-xl p-4 flex flex-col gap-3 hover:bg-white/10 transition-colors">
                                <div className="flex justify-between items-start">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400 flex-shrink-0"><FileText size={20} /></div>
                                        <div className="min-w-0"><h4 className="font-bold text-white text-sm truncate">{exp.category}</h4><p className="text-xs text-gray-400 font-mono">{new Date(exp.date).toLocaleDateString()}</p></div>
                                    </div>
                                    <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase bg-rose-900/30 text-rose-400 flex-shrink-0">EXPENSE</span>
                                </div>
                                <div className="flex justify-between items-center border-t border-white/5 pt-3">
                                    <p className="font-bold text-white">-€{exp.amount.toFixed(2)}</p>
                                    <div className="flex gap-1">
                                        <button onClick={() => handleEditExpense(exp)} className="p-1.5 hover:bg-white/10 rounded-lg text-amber-400"><Edit2 size={16} /></button>
                                        <button onClick={() => handleViewExpense(exp)} className="p-1.5 hover:bg-white/10 rounded-lg text-blue-400">{openingDocId === exp.id ? <Loader2 className="animate-spin w-4 h-4" /> : <Eye size={16} />}</button>
                                        <button onClick={() => handleDownloadExpense(exp)} className="p-1.5 hover:bg-white/10 rounded-lg text-green-400"><Download size={16} /></button>
                                        <button onClick={() => handleArchiveExpenseClick(exp.id)} className="p-1.5 hover:bg-white/10 rounded-lg text-indigo-400"><Archive size={16} /></button>
                                        <button onClick={() => deleteExpense(exp.id)} className="p-1.5 hover:bg-white/10 rounded-lg text-red-400"><Trash2 size={16} /></button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* INVOICE MODAL */}
            {showInvoiceModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
                    <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-2xl custom-finance-scroll">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-2xl font-bold text-white">{editingInvoiceId ? t('finance.editInvoice', 'Edit Invoice') : t('finance.createInvoice')}</h2>
                            <button onClick={closeInvoiceModal} className="text-gray-400 hover:text-white"><X size={24} /></button>
                        </div>
                        <form onSubmit={handleCreateOrUpdateInvoice} className="space-y-6">
                            <div className="space-y-4">
                                {editingInvoiceId && (
                                    <div className="bg-white/5 p-4 rounded-xl border border-white/10 mb-4">
                                        <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-2"><Activity size={14} /> {t('finance.statusLabel', 'Invoice Status')}</label>
                                        <select value={newInvoice.status} onChange={(e) => setNewInvoice({...newInvoice, status: e.target.value})} className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-start">
                                            <option value="DRAFT">{t('finance.status.draft')}</option>
                                            <option value="SENT">{t('finance.status.sent')}</option>
                                            <option value="PAID">{t('finance.status.paid')}</option>
                                            <option value="CANCELLED">{t('finance.status.cancelled')}</option>
                                        </select>
                                    </div>
                                )}
                                <h3 className="text-sm font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><User size={16} /> {t('caseCard.client')}</h3>
                                <div><label className="block text-sm text-gray-300 mb-1">{t('business.firmNameLabel', 'Name')}</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_name} onChange={e => setNewInvoice({...newInvoice, client_name: e.target.value})} /></div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div><label className="block text-sm text-gray-300 mb-1">{t('business.publicEmail', 'Email')}</label><input type="email" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_email} onChange={e => setNewInvoice({...newInvoice, client_email: e.target.value})} /></div>
                                    <div><label className="block text-sm text-gray-300 mb-1">{t('business.phone', 'Phone')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_phone} onChange={e => setNewInvoice({...newInvoice, client_phone: e.target.value})} /></div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div><label className="block text-sm text-gray-300 mb-1">{t('business.city')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_city} onChange={e => setNewInvoice({...newInvoice, client_city: e.target.value})} /></div>
                                    <div><label className="block text-sm text-gray-300 mb-1">{t('business.taxId')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_tax_id} onChange={e => setNewInvoice({...newInvoice, client_tax_id: e.target.value})} /></div>
                                </div>
                                <div><label className="block text-sm text-gray-300 mb-1">{t('business.address')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_address} onChange={e => setNewInvoice({...newInvoice, client_address: e.target.value})} /></div>
                            </div>
                            <div className="space-y-3 pt-4 border-t border-white/10">
                                <h3 className="text-sm font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><FileText size={16} /> {t('finance.services', 'Services')}</h3>
                                {lineItems.map((item, index) => (
                                    <div key={index} className="flex gap-2 items-center">
                                        <input type="text" placeholder={t('finance.description', 'Description')} className="flex-1 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.description} onChange={e => updateLineItem(index, 'description', e.target.value)} required />
                                        <input type="number" placeholder={t('finance.qty', 'Qty')} className="w-20 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', parseFloat(e.target.value))} min="1" />
                                        <input type="number" placeholder={t('finance.price', 'Price')} className="w-24 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.unit_price} onChange={e => updateLineItem(index, 'unit_price', parseFloat(e.target.value))} min="0" />
                                        <button type="button" onClick={() => removeLineItem(index)} className="p-2 text-red-400 hover:bg-red-900/20 rounded-lg"><Trash2 size={18} /></button>
                                    </div>
                                ))}
                                <button type="button" onClick={addLineItem} className="text-sm text-primary-start hover:underline flex items-center gap-1"><Plus size={14} /> {t('finance.addLine', 'Add Line')}</button>
                            </div>
                            <div className="flex justify-end gap-3">
                                <button type="button" onClick={closeInvoiceModal} className="px-4 py-2 text-gray-400">{t('general.cancel')}</button>
                                <button type="submit" className="px-6 py-2 bg-green-600 text-white rounded-lg font-bold">{t('general.save')}</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* EXPENSE MODAL */}
            {showExpenseModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
                    <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6 shadow-2xl">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold text-white flex items-center gap-2"><MinusCircle size={20} className="text-rose-500" /> {editingExpenseId ? t('finance.editExpense', 'Edit Expense') : t('finance.addExpense')}</h2>
                            <button onClick={closeExpenseModal} className="text-gray-400 hover:text-white"><X size={24} /></button>
                        </div>
                        <div className="mb-6">
                            <input type="file" ref={receiptInputRef} className="hidden" accept="image/*,.pdf" onChange={(e) => setExpenseReceipt(e.target.files?.[0] || null)} />
                            <button onClick={() => receiptInputRef.current?.click()} className={`w-full py-3 border border-dashed rounded-xl flex items-center justify-center gap-2 transition-all font-medium ${expenseReceipt ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'}`}>
                                {expenseReceipt ? (<><CheckCircle size={18} /> {expenseReceipt.name}</>) : (<><Paperclip size={18} /> {t('finance.attachReceipt')}</>)}
                            </button>
                        </div>
                        <form onSubmit={handleCreateOrUpdateExpense} className="space-y-5">
                            <div><label className="block text-sm text-gray-300 mb-1">{t('finance.expenseCategory')}</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.category} onChange={e => setNewExpense({...newExpense, category: e.target.value})} /></div>
                            <div><label className="block text-sm text-gray-300 mb-1">{t('finance.amount')}</label><input required type="number" step="0.01" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.amount} onChange={e => setNewExpense({...newExpense, amount: parseFloat(e.target.value)})} /></div>
                            <div><label className="block text-sm text-gray-300 mb-1">{t('finance.date')}</label><DatePicker selected={expenseDate} onChange={(date: Date | null) => setExpenseDate(date)} locale={currentLocale} dateFormat="dd/MM/yyyy" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-start" required /></div>
                            <div><label className="block text-sm text-gray-300 mb-1">{t('finance.description')}</label><textarea rows={3} className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.description} onChange={e => setNewExpense({...newExpense, description: e.target.value})} /></div>
                            <div className="flex justify-end gap-3 pt-4">
                                <button type="button" onClick={closeExpenseModal} className="px-4 py-2 text-gray-400">{t('general.cancel')}</button>
                                <button type="submit" className="px-6 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-bold">{t('general.save')}</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* ARCHIVE MODALS */}
            {showArchiveInvoiceModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200"><div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6 shadow-2xl"><h2 className="text-xl font-bold text-white mb-4">{t('finance.archiveInvoice')}</h2><div className="space-y-3 mb-6"><label className="block text-sm text-gray-400 mb-1">{t('drafting.selectCaseLabel')}</label><select className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-start" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">{t('archive.generalNoCase')}</option>{cases.map(c => (<option key={c.id} value={c.id}>{c.title}</option>))}</select></div><div className="flex justify-end gap-3"><button onClick={() => setShowArchiveInvoiceModal(false)} className="px-4 py-2 text-gray-400 hover:text-white">{t('general.cancel')}</button><button onClick={submitArchiveInvoice} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold">{t('general.save')}</button></div></div></div>)}
            {showArchiveExpenseModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200"><div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6 shadow-2xl"><h2 className="text-xl font-bold text-white mb-4">{t('finance.archiveExpenseTitle')}</h2><div className="space-y-3 mb-6"><label className="block text-sm text-gray-400 mb-1">{t('drafting.selectCaseLabel')}</label><select className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-start" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">{t('archive.generalNoCase')}</option>{cases.map(c => (<option key={c.id} value={c.id}>{c.title}</option>))}</select></div><div className="flex justify-end gap-3"><button onClick={() => setShowArchiveExpenseModal(false)} className="px-4 py-2 text-gray-400 hover:text-white">{t('general.cancel')}</button><button onClick={submitArchiveExpense} className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-bold">{t('general.save')}</button></div></div></div>)}

            {viewingDoc && <PDFViewerModal documentData={viewingDoc} onClose={closePreview} t={t} directUrl={viewingUrl} />}
        </motion.div>
    );
};