// FILE: src/pages/BusinessPage.tsx
// PHOENIX PROTOCOL - BUSINESS PAGE V9.3 (UCA-COMPLIANT HEADER)
// 1. CHANGE: Username is now displayed in uppercase as per user request.

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

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 sm:mb-10 gap-4 sm:gap-6">
        <div>
            {/* Dynamic Welcome Message */}
            <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">
                {t('dashboard.welcome', { name: user?.username ? user.username.toUpperCase() : 'Përdorues' })}
            </h1>
            {/* Context Label */}
            <p className="text-gray-400 text-sm sm:text-base">
                {t('business.title', 'Qendra e Biznesit')}
            </p>
        </div>
        
        <div className="w-full sm:w-auto flex overflow-x-auto no-scrollbar bg-background-light/10 p-1.5 rounded-2xl border border-white/10 backdrop-blur-md">
            <button 
                onClick={() => setActiveTab('profile')} 
                className={`flex-shrink-0 flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${activeTab === 'profile' ? 'bg-primary-start text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
                <Building2 size={18} />
                <span>{t('business.profile')}</span>
            </button>
            <button 
                onClick={() => setActiveTab('finance')} 
                className={`flex-shrink-0 flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${activeTab === 'finance' ? 'bg-primary-start text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
                <FileText size={18} />
                <span>{t('business.finance')}</span>
            </button>
            <button 
                onClick={() => setActiveTab('archive')} 
                className={`flex-shrink-0 flex items-center gap-2 px-4 sm:px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-300 ${activeTab === 'archive' ? 'bg-primary-start text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}
            >
                <FolderOpen size={18} />
                <span>{t('business.archive')}</span>
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