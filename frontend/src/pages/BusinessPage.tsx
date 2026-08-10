// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUSINESS PAGE V13.4 (REMOVED ADMIN ROLE SUFFIX)

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
    { id: 'profile', label: t('business.profile'), icon: <Building2 size={15} /> },
    { id: 'team', label: t('business.team'), icon: <Users size={15} /> },
    { id: 'finance', label: t('business.finance'), icon: <FileText size={15} /> },
    { id: 'archive', label: t('business.archive'), icon: <FolderOpen size={15} /> }
  ] as const;

  return (
    <div className="w-full min-h-screen pt-12 pb-12 bg-canvas">
      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        
        {/* Executive Row: Greeting (Left) and Tabs (Right) */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-10">
            
            {/* The Greeting without (admin) */}
            <div className="text-center lg:text-left">
                <h1 className="text-2xl sm:text-3xl font-black text-text-primary uppercase tracking-widest mb-1 select-none">
                    {t('general.welcome', 'Mirësevini')}
                </h1>
                <p className="text-base sm:text-lg font-bold text-text-secondary tracking-wide">
                    {formatName(user?.full_name || user?.username)}
                </p>
            </div>

            {/* Navigation Tabs - Standardized h-11 / 44px capsule layout */}
            <div className="glass-panel p-1 rounded-full bg-surface border border-main shadow-sm w-full lg:w-auto flex flex-wrap justify-center gap-1 h-11 items-center shrink-0">
                {tabs.map((tab) => (
                    <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveTab(tab.id as ActiveTab)}
                        className={`
                            flex items-center gap-2 px-4 sm:px-6 h-9 rounded-full text-[10px] sm:text-xs 
                            font-black uppercase tracking-wider transition-all whitespace-nowrap focus:outline-none
                            ${activeTab === tab.id 
                                ? 'bg-primary-start text-white shadow-lg shadow-primary-start/15' 
                                : 'text-text-muted hover:text-text-primary hover:bg-hover'
                            }
                        `}
                    >
                        {tab.icon} 
                        <span className="hidden sm:inline">{tab.label}</span>
                        <span className="sm:hidden">{tab.label.substring(0, 3)}</span>
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
            {renderActiveTab()}
        </motion.div>
      </div>
    </div>
  );
};

export default BusinessPage;