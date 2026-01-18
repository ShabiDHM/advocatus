// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUSINESS PAGE V11.0 (TEAM INTEGRATION)
// 1. FEATURE: Added 'Team' tab for Organization Management.
// 2. LAYOUT: Updated tab grid to support 4 items (Profile, Team, Finance, Archive).
// 3. LOGIC: Connected TeamTab component.

import React, { useState } from 'react';
import { Building2, FileText, FolderOpen, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { ProfileTab } from '../components/business/ProfileTab';
import { FinanceTab } from '../components/business/FinanceTab';
import { ArchiveTab } from '../components/business/ArchiveTab';
import { TeamTab } from '../components/business/TeamTab';

// PHOENIX UPDATE: Added 'team' to allowed tabs
type ActiveTab = 'profile' | 'team' | 'finance' | 'archive';

const BusinessPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');

  const capitalize = (s: string | undefined) => {
    if (!s) return 'Përdorues';
    return s
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Component mapping
  const renderActiveTab = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileTab />;
      case 'team':
        return <TeamTab />;
      case 'finance':
        return <FinanceTab />;
      case 'archive':
        return <ArchiveTab />;
      default:
        return null;
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 h-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 sm:mb-10 gap-4 sm:gap-6">
        <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2 tracking-tight">
                {t('dashboard.welcome', { name: capitalize(user?.username) })}
            </h1>
            <p className="text-text-secondary text-sm sm:text-base">
                {t('business.title', 'Qendra e Biznesit')}
            </p>
        </div>
        
        {/* Tab Switcher - Updated for 4 cols on mobile */}
        <div className="w-full sm:w-auto grid grid-cols-4 sm:flex glass-panel p-1.5 rounded-xl gap-1 sm:gap-0">
            <button 
                onClick={() => setActiveTab('profile')} 
                className={`flex items-center justify-center gap-1.5 sm:gap-2 px-1 sm:px-5 py-2.5 rounded-lg text-xs sm:text-sm font-bold transition-all duration-300 w-full sm:w-auto ${activeTab === 'profile' ? 'bg-gradient-to-r from-primary-start to-primary-end text-white shadow-lg shadow-primary-start/20' : 'text-text-secondary hover:text-white hover:bg-white/5'}`}
                title={t('business.profile')}
            >
                <Building2 size={16} className="sm:w-[18px] sm:h-[18px]" />
                <span className="truncate hidden sm:inline">{t('business.profile')}</span>
                <span className="sm:hidden">Profile</span>
            </button>
            <button 
                onClick={() => setActiveTab('team')} 
                className={`flex items-center justify-center gap-1.5 sm:gap-2 px-1 sm:px-5 py-2.5 rounded-lg text-xs sm:text-sm font-bold transition-all duration-300 w-full sm:w-auto ${activeTab === 'team' ? 'bg-gradient-to-r from-primary-start to-primary-end text-white shadow-lg shadow-primary-start/20' : 'text-text-secondary hover:text-white hover:bg-white/5'}`}
                title={t('business.team', 'Team')}
            >
                <Users size={16} className="sm:w-[18px] sm:h-[18px]" />
                <span className="truncate hidden sm:inline">{t('business.team', 'Team')}</span>
                <span className="sm:hidden">Team</span>
            </button>
            <button 
                onClick={() => setActiveTab('finance')} 
                className={`flex items-center justify-center gap-1.5 sm:gap-2 px-1 sm:px-5 py-2.5 rounded-lg text-xs sm:text-sm font-bold transition-all duration-300 w-full sm:w-auto ${activeTab === 'finance' ? 'bg-gradient-to-r from-primary-start to-primary-end text-white shadow-lg shadow-primary-start/20' : 'text-text-secondary hover:text-white hover:bg-white/5'}`}
                title={t('business.finance')}
            >
                <FileText size={16} className="sm:w-[18px] sm:h-[18px]" />
                <span className="truncate hidden sm:inline">{t('business.finance')}</span>
                <span className="sm:hidden">Fin.</span>
            </button>
            <button 
                onClick={() => setActiveTab('archive')} 
                className={`flex items-center justify-center gap-1.5 sm:gap-2 px-1 sm:px-5 py-2.5 rounded-lg text-xs sm:text-sm font-bold transition-all duration-300 w-full sm:w-auto ${activeTab === 'archive' ? 'bg-gradient-to-r from-primary-start to-primary-end text-white shadow-lg shadow-primary-start/20' : 'text-text-secondary hover:text-white hover:bg-white/5'}`}
                title={t('business.archive')}
            >
                <FolderOpen size={16} className="sm:w-[18px] sm:h-[18px]" />
                <span className="truncate hidden sm:inline">{t('business.archive')}</span>
                <span className="sm:hidden">Arch.</span>
            </button>
        </div>
      </div>

      <div className="min-h-[500px] animate-in fade-in slide-in-from-bottom-4 duration-500">
        {renderActiveTab()}
      </div>
    </div>
  );
};

export default BusinessPage;