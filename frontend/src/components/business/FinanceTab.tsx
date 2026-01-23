// FILE: src/components/business/FinanceTab.tsx
// PHOENIX PROTOCOL - FINANCE TAB V10.2 (AI AUTO-FILL)
// 1. FEATURE: Implemented 'AI Scan' for expense receipts.
// 2. LOGIC: Uploading a receipt now triggers OCR + LLM analysis to auto-fill form fields.
// 3. UI: Added loading state to the upload button during analysis.

import React, { useEffect, useState, useRef, useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
    TrendingUp, TrendingDown, Wallet, Calculator, MinusCircle, Plus, FileText, 
    Edit2, Eye, Download, Archive, Trash2, CheckCircle, Paperclip, X, User, Activity, 
    Loader2, BarChart2, History, Search, Briefcase, ChevronRight, ChevronDown,
    Car, Coffee, Building, Users, Landmark, Zap, Wifi, Receipt, Utensils, Sparkles
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../../services/api';
import { 
    Invoice, InvoiceItem, Case, Document, 
    Expense, ExpenseCreateRequest, AnalyticsDashboardData, TopProductItem 
} from '../../data/types';
import { useTranslation } from 'react-i18next';
import PDFViewerModal from '../PDFViewerModal';
import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { sq, enUS } from 'date-fns/locale';
import { 
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell 
} from 'recharts';

const DatePicker = (ReactDatePicker as any).default;

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

const QuickActionButton = ({ icon, label, onClick, color }: { icon: React.ReactNode, label: string, onClick: () => void, color: string }) => (
    <button onClick={onClick} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-transparent hover:border-white/10 transition-all duration-200 text-sm font-semibold group`}>
        <div className={`p-2 rounded-lg ${color.replace('text-', 'bg-')}/10 ${color} group-hover:scale-110 transition-transform`}>{icon}</div>
        <span className="text-gray-200 group-hover:text-white">{label}</span>
    </button>
);

const TabButton = ({ label, icon, isActive, onClick }: { label: string, icon: React.ReactNode, isActive: boolean, onClick: () => void }) => (
    <button 
        onClick={onClick} 
        className={`
            w-full sm:w-auto 
            flex items-center justify-center 
            gap-1.5 sm:gap-2 
            px-2 sm:px-4 py-2.5 
            rounded-xl 
            text-[10px] sm:text-xs md:text-sm font-bold 
            transition-all duration-300 
            ${isActive ? 'bg-gradient-to-r from-primary-start to-primary-end text-white shadow-lg shadow-primary-start/20' : 'text-text-secondary hover:bg-white/5 hover:text-white'}
        `}
    >
        <span className="shrink-0">{icon}</span>
        <span className="whitespace-nowrap">{label}</span>
    </button>
);

const SkeletonChart = () => (
    <div className="glass-panel rounded-2xl p-4 animate-pulse">
        <div className="h-6 bg-white/5 rounded w-1/3 mb-4"></div>
        <div className="h-64 bg-white/5 rounded"></div>
    </div>
);

const SkeletonGrid = () => (
     <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-pulse">
        <div className="glass-panel rounded-2xl p-4">
            <div className="h-6 bg-white/5 rounded w-1/2 mb-4"></div>
            <div className="h-64 bg-white/5 rounded"></div>
        </div>
        <div className="glass-panel rounded-2xl p-4">
            <div className="h-6 bg-white/5 rounded w-1/2 mb-4"></div>
            <div className="space-y-2 mt-4">
                <div className="h-8 bg-white/5 rounded"></div>
                <div className="h-8 bg-white/5 rounded"></div>
                <div className="h-8 bg-white/5 rounded"></div>
                <div className="h-8 bg-white/5 rounded"></div>
                <div className="h-8 bg-white/5 rounded"></div>
            </div>
        </div>
    </div>
);

export const FinanceTab: React.FC = () => {
    type ActiveTab = 'transactions' | 'reports' | 'history';

    const { t, i18n } = useTranslation();
    const navigate = useNavigate();
    const localeMap: { [key: string]: any } = { sq, al: sq, en: enUS };
    const currentLocale = localeMap[i18n.language] || enUS;

    const [loading, setLoading] = useState(true);
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [cases, setCases] = useState<Case[]>([]);
    const [activeTab, setActiveTab] = useState<ActiveTab>('transactions');
    const [openingDocId, setOpeningDocId] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [analyticsData, setAnalyticsData] = useState<AnalyticsDashboardData | null>(null);
    const [showInvoiceModal, setShowInvoiceModal] = useState(false);
    const [showExpenseModal, setShowExpenseModal] = useState(false);
    const [showArchiveInvoiceModal, setShowArchiveInvoiceModal] = useState(false);
    const [showArchiveExpenseModal, setShowArchiveExpenseModal] = useState(false);
    const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
    const [selectedExpenseId, setSelectedExpenseId] = useState<string | null>(null);
    const [selectedCaseForInvoice, setSelectedCaseForInvoice] = useState<string>("");
    const [editingInvoiceId, setEditingInvoiceId] = useState<string | null>(null);
    const [editingExpenseId, setEditingExpenseId] = useState<string | null>(null);
    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [viewingUrl, setViewingUrl] = useState<string | null>(null);
    const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);

    // PHOENIX: State for receipt scanning
    const [isScanningReceipt, setIsScanningReceipt] = useState(false);

    const [newInvoice, setNewInvoice] = useState({ 
        client_name: '', client_email: '', client_phone: '', client_address: '', 
        client_city: '', client_tax_id: '', client_website: '', 
        tax_rate: 18, notes: '', status: 'PAID', related_case_id: '' 
    });
    const [includeVat, setIncludeVat] = useState(true);

    const [lineItems, setLineItems] = useState<InvoiceItem[]>([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);
    const [newExpense, setNewExpense] = useState<ExpenseCreateRequest>({ category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0], related_case_id: '' });
    const [expenseDate, setExpenseDate] = useState<Date | null>(new Date());
    const [expenseReceipt, setExpenseReceipt] = useState<File | null>(null);
    const receiptInputRef = useRef<HTMLInputElement>(null);

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

    useEffect(() => {
        if (!includeVat) {
            setNewInvoice(prev => ({ ...prev, tax_rate: 0 }));
        } else if (newInvoice.tax_rate === 0) {
            setNewInvoice(prev => ({ ...prev, tax_rate: 18 }));
        }
    }, [includeVat]);

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
            const inCase = item.caseData.title.toLowerCase().includes(lowerTerm) || 
                           item.caseData.case_number.toLowerCase().includes(lowerTerm);
            const inActivity = item.activity.some(act => 
                (act.label && act.label.toLowerCase().includes(lowerTerm))
            );
            return inCase || inActivity;
        });
    }, [historyByCase, searchTerm, activeTab]);

    const getCategoryIcon = (category: string) => {
        const cat = category.toLowerCase();
        if (cat.includes('transport') || cat.includes('naft') || cat.includes('vetur') || cat.includes('fuel') || cat.includes('parking')) return <Car size={18} />;
        if (cat.includes('ushqim') || cat.includes('drek') || cat.includes('food') || cat.includes('restaurant')) return <Utensils size={18} />;
        if (cat.includes('kafe') || cat.includes('coffee')) return <Coffee size={18} />;
        if (cat.includes('zyr') || cat.includes('rent') || cat.includes('qira') || cat.includes('office')) return <Building size={18} />;
        if (cat.includes('pag') || cat.includes('rrog') || cat.includes('salary') || cat.includes('staff')) return <Users size={18} />;
        if (cat.includes('tatim') || cat.includes('taksa') || cat.includes('tax')) return <Landmark size={18} />;
        if (cat.includes('rrym') || cat.includes('drita') || cat.includes('energy')) return <Zap size={18} />;
        if (cat.includes('internet') || cat.includes('tel')) return <Wifi size={18} />;
        return <Receipt size={18} />;
    };

    const closePreview = () => { if (viewingUrl) window.URL.revokeObjectURL(viewingUrl); setViewingUrl(null); setViewingDoc(null); };
    const addLineItem = () => setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0, total: 0 }]);
    const removeLineItem = (i: number) => lineItems.length > 1 && setLineItems(lineItems.filter((_, idx) => idx !== i));
    const updateLineItem = (i: number, f: keyof InvoiceItem, v: any) => { const n = [...lineItems]; n[i] = { ...n[i], [f]: v }; n[i].total = n[i].quantity * n[i].unit_price; setLineItems(n); };
    
    // --- Invoice Handlers ---
    const handleEditInvoice = (invoice: Invoice) => { 
        setEditingInvoiceId(invoice.id); 
        setNewInvoice({ 
            client_name: invoice.client_name, 
            client_email: invoice.client_email || '', 
            client_address: invoice.client_address || '', 
            client_phone: (invoice as any).client_phone || '', 
            client_city: (invoice as any).client_city || '', 
            client_tax_id: (invoice as any).client_tax_id || '', 
            client_website: (invoice as any).client_website || '', 
            tax_rate: invoice.tax_rate, 
            notes: invoice.notes || '', 
            status: invoice.status,
            related_case_id: (invoice as any).related_case_id || '' 
        }); 
        setIncludeVat(invoice.tax_rate > 0);
        setLineItems(invoice.items); 
        setShowInvoiceModal(true); 
    };

    const handleCreateOrUpdateInvoice = async (e: React.FormEvent) => { 
        e.preventDefault(); 
        try { 
            const payload = { 
                client_name: newInvoice.client_name, 
                client_email: newInvoice.client_email, 
                client_address: newInvoice.client_address, 
                client_phone: newInvoice.client_phone, 
                client_city: newInvoice.client_city, 
                client_tax_id: newInvoice.client_tax_id, 
                client_website: newInvoice.client_website, 
                related_case_id: newInvoice.related_case_id, 
                items: lineItems, 
                tax_rate: includeVat ? newInvoice.tax_rate : 0, 
                notes: newInvoice.notes, 
                status: newInvoice.status 
            }; 
            if (editingInvoiceId) { 
                const u = await apiService.updateInvoice(editingInvoiceId, payload); 
                setInvoices(invoices.map(i => i.id === editingInvoiceId ? u : i)); 
            } else { 
                const n = await apiService.createInvoice(payload); 
                setInvoices([n, ...invoices]); 
            } 
            closeInvoiceModal(); 
        } catch { alert(t('error.generic')); } 
    };

    const closeInvoiceModal = () => { 
        setShowInvoiceModal(false); 
        setEditingInvoiceId(null); 
        setNewInvoice({ 
            client_name: '', client_email: '', client_phone: '', client_address: '', 
            client_city: '', client_tax_id: '', client_website: '', 
            tax_rate: 18, notes: '', status: 'PAID', related_case_id: '' 
        }); 
        setIncludeVat(true);
        setLineItems([{ description: '', quantity: 1, unit_price: 0, total: 0 }]); 
    };

    const deleteInvoice = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteInvoice(id); setInvoices(invoices.filter(inv => inv.id !== id)); } catch { alert(t('documentsPanel.deleteFailed')); } };
    const handleViewInvoice = async (invoice: Invoice) => { setOpeningDocId(invoice.id); try { const blob = await apiService.getInvoicePdfBlob(invoice.id, i18n.language || 'sq'); const url = window.URL.createObjectURL(blob); setViewingUrl(url); setViewingDoc({ id: invoice.id, file_name: `Invoice #${invoice.invoice_number}`, mime_type: 'application/pdf', status: 'READY' } as any); } catch { alert(t('error.generic')); } finally { setOpeningDocId(null); } };
    const downloadInvoice = async (id: string) => { try { await apiService.downloadInvoicePdf(id, i18n.language || 'sq'); } catch { alert(t('error.generic')); } };
    const handleArchiveInvoiceClick = (id: string) => { setSelectedInvoiceId(id); setShowArchiveInvoiceModal(true); };
    const submitArchiveInvoice = async () => { if (!selectedInvoiceId) return; try { await apiService.archiveInvoice(selectedInvoiceId, selectedCaseForInvoice || undefined); alert(t('general.saveSuccess')); setShowArchiveInvoiceModal(false); setSelectedCaseForInvoice(""); } catch { alert(t('error.generic')); } };

    // --- Expense Handlers ---
    const handleEditExpense = (expense: Expense) => { setEditingExpenseId(expense.id); setNewExpense({ category: expense.category, amount: expense.amount, description: expense.description || '', date: expense.date, related_case_id: expense.related_case_id || '' }); setExpenseDate(new Date(expense.date)); setShowExpenseModal(true); };
    const handleCreateOrUpdateExpense = async (e: React.FormEvent) => { e.preventDefault(); try { const payload = { ...newExpense, date: expenseDate ? expenseDate.toISOString().split('T')[0] : new Date().toISOString().split('T')[0] }; let s: Expense; if (editingExpenseId) { s = await apiService.updateExpense(editingExpenseId, payload); setExpenses(expenses.map(exp => exp.id === editingExpenseId ? s : exp)); } else { s = await apiService.createExpense(payload); setExpenses([s, ...expenses]); } if (expenseReceipt && s.id) { await apiService.uploadExpenseReceipt(s.id, expenseReceipt); const f = { ...s, receipt_url: "PENDING_REFRESH" }; setExpenses(prev => prev.map(exp => exp.id === f.id ? f : exp)); } closeExpenseModal(); } catch { alert(t('error.generic')); } };
    const closeExpenseModal = () => { setShowExpenseModal(false); setEditingExpenseId(null); setNewExpense({ category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0], related_case_id: '' }); setExpenseReceipt(null); setIsScanningReceipt(false); };
    const deleteExpense = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteExpense(id); setExpenses(expenses.filter(e => e.id !== id)); } catch { alert(t('error.generic')); } };
    
    // PHOENIX: Enhanced Receipt Upload with AI Auto-fill
    const handleReceiptUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        
        setExpenseReceipt(file);
        
        // Only run AI if not editing an existing expense (optional, but safer)
        if (!editingExpenseId) {
            setIsScanningReceipt(true);
            try {
                const aiResult = await apiService.analyzeExpenseReceipt(file);
                
                // Auto-fill fields if data found
                if (aiResult) {
                    setNewExpense(prev => ({
                        ...prev,
                        category: aiResult.category || prev.category,
                        amount: aiResult.amount || prev.amount,
                        description: aiResult.description || prev.description
                    }));
                    
                    if (aiResult.date) {
                        const parsedDate = new Date(aiResult.date);
                        if (!isNaN(parsedDate.getTime())) {
                            setExpenseDate(parsedDate);
                        }
                    }
                }
            } catch (err) {
                console.warn("AI Scan failed, falling back to manual entry", err);
                // Fail silently or show toast - user can still enter manually
            } finally {
                setIsScanningReceipt(false);
            }
        }
    };

    // --- Generate Digital Receipt ---
    const generateDigitalReceipt = (expense: Expense): File => {
        const content = `DËSHMI DIGJITALE E SHPENZIMIT (JURISTI AI)\n------------------------------------------------\n` +
                        `Kategoria:   ${expense.category}\n` +
                        `Shuma:       €${expense.amount.toFixed(2)}\n` +
                        `Data:        ${new Date(expense.date).toLocaleDateString('sq-AL')}\n` +
                        `Përshkrimi:  ${expense.description || 'Pa përshkrim'}\n` +
                        `Lënda:       ${expense.related_case_id ? (cases.find(c => c.id === expense.related_case_id)?.title || 'E panjohur') : 'Jo e specifikuar'}\n` +
                        `------------------------------------------------\n` +
                        `Gjeneruar më: ${new Date().toLocaleString('sq-AL')}`;
        const blob = new Blob([content], { type: 'text/plain' });
        return new File([blob], `Shpenzim_${expense.category.replace(/\s+/g, '_')}_${expense.date}.txt`, { type: 'text/plain' });
    };

    // --- VIEW EXPENSE ---
    const handleViewExpense = async (expense: Expense) => { 
        setOpeningDocId(expense.id); 
        try { 
            let url: string;
            let file_name: string;
            let mime_type: string;

            if (expense.receipt_url) {
                const { blob, filename } = await apiService.getExpenseReceiptBlob(expense.id); 
                url = window.URL.createObjectURL(blob); 
                file_name = filename;
                const ext = filename.split('.').pop()?.toLowerCase(); 
                mime_type = ext === 'pdf' ? 'application/pdf' : 'image/jpeg'; 
            } else {
                const file = generateDigitalReceipt(expense);
                url = window.URL.createObjectURL(file);
                file_name = file.name;
                mime_type = 'text/plain';
            }

            setViewingUrl(url); 
            setViewingDoc({ id: expense.id, file_name, mime_type, status: 'READY' } as any); 
        } catch { 
            alert(t('error.receiptNotFound', 'Gabim gjatë hapjes.')); 
        } finally { 
            setOpeningDocId(null); 
        } 
    };

    // --- DOWNLOAD EXPENSE ---
    const handleDownloadExpense = async (expense: Expense) => { 
        try { 
            let url: string;
            let filename: string;

            if (expense.receipt_url) {
                const { blob, filename: fn } = await apiService.getExpenseReceiptBlob(expense.id); 
                url = window.URL.createObjectURL(blob); 
                filename = fn;
            } else {
                const file = generateDigitalReceipt(expense);
                url = window.URL.createObjectURL(file);
                filename = file.name;
            }

            const a = document.createElement('a'); 
            a.href = url; 
            a.download = filename; 
            document.body.appendChild(a); 
            a.click(); 
            document.body.removeChild(a); 
            if (!expense.receipt_url) window.URL.revokeObjectURL(url);
        } catch { 
            alert(t('error.generic')); 
        } 
    };

    // --- ARCHIVE EXPENSE ---
    const handleArchiveExpenseClick = (id: string) => { 
        setSelectedExpenseId(id); 
        setShowArchiveExpenseModal(true); 
    };

    const submitArchiveExpense = async () => { 
        if (!selectedExpenseId) return; 
        try { 
            const ex = expenses.find(e => e.id === selectedExpenseId); 
            if (!ex) return; 
            
            let fileToUpload: File;

            if (ex.receipt_url) {
                const { blob, filename } = await apiService.getExpenseReceiptBlob(ex.id); 
                fileToUpload = new File([blob], filename, { type: blob.type }); 
            } else {
                fileToUpload = generateDigitalReceipt(ex);
            }

            await apiService.uploadArchiveItem(fileToUpload, fileToUpload.name, "EXPENSE", selectedCaseForInvoice || undefined, undefined); 
            alert(t('general.saveSuccess')); 
            setShowArchiveExpenseModal(false); 
            setSelectedCaseForInvoice(""); 
        } catch { 
            alert(t('error.generic')); 
        } 
    };

    if (loading) return <div className="flex justify-center h-64 items-center"><Loader2 className="animate-spin text-primary-start" /></div>;
    
    return (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <style>{`.custom-finance-scroll::-webkit-scrollbar { width: 6px; } .custom-finance-scroll::-webkit-scrollbar-track { background: transparent; } .custom-finance-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 10px; } .no-scrollbar::-webkit-scrollbar { display: none; } .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }`}</style>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 lg:h-[600px]">
                <div className="lg:col-span-1 flex flex-col gap-6 h-full">
                    {/* Overview Card */}
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

                    {/* Quick Actions */}
                    <div className="glass-panel rounded-3xl p-6 space-y-3 flex-1 flex flex-col justify-start">
                        <h3 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-2">{t('finance.quickActions')}</h3>
                        <QuickActionButton icon={<Plus size={18} />} label={t('finance.createInvoice')} onClick={() => setShowInvoiceModal(true)} color="text-emerald-400" />
                        <QuickActionButton icon={<MinusCircle size={18} />} label={t('finance.addExpense')} onClick={() => setShowExpenseModal(true)} color="text-rose-400" />
                        <QuickActionButton icon={<Calculator size={18} />} label={t('finance.monthlyClose')} onClick={() => navigate('/finance/wizard')} color="text-text-secondary" />
                    </div>
                </div>

                {/* Main Content Area */}
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
                                                    <div className={`p-2.5 rounded-xl ${tx.type === 'invoice' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                                                        {tx.type === 'invoice' ? <FileText size={20} /> : getCategoryIcon(tx.category)}
                                                    </div>
                                                    <div className="text-right">
                                                         <p className={`text-lg font-bold ${tx.type === 'invoice' ? 'text-emerald-400' : 'text-rose-400'}`}>
                                                            {tx.type === 'invoice' ? '+' : '-'}€{tx.type === 'invoice' ? tx.total_amount.toFixed(2) : tx.amount.toFixed(2)}
                                                        </p>
                                                        <span className="text-[10px] text-gray-500 font-mono">{new Date(tx.date).toLocaleDateString()}</span>
                                                    </div>
                                                </div>
                                                <h4 className="font-bold text-white text-sm truncate mb-1" title={tx.type === 'invoice' ? tx.client_name : tx.category}>
                                                    {tx.type === 'invoice' ? tx.client_name : tx.category}
                                                </h4>
                                                <p className="text-xs text-gray-400 truncate">
                                                    {tx.type === 'invoice' ? `#${tx.invoice_number}` : (tx.description || t('finance.noDescription'))}
                                                </p>
                                            </div>
                                            <div className="border-t border-white/5 p-2 flex items-center justify-end gap-1 bg-black/20">
                                                <button onClick={() => tx.type === 'invoice' ? handleEditInvoice(tx) : handleEditExpense(tx)} className="p-2 hover:bg-white/10 rounded-lg text-amber-400 transition-colors" title={t('general.edit')}><Edit2 size={14} /></button>
                                                <button onClick={() => tx.type === 'invoice' ? handleViewInvoice(tx) : handleViewExpense(tx)} disabled={(tx.type === 'expense' && !tx.receipt_url) && openingDocId !== tx.id && !openingDocId} className="p-2 hover:bg-white/10 rounded-lg text-blue-400 transition-colors disabled:opacity-50" title={t('general.view')}>{openingDocId === tx.id ? <Loader2 size={14} className="animate-spin"/> : <Eye size={14} />}</button>
                                                <button onClick={() => tx.type === 'invoice' ? downloadInvoice(tx.id) : handleDownloadExpense(tx)} className="p-2 hover:bg-white/10 rounded-lg text-green-400 transition-colors" title={t('general.download')}><Download size={14} /></button>
                                                <button onClick={() => tx.type === 'invoice' ? handleArchiveInvoiceClick(tx.id) : handleArchiveExpenseClick(tx.id)} className="p-2 hover:bg-white/10 rounded-lg text-indigo-400 transition-colors" title={t('general.archive')}><Archive size={14} /></button>
                                                <button onClick={() => tx.type === 'invoice' ? deleteInvoice(tx.id) : deleteExpense(tx.id)} className="p-2 hover:bg-white/10 rounded-lg text-red-400 transition-colors" title={t('general.delete')}><Trash2 size={14} /></button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        
                        {/* (Reports and History sections omitted for brevity but preserved in structure) */}
                        {activeTab === 'reports' && (<div className="h-full overflow-y-auto custom-finance-scroll pr-2 space-y-6">{!analyticsData ? <div className="space-y-6"><SkeletonChart /><SkeletonGrid /></div> : (<><div className="glass-panel rounded-2xl p-4"><h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2"><TrendingUp size={16} className="text-primary-start"/> {t('finance.analytics.salesTrend')}</h4><div className="h-64 w-full min-h-[250px]"><ResponsiveContainer width="100%" height="100%"><AreaChart data={analyticsData.sales_trend}><defs><linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/><stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" /><XAxis dataKey="date" stroke="#6b7280" fontSize={12} tickFormatter={(str) => str.slice(5)} tick={{fill: '#9ca3af'}} /><YAxis stroke="#6b7280" fontSize={12} tick={{fill: '#9ca3af'}} width={40} /><Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: 'rgba(255,255,255,0.1)', color: '#f3f4f6', borderRadius: '12px' }} formatter={(value: any) => [`€${Number(value).toFixed(2)}`, t('finance.income')]} labelStyle={{ color: '#9ca3af', marginBottom: '4px' }} /><Area type="monotone" dataKey="amount" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorSales)" /></AreaChart></ResponsiveContainer></div></div><div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-2"><div className="glass-panel rounded-2xl p-4"><h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2"><BarChart2 size={16} className="text-success-start" /> {t('finance.analytics.topProducts')}</h4><div className="h-64 w-full min-h-[250px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={analyticsData.top_products} layout="vertical"><CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={true} vertical={false} /><XAxis type="number" stroke="#6b7280" fontSize={12} hide /><YAxis dataKey="product_name" type="category" stroke="#9ca3af" fontSize={12} width={100} tick={{fill: '#e5e7eb', fontSize: 12}} /><Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: 'rgba(255,255,255,0.1)', color: '#f3f4f6', borderRadius: '12px' }} formatter={(value: any) => [`€${Number(value).toFixed(2)}`, t('finance.analytics.tableValue')]} /><Bar dataKey="total_revenue" fill="#10b981" radius={[0, 4, 4, 0]} barSize={20}>{analyticsData.top_products.map((_: TopProductItem, index: number) => (<Cell key={`cell-${index}`} fill={['#34d399', '#60a5fa', '#fbbf24', '#f87171', '#a78bfa'][index % 5]} />))}</Bar></BarChart></ResponsiveContainer></div></div><div className="glass-panel rounded-2xl p-4 flex flex-col"><h4 className="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4 flex items-center gap-2"><FileText size={16} className="text-blue-400" /> {t('finance.analytics.productDetails')}</h4><div className="overflow-y-auto max-h-64 custom-finance-scroll pr-2 flex-1"><table className="w-full text-sm text-left text-gray-300"><thead className="text-xs text-gray-400 uppercase bg-white/5 sticky top-0 backdrop-blur-sm"><tr><th className="px-3 py-2 rounded-tl-lg">{t('finance.analytics.tableProduct')}</th><th className="px-3 py-2 text-right">{t('finance.analytics.tableQty')}</th><th className="px-3 py-2 text-right rounded-tr-lg">{t('finance.analytics.tableValue')}</th></tr></thead><tbody className="divide-y divide-white/5">{analyticsData.top_products.map((p: TopProductItem, i: number) => (<tr key={i} className="hover:bg-white/5 transition-colors"><td className="px-3 py-2 font-medium text-white truncate max-w-[120px]" title={p.product_name}>{p.product_name}</td><td className="px-3 py-2 text-right font-mono text-gray-400">{p.total_quantity}</td><td className="px-3 py-2 text-right font-bold text-emerald-400">€{p.total_revenue.toFixed(2)}</td></tr>))}</tbody></table></div></div></div></>)}</div>)}
                        {activeTab === 'history' && (<div className="flex flex-col h-full space-y-4"><div className="relative flex-none"><div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Search className="h-5 w-5 text-gray-500" /></div><input type="text" placeholder={t('header.searchPlaceholder') || "Kërko..."} className="glass-input w-full pl-10 pr-3 py-2.5 rounded-xl" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} /></div><div className="space-y-4 flex-1 overflow-y-auto custom-finance-scroll pr-2">{filteredHistory.length === 0 ? (<div className="flex justify-center items-center h-full text-gray-500 text-center flex-col"><div className="bg-white/5 p-4 rounded-full mb-3"><Briefcase size={32} className="text-gray-600" /></div><p className="font-bold text-gray-400">{t('finance.noHistoryData', "Nuk ka të dhëna historike")}</p><p className="text-sm max-w-xs mt-2">{t('finance.historyHelper', "Shtoni shpenzime ose fatura të lidhura me lëndë për të parë pasqyrën këtu.")}</p></div>) : (filteredHistory.map((item) => (<div key={item.caseData.id} className="bg-white/5 border border-white/10 rounded-xl overflow-hidden"><div className="p-4 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors" onClick={() => setExpandedCaseId(expandedCaseId === item.caseData.id ? null : item.caseData.id)}><div className="flex items-center gap-3"><div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg"><Briefcase size={18} /></div><div><h4 className="font-bold text-white text-sm">{item.caseData.title}</h4><p className="text-xs text-gray-500">{item.caseData.case_number}</p></div></div><div className="flex items-center gap-4"><div className="text-right"><p className="text-xs text-gray-400 uppercase">{t('finance.balance', 'Bilanci')}</p><p className={`font-bold ${item.balance >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{item.balance >= 0 ? '+' : ''}€{item.balance.toFixed(2)}</p></div>{expandedCaseId === item.caseData.id ? <ChevronDown size={18} className="text-gray-500"/> : <ChevronRight size={18} className="text-gray-500"/>}</div></div>{expandedCaseId === item.caseData.id && (<div className="bg-black/20 p-4 border-t border-white/5 space-y-2"><h5 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('finance.details', 'Detajet Financiare')}</h5>{item.activity.map((act, idx) => (<div key={`${act.type}-${idx}`} className="flex justify-between items-center text-sm py-1 border-b border-white/5 last:border-0"><div className="flex items-center gap-3"><span className="text-gray-400 text-xs font-mono">{new Date(act.date).toLocaleDateString('sq-AL')}</span><div className="flex flex-col"><span className="text-white font-medium">{act.label || act.type}</span><span className={`text-[10px] uppercase ${act.type === 'invoice' ? 'text-emerald-500/70' : 'text-rose-500/70'}`}>{act.type === 'invoice' ? t('finance.invoice') : t('finance.expense')}</span></div></div><span className={`${act.type === 'invoice' ? 'text-emerald-400' : 'text-rose-400'} font-mono`}>{act.type === 'invoice' ? '+' : '-'}€{act.amount.toFixed(2)}</span></div>))}</div>)}</div>)))}</div></div>)}
                    </div>
                </div>
            </div>
            
            {showInvoiceModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="glass-high w-full max-w-2xl max-h-[90vh] overflow-y-auto p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200 custom-finance-scroll"><div className="flex justify-between items-center mb-6"><h2 className="text-2xl font-bold text-white">{editingInvoiceId ? t('finance.editInvoice') : t('finance.createInvoice')}</h2><button onClick={closeInvoiceModal} className="text-gray-400 hover:text-white"><X size={24} /></button></div><form onSubmit={handleCreateOrUpdateInvoice} className="space-y-6"><div className="space-y-4">
                <h3 className="text-xs font-bold text-primary-start uppercase tracking-wider flex items-center gap-2 mb-4"><User size={16} /> {t('caseCard.client')}</h3><div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel', "Lënda e Lidhur")}</label><select value={newInvoice.related_case_id} onChange={e => setNewInvoice({...newInvoice, related_case_id: e.target.value})} className="glass-input w-full px-4 py-2.5 rounded-xl"><option value="">-- {t('finance.noCase', 'Pa Lëndë')} --</option>{cases.map(c => <option key={c.id} value={c.id} className="bg-gray-900">{c.title}</option>)}</select></div><div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.clientName', 'Emri')}</label><input required type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={newInvoice.client_name} onChange={e => setNewInvoice({...newInvoice, client_name: e.target.value})} /></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.publicEmail')}</label><input type="email" className="glass-input w-full px-4 py-2.5 rounded-xl" value={newInvoice.client_email} onChange={e => setNewInvoice({...newInvoice, client_email: e.target.value})} /></div><div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.phone')}</label><input type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={newInvoice.client_phone} onChange={e => setNewInvoice({...newInvoice, client_phone: e.target.value})} /></div></div><div className="grid grid-cols-1 sm:grid-cols-2 gap-4"><div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.city')}</label><input type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={newInvoice.client_city} onChange={e => setNewInvoice({...newInvoice, client_city: e.target.value})} /></div><div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.taxId')}</label><input type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={newInvoice.client_tax_id} onChange={e => setNewInvoice({...newInvoice, client_tax_id: e.target.value})} /></div></div><div><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('business.address')}</label><input type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={newInvoice.client_address} onChange={e => setNewInvoice({...newInvoice, client_address: e.target.value})} /></div><div className="flex items-center gap-3 bg-white/5 p-3 rounded-xl border border-white/10"><input type="checkbox" id="vatToggle" checked={includeVat} onChange={(e) => setIncludeVat(e.target.checked)} className="w-4 h-4 text-primary-start rounded border-gray-300 focus:ring-primary-start" /><label htmlFor="vatToggle" className="text-sm text-gray-300 cursor-pointer select-none">Apliko TVSH (18%)</label></div></div><div className="space-y-3 pt-6 border-t border-white/10"><h3 className="text-xs font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><FileText size={16} /> {t('finance.services')}</h3>{lineItems.map((item, index) => (<div key={index} className="flex flex-col sm:flex-row gap-2 items-center"><input type="text" placeholder={t('finance.description')} className="flex-1 w-full glass-input px-3 py-2 rounded-xl" value={item.description} onChange={e => updateLineItem(index, 'description', e.target.value)} required /><input type="number" placeholder={t('finance.qty')} className="w-full sm:w-20 glass-input px-3 py-2 rounded-xl" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', parseFloat(e.target.value))} min="1" /><input type="number" placeholder={t('finance.price')} className="w-full sm:w-24 glass-input px-3 py-2 rounded-xl" value={item.unit_price} onChange={e => updateLineItem(index, 'unit_price', parseFloat(e.target.value))} min="0" /><button type="button" onClick={() => removeLineItem(index)} className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg self-end sm:self-center"><Trash2 size={18} /></button></div>))}<button type="button" onClick={addLineItem} className="text-sm text-primary-start hover:underline flex items-center gap-1 font-medium"><Plus size={14} /> {t('finance.addLine')}</button></div><div className="flex justify-end gap-3 pt-4"><button type="button" onClick={closeInvoiceModal} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10 transition-colors">{t('general.cancel')}</button><button type="submit" className="px-8 py-2.5 bg-gradient-to-r from-success-start to-success-end text-white rounded-xl font-bold shadow-lg shadow-success-start/20 hover:scale-[1.02] transition-transform">{t('general.save')}</button></div></form></div></div>)}
            
            {showExpenseModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="glass-high w-full max-w-md p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold text-white flex items-center gap-2">
                                <MinusCircle size={20} className="text-rose-500" /> {editingExpenseId ? t('finance.editExpense') : t('finance.addExpense')}
                            </h2>
                            <button onClick={closeExpenseModal} className="text-gray-400 hover:text-white"><X size={24} /></button>
                        </div>
                        
                        {/* PHOENIX: Enhanced Receipt Upload UI */}
                        <div className="mb-6">
                            <input type="file" ref={receiptInputRef} className="hidden" accept="image/*,.pdf" onChange={handleReceiptUpload} />
                            <button 
                                onClick={() => receiptInputRef.current?.click()} 
                                disabled={isScanningReceipt}
                                className={`w-full py-4 border border-dashed rounded-xl flex items-center justify-center gap-2 transition-all 
                                    ${expenseReceipt ? 'bg-primary-start/10 border-primary-start text-primary-300' : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10'}
                                    ${isScanningReceipt ? 'cursor-wait opacity-80' : ''}`}
                            >
                                {isScanningReceipt ? (
                                    <><Loader2 size={18} className="animate-spin" /> Analizimi i faturës me AI...</>
                                ) : expenseReceipt ? (
                                    <><CheckCircle size={18} /> {expenseReceipt.name}</>
                                ) : (
                                    <><Paperclip size={18} /> {t('finance.attachReceipt')}</>
                                )}
                            </button>
                            {isScanningReceipt && <p className="text-center text-[10px] text-gray-500 mt-2 flex items-center justify-center gap-1"><Sparkles size={10} className="text-primary-start"/> Duke nxjerrë të dhënat automatikisht...</p>}
                        </div>

                        <form onSubmit={handleCreateOrUpdateExpense} className="space-y-5">
                            <div>
                                <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel', "Lënda e Lidhur")}</label>
                                <select value={newExpense.related_case_id} onChange={e => setNewExpense({...newExpense, related_case_id: e.target.value})} className="glass-input w-full px-4 py-2.5 rounded-xl">
                                    <option value="">-- {t('finance.noCase', 'Pa Lëndë')} --</option>
                                    {cases.map(c => <option key={c.id} value={c.id} className="bg-gray-900">{c.title}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.expenseCategory')}</label>
                                <input required type="text" className="glass-input w-full px-4 py-2.5 rounded-xl" value={newExpense.category} onChange={e => setNewExpense({...newExpense, category: e.target.value})} />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.amount')}</label>
                                <input required type="number" step="0.01" className="glass-input w-full px-4 py-2.5 rounded-xl" value={newExpense.amount} onChange={e => setNewExpense({...newExpense, amount: parseFloat(e.target.value)})} />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.date')}</label>
                                <DatePicker selected={expenseDate} onChange={(date: Date | null) => setExpenseDate(date)} locale={currentLocale} dateFormat="dd/MM/yyyy" className="glass-input w-full px-4 py-2.5 rounded-xl" required />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('finance.description')}</label>
                                <textarea rows={2} className="glass-input w-full px-4 py-2.5 rounded-xl resize-none" value={newExpense.description} onChange={e => setNewExpense({...newExpense, description: e.target.value})} />
                            </div>
                            <div className="flex justify-end gap-3 pt-4">
                                <button type="button" onClick={closeExpenseModal} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10 transition-colors">{t('general.cancel')}</button>
                                <button type="submit" className="px-8 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl font-bold shadow-lg shadow-rose-500/20">{t('general.save')}</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
            
            {showArchiveInvoiceModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="glass-high w-full max-w-md p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200"><h2 className="text-xl font-bold text-white mb-6">{t('finance.archiveInvoice')}</h2><div className="mb-8"><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel')}</label><select className="glass-input w-full px-4 py-2.5 rounded-xl" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">{t('archive.generalNoCase')}</option>{cases.map(c => (<option key={c.id} value={c.id} className="bg-gray-900">{c.title}</option>))}</select></div><div className="flex justify-end gap-3"><button onClick={() => setShowArchiveInvoiceModal(false)} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10">{t('general.cancel')}</button><button onClick={submitArchiveInvoice} className="px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold shadow-lg">{t('general.save')}</button></div></div></div>)}
            {showArchiveExpenseModal && (<div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"><div className="glass-high w-full max-w-md p-8 rounded-3xl animate-in fade-in zoom-in-95 duration-200"><h2 className="text-xl font-bold text-white mb-6">{t('finance.archiveExpenseTitle')}</h2><div className="mb-8"><label className="block text-xs text-gray-400 mb-1 font-bold uppercase">{t('drafting.selectCaseLabel')}</label><select className="glass-input w-full px-4 py-2.5 rounded-xl" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">{t('archive.generalNoCase')}</option>{cases.map(c => (<option key={c.id} value={c.id} className="bg-gray-900">{c.title}</option>))}</select></div><div className="flex justify-end gap-3"><button onClick={() => setShowArchiveExpenseModal(false)} className="px-6 py-2.5 rounded-xl text-text-secondary hover:text-white hover:bg-white/10">{t('general.cancel')}</button><button onClick={submitArchiveExpense} className="px-8 py-2.5 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold shadow-lg">{t('general.save')}</button></div></div></div>)}

            {viewingDoc && <PDFViewerModal documentData={viewingDoc} onClose={closePreview} onMinimize={closePreview} t={t} directUrl={viewingUrl} />}
        </motion.div>
    );
};