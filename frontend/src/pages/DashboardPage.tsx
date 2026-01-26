// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V9.0 (TYPE INTEGRITY & CLEANUP)
// 1. FIX: Resolved TypeScript error "Property 'type' does not exist on type 'CalendarEvent'" by removing 'event.type'.
// 2. CLEANUP: Removed unused 'now' variable to resolve the "value is never read" warning.
// 3. ARCH: Maintained all V8.0 critical deadline calculation and admin gatekeeper logic.

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Loader2, Activity, AlertTriangle, Clock } from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent } from '../data/types';
import CaseCard from '../components/CaseCard';
import DayEventsModal from '../components/DayEventsModal';
// Extended date-fns imports
import { isSameDay, parseISO, isToday, isYesterday, isPast } from 'date-fns'; 
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth(); // Destructure user from AuthContext

  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  
  // Briefing State
  const [todaysEvents, setTodaysEvents] = useState<CalendarEvent[]>([]);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const hasCheckedBriefing = useRef(false);

  // NEW STATE: Critical Deadlines
  const [criticalDeadlinesCount, setCriticalDeadlinesCount] = useState<{
    today: number;
    yesterdayMissed: number;
  }>({ today: 0, yesterdayMissed: 0 });

  const initialNewCaseData = { 
    title: '', 
    clientName: '',
    clientEmail: '',
    clientPhone: ''
  };
  const [newCaseData, setNewCaseData] = useState(initialNewCaseData);

  // PHOENIX GATEKEEPER LOGIC: Check for ADMIN role
  const isAdmin = useMemo(() => {
    return user?.role === 'ADMIN';
  }, [user]);

  // NEW LOGIC: Deadline calculation (FIXED FOR TYPE INTEGRITY)
  const calculateCriticalDeadlines = (events: CalendarEvent[]) => {
      let todayCount = 0;
      let yesterdayMissedCount = 0;

      // REMOVED: const now = new Date(); (Resolved Error 6133)

      events.forEach(event => {
          // FIXED: Relying only on event.title for criticality check (Resolved Error 2339)
          const isCriticalType = ['Seancë Gjyqësore', 'Afat Ligjor'].includes(event.title); 

          if (isCriticalType) {
              const eventDate = parseISO(event.start_date);
              
              if (isToday(eventDate)) {
                  todayCount++;
              } else if (isYesterday(eventDate) && isPast(eventDate)) {
                  // Count as missed if it was yesterday and has definitely passed
                  yesterdayMissedCount++;
              }
          }
      });

      setCriticalDeadlinesCount({ today: todayCount, yesterdayMissed: yesterdayMissedCount });
  };
  // END NEW LOGIC: Deadline calculation

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
      
      // RUN NEW LOGIC
      calculateCriticalDeadlines(eventsData);
      
      // Original Briefing Modal Logic (remains separate from the Admin Row)
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

  // Helper for Row Styling
  const criticalCount = criticalDeadlinesCount.today + criticalDeadlinesCount.yesterdayMissed;
  const rowStyleClasses = criticalCount > 0 
      ? 'from-red-900/40 to-black/20 border border-red-700/50' // Highlight Red for active or missed deadlines
      : 'from-teal-900/40 to-black/20 border border-teal-700/50';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-full flex flex-col">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4 flex-shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-text-primary tracking-tight">
            {t('dashboard.mainTitle', 'Pasqyra e Rasteve')}
          </h1>
          <p className="text-text-secondary mt-1">{t('dashboard.subtitle', 'Menaxhoni rastet tuaja.')}</p>
        </div>
        <button 
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20 rounded-xl text-white font-semibold transition-all active:scale-95"
        >
          <Plus size={20} /> {t('dashboard.newCase', 'Rast i Ri')}
        </button>
      </div>

      {/* ADMIN: DAILY BRIEFING ROW - Updated to show Critical Deadlines */}
      {isAdmin && (
          <motion.div 
              className={`mb-8 p-4 rounded-xl shadow-lg ${rowStyleClasses}`}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.3 }}
          >
              <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                      {criticalCount > 0 ? (
                          <AlertTriangle className="h-6 w-6 text-red-500 flex-shrink-0 animate-pulse" />
                      ) : (
                          <Activity className="h-6 w-6 text-teal-400 flex-shrink-0" />
                      )}
                      <h2 className="text-lg font-semibold text-white">{t('adminBriefing.title', 'Përmbledhje Ditore (Admin)')}</h2>
                  </div>

                  {/* CRITICAL DEADLINES DISPLAY */}
                  <div className="flex items-center gap-4 text-sm font-medium">
                    {/* Yesterday Missed */}
                    {criticalDeadlinesCount.yesterdayMissed > 0 && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-900/70 text-red-300">
                            <Clock size={16} />
                            {criticalDeadlinesCount.yesterdayMissed} {t('briefing.missed', 'Dje i Humbur')}
                        </span>
                    )}

                    {/* Today Critical */}
                    {criticalDeadlinesCount.today > 0 && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-yellow-800/70 text-yellow-300">
                            <AlertTriangle size={16} />
                            {criticalDeadlinesCount.today} {t('briefing.today', 'Sot Kritik')}
                        </span>
                    )}
                    
                    {/* General Status (if no critical items) */}
                    {criticalCount === 0 && (
                        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-900/70 text-teal-300">
                            {t('briefing.statusOk', 'Afate OK')}
                        </span>
                    )}
                  </div>
                  
                  {/* Action Button */}
                  <button className="px-3 py-1 text-sm bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-medium transition-colors"
                          onClick={() => window.location.href = '/calendar'}
                  >
                      {t('adminBriefing.viewCalendar', 'Shiko Kalendarin')}
                  </button>
              </div>
          </motion.div>
      )}
      {/* END ADMIN: DAILY BRIEFING ROW */}

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

      {/* Create Modal - Glass Style (Remains Unchanged) */}
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

      {/* Daily Briefing Modal (Remains Unchanged) */}
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