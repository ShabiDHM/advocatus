// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUSINESS SUITE (CLEANED)
// 1. FIX: Removed unused 'X' import.
// 2. STATUS: Clean build, zero warnings.

import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { 
    Building2, Mail, Phone, MapPin, Globe, Palette, Save, Upload, Loader2, 
    CreditCard, FileText, Plus, Download, Trash2, FolderOpen, File, ArrowLeft,
    Briefcase, Eye, Archive, Camera, Check
} from 'lucide-react';
import { apiService, API_V1_URL } from '../services/api';
import { BusinessProfile, BusinessProfileUpdate, Invoice, InvoiceItem, ArchiveItemOut, Case, Document } from '../data/types';
import { useTranslation } from 'react-i18next';
import PDFViewerModal from '../components/PDFViewerModal';

type ActiveTab = 'profile' | 'finance' | 'archive';
type ArchiveView = 'ROOT' | 'FOLDER';

const DEFAULT_COLOR = '#3b82f6';

const BusinessPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const archiveInputRef = useRef<HTMLInputElement>(null);

  // Logo Blob State
  const [logoSrc, setLogoSrc] = useState<string | null>(null);
  const [logoLoading, setLogoLoading] = useState(false);

  // Data
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [archiveItems, setArchiveItems] = useState<ArchiveItemOut[]>([]);
  const [cases, setCases] = useState<Case[]>([]);

  // Archive State
  const [archiveView, setArchiveView] = useState<ArchiveView>('ROOT');
  const [currentFolderId, setCurrentFolderId] = useState<string | null>(null);
  const [currentFolderName, setCurrentFolderName] = useState<string>("Të Përgjithshme");
  const [isUploading, setIsUploading] = useState(false);
  
  // Viewer State (Unified)
  const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
  const [viewingUrl, setViewingUrl] = useState<string | null>(null);

  // Modals
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [showArchiveInvoiceModal, setShowArchiveInvoiceModal] = useState(false);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [selectedCaseForInvoice, setSelectedCaseForInvoice] = useState<string>("");

  // Forms
  const [formData, setFormData] = useState<BusinessProfileUpdate>({
    firm_name: '', email_public: '', phone: '', address: '', city: '', website: '', tax_id: '', branding_color: DEFAULT_COLOR
  });
  const [newInvoice, setNewInvoice] = useState({ client_name: '', client_email: '', client_address: '', tax_rate: 18, notes: '' });
  const [lineItems, setLineItems] = useState<InvoiceItem[]>([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    const url = profile?.logo_url;
    if (url) {
        if (url.startsWith('blob:') || url.startsWith('data:')) { setLogoSrc(url); return; }
        setLogoLoading(true);
        apiService.fetchImageBlob(url)
            .then(blob => setLogoSrc(URL.createObjectURL(blob)))
            .catch(() => setLogoSrc(!url.startsWith('http') ? `${API_V1_URL.replace(/\/$/, '')}/${url.startsWith('/') ? url.slice(1) : url}` : url))
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
        firm_name: profileData.firm_name || '',
        email_public: profileData.email_public || '',
        phone: profileData.phone || '',
        address: profileData.address || '',
        city: profileData.city || '',
        website: profileData.website || '',
        tax_id: profileData.tax_id || '',
        branding_color: profileData.branding_color || DEFAULT_COLOR
      });
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      setLoading(false);
    }
  };

  // --- ACTIONS ---
  const openFolder = async (folderId: string | null, name: string) => {
      setLoading(true);
      try {
          const files = await apiService.getArchiveItems(undefined, folderId || undefined);
          setArchiveItems(files);
          setCurrentFolderId(folderId);
          setCurrentFolderName(name);
          setArchiveView('FOLDER');
      } catch (error) { console.error("Failed to open folder", error); } finally { setLoading(false); }
  };

  const handleSmartUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      setIsUploading(true);
      try {
          let category = "GENERAL";
          const nameLower = file.name.toLowerCase();
          if (nameLower.includes("fatura") || nameLower.includes("invoice")) category = "INVOICE";
          else if (nameLower.includes("kontrata") || nameLower.includes("contract")) category = "CONTRACT";
          const newItem = await apiService.uploadArchiveItem(file, file.name, category, currentFolderId || undefined);
          setArchiveItems([newItem, ...archiveItems]);
      } catch (error) { alert("Ngarkimi dështoi."); } finally { setIsUploading(false); if (archiveInputRef.current) archiveInputRef.current.value = ''; }
  };

  const handleArchiveInvoiceClick = (invoiceId: string) => { setSelectedInvoiceId(invoiceId); setShowArchiveInvoiceModal(true); };
  
  const submitArchiveInvoice = async () => {
      if (!selectedInvoiceId) return;
      try {
          await apiService.archiveInvoice(selectedInvoiceId, selectedCaseForInvoice || undefined);
          alert("Fatura u arkivua me sukses!");
          setShowArchiveInvoiceModal(false);
          setSelectedCaseForInvoice("");
      } catch (error) { alert("Arkivimi dështoi."); }
  };

  const handleViewItem = async (item: ArchiveItemOut) => {
      try {
          const blob = await apiService.getArchiveFileBlob(item.id);
          const url = window.URL.createObjectURL(blob);
          const tempDoc: any = {
              id: item.id,
              file_name: item.title,
              mime_type: item.file_type === 'PDF' ? 'application/pdf' : 'image/png', 
              status: 'READY'
          };
          setViewingUrl(url);
          setViewingDoc(tempDoc);
      } catch (error) { alert("Nuk mund të hapet dokumenti."); }
  };

  const handleViewInvoice = async (invoice: Invoice) => {
      try {
          const blob = await apiService.getInvoicePdfBlob(invoice.id);
          const url = window.URL.createObjectURL(blob);
          const tempDoc: any = {
              id: invoice.id,
              file_name: `Invoice #${invoice.invoice_number}`,
              mime_type: 'application/pdf',
              status: 'READY'
          };
          setViewingUrl(url);
          setViewingDoc(tempDoc);
      } catch (error) { alert("Nuk mund të hapet fatura."); }
  };

  const closePreview = () => { 
      if (viewingUrl) window.URL.revokeObjectURL(viewingUrl); 
      setViewingUrl(null); 
      setViewingDoc(null); 
  };

  const deleteArchiveItem = async (id: string) => { if(!window.confirm("A jeni i sigurt?")) return; try { await apiService.deleteArchiveItem(id); setArchiveItems(archiveItems.filter(item => item.id !== id)); } catch (error) { alert("Fshirja dështoi."); } };
  const downloadArchiveItem = async (id: string, title: string) => { try { await apiService.downloadArchiveItem(id, title); } catch (error) { alert("Shkarkimi dështoi."); } };

  // Profile & Invoice Form Handlers
  const handleProfileSubmit = async (e: React.FormEvent) => { e.preventDefault(); setSaving(true); try { const cleanData: any = { ...formData }; Object.keys(cleanData).forEach(key => { if (cleanData[key] === '') cleanData[key] = null; }); if (!cleanData.firm_name) cleanData.firm_name = "Zyra Ligjore"; const updatedProfile = await apiService.updateBusinessProfile(cleanData); setProfile(updatedProfile); alert(t('settings.successMessage')); } catch (error) { alert(t('error.generic')); } finally { setSaving(false); } };
  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => { const file = e.target.files?.[0]; if (!file) return; try { setSaving(true); setLogoLoading(true); const updatedProfile = await apiService.uploadBusinessLogo(file); setProfile(updatedProfile); const reader = new FileReader(); reader.onload = (e) => { if(e.target?.result) setLogoSrc(e.target.result as string); setLogoLoading(false); }; reader.readAsDataURL(file); } catch (error) { alert(t('error.uploadFailed')); setLogoLoading(false); } finally { setSaving(false); } };
  
  // Invoice Form Logic
  const addLineItem = () => setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0, total: 0 }]);
  const removeLineItem = (index: number) => lineItems.length > 1 && setLineItems(lineItems.filter((_, i) => i !== index));
  const updateLineItem = (index: number, field: keyof InvoiceItem, value: any) => { const newItems = [...lineItems]; newItems[index] = { ...newItems[index], [field]: value }; newItems[index].total = newItems[index].quantity * newItems[index].unit_price; setLineItems(newItems); };
  
  const handleCreateInvoice = async (e: React.FormEvent) => { e.preventDefault(); try { const created = await apiService.createInvoice({ ...newInvoice, items: lineItems }); setInvoices([created, ...invoices]); setShowInvoiceModal(false); setNewInvoice({ client_name: '', client_email: '', client_address: '', tax_rate: 18, notes: '' }); setLineItems([{ description: '', quantity: 1, unit_price: 0, total: 0 }]); } catch (error) { alert("Dështoi krijimi i faturës."); } };
  const deleteInvoice = async (id: string) => { if(!window.confirm(t('general.confirmDelete', "A jeni i sigurt?"))) return; try { await apiService.deleteInvoice(id); setInvoices(invoices.filter(inv => inv.id !== id)); } catch (error) { alert("Fshirja dështoi."); } };
  const downloadInvoice = async (id: string) => { try { await apiService.downloadInvoicePdf(id, i18n.language); } catch (error) { alert("Shkarkimi dështoi."); } };

  if (loading && archiveView === 'ROOT') return <div className="flex justify-center items-center h-96"><Loader2 className="w-8 h-8 animate-spin text-primary-start" /></div>;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Header and Tabs */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div><h1 className="text-3xl font-bold text-white mb-2">{t('business.title', 'Zyra Ime')}</h1><p className="text-gray-400">Qendra Administrative për Zyrën tuaj Ligjore.</p></div>
        <div className="flex bg-background-light/20 p-1 rounded-xl border border-glass-edge">
            <button onClick={() => setActiveTab('profile')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'profile' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><Building2 className="w-4 h-4 inline-block mr-2" />Profili</button>
            <button onClick={() => setActiveTab('finance')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'finance' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><FileText className="w-4 h-4 inline-block mr-2" />Financat</button>
            <button onClick={() => setActiveTab('archive')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'archive' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><FolderOpen className="w-4 h-4 inline-block mr-2" />Arkiva</button>
        </div>
      </div>

      {/* Profile Section */}
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
                    <div className="absolute top-0 w-full h-1 bg-gradient-to-r from-accent-start to-accent-end" />
                    <h3 className="text-white font-semibold mb-6 flex items-center gap-2 border-b border-glass-edge pb-2"><Palette className="w-4 h-4 text-accent-start" /> Branding</h3>
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

      {activeTab === 'finance' && (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <div className="flex justify-between items-center"><h2 className="text-xl font-bold text-white">Faturat e Lëshuara</h2><button onClick={() => setShowInvoiceModal(true)} className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-xl shadow-lg transition-all"><Plus size={20} /> Krijo Faturë</button></div>
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

      {activeTab === 'archive' && (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            {archiveView === 'ROOT' && (
                <>
                    <h2 className="text-xl font-bold text-white mb-4">Dosjet e Çështjeve</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
                        <div onClick={() => openFolder(null, "Të Përgjithshme")} className="bg-background-dark border border-glass-edge rounded-xl p-6 hover:bg-background-light/10 transition-colors cursor-pointer text-center group"><FolderOpen className="w-12 h-12 text-yellow-500 mx-auto mb-3 group-hover:scale-110 transition-transform" /><h3 className="text-sm font-medium text-white">Të Përgjithshme</h3><p className="text-xs text-gray-500 mt-1">Dokumente Zyre</p></div>
                        {cases.map(c => (
                            <div key={c.id} onClick={() => openFolder(c.id, c.title)} className="bg-background-dark border border-glass-edge rounded-xl p-6 hover:bg-background-light/10 transition-colors cursor-pointer text-center group"><Briefcase className="w-12 h-12 text-primary-start mx-auto mb-3 group-hover:scale-110 transition-transform" /><h3 className="text-sm font-medium text-white truncate px-2">{c.title}</h3><p className="text-xs text-gray-500 mt-1">{c.client?.name || c.case_number}</p></div>
                        ))}
                    </div>
                </>
            )}
            {archiveView === 'FOLDER' && (
                <>
                    <div className="flex justify-between items-center mb-6"><div className="flex items-center gap-4"><button onClick={() => setArchiveView('ROOT')} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors"><ArrowLeft size={20} /></button><div><h2 className="text-xl font-bold text-white">{currentFolderName}</h2><p className="text-sm text-gray-400">Arkiva / {currentFolderName}</p></div></div><div className="relative"><input type="file" ref={archiveInputRef} className="hidden" onChange={handleSmartUpload} /><button onClick={() => archiveInputRef.current?.click()} disabled={isUploading} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-lg transition-all disabled:opacity-50">{isUploading ? <Loader2 className="animate-spin w-5 h-5" /> : <Upload size={20} />} Ngarko Dokument</button></div></div>
                    {archiveItems.length === 0 ? (
                        <div className="text-center py-12 bg-background-dark border border-glass-edge rounded-2xl"><FolderOpen className="w-12 h-12 text-gray-600 mx-auto mb-3" /><p className="text-gray-400">Kjo dosje është e zbrazët.</p><p className="text-sm text-gray-600">Përdorni butonin 'Ngarko' për të shtuar dokumente.</p></div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {archiveItems.map(item => (
                                <div key={item.id} className="bg-background-dark border border-glass-edge rounded-xl p-4 hover:bg-background-light/5 transition-colors flex flex-col justify-between h-40">
                                    <div className="flex justify-between items-start"><div className="p-2 bg-background-light/20 rounded-lg"><File className="w-6 h-6 text-primary-start" /></div><span className="text-xs px-2 py-1 bg-background-light/30 rounded text-gray-400 uppercase">{item.file_type}</span></div>
                                    <div><h3 className="font-semibold text-white truncate" title={item.title}>{item.title}</h3><p className="text-xs text-gray-500 mt-1">{new Date(item.created_at).toLocaleDateString()} • {(item.file_size / 1024).toFixed(1)} KB</p></div>
                                    <div className="flex justify-end gap-2 mt-2 pt-2 border-t border-glass-edge/50">
                                        <button onClick={() => handleViewItem(item)} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors" title="Shiko"><Eye size={16} /></button>
                                        <button onClick={() => downloadArchiveItem(item.id, item.title)} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors"><Download size={16} /></button>
                                        <button onClick={() => deleteArchiveItem(item.id)} className="p-1.5 hover:bg-red-900/20 rounded text-red-400 hover:text-red-300 transition-colors"><Trash2 size={16} /></button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            )}
        </motion.div>
      )}

      {showInvoiceModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6 shadow-2xl">
                  <h2 className="text-2xl font-bold text-white mb-6">Krijo Faturë të Re</h2>
                  <form onSubmit={handleCreateInvoice} className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div><label className="block text-sm text-gray-400 mb-1">Klienti</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_name} onChange={e => setNewInvoice({...newInvoice, client_name: e.target.value})} placeholder="Emri i Klientit" /></div>
                          <div><label className="block text-sm text-gray-400 mb-1">Email</label><input type="email" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={newInvoice.client_email} onChange={e => setNewInvoice({...newInvoice, client_email: e.target.value})} placeholder="email@client.com" /></div>
                      </div>
                      <div className="space-y-3">
                          <label className="block text-sm text-gray-400">Shërbimet / Produktet</label>
                          {lineItems.map((item, index) => (
                              <div key={index} className="flex gap-2 items-center">
                                  <input type="text" placeholder="Përshkrimi" className="flex-1 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.description} onChange={e => updateLineItem(index, 'description', e.target.value)} required />
                                  <input type="number" placeholder="Sasia" className="w-20 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.quantity} onChange={e => updateLineItem(index, 'quantity', parseFloat(e.target.value))} min="1" />
                                  <input type="number" placeholder="Çmimi" className="w-24 bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={item.unit_price} onChange={e => updateLineItem(index, 'unit_price', parseFloat(e.target.value))} min="0" step="0.01" />
                                  <button type="button" onClick={() => removeLineItem(index)} className="p-2 text-red-400 hover:bg-red-900/20 rounded-lg"><Trash2 size={18} /></button>
                              </div>
                          ))}
                          <button type="button" onClick={addLineItem} className="text-sm text-primary-start hover:underline flex items-center gap-1"><Plus size={14} /> Shto Rresht</button>
                      </div>
                      <div className="flex justify-between items-center pt-4 border-t border-white/10"><div className="text-right w-full"><p className="text-gray-400">TVSH: 18%</p><p className="text-xl font-bold text-white">Totali: €{lineItems.reduce((acc, i) => acc + (i.quantity * i.unit_price), 0) * 1.18}</p></div></div>
                      <div className="flex justify-end gap-3"><button type="button" onClick={() => setShowInvoiceModal(false)} className="px-4 py-2 text-gray-400 hover:text-white">Anulo</button><button type="submit" className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold">Krijo Faturën</button></div>
                  </form>
              </div>
          </div>
      )}

      {showArchiveInvoiceModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-md p-6 shadow-2xl">
                  <h2 className="text-xl font-bold text-white mb-4">Arkivo Faturën</h2>
                  <div className="space-y-3 mb-6"><label className="block text-sm text-gray-400 mb-1">Dosja e Çështjes</label><select className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary-start" value={selectedCaseForInvoice} onChange={(e) => setSelectedCaseForInvoice(e.target.value)}><option value="">Të Përgjithshme (Pa Dosje)</option>{cases.map(c => (<option key={c.id} value={c.id}>{c.title}</option>))}</select></div>
                  <div className="flex justify-end gap-3"><button onClick={() => setShowArchiveInvoiceModal(false)} className="px-4 py-2 text-gray-400 hover:text-white">Anulo</button><button onClick={submitArchiveInvoice} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold">Arkivo</button></div>
              </div>
          </div>
      )}

      {viewingDoc && (
          <PDFViewerModal 
              documentData={viewingDoc}
              onClose={closePreview}
              t={t}
              directUrl={viewingUrl}
          />
      )}
    </div>
  );
};

export default BusinessPage;