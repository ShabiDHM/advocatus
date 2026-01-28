// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V13.1 (i18n FIX)
// 1. REFACTOR: Removed hardcoded strings from 'runIntelligenceEngine'.
// 2. LOGIC: Now stores an 'insightState' object { key, count } to use with t().
// 3. I18N: Added translation keys for metrics and buttons.

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Loader2, AlertTriangle, Clock, CheckCircle2, Zap } from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent } from '../data/types';
import CaseCard from '../components/CaseCard';
import DayEventsModal from '../components/DayEventsModal';
import { isSameDay, parseISO, isToday, isYesterday, isPast, addDays, isBefore } from 'date-fns'; 
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();

  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  
  // Briefing State
  const [todaysEvents, setTodaysEvents] = useState<CalendarEvent[]>([]);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const hasCheckedBriefing = useRef(false);

  // Intelligent Briefing State
  const [criticalDeadlinesCount, setCriticalDeadlinesCount] = useState<{
    today: number;
    yesterdayMissed: number;
    upcoming: number;
  }>({ today: 0, yesterdayMissed: 0, upcoming: 0 });
  
  const [totalAlerts, setTotalAlerts] = useState(0);
  
  // REPLACED hardcoded string with state object for i18n
  const [insightState, setInsightState] = useState<{ key: string; count: number }>({ 
      key: 'adminBriefing.insight.optimal', 
      count: 0 
  });

  const initialNewCaseData = { 
    title: '', 
    clientName: '',
    clientEmail: '',
    clientPhone: ''
  };
  const [newCaseData, setNewCaseData] = useState(initialNewCaseData);

  const isAdmin = useMemo(() => {
    return user?.role === 'ADMIN';
  }, [user]);

  // LOGIC: Intelligent Analysis
  const runIntelligenceEngine = (events: CalendarEvent[], casesList: Case[]) => {
      let todayCount = 0;
      let yesterdayMissedCount = 0;
      let upcomingCount = 0;
      
      const next48Hours = addDays(new Date(), 2);

      events.forEach(event => {
          const isCriticalType = ['Seancë Gjyqësore', 'Afat Ligjor', 'Hearing', 'Deadline'].some(type => 
              event.title.includes(type) || (event.priority === 'CRITICAL')
          );

          if (isCriticalType) {
              const eventDate = parseISO(event.start_date);
              
              if (isToday(eventDate)) {
                  todayCount++;
              } else if (isYesterday(eventDate) && isPast(eventDate)) {
                  yesterdayMissedCount++;
              } else if (isBefore(eventDate, next48Hours) && !isPast(eventDate)) {
                  upcomingCount++;
              }
          }
      });

      setCriticalDeadlinesCount({ 
        today: todayCount, 
        yesterdayMissed: yesterdayMissedCount,
        upcoming: upcomingCount
      });

      const alerts = casesList.reduce((sum, c) => sum + (c.alert_count || 0), 0);
      setTotalAlerts(alerts);

      // Generate Strategy Key instead of String
      if (yesterdayMissedCount > 0) {
          setInsightState({ key: 'adminBriefing.insight.missed', count: yesterdayMissedCount });
      } else if (todayCount > 0) {
          setInsightState({ key: 'adminBriefing.insight.today', count: todayCount });
      } else if (upcomingCount > 0) {
          setInsightState({ key: 'adminBriefing.insight.upcoming', count: upcomingCount });
      } else if (alerts > 5) {
          setInsightState({ key: 'adminBriefing.insight.alerts', count: alerts });
      } else {
          setInsightState({ key: 'adminBriefing.insight.optimal', count: 0 });
      }
  };

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
      
      runIntelligenceEngine(eventsData, casesWithDefaults);
      
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

  const casesToDisplay = cases;

  const criticalCount = criticalDeadlinesCount.today + criticalDeadlinesCount.yesterdayMissed;
  
  const rowStyleClasses = criticalCount > 0 
      ? 'from-red-950/90 to-black/90 border-red-500/50 text-red-100' 
      : criticalDeadlinesCount.upcoming > 0 
        ? 'from-orange-950/90 to-black/90 border-orange-500/50 text-orange-100'
        : totalAlerts > 5
          ? 'from-yellow-950/90 to-black/90 border-yellow-500/50 text-yellow-100'
          : 'from-emerald-950/90 to-black/90 border-emerald-500/50 text-emerald-100';

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 min-h-screen flex flex-col">
      
      {/* Sticky Admin Briefing */}
      {isAdmin && (
          <motion.div 
              className={`sticky top-2 z-30 mb-8 p-0 rounded-xl shadow-2xl backdrop-blur-md border ${rowStyleClasses.split(' ')[2]}`}
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.4 }}
          >
              <div className={`rounded-xl p-4 bg-gradient-to-r ${rowStyleClasses}`}>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    
                    {/* LEFT: Icon & Status */}
                    <div className="flex items-center gap-4">
                        <div className="p-2 bg-white/10 rounded-lg backdrop-blur-sm">
                            {criticalCount > 0 ? (
                                <AlertTriangle className="h-6 w-6 animate-pulse text-red-400" />
                            ) : criticalDeadlinesCount.upcoming > 0 ? (
                                <Clock className="h-6 w-6 text-orange-400" />
                            ) : totalAlerts > 5 ? (
                                <Zap className="h-6 w-6 text-yellow-400" />
                            ) : (
                                <CheckCircle2 className="h-6 w-6 text-emerald-400" />
                            )}
                        </div>
                        <div>
                            <h2 className="text-sm font-bold uppercase tracking-wider opacity-80">
                                {t('adminBriefing.title', 'Inteligjenca Ditore')}
                            </h2>
                            <p className="font-medium text-lg leading-tight">
                                {/* DYNAMIC TRANSLATION */}
                                {t(insightState.key, { count: insightState.count })}
                            </p>
                        </div>
                    </div>

                    {/* RIGHT: Metrics & Actions */}
                    <div className="flex items-center gap-3 self-end md:self-auto">
                        <div className="flex gap-2 mr-2">
                             {criticalDeadlinesCount.today > 0 && (
                                <div className="flex flex-col items-center px-3 py-1 bg-black/30 rounded-lg">
                                    <span className="text-xs opacity-70">{t('adminBriefing.metric.today', 'Sot')}</span>
                                    <span className="font-bold">{criticalDeadlinesCount.today}</span>
                                </div>
                             )}
                             {totalAlerts > 0 && (
                                <div className="flex flex-col items-center px-3 py-1 bg-black/30 rounded-lg">
                                    <span className="text-xs opacity-70">{t('adminBriefing.metric.alerts', 'Sinjalizime')}</span>
                                    <span className="font-bold">{totalAlerts}</span>
                                </div>
                             )}
                        </div>

                        <button 
                            className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg font-medium transition-all text-sm whitespace-nowrap"
                            onClick={() => window.location.href = '/calendar'}
                        >
                            {t('adminBriefing.viewCalendar', 'Hap Kalendarin')}
                        </button>
                    </div>
                </div>
              </div>
          </motion.div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4 flex-shrink-0">
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

      {/* Case Grid */}
      {isLoading ? (
        <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>
      ) : (
        <div className="flex-1 -mr-4 pr-4 pb-4">
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