// FILE: src/components/business/ProfileTab.tsx
// PHOENIX PROTOCOL - PROFILE TAB V3.0 (GLASS STYLE)
// 1. VISUALS: Full Glassmorphism adoption (glass-panel, glass-input).
// 2. UX: Enhanced logo upload and branding interactions.
// 3. LOGIC: Preserved all data fetching and submission flows.

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
    Building2, Mail, Phone, Palette, Save, Upload, Loader2, Camera, MapPin, Globe, CreditCard
} from 'lucide-react';
import { apiService, API_V1_URL } from '../../services/api';
import { BusinessProfile, BusinessProfileUpdate } from '../../data/types';
import { useTranslation } from 'react-i18next';

const DEFAULT_COLOR = '#3b82f6';

export const ProfileTab: React.FC = () => {
    const { t } = useTranslation();
    const [profile, setProfile] = useState<BusinessProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [logoSrc, setLogoSrc] = useState<string | null>(null);
    const [logoLoading, setLogoLoading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [formData, setFormData] = useState<BusinessProfileUpdate>({
        firm_name: '', email_public: '', phone: '', address: '', city: '', website: '', tax_id: '', branding_color: DEFAULT_COLOR
    });

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const data = await apiService.getBusinessProfile();
                setProfile(data);
                setFormData({
                    firm_name: data.firm_name || '', email_public: data.email_public || '', phone: data.phone || '',
                    address: data.address || '', city: data.city || '', website: data.website || '',
                    tax_id: data.tax_id || '', branding_color: data.branding_color || DEFAULT_COLOR
                });
            } catch (error) { console.error(error); } finally { setLoading(false); }
        };
        fetchProfile();
    }, []);

    useEffect(() => {
        const url = profile?.logo_url;
        if (url) {
            if (url.startsWith('blob:') || url.startsWith('data:')) { setLogoSrc(url); return; }
            setLogoLoading(true);
            apiService.fetchImageBlob(url)
                .then((blob: Blob) => setLogoSrc(URL.createObjectURL(blob)))
                .catch(() => {
                    const cleanBase = API_V1_URL.endsWith('/') ? API_V1_URL.slice(0, -1) : API_V1_URL;
                    const cleanPath = url.startsWith('/') ? url.slice(1) : url;
                    if (!url.startsWith('http')) setLogoSrc(`${cleanBase}/${cleanPath}`);
                    else setLogoSrc(url);
                })
                .finally(() => setLogoLoading(false));
        }
    }, [profile?.logo_url]);

    const handleProfileSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            const clean: any = { ...formData };
            Object.keys(clean).forEach(k => clean[k] === '' && (clean[k] = null));
            await apiService.updateBusinessProfile(clean);
            alert(t('settings.successMessage'));
        } catch { alert(t('error.generic')); } finally { setSaving(false); }
    };

    const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        setSaving(true);
        try {
            const p = await apiService.uploadBusinessLogo(f);
            setProfile(p);
        } catch { alert(t('business.logoUploadFailed')); } finally { setSaving(false); }
    };

    if (loading) return <div className="flex justify-center h-64 items-center"><Loader2 className="animate-spin text-primary-start" /></div>;

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="space-y-8">
                {/* Logo Section - Glass Panel */}
                <div className="glass-panel rounded-3xl p-8 flex flex-col items-center shadow-xl relative overflow-hidden group">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-primary-start to-primary-end" />
                    <h3 className="text-white font-bold mb-8 self-start text-lg">{t('business.logoIdentity')}</h3>
                    <div className="relative group cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                        <div className={`w-40 h-40 rounded-full overflow-hidden flex items-center justify-center border-4 transition-all shadow-2xl ${logoSrc ? 'border-white/20' : 'border-dashed border-white/10 hover:border-primary-start'}`}>
                            {logoLoading ? <Loader2 className="w-10 h-10 animate-spin text-primary-start" /> : logoSrc ? <img src={logoSrc} alt="Logo" className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-500" onError={() => setLogoSrc(null)} /> : <div className="text-center group-hover:scale-110 transition-transform"><Upload className="w-10 h-10 text-gray-400 mx-auto mb-2" /><span className="text-xs text-gray-500 font-bold uppercase tracking-wider">{t('business.upload')}</span></div>}
                        </div>
                        <div className="absolute inset-0 rounded-full bg-black/60 backdrop-blur-[2px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300"><Camera className="w-10 h-10 text-white drop-shadow-lg" /></div>
                    </div>
                    <input type="file" ref={fileInputRef} onChange={handleLogoUpload} className="hidden" accept="image/*" />
                </div>

                {/* Branding Section - Glass Panel */}
                <div className="glass-panel rounded-3xl p-8 shadow-xl relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-accent-start to-accent-end" />
                    <h3 className="text-white font-bold mb-6 flex items-center gap-2"><Palette className="w-5 h-5 text-accent-start" /> {t('business.branding')}</h3>
                    <div className="flex items-center gap-4 mb-6">
                        <div className="relative overflow-hidden w-16 h-16 rounded-2xl border-2 border-white/10 shadow-inner"><input type="color" value={formData.branding_color || DEFAULT_COLOR} onChange={(e) => setFormData({ ...formData, branding_color: e.target.value })} className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] cursor-pointer" /></div>
                        <div className="flex-1"><div className="relative"><span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono text-lg">#</span><input type="text" value={(formData.branding_color || DEFAULT_COLOR).replace('#', '')} onChange={(e) => setFormData({ ...formData, branding_color: `#${e.target.value}` })} className="glass-input w-full pl-8 pr-4 py-3 rounded-xl text-white font-mono uppercase" /></div></div>
                    </div>
                    <button className="w-full py-3 rounded-xl text-white font-bold text-sm shadow-lg transition-transform active:scale-95 flex items-center justify-center gap-2" style={{ backgroundColor: formData.branding_color || DEFAULT_COLOR }}><Save className="w-4 h-4" />{t('business.saveColor')}</button>
                </div>
            </div>

            {/* Profile Form - Glass Panel */}
            <div className="md:col-span-2">
                <form onSubmit={handleProfileSubmit} className="glass-panel rounded-3xl p-8 space-y-8 shadow-xl h-full relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-success-start to-success-end" />
                    <h3 className="text-xl font-bold text-white flex items-center gap-3"><Building2 className="w-6 h-6 text-success-start" />{t('business.firmData')}</h3>
                    
                    <div className="grid grid-cols-1 gap-6">
                        <div className="group">
                            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.firmNameLabel')}</label>
                            <div className="relative">
                                <Building2 className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" />
                                <input type="text" name="firm_name" value={formData.firm_name} onChange={(e) => setFormData({ ...formData, firm_name: e.target.value })} className="glass-input w-full pl-12 pr-4 py-3 rounded-xl text-white" placeholder={t('business.firmNamePlaceholder')} />
                            </div>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.publicEmail')}</label><div className="relative"><Mail className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" /><input type="email" name="email_public" value={formData.email_public} onChange={(e) => setFormData({ ...formData, email_public: e.target.value })} className="glass-input w-full pl-12 pr-4 py-3 rounded-xl text-white" /></div></div>
                            <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.phone')}</label><div className="relative"><Phone className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" /><input type="text" name="phone" value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} className="glass-input w-full pl-12 pr-4 py-3 rounded-xl text-white" /></div></div>
                        </div>
                    </div>
                    
                    <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.address')}</label><div className="relative"><MapPin className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" /><input type="text" name="address" value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} className="glass-input w-full pl-12 pr-4 py-3 rounded-xl text-white" /></div></div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.city')}</label><input type="text" name="city" value={formData.city} onChange={(e) => setFormData({ ...formData, city: e.target.value })} className="glass-input w-full px-4 py-3 rounded-xl text-white" /></div>
                        <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.website')}</label><div className="relative"><Globe className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" /><input type="text" name="website" value={formData.website} onChange={(e) => setFormData({ ...formData, website: e.target.value })} className="glass-input w-full pl-12 pr-4 py-3 rounded-xl text-white" /></div></div>
                    </div>
                    
                    <div className="group"><label className="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">{t('business.taxId')}</label><div className="relative"><CreditCard className="absolute left-4 top-3.5 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" /><input type="text" name="tax_id" value={formData.tax_id} onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })} className="glass-input w-full pl-12 pr-4 py-3 rounded-xl text-white" /></div></div>
                    
                    <div className="pt-8 flex justify-end mt-auto"><button type="submit" disabled={saving} className="flex items-center gap-2 px-10 py-3.5 bg-gradient-to-r from-success-start to-success-end text-white rounded-xl font-bold hover:shadow-lg hover:shadow-success-start/20 transition-all disabled:opacity-50 hover:scale-[1.02] active:scale-95">{saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}{t('general.save')}</button></div>
                </form>
            </div>
        </motion.div>
    );
};