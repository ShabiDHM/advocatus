// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V16.0 (CONTENT SCROLLING FIX)
// 1. UX: Implemented a fixed-height container using 'h-full' and 'flex-col'.
// 2. SCROLL: Ensured only the Case Grid itself is scrollable (overflow-y-auto), keeping the Briefing and Title static.
// 3. STATUS: Finalizes the Dashboard layout to match the requested image behavior.

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Loader2, AlertTriangle, Clock, CheckCircle2, ShieldAlert } from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent } from '../data/types'; 
import CaseCard from '../components/CaseCard';
import DayEventsModal from '../components/DayEventsModal';
import { isSameDay, parseISO } from 'date-fns';
import { motion } from 'framer-motion';

// NOTE: This interface should be in data/types.ts for best practice.
interface EnrichedCalendarEvent extends CalendarEvent {
  severity: 'PREKLUZIV' | 'GJYQESOR' | 'PROCEDURAL';
  working_days_remaining: number;
}

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();

  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  
  const [todaysEvents, setTodaysEvents] = useState<CalendarEvent[]>([]);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const hasCheckedBriefing = useRef(false);

  const [briefingCard, setBriefingCard] = useState<EnrichedCalendarEvent | null>(null);

  const initialNewCaseData = { 
    title: '', 
    clientName: '',
    clientEmail: '',
    clientPhone: ''
  };
  const [newCaseData, setNewCaseData] = useState(initialNewCaseData);

  // --- KUJDESTARI LOGIC (Unchanged) ---
  const findMostCriticalEvent = (events: EnrichedCalendarEvent[]) => {
    if (!events || events.length === 0) {
      setBriefingCard(null);
      return;
    }
    const severityOrder = { 'PREKLUZIV': 1, 'GJYQESOR': 2, 'PROCEDURAL': 3 };
    const mostCritical = events
      .filter(e => e.working_days_remaining < 10)
      .sort((a, b) => {
        const severityA = severityOrder[a.severity] || 4;
        const severityB = severityOrder[b.severity] || 4;
        if (severityA !== severityB) {
          return severityA - severityB;
        }
        return a.working_days_remaining - b.working_days_remaining;
      })[0];
    setBriefingCard(mostCritical || null);
  };

  const getBriefingDetails = () => {
    if (!briefingCard) {
      return {
        style: 'from-emerald-950/90 to-black/90 border-emerald-500/50 text-emerald-100',
        icon: <CheckCircle2 className="h-6 w-6 text-emerald-400" />,
        text: t('adminBriefing.insight.optimal')
      };
    }

    const { severity, working_days_remaining, title } = briefingCard;
    let style = 'from-sky-950/90 to-black/90 border-sky-500/50 text-sky-100'; 
    let icon = <Clock className="h-6 w-6 text-sky-400" />;
    let text = `${title} - ${working_days_remaining} ditë pune`;

    if (severity === 'PREKLUZIV') {
      style = 'from-red-950/90 to-black/90 border-red-500/50 text-red-100';
      icon = <ShieldAlert className="h-6 w-6 animate-pulse text-red-400" />;
      if (working_days_remaining < 0) {
         text = t('adminBriefing.kujdestari.prekluziv_missed', { title });
      } else if (working_days_remaining === 0) {
         text = t('adminBriefing.kujdestari.prekluziv_today', { title });
      } else {
         text = t('adminBriefing.kujdestari.prekluziv_upcoming', { title, count: working_days_remaining });
      }
    } else if (severity === 'GJYQESOR') {
      style = 'from-orange-950/90 to-black/90 border-orange-500/50 text-orange-100';
      icon = <AlertTriangle className="h-6 w-6 text-orange-400" />;
      if (working_days_remaining < 0) {
         text = t('adminBriefing.kujdestari.gjyqesor_missed', { title });
      } else if (working_days_remaining === 0) {
         text = t('adminBriefing.kujdestari.gjyqesor_today', { title });
      } else {
         text = t('adminBriefing.kujdestari.gjyqesor_upcoming', { title, count: working_days_remaining });
      }
    }

    return { style, icon, text };
  };

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [casesData, eventsData] = await Promise.all([
          apiService.getCases(),
          apiService.getCalendarEvents() as Promise<EnrichedCalendarEvent[]>
      ]);

      const casesWithDefaults = casesData.map(c => ({
          ...c,
          document_count: c.document_count || 0,
          alert_count: c.alert_count || 0,
          event_count: c.event_count || 0,
      }));
      setCases(casesWithDefaults);
      
      findMostCriticalEvent(eventsData);
      
      if (!hasCheckedBriefing.current && eventsData.length > 0) {
          const today = new Date();
          const matches = eventsData.filter(e => isSameDay(parseISO(e.start_date), today));
          if (matches.length > 0) {
              setTodaysEvents(matches);
          }
          hasCheckedBriefing.current = true;
      }

    } catch (error) {
      console.error("Failed to load dashboard data", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => { e.preventDefault(); setIsCreating(true); try { const tempCaseNumber = `R-${Date.now().toString().slice(-6)}`; const payload: CreateCaseRequest = { case_number: tempCaseNumber, title: newCaseData.title, case_name: newCaseData.title, description: "", clientName: newCaseData.clientName, clientEmail: newCaseData.clientEmail, clientPhone: newCaseData.clientPhone, status: 'open' }; await apiService.createCase(payload); setShowCreateModal(false); setNewCaseData(initialNewCaseData); loadData(); } catch (error) { console.error("Failed to create case", error); alert(t('error.generic')); } finally { setIsCreating(false); } };
  const handleDeleteCase = async (caseId: string) => { if (window.confirm(t('dashboard.confirmDelete', 'A jeni i sigurt?'))) { try { await apiService.deleteCase(caseId); setCases(prevCases => prevCases.filter(c => c.id !== caseId)); } catch (error) { console.error("Failed to delete case", error); alert(t('error.generic')); } } };
  const handleModalInputChange = (e: React.ChangeEvent<HTMLInputElement>) => { const { name, value } = e.target; setNewCaseData(prev => ({ ...prev, [name]: value })); };

  const casesToDisplay = cases;
  const { style: rowStyleClasses, icon: briefingIcon, text: briefingText } = getBriefingDetails();

  return (
    // PHOENIX FIX: Removed 'min-h-screen' to allow the main layout to handle height, and added 'h-full' to this inner div.
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-8 h-full flex flex-col">
      
      {/* Kujdestari Briefing Card - REMAINS STATIC */}
      <motion.div 
          className={`shrink-0 mb-8 p-0 rounded-xl shadow-2xl backdrop-blur-md border ${rowStyleClasses.split(' ')[2]}`}
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
      >
          <div className={`rounded-xl p-4 bg-gradient-to-r ${rowStyleClasses}`}>
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
                        {briefingIcon}
                    </div>
                    <div>
                        <h2 className="text-sm font-bold uppercase tracking-wider opacity-80">
                            {t('adminBriefing.title', 'Kujdestari Ditor')}
                        </h2>
                        <p className="font-medium text-lg leading-tight">
                            {briefingText}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3 self-end md:self-auto">
                    <button 
                        className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg font-medium transition-all text-sm whitespace-nowrap"
                        onClick={() => window.location.href = '/calendar'}
                    >
                        {t('adminBriefing.viewCalendar', 'Shiko Kalendarin')}
                    </button>
                </div>
            </div>
          </div>
      </motion.div>

      {/* Header (Pasqyra e Rasteve) - REMAINS STATIC */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4 flex-shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">{t('dashboard.mainTitle', 'Pasqyra e Rasteve')}</h1>
          <p className="text-text-secondary mt-1">{t('dashboard.subtitle', 'Menaxhoni rastet tuaja.')}</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20 rounded-xl text-white font-semibold transition-all active:scale-95">
          <Plus size={20} /> {t('dashboard.newCase', 'Rast i Ri')}
        </button>
      </div>

      {/* Case Grid - IS NOW THE SCROLLABLE AREA */}
      {isLoading ? (
        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>
      ) : (
        // PHOENIX FIX: Added 'flex-1 overflow-y-auto' to make THIS block scrollable, keeping the elements above static.
        <div className="flex-1 overflow-y-auto custom-scrollbar -mr-4 pr-4 pb-4">
          {casesToDisplay.length === 0 ? (
             <div className="text-center py-20 opacity-50"><p className="text-xl text-text-secondary">{t('dashboard.noCases', 'Nuk u gjetën raste.')}</p></div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {casesToDisplay.map((c) => (<CaseCard key={c.id} caseData={c} onDelete={handleDeleteCase} />))}
            </div>
          )}
        </div>
      )}

      {/* Create Modal */}
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
                    {isCreating && <Loader2 className="animate-spin h-4 w-4" />} {t('general.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Daily Events Modal */}
      <DayEventsModal isOpen={isBriefingOpen} onClose={() => setIsBriefingOpen(false)} date={new Date()} events={todaysEvents} t={t} onAddEvent={() => { setIsBriefingOpen(false); window.location.href = '/calendar'; }} />
    </div>
  );
};

export default DashboardPage;