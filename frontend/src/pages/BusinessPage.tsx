// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - FINANCE LOGIC REPAIR
// 1. MATH FIX: Income now includes ALL invoices (Paid + Draft + Sent) to reflect total value immediately.
// 2. CLEANUP: Removed unused 'Bot', 'AccountantModal' states to clear build warnings.
// 3. UI: Added 'Expense List' section to visualize and delete expenses.

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Building2, Mail, Phone, MapPin, Globe, Palette, Save, Upload, Loader2, 
    CreditCard, FileText, Plus, Download, Trash2, FolderOpen, File,
    Briefcase, Eye, Archive, Camera, X, User, FolderPlus, Home, ChevronRight,
    FileImage, FileCode, Hash, Info, Calendar, TrendingUp, TrendingDown, Wallet, MinusCircle
} from 'lucide-react';
import { apiService, API_V1_URL, Expense, ExpenseCreateRequest } from '../services/api';
import { BusinessProfile, BusinessProfileUpdate, Invoice, InvoiceItem, ArchiveItemOut, Case, Document } from '../data/types';
import { useTranslation } from 'react-i18next';
import PDFViewerModal from '../components/PDFViewerModal';

type ActiveTab = 'profile' | 'finance' | 'archive';

type Breadcrumb = {
    id: string | null;
    name: string;
    type: 'ROOT' | 'CASE' | 'FOLDER';
};

const DEFAULT_COLOR = '#3b82f6';

const BusinessPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const archiveInputRef = useRef<HTMLInputElement>(null);

  // Logo State
  const [logoSrc, setLogoSrc] = useState<string | null>(null);
  const [logoLoading, setLogoLoading] = useState(false);

  // Data
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]); 
  const [archiveItems, setArchiveItems] = useState<ArchiveItemOut[]>([]);
  const [cases, setCases] = useState<Case[]>([]);

  // --- ARCHIVE STATE ---
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([{ id: null, name: t('business.archive'), type: 'ROOT' }]);
  const [isUploading, setIsUploading] = useState(false);
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null);
  
  // Modals
  const [showFolderModal, setShowFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [showExpenseModal, setShowExpenseModal] = useState(false); 
  const [showArchiveInvoiceModal, setShowArchiveInvoiceModal] = useState(false);
  
  // Selection
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [selectedCaseForInvoice, setSelectedCaseForInvoice] = useState<string>("");

  // Viewer
  const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);

  // Forms
  const [formData, setFormData] = useState<BusinessProfileUpdate>({
    firm_name: '', email_public: '', phone: '', address: '', city: '', website: '', tax_id: '', branding_color: DEFAULT_COLOR
  });
  
  const [newInvoice, setNewInvoice] = useState({ 
      client_name: '', client_email: '', client_phone: '', client_address: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: 18, notes: '' 
  });
  const [lineItems, setLineItems] = useState<InvoiceItem[]>([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);

  const [newExpense, setNewExpense] = useState<ExpenseCreateRequest>({
      category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0]
  });

  // --- FINANCIAL CALCULATIONS (FIXED) ---
  // Count ALL invoices (Draft, Sent, Paid) as "Revenue" for the dashboard view
  const totalIncome = invoices.reduce((sum, inv) => sum + inv.total_amount, 0);
  const totalExpenses = expenses.reduce((sum, exp) => sum + exp.amount, 0);
  const totalBalance = totalIncome - totalExpenses;

  // --- INITIAL LOAD ---
  useEffect(() => { fetchData(); }, []);

  useEffect(() => {
      setBreadcrumbs(prev => {
          if (prev.length > 0 && prev[0].type === 'ROOT') {
              const newCrumbs = [...prev];
              newCrumbs[0].name = t('business.archive');
              return newCrumbs;
          }
          return prev;
      });
  }, [t]);

  useEffect(() => {
      if (activeTab === 'archive') fetchArchiveContent();
  }, [breadcrumbs, activeTab]);

  // Logo Fetcher
  useEffect(() => {
    const url = profile?.logo_url;
    if (url) {
        if (url.startsWith('blob:') || url.startsWith('data:')) { setLogoSrc(url); return; }
        setLogoLoading(true);
        apiService.fetchImageBlob(url)
            .then(blob => setLogoSrc(URL.createObjectURL(blob)))
            .catch(() => {
                if (!url.startsWith('http')) {
                    const cleanBase = API_V1_URL.endsWith('/') ? API_V1_URL.slice(0, -1) : API_V1_URL;
                    const cleanPath = url.startsWith('/') ? url.slice(1) : url;
                    setLogoSrc(`${cleanBase}/${cleanPath}`);
                } else { setLogoSrc(url); }
            })
            .finally(() => setLogoLoading(false));
    }
  }, [profile?.logo_url]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [profileData, invoiceData, expenseData, casesData] = await Promise.all([
          apiService.getBusinessProfile(),
          apiService.getInvoices().catch(() => []),
          apiService.getExpenses().catch(() => []), 
          apiService.getCases().catch(() => []) 
      ]);
      setProfile(profileData);
      setInvoices(invoiceData);
      setExpenses(expenseData);
      setCases(casesData);
      setFormData({
        firm_name: profileData.firm_name || '', email_public: profileData.email_public || '', phone: profileData.phone || '',
        address: profileData.address || '', city: profileData.city || '', website: profileData.website || '',
        tax_id: profileData.tax_id || '', branding_color: profileData.branding_color || DEFAULT_COLOR
      });
    } catch (error) { console.error("Failed to load data:", error); } finally { setLoading(false); }
  };

  // --- ARCHIVE LOGIC ---
  const getCurrentContext = () => {
      const caseCrumb = breadcrumbs.find(b => b.type === 'CASE');
      const caseId = caseCrumb ? caseCrumb.id : undefined;
      const active = breadcrumbs[breadcrumbs.length - 1];
      const parentId = active.type === 'FOLDER' ? active.id : undefined;
      return { caseId, parentId };
  };

  const fetchArchiveContent = async () => {
      const active = breadcrumbs[breadcrumbs.length - 1];
      setLoading(true);
      try {
          if (active.type === 'ROOT') {
              const items = await apiService.getArchiveItems(undefined, undefined, "null");
              setArchiveItems(items);
          } 
          else if (active.type === 'CASE') {
              const items = await apiService.getArchiveItems(undefined, active.id!, "null");
              setArchiveItems(items);
          }
          else if (active.type === 'FOLDER') {
              const items = await apiService.getArchiveItems(undefined, undefined, active.id!);
              setArchiveItems(items);
          }
      } catch (error) {
          console.error("Archive fetch failed:", error);
      } finally {
          setLoading(false);
      }
  };

  const handleNavigate = (_: Breadcrumb, index: number) => {
      setBreadcrumbs(prev => prev.slice(0, index + 1));
  };

  const handleEnterFolder = (folderId: string, folderName: string, type: 'FOLDER' | 'CASE') => {
      setBreadcrumbs(prev => [...prev, { id: folderId, name: folderName, type }]);
  };

  const handleCreateFolder = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!newFolderName.trim()) return;
      const { caseId, parentId } = getCurrentContext();
      try {
          await apiService.createArchiveFolder(newFolderName, parentId || undefined, caseId || undefined);
          setNewFolderName("");
          setShowFolderModal(false);
          fetchArchiveContent(); 
      } catch (error) { alert(t('error.generic')); }
  };

  const handleSmartUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setIsUploading(true);
      const { caseId, parentId } = getCurrentContext();
      try {
          let category = "GENERAL";
          const nameLower = file.name.toLowerCase();
          if (nameLower.includes("fatura")) category = "INVOICE";
          else if (nameLower.includes("kontrata")) category = "CONTRACT";
          await apiService.uploadArchiveItem(file, file.name, category, caseId || undefined, parentId || undefined);
          fetchArchiveContent(); 
      } catch (error) { alert(t('error.uploadFailed')); } 
      finally { setIsUploading(false); if (archiveInputRef.current) archiveInputRef.current.value = ''; }
  };

  // --- DRAG AND DROP HANDLERS ---
  const onDragStart = (e: React.DragEvent, id: string) => {
      e.dataTransfer.effectAllowed = 'move';
      setDraggedItemId(id);
      const img = new Image();
      img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'; 
      e.dataTransfer.setDragImage(img, 0, 0);
  };

  const onDragOver = (e: React.DragEvent) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
  };

  const onDrop = (e: React.DragEvent, targetId: string) => {
      e.preventDefault();
      if (!draggedItemId || draggedItemId === targetId) return;

      const draggedIndex = archiveItems.findIndex(i => i.id === draggedItemId);
      const targetIndex = archiveItems.findIndex(i => i.id === targetId);
      if (draggedIndex === -1 || targetIndex === -1) return;

      const newItems = [...archiveItems];
      const [movedItem] = newItems.splice(draggedIndex, 1);
      newItems.splice(targetIndex, 0, movedItem);
      setArchiveItems(newItems);
      setDraggedItemId(null);
  };

  const onDragEnd = () => { setDraggedItemId(null); };

  // --- VIEWER & ACTIONS ---
  const getMimeType = (fileType: string, fileName: string) => {
      const ext = fileName.split('.').pop()?.toLowerCase() || '';
      if (fileType === 'PDF' || ext === 'pdf') return 'application/pdf';
      if (['PNG', 'JPG', 'JPEG', 'WEBP', 'GIF'].includes(fileType) || ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext)) return 'image/jpeg';
      if (['TXT', 'MD', 'LOG', 'CSV', 'JSON'].includes(fileType) || ['txt', 'md', 'log', 'csv', 'json'].includes(ext)) return 'text/plain';
      return 'application/octet-stream';
  };

  const getFileIcon = (fileType: string) => {
      const ft = fileType.toUpperCase();
      if (ft === 'PDF') return <FileText className="w-5 h-5 text-red-400" />;
      if (['PNG', 'JPG', 'JPEG'].includes(ft)) return <FileImage className="w-5 h-5 text-purple-400" />;
      if (['JSON', 'JS', 'TS'].includes(ft)) return <FileCode className="w-5 h-5 text-yellow-400" />;
      return <File className="w-5 h-5 text-blue-400" />;
  };

  const handleViewItem = async (item: ArchiveItemOut) => {
      try {
          const blob = await apiService.getArchiveFileBlob(item.id);
          const url = window.URL.createObjectURL(blob);
          const mime = getMimeType(item.file_type, item.title);
          setViewingUrl(url);
          setViewingDoc({ id: item.id, file_name: item.title, mime_type: mime, status: 'READY' } as any);
      } catch (error) { alert(t('error.generic')); }
  };

  const handleViewInvoice = async (invoice: Invoice) => {
      try {
          const blob = await apiService.getInvoicePdfBlob(invoice.id);
          const url = window.URL.createObjectURL(blob);
          setViewingUrl(url);
          setViewingDoc({ id: invoice.id, file_name: `Invoice #${invoice.invoice_number}`, mime_type: 'application/pdf', status: 'READY' } as any);
      } catch (error) { alert(t('error.generic')); }
  };

  const closePreview = () => { if (viewingUrl) window.URL.revokeObjectURL(viewingUrl); setViewingUrl(null); setViewingDoc(null); };
  const deleteArchiveItem = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteArchiveItem(id); fetchArchiveContent(); } catch (error) { alert(t('documentsPanel.deleteFailed')); } };
  const downloadArchiveItem = async (id: string, title: string) => { try { await apiService.downloadArchiveItem(id, title); } catch (error) { alert(t('error.generic')); } };

  // --- HANDLERS ---
  const handleProfileSubmit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true); try { const clean: any = {...formData}; Object.keys(clean).forEach(k => clean[k]=== '' && (clean[k]=null)); await apiService.updateBusinessProfile(clean); alert(t('settings.successMessage')); } catch{ alert(t('error.generic')); } finally { setSaving(false); } };
  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if(!f) return; setSaving(true); try { const p = await apiService.uploadBusinessLogo(f); setProfile(p); } catch { alert(t('business.logoUploadFailed')); } finally { setSaving(false); } };
  const handleArchiveInvoiceClick = (invoiceId: string) => { setSelectedInvoiceId(invoiceId); setShowArchiveInvoiceModal(true); };
  const submitArchiveInvoice = async () => { if (!selectedInvoiceId) return; try { await apiService.archiveInvoice(selectedInvoiceId, selectedCaseForInvoice || undefined); alert(t('general.saveSuccess')); setShowArchiveInvoiceModal(false); setSelectedCaseForInvoice(""); } catch (error) { alert(t('error.generic')); } };
  const addLineItem = () => setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0, total: 0 }]);
  const removeLineItem = (i: number) => lineItems.length > 1 && setLineItems(lineItems.filter((_, idx) => idx !== i));
  const updateLineItem = (i: number, f: keyof InvoiceItem, v: any) => { const n = [...lineItems]; n[i] = { ...n[i], [f]: v }; n[i].total = n[i].quantity * n[i].unit_price; setLineItems(n); };
  
  const handleCreateInvoice = async (e: React.FormEvent) => { 
      e.preventDefault(); 
      try { 
          const fullAddressBlock = [
              newInvoice.client_address,
              newInvoice.client_city,
              newInvoice.client_phone ? `Tel: ${newInvoice.client_phone}` : '',
              newInvoice.client_tax_id ? `NUI: ${newInvoice.client_tax_id}` : '',
              newInvoice.client_website
          ].filter(Boolean).join('\n');

          const payload = { 
              client_name: newInvoice.client_name, 
              client_email: newInvoice.client_email, 
              client_address: fullAddressBlock, 
              items: lineItems, 
              tax_rate: newInvoice.tax_rate, 
              notes: newInvoice.notes 
          }; 
          
          const inv = await apiService.createInvoice(payload); 
          setInvoices([inv, ...invoices]); 
          setShowInvoiceModal(false); 
          setNewInvoice({ 
              client_name: '', client_email: '', client_phone: '', client_address: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: 18, notes: '' 
          }); 
          setLineItems([{ description: '', quantity: 1, unit_price: 0, total: 0 }]); 
      } catch { 
          alert(t('error.generic')); 
      } 
  };

  const handleCreateExpense = async (e: React.FormEvent) => {
      e.preventDefault();
      try {
          const expense = await apiService.createExpense(newExpense);
          setExpenses([expense, ...expenses]);
          setShowExpenseModal(false);
          setNewExpense({ category: '', amount: 0, description: '', date: new Date().toISOString().split('T')[0] });
      } catch {
          alert(t('error.generic'));
      }
  };

  const deleteExpense = async (id: string) => {
      if(!window.confirm(t('general.confirmDelete'))) return;
      try {
          await apiService.deleteExpense(id);
          setExpenses(expenses.filter(e => e.id !== id));
      } catch {
          alert(t('error.generic'));
      }
  };

  const deleteInvoice = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteInvoice(id); setInvoices(invoices.filter(inv => inv.id !== id)); } catch (error) { alert(t('documentsPanel.deleteFailed')); } };
  const downloadInvoice = async (id: string) => { try { await apiService.downloadInvoicePdf(id, i18n.language); } catch (error) { alert(t('error.generic')); } };

  if (loading && activeTab !== 'archive') return <div className="flex justify-center items-center h-96"><Loader2 className="w-8 h-8 animate-spin text-primary-start" /></div>;

  const currentView = breadcrumbs[breadcrumbs.length - 1];

  // --- COMPONENT: FINANCE CARD ---
  const FinanceCard = ({ title, amount, icon, color, subtext }: { title: string, amount: string, icon: React.ReactNode, color: string, subtext?: string }) => (
    <div className="group relative overflow-hidden rounded-2xl bg-gray-900/40 backdrop-blur-md border border-white/5 p-6 hover:bg-gray-800/60 transition-all duration-300 hover:-translate-y-1 shadow-lg">
        <div className={`absolute top-0 left-0 w-1 h-full ${color}`} />
        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110">
            {icon}
        </div>
        <div className="relative z-10">
            <div className="flex items-center gap-3 mb-4">
                <div className={`p-2.5 rounded-xl bg-white/5 border border-white/10 ${color.replace('bg-', 'text-')}`}>
                    {icon}
                </div>
                <h3 className="text-gray-400 text-sm font-medium uppercase tracking-wider">{title}</h3>
            </div>
            <p className="text-2xl sm:text-3xl font-bold text-white tracking-tight">{amount}</p>
            {subtext && <p className="text-xs text-gray-500 mt-2 font-mono">{subtext}</p>}
        </div>
    </div>
  );

  // --- COMPONENT: RICH ARCHIVE CARD ---
  const ArchiveCard = ({ 
      title, subtitle, type, date, icon, statusColor, onClick, onDownload, onDelete, isFolder, isDragging 
  }: { 
      title: string, subtitle: string, type: string, date: string, icon: React.ReactNode, statusColor: string, 
      onClick: () => void, onDownload?: () => void, onDelete?: () => void, isFolder: boolean, isDragging?: boolean 
  }) => (
    <div 
        onClick={onClick}
        className={`
            group relative flex flex-col justify-between h-full min-h-[14rem] p-6 rounded-2xl transition-all duration-300 cursor-pointer
            bg-gray-900/40 backdrop-blur-md border border-white/5 shadow-xl hover:shadow-2xl hover:bg-gray-800/60
            ${isDragging ? 'opacity-30 scale-95 border-dashed border-white/50' : ''}
            hover:-translate-y-1 hover:scale-[1.01]
        `}
    >
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
        <div>
            <div className="flex flex-col mb-4 relative z-10">
                <div className="flex justify-between items-start gap-2">
                    <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 group-hover:scale-110 transition-transform duration-300">
                        {icon}
                    </div>
                    <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${statusColor} shadow-[0_0_8px_currentColor]`} />
                </div>
                <div className="mt-4">
                    <h2 className="text-lg font-bold text-gray-100 line-clamp-2 leading-tight tracking-tight group-hover:text-primary-start transition-colors break-words" title={title}>{title}</h2>
                    <div className="flex items-center gap-2 mt-2">
                         <Calendar className="w-3 h-3 text-gray-600 flex-shrink-0" /><p className="text-xs text-gray-500 font-medium truncate">{isFolder ? t('archive.created') + ':' : t('archive.uploaded') + ':'} <span className="text-gray-400">{date}</span></p>
                    </div>
                </div>
            </div>
            <div className="flex flex-col mb-6 relative z-10">
                <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/5">
                    <Info className="w-3 h-3 text-indigo-400" /><span className="text-xs font-bold text-gray-300 uppercase tracking-wider">{isFolder ? t('archive.contents') : t('archive.details')}</span>
                </div>
                <div className="space-y-1.5 pl-1">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-200">
                        {isFolder ? <FolderOpen className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" /> : <FileText className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />}<span className="truncate">{type}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                        <Hash className="w-3 h-3 flex-shrink-0" /><span className="truncate">{subtitle}</span>
                    </div>
                </div>
            </div>
        </div>
        <div className="relative z-10 pt-4 border-t border-white/5 flex items-center justify-between min-h-[3rem]">
            <span className="text-xs font-medium text-indigo-400 group-hover:text-indigo-300 transition-colors flex items-center gap-1">{isFolder ? t('archive.openFolder') : ''}</span>
            <div className="flex gap-1 items-center">
                {!isFolder && (<button onClick={(e) => { e.stopPropagation(); onClick(); }} className="p-2 rounded-lg text-gray-600 hover:text-blue-400 hover:bg-blue-400/10 transition-colors" title={t('archive.view')}><Eye className="h-4 w-4" /></button>)}
                {!isFolder && onDownload && (<button onClick={(e) => { e.stopPropagation(); onDownload(); }} className="p-2 rounded-lg text-gray-600 hover:text-green-400 hover:bg-green-400/10 transition-colors" title={t('archive.download')}><Download className="h-4 w-4" /></button>)}
                {onDelete && (<button onClick={(e) => { e.stopPropagation(); onDelete(); }} className="p-2 -mr-2 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-400/10 transition-colors" title={t('archive.delete')}><Trash2 className="h-4 w-4" /></button>)}
            </div>
        </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-10 gap-6">
        <div><h1 className="text-3xl font-bold text-white mb-2">{t('business.title')}</h1><p className="text-gray-400">{t('business.subtitle')}</p></div>
        <div className="flex bg-background-light/10 p-1.5 rounded-2xl border border-white/10 backdrop-blur-md">
            <button onClick={() => setActiveTab('profile')} className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${activeTab === 'profile' ? 'bg-primary-start text-white shadow-lg scale-105' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}><Building2 size={18} /><span>{t('business.profile')}</span></button>
            <button onClick={() => setActiveTab('finance')} className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${activeTab === 'finance' ? 'bg-primary-start text-white shadow-lg scale-105' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}><FileText size={18} /><span>{t('business.finance')}</span></button>
            <button onClick={() => setActiveTab('archive')} className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${activeTab === 'archive' ? 'bg-primary-start text-white shadow-lg scale-105' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}><FolderOpen size={18} /><span>{t('business.archive')}</span></button>
        </div>
      </div>

      {/* --- PROFILE TAB --- */}
      {activeTab === 'profile' && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="space-y-8">
                <div className="bg-background-dark border border-glass-edge rounded-3xl p-8 flex flex-col items-center shadow-xl relative overflow-hidden group">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-primary-start to-primary-end" />
                    <h3 className="text-white font-bold mb-8 self-start text-lg">{t('business.logoIdentity')}</h3>
                    <div className="relative group cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                        <div className={`w-40 h-40 rounded-full overflow-hidden flex items-center justify-center border-4 transition-all shadow-2xl ${logoSrc ? 'border-white/20' : 'border-dashed border-gray-700 hover:border-primary-start'}`}>
                            {logoLoading ? <Loader2 className="w-10 h-10 animate-spin text-primary-start" /> : logoSrc ? <img src={logoSrc} alt="Logo" className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-500" onError={() => setLogoSrc(null)} /> : <div className="text-center group-hover:scale-110 transition-transform"><Upload className="w-10 h-10 text-gray-600 mx-auto mb-2" /><span className="text-xs text-gray-500 font-bold uppercase tracking-wider">{t('business.upload')}</span></div>}
                        </div>
                        <div className="absolute inset-0 rounded-full bg-black/60 backdrop-blur-[2px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300"><Camera className="w-10 h-10 text-white drop-shadow-lg" /></div>
                    </div>
                    <input type="file" ref={fileInputRef} onChange={handleLogoUpload} className="hidden" accept="image/*" />
                </div>
                <div className="bg-background-dark border border-glass-edge rounded-3xl p-8 shadow-xl relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-pink-500 to-purple-600" />
                    <h3 className="text-white font-bold mb-6 flex items-center gap-2"><Palette className="w-5 h-5 text-purple-400" /> {t('business.branding')}</h3>
                    <div className="flex items-center gap-4 mb-6">
                        <div className="relative overflow-hidden w-16 h-16 rounded-2xl border-2 border-white/10 shadow-inner"><input type="color" value={formData.branding_color || DEFAULT_COLOR} onChange={(e) => setFormData({...formData, branding_color: e.target.value})} className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] cursor-pointer" /></div>
                        <div className="flex-1"><div className="relative"><span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono text-lg">#</span><input type="text" value={(formData.branding_color || DEFAULT_COLOR).replace('#', '')} onChange={(e) => setFormData({...formData, branding_color: `#${e.target.value}`})} className="w-full bg-background-light/50 border border-glass-edge rounded-xl pl-8 pr-4 py-3 text-white font-mono uppercase focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                    </div>
                    <button className="w-full py-3 rounded-xl text-white font-bold text-sm shadow-lg transition-transform active:scale-95 flex items-center justify-center gap-2" style={{ backgroundColor: formData.branding_color || DEFAULT_COLOR }}><Save className="w-4 h-4" />{t('business.saveColor')}</button>
                </div>
            </div>
            
            <div className="md:col-span-2">
                <form onSubmit={handleProfileSubmit} className="bg-background-dark border border-glass-edge rounded-3xl p-8 space-y-8 shadow-xl h-full relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-blue-500 to-cyan-500" />
                    <h3 className="text-xl font-bold text-white flex items-center gap-3"><Briefcase className="w-6 h-6 text-primary-start" />{t('business.firmData')}</h3>
                    <div className="grid grid-cols-1 gap-6">
                        <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.firmNameLabel')}</label><div className="relative"><Building2 className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="firm_name" value={formData.firm_name} onChange={(e) => setFormData({...formData, firm_name: e.target.value})} className="w-full bg-background-light/50 border border-glass-edge rounded-xl pl-12 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" placeholder={t('business.firmNamePlaceholder')} /></div></div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.publicEmail')}</label><div className="relative"><Mail className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="email" name="email_public" value={formData.email_public} onChange={(e) => setFormData({...formData, email_public: e.target.value})} className="w-full bg-background-light/50 border border-glass-edge rounded-xl pl-12 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                            <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.phone')}</label><div className="relative"><Phone className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="phone" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} className="w-full bg-background-light/50 border border-glass-edge rounded-xl pl-12 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                        </div>
                        <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.address')}</label><div className="relative"><MapPin className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="address" value={formData.address} onChange={(e) => setFormData({...formData, address: e.target.value})} className="w-full bg-background-light/50 border border-glass-edge rounded-xl pl-12 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.city')}</label><input type="text" name="city" value={formData.city} onChange={(e) => setFormData({...formData, city: e.target.value})} className="w-full bg-background-light/50 border border-glass-edge rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div>
                            <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.website')}</label><div className="relative"><Globe className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="website" value={formData.website} onChange={(e) => setFormData({...formData, website: e.target.value})} className="w-full bg-background-light/50 border border-glass-edge rounded-xl pl-12 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                        </div>
                        <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.taxId')}</label><div className="relative"><CreditCard className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="tax_id" value={formData.tax_id} onChange={(e) => setFormData({...formData, tax_id: e.target.value})} className="w-full bg-background-light/50 border border-glass-edge rounded-xl pl-12 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                    </div>
                    <div className="pt-8 flex justify-end mt-auto"><button type="submit" disabled={saving} className="flex items-center gap-2 px-10 py-3.5 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold hover:shadow-lg hover:shadow-primary-start/20 transition-all disabled:opacity-50 hover:scale-[1.02] active:scale-95">{saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}{t('general.save')}</button></div>
                </form>
            </div>
        </motion.div>
      )}

      {/* --- FINANCE TAB --- */}
      {activeTab === 'finance' && (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-8">
            
            {/* PHOENIX: Financial Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                <FinanceCard 
                    title={t('finance.income')} 
                    amount={`€${totalIncome.toFixed(2)}`} 
                    icon={<TrendingUp className="w-6 h-6" />} 
                    color="bg-emerald-500" 
                    subtext={t('finance.incomeSub')}
                />
                <FinanceCard 
                    title={t('finance.expense')} 
                    amount={`€${totalExpenses.toFixed(2)}`} 
                    icon={<TrendingDown className="w-6 h-6" />} 
                    color="bg-rose-500" 
                    subtext={t('finance.expenseSub')}
                />
                <FinanceCard 
                    title={t('finance.balance')} 
                    amount={`€${totalBalance.toFixed(2)}`} 
                    icon={<Wallet className="w-6 h-6" />} 
                    color="bg-blue-500" 
                    subtext={t('finance.balanceSub')}
                />
            </div>

            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <h2 className="text-2xl font-bold text-white">{t('finance.invoicesTitle')}</h2>
                <div className="flex gap-3 w-full sm:w-auto">
                    {/* PHOENIX: Add Expense Button */}
                    <button onClick={() => setShowExpenseModal(true)} className="flex-1 sm:flex-none justify-center flex items-center gap-2 px-5 py-3 bg-rose-600 hover:bg-rose-700 text-white rounded-xl shadow-lg transition-all font-medium">
                        <MinusCircle size={20} /> <span>{t('finance.addExpense')}</span>
                    </button>
                    {/* Create Invoice Button */}
                    <button onClick={() => setShowInvoiceModal(true)} className="flex-1 sm:flex-none justify-center flex items-center gap-2 px-5 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl shadow-lg transition-all font-medium">
                        <Plus size={20} /> <span>{t('finance.createInvoice')}</span>
                    </button>
                </div>
            </div>

            {/* EXPENSE LIST SECTION (NEW) - To visualize and manage expenses */}
            {expenses.length > 0 && (
                <div className="bg-background-dark border border-glass-edge rounded-3xl p-6 shadow-xl mb-8">
                    <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2"><MinusCircle className="text-rose-500" size={20} /> {t('finance.expense')}</h3>
                    <div className="divide-y divide-white/5">
                        {expenses.map(exp => (
                            <div key={exp.id} className="py-3 flex justify-between items-center group hover:bg-white/5 px-2 rounded-lg transition-colors">
                                <div>
                                    <p className="text-white font-bold">{exp.category}</p>
                                    <p className="text-gray-400 text-xs">{exp.description} • {new Date(exp.date).toLocaleDateString()}</p>
                                </div>
                                <div className="flex items-center gap-4">
                                    <p className="text-rose-400 font-mono font-bold">-€{exp.amount.toFixed(2)}</p>
                                    <button onClick={() => deleteExpense(exp.id)} className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"><Trash2 size={16} /></button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {invoices.length === 0 ? (
                <div className="text-center py-20 bg-background-dark border border-glass-edge rounded-3xl"><FileText className="w-16 h-16 text-gray-700 mx-auto mb-4" /><p className="text-gray-400 text-lg">{t('finance.noInvoices')}</p></div>
            ) : (
                <div className="grid gap-4">
                    {invoices.map(inv => (
                        <div key={inv.id} className="bg-background-dark border border-glass-edge rounded-2xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 hover:border-white/20 transition-all group">
                            <div className="flex items-center gap-5 w-full md:w-auto overflow-hidden">
                                <div className={`p-3.5 rounded-xl flex-shrink-0 ${inv.status === 'PAID' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                                    <FileText size={28} />
                                </div>
                                <div className="min-w-0">
                                    <h3 className="font-bold text-white text-lg truncate pr-2">{inv.client_name}</h3>
                                    <p className="text-sm text-gray-400 font-mono truncate">{inv.invoice_number} • {new Date(inv.issue_date).toLocaleDateString()}</p>
                                </div>
                            </div>
                            
                            <div className="flex items-center justify-between w-full md:w-auto gap-4 md:gap-8 mt-2 md:mt-0">
                                <div className="text-left md:text-right">
                                    <p className="text-xl font-bold text-white">€{inv.total_amount.toFixed(2)}</p>
                                    <span className={`inline-block text-[10px] px-2.5 py-1 rounded-full font-bold tracking-wide uppercase mt-1 ${inv.status === 'PAID' ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-500/20' : 'bg-amber-900/30 text-amber-400 border border-amber-500/20'}`}>
                                        {inv.status}
                                    </span>
                                </div>
                                
                                <div className="flex gap-1 sm:gap-2">
                                    <button onClick={() => handleViewInvoice(inv)} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-gray-400 hover:text-blue-400 transition-colors" title={t('finance.viewPdf')}><Eye size={18} /></button>
                                    <button onClick={() => downloadInvoice(inv.id)} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-gray-400 hover:text-green-400 transition-colors" title={t('finance.downloadPdf')}><Download size={18} /></button>
                                    <button onClick={() => handleArchiveInvoiceClick(inv.id)} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-gray-400 hover:text-indigo-400 transition-colors" title={t('finance.archiveInvoice')}><Archive size={18} /></button>
                                    <button onClick={() => deleteInvoice(inv.id)} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-gray-400 hover:text-red-400 transition-colors" title={t('finance.deleteInvoice')}><Trash2 size={18} /></button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </motion.div>
      )}

      {/* --- ARCHIVE TAB (NEW CASE CARD STYLE) --- */}
      {activeTab === 'archive' && (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-8">
            {/* Toolbar */}
            <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center bg-white/5 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-2xl">
                    <div className="flex items-center gap-2 overflow-x-auto text-sm no-scrollbar px-2 py-1">
                        {breadcrumbs.map((crumb, index) => (
                            <React.Fragment key={crumb.id || 'root'}>
                                <button onClick={() => handleNavigate(crumb, index)} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${index === breadcrumbs.length - 1 ? 'bg-primary-start/20 text-primary-start font-bold border border-primary-start/20 shadow-inner' : 'text-gray-400 hover:text-white hover:bg-white/10'}`}>
                                    {crumb.type === 'ROOT' ? <Home size={14} /> : crumb.type === 'CASE' ? <Briefcase size={14} /> : <FolderOpen size={14} />}
                                    {crumb.name}
                                </button>
                                {index < breadcrumbs.length - 1 && <ChevronRight size={14} className="text-gray-600 flex-shrink-0" />}
                            </React.Fragment>
                        ))}
                    </div>
                    <div className="flex gap-2 flex-shrink-0 p-1">
                        <button onClick={() => setShowFolderModal(true)} className="flex items-center gap-2 px-4 py-2 bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 hover:text-amber-400 rounded-xl border border-amber-500/30 transition-all font-bold text-xs uppercase tracking-wide">
                            <FolderPlus size={16} /> <span className="hidden sm:inline">{t('archive.createFolder')}</span>
                        </button>
                        <div className="relative">
                            <input type="file" ref={archiveInputRef} className="hidden" onChange={handleSmartUpload} />
                            <button onClick={() => archiveInputRef.current?.click()} disabled={isUploading} className="flex items-center gap-2 px-4 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl shadow-lg shadow-primary-start/20 transition-all font-bold text-xs uppercase tracking-wide disabled:opacity-50 disabled:cursor-wait">
                                {isUploading ? <Loader2 className="animate-spin w-4 h-4" /> : <Upload size={16} />} <span className="hidden sm:inline">{t('archive.upload')}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* CONTENT GRID - RICH CARDS */}
            <div className="space-y-10">
                {currentView.type === 'ROOT' && cases.length > 0 && (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 ml-2 flex items-center gap-2 opacity-70"><Briefcase size={14} /> {t('archive.caseFolders')}</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {cases.map(c => (
                                <div key={c.id} className="h-full">
                                    <ArchiveCard title={c.title || `Rasti #${c.case_number}`} subtitle={c.case_number || 'Pa numër'} type="Dosje Çështjeje" date={new Date(c.created_at).toLocaleDateString()} icon={<Briefcase className="w-5 h-5 text-indigo-400" />} statusColor="bg-indigo-400" isFolder={true} onClick={() => handleEnterFolder(c.id, c.title, 'CASE')} />
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                    {(currentView.type !== 'ROOT' || archiveItems.length > 0) && (
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 ml-2 flex items-center gap-2 opacity-70"><FolderOpen size={14} /> {currentView.type === 'ROOT' ? t('archive.myDocuments') : t('archive.contents')}</h3>
                    )}
                    {archiveItems.length === 0 && currentView.type !== 'ROOT' ? (
                        <div className="text-center py-24 border-2 border-dashed border-white/5 rounded-3xl bg-white/[0.02] flex flex-col items-center justify-center">
                            <div className="p-6 bg-white/5 rounded-full mb-4 animate-pulse"><FolderOpen className="w-16 h-16 text-gray-600" /></div>
                            <p className="text-gray-300 font-medium text-lg">{t('archive.emptyFolder')}</p>
                            <p className="text-sm text-gray-500 mt-2">{t('archive.emptyHint')}</p>
                        </div>
                    ) : (
                        <motion.div layout className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            <AnimatePresence>
                            {archiveItems.map(item => {
                                const isFolder = (item as any).item_type === 'FOLDER';
                                const fileExt = item.file_type || 'FILE';
                                const isDragging = draggedItemId === item.id;
                                return (
                                    <motion.div layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} transition={{ type: "spring", stiffness: 300, damping: 25 }} key={item.id} draggable onDragStart={(e) => onDragStart(e as any, item.id)} onDragOver={onDragOver} onDrop={(e) => onDrop(e as any, item.id)} onDragEnd={onDragEnd} className="h-full">
                                        <ArchiveCard title={item.title} subtitle={isFolder ? t('archive.caseFolders') : `${fileExt} Dokument`} type={isFolder ? 'Folder' : fileExt} date={new Date().toLocaleDateString()} icon={isFolder ? <FolderOpen className="w-5 h-5 text-amber-500" /> : getFileIcon(fileExt)} statusColor={isFolder ? 'bg-amber-400' : 'bg-blue-400'} isFolder={isFolder} isDragging={isDragging} onClick={() => isFolder ? handleEnterFolder(item.id, item.title, 'FOLDER') : handleViewItem(item)} onDownload={() => downloadArchiveItem(item.id, item.title)} onDelete={() => deleteArchiveItem(item.id)} />
                                    </motion.div>
                                );
                            })}
                            </AnimatePresence>
                        </motion.div>
                    )}
                </div>
            </div>
        </motion.div>
      )}

      {/* --- CREATE FOLDER MODAL --- */}
      {showFolderModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
              <div className="bg-background-dark border border-glass-edge rounded-3xl w-full max-w-sm p-8 shadow-2xl scale-100">
                  <div className="flex justify-between items-center mb-6">
                      <h3 className="text-xl font-bold text-white">{t('archive.newFolderTitle')}</h3>
                      <button onClick={() => setShowFolderModal(false)} className="text-gray-500 hover:text-white"><X size={24}/></button>
                  </div>
                  <form onSubmit={handleCreateFolder}>
                      <div className="relative mb-8">
                          <FolderOpen className="absolute left-4 top-3.5 w-6 h-6 text-amber-500" />
                          <input autoFocus type="text" value={newFolderName} onChange={(e) => setNewFolderName(e.target.value)} placeholder={t('archive.folderNamePlaceholder')} className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3.5 text-white text-lg focus:ring-2 focus:ring-amber-500/50 outline-none transition-all placeholder:text-gray-600" />
                      </div>
                      <div className="flex justify-end gap-3"><button type="button" onClick={() => setShowFolderModal(false)} className="px-6 py-3 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-colors font-medium">{t('general.cancel')}</button><button type="submit" className="px-8 py-3 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-white rounded-xl font-bold shadow-lg shadow-amber-500/20 transition-all transform hover:scale-[1.02]">{t('general.create')}</button></div>
                  </form>
              </div>
          </div>
      )}

      {/* --- CREATE INVOICE MODAL --- */}
      {showInvoiceModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-2xl [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-gray-700 [&::-webkit-scrollbar-thumb]:rounded-full">
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-white">{t('finance.createInvoice')}</h2>
                    <button onClick={() => setShowInvoiceModal(false)} className="text-gray-400 hover:text-white"><X size={24} /></button>
                  </div>
                  <form onSubmit={handleCreateInvoice} className="space-y-6">
                      <div className="space-y-4">
                          <h3 className="text-sm font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><User size={16} /> {t('caseCard.client')}</h3>
                          <div><label className="block text-sm text-gray-300 mb-1">Emri</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_name} onChange={e => setNewInvoice({...newInvoice, client_name: e.target.value})} /></div>
                          <div className="grid grid-cols-2 gap-4">
                              <div><label className="block text-sm text-gray-300 mb-1">Email</label><input type="email" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_email} onChange={e => setNewInvoice({...newInvoice, client_email: e.target.value})} /></div>
                              <div><label className="block text-sm text-gray-300 mb-1">Telefon</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_phone} onChange={e => setNewInvoice({...newInvoice, client_phone: e.target.value})} /></div>
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                              <div><label className="block text-sm text-gray-300 mb-1">{t('business.city')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_city} onChange={e => setNewInvoice({...newInvoice, client_city: e.target.value})} /></div>
                              <div><label className="block text-sm text-gray-300 mb-1">{t('business.taxId')}</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_tax_id} onChange={e => setNewInvoice({...newInvoice, client_tax_id: e.target.value})} placeholder="NUI / Fiscal No." /></div>
                          </div>
                          <div><label className="block text-sm text-gray-300 mb-1">{t('business.website')} <span className="text-gray-500 text-xs">(Opsional)</span></label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_website} onChange={e => setNewInvoice({...newInvoice, client_website: e.target.value})} /></div>
                          <div><label className="block text-sm text-gray-300 mb-1">Adresa</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_address} onChange={e => setNewInvoice({...newInvoice, client_address: e.target.value})} /></div>
                      </div>
                      <div className="space-y-3 pt-4 border-t border-white/10">
                          <h3 className="text-sm font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><FileText size={16} /> Shërbimet</h3>
                          {lineItems.map((item, index) => (
                              <div key={index} className="flex gap-2 items-center">
                                  <input type="text" placeholder="Përshkrimi" className="flex-1 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.description} onChange={e => updateLineItem(index, 'description', e.target.value)} required />
                                  <input type="number" placeholder="Sasia" className="w-20 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', parseFloat(e.target.value))} min="1" />
                                  <input type="number" placeholder="Çmimi" className="w-24 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.unit_price} onChange={e => updateLineItem(index, 'unit_price', parseFloat(e.target.value))} min="0" />
                                  <button type="button" onClick={() => removeLineItem(index)} className="p-2 text-red-400 hover:bg-red-900/20 rounded-lg"><Trash2 size={18} /></button>
                              </div>
                          ))}
                          <button type="button" onClick={addLineItem} className="text-sm text-primary-start hover:underline flex items-center gap-1"><Plus size={14} /> Shto Rresht</button>
                      </div>
                      <div className="flex justify-end gap-3"><button type="button" onClick={() => setShowInvoiceModal(false)} className="px-4 py-2 text-gray-400">{t('general.cancel')}</button><button type="submit" className="px-6 py-2 bg-green-600 text-white rounded-lg font-bold">{t('general.create')}</button></div>
                  </form>
              </div>
          </div>
      )}

      {/* --- CREATE EXPENSE MODAL --- */}
      {showExpenseModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6 shadow-2xl">
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-white flex items-center gap-2"><MinusCircle size={20} className="text-rose-500" /> {t('finance.addExpense')}</h2>
                    <button onClick={() => setShowExpenseModal(false)} className="text-gray-400 hover:text-white"><X size={24} /></button>
                  </div>
                  <form onSubmit={handleCreateExpense} className="space-y-5">
                      <div><label className="block text-sm text-gray-300 mb-1">{t('finance.expenseCategory')}</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.category} onChange={e => setNewExpense({...newExpense, category: e.target.value})} placeholder="psh. Qira, Rrogat" /></div>
                      <div><label className="block text-sm text-gray-300 mb-1">{t('finance.amount')}</label><input required type="number" step="0.01" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.amount} onChange={e => setNewExpense({...newExpense, amount: parseFloat(e.target.value)})} /></div>
                      <div><label className="block text-sm text-gray-300 mb-1">{t('finance.date')}</label><input required type="date" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.date} onChange={e => setNewExpense({...newExpense, date: e.target.value})} /></div>
                      <div><label className="block text-sm text-gray-300 mb-1">{t('finance.description')}</label><textarea rows={3} className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newExpense.description} onChange={e => setNewExpense({...newExpense, description: e.target.value})} /></div>
                      <div className="flex justify-end gap-3 pt-4"><button type="button" onClick={() => setShowExpenseModal(false)} className="px-4 py-2 text-gray-400">{t('general.cancel')}</button><button type="submit" className="px-6 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-bold">{t('general.save')}</button></div>
                  </form>
              </div>
          </div>
      )}

      {showArchiveInvoiceModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6 shadow-2xl">
                  <h2 className="text-xl font-bold text-white mb-4">{t('finance.archiveInvoice')}</h2>
                  <div className="space-y-3 mb-6"><label className="block text-sm text-gray-400 mb-1">{t('drafting.selectCaseLabel')}</label><select className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-start" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">Të Përgjithshme (Pa Dosje)</option>{cases.map(c => (<option key={c.id} value={c.id}>{c.title}</option>))}</select></div>
                  <div className="flex justify-end gap-3"><button onClick={() => setShowArchiveInvoiceModal(false)} className="px-4 py-2 text-gray-400 hover:text-white">{t('general.cancel')}</button><button onClick={submitArchiveInvoice} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold">{t('general.save')}</button></div>
              </div>
          </div>
      )}

      {viewingDoc && <PDFViewerModal documentData={viewingDoc} onClose={closePreview} t={t} directUrl={viewingUrl} />}
    </div>
  );
};

export default BusinessPage;