// FILE: src/components/business/ProfileTab.tsx
// PHOENIX PROTOCOL - PROFILE TAB V7.1 (FIXED DOUBLE TOP BORDER)

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
    Building2, Mail, Phone, Save, Upload, Loader2, Camera, MapPin, Globe, CreditCard
} from 'lucide-react';
import { apiService, API_V1_URL } from '../../services/api';
import { BusinessProfile, BusinessProfileUpdate } from '../../data/types';
import { useTranslation } from 'react-i18next';

const DEFAULT_COLOR = '#6366F1'; // Aligned with the app's standard primary color

export const ProfileTab: React.FC = () => {
    const { t } = useTranslation();
    const [profile, setProfile] = useState<BusinessProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [logoSrc, setLogoSrc] = useState<string | null>(null);
    const [logoLoading, setLogoLoading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [formData, setFormData] = useState<BusinessProfileUpdate>({
        firm_name: '', 
        email_public: '', 
        phone: '', 
        address: '', 
        city: '', 
        website: '', 
        tax_id: '', 
        branding_color: DEFAULT_COLOR
    });

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const data = await apiService.getBusinessProfile();
                setProfile(data);
                setFormData({
                    firm_name: data.firm_name || '', 
                    email_public: data.email_public || '', 
                    phone: data.phone || '',
                    address: data.address || '', 
                    city: data.city || '', 
                    website: data.website || '',
                    tax_id: data.tax_id || '', 
                    branding_color: data.branding_color || DEFAULT_COLOR
                });
            } catch (error) { 
                console.error(error); 
            } finally { 
                setLoading(false); 
            }
        };
        fetchProfile();
    }, []);

    useEffect(() => {
        const url = profile?.logo_url;
        if (url) {
            if (url.startsWith('blob:') || url.startsWith('data:')) { 
                setLogoSrc(url); 
                return; 
            }
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
        } catch { 
            alert(t('error.generic')); 
        } finally { 
            setSaving(false); 
        }
    };

    const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        setSaving(true);
        try {
            const p = await apiService.uploadBusinessLogo(f);
            setProfile(p);
        } catch { 
            alert(t('business.logoUploadFailed')); 
        } finally { 
            setSaving(false); 
        }
    };

    if (loading) return (
        <div className="flex justify-center h-64 items-center">
            <Loader2 className="animate-spin text-primary-start w-8 h-8" />
        </div>
    );

    return (
        <motion.div 
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            className="w-full max-w-5xl mx-auto"
        >
            <form onSubmit={handleProfileSubmit} className="glass-panel border-x border-b border-border-main rounded-3xl p-8 sm:p-10 shadow-sm relative overflow-hidden">
                
                {/* Top Border Accent – now the only top border */}
                <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-primary-start to-primary-hover" />

                {/* --- HEADER SECTION: Title + Logo --- */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-12 gap-6 border-b border-border-main/50 pb-8">
                    
                    <div className="flex items-center gap-4">
                        <div className="p-3.5 bg-primary-start/10 text-primary-start rounded-2xl shadow-inner">
                            <Building2 size={28} />
                        </div>
                        <div>
                            <h3 className="text-2xl sm:text-3xl font-black text-text-primary tracking-tight">
                                {t('business.firmData', 'Të dhënat e Zyrës')}
                            </h3>
                            <p className="text-sm text-text-muted font-medium mt-1">
                                {t('business.firmDataSub', 'Përditësoni të dhënat publike dhe logon e zyrës suaj.')}
                            </p>
                        </div>
                    </div>

                    {/* Premium Logo Upload Circle */}
                    <div className="relative group cursor-pointer shrink-0" onClick={() => fileInputRef.current?.click()}>
                        <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-surface flex items-center justify-center overflow-hidden border border-border-main shadow-sm transition-all duration-300 group-hover:border-primary-start/50 group-hover:shadow-md hover-lift">
                            {logoLoading ? (
                                <Loader2 className="w-8 h-8 animate-spin text-primary-start" />
                            ) : logoSrc ? (
                                <img src={logoSrc} alt="Logo" className="w-full h-full object-contain p-2" onError={() => setLogoSrc(null)} />
                            ) : (
                                <div className="flex flex-col items-center gap-1 text-text-muted group-hover:text-primary-start transition-colors">
                                    <Upload className="w-6 h-6" />
                                    <span className="text-[9px] font-black uppercase tracking-widest">Logo</span>
                                </div>
                            )}
                            
                            {/* Hover Camera Overlay */}
                            <div className="absolute inset-0 bg-canvas/70 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center backdrop-blur-[2px]">
                                <Camera className="w-6 h-6 text-primary-start drop-shadow-md" />
                            </div>
                        </div>
                        <input type="file" ref={fileInputRef} onChange={handleLogoUpload} className="hidden" accept="image/*" />
                    </div>
                </div>

                {/* --- FORM FIELDS GRID --- */}
                <div className="space-y-8">
                    
                    {/* Firm Name (Full Width) */}
                    <div className="group">
                        <label className="block text-[11px] font-black text-text-muted uppercase tracking-widest mb-2 ml-1">
                            {t('business.firmNameLabel')}
                        </label>
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                <Building2 className="w-5 h-5 text-text-muted group-focus-within:text-primary-start transition-colors" />
                            </div>
                            <input 
                                type="text" 
                                name="firm_name" 
                                value={formData.firm_name} 
                                onChange={(e) => setFormData({ ...formData, firm_name: e.target.value })} 
                                className="glass-input bg-surface w-full rounded-xl py-3.5 pl-12 pr-4 text-sm font-semibold text-text-primary placeholder:text-text-disabled focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 hover:border-border-strong transition-all" 
                                placeholder={t('business.firmNamePlaceholder')} 
                            />
                        </div>
                    </div>

                    {/* Email & Phone (Two Columns) */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                        <div className="group">
                            <label className="block text-[11px] font-black text-text-muted uppercase tracking-widest mb-2 ml-1">
                                {t('business.publicEmail')}
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Mail className="w-5 h-5 text-text-muted group-focus-within:text-primary-start transition-colors" />
                                </div>
                                <input 
                                    type="email" 
                                    name="email_public" 
                                    value={formData.email_public} 
                                    onChange={(e) => setFormData({ ...formData, email_public: e.target.value })} 
                                    className="glass-input bg-surface w-full rounded-xl py-3.5 pl-12 pr-4 text-sm font-semibold text-text-primary placeholder:text-text-disabled focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 hover:border-border-strong transition-all" 
                                />
                            </div>
                        </div>
                        <div className="group">
                            <label className="block text-[11px] font-black text-text-muted uppercase tracking-widest mb-2 ml-1">
                                {t('business.phone')}
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Phone className="w-5 h-5 text-text-muted group-focus-within:text-primary-start transition-colors" />
                                </div>
                                <input 
                                    type="text" 
                                    name="phone" 
                                    value={formData.phone} 
                                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })} 
                                    className="glass-input bg-surface w-full rounded-xl py-3.5 pl-12 pr-4 text-sm font-semibold text-text-primary placeholder:text-text-disabled focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 hover:border-border-strong transition-all" 
                                />
                            </div>
                        </div>
                    </div>
                    
                    {/* Address (Full Width) */}
                    <div className="group">
                        <label className="block text-[11px] font-black text-text-muted uppercase tracking-widest mb-2 ml-1">
                            {t('business.address')}
                        </label>
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                <MapPin className="w-5 h-5 text-text-muted group-focus-within:text-primary-start transition-colors" />
                            </div>
                            <input 
                                type="text" 
                                name="address" 
                                value={formData.address} 
                                onChange={(e) => setFormData({ ...formData, address: e.target.value })} 
                                className="glass-input bg-surface w-full rounded-xl py-3.5 pl-12 pr-4 text-sm font-semibold text-text-primary placeholder:text-text-disabled focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 hover:border-border-strong transition-all" 
                            />
                        </div>
                    </div>
                    
                    {/* City & Website (Two Columns) */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                        <div className="group">
                            <label className="block text-[11px] font-black text-text-muted uppercase tracking-widest mb-2 ml-1">
                                {t('business.city')}
                            </label>
                            <input 
                                type="text" 
                                name="city" 
                                value={formData.city} 
                                onChange={(e) => setFormData({ ...formData, city: e.target.value })} 
                                className="glass-input bg-surface w-full rounded-xl py-3.5 px-5 text-sm font-semibold text-text-primary placeholder:text-text-disabled focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 hover:border-border-strong transition-all" 
                            />
                        </div>
                        <div className="group">
                            <label className="block text-[11px] font-black text-text-muted uppercase tracking-widest mb-2 ml-1">
                                {t('business.website')}
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Globe className="w-5 h-5 text-text-muted group-focus-within:text-primary-start transition-colors" />
                                </div>
                                <input 
                                    type="text" 
                                    name="website" 
                                    value={formData.website} 
                                    onChange={(e) => setFormData({ ...formData, website: e.target.value })} 
                                    className="glass-input bg-surface w-full rounded-xl py-3.5 pl-12 pr-4 text-sm font-semibold text-text-primary placeholder:text-text-disabled focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 hover:border-border-strong transition-all" 
                                />
                            </div>
                        </div>
                    </div>
                    
                    {/* Tax ID (Full Width) */}
                    <div className="group">
                        <label className="block text-[11px] font-black text-text-muted uppercase tracking-widest mb-2 ml-1">
                            {t('business.taxId')}
                        </label>
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                <CreditCard className="w-5 h-5 text-text-muted group-focus-within:text-primary-start transition-colors" />
                            </div>
                            <input 
                                type="text" 
                                name="tax_id" 
                                value={formData.tax_id} 
                                onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })} 
                                className="glass-input bg-surface w-full rounded-xl py-3.5 pl-12 pr-4 text-sm font-semibold text-text-primary placeholder:text-text-disabled focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 hover:border-border-strong transition-all" 
                            />
                        </div>
                    </div>
                </div>
                
                {/* --- FOOTER: Action Buttons --- */}
                <div className="pt-8 mt-8 border-t border-border-main/50 flex justify-end">
                    <button 
                        type="submit" 
                        disabled={saving} 
                        className="btn-primary flex items-center justify-center gap-2 px-10 py-3.5 rounded-xl text-xs font-black uppercase tracking-widest shadow-lg hover:-translate-y-0.5 hover:shadow-accent-glow transition-all disabled:opacity-50 disabled:hover:translate-y-0"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        {saving ? t('general.saving', 'Duke ruajtur...') : t('general.save')}
                    </button>
                </div>
            </form>
        </motion.div>
    );
};