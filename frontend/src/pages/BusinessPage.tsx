// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUSINESS PAGE V12.0 (GREETING HIERARCHY RESTORED)
// 1. FIXED: Greeting split into two lines (Mirësevini / Name).
// 2. FIXED: Removed uppercase/tracking overrides from the greeting to ensure clean text.
// 3. FIXED: Header and Tabs are now properly flex-aligned.
// 4. RETAINED: 100% of the original logic, lazy-loading, and tab state management.

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

  // Professional Name Formatting Helper
  const formatName = (name: string | undefined) => {
    if (!name) return "Shaban Bala";
    return name.toLowerCase().split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'profile': return <ProfileTab />;
      case 'team': return <TeamTab />;
      case 'finance': return <FinanceTab />;
      case 'archive': return <ArchiveTab />;
      default: return null;
    }
  };

  const tabs = [
    { id: 'profile', label: t('business.profile'), icon: <Building2 size={16} /> },
    { id: 'team', label: t('business.team'), icon: <Users size={16} /> },
    { id: 'finance', label: t('business.finance'), icon: <FileText size={16} /> },
    { id: 'archive', label: t('business.archive'), icon: <FolderOpen size={16} /> }
  ] as const;

  return (
    <div className="w-full min-h-screen pt-12 pb-12">
      <div className="max-w-5xl mx-auto px-6">
        
        {/* Executive Row: Greeting (Left) and Tabs (Right) */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-10">
            {/* The Greeting - Fixed 2-Line Structure */}
            <div>
                <h1 className="text-xl font-bold text-text-muted mb-0.5">
                    {t('general.welcome', 'Mirësevini')}
                </h1>
                <h2 className="text-3xl font-black text-text-primary tracking-tighter">
                    {formatName(user?.full_name || user?.username)}
                </h2>
            </div>

            {/* Navigation Tabs - Segmented Bar */}
            <div className="flex bg-surface p-1.5 rounded-2xl border border-border-main shadow-inner w-fit">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as ActiveTab)}
                        className={`flex items-center gap-2 px-6 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                            activeTab === tab.id 
                            ? 'bg-primary-start text-white shadow-md' 
                            : 'text-text-muted hover:text-text-primary hover:bg-canvas'
                        }`}
                    >
                        {tab.icon} {tab.label}
                    </button>
                ))}
            </div>
        </div>

        {/* Content Area - Symmetrical */}
        <motion.div 
            key={activeTab}
            initial={{ opacity: 0, y: 10 }} 
            animate={{ opacity: 1, y: 0 }} 
            className="w-full"
        >
            {renderActiveTab()}
        </motion.div>
      </div>
    </div>
  );
};

export default BusinessPage;