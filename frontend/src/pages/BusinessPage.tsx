// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - RESTORATION COMPLETE
// 1. RECOVERY: Restored the full Profile and Finance tab logic (Forms, Modals, State Handlers).
// 2. INTEGRATION: Combined with the new Glassmorphic Archive V2 UI.
// 3. CLEANUP: Verified every import and state variable is actually used in the JSX.

import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { 
    Building2, Mail, Phone, MapPin, Globe, Palette, Save, Upload, Loader2, 
    CreditCard, FileText, Plus, Download, Trash2, FolderOpen, File,
    Briefcase, Eye, Archive, Camera, Check, Bot, X, User, FolderPlus, Home, ChevronRight,
    FileImage, FileCode
} from 'lucide-react';
import { apiService, API_V1_URL } from '../services/api';
import { BusinessProfile, BusinessProfileUpdate, Invoice, InvoiceItem, ArchiveItemOut, Case, Document } from '../data/types';
import { useTranslation } from 'react-i18next';
import PDFViewerModal from '../components/PDFViewerModal';

type ActiveTab = 'profile' | 'finance' | 'archive';

// Breadcrumb Node Definition
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
  const [archiveItems, setArchiveItems] = useState<ArchiveItemOut[]>([]);
  const [cases, setCases] = useState<Case[]>([]);

  // --- ARCHIVE STATE ---
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([{ id: null, name: 'Arkiva', type: 'ROOT' }]);
  const [isUploading, setIsUploading] = useState(false);
  const [draggedItemId, setDraggedItemId] = useState<string | null>(null);
  
  // Modals
  const [showFolderModal, setShowFolderModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [showArchiveInvoiceModal, setShowArchiveInvoiceModal] = useState(false);
  const [showAccountantModal, setShowAccountantModal] = useState(false);
  
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

  // --- INITIAL LOAD ---
  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
      if (activeTab === 'archive') {
          fetchArchiveContent();
      }
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
      const [profileData, invoiceData, casesData] = await Promise.all([
          apiService.getBusinessProfile(),
          apiService.getInvoices().catch(() => []),
          apiService.getCases().catch(() => []) 
      ]);
      setProfile(profileData);
      setInvoices(invoiceData);
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
      } catch (error) { alert("Krijimi i dosjes dështoi."); }
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
      } catch (error) { alert("Ngarkimi dështoi."); } 
      finally { setIsUploading(false); if (archiveInputRef.current) archiveInputRef.current.value = ''; }
  };

  // --- DRAG AND DROP HANDLERS ---
  const onDragStart = (e: React.DragEvent, id: string) => {
      e.dataTransfer.effectAllowed = 'move';
      setDraggedItemId(id);
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
      if (ft === 'PDF') return <FileText className="w-8 h-8 text-red-400" />;
      if (['PNG', 'JPG', 'JPEG'].includes(ft)) return <FileImage className="w-8 h-8 text-purple-400" />;
      if (['JSON', 'JS', 'TS'].includes(ft)) return <FileCode className="w-8 h-8 text-yellow-400" />;
      if (['TXT', 'MD'].includes(ft)) return <FileText className="w-8 h-8 text-gray-400" />;
      return <File className="w-8 h-8 text-blue-400" />;
  };

  const handleViewItem = async (item: ArchiveItemOut) => {
      try {
          const blob = await apiService.getArchiveFileBlob(item.id);
          const url = window.URL.createObjectURL(blob);
          const mime = getMimeType(item.file_type, item.title);
          setViewingUrl(url);
          setViewingDoc({ id: item.id, file_name: item.title, mime_type: mime, status: 'READY' } as any);
      } catch (error) { alert("Nuk mund të hapet dokumenti."); }
  };

  const handleViewInvoice = async (invoice: Invoice) => {
      try {
          const blob = await apiService.getInvoicePdfBlob(invoice.id);
          const url = window.URL.createObjectURL(blob);
          setViewingUrl(url);
          setViewingDoc({ id: invoice.id, file_name: `Invoice #${invoice.invoice_number}`, mime_type: 'application/pdf', status: 'READY' } as any);
      } catch (error) { alert("Nuk mund të hapet fatura."); }
  };

  const closePreview = () => { if (viewingUrl) window.URL.revokeObjectURL(viewingUrl); setViewingUrl(null); setViewingDoc(null); };
  const deleteArchiveItem = async (id: string) => { if(!window.confirm("A jeni i sigurt?")) return; try { await apiService.deleteArchiveItem(id); fetchArchiveContent(); } catch (error) { alert("Fshirja dështoi."); } };
  const downloadArchiveItem = async (id: string, title: string) => { try { await apiService.downloadArchiveItem(id, title); } catch (error) { alert("Shkarkimi dështoi."); } };

  // --- HANDLERS (Profile & Finance) ---
  const handleProfileSubmit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true); try { const clean: any = {...formData}; Object.keys(clean).forEach(k => clean[k]=== '' && (clean[k]=null)); await apiService.updateBusinessProfile(clean); alert(t('settings.successMessage')); } catch{ alert(t('error.generic')); } finally { setSaving(false); } };
  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if(!f) return; setSaving(true); try { const p = await apiService.uploadBusinessLogo(f); setProfile(p); } catch { alert(t('error.uploadFailed')); } finally { setSaving(false); } };
  
  const handleArchiveInvoiceClick = (invoiceId: string) => { setSelectedInvoiceId(invoiceId); setShowArchiveInvoiceModal(true); };
  const submitArchiveInvoice = async () => { if (!selectedInvoiceId) return; try { await apiService.archiveInvoice(selectedInvoiceId, selectedCaseForInvoice || undefined); alert("Fatura u arkivua me sukses!"); setShowArchiveInvoiceModal(false); setSelectedCaseForInvoice(""); } catch (error) { alert("Arkivimi dështoi."); } };
  
  const addLineItem = () => setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0, total: 0 }]);
  const removeLineItem = (i: number) => lineItems.length > 1 && setLineItems(lineItems.filter((_, idx) => idx !== i));
  const updateLineItem = (i: number, f: keyof InvoiceItem, v: any) => { const n = [...lineItems]; n[i] = { ...n[i], [f]: v }; n[i].total = n[i].quantity * n[i].unit_price; setLineItems(n); };
  
  const handleCreateInvoice = async (e: React.FormEvent) => { 
      e.preventDefault(); 
      try { 
          const addr = [newInvoice.client_address, newInvoice.client_city, newInvoice.client_phone ? `Tel: ${newInvoice.client_phone}` : '', newInvoice.client_tax_id ? `NUI: ${newInvoice.client_tax_id}` : ''].filter(Boolean).join('\n'); 
          const payload = { client_name: newInvoice.client_name, client_email: newInvoice.client_email, client_address: addr, items: lineItems, tax_rate: newInvoice.tax_rate, notes: newInvoice.notes }; 
          const inv = await apiService.createInvoice(payload); 
          setInvoices([inv, ...invoices]); 
          setShowInvoiceModal(false); 
          setNewInvoice({ client_name: '', client_email: '', client_phone: '', client_address: '', client_city: '', client_tax_id: '', client_website: '', tax_rate: 18, notes: '' }); 
          setLineItems([{ description: '', quantity: 1, unit_price: 0, total: 0 }]); 
      } catch { alert("Dështoi."); } 
  };
  
  const deleteInvoice = async (id: string) => { if(!window.confirm(t('general.confirmDelete', "A jeni i sigurt?"))) return; try { await apiService.deleteInvoice(id); setInvoices(invoices.filter(inv => inv.id !== id)); } catch (error) { alert("Fshirja dështoi."); } };
  const downloadInvoice = async (id: string) => { try { await apiService.downloadInvoicePdf(id, i18n.language); } catch (error) { alert("Shkarkimi dështoi."); } };

  if (loading && activeTab !== 'archive') return <div className="flex justify-center items-center h-96"><Loader2 className="w-8 h-8 animate-spin text-primary-start" /></div>;

  const currentView = breadcrumbs[breadcrumbs.length - 1];

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div><h1 className="text-3xl font-bold text-white mb-2">{t('business.title', 'Zyra Ime')}</h1><p className="text-gray-400">Qendra Administrative për Zyrën tuaj Ligjore.</p></div>
        <div className="flex bg-background-light/20 p-1 rounded-xl border border-glass-edge">
            <button onClick={() => setActiveTab('profile')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'profile' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><Building2 className="w-4 h-4 inline-block mr-2" />Profili</button>
            <button onClick={() => setActiveTab('finance')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'finance' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><FileText className="w-4 h-4 inline-block mr-2" />Financat</button>
            <button onClick={() => setActiveTab('archive')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'archive' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><FolderOpen className="w-4 h-4 inline-block mr-2" />Arkiva</button>
        </div>
      </div>

      {/* --- PROFILE TAB --- */}
      {activeTab === 'profile' && (
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="space-y-8">
                <div className="bg-background-dark border border-glass-edge rounded-2xl p-6 flex flex-col items-center shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-primary-start to-primary-end" />
                    <h3 className="text-white font-semibold mb-6 self-start w-full border-b border-glass-edge pb-2">Logo & Identiteti</h3>
                    <div className="relative group cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                        <div className={`w-36 h-36 rounded-full overflow-hidden flex items-center justify-center border-4 transition-all shadow-xl ${logoSrc ? 'border-background-light' : 'border-dashed border-gray-600 hover:border-primary-start'}`}>
                            {logoLoading ? <Loader2 className="w-8 h-8 animate-spin text-primary-start" /> : logoSrc ? <img src={logoSrc} alt="Logo" className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-500" onError={() => setLogoSrc(null)} /> : <div className="text-center group-hover:scale-110 transition-transform"><Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" /><span className="text-xs text-gray-500 font-medium">Ngarko Logo</span></div>}
                        </div>
                        <div className="absolute inset-0 rounded-full bg-black/50 backdrop-blur-[2px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300"><Camera className="w-8 h-8 text-white drop-shadow-lg" /></div>
                        <div className="absolute bottom-1 right-1 bg-primary-start p-2.5 rounded-full shadow-lg border-4 border-background-dark group-hover:scale-110 transition-transform"><Check className="w-4 h-4 text-white" /></div>
                    </div>
                    <input type="file" ref={fileInputRef} onChange={handleLogoUpload} className="hidden" accept="image/*" />
                    <p className="mt-4 text-xs text-gray-400 text-center max-w-[200px]">{logoSrc ? "Klikoni mbi foto për ta ndryshuar" : "Rekomandohet: 500x500px, PNG transparente"}</p>
                </div>
                <div className="bg-background-dark border border-glass-edge rounded-2xl p-6 shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-pink-500 to-purple-500" />
                    <h3 className="text-white font-semibold mb-6 flex items-center gap-2 border-b border-glass-edge pb-2"><Palette className="w-4 h-4 text-purple-400" /> Branding</h3>
                    <div className="flex items-center gap-4 mb-6">
                        <div className="relative overflow-hidden w-14 h-14 rounded-xl border-2 border-white/10 shadow-inner group"><input type="color" value={formData.branding_color || DEFAULT_COLOR} onChange={(e) => setFormData({...formData, branding_color: e.target.value})} className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] cursor-pointer p-0 border-0" /></div>
                        <div className="flex-1"><div className="relative"><span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-mono">#</span><input type="text" value={(formData.branding_color || DEFAULT_COLOR).replace('#', '')} onChange={(e) => setFormData({...formData, branding_color: `#${e.target.value}`})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-7 pr-4 py-3 text-white font-mono uppercase focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                    </div>
                    <div className="p-4 rounded-xl bg-background-light/30 border border-glass-edge/50"><p className="text-[10px] text-gray-500 mb-2 uppercase tracking-wider font-bold">Pamja e Butonave</p><button className="w-full py-2.5 rounded-lg text-white font-medium text-sm shadow-md transition-transform active:scale-95 flex items-center justify-center gap-2" style={{ backgroundColor: formData.branding_color || DEFAULT_COLOR }}><Save className="w-4 h-4" />Ruaj Shembullin</button></div>
                </div>
            </div>
            
            <div className="md:col-span-2">
                <form onSubmit={handleProfileSubmit} className="bg-background-dark border border-glass-edge rounded-2xl p-8 space-y-6 shadow-lg h-full">
                    <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2"><Briefcase className="w-6 h-6 text-primary-start" />Të Dhënat e Zyrës</h3>
                    <div className="grid grid-cols-1 gap-6">
                        <div><label className="block text-sm font-medium text-gray-300 mb-2">Emri i Zyrës Ligjore</label><div className="relative group"><Building2 className="absolute left-3 top-3 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="firm_name" value={formData.firm_name} onChange={(e) => setFormData({...formData, firm_name: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" placeholder="p.sh. Drejtësia Sh.p.k" /></div></div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div><label className="block text-sm text-gray-300 mb-2">Email Publik</label><div className="relative group"><Mail className="absolute left-3 top-3 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="email" name="email_public" value={formData.email_public} onChange={(e) => setFormData({...formData, email_public: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                            <div><label className="block text-sm text-gray-300 mb-2">Telefon</label><div className="relative group"><Phone className="absolute left-3 top-3 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="phone" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                        </div>
                        <div><label className="block text-sm text-gray-300 mb-2">Adresa</label><div className="relative group"><MapPin className="absolute left-3 top-3 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="address" value={formData.address} onChange={(e) => setFormData({...formData, address: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div><label className="block text-sm text-gray-300 mb-2">Qyteti</label><input type="text" name="city" value={formData.city} onChange={(e) => setFormData({...formData, city: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div>
                            <div><label className="block text-sm text-gray-300 mb-2">Website</label><div className="relative group"><Globe className="absolute left-3 top-3 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="website" value={formData.website} onChange={(e) => setFormData({...formData, website: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                        </div>
                        <div><label className="block text-sm text-gray-300 mb-2">Numri Fiskal / NUI</label><div className="relative group"><CreditCard className="absolute left-3 top-3 w-5 h-5 text-gray-500 group-focus-within:text-primary-start transition-colors" /><input type="text" name="tax_id" value={formData.tax_id} onChange={(e) => setFormData({...formData, tax_id: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all" /></div></div>
                    </div>
                    <div className="pt-8 flex justify-end border-t border-white/10 mt-8"><button type="submit" disabled={saving} className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold hover:shadow-lg transition-all disabled:opacity-50 hover:scale-[1.02] active:scale-95">{saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}{t('general.save', 'Ruaj Ndryshimet')}</button></div>
                </form>
            </div>
        </motion.div>
      )}

      {/* --- FINANCE TAB --- */}
      {activeTab === 'finance' && (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-bold text-white">Faturat e Lëshuara</h2>
                <div className="flex gap-3">
                    <button onClick={() => setShowAccountantModal(true)} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-xl shadow-lg transition-all border border-indigo-400/30">
                        <Bot size={20} /> Kontabilisti AI
                    </button>
                    <button onClick={() => setShowInvoiceModal(true)} className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-xl shadow-lg transition-all">
                        <Plus size={20} /> Krijo Faturë
                    </button>
                </div>
            </div>
            {invoices.length === 0 ? (
                <div className="text-center py-12 bg-background-dark border border-glass-edge rounded-2xl"><FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" /><p className="text-gray-400">Nuk keni asnjë faturë të krijuar.</p></div>
            ) : (
                <div className="grid gap-4">{invoices.map(inv => (
                    <div key={inv.id} className="bg-background-dark border border-glass-edge rounded-xl p-4 flex flex-col sm:flex-row justify-between items-center gap-4">
                        <div className="flex items-center gap-4 w-full sm:w-auto"><div className={`p-3 rounded-lg ${inv.status === 'PAID' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}><FileText size={24} /></div><div><h3 className="font-bold text-white">{inv.client_name}</h3><p className="text-sm text-gray-400">{inv.invoice_number} • {new Date(inv.issue_date).toLocaleDateString()}</p></div></div>
                        <div className="flex items-center gap-6 w-full sm:w-auto justify-between sm:justify-end">
                            <div className="text-right"><p className="text-lg font-bold text-white">€{inv.total_amount.toFixed(2)}</p><span className={`text-xs px-2 py-0.5 rounded-full ${inv.status === 'PAID' ? 'bg-green-900 text-green-300' : 'bg-yellow-900 text-yellow-300'}`}>{inv.status}</span></div>
                            <div className="flex gap-2">
                                <button onClick={() => handleViewInvoice(inv)} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title="Shiko PDF"><Eye size={20} /></button>
                                <button onClick={() => downloadInvoice(inv.id)} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title="Shkarko PDF"><Download size={20} /></button>
                                <button onClick={() => handleArchiveInvoiceClick(inv.id)} className="p-2 hover:bg-blue-900/20 rounded-lg text-blue-400 hover:text-blue-300 transition-colors" title="Arkivo Faturën"><Archive size={20} /></button>
                                <button onClick={() => deleteInvoice(inv.id)} className="p-2 hover:bg-red-900/20 rounded-lg text-red-400 hover:text-red-300 transition-colors" title="Fshi Faturën"><Trash2 size={20} /></button>
                            </div>
                        </div>
                    </div>
                ))}</div>
            )}
        </motion.div>
      )}

      {/* --- ARCHIVE TAB (V2 - REDESIGNED CARDS & STREAMING FIX) --- */}
      {activeTab === 'archive' && (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            
            {/* Toolbar & Breadcrumbs */}
            <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center bg-background-light/5 backdrop-blur-md p-3 rounded-2xl border border-white/10 shadow-lg">
                    {/* Breadcrumbs */}
                    <div className="flex items-center gap-2 overflow-x-auto text-sm no-scrollbar px-2">
                        {breadcrumbs.map((crumb, index) => (
                            <React.Fragment key={crumb.id || 'root'}>
                                <button 
                                    onClick={() => handleNavigate(crumb, index)}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${index === breadcrumbs.length - 1 ? 'bg-primary-start/20 text-primary-start font-bold border border-primary-start/20' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
                                >
                                    {crumb.type === 'ROOT' ? <Home size={14} /> : crumb.type === 'CASE' ? <Briefcase size={14} /> : <FolderOpen size={14} />}
                                    {crumb.name}
                                </button>
                                {index < breadcrumbs.length - 1 && <ChevronRight size={14} className="text-gray-600 flex-shrink-0" />}
                            </React.Fragment>
                        ))}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 flex-shrink-0">
                        <button onClick={() => setShowFolderModal(true)} className="flex items-center gap-2 px-4 py-2 bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20 hover:text-yellow-400 rounded-xl border border-yellow-500/30 transition-all font-medium text-sm">
                            <FolderPlus size={18} /> <span className="hidden sm:inline">Dosje</span>
                        </button>
                        <div className="relative">
                            <input type="file" ref={archiveInputRef} className="hidden" onChange={handleSmartUpload} />
                            <button onClick={() => archiveInputRef.current?.click()} disabled={isUploading} className="flex items-center gap-2 px-4 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl shadow-lg shadow-primary-start/20 transition-all font-medium text-sm disabled:opacity-50 disabled:cursor-wait">
                                {isUploading ? <Loader2 className="animate-spin w-4 h-4" /> : <Upload size={18} />} <span className="hidden sm:inline">Ngarko</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* CONTENT GRID */}
            <div className="space-y-8">
                
                {/* 1. VIRTUAL CASE FOLDERS (Only at ROOT) */}
                {currentView.type === 'ROOT' && cases.length > 0 && (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 ml-1 flex items-center gap-2 opacity-70">
                            <Briefcase size={14} /> {t('archive.caseFolders', 'Dosjet e Çështjeve')}
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                            {cases.map(c => (
                                <div key={c.id} onClick={() => handleEnterFolder(c.id, c.title, 'CASE')} 
                                     className="group relative bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-5 hover:bg-white/10 hover:border-primary-start/30 transition-all cursor-pointer shadow-sm hover:shadow-xl hover:shadow-primary-start/5 hover:-translate-y-1">
                                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-start to-primary-end rounded-t-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                                    <div className="p-3 w-12 h-12 rounded-xl bg-gradient-to-br from-primary-start/20 to-primary-end/20 border border-primary-start/30 flex items-center justify-center mb-3 text-primary-start group-hover:scale-110 transition-transform">
                                        <Briefcase size={20} />
                                    </div>
                                    <h4 className="text-sm font-bold text-white truncate w-full mb-1">{c.title}</h4>
                                    <div className="flex items-center justify-between">
                                        <p className="text-[10px] text-gray-400 bg-black/30 px-2 py-0.5 rounded-full inline-block border border-white/5">{c.case_number}</p>
                                        <ChevronRight size={14} className="text-gray-600 group-hover:text-primary-start group-hover:translate-x-1 transition-all" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* 2. ARCHIVE CONTENTS (Folders & Files) */}
                <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                    {(currentView.type !== 'ROOT' || archiveItems.length > 0) && (
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4 ml-1 flex items-center gap-2 opacity-70">
                            <FolderOpen size={14} /> {currentView.type === 'ROOT' ? t('archive.myDocuments', 'Dokumentet e Mia') : t('archive.contents', 'Përmbajtja')}
                        </h3>
                    )}
                    
                    {archiveItems.length === 0 && currentView.type !== 'ROOT' ? (
                        <div className="text-center py-20 border-2 border-dashed border-white/10 rounded-3xl bg-white/5 flex flex-col items-center justify-center">
                            <div className="p-6 bg-white/5 rounded-full mb-4 animate-pulse">
                                <FolderOpen className="w-12 h-12 text-gray-600" />
                            </div>
                            <p className="text-gray-300 font-medium text-lg">Kjo dosje është e zbrazët</p>
                            <p className="text-sm text-gray-500 mt-2 max-w-xs mx-auto">Filloni duke ngarkuar dokumente ose krijoni nën-dosje për të organizuar punën tuaj.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                            {archiveItems.map(item => {
                                const isFolder = (item as any).item_type === 'FOLDER';
                                const fileExt = item.file_type || 'FILE';
                                const isDragging = draggedItemId === item.id;
                                
                                return (
                                    <div key={item.id} 
                                         draggable
                                         onDragStart={(e) => onDragStart(e, item.id)}
                                         onDragOver={onDragOver}
                                         onDrop={(e) => onDrop(e, item.id)}
                                         onClick={() => isFolder ? handleEnterFolder(item.id, item.title, 'FOLDER') : null}
                                         className={`
                                            group relative rounded-2xl p-4 transition-all duration-300 border
                                            ${isFolder ? 'cursor-pointer hover:border-yellow-500/40 bg-gradient-to-b from-white/10 to-white/5' : 'bg-white/5 hover:border-blue-500/40 hover:bg-white/10'}
                                            ${isDragging ? 'opacity-50 scale-95 border-dashed border-white/50' : 'border-white/10'}
                                            flex flex-col justify-between h-40 shadow-sm hover:shadow-xl hover:-translate-y-1
                                         `}>
                                        
                                        {/* Icon Container */}
                                        <div className="flex justify-between items-start mb-2">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-lg border border-white/10
                                                ${isFolder ? 'bg-gradient-to-br from-yellow-500/20 to-yellow-600/20 text-yellow-400' : 'bg-gradient-to-br from-blue-500/20 to-blue-600/20 text-blue-400'}
                                            `}>
                                                {isFolder ? <FolderOpen size={20} /> : getFileIcon(fileExt)}
                                            </div>
                                            
                                            {/* Context Actions (Always visible on hover for desktop) */}
                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                                {!isFolder && (
                                                    <button onClick={(e) => {e.stopPropagation(); deleteArchiveItem(item.id)}} className="text-gray-500 hover:text-red-400 transition-colors p-1">
                                                        <Trash2 size={16} />
                                                    </button>
                                                )}
                                                {isFolder && (
                                                    <ChevronRight size={16} className="text-gray-600 group-hover:text-yellow-500 transition-colors" />
                                                )}
                                            </div>
                                        </div>

                                        {/* Info */}
                                        <div className="w-full mt-auto">
                                            <h4 className="text-sm font-semibold text-gray-200 truncate w-full mb-1 group-hover:text-white transition-colors" title={item.title}>{item.title}</h4>
                                            <div className="flex justify-between items-end border-t border-white/5 pt-2 mt-1">
                                                {isFolder ? (
                                                    <span className="text-[10px] text-yellow-500/80 font-bold uppercase tracking-wider">Dosje</span>
                                                ) : (
                                                    <>
                                                        <span className="text-[10px] text-gray-500 font-mono bg-black/20 px-1.5 py-0.5 rounded">{fileExt}</span>
                                                        <div className="flex gap-1">
                                                            <button onClick={(e) => {e.stopPropagation(); handleViewItem(item)}} className="text-gray-400 hover:text-blue-400 transition-colors" title="Shiko"><Eye size={14} /></button>
                                                            <button onClick={(e) => {e.stopPropagation(); downloadArchiveItem(item.id, item.title)}} className="text-gray-400 hover:text-green-400 transition-colors" title="Shkarko"><Download size={14} /></button>
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
      )}

      {/* --- CREATE FOLDER MODAL --- */}
      {showFolderModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-sm p-6 shadow-2xl scale-100">
                  <div className="flex justify-between items-center mb-4">
                      <h3 className="text-lg font-bold text-white">Krijo Dosje të Re</h3>
                      <button onClick={() => setShowFolderModal(false)} className="text-gray-500 hover:text-white"><X size={20}/></button>
                  </div>
                  <form onSubmit={handleCreateFolder}>
                      <div className="relative mb-6">
                          <FolderOpen className="absolute left-3 top-3.5 w-5 h-5 text-gray-500" />
                          <input 
                            autoFocus
                            type="text" 
                            value={newFolderName} 
                            onChange={(e) => setNewFolderName(e.target.value)} 
                            placeholder="Emri i Dosjes" 
                            className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-3 text-white focus:ring-2 focus:ring-primary-start outline-none transition-all placeholder:text-gray-600"
                          />
                      </div>
                      <div className="flex justify-end gap-3">
                          <button type="button" onClick={() => setShowFolderModal(false)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors">Anulo</button>
                          <button type="submit" className="px-6 py-2 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white rounded-xl font-bold shadow-lg shadow-primary-start/20 transition-all">Krijo</button>
                      </div>
                  </form>
              </div>
          </div>
      )}

      {/* --- INVOICE MODAL --- */}
      {showInvoiceModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-2xl [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-gray-700 [&::-webkit-scrollbar-thumb]:rounded-full">
                  <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-bold text-white">Krijo Faturë të Re</h2>
                    <button onClick={() => setShowInvoiceModal(false)} className="text-gray-400 hover:text-white"><X size={24} /></button>
                  </div>
                  <form onSubmit={handleCreateInvoice} className="space-y-6">
                      <div className="space-y-4">
                          <h3 className="text-sm font-bold text-primary-start uppercase tracking-wider flex items-center gap-2"><User size={16} /> Të Dhënat e Klientit</h3>
                          <div><label className="block text-sm text-gray-300 mb-1">Emri</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_name} onChange={e => setNewInvoice({...newInvoice, client_name: e.target.value})} /></div>
                          <div className="grid grid-cols-2 gap-4">
                              <div><label className="block text-sm text-gray-300 mb-1">Email</label><input type="email" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_email} onChange={e => setNewInvoice({...newInvoice, client_email: e.target.value})} /></div>
                              <div><label className="block text-sm text-gray-300 mb-1">Telefon</label><input type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_phone} onChange={e => setNewInvoice({...newInvoice, client_phone: e.target.value})} /></div>
                          </div>
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
                      <div className="flex justify-end gap-3"><button type="button" onClick={() => setShowInvoiceModal(false)} className="px-4 py-2 text-gray-400">Anulo</button><button type="submit" className="px-6 py-2 bg-green-600 text-white rounded-lg font-bold">Krijo</button></div>
                  </form>
              </div>
          </div>
      )}

      {/* --- ARCHIVE INVOICE MODAL --- */}
      {showArchiveInvoiceModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6 shadow-2xl">
                  <h2 className="text-xl font-bold text-white mb-4">Arkivo Faturën</h2>
                  <div className="space-y-3 mb-6"><label className="block text-sm text-gray-400 mb-1">Dosja e Çështjes</label><select className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-start" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">Të Përgjithshme (Pa Dosje)</option>{cases.map(c => (<option key={c.id} value={c.id}>{c.title}</option>))}</select></div>
                  <div className="flex justify-end gap-3"><button onClick={() => setShowArchiveInvoiceModal(false)} className="px-4 py-2 text-gray-400 hover:text-white">Anulo</button><button onClick={submitArchiveInvoice} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold">Arkivo</button></div>
              </div>
          </div>
      )}

      {/* --- ACCOUNTANT AI MODAL --- */}
      {showAccountantModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
            <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-4xl h-[80vh] flex flex-col shadow-2xl overflow-hidden relative">
                <button onClick={() => setShowAccountantModal(false)} className="absolute top-4 right-4 p-2 bg-white/5 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors z-10"><X size={24} /></button>
                <div className="p-8 border-b border-white/10 flex justify-between items-center bg-gradient-to-r from-indigo-900/40 to-purple-900/40">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-indigo-500/20 rounded-xl border border-indigo-500/30 shadow-lg shadow-indigo-500/10"><Bot className="w-10 h-10 text-indigo-300" /></div>
                        <div><h2 className="text-2xl font-bold text-white tracking-tight">Kontabilisti AI</h2><p className="text-sm text-indigo-200/80 font-medium">Asistenti Financiar për Zyrën tuaj</p></div>
                    </div>
                </div>
                <div className="flex-1 p-8 overflow-y-auto flex flex-col items-center justify-center text-center space-y-8">
                        <div className="relative"><div className="absolute inset-0 bg-indigo-500 blur-3xl opacity-20 rounded-full"></div><div className="w-32 h-32 bg-indigo-950/50 backdrop-blur-sm rounded-full flex items-center justify-center border border-indigo-500/30 shadow-2xl relative z-10"><Bot className="w-16 h-16 text-indigo-400" /></div></div>
                        <h3 className="text-2xl font-bold text-white">Së Shpejti...</h3>
                        <p className="text-gray-400">Ky modul është në zhvillim e sipër.</p>
                        <button onClick={() => setShowAccountantModal(false)} className="px-6 py-2 rounded-full border border-indigo-500/50 text-indigo-300 hover:bg-indigo-500/10 transition-colors text-sm font-medium">Mbyll</button>
                </div>
            </div>
        </div>
      )}

      {viewingDoc && <PDFViewerModal documentData={viewingDoc} onClose={closePreview} t={t} directUrl={viewingUrl} />}
    </div>
  );
};

export default BusinessPage;