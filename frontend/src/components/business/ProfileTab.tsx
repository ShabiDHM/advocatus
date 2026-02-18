// FILE: src/components/business/ProfileTab.tsx
// PHOENIX PROTOCOL - PROFILE TAB V4.0 (UNIFIED DESIGN)
// 1. LAYOUT: Unified into a single card design as per Image 2.
// 2. UI: Logo moved to top-right header position.
// 3. STYLING: Inputs and buttons matched to target design.

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
    Building2, Mail, Phone, Save, Upload, Loader2, Camera, MapPin, Globe, CreditCard
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
        firm_name: '', 
        email_public: '', 
        phone: '', 
        address: '', 
        city: '', 
        website: '', 
        tax_id: '', 
        branding_color: DEFAULT_COLOR
    });

    // --- DATA FETCHING (Preserved) ---
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

    // --- LOGO HANDLING (Preserved) ---
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
            // Optional: You can replace this alert with a toast notification if available
            // alert(t('settings.successMessage')); 
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
            className="w-full"
        >
            <form onSubmit={handleProfileSubmit} className="glass-panel rounded-2xl p-6 sm:p-8 relative overflow-hidden border border-white/5 bg-[#0A0F1C]/80 backdrop-blur-md">
                
                {/* Top Border Accent */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-success-start to-success-end" />

                {/* --- HEADER SECTION: Title + Logo --- */}
                <div className="flex justify-between items-start mb-10">
                    <div className="mt-2">
                        <h3 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-3">
                            <Building2 className="w-6 h-6 sm:w-7 sm:h-7 text-success-start" />
                            {t('business.firmData')}
                        </h3>
                    </div>

                    {/* Logo Circle (Top Right) */}
                    <div className="relative group cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-white flex items-center justify-center overflow-hidden border-2 border-white/20 shadow-lg transition-transform group-hover:scale-105">
                            {logoLoading ? (
                                <Loader2 className="w-6 h-6 animate-spin text-primary-start" />
                            ) : logoSrc ? (
                                <img src={logoSrc} alt="Logo" className="w-full h-full object-contain p-1" onError={() => setLogoSrc(null)} />
                            ) : (
                                <Upload className="w-6 h-6 text-gray-400" />
                            )}
                        </div>
                        {/* Hover Overlay */}
                        <div className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <Camera className="w-5 h-5 text-white" />
                        </div>
                        <input type="file" ref={fileInputRef} onChange={handleLogoUpload} className="hidden" accept="image/*" />
                    </div>
                </div>

                {/* --- FORM FIELDS --- */}
                <div className="space-y-6">
                    
                    {/* Firm Name (Full Width) */}
                    <div className="group">
                        <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                            {t('business.firmNameLabel')}
                        </label>
                        <div className="relative">
                            <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" />
                            <input 
                                type="text" 
                                name="firm_name" 
                                value={formData.firm_name} 
                                onChange={(e) => setFormData({ ...formData, firm_name: e.target.value })} 
                                className="w-full bg-[#111827] border border-gray-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:border-success-start/50 focus:ring-1 focus:ring-success-start/50 transition-all" 
                                placeholder={t('business.firmNamePlaceholder')} 
                            />
                        </div>
                    </div>

                    {/* Email & Phone (Two Columns) */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        <div className="group">
                            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                                {t('business.publicEmail')}
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" />
                                <input 
                                    type="email" 
                                    name="email_public" 
                                    value={formData.email_public} 
                                    onChange={(e) => setFormData({ ...formData, email_public: e.target.value })} 
                                    className="w-full bg-[#111827] border border-gray-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:border-success-start/50 focus:ring-1 focus:ring-success-start/50 transition-all" 
                                />
                            </div>
                        </div>
                        <div className="group">
                            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                                {t('business.phone')}
                            </label>
                            <div className="relative">
                                <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" />
                                <input 
                                    type="text" 
                                    name="phone" 
                                    value={formData.phone} 
                                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })} 
                                    className="w-full bg-[#111827] border border-gray-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:border-success-start/50 focus:ring-1 focus:ring-success-start/50 transition-all" 
                                />
                            </div>
                        </div>
                    </div>
                    
                    {/* Address (Full Width) */}
                    <div className="group">
                        <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                            {t('business.address')}
                        </label>
                        <div className="relative">
                            <MapPin className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" />
                            <input 
                                type="text" 
                                name="address" 
                                value={formData.address} 
                                onChange={(e) => setFormData({ ...formData, address: e.target.value })} 
                                className="w-full bg-[#111827] border border-gray-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:border-success-start/50 focus:ring-1 focus:ring-success-start/50 transition-all" 
                            />
                        </div>
                    </div>
                    
                    {/* City & Website (Two Columns) */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        <div className="group">
                            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                                {t('business.city')}
                            </label>
                            <input 
                                type="text" 
                                name="city" 
                                value={formData.city} 
                                onChange={(e) => setFormData({ ...formData, city: e.target.value })} 
                                className="w-full bg-[#111827] border border-gray-800 rounded-xl py-3 px-4 text-white placeholder-gray-600 focus:outline-none focus:border-success-start/50 focus:ring-1 focus:ring-success-start/50 transition-all" 
                            />
                        </div>
                        <div className="group">
                            <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                                {t('business.website')}
                            </label>
                            <div className="relative">
                                <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" />
                                <input 
                                    type="text" 
                                    name="website" 
                                    value={formData.website} 
                                    onChange={(e) => setFormData({ ...formData, website: e.target.value })} 
                                    className="w-full bg-[#111827] border border-gray-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:border-success-start/50 focus:ring-1 focus:ring-success-start/50 transition-all" 
                                />
                            </div>
                        </div>
                    </div>
                    
                    {/* Tax ID (Full Width) */}
                    <div className="group">
                        <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
                            {t('business.taxId')}
                        </label>
                        <div className="relative">
                            <CreditCard className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 group-focus-within:text-success-start transition-colors" />
                            <input 
                                type="text" 
                                name="tax_id" 
                                value={formData.tax_id} 
                                onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })} 
                                className="w-full bg-[#111827] border border-gray-800 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-600 focus:outline-none focus:border-success-start/50 focus:ring-1 focus:ring-success-start/50 transition-all" 
                            />
                        </div>
                    </div>
                </div>
                
                {/* --- FOOTER: Save Button --- */}
                <div className="pt-8 flex justify-end mt-4">
                    <button 
                        type="submit" 
                        disabled={saving} 
                        className="flex items-center gap-2 px-10 py-3 bg-success-start hover:bg-success-end text-white rounded-lg font-bold shadow-lg shadow-success-start/20 transition-all disabled:opacity-50 hover:scale-[1.02] active:scale-95"
                    >
                        {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
                        {t('general.save')}
                    </button>
                </div>
            </form>
        </motion.div>
    );
};