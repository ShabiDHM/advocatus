// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD (CLEANED)
// 1. REMOVED: Unused imports (Search, AlertTriangle).
// 2. FUNCTIONAL: Case creation and stats display.

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Plus, Briefcase, Clock, CheckCircle } from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest } from '../data/types';
import { useAuth } from '../context/AuthContext';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCaseData, setNewCaseData] = useState({ title: '', case_number: '', description: '' });

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      const data = await apiService.getCases();
      setCases(data);
    } catch (error) {
      console.error("Failed to load cases", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload: CreateCaseRequest = {
          case_number: newCaseData.case_number,
          title: newCaseData.title,
          case_name: newCaseData.title, // Mapped alias
          description: newCaseData.description,
          status: 'open'
      };
      await apiService.createCase(payload);
      setShowCreateModal(false);
      setNewCaseData({ title: '', case_number: '', description: '' });
      loadCases();
    } catch (error) {
      console.error("Failed to create case", error);
      alert(t('error.generic'));
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">{t('dashboard.welcome', { name: user?.full_name?.split(' ')[0] })}</h1>
          <p className="text-text-secondary mt-1">{t('dashboard.subtitle', 'Pasqyra e rasteve tuaja aktive.')}</p>
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
            <Link key={c.id} to={`/cases/${c.id}`} className="group bg-background-light/30 backdrop-blur-md p-6 rounded-2xl border border-glass-edge hover:border-primary-start/50 transition-all hover:shadow-xl hover:-translate-y-1 block">
              <div className="flex justify-between items-start mb-4">
                <div className="p-3 rounded-xl bg-white/5 group-hover:bg-primary-start/20 transition-colors">
                  <Briefcase className="h-6 w-6 text-text-primary group-hover:text-primary-start" />
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-medium ${c.status === 'open' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                  {c.status.toUpperCase()}
                </span>
              </div>
              <h3 className="text-xl font-bold text-white mb-2 group-hover:text-primary-start transition-colors truncate">{c.case_name || c.title}</h3>
              <p className="text-text-secondary text-sm mb-4 line-clamp-2">{c.description || "No description."}</p>
              <div className="flex items-center text-xs text-text-secondary pt-4 border-t border-glass-edge/50">
                <Clock size={14} className="mr-1" /> {new Date(c.created_at).toLocaleDateString()}
                <span className="mx-2">•</span>
                <span>#{c.case_number}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-background-dark border border-glass-edge p-8 rounded-2xl w-full max-w-md shadow-2xl">
            <h2 className="text-2xl font-bold text-white mb-6">{t('dashboard.createCaseTitle')}</h2>
            <form onSubmit={handleCreateCase} className="space-y-4">
              <div>
                <label className="block text-sm text-text-secondary mb-1">{t('dashboard.caseNumber')}</label>
                <input required type="text" value={newCaseData.case_number} onChange={e => setNewCaseData({...newCaseData, case_number: e.target.value})} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">{t('dashboard.caseTitle')}</label>
                <input required type="text" value={newCaseData.title} onChange={e => setNewCaseData({...newCaseData, title: e.target.value})} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">{t('dashboard.description')}</label>
                <textarea value={newCaseData.description} onChange={e => setNewCaseData({...newCaseData, description: e.target.value})} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" rows={3} />
              </div>
              <div className="flex justify-end gap-3 mt-6">
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