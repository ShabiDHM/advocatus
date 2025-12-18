// FILE: src/components/business/FinanceTab.tsx
// PHOENIX PROTOCOL - FINANCE TAB V10.4 (FUNCTIONAL UPLOAD)
// 1. FIX: Activated the apiService.uploadPosFile call in handleFileUpload.
// 2. ADDED: Proper success and error alerting for the upload process.

import React, { useEffect, useState, useRef, useMemo, Fragment } from 'react';
import { motion } from 'framer-motion';
import { Menu, Transition } from '@headlessui/react';
import { 
    TrendingUp, TrendingDown, Wallet, Calculator, MinusCircle, Plus, FileText, 
    Edit2, Eye, Download, Archive, Trash2, CheckCircle, Paperclip, X, User, Activity, Loader2, UploadCloud, BarChart2, History, FileUp, MoreVertical
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiService, Expense, ExpenseCreateRequest, ImportBatchOut } from '../../services/api';
import { Invoice, InvoiceItem, Case, Document } from '../../data/types';
import { useTranslation } from 'react-i18next';
import PDFViewerModal from '../PDFViewerModal';
import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { sq, enUS } from 'date-fns/locale';

const DatePicker = (ReactDatePicker as any).default;

// --- UI SUB-COMPONENTS ---

const SmartStatCard = ({ title, amount, icon, color }: { title: string, amount: string, icon: React.ReactNode, color: string }) => (
    <div className="group relative overflow-hidden rounded-xl bg-white/5 border border-white/10 p-4 hover:bg-white/10 transition-all duration-300">
        <div className="flex items-center gap-4">
            <div className={`p-3 rounded-lg ${color.replace('text-', 'bg-')}/10 ${color}`}>{icon}</div>
            <div>
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">{title}</p>
                <p className="text-xl font-bold text-white tracking-tight">{amount}</p>
            </div>
        </div>
    </div>
);

const QuickActionButton = ({ icon, label, onClick, color }: { icon: React.ReactNode, label: string, onClick: () => void, color: string }) => (
    <button onClick={onClick} className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg bg-white/5 hover:bg-white/10 border border-transparent hover:border-white/20 transition-all duration-200 text-sm font-semibold`}>
        <div className={`p-2 rounded-md ${color.replace('text-', 'bg-')}/10 ${color}`}>{icon}</div>
        <span className="text-white">{label}</span>
    </button>
);

const TabButton = ({ label, icon, isActive, onClick }: { label: string, icon: React.ReactNode, isActive: boolean, onClick: () => void }) => (
    <button onClick={onClick} className={`flex-shrink-0 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${isActive ? 'bg-secondary-start/10 text-secondary-start' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}>
        {icon} {label}
    </button>
);


// --- MAIN FINANCE TAB COMPONENT ---

