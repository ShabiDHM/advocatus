// FILE: src/components/business/FinanceTab.tsx
// PHOENIX PROTOCOL - FINANCE TAB V13.0 (GATEKEEPER ENFORCEMENT)
// 1. FEAT: Implemented 'isPro' check to lock 'Mbyllja Mujore' for Basic users.
// 2. UI: Added Lock icon and visual feedback for restricted actions.
// 3. SEC: Prevented navigation to the Wizard if user is not Pro/Admin.

import React, { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
    TrendingUp, TrendingDown, Wallet, Calculator, MinusCircle, Plus, FileText, 
    Edit2, Eye, Download, Archive, Trash2, Activity, Loader2, BarChart2, History, 
    Search, Briefcase, ChevronRight, ChevronDown, Car, Coffee, Building, Users, 
    Landmark, Zap, Wifi, Receipt, Utensils, Lock // PHOENIX: Added Lock Icon
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../../services/api';
import { Invoice, Case, Document, Expense, AnalyticsDashboardData } from '../../data/types';
import { useTranslation } from 'react-i18next';
import FileViewerModal from '../FileViewerModal'; 
import { InvoiceModal } from './finance/InvoiceModal';
import { ExpenseModal } from './finance/ExpenseModal';
import { FinanceAnalytics } from './finance/FinanceAnalytics';
import { useAuth } from '../../context/AuthContext'; // PHOENIX: Imported Auth Hook

// --- UI SUB-COMPONENTS ---
const SmartStatCard = ({ title, amount, icon, color }: { title: string, amount: string, icon: React.ReactNode, color: string }) => (
    <div className="group relative overflow-hidden rounded-2xl glass-panel p-5 hover:bg-white/10 transition-all duration-300">
        <div className="flex items-center gap-4 relative z-10">
            <div className={`p-3 rounded-xl ${color.replace('text-', 'bg-')}/10 ${color} shadow-inner`}>{icon}</div>
            <div>
                <p className="text-xs text-text-secondary font-bold uppercase tracking-wider">{title}</p>
                <p className="text-2xl font-bold text-white tracking-tight">{amount}</p>
            </div>
        </div>
        <div className={`absolute top-0 right-0 p-8 rounded-full blur-2xl opacity-10 ${color.replace('text-', 'bg-')}`} />
    </div>
);

// PHOENIX: Extended QuickActionButton to support 'locked' state
const QuickActionButton = ({ icon, label, onClick, color, locked = false }: { icon: React.ReactNode, label: string, onClick: () => void, color: string, locked?: boolean }) => (
    <button 
        onClick={onClick} 
        disabled={locked}
        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-transparent transition-all duration-200 text-sm font-semibold group relative overflow-hidden
        ${locked 
            ? 'bg-white/5 opacity-60 cursor-not-allowed hover:bg-white/5' 
            : 'bg-white/5 hover:bg-white/10 hover:border-white/10'
        }`}
    >
        <div className={`p-2 rounded-lg transition-transform ${locked ? 'bg-gray-700 text-gray-400' : `${color.replace('text-', 'bg-')}/10 ${color} group-hover:scale-110`}`}>
            {locked ? <Lock size={18} /> : icon}
        </div>
        <span className={`text-gray-200 ${locked ? '' : 'group-hover:text-white'}`}>{label}</span>
    </button>
);

const TabButton = ({ label, icon, isActive, onClick }: { label: string, icon: React.ReactNode, isActive: boolean, onClick: () => void }) => (
    <button onClick={onClick} className={`w-full sm:w-auto flex items-center justify-center gap-1.5 sm:gap-2 px-2 sm:px-4 py-2.5 rounded-xl text-[10px] sm:text-xs md:text-sm font-bold transition-all duration-300 ${isActive ? 'bg-gradient-to-r from-primary-start to-primary-end text-white shadow-lg shadow-primary-start/20' : 'text-text-secondary hover:bg-white/5 hover:text-white'}`}>
        <span className="shrink-0">{icon}</span>
        <span className="whitespace-nowrap">{label}</span>
    </button>
);

const SkeletonChart = () => (
    <div className="glass-panel rounded-2xl p-4 animate-pulse"><div className="h-6 bg-white/5 rounded w-1/3 mb-4"></div><div className="h-64 bg-white/5 rounded"></div></div>
);

const SkeletonGrid = () => (
     <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse"><div className="glass-panel rounded-2xl p-4"><div className="h-6 bg-white/5 rounded w-1/2 mb-4"></div><div className="h-64 bg-white/5 rounded"></div></div><div className="glass-panel rounded-2xl p-4"><div className="h-6 bg-white/5 rounded w-1/2 mb-4"></div><div className="space-y-2 mt-4"><div className="h-8 bg-white/5 rounded"></div><div className="h-8 bg-white/5 rounded"></div><div className="h-8 bg-white/5 rounded"></div><div className="h-8 bg-white/5 rounded"></div><div className="h-8 bg-white/5 rounded"></div></div></div></div>
);

export const FinanceTab: React.FC = () => {
    type ActiveTab = 'transactions' | 'reports' | 'history';
    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const { user } = useAuth(); // PHOENIX: Access user context

    const [loading, setLoading] = useState(true);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [cases, setCases] = useState<Case[]>([]);
    const [activeTab, setActiveTab] = useState<ActiveTab>('transactions');
    const [searchTerm, setSearchTerm] = useState('');
    const [analyticsData, setAnalyticsData] = useState<AnalyticsDashboardData | null>(null);

    // Modal States
    const [showInvoiceModal, setShowInvoiceModal] = useState(false);
    const [showExpenseModal, setShowExpenseModal] = useState(false);
    const [showArchiveInvoiceModal, setShowArchiveInvoiceModal] = useState(false);
    const [showArchiveExpenseModal, setShowArchiveExpenseModal] = useState(false);
    
    // Selection/Editing States
    const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
    const [selectedExpenseId, setSelectedExpenseId] = useState<string | null>(null);
    const [selectedCaseForArchive, setSelectedCaseForArchive] = useState<string>("");
    
    const [editingInvoice, setEditingInvoice] = useState<Invoice | null>(null);
    const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
    
    // Viewer States
    const [openingDocId, setOpeningDocId] = useState<string | null>(null);
    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [viewingUrl, setViewingUrl] = useState<string | null>(null);
    const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);

    // PHOENIX GATEKEEPER LOGIC
    const isPro = useMemo(() => {
        if (!user) return false;
        return user.subscription_tier === 'PRO' || user.role === 'ADMIN';
    }, [user]);

    const loadInitialData = async () => {
        try {
            const [inv, exp, cs, analytics] = await Promise.all([
                apiService.getInvoices().catch(() => []),
                apiService.getExpenses().catch(() => []),
                apiService.getCases().catch(() => []),
                apiService.getAnalyticsDashboard(30).catch(() => null)
            ]);
            setInvoices(inv); setExpenses(exp); setCases(cs); setAnalyticsData(analytics);
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

    const filteredTransactions = useMemo(() => {
        if (!searchTerm || activeTab !== 'transactions') return sortedTransactions;
        const lowerTerm = searchTerm.toLowerCase();
        return sortedTransactions.filter(tx => {
            if (tx.type === 'invoice') return (tx.client_name.toLowerCase().includes(lowerTerm) || tx.invoice_number?.toLowerCase().includes(lowerTerm) || tx.total_amount.toString().includes(lowerTerm));
            else return (tx.category.toLowerCase().includes(lowerTerm) || (tx.description && tx.description.toLowerCase().includes(lowerTerm)) || tx.amount.toString().includes(lowerTerm));
        });
    }, [sortedTransactions, searchTerm, activeTab]);

    const historyByCase = useMemo(() => {
        return cases.map(c => {
            const caseExpenses = expenses.filter(e => e.related_case_id === c.id);
            const caseInvoices = invoices.filter(i => (i as any).related_case_id === c.id);
            const expenseTotal = caseExpenses.reduce((sum, e) => sum + e.amount, 0);
            const invoiceTotal = caseInvoices.reduce((sum, i) => sum + i.total_amount, 0);
            const balance = invoiceTotal - expenseTotal;
            const activity = [
                ...caseExpenses.map(e => ({ ...e, type: 'expense', date: e.date, amount: e.amount, label: e.category })),
                ...caseInvoices.map(i => ({ ...i, type: 'invoice', date: i.issue_date, amount: i.total_amount, label: i.client_name }))
            ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
            return { caseData: c, expenseTotal, invoiceTotal, balance, activity, hasActivity: activity.length > 0 };
        }).filter(x => x.hasActivity).sort((a, b) => b.balance - a.balance); 
    }, [cases, expenses, invoices]);

    const filteredHistory = useMemo(() => {
        if (!searchTerm || activeTab !== 'history') return historyByCase;
        const lowerTerm = searchTerm.toLowerCase();
        return historyByCase.filter(item => {
            const inCase = item.caseData.title.toLowerCase().includes(lowerTerm) || item.caseData.case_number.toLowerCase().includes(lowerTerm);
            const inActivity = item.activity.some(act => (act.label && act.label.toLowerCase().includes(lowerTerm)));
            return inCase || inActivity;
        });
    }, [historyByCase, searchTerm, activeTab]);

    const getCategoryIcon = (category: string) => {
        const cat = category.toLowerCase();
        if (cat.includes('transport') || cat.includes('naft') || cat.includes('vetur') || cat.includes('fuel')) return <Car size={18} />;
        if (cat.includes('ushqim') || cat.includes('drek') || cat.includes('food')) return <Utensils size={18} />;
        if (cat.includes('kafe') || cat.includes('coffee')) return <Coffee size={18} />;
        if (cat.includes('zyr') || cat.includes('rent') || cat.includes('qira')) return <Building size={18} />;
        if (cat.includes('pag') || cat.includes('rrog') || cat.includes('salary')) return <Users size={18} />;
        if (cat.includes('tatim') || cat.includes('taksa') || cat.includes('tax')) return <Landmark size={18} />;
        if (cat.includes('rrym') || cat.includes('drita') || cat.includes('energy')) return <Zap size={18} />;
        if (cat.includes('internet') || cat.includes('tel')) return <Wifi size={18} />;
        return <Receipt size={18} />;
    };

    const closePreview = () => { if (viewingUrl) window.URL.revokeObjectURL(viewingUrl); setViewingUrl(null); setViewingDoc(null); };
    
    // --- Actions ---
    const handleInvoiceSuccess = (invoice: Invoice, isUpdate: boolean) => {
        if (isUpdate) { setInvoices(invoices.map(i => i.id === invoice.id ? invoice : i)); } 
        else { setInvoices([invoice, ...invoices]); }
    };

    const handleExpenseSuccess = (expense: Expense, isUpdate: boolean) => {
        if (isUpdate) { setExpenses(expenses.map(e => e.id === expense.id ? expense : e)); } 
        else { setExpenses([expense, ...expenses]); }
    };

    const deleteInvoice = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteInvoice(id); setInvoices(invoices.filter(inv => inv.id !== id)); } catch { alert(t('documentsPanel.deleteFailed')); } };
    const deleteExpense = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteExpense(id); setExpenses(expenses.filter(e => e.id !== id)); } catch { alert(t('error.generic')); } };
    
    // Viewing & Downloading Logic
    const handleViewInvoice = async (invoice: Invoice) => { setOpeningDocId(invoice.id); try { const blob = await apiService.getInvoicePdfBlob(invoice.id, i18n.language || 'sq'); const url = window.URL.createObjectURL(blob); setViewingUrl(url); setViewingDoc({ id: invoice.id, file_name: `Invoice #${invoice.invoice_number}`, mime_type: 'application/pdf', status: 'READY' } as any); } catch { alert(t('error.generic')); } finally { setOpeningDocId(null); } };
    const downloadInvoice = async (id: string) => { try { await apiService.downloadInvoicePdf(id, i18n.language || 'sq'); } catch { alert(t('error.generic')); } };
    
    const generateDigitalReceipt = (expense: Expense): File => {
        const content = `DËSHMI DIGJITALE E SHPENZIMIT (JURISTI AI)\n------------------------------------------------\nKategoria:   ${expense.category}\nShuma:       €${expense.amount.toFixed(2)}\nData:        ${new Date(expense.date).toLocaleDateString('sq-AL')}\nPërshkrimi:  ${expense.description || 'Pa përshkrim'}\nLënda:       ${expense.related_case_id ? (cases.find(c => c.id === expense.related_case_id)?.title || 'E panjohur') : 'Jo e specifikuar'}\n------------------------------------------------\nGjeneruar më: ${new Date().toLocaleString('sq-AL')}`;
        const blob = new Blob([content], { type: 'text/plain' });
        return new File([blob], `Shpenzim_${expense.category.replace(/\s+/g, '_')}_${expense.date}.txt`, { type: 'text/plain' });
    };

    const handleViewExpense = async (expense: Expense) => { 
        setOpeningDocId(expense.id); 
        try { 
            let blob: Blob; let filename: string;
            if (expense.receipt_url) { const response = await apiService.getExpenseReceiptBlob(expense.id); blob = response.blob; filename = response.filename; if (blob.type === 'application/json') throw new Error('Invalid receipt data'); } 
            else { const file = generateDigitalReceipt(expense); blob = file; filename = file.name; }
            const url = window.URL.createObjectURL(blob); setViewingUrl(url); setViewingDoc({ id: expense.id, file_name: filename, mime_type: blob.type, status: 'READY' } as any); 
        } catch (err: any) { alert(t('error.receiptNotFound', err.message)); } finally { setOpeningDocId(null); } 
    };

    const handleDownloadExpense = async (expense: Expense) => { 
        try { 
            let url: string; let filename: string;
            if (expense.receipt_url) { const { blob, filename: fn } = await apiService.getExpenseReceiptBlob(expense.id); url = window.URL.createObjectURL(blob); filename = fn; } 
            else { const file = generateDigitalReceipt(expense); url = window.URL.createObjectURL(file); filename = file.name; }
            const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); document.body.removeChild(a); if (!expense.receipt_url) window.URL.revokeObjectURL(url);
        } catch { alert(t('error.generic')); } 
    };

    const submitArchiveInvoice = async () => { if (!selectedInvoiceId) return; try { await apiService.archiveInvoice(selectedInvoiceId, selectedCaseForArchive || undefined); alert(t('general.saveSuccess')); setShowArchiveInvoiceModal(false); setSelectedCaseForArchive(""); } catch { alert(t('error.generic')); } };
    const submitArchiveExpense = async () => { 
        if (!selectedExpenseId) return; 
        try { 
            const ex = expenses.find(e => e.id === selectedExpenseId); if (!ex) return; 
            let fileToUpload: File;
            if (ex.receipt_url) { const { blob, filename } = await apiService.getExpenseReceiptBlob(ex.id); fileToUpload = new File([blob], filename, { type: blob.type }); } 
            else { fileToUpload = generateDigitalReceipt(ex); }
            await apiService.uploadArchiveItem(fileToUpload, fileToUpload.name, "EXPENSE", selectedCaseForArchive || undefined, undefined); alert(t('general.saveSuccess')); setShowArchiveExpenseModal(false); setSelectedCaseForArchive(""); 
        } catch { alert(t('error.generic')); } 
    };

    if (loading) return <div className="flex justify-center h-64 items-center"><Loader2 className="animate-spin text-primary-start" /></div>;
    
    return (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <style>{`.custom-finance-scroll::-webkit-scrollbar { width: 6px; } .custom-finance-scroll::-webkit-scrollbar-track { background: transparent; } .custom-finance-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 10px; } .no-scrollbar::-webkit-scrollbar { display: none; } .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }`}</style>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 lg:h-[600px]">
                <div className="lg:col-span-1 flex flex-col gap-6 h-full">
                    <div className="glass-panel rounded-3xl p-6 space-y-4 flex-none">
                        <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-2">{t('finance.overview')}</h3>
                        <SmartStatCard title={t('finance.income')} amount={`€${totalIncome.toFixed(2)}`} icon={<TrendingUp size={20} />} color="text-emerald-400" />
                        <SmartStatCard title={t('finance.expense')} amount={`€${totalExpenses.toFixed(2)}`} icon={<TrendingDown size={20} />} color="text-rose-400" />
                        <SmartStatCard title={t('finance.balance')} amount={`€${totalBalance.toFixed(2)}`} icon={<Wallet size={20} />} color="text-blue-400" />
                        
                        {analyticsData && (
                            <div className="pt-4 border-t border-white/5 mt-4">
                                <h4 className="text-[10px] font-bold text-primary-start uppercase tracking-wider mb-2">{t('finance.analytics.periodTitle')}</h4>
                                <div className="grid grid-cols-2 gap-2">
                                    <div className="bg-primary-start/10 p-2 rounded-lg text-center border border-primary-start/20"><p className="text-[10px] text-primary-300">{t('finance.analytics.totalSales')}</p><p className="font-bold text-white">€{analyticsData.total_revenue_period.toFixed(2)}</p></div>
                                    <div className="bg-primary-start/10 p-2 rounded-lg text-center border border-primary-start/20"><p className="text-[10px] text-primary-300">{t('finance.analytics.invoiceCount')}</p><p className="font-bold text-white">{analyticsData.total_transactions_period}</p></div>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="glass-panel rounded-3xl p-6 space-y-3 flex-1 flex flex-col justify-start">
                        <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-2">{t('finance.quickActions')}</h3>
                        <QuickActionButton icon={<Plus size={18} />} label={t('finance.createInvoice')} onClick={() => { setEditingInvoice(null); setShowInvoiceModal(true); }} color="text-emerald-400" />
                        <QuickActionButton icon={<MinusCircle size={18} />} label={t('finance.addExpense')} onClick={() => { setEditingExpense(null); setShowExpenseModal(true); }} color="text-rose-400" />
                        
                        {/* PHOENIX: LOCKED IF NOT PRO */}
                        <QuickActionButton 
                            icon={<Calculator size={18} />} 
                            label={t('finance.monthlyClose')} 
                            onClick={() => isPro && navigate('/finance/wizard')} 
                            color="text-text-secondary" 
                            locked={!isPro} // Pass locked state
                        />
                    </div>
                </div>

                <div className="lg:col-span-2 glass-panel rounded-3xl p-6 flex flex-col h-full min-w-0 overflow-hidden">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4 border-b border-white/5 pb-4 flex-none">
                        <h2 className="text-lg font-bold text-white shrink-0">{t('finance.activityAndReports')}</h2>
                        <div className="w-full sm:w-auto grid grid-cols-3 sm:flex items-center gap-2 bg-white/5 p-1 rounded-xl border border-white/5">
                            <TabButton label={t('finance.tabTransactions')} icon={<Activity size={16} />} isActive={activeTab === 'transactions'} onClick={() => setActiveTab('transactions')} />
                            <TabButton label={t('finance.tabReports')} icon={<BarChart2 size={16} />} isActive={activeTab === 'reports'} onClick={() => setActiveTab('reports')} />
                            <TabButton label={t('finance.tabHistory')} icon={<History size={16} />} isActive={activeTab === 'history'} onClick={() => setActiveTab('history')} />
                        </div>
                    </div>
                    
                    <div className="flex-1 flex flex-col min-h-0 relative -mr-2 pr-2 overflow-hidden">
                        {activeTab === 'transactions' && (
                            <div className="flex flex-col h-full space-y-4">
                                <div className="relative flex-none">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Search className="h-5 w-5 text-gray-500" /></div>
                                    <input type="text" placeholder={t('header.searchPlaceholder') || "Kërko..."} className="glass-input w-full pl-10 pr-3 py-2.5 rounded-xl" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 overflow-y-auto custom-finance-scroll pr-2 pb-4 content-start">
                                    {filteredTransactions.length === 0 ? <p className="text-gray-500 italic text-sm text-center col-span-full py-10">{t('finance.noTransactions')}</p> : filteredTransactions.map(tx => (
                                        <div key={`${tx.type}-${tx.id}`} className="group relative glass-panel rounded-2xl overflow-hidden hover:bg-white/10 transition-all duration-300 flex flex-col border border-white/5 hover:border-white/20 h-fit">
                                            <div className={`absolute left-0 top-0 bottom-0 w-1 ${tx.type === 'invoice' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                                            <div className="p-4 flex-1">
                                                <div className="flex items-start justify-between mb-3">
                                                    <div className={`p-2.5 rounded-xl ${tx.type === 'invoice' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>{tx.type === 'invoice' ? <FileText size={20} /> : getCategoryIcon(tx.category)}</div>
                                                    <div className="text-right"><p className={`text-lg font-bold ${tx.type === 'invoice' ? 'text-emerald-400' : 'text-rose-400'}`}>{tx.type === 'invoice' ? '+' : '-'}€{tx.type === 'invoice' ? tx.total_amount.toFixed(2) : tx.amount.toFixed(2)}</p><span className="text-[10px] text-gray-500 font-mono">{new Date(tx.date).toLocaleDateString()}</span></div>
                                                </div>
                                                <h4 className="font-bold text-white text-sm truncate mb-1" title={tx.type === 'invoice' ? tx.client_name : tx.category}>{tx.type === 'invoice' ? tx.client_name : tx.category}</h4>
                                                <p className="text-xs text-gray-400 truncate">{tx.type === 'invoice' ? `#${tx.invoice_number}` : (tx.description || t('finance.noDescription'))}</p>
                                            </div>
                                            <div className="border-t border-white/5 p-2 flex items-center justify-end gap-1 bg-black/20">
                                                <button onClick={() => { if(tx.type === 'invoice') { setEditingInvoice(tx); setShowInvoiceModal(true); } else { setEditingExpense(tx); setShowExpenseModal(true); } }} className="p-2 hover:bg-white/10 rounded-lg text-amber-400 transition-colors" title={t('general.edit')}><Edit2 size={14} /></button>
                                                <button onClick={() => tx.type === 'invoice' ? handleViewInvoice(tx) : handleViewExpense(tx)} disabled={openingDocId != null && openingDocId !== tx.id} className="p-2 hover:bg-white/10 rounded-lg text-blue-400 transition-colors disabled:opacity-50" title={t('general.view')}>{openingDocId === tx.id ? <Loader2 size={14} className="animate-spin"/> : <Eye size={14} />}</button>
                                                <button onClick={() => tx.type === 'invoice' ? downloadInvoice(tx.id) : handleDownloadExpense(tx)} className="p-2 hover:bg-white/10 rounded-lg text-green-400 transition-colors" title={t('general.download')}><Download size={14} /></button>
                                                <button onClick={() => { if (tx.type === 'invoice') { setSelectedInvoiceId(tx.id); setShowArchiveInvoiceModal(true); } else { setSelectedExpenseId(tx.id); setShowArchiveExpenseModal(true); } }} className="p-2 hover:bg-white/10 rounded-lg text-indigo-400 transition-colors" title={t('general.archive')}><Archive size={14} /></button>
                                                <button onClick={() => tx.type === 'invoice' ? deleteInvoice(tx.id) : deleteExpense(tx.id)} className="p-2 hover:bg-white/10 rounded-lg text-red-400 transition-colors" title={t('general.delete')}><Trash2 size={14} /></button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {activeTab === 'reports' && (<div className="h-full overflow-y-auto custom-finance-scroll pr-2 space-y-6">{!analyticsData ? <div className="space-y-6"><SkeletonChart /><SkeletonGrid /></div> : <FinanceAnalytics data={analyticsData} />}</div>)}
                        {activeTab === 'history' && (<div className="flex flex-col h-full space-y-4"><div className="relative flex-none"><div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Search className="h-5 w-5 text-gray-500" /></div><input type="text" placeholder={t('header.searchPlaceholder') || "Kërko..."} className="glass-input w-full pl-10 pr-3 py-2.5 rounded-xl" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} /></div><div className="space-y-4 flex-1 overflow-y-auto custom-finance-scroll pr-2">{filteredHistory.length === 0 ? (<div className="flex justify-center items-center h-full text-gray-500 text-center flex-col"><div className="bg-white/5 p-4 rounded-full mb-3"><Briefcase size={32} className="text-gray-600" /></div><p className="font-bold text-gray-400">{t('finance.noHistoryData', "Nuk ka të dhëna historike")}</p><p className="text-sm max-w-xs mt-2">{t('finance.historyHelper', "Shtoni shpenzime ose fatura të lidhura me lëndë për të parë pasqyrën këtu.")}</p></div>) : (filteredHistory.map((item) => (<div key={item.caseData.id} className="bg-white/5 border border-white/10 rounded-xl overflow-hidden"><div className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors" onClick={() => setExpandedCaseId(expandedCaseId === item.caseData.id ? null : item.caseData.id)}><div className="flex items-center gap-3"><div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg"><Briefcase size={18} /></div><div><h4 className="font-bold text-white text-sm">{item.caseData.title}</h4><p className="text-xs text-gray-500">{item.caseData.case_number}</p></div></div><div className="flex items-center gap-4"><div className="text-right"><p className="text-xs text-gray-400 uppercase">{t('finance.balance', 'Bilanci')}</p><p className={`font-bold ${item.balance >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{item.balance >= 0 ? '+' : ''}€{item.balance.toFixed(2)}</p></div>{expandedCaseId === item.caseData.id ? <ChevronDown size={18} className="text-gray-500"/> : <ChevronRight size={18} className="text-gray-500"/>}</div></div>{expandedCaseId === item.caseData.id && (<div className="bg-black/20 p-4 border-t border-white/5 space-y-2"><h5 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('finance.details', 'Detajet Financiare')}</h5>{item.activity.map((act, idx) => (<div key={`${act.type}-${idx}`} className="flex justify-between items-center text-sm py-1 border-b border-white/5 last:border-0"><div className="flex items-center gap-3"><span className="text-gray-400 text-xs font-mono">{new Date(act.date).toLocaleDateString('sq-AL')}</span><div className="flex flex-col"><span className="text-white font-medium">{act.label || act.type}</span><span className={`text-[10px] uppercase ${act.type === 'invoice' ? 'text-emerald-500/70' : 'text-rose-500/70'}`}>{act.type === 'invoice' ? t('finance.invoice') : t('finance.expense')}</span></div></div><span className={`${act.type === 'invoice' ? 'text-emerald-400' : 'text-rose-400'} font-mono`}>{act.type === 'invoice' ? '+' : '-'}€{act.amount.toFixed(2)}</span></div>))}</div>)}</div>)))}</div></div>)}</div></div></div>

            <InvoiceModal isOpen={showInvoiceModal} onClose={() => setShowInvoiceModal(false)} onSuccess={handleInvoiceSuccess} cases={cases} editingInvoice={editingInvoice} />
            <ExpenseModal isOpen={showExpenseModal} onClose={() => setShowExpenseModal(false)} onSuccess={handleExpenseSuccess} cases={cases} editingExpense={editingExpense} />
            {showArchiveInvoiceModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="glass-high w-full max-w-md p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200"><h2 className="text-xl font-bold text-white mb-6">{t('finance.archiveInvoice')}</h2><div className="mb-8"><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel')}</label><select className="glass-input w-full px-4 py-2.5 rounded-xl" value={selectedCaseForArchive} onChange={(e) => setSelectedCaseForArchive(e.target.value)}><option value="">{t('archive.generalNoCase')}</option>{cases.map(c => (<option key={c.id} value={c.id} className="bg-gray-900">{c.title}</option>))}</select></div><div className="flex justify-end gap-3"><button onClick={() => setShowArchiveInvoiceModal(false)} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10">{t('general.cancel')}</button><button onClick={submitArchiveInvoice} className="px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold shadow-lg">{t('general.save')}</button></div></div></div>)}
            {showArchiveExpenseModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="glass-high w-full max-w-md p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200"><h2 className="text-xl font-bold text-white mb-6">{t('finance.archiveExpenseTitle')}</h2><div className="mb-8"><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel')}</label><select className="glass-input w-full px-4 py-2.5 rounded-xl" value={selectedCaseForArchive} onChange={(e) => setSelectedCaseForArchive(e.target.value)}><option value="">{t('archive.generalNoCase')}</option>{cases.map(c => (<option key={c.id} value={c.id} className="bg-gray-900">{c.title}</option>))}</select></div><div className="flex justify-end gap-3"><button onClick={() => setShowArchiveExpenseModal(false)} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10">{t('general.cancel')}</button><button onClick={submitArchiveExpense} className="px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold shadow-lg">{t('general.save')}</button></div></div></div>)}
            {viewingDoc && <FileViewerModal documentData={viewingDoc} onClose={closePreview} onMinimize={closePreview} t={t} directUrl={viewingUrl} isAuth={true} />}
        </motion.div>
    );
};