// FILE: src/pages/BusinessPage.tsx (second app)
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { ProfileTab } from '../components/business/ProfileTab';
import { FinanceTab } from '../components/business/FinanceTab';
import { ArchiveTab } from '../components/business/ArchiveTab';
import { TeamTab } from '../components/business/TeamTab';
import { Building2, FileText, FolderOpen, Users } from 'lucide-react';

type ActiveTab = 'profile' | 'team' | 'finance' | 'archive';

const BusinessPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<ActiveTab>('profile');

  const capitalize = (s: string | undefined) => {
    if (!s) return '';
    return s.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome text – now inside the same horizontal wrapper */}
      <div className="mb-6 sm:mb-10">
        <h1 className="text-2xl sm:text-3xl font-bold text-text-primary mb-2 tracking-tight">
          {t('general.welcome_name', { name: capitalize(user?.username) })}
        </h1>
        <p className="text-text-secondary text-sm sm:text-base">
          {t('business.subtitle')}
        </p>
      </div>

      {/* Tabs (mobile‑friendly) – you can keep the original tabs style or upgrade to segmented bar */}
      <div className="flex flex-wrap gap-2 mb-6 border-b border-border-main pb-4">
        <button
          onClick={() => setActiveTab('profile')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
            activeTab === 'profile' ? 'btn-primary shadow-sm' : 'text-text-secondary hover:text-text-primary hover:bg-hover'
          }`}
        >
          <Building2 size={16} /> {t('business.profile')}
        </button>
        <button
          onClick={() => setActiveTab('team')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
            activeTab === 'team' ? 'btn-primary shadow-sm' : 'text-text-secondary hover:text-text-primary hover:bg-hover'
          }`}
        >
          <Users size={16} /> {t('business.team')}
        </button>
        <button
          onClick={() => setActiveTab('finance')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
            activeTab === 'finance' ? 'btn-primary shadow-sm' : 'text-text-secondary hover:text-text-primary hover:bg-hover'
          }`}
        >
          <FileText size={16} /> {t('business.finance')}
        </button>
        <button
          onClick={() => setActiveTab('archive')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
            activeTab === 'archive' ? 'btn-primary shadow-sm' : 'text-text-secondary hover:text-text-primary hover:bg-hover'
          }`}
        >
          <FolderOpen size={16} /> {t('business.archive')}
        </button>
      </div>

      <div className="min-h-[500px] animate-in fade-in slide-in-from-bottom-4 duration-500">
        {renderActiveTab()}
      </div>
    </div>
  );
};

export default BusinessPage;