// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUSINESS PAGE (CLEANED)
// 1. REMOVED: Unused icon imports.
// 2. FUNCTIONAL: Profile editing and Logo upload.

import React, { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Building2, BarChart3, Save, Upload, Briefcase, FileText, Clock } from 'lucide-react';
import { apiService, API_V1_URL } from '../services/api';
import { BusinessProfile } from '../data/types';

const StatCard: React.FC<{ title: string; value: string | number; icon: React.ReactNode; color: string }> = ({ title, value, icon, color }) => (
    <div className="bg-background-light/30 backdrop-blur-md p-6 rounded-2xl border border-glass-edge shadow-lg flex items-center justify-between">
        <div>
            <p className="text-text-secondary text-sm font-medium mb-1">{title}</p>
            <h3 className="text-2xl font-bold text-text-primary">{value}</h3>
        </div>
        <div className={`p-3 rounded-xl ${color} bg-opacity-20`}>
            {icon}
        </div>
    </div>
);

const BusinessPage: React.FC = () => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState<'dashboard' | 'profile'>('dashboard');
    const [profile, setProfile] = useState<BusinessProfile | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    
    const [stats, setStats] = useState({ cases: 0 });
    const fileInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [profData, casesData] = await Promise.all([
                apiService.getBusinessProfile(),
                apiService.getCases()
            ]);
            setProfile(profData);
            setStats({ cases: casesData.length });
        } catch (error) {
            console.error("Failed to load business data", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSaveProfile = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!profile) return;
        setIsSaving(true);
        try {
            const updated = await apiService.updateBusinessProfile({
                firm_name: profile.firm_name,
                address: profile.address,
                city: profile.city,
                phone: profile.phone,
                email_public: profile.email_public,
                website: profile.website,
                tax_id: profile.tax_id
            });
            setProfile(updated);
            alert(t('general.saveSuccess', 'Profili u ruajt me sukses!'));
        } catch (error) {
            console.error(error);
            alert(t('error.generic'));
        } finally {
            setIsSaving(false);
        }
    };

    const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        try {
            const updated = await apiService.uploadBusinessLogo(file);
            setProfile(updated);
        } catch (error) {
            console.error("Logo upload failed", error);
            alert("Ngarkimi i logos dështoi.");
        }
    };

    if (isLoading) return <div className="flex justify-center items-center h-96"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-secondary-start"></div></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-text-primary mb-2">{t('business.title', 'Qendra e Biznesit')}</h1>
                <p className="text-text-secondary">{t('business.subtitle', 'Menaxhoni identitetin e zyrës suaj ligjore.')}</p>
            </div>

            <div className="flex space-x-4 mb-8 border-b border-glass-edge">
                <button onClick={() => setActiveTab('dashboard')} className={`pb-3 px-1 text-sm font-medium transition-colors relative ${activeTab === 'dashboard' ? 'text-secondary-start' : 'text-text-secondary hover:text-text-primary'}`}>
                    <div className="flex items-center gap-2"><BarChart3 size={18} />{t('business.dashboard', 'Pasqyra')}</div>
                    {activeTab === 'dashboard' && <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-secondary-start" />}
                </button>
                <button onClick={() => setActiveTab('profile')} className={`pb-3 px-1 text-sm font-medium transition-colors relative ${activeTab === 'profile' ? 'text-secondary-start' : 'text-text-secondary hover:text-text-primary'}`}>
                    <div className="flex items-center gap-2"><Building2 size={18} />{t('business.profile', 'Profili i Zyrës')}</div>
                    {activeTab === 'profile' && <motion.div layoutId="activeTab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-secondary-start" />}
                </button>
            </div>

            <div className="min-h-[500px]">
                {activeTab === 'dashboard' && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <StatCard title={t('business.totalCases', 'Raste Totale')} value={stats.cases} icon={<Briefcase className="text-blue-400" />} color="bg-blue-500" />
                        <StatCard title={t('business.documentsProcessed', 'Dokumente të Procesuara')} value="--" icon={<FileText className="text-green-400" />} color="bg-green-500" />
                        <StatCard title={t('business.efficiency', 'Efiçenca')} value="High" icon={<Clock className="text-purple-400" />} color="bg-purple-500" />
                    </motion.div>
                )}

                {activeTab === 'profile' && profile && (
                    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="col-span-1">
                            <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge text-center">
                                <div className="w-32 h-32 mx-auto bg-background-dark rounded-full flex items-center justify-center mb-4 overflow-hidden border-2 border-secondary-start/30 relative group">
                                    {profile.logo_url ? <img src={`${API_V1_URL}${profile.logo_url}`} alt="Logo" className="w-full h-full object-cover" /> : <Building2 className="w-12 h-12 text-text-secondary" />}
                                    <div className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer" onClick={() => fileInputRef.current?.click()}><Upload className="text-white w-8 h-8" /></div>
                                </div>
                                <input type="file" ref={fileInputRef} onChange={handleLogoUpload} className="hidden" accept="image/*" />
                                <button onClick={() => fileInputRef.current?.click()} className="px-4 py-2 rounded-lg bg-secondary-start/10 text-secondary-start text-sm font-medium hover:bg-secondary-start/20 transition-colors">{t('business.changeLogo', 'Ndrysho Logon')}</button>
                            </div>
                        </div>
                        <div className="col-span-1 lg:col-span-2">
                            <form onSubmit={handleSaveProfile} className="space-y-6 bg-background-light/30 p-6 sm:p-8 rounded-2xl border border-glass-edge">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div><label className="block text-sm font-medium text-text-secondary mb-1">{t('business.firmName', 'Emri i Zyrës')}</label><input type="text" value={profile.firm_name} onChange={(e) => setProfile({...profile, firm_name: e.target.value})} className="w-full px-4 py-2 bg-background-dark border border-glass-edge rounded-lg text-text-primary focus:ring-1 focus:ring-secondary-start outline-none" /></div>
                                    <div><label className="block text-sm font-medium text-text-secondary mb-1">{t('business.taxId', 'Numri Fiskal')}</label><input type="text" value={profile.tax_id || ''} onChange={(e) => setProfile({...profile, tax_id: e.target.value})} className="w-full px-4 py-2 bg-background-dark border border-glass-edge rounded-lg text-text-primary focus:ring-1 focus:ring-secondary-start outline-none" /></div>
                                    <div className="md:col-span-2"><label className="block text-sm font-medium text-text-secondary mb-1">{t('business.address', 'Adresa')}</label><input type="text" value={profile.address || ''} onChange={(e) => setProfile({...profile, address: e.target.value})} className="w-full px-4 py-2 bg-background-dark border border-glass-edge rounded-lg text-text-primary focus:ring-1 focus:ring-secondary-start outline-none" /></div>
                                    <div><label className="block text-sm font-medium text-text-secondary mb-1">{t('business.city', 'Qyteti')}</label><input type="text" value={profile.city || ''} onChange={(e) => setProfile({...profile, city: e.target.value})} className="w-full px-4 py-2 bg-background-dark border border-glass-edge rounded-lg text-text-primary focus:ring-1 focus:ring-secondary-start outline-none" /></div>
                                    <div><label className="block text-sm font-medium text-text-secondary mb-1">{t('business.website', 'Webfaqja')}</label><input type="text" value={profile.website || ''} onChange={(e) => setProfile({...profile, website: e.target.value})} className="w-full px-4 py-2 bg-background-dark border border-glass-edge rounded-lg text-text-primary focus:ring-1 focus:ring-secondary-start outline-none" /></div>
                                </div>
                                <div className="pt-4 flex justify-end"><button type="submit" disabled={isSaving} className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-secondary-start to-secondary-end text-white font-semibold shadow-lg hover:opacity-90 transition-opacity disabled:opacity-50">{isSaving ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}<span>{t('general.save', 'Ruaj')}</span></button></div>
                            </form>
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    );
};

const Loader2 = ({ className }: { className?: string }) => (<svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>);

export default BusinessPage;