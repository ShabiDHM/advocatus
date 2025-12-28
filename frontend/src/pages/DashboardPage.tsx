// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V6.0 (GLASS & MOBILE GRID)
// 1. VISUALS: Full Glassmorphism adoption (glass-panel, glass-input).
// 2. LAYOUT: Responsive grid (1 col mobile -> 3 cols desktop) without fixed height constraints on mobile.
// 3. UX: Improved modal animations and input focus states.

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Loader2 } from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent } from '../data/types';
import CaseCard from '../components/CaseCard';
import DayEventsModal from '../components/DayEventsModal';
import { isSameDay, parseISO } from 'date-fns';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  
  // Briefing State
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
      const [casesData, eventsData] = await Promise.all([
          apiService.getCases(),
          apiService.getCalendarEvents()
      ]);

      const casesWithDefaults = casesData.map(c => ({
          ...c,
          document_count: c.document_count || 0,
          alert_count: c.alert_count || 0,
          event_count: c.event_count || 0,
      }));
      setCases(casesWithDefaults);

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
    setIsCreating(true);
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
      loadData(); 
    } catch (error) {
      console.error("Failed to create case", error);
      alert(t('error.generic'));
    } finally {
      setIsCreating(false);
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

  // Logic: Show all cases in the grid, rely on overflow for scrolling
  const casesToDisplay = cases;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-full flex flex-col">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4 flex-shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">
            {t('dashboard.mainTitle', 'Asistenti Juridik')}
          </h1>
          <p className="text-text-secondary mt-1">{t('dashboard.subtitle')}</p>
        </div>
        <button 
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20 rounded-xl text-white font-semibold transition-all active:scale-95"
        >
          <Plus size={20} /> {t('dashboard.newCase')}
        </button>
      </div>

      {/* Case Grid - Flexible height */}
      {isLoading ? (
        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>
      ) : (
        <div className="flex-1 overflow-y-auto custom-scrollbar -mr-4 pr-4 pb-4">
          {casesToDisplay.length === 0 ? (
             <div className="text-center py-20 opacity-50">
               <p className="text-xl text-text-secondary">{t('dashboard.noCases', 'Nuk u gjetën raste.')}</p>
             </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {casesToDisplay.map((c) => (
                <CaseCard 
                    key={c.id} 
                    caseData={c} 
                    onDelete={handleDeleteCase} 
                />
                ))}
            </div>
          )}
        </div>
      )}

      {/* Create Modal - Glass Style */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-high w-full max-w-sm p-8 rounded-2xl animate-in fade-in zoom-in-95 duration-200">
            <h2 className="text-2xl font-bold text-white mb-6">{t('dashboard.createCaseTitle')}</h2>
            <form onSubmit={handleCreateCase} className="space-y-5">
              
              <div>
                <label className="block text-sm text-text-secondary mb-1">{t('dashboard.caseTitle')}</label>
                <input required name="title" type="text" value={newCaseData.title} onChange={handleModalInputChange} className="glass-input w-full rounded-xl px-4 py-2" />
              </div>
              
              <div className="pt-4 border-t border-white/10">
                <label className="block text-sm text-primary-start mb-3 font-medium">{t('caseCard.client')}</label>
                <div className="space-y-3">
                    <input required name="clientName" placeholder={t('dashboard.clientName')} type="text" value={newCaseData.clientName} onChange={handleModalInputChange} className="glass-input w-full rounded-xl px-4 py-2" />
                    <input name="clientEmail" placeholder={t('dashboard.clientEmail')} type="email" value={newCaseData.clientEmail} onChange={handleModalInputChange} className="glass-input w-full rounded-xl px-4 py-2" />
                    <input name="clientPhone" placeholder={t('dashboard.clientPhone')} type="tel" value={newCaseData.clientPhone} onChange={handleModalInputChange} className="glass-input w-full rounded-xl px-4 py-2" />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-8">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-4 py-2 rounded-xl hover:bg-white/5 text-text-secondary hover:text-white transition-colors">{t('general.cancel')}</button>
                <button type="submit" disabled={isCreating} className="px-6 py-2 rounded-xl bg-primary-start hover:bg-primary-end text-white font-bold shadow-lg shadow-primary-start/20 transition-all active:scale-95 flex items-center gap-2">
                    {isCreating && <Loader2 className="animate-spin h-4 w-4" />}
                    {t('general.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Daily Briefing Modal */}
      <DayEventsModal 
        isOpen={isBriefingOpen}
        onClose={() => setIsBriefingOpen(false)}
        date={new Date()} 
        events={todaysEvents}
        t={t}
        onAddEvent={() => {
            setIsBriefingOpen(false);
            window.location.href = '/calendar'; 
        }}
      />
    </div>
  );
};

export default DashboardPage;