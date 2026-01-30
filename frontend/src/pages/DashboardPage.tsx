// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V21.0 (WISDOM RENDERING)
import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, 
  Loader2, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  PartyPopper, 
  Coffee,
  Quote
} from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent, BriefingResponse } from '../data/types'; 
import CaseCard from '../components/CaseCard';
import DayEventsModal from '../components/DayEventsModal';
import { isSameDay, parseISO } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [todaysEvents, setTodaysEvents] = useState<CalendarEvent[]>([]);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const hasCheckedBriefing = useRef<boolean>(false);
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);

  const [newCaseData, setNewCaseData] = useState({ title: '', clientName: '', clientEmail: '', clientPhone: '' });

  const getBriefingTheme = (status: string) => {
    switch (status) {
      case 'HOLIDAY': return { style: 'from-indigo-950/90 to-black/90 border-indigo-500/50 text-indigo-100', icon: <PartyPopper className="h-6 w-6 text-indigo-400" />, glow: 'bg-indigo-500/20' };
      case 'WEEKEND': return { style: 'from-teal-950/90 to-black/90 border-teal-500/50 text-teal-100', icon: <Coffee className="h-6 w-6 text-teal-400" />, glow: 'bg-teal-500/20' };
      case 'CRITICAL': return { style: 'from-red-950/90 to-black/90 border-red-500/50 text-red-100', icon: <ShieldAlert className="h-6 w-6 animate-pulse text-red-400" />, glow: 'bg-red-500/20' };
      case 'WARNING': return { style: 'from-amber-950/90 to-black/90 border-amber-500/50 text-amber-100', icon: <AlertTriangle className="h-6 w-6 text-amber-400" />, glow: 'bg-amber-500/20' };
      default: return { style: 'from-emerald-950/90 to-black/90 border-emerald-500/50 text-emerald-100', icon: <CheckCircle2 className="h-6 w-6 text-emerald-400" />, glow: 'bg-emerald-500/20' };
    }
  };

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [casesData, briefingData, eventsData] = await Promise.all([
          apiService.getCases(),
          apiService.getBriefing(),
          apiService.getCalendarEvents()
      ]);
      setCases(casesData);
      setBriefing(briefingData);
      if (!hasCheckedBriefing.current && eventsData.length > 0) {
          const today = new Date();
          const matches = eventsData.filter(e => isSameDay(parseISO(e.start_date), today));
          if (matches.length > 0) { setTodaysEvents(matches); setIsBriefingOpen(true); }
          hasCheckedBriefing.current = true;
      }
    } catch { setIsLoading(false); } finally { setIsLoading(false); }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault(); setIsCreating(true);
    try {
      const payload: CreateCaseRequest = { case_number: `R-${Date.now().toString().slice(-6)}`, title: newCaseData.title, clientName: newCaseData.clientName, clientEmail: newCaseData.clientEmail, clientPhone: newCaseData.clientPhone, status: 'open' };
      await apiService.createCase(payload);
      setShowCreateModal(false); setNewCaseData({ title: '', clientName: '', clientEmail: '', clientPhone: '' });
      loadData();
    } catch { alert(t('error.generic') as string); } finally { setIsCreating(false); }
  };

  const theme = getBriefingTheme(briefing?.status || 'OPTIMAL');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-8 h-full flex flex-col">
      <AnimatePresence mode="wait">
        {briefing && (
          <motion.div key={briefing.status} className={`shrink-0 mb-8 rounded-2xl shadow-2xl backdrop-blur-md border ${theme.style.split(' ')[2]} overflow-hidden relative`} initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
              <div className={`absolute -right-10 -top-10 w-40 h-40 blur-3xl rounded-full ${theme.glow} opacity-50`} />
              <div className={`p-5 bg-gradient-to-r ${theme.style}`}>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
                    <div className="flex items-center gap-5">
                        <div className="p-3 bg-white/10 rounded-xl backdrop-blur-md ring-1 ring-white/20">{theme.icon}</div>
                        <div>
                            <h2 className="text-xs font-black uppercase tracking-widest text-white/60 mb-1">{t('briefing.kujdestari_title') as string}</h2>
                            <div className="space-y-1">
                              <p className="font-bold text-xl text-white">
                                  {t(`briefing.greetings.${briefing.greeting_key}`, briefing.data || {}) as string}
                              </p>
                              
                              {/* PHOENIX: Message or Quote Rendering */}
                              {briefing.status === 'OPTIMAL' && briefing.data?.quote_key ? (
                                <div className="flex items-start gap-2 mt-1 py-1 px-3 bg-white/5 rounded-lg border border-white/10 italic">
                                   <Quote size={14} className="text-emerald-400 shrink-0 mt-1" />
                                   <p className="text-emerald-50/90 text-sm font-medium">
                                       {t(`briefing.quotes.${briefing.data.quote_key}`) as string}
                                   </p>
                                </div>
                              ) : (
                                <p className="text-white/80 font-medium">
                                    {t(`briefing.messages.${briefing.message_key}`, {
                                      ...(briefing.data || {}),
                                      holiday_name: briefing.data?.holiday ? t(`holidays.${briefing.data.holiday}`) : ''
                                    }) as string}
                                </p>
                              )}
                            </div>
                        </div>
                    </div>
                    <button onClick={() => window.location.href = '/calendar'} className="px-5 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold border border-white/10 text-sm whitespace-nowrap active:scale-95">{t('briefing.view_calendar') as string}</button>
                </div>
              </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex justify-between items-center mb-6 flex-shrink-0">
        <div>
          <h1 className="text-4xl font-black text-text-primary tracking-tighter">{t('dashboard.mainTitle') as string}</h1>
          <p className="text-text-secondary font-medium mt-1">{t('dashboard.subtitle') as string}</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-start to-primary-end rounded-2xl text-white font-black shadow-lg shadow-primary-start/20 transition-all active:scale-95">
          <Plus size={22} strokeWidth={3} /> {t('dashboard.newCase') as string}
        </button>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-10 w-10 text-primary-start" /></div>
      ) : (
        <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 pb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {cases.map((c) => (<CaseCard key={c.id} caseData={c} onDelete={() => loadData()} />))}
          </div>
        </div>
      )}

      {showCreateModal && (
        <div className="fixed inset-0 bg-background-dark/90 backdrop-blur-xl flex items-center justify-center z-[100] p-4">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="glass-high w-full max-w-md p-8 rounded-3xl shadow-2xl">
            <h2 className="text-3xl font-black text-white mb-8 tracking-tight">{t('dashboard.createCaseTitle') as string}</h2>
            <form onSubmit={handleCreateCase} className="space-y-6">
              <input required placeholder={t('dashboard.caseTitle') as string} value={newCaseData.title} onChange={(e) => setNewCaseData(p => ({...p, title: e.target.value}))} className="glass-input w-full rounded-2xl px-5 py-3 outline-none focus:ring-2 ring-primary-start" />
              <div className="pt-6 border-t border-white/10 space-y-3">
                  <input required placeholder={t('dashboard.clientName') as string} value={newCaseData.clientName} onChange={(e) => setNewCaseData(p => ({...p, clientName: e.target.value}))} className="glass-input w-full rounded-2xl px-5 py-3 outline-none" />
                  <input placeholder={t('dashboard.clientEmail') as string} value={newCaseData.clientEmail} onChange={(e) => setNewCaseData(p => ({...p, clientEmail: e.target.value}))} className="glass-input w-full rounded-2xl px-5 py-3 outline-none" />
                  <input placeholder={t('dashboard.clientPhone') as string} value={newCaseData.clientPhone} onChange={(e) => setNewCaseData(p => ({...p, clientPhone: e.target.value}))} className="glass-input w-full rounded-2xl px-5 py-3 outline-none" />
              </div>
              <div className="flex justify-end gap-4 mt-8">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-6 py-2 font-bold text-white/60 hover:text-white">{t('general.cancel') as string}</button>
                <button type="submit" disabled={isCreating} className="px-8 py-3 rounded-2xl bg-primary-start text-white font-black shadow-xl flex items-center gap-2 active:scale-95">
                    {isCreating ? <Loader2 className="animate-spin h-5 w-5" /> : t('general.create') as string}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
      <DayEventsModal isOpen={isBriefingOpen} onClose={() => setIsBriefingOpen(false)} date={new Date()} events={todaysEvents} t={t} onAddEvent={() => { setIsBriefingOpen(false); window.location.href = '/calendar'; }} />
    </div>
  );
};

export default DashboardPage;