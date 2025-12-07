// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD BRIEFING
// 1. FEATURE: Auto-opens 'Daily Briefing' popup if events exist for today.
// 2. LOGIC: Fetches calendar events in parallel with cases to power the briefing.
// 3. UX: Non-intrusive; only appears if actionable items exist.

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent } from '../data/types';
import { useAuth } from '../context/AuthContext';
import CaseCard from '../components/CaseCard';
import DayEventsModal from '../components/DayEventsModal'; // PHOENIX: Import
import { isSameDay, parseISO } from 'date-fns';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  // PHOENIX: Briefing State
  const [todaysEvents, setTodaysEvents] = useState<CalendarEvent[]>([]);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const hasCheckedBriefing = useRef(false);

  const initialNewCaseData = { 
    title: '', 
    clientName: '',
    clientEmail: '',
    clientPhone: ''
  };
  const [newCaseData, setNewCaseData] = useState(initialNewCaseData);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // PHOENIX: Parallel Fetch (Cases + Calendar)
      const [casesData, eventsData] = await Promise.all([
          apiService.getCases(),
          apiService.getCalendarEvents()
      ]);

      // 1. Process Cases
      const casesWithDefaults = casesData.map(c => ({
          ...c,
          document_count: c.document_count || 0,
          alert_count: c.alert_count || 0,
          event_count: c.event_count || 0,
          finding_count: c.finding_count || 0,
      }));
      setCases(casesWithDefaults);

      // 2. Process Briefing (Run Once)
      if (!hasCheckedBriefing.current && eventsData.length > 0) {
          const today = new Date();
          const matches = eventsData.filter(e => isSameDay(parseISO(e.start_date), today));
          
          if (matches.length > 0) {
              setTodaysEvents(matches);
              setIsBriefingOpen(true);
          }
          hasCheckedBriefing.current = true;
      }

    } catch (error) {
      console.error("Failed to load dashboard data", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const tempCaseNumber = `R-${Date.now().toString().slice(-6)}`;
      
      const payload: CreateCaseRequest = {
          case_number: tempCaseNumber,
          title: newCaseData.title,
          case_name: newCaseData.title,
          description: "", 
          clientName: newCaseData.clientName,
          clientEmail: newCaseData.clientEmail,
          clientPhone: newCaseData.clientPhone,
          status: 'open'
      };
      await apiService.createCase(payload);
      setShowCreateModal(false);
      setNewCaseData(initialNewCaseData);
      loadData(); // Reload all data
    } catch (error) {
      console.error("Failed to create case", error);
      alert(t('error.generic'));
    }
  };

  const handleDeleteCase = async (caseId: string) => {
    if (window.confirm(t('dashboard.confirmDelete', 'A jeni i sigurt?'))) {
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

  const getFormattedName = () => {
    if (!user || !user.username) return '';
    const namePart = user.username.trim().split(' ')[0];
    if (!namePart) return '';
    return namePart.charAt(0).toUpperCase() + namePart.slice(1).toLowerCase();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            {t('dashboard.welcome', { name: getFormattedName() })}
          </h1>
          <p className="text-gray-400 mt-1">{t('dashboard.subtitle')}</p>
        </div>
        <button 
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-white font-semibold shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 hover:scale-[1.02] transition-all"
        >
          <Plus size={20} /> {t('dashboard.newCase')}
        </button>
      </div>

      {/* Case Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div></div>
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
          <div className="bg-gray-900 border border-white/10 p-8 rounded-2xl w-full max-w-sm shadow-2xl">
            <h2 className="text-2xl font-bold text-white mb-6">{t('dashboard.createCaseTitle')}</h2>
            <form onSubmit={handleCreateCase} className="space-y-5">
              
              <div>
                <label className="block text-sm text-gray-400 mb-1">{t('dashboard.caseTitle')}</label>
                <input required name="title" type="text" value={newCaseData.title} onChange={handleModalInputChange} className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-indigo-500 outline-none transition-colors" />
              </div>
              
              <div className="pt-4 border-t border-white/10">
                <label className="block text-sm text-gray-400 mb-2 font-medium text-indigo-400">{t('caseCard.client')}</label>
                <div className="space-y-3">
                    <input required name="clientName" placeholder={t('dashboard.clientName')} type="text" value={newCaseData.clientName} onChange={handleModalInputChange} className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-indigo-500 outline-none transition-colors" />
                    <input name="clientEmail" placeholder={t('dashboard.clientEmail')} type="email" value={newCaseData.clientEmail} onChange={handleModalInputChange} className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-indigo-500 outline-none transition-colors" />
                    <input name="clientPhone" placeholder={t('dashboard.clientPhone')} type="tel" value={newCaseData.clientPhone} onChange={handleModalInputChange} className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-indigo-500 outline-none transition-colors" />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-8">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-4 py-2 rounded-lg hover:bg-white/5 text-gray-400 transition-colors">{t('general.cancel')}</button>
                <button type="submit" className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-lg transition-all">{t('general.create')}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PHOENIX: Daily Briefing Modal */}
      <DayEventsModal 
        isOpen={isBriefingOpen}
        onClose={() => setIsBriefingOpen(false)}
        date={new Date()} // Always today
        events={todaysEvents}
        t={t}
        onAddEvent={() => {
            setIsBriefingOpen(false);
            // Optional: Redirect to calendar or show add modal here
            window.location.href = '/calendar'; 
        }}
      />
    </div>
  );
};

export default DashboardPage;