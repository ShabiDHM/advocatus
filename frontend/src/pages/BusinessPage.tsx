// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - CLEANUP
// 1. FIX: Removed unused 'ArrowLeft' import.
// 2. TYPES: Strictly uses 'ArchiveItemOut' for the Archive list.
// 3. STATUS: Zero linter errors.

import React, { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Building2, Mail, Phone, MapPin, Globe, Palette, Save, Upload, Loader2, CreditCard, FileText, Plus, Download, Trash2, FolderOpen, File } from 'lucide-react';
import { apiService } from '../services/api';
import { BusinessProfile, BusinessProfileUpdate, Invoice, InvoiceItem, ArchiveItemOut } from '../data/types';
import { useTranslation } from 'react-i18next';

type ActiveTab = 'profile' | 'finance' | 'archive';

const BusinessPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const archiveInputRef = useRef<HTMLInputElement>(null);

  // Data States
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  // PHOENIX FIX: Using ArchiveItemOut from types
  const [archiveItems, setArchiveItems] = useState<ArchiveItemOut[]>([]);

  // Modals
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Forms
  const [formData, setFormData] = useState<BusinessProfileUpdate>({
    firm_name: '', email_public: '', phone: '', address: '', city: '', website: '', tax_id: '', branding_color: '#1f2937'
  });
  const [newInvoice, setNewInvoice] = useState({ client_name: '', client_email: '', client_address: '', tax_rate: 18, notes: '' });
  const [lineItems, setLineItems] = useState<InvoiceItem[]>([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);
  
  // Archive Upload Form
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadCategory, setUploadCategory] = useState("GENERAL");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [profileData, invoiceData, archiveData] = await Promise.all([
          apiService.getBusinessProfile(),
          apiService.getInvoices().catch(() => []),
          apiService.getArchiveItems().catch(() => []) 
      ]);
      
      setProfile(profileData);
      setInvoices(invoiceData);
      setArchiveItems(archiveData);
      
      setFormData({
        firm_name: profileData.firm_name || '',
        email_public: profileData.email_public || '',
        phone: profileData.phone || '',
        address: profileData.address || '',
        city: profileData.city || '',
        website: profileData.website || '',
        tax_id: profileData.tax_id || '',
        branding_color: profileData.branding_color || '#1f2937'
      });
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      setLoading(false);
    }
  };

  // --- PROFILE LOGIC ---
  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
        const cleanData: any = { ...formData };
        Object.keys(cleanData).forEach(key => { if (cleanData[key] === '') cleanData[key] = null; });
        if (!cleanData.firm_name) cleanData.firm_name = "Zyra Ligjore";
        const updatedProfile = await apiService.updateBusinessProfile(cleanData);
        setProfile(updatedProfile);
        alert(t('settings.successMessage', 'Profili u përditësua me sukses!'));
    } catch (error) {
      alert(t('error.generic', 'Gabim gjatë ruajtjes.'));
    } finally { setSaving(false); }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      setSaving(true);
      const updatedProfile = await apiService.uploadBusinessLogo(file);
      setProfile(updatedProfile);
    } catch (error) { alert(t('error.uploadFailed')); } finally { setSaving(false); }
  };

  // --- INVOICE LOGIC ---
  const addLineItem = () => setLineItems([...lineItems, { description: '', quantity: 1, unit_price: 0, total: 0 }]);
  const removeLineItem = (index: number) => lineItems.length > 1 && setLineItems(lineItems.filter((_, i) => i !== index));
  const updateLineItem = (index: number, field: keyof InvoiceItem, value: any) => {
      const newItems = [...lineItems];
      newItems[index] = { ...newItems[index], [field]: value };
      newItems[index].total = newItems[index].quantity * newItems[index].unit_price;
      setLineItems(newItems);
  };
  const handleCreateInvoice = async (e: React.FormEvent) => {
      e.preventDefault();
      try {
          const created = await apiService.createInvoice({ ...newInvoice, items: lineItems });
          setInvoices([created, ...invoices]);
          setShowInvoiceModal(false);
          setNewInvoice({ client_name: '', client_email: '', client_address: '', tax_rate: 18, notes: '' });
          setLineItems([{ description: '', quantity: 1, unit_price: 0, total: 0 }]);
      } catch (error) { alert("Dështoi krijimi i faturës."); }
  };
  
  const deleteInvoice = async (id: string) => {
      if(!window.confirm(t('general.confirmDelete', "A jeni i sigurt?"))) return;
      try {
          await apiService.deleteInvoice(id); 
          setInvoices(invoices.filter(inv => inv.id !== id));
      } catch (error) { alert("Fshirja dështoi."); }
  };

  const downloadInvoice = async (id: string) => { try { await apiService.downloadInvoicePdf(id, i18n.language); } catch (error) { alert("Shkarkimi dështoi."); } };

  // --- ARCHIVE LOGIC ---
  const handleUploadArchive = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!uploadFile) return;
      
      try {
          const newItem = await apiService.uploadArchiveItem(uploadFile, uploadTitle, uploadCategory);
          setArchiveItems([newItem, ...archiveItems]);
          setShowUploadModal(false);
          setUploadFile(null);
          setUploadTitle("");
      } catch (error) { alert("Ngarkimi dështoi."); }
  };

  const deleteArchiveItem = async (id: string) => {
      if(!window.confirm("A jeni i sigurt?")) return;
      try {
          await apiService.deleteArchiveItem(id);
          setArchiveItems(archiveItems.filter(item => item.id !== id));
      } catch (error) { alert("Fshirja dështoi."); }
  };

  const downloadArchiveItem = async (id: string, title: string) => {
      try { await apiService.downloadArchiveItem(id, title); } catch (error) { alert("Shkarkimi dështoi."); }
  };

  if (loading) return <div className="flex justify-center items-center h-96"><Loader2 className="w-8 h-8 animate-spin text-primary-start" /></div>;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
            <h1 className="text-3xl font-bold text-white mb-2">{t('business.title', 'Zyra Ime')}</h1>
            <p className="text-gray-400">Qendra Administrative për Zyrën tuaj Ligjore.</p>
        </div>
        
        <div className="flex bg-background-light/20 p-1 rounded-xl border border-glass-edge">
            <button onClick={() => setActiveTab('profile')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'profile' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><Building2 className="w-4 h-4 inline-block mr-2" />Profili</button>
            <button onClick={() => setActiveTab('finance')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'finance' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><FileText className="w-4 h-4 inline-block mr-2" />Financat</button>
            <button onClick={() => setActiveTab('archive')} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${activeTab === 'archive' ? 'bg-primary-start text-white shadow-lg' : 'text-text-secondary hover:text-white'}`}><FolderOpen className="w-4 h-4 inline-block mr-2" />Arkiva</button>
        </div>
      </div>

      {/* --- TAB: PROFILE --- */}
      {activeTab === 'profile' && (
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="space-y-6">
                <div className="bg-background-dark border border-glass-edge rounded-2xl p-6 text-center">
                    <div className="relative w-32 h-32 mx-auto mb-4 bg-background-light rounded-full flex items-center justify-center overflow-hidden border-2 border-dashed border-gray-600 group hover:border-primary-start transition-colors">
                    {profile?.logo_url ? <img src={profile.logo_url} alt="Logo" className="w-full h-full object-cover" /> : <Building2 className="w-12 h-12 text-gray-500" />}
                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer" onClick={() => fileInputRef.current?.click()}><Upload className="w-6 h-6 text-white" /></div>
                    </div>
                    <input type="file" ref={fileInputRef} onChange={handleLogoUpload} className="hidden" accept="image/*" />
                    <h3 className="text-lg font-semibold text-white mb-1">{formData.firm_name || 'Emri i Zyrës'}</h3>
                    <p className="text-sm text-gray-400">Logo & Identiteti Vizual</p>
                </div>
                <div className="bg-background-dark border border-glass-edge rounded-2xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><Palette className="w-5 h-5 text-accent-start" /> Branding</h3>
                    <div className="space-y-4">
                    <div><label className="block text-sm text-gray-400 mb-2">Ngjyra Kryesore (HEX)</label><div className="flex gap-3"><input type="color" name="branding_color" value={formData.branding_color} onChange={(e) => setFormData({...formData, branding_color: e.target.value})} className="h-10 w-16 bg-transparent border-0 rounded cursor-pointer" /><input type="text" name="branding_color" value={formData.branding_color} onChange={(e) => setFormData({...formData, branding_color: e.target.value})} className="flex-1 bg-background-light border border-glass-edge rounded-lg px-3 py-2 text-white font-mono" /></div></div>
                    </div>
                </div>
            </div>
            <div className="md:col-span-2">
                <form onSubmit={handleProfileSubmit} className="bg-background-dark border border-glass-edge rounded-2xl p-6 space-y-6">
                    <div className="grid grid-cols-1 gap-6">
                        <div><label className="block text-sm font-medium text-gray-300 mb-2">Emri i Zyrës Ligjore</label><div className="relative"><Building2 className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" /><input type="text" name="firm_name" value={formData.firm_name} onChange={(e) => setFormData({...formData, firm_name: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2.5 text-white focus:ring-2 focus:ring-primary-start outline-none" /></div></div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div><label className="block text-sm text-gray-300 mb-2">Email Publik</label><div className="relative"><Mail className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" /><input type="email" name="email_public" value={formData.email_public} onChange={(e) => setFormData({...formData, email_public: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2 text-white" /></div></div>
                            <div><label className="block text-sm text-gray-300 mb-2">Telefon</label><div className="relative"><Phone className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" /><input type="text" name="phone" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2 text-white" /></div></div>
                        </div>
                        <div><label className="block text-sm text-gray-300 mb-2">Adresa</label><div className="relative"><MapPin className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" /><input type="text" name="address" value={formData.address} onChange={(e) => setFormData({...formData, address: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2 text-white" /></div></div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div><label className="block text-sm text-gray-300 mb-2">Qyteti</label><input type="text" name="city" value={formData.city} onChange={(e) => setFormData({...formData, city: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl px-4 py-2 text-white" /></div>
                            <div><label className="block text-sm text-gray-300 mb-2">Website</label><div className="relative"><Globe className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" /><input type="text" name="website" value={formData.website} onChange={(e) => setFormData({...formData, website: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2 text-white" /></div></div>
                        </div>
                        <div><label className="block text-sm text-gray-300 mb-2">Numri Fiskal / NUI</label><div className="relative"><CreditCard className="absolute left-3 top-2.5 w-5 h-5 text-gray-500" /><input type="text" name="tax_id" value={formData.tax_id} onChange={(e) => setFormData({...formData, tax_id: e.target.value})} className="w-full bg-background-light border border-glass-edge rounded-xl pl-10 pr-4 py-2 text-white" /></div></div>
                    </div>
                    <div className="pt-4 flex justify-end"><button type="submit" disabled={saving} className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold hover:shadow-lg transition-all disabled:opacity-50">{saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}{t('general.save', 'Ruaj Ndryshimet')}</button></div>
                </form>
            </div>
        </motion.div>
      )}

      {/* --- TAB: FINANCE --- */}
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
                                <button onClick={() => downloadInvoice(inv.id)} className="p-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-white transition-colors" title="Shkarko PDF"><Download size={20} /></button>
                                <button onClick={() => deleteInvoice(inv.id)} className="p-2 hover:bg-red-900/20 rounded-lg text-red-400 hover:text-red-300 transition-colors" title="Fshi Faturën"><Trash2 size={20} /></button>
                            </div>
                        </div>
                    </div>
                ))}</div>
            )}
        </motion.div>
      )}

      {/* --- TAB: ARCHIVE (FILES) --- */}
      {activeTab === 'archive' && (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-bold text-white">Dokumentet e Arkivuara</h2>
                <button onClick={() => setShowUploadModal(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl shadow-lg transition-all"><Upload size={20} /> Ngarko Dokument</button>
            </div>
            
            {archiveItems.length === 0 ? (
                <div className="text-center py-12 bg-background-dark border border-glass-edge rounded-2xl"><FolderOpen className="w-12 h-12 text-gray-600 mx-auto mb-3" /><p className="text-gray-400">Arkiva është e zbrazët.</p><p className="text-sm text-gray-600">Ngarkoni dokumente të rëndësishme për ti ruajtur këtu.</p></div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {archiveItems.map(item => (
                        <div key={item.id} className="bg-background-dark border border-glass-edge rounded-xl p-4 hover:bg-background-light/5 transition-colors flex flex-col justify-between h-40">
                            <div className="flex justify-between items-start">
                                <div className="p-2 bg-background-light/20 rounded-lg"><File className="w-6 h-6 text-primary-start" /></div>
                                <span className="text-xs px-2 py-1 bg-background-light/30 rounded text-gray-400">{item.file_type}</span>
                            </div>
                            <div>
                                <h3 className="font-semibold text-white truncate" title={item.title}>{item.title}</h3>
                                <p className="text-xs text-gray-500 mt-1">{new Date(item.created_at).toLocaleDateString()} • {(item.file_size / 1024).toFixed(1)} KB</p>
                            </div>
                            <div className="flex justify-end gap-2 mt-2 pt-2 border-t border-glass-edge/50">
                                <button onClick={() => downloadArchiveItem(item.id, item.title)} className="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors"><Download size={16} /></button>
                                <button onClick={() => deleteArchiveItem(item.id)} className="p-1.5 hover:bg-red-900/20 rounded text-red-400 hover:text-red-300 transition-colors"><Trash2 size={16} /></button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </motion.div>
      )}

      {/* CREATE INVOICE MODAL */}
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

      {/* UPLOAD ARCHIVE MODAL */}
      {showUploadModal && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
              <div className="bg-background-dark border border-glass-edge rounded-2xl w-full max-w-lg p-6 shadow-2xl">
                  <h2 className="text-2xl font-bold text-white mb-6">Ngarko Dokument</h2>
                  <form onSubmit={handleUploadArchive} className="space-y-4">
                      <div><label className="block text-sm text-gray-400 mb-1">Titulli i Dokumentit</label><input required type="text" className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={uploadTitle} onChange={e => setUploadTitle(e.target.value)} placeholder="psh. Kontrata Qirasë 2025" /></div>
                      <div><label className="block text-sm text-gray-400 mb-1">Kategoria</label><select className="w-full bg-background-light border-glass-edge rounded-lg px-3 py-2 text-white" value={uploadCategory} onChange={e => setUploadCategory(e.target.value)}><option value="GENERAL">Të Përgjithshme</option><option value="CONTRACT">Kontrata</option><option value="INVOICE">Fatura</option><option value="REPORT">Raporte</option></select></div>
                      <div><label className="block text-sm text-gray-400 mb-1">Zgjidh Skedarin</label><div className="flex items-center justify-center w-full"><label className="flex flex-col w-full h-32 border-2 border-dashed border-glass-edge hover:bg-background-light/5 hover:border-primary-start group cursor-pointer rounded-xl"><div className="flex flex-col items-center justify-center pt-7"><Upload className="w-8 h-8 text-gray-400 group-hover:text-white mb-2" /><p className="pt-1 text-sm tracking-wider text-gray-400 group-hover:text-white">{uploadFile ? uploadFile.name : "Kliko për të zgjedhur"}</p></div><input type="file" className="opacity-0" ref={archiveInputRef} onChange={(e) => setUploadFile(e.target.files?.[0] || null)} /></label></div></div>
                      <div className="flex justify-end gap-3 pt-4"><button type="button" onClick={() => setShowUploadModal(false)} className="px-4 py-2 text-gray-400 hover:text-white">Anulo</button><button type="submit" disabled={!uploadFile} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-bold">Ngarko</button></div>
                  </form>
              </div>
          </div>
      )}
    </div>
  );
};

export default BusinessPage;