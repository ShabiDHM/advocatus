// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - FORM OPTIMIZATION
// 1. SIMPLIFICATION: Removed 'case_number' and 'description' inputs.
// 2. AUTO-FILL: Sends generated case number to backend (though backend double-checks).
// 3. UX: Compact form focused on Title + Client.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Briefcase, Clock, CheckCircle } from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest } from '../data/types';
import { useAuth } from '../context/AuthContext';
import CaseCard from '../components/CaseCard';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  const initialNewCaseData = { 
    title: '', 
    clientName: '',
    clientEmail: '',
    clientPhone: ''
  };
  const [newCaseData, setNewCaseData] = useState(initialNewCaseData);

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    setIsLoading(true);
    try {
      const data = await apiService.getCases();
      const casesWithDefaults = data.map(c => ({
          ...c,
          document_count: c.document_count || 0,
          alert_count: c.alert_count || 0,
          event_count: c.event_count || 0,
      }));
      setCases(casesWithDefaults);
    } catch (error) {
      console.error("Failed to load cases", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Auto-generate a temp number for the payload (Backend will finalize/overwrite if needed)
      const tempCaseNumber = `R-${Date.now().toString().slice(-6)}`;
      
      const payload: CreateCaseRequest = {
          case_number: tempCaseNumber,
          title: newCaseData.title,
          case_name: newCaseData.title,
          description: "", // Default empty description
          clientName: newCaseData.clientName,
          clientEmail: newCaseData.clientEmail,
          clientPhone: newCaseData.clientPhone,
          status: 'open'
      };
      await apiService.createCase(payload);
      setShowCreateModal(false);
      setNewCaseData(initialNewCaseData);
      loadCases();
    } catch (error) {
      console.error("Failed to create case", error);
      alert(t('error.generic'));
    }
  };

  const handleDeleteCase = async (caseId: string) => {
    if (window.confirm(t('dashboard.confirmDelete'))) {
        try {
            await apiService.deleteCase(caseId);
            setCases(prevCases => prevCases.filter(c => c.id !== caseId));
        } catch (error) {
            console.error("Failed to delete case", error);
            alert(t('error.generic'));
        }
    }
  };

  const handleModalInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setNewCaseData(prev => ({ ...prev, [name]: value }));
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">{t('dashboard.welcome', { name: user?.username?.split(' ')[0] })}</h1>
          <p className="text-text-secondary mt-1">{t('dashboard.subtitle')}</p>
        </div>
        <button 
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-start to-primary-end rounded-xl text-white font-semibold shadow-lg glow-primary hover:scale-105 transition-transform"
        >
          <Plus size={20} /> {t('dashboard.newCase')}
        </button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard title={t('dashboard.activeCases')} value={cases.filter(c => c.status === 'open').length} icon={<Briefcase className="text-blue-400" />} color="bg-blue-500" />
        <StatCard title={t('dashboard.pendingDocs')} value={0} icon={<Clock className="text-yellow-400" />} color="bg-yellow-500" />
        <StatCard title={t('dashboard.completed')} value={cases.filter(c => c.status === 'closed').length} icon={<CheckCircle className="text-green-400" />} color="bg-green-500" />
      </div>

      {/* Case Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cases.map((c) => (
            <CaseCard 
              key={c.id} 
              caseData={c} 
              onDelete={handleDeleteCase} 
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-background-dark border border-glass-edge p-8 rounded-2xl w-full max-w-sm shadow-2xl">
            <h2 className="text-2xl font-bold text-white mb-6">{t('dashboard.createCaseTitle')}</h2>
            <form onSubmit={handleCreateCase} className="space-y-5">
              
              <div>
                <label className="block text-sm text-text-secondary mb-1">{t('dashboard.caseTitle')}</label>
                <input required name="title" type="text" value={newCaseData.title} onChange={handleModalInputChange} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
              </div>
              
              <div className="pt-4 border-t border-glass-edge/50">
                <label className="block text-sm text-text-secondary mb-2 font-medium text-primary-start">{t('caseCard.client')}</label>
                <div className="space-y-3">
                    <input required name="clientName" placeholder={t('dashboard.clientName')} type="text" value={newCaseData.clientName} onChange={handleModalInputChange} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
                    <input name="clientEmail" placeholder={t('dashboard.clientEmail')} type="email" value={newCaseData.clientEmail} onChange={handleModalInputChange} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
                    <input name="clientPhone" placeholder={t('dashboard.clientPhone')} type="tel" value={newCaseData.clientPhone} onChange={handleModalInputChange} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-8">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-4 py-2 rounded-lg hover:bg-white/10 text-text-secondary transition-colors">{t('general.cancel')}</button>
                <button type="submit" className="px-6 py-2 rounded-lg bg-primary-start hover:bg-primary-end text-white font-semibold shadow-lg transition-all">{t('general.create')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

const StatCard = ({ title, value, icon, color }: any) => (
  <div className="bg-background-light/30 backdrop-blur-md p-6 rounded-2xl border border-glass-edge flex items-center justify-between">
    <div>
      <p className="text-text-secondary text-sm font-medium mb-1">{title}</p>
      <h3 className="text-3xl font-bold text-white">{value}</h3>
    </div>
    <div className={`p-3 rounded-xl ${color} bg-opacity-20`}>{icon}</div>
  </div>
);

export default DashboardPage;