// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUSINESS PAGE V9.5 (MOBILE NAVIGATION GRID FIX)
// 1. FIX: Switched navigation from scrollable flex to grid-cols-3 on mobile.
// 2. UI: Buttons are now fully centered and responsive.

import React, { useState } from 'react';
import { Building2, FileText, FolderOpen } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { ProfileTab } from '../components/business/ProfileTab';
import { FinanceTab } from '../components/business/FinanceTab';
import { ArchiveTab } from '../components/business/ArchiveTab';

type ActiveTab = 'profile' | 'finance' | 'archive';

const BusinessPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');

  // Helper function to capitalize the first letter of a string
  const capitalize = (s: string | undefined) => {
    if (!s) return 'Përdorues';
    return s.charAt(0).toUpperCase() + s.slice(1);
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 sm:mb-10 gap-4 sm:gap-6">
        <div>
            {/* Dynamic Welcome Message */}
            <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">
                {t('dashboard.welcome', { name: capitalize(user?.username) })}
            </h1>
            {/* Context Label */}
            <p className="text-gray-400 text-sm sm:text-base">
                {t('business.title', 'Qendra e Biznesit')}
            </p>
        </div>
        
        {/* FIX: Grid layout for mobile (3 cols), Flex for desktop */}
        <div className="w-full sm:w-auto grid grid-cols-3 sm:flex bg-background-light/10 p-1.5 rounded-2xl border border-white/10 backdrop-blur-md gap-1 sm:gap-0">
            <button 
                onClick={() => setActiveTab('profile')} 
                className={`flex items-center justify-center gap-1.5 sm:gap-2 px-1 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all duration-300 w-full sm:w-auto ${activeTab === 'profile' ? 'bg-primary-start text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
                <Building2 size={16} className="sm:w-[18px] sm:h-[18px]" />
                <span className="truncate">{t('business.profile')}</span>
            </button>
            <button 
                onClick={() => setActiveTab('finance')} 
                className={`flex items-center justify-center gap-1.5 sm:gap-2 px-1 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all duration-300 w-full sm:w-auto ${activeTab === 'finance' ? 'bg-primary-start text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
                <FileText size={16} className="sm:w-[18px] sm:h-[18px]" />
                <span className="truncate">{t('business.finance')}</span>
            </button>
            <button 
                onClick={() => setActiveTab('archive')} 
                className={`flex items-center justify-center gap-1.5 sm:gap-2 px-1 sm:px-5 py-2.5 rounded-xl text-xs sm:text-sm font-medium transition-all duration-300 w-full sm:w-auto ${activeTab === 'archive' ? 'bg-primary-start text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
                <FolderOpen size={16} className="sm:w-[18px] sm:h-[18px]" />
                <span className="truncate">{t('business.archive')}</span>
            </button>
        </div>
      </div>

      <div className="min-h-[500px]">
        {activeTab === 'profile' && <ProfileTab />}
        {activeTab === 'finance' && <FinanceTab />}
        {activeTab === 'archive' && <ArchiveTab />}
      </div>
    </div>
  );
};

export default BusinessPage;