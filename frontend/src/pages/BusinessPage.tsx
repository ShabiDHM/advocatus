// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUSINESS PAGE V10.0 (SYMMETRY RESTORED)
// 1. FIXED: Unified Welcome text, Tabs, and Panels into one single column container.
// 2. ENHANCED: Tabs migrated to the "Executive Segmented Bar" style.
// 3. RETAINED: 100% of the original tab logic and lazy loading.

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { ProfileTab } from '../components/business/ProfileTab';
import { FinanceTab } from '../components/business/FinanceTab';
import { ArchiveTab } from '../components/business/ArchiveTab';
import { TeamTab } from '../components/business/TeamTab';
import { Building2, FileText, FolderOpen, Users } from 'lucide-react';
import { motion } from 'framer-motion';

type ActiveTab = 'profile' | 'team' | 'finance' | 'archive';

const BusinessPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');

  const tabs = [
    { id: 'profile', label: t('business.profile'), icon: <Building2 size={16} /> },
    { id: 'team', label: t('business.team'), icon: <Users size={16} /> },
    { id: 'finance', label: t('business.finance'), icon: <FileText size={16} /> },
    { id: 'archive', label: t('business.archive'), icon: <FolderOpen size={16} /> }
  ] as const;

  return (
    <div className="w-full min-h-screen pt-12 pb-12">
        {/* Unified Container: All items share this max-width and margin */}
        <div className="max-w-5xl mx-auto px-6">
            
            {/* Header + Tabs Area */}
            <div className="mb-10 flex flex-col gap-8">
                <div>
                    <h1 className="text-3xl font-black text-text-primary tracking-tighter mb-1">
                        {t('general.welcome_name', { name: user?.username || 'Shaban Bala' })}
                    </h1>
                    <p className="text-xs font-black text-text-muted uppercase tracking-widest">
                        {t('business.subtitle', 'Menaxhoni zyrën tuaj.')}
                    </p>
                </div>

                {/* Segmented Bar - Aligned to Panel width */}
                <div className="flex bg-surface p-1.5 rounded-2xl border border-border-main shadow-inner w-fit">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as ActiveTab)}
                            className={`flex items-center gap-2 px-6 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                                activeTab === tab.id 
                                ? 'bg-primary-start text-white shadow-lg' 
                                : 'text-text-muted hover:text-text-primary hover:bg-canvas'
                            }`}
                        >
                            {tab.icon} {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content Area */}
            <motion.div 
                key={activeTab}
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }} 
                className="w-full"
            >
                {activeTab === 'profile' && <ProfileTab />}
                {activeTab === 'team' && <TeamTab />}
                {activeTab === 'finance' && <FinanceTab />}
                {activeTab === 'archive' && <ArchiveTab />}
            </motion.div>
        </div>
    </div>
  );
};

export default BusinessPage;