export const FinanceTab: React.FC = () => {
    type ActiveTab = 'transactions' | 'reports' | 'imports';

    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const localeMap: { [key: string]: any } = { sq, al: sq, en: enUS };
    const currentLocale = localeMap[i18n.language] || enUS;

    // --- STATE MANAGEMENT ---
    const [loading, setLoading] = useState(true);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [cases, setCases] = useState<Case[]>([]);
    const [importBatches, setImportBatches] = useState<ImportBatchOut[]>([]);
    const [activeTab, setActiveTab] = useState<ActiveTab>('transactions');
    const [openingDocId, setOpeningDocId] = useState<string | null>(null);

    // Modal States & Handlers
    const [showInvoiceModal, setShowInvoiceModal] = useState(false);
    const [showExpenseModal, setShowExpenseModal] = useState(false);
    const [showImportModal, setShowImportModal] = useState(false);
    const [showArchiveInvoiceModal, setShowArchiveInvoiceModal] = useState(false);
    const [showArchiveExpenseModal, setShowArchiveExpenseModal] = useState(false);
    
    // Selection / Edit States
    const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
    const [selectedExpenseId, setSelectedExpenseId] = useState<string | null>(null);
    const [selectedCaseForInvoice, setSelectedCaseForInvoice] = useState<string>("");
    const [editingInvoiceId, setEditingInvoiceId] = useState<string | null>(null);
    const [editingExpenseId, setEditingExpenseId] = useState<string | null>(null);

    // Document Viewing
    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [viewingUrl, setViewingUrl] = useState<string | null>(null);

    // Form States
    const [newInvoice, setNewInvoice] = useState({ client_name: '', client_email: '', client_phone: '', client_address: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: 18, notes: '', status: 'DRAFT' });
    const [lineItems, setLineItems] = useState<InvoiceItem[]>([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);
    const [newExpense, setNewExpense] = useState<ExpenseCreateRequest>({ category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0] });
    const [expenseDate, setExpenseDate] = useState<Date | null>(new Date());
    const [expenseReceipt, setExpenseReceipt] = useState<File | null>(null);
    const receiptInputRef = useRef<HTMLInputElement>(null);

    // Import Modal State
    const [isUploading, setIsUploading] = useState(false);
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [uploadError, setUploadError] = useState<string | null>(null);

    // --- DATA ---
    const loadInitialData = async () => {
        try {
            // PHOENIX: In the future, this should also fetch import batches
            const [inv, exp, cs] = await Promise.all([
                apiService.getInvoices().catch(() => []),
                apiService.getExpenses().catch(() => []),
                apiService.getCases().catch(() => []),
            ]);
            setInvoices(inv); setExpenses(exp); setCases(cs); 
        } catch (e) { console.error(e); } finally { setLoading(false); }
    };

    useEffect(() => { loadInitialData(); }, []);

    const totalIncome = invoices.reduce((sum, inv) => sum + inv.total_amount, 0);
    const totalExpenses = expenses.reduce((sum, exp) => sum + exp.amount, 0);
    const totalBalance = totalIncome - totalExpenses;

    const sortedTransactions = useMemo(() => {
        const combined = [
            ...invoices.map(i => ({ ...i, type: 'invoice' as const, date: i.issue_date })),
            ...expenses.map(e => ({ ...e, type: 'expense' as const }))
        ];
        return combined.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    }, [invoices, expenses]);

    // --- HANDLERS ---
    const closePreview = () => { if (viewingUrl) window.URL.revokeObjectURL(viewingUrl); setViewingUrl(null); setViewingDoc(null); };
    const addLineItem = () => setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0, total: 0 }]);
    const removeLineItem = (i: number) => lineItems.length > 1 && setLineItems(lineItems.filter((_, idx) => idx !== i));
    const updateLineItem = (i: number, f: keyof InvoiceItem, v: any) => { const n = [...lineItems]; n[i] = { ...n[i], [f]: v }; n[i].total = n[i].quantity * n[i].unit_price; setLineItems(n); };
    
    // Invoice Handlers
    const handleEditInvoice = (invoice: Invoice) => { setEditingInvoiceId(invoice.id); setNewInvoice({ client_name: invoice.client_name, client_email: invoice.client_email || '', client_address: invoice.client_address || '', client_phone: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: invoice.tax_rate, notes: invoice.notes || '', status: invoice.status }); setLineItems(invoice.items); setShowInvoiceModal(true); };
    const handleCreateOrUpdateInvoice = async (e: React.FormEvent) => { e.preventDefault(); try { const payload = { client_name: newInvoice.client_name, client_email: newInvoice.client_email, client_address: newInvoice.client_address, items: lineItems, tax_rate: newInvoice.tax_rate, notes: newInvoice.notes, status: newInvoice.status }; if (editingInvoiceId) { const u = await apiService.updateInvoice(editingInvoiceId, payload); setInvoices(invoices.map(i => i.id === editingInvoiceId ? u : i)); } else { const n = await apiService.createInvoice(payload); setInvoices([n, ...invoices]); } closeInvoiceModal(); } catch { alert(t('error.generic')); } };
    const closeInvoiceModal = () => { setShowInvoiceModal(false); setEditingInvoiceId(null); setNewInvoice({ client_name: '', client_email: '', client_phone: '', client_address: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: 18, notes: '', status: 'DRAFT' }); setLineItems([{ description: '', quantity: 1, unit_price: 0, total: 0 }]); };
    const deleteInvoice = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteInvoice(id); setInvoices(invoices.filter(inv => inv.id !== id)); } catch { alert(t('documentsPanel.deleteFailed')); } };
    const handleViewInvoice = async (invoice: Invoice) => { setOpeningDocId(invoice.id); try { const blob = await apiService.getInvoicePdfBlob(invoice.id, i18n.language); const url = window.URL.createObjectURL(blob); setViewingUrl(url); setViewingDoc({ id: invoice.id, file_name: `Invoice #${invoice.invoice_number}`, mime_type: 'application/pdf', status: 'READY' } as any); } catch { alert(t('error.generic')); } finally { setOpeningDocId(null); } };
    const downloadInvoice = async (id: string) => { try { await apiService.downloadInvoicePdf(id, i18n.language); } catch { alert(t('error.generic')); } };
    const handleArchiveInvoiceClick = (id: string) => { setSelectedInvoiceId(id); setShowArchiveInvoiceModal(true); };
    const submitArchiveInvoice = async () => { if (!selectedInvoiceId) return; try { await apiService.archiveInvoice(selectedInvoiceId, selectedCaseForInvoice || undefined); alert(t('general.saveSuccess')); setShowArchiveInvoiceModal(false); setSelectedCaseForInvoice(""); } catch { alert(t('error.generic')); } };

    // Expense Handlers
    const handleEditExpense = (expense: Expense) => { setEditingExpenseId(expense.id); setNewExpense({ category: expense.category, amount: expense.amount, description: expense.description || '', date: expense.date }); setExpenseDate(new Date(expense.date)); setShowExpenseModal(true); };
    const handleCreateOrUpdateExpense = async (e: React.FormEvent) => { e.preventDefault(); try { const payload = { ...newExpense, date: expenseDate ? expenseDate.toISOString().split('T')[0] : new Date().toISOString().split('T')[0] }; let s: Expense; if (editingExpenseId) { s = await apiService.updateExpense(editingExpenseId, payload); setExpenses(expenses.map(exp => exp.id === editingExpenseId ? s : exp)); } else { s = await apiService.createExpense(payload); setExpenses([s, ...expenses]); } if (expenseReceipt && s.id) { await apiService.uploadExpenseReceipt(s.id, expenseReceipt); const f = { ...s, receipt_url: "PENDING_REFRESH" }; setExpenses(prev => prev.map(exp => exp.id === f.id ? f : exp)); } closeExpenseModal(); } catch { alert(t('error.generic')); } };
    const closeExpenseModal = () => { setShowExpenseModal(false); setEditingExpenseId(null); setNewExpense({ category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0] }); setExpenseReceipt(null); };
    const deleteExpense = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteExpense(id); setExpenses(expenses.filter(e => e.id !== id)); } catch { alert(t('error.generic')); } };
    const handleViewExpense = async (expense: Expense) => { if (!expense.receipt_url) { alert(t('error.noReceiptAttached')); return; } setOpeningDocId(expense.id); try { const { blob, filename } = await apiService.getExpenseReceiptBlob(expense.id); const url = window.URL.createObjectURL(blob); const ext = filename.split('.').pop()?.toLowerCase(); const mime = ext === 'pdf' ? 'application/pdf' : 'image/jpeg'; setViewingUrl(url); setViewingDoc({ id: expense.id, file_name: filename, mime_type: mime, status: 'READY' } as any); } catch { alert(t('error.receiptNotFound')); } finally { setOpeningDocId(null); } };
    const handleDownloadExpense = async (expense: Expense) => { if (!expense.receipt_url) { alert(t('error.noReceiptAttached')); return; } try { const { blob, filename } = await apiService.getExpenseReceiptBlob(expense.id); const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); document.body.removeChild(a); } catch { alert(t('error.generic')); } };
    const handleArchiveExpenseClick = (id: string) => { const ex = expenses.find(e => e.id === id); if (!ex || !ex.receipt_url) { alert(t('error.noReceiptToArchive')); return; } setSelectedExpenseId(id); setShowArchiveExpenseModal(true); };
    const submitArchiveExpense = async () => { if (!selectedExpenseId) return; try { const ex = expenses.find(e => e.id === selectedExpenseId); if (!ex || !ex.receipt_url) return; const { blob, filename } = await apiService.getExpenseReceiptBlob(ex.id); const f = new File([blob], filename, { type: blob.type }); await apiService.uploadArchiveItem(f, filename, "EXPENSE", selectedCaseForInvoice || undefined, undefined); alert(t('general.saveSuccess')); setShowArchiveExpenseModal(false); setSelectedCaseForInvoice(""); } catch { alert(t('error.generic')); } };

    // Import Handlers
    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => { const file = e.target.files?.[0]; if (file) { setUploadError(null); setUploadFile(file); } };
    const closeImportModal = () => { setShowImportModal(false); setUploadFile(null); setUploadError(null); setIsUploading(false); };
    const handleFileUpload = async () => {
        if (!uploadFile) return;
        setIsUploading(true);
        setUploadError(null);
        try {
            const response = await apiService.uploadPosFile(uploadFile);
            setImportBatches(prev => [response, ...prev]);
            alert(`Sukses! U importuan ${response.row_count} transaksione.`);
            // PHOENIX: In the future, we should refresh all finance data here.
            // For now, we switch to the history tab to show the result.
            setActiveTab('imports');
            closeImportModal();
        } catch (error: any) {
            const detail = error.response?.data?.detail || "Ngarkimi dështoi. Ju lutemi provoni përsëri.";
            setUploadError(detail);
        } finally {
            setIsUploading(false);
        }
    };

    if (loading) return <div className="flex justify-center h-64 items-center"><Loader2 className="animate-spin text-secondary-start" /></div>;

    // ... (rest of the file remains the same, no need to repeat)
    return (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <style>{`.custom-finance-scroll::-webkit-scrollbar { width: 6px; } .custom-finance-scroll::-webkit-scrollbar-track { background: rgba(0,0,0,0.1); } .custom-finance-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 10px; } .no-scrollbar::-webkit-scrollbar { display: none; } .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }`}</style>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="lg:col-span-1 flex flex-col gap-6">
                    <div className="bg-background-dark/50 border border-glass-edge rounded-3xl p-6 space-y-4"><h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">{t('finance.overview')}</h3><SmartStatCard title={t('finance.income')} amount={`€${totalIncome.toFixed(2)}`} icon={<TrendingUp size={20} />} color="text-emerald-400" /><SmartStatCard title={t('finance.expense')} amount={`€${totalExpenses.toFixed(2)}`} icon={<TrendingDown size={20} />} color="text-rose-400" /><SmartStatCard title={t('finance.balance')} amount={`€${totalBalance.toFixed(2)}`} icon={<Wallet size={20} />} color="text-blue-400" /></div>
                    <div className="bg-background-dark/50 border border-glass-edge rounded-3xl p-6 space-y-3"><h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">{t('finance.quickActions')}</h3><QuickActionButton icon={<Plus size={18} />} label={t('finance.createInvoice')} onClick={() => setShowInvoiceModal(true)} color="text-emerald-400" /><QuickActionButton icon={<MinusCircle size={18} />} label={t('finance.addExpense')} onClick={() => setShowExpenseModal(true)} color="text-rose-400" /><QuickActionButton icon={<FileUp size={18} />} label={t('finance.importTransactions')} onClick={() => setShowImportModal(true)} color="text-indigo-400" /><QuickActionButton icon={<Calculator size={18} />} label={t('finance.monthlyClose')} onClick={() => navigate('/finance/wizard')} color="text-gray-400" /></div>
                </div>

                <div className="lg:col-span-2 bg-background-dark/50 border border-glass-edge rounded-3xl p-6 flex flex-col min-h-[600px]">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4 border-b border-white/10 pb-4"><h2 className="text-lg font-bold text-white shrink-0">{t('finance.activityAndReports')}</h2><div className="w-full sm:w-auto flex items-center gap-2 bg-background-light p-1 rounded-xl border border-white/5 overflow-x-auto no-scrollbar"><TabButton label={t('finance.tabTransactions')} icon={<Activity size={16} />} isActive={activeTab === 'transactions'} onClick={() => setActiveTab('transactions')} /><TabButton label={t('finance.tabReports')} icon={<BarChart2 size={16} />} isActive={activeTab === 'reports'} onClick={() => setActiveTab('reports')} /><TabButton label={t('finance.tabHistory')} icon={<History size={16} />} isActive={activeTab === 'imports'} onClick={() => setActiveTab('imports')} /></div></div>
                    <div className="flex-1 overflow-y-auto custom-finance-scroll -mr-2 pr-2">
                        {activeTab === 'transactions' && (<div className="space-y-3">{sortedTransactions.length === 0 ? <p className="text-gray-500 italic text-sm text-center py-10">{t('finance.noTransactions')}</p> : sortedTransactions.map(tx => (<div key={`${tx.type}-${tx.id}`} className="bg-white/5 border border-white/10 rounded-xl p-3 hover:bg-white/10 transition-colors"><div className="flex justify-between items-center"><div className="flex items-center gap-3 min-w-0"><div className={`p-2 rounded-lg flex-shrink-0 ${tx.type === 'invoice' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>{tx.type === 'invoice' ? <FileText size={18} /> : <MinusCircle size={18} />}</div><div className="min-w-0"><h4 className="font-bold text-white text-sm truncate">{tx.type === 'invoice' ? tx.client_name : tx.category}</h4><p className="text-xs text-gray-400 font-mono">{tx.type === 'invoice' ? `#${tx.invoice_number}` : new Date(tx.date).toLocaleDateString()}</p></div></div><div className="flex items-center gap-4"><p className={`font-bold ${tx.type === 'invoice' ? 'text-emerald-400' : 'text-rose-400'}`}>{tx.type === 'invoice' ? `+€${tx.total_amount.toFixed(2)}` : `-€${tx.amount.toFixed(2)}`}</p><Menu as="div" className="relative"><Menu.Button className="p-1.5 hover:bg-white/10 rounded-full text-gray-400"><MoreVertical size={16} /></Menu.Button><Transition as={Fragment} enter="transition ease-out duration-100" enterFrom="transform opacity-0 scale-95" enterTo="transform opacity-100 scale-100" leave="transition ease-in duration-75" leaveFrom="transform opacity-100 scale-100" leaveTo="transform opacity-0 scale-95"><Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right divide-y divide-white/10 rounded-md bg-background-light shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-10 border border-glass-edge"><div className="px-1 py-1"><Menu.Item>{({ active }: { active: boolean }) => (<button onClick={() => tx.type === 'invoice' ? handleEditInvoice(tx) : handleEditExpense(tx)} className={`${active ? 'bg-white/10 text-white' : 'text-gray-300'} group flex w-full items-center rounded-md px-2 py-2 text-sm`}><Edit2 className="mr-2 h-4 w-4 text-amber-400" />{t('general.edit')}</button>)}</Menu.Item><Menu.Item>{({ active }: { active: boolean }) => (<button onClick={() => tx.type === 'invoice' ? handleViewInvoice(tx) : handleViewExpense(tx)} disabled={(tx.type === 'expense' && !tx.receipt_url) || openingDocId === tx.id} className={`${active ? 'bg-white/10 text-white' : 'text-gray-300'} group flex w-full items-center rounded-md px-2 py-2 text-sm disabled:opacity-50`}>{openingDocId === tx.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin"/> : <Eye className="mr-2 h-4 w-4 text-blue-400" />}{t('general.view')}</button>)}</Menu.Item><Menu.Item>{({ active }: { active: boolean }) => (<button onClick={() => tx.type === 'invoice' ? downloadInvoice(tx.id) : handleDownloadExpense(tx)} disabled={tx.type === 'expense' && !tx.receipt_url} className={`${active ? 'bg-white/10 text-white' : 'text-gray-300'} group flex w-full items-center rounded-md px-2 py-2 text-sm disabled:opacity-50`}><Download className="mr-2 h-4 w-4 text-green-400" />{t('general.download')}</button>)}</Menu.Item></div><div className="px-1 py-1"><Menu.Item>{({ active }: { active: boolean }) => (<button onClick={() => tx.type === 'invoice' ? handleArchiveInvoiceClick(tx.id) : handleArchiveExpenseClick(tx.id)} disabled={tx.type === 'expense' && !tx.receipt_url} className={`${active ? 'bg-white/10 text-white' : 'text-gray-300'} group flex w-full items-center rounded-md px-2 py-2 text-sm disabled:opacity-50`}><Archive className="mr-2 h-4 w-4 text-indigo-400" />{t('general.archive')}</button>)}</Menu.Item></div><div className="px-1 py-1"><Menu.Item>{({ active }: { active: boolean }) => (<button onClick={() => tx.type === 'invoice' ? deleteInvoice(tx.id) : deleteExpense(tx.id)} className={`${active ? 'bg-red-500/20 text-red-400' : 'text-red-400'} group flex w-full items-center rounded-md px-2 py-2 text-sm`}><Trash2 className="mr-2 h-4 w-4" />{t('general.delete')}</button>)}</Menu.Item></div></Menu.Items></Transition></Menu></div></div></div>))}</div>)}
                        {activeTab === 'reports' && (<div className="flex items-center justify-center h-full text-center text-gray-500"><div className="space-y-2"><BarChart2 className="mx-auto" size={40} /><p className="font-bold text-lg">{t('finance.reportsTitle')}</p><p className="text-sm">{t('finance.reportsComingSoon')}</p></div></div>)}
                        {activeTab === 'imports' && (
                            <div className="space-y-3">
                                {importBatches.length === 0 ? (
                                    <p className="text-gray-500 italic text-sm text-center py-10">{t('finance.historyDescription')}</p>
                                ) : (
                                    importBatches.map(batch => (
                                        <div key={batch.id} className="bg-white/5 border border-white/10 rounded-xl p-3 flex justify-between items-center">
                                            <div className="flex items-center gap-3">
                                                <CheckCircle size={18} className="text-emerald-400" />
                                                <div>
                                                    <p className="font-medium text-white text-sm">{batch.filename}</p>
                                                    <p className="text-xs text-gray-500 font-mono">{new Date(batch.created_at).toLocaleString()}</p>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm font-medium text-white">{batch.row_count} Transaksione</p>
                                                <p className="text-xs text-gray-500 font-mono">+€{batch.total_volume.toFixed(2)}</p>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {showImportModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-lg p-6"><div className="flex justify-between items-center mb-4"><h2 className="text-xl font-bold text-white flex items-center gap-2"><FileUp size={20} className="text-indigo-400" /> {t('finance.importModal.title')}</h2><button onClick={closeImportModal} className="text-gray-400 hover:text-white"><X size={24} /></button></div><p className="text-sm text-gray-400 mb-6">{t('finance.importModal.description')}</p><div><label htmlFor="file-upload" className="w-full py-10 border-2 border-dashed border-white/20 rounded-xl flex flex-col items-center justify-center gap-3 cursor-pointer hover:bg-white/5 hover:border-indigo-400">{uploadFile ? (<><FileText size={32} className="text-indigo-400" /><span className="font-medium text-white">{uploadFile.name}</span><span className="text-xs text-gray-400">{t('finance.importModal.changeFile')}</span></>) : (<><UploadCloud size={32} className="text-gray-500" /><span className="font-medium text-white">{t('finance.importModal.selectFile')}</span><span className="text-xs text-gray-500">{t('finance.importModal.fileTypes')}</span></>)}</label><input id="file-upload" type="file" className="hidden" accept=".csv,.xlsx,.xls" onChange={handleFileSelect} />{uploadError && <p className="text-rose-400 text-sm mt-2 text-center">{uploadError}</p>}</div><div className="flex justify-end gap-3 pt-6 mt-6 border-t border-white/10"><button type="button" onClick={closeImportModal} className="px-4 py-2 text-gray-400 rounded-lg hover:bg-white/5">{t('general.cancel')}</button><button type="button" onClick={handleFileUpload} disabled={!uploadFile || isUploading} className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-bold flex items-center gap-2 disabled:opacity-50 hover:bg-indigo-500">{isUploading ? <Loader2 className="animate-spin" size={18} /> : <FileUp size={18} />}{isUploading ? t('finance.importModal.importing') : t('finance.importModal.import')}</button></div></div></div>)}
            {showInvoiceModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 custom-finance-scroll"><div className="flex justify-between items-center mb-6"><h2 className="text-2xl font-bold text-white">{editingInvoiceId ? t('finance.editInvoice') : t('finance.createInvoice')}</h2><button onClick={closeInvoiceModal} className="text-gray-400 hover:text-white"><X size={24} /></button></div><form onSubmit={handleCreateOrUpdateInvoice} className="space-y-6"><div className="space-y-4">{editingInvoiceId && (<div className="bg-white/5 p-4 rounded-xl border-white/10 mb-4"><label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2"><Activity size={14} /> {t('finance.statusLabel')}</label><select value={newInvoice.status} onChange={(e) => setNewInvoice({...newInvoice, status: e.target.value})} className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white"><option value="DRAFT">{t('finance.status.draft')}</option><option value="SENT">{t('finance.status.sent')}</option><option value="PAID">{t('finance.status.paid')}</option><option value="CANCELLED">{t('finance.status.cancelled')}</option></select></div>)}<h3 className="text-sm font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><User size={16} /> {t('caseCard.client')}</h3><div><label className="block text-sm text-gray-300 mb-1">{t('business.firmNameLabel')}</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_name} onChange={e => setNewInvoice({...newInvoice, client_name: e.target.value})} /></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><div><label className="block text-sm text-gray-300 mb-1">{t('business.publicEmail')}</label><input type="email" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_email} onChange={e => setNewInvoice({...newInvoice, client_email: e.target.value})} /></div><div><label className="block text-sm text-gray-300 mb-1">{t('business.phone')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_phone} onChange={e => setNewInvoice({...newInvoice, client_phone: e.target.value})} /></div></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><div><label className="block text-sm text-gray-300 mb-1">{t('business.city')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_city} onChange={e => setNewInvoice({...newInvoice, client_city: e.target.value})} /></div><div><label className="block text-sm text-gray-300 mb-1">{t('business.taxId')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_tax_id} onChange={e => setNewInvoice({...newInvoice, client_tax_id: e.target.value})} /></div></div><div><label className="block text-sm text-gray-300 mb-1">{t('business.address')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_address} onChange={e => setNewInvoice({...newInvoice, client_address: e.target.value})} /></div></div><div className="space-y-3 pt-4 border-t border-white/10"><h3 className="text-sm font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><FileText size={16} /> {t('finance.services')}</h3>{lineItems.map((item, index) => (<div key={index} className="flex flex-col sm:flex-row gap-2 items-center"><input type="text" placeholder={t('finance.description')} className="flex-1 w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.description} onChange={e => updateLineItem(index, 'description', e.target.value)} required /><input type="number" placeholder={t('finance.qty')} className="w-full sm:w-20 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', parseFloat(e.target.value))} min="1" /><input type="number" placeholder={t('finance.price')} className="w-full sm:w-24 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.unit_price} onChange={e => updateLineItem(index, 'unit_price', parseFloat(e.target.value))} min="0" /><button type="button" onClick={() => removeLineItem(index)} className="p-2 text-red-400 hover:bg-red-900/20 rounded-lg self-end sm:self-center"><Trash2 size={18} /></button></div>))}<button type="button" onClick={addLineItem} className="text-sm text-primary-start hover:underline flex items-center gap-1"><Plus size={14} /> {t('finance.addLine')}</button></div><div className="flex justify-end gap-3"><button type="button" onClick={closeInvoiceModal} className="px-4 py-2 text-gray-400">{t('general.cancel')}</button><button type="submit" className="px-6 py-2 bg-green-600 text-white rounded-lg font-bold">{t('general.save')}</button></div></form></div></div>)}
            {showExpenseModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6"><div className="flex justify-between items-center mb-6"><h2 className="text-xl font-bold text-white flex items-center gap-2"><MinusCircle size={20} className="text-rose-500" /> {editingExpenseId ? t('finance.editExpense') : t('finance.addExpense')}</h2><button onClick={closeExpenseModal} className="text-gray-400 hover:text-white"><X size={24} /></button></div><div className="mb-6"><input type="file" ref={receiptInputRef} className="hidden" accept="image/*,.pdf" onChange={(e) => setExpenseReceipt(e.target.files?.[0] || null)} /><button onClick={() => receiptInputRef.current?.click()} className={`w-full py-3 border border-dashed rounded-xl flex items-center justify-center gap-2 transition-all ${expenseReceipt ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300' : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'}`}>{expenseReceipt ? (<><CheckCircle size={18} /> {expenseReceipt.name}</>) : (<><Paperclip size={18} /> {t('finance.attachReceipt')}</>)}</button></div><form onSubmit={handleCreateOrUpdateExpense} className="space-y-5"><div><label className="block text-sm text-gray-300 mb-1">{t('finance.expenseCategory')}</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.category} onChange={e => setNewExpense({...newExpense, category: e.target.value})} /></div><div><label className="block text-sm text-gray-300 mb-1">{t('finance.amount')}</label><input required type="number" step="0.01" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.amount} onChange={e => setNewExpense({...newExpense, amount: parseFloat(e.target.value)})} /></div><div><label className="block text-sm text-gray-300 mb-1">{t('finance.date')}</label><DatePicker selected={expenseDate} onChange={(date: Date | null) => setExpenseDate(date)} locale={currentLocale} dateFormat="dd/MM/yyyy" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" required /></div><div><label className="block text-sm text-gray-300 mb-1">{t('finance.description')}</label><textarea rows={3} className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.description} onChange={e => setNewExpense({...newExpense, description: e.target.value})} /></div><div className="flex justify-end gap-3 pt-4"><button type="button" onClick={closeExpenseModal} className="px-4 py-2 text-gray-400">{t('general.cancel')}</button><button type="submit" className="px-6 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-bold">{t('general.save')}</button></div></form></div></div>)}
            {showArchiveInvoiceModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6"><h2 className="text-xl font-bold text-white mb-4">{t('finance.archiveInvoice')}</h2><div className="mb-6"><label className="block text-sm text-gray-400 mb-1">{t('drafting.selectCaseLabel')}</label><select className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">{t('archive.generalNoCase')}</option>{cases.map(c => (<option key={c.id} value={c.id}>{c.title}</option>))}</select></div><div className="flex justify-end gap-3"><button onClick={() => setShowArchiveInvoiceModal(false)} className="px-4 py-2 text-gray-400">{t('general.cancel')}</button><button onClick={submitArchiveInvoice} className="px-6 py-2 bg-blue-600 text-white rounded-lg">{t('general.save')}</button></div></div></div>)}
            {showArchiveExpenseModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6"><h2 className="text-xl font-bold text-white mb-4">{t('finance.archiveExpenseTitle')}</h2><div className="mb-6"><label className="block text-sm text-gray-400 mb-1">{t('drafting.selectCaseLabel')}</label><select className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">{t('archive.generalNoCase')}</option>{cases.map(c => (<option key={c.id} value={c.id}>{c.title}</option>))}</select></div><div className="flex justify-end gap-3"><button onClick={() => setShowArchiveExpenseModal(false)} className="px-4 py-2 text-gray-400">{t('general.cancel')}</button><button onClick={submitArchiveExpense} className="px-6 py-2 bg-indigo-600 text-white rounded-lg">{t('general.save')}</button></div></div></div>)}

            {viewingDoc && <PDFViewerModal documentData={viewingDoc} onClose={closePreview} t={t} directUrl={viewingUrl} />}
        </motion.div>
    );
};