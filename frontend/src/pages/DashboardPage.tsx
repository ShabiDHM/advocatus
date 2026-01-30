// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V23.0 (IDENTITY & WISDOM FINAL)
import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, Loader2, AlertTriangle, CheckCircle2, ShieldAlert, 
  PartyPopper, Coffee, Quote as QuoteIcon 
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

  const getTheme = (status: string) => {
    switch (status) {
      case 'HOLIDAY': return { style: 'from-indigo-950 to-black border-indigo-500/50', icon: <PartyPopper className="h-6 w-6 text-indigo-400" /> };
      case 'WEEKEND': return { style: 'from-teal-950 to-black border-teal-500/50', icon: <Coffee className="h-6 w-6 text-teal-400" /> };
      case 'CRITICAL': return { style: 'from-red-950 to-black border-red-500/50', icon: <ShieldAlert className="h-6 w-6 animate-pulse text-red-400" /> };
      case 'WARNING': return { style: 'from-amber-950 to-black border-amber-500/50', icon: <AlertTriangle className="h-6 w-6 text-amber-400" /> };
      default: return { style: 'from-emerald-950 to-black border-emerald-500/50', icon: <CheckCircle2 className="h-6 w-6 text-emerald-400" /> };
    }
  };

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [cData, bData, eData] = await Promise.all([apiService.getCases(), apiService.getBriefing(), apiService.getCalendarEvents()]);
      setCases(cData); setBriefing(bData);
      if (!hasCheckedBriefing.current && eData.length > 0) {
        const today = new Date();
        const matches = eData.filter(e => isSameDay(parseISO(e.start_date), today));
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
      setShowCreateModal(false); setNewCaseData({ title: '', clientName: '', clientEmail: '', clientPhone: '' }); loadData();
    } catch { alert(t('error.generic') as string); } finally { setIsCreating(false); }
  };

  const theme = getTheme(briefing?.status || 'OPTIMAL');

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-8 h-full flex flex-col">
      <AnimatePresence mode="wait">
        {briefing && (
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className={`shrink-0 mb-8 rounded-2xl shadow-2xl border ${theme.style.split(' ')[2]} overflow-hidden`}>
            <div className={`p-6 bg-gradient-to-r ${theme.style}`}>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="flex items-center gap-5">
                  <div className="p-3 bg-white/10 rounded-xl ring-1 ring-white/20">{theme.icon}</div>
                  <div>
                    <h2 className="text-[10px] font-black uppercase tracking-[0.2em] text-white/50 mb-1">{t('briefing.kujdestari_title') as string}</h2>
                    <p className="font-bold text-2xl text-white tracking-tight">{t(`briefing.greetings.${briefing.greeting_key}`, briefing.data || {}) as string}</p>
                    <p className="text-white/70 font-medium mt-0.5">{t(`briefing.messages.${briefing.message_key}`, { ...(briefing.data || {}), holiday_name: briefing.data?.holiday ? t(`holidays.${briefing.data.holiday}`) : '' }) as string}</p>
                    
                    {briefing.status === 'OPTIMAL' && briefing.data?.quote_key && (
                      <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} className="mt-4 flex items-start gap-3 py-3 px-4 bg-white/5 rounded-xl border border-white/10 max-w-2xl backdrop-blur-sm shadow-inner">
                        <QuoteIcon size={14} className="text-emerald-400 shrink-0 mt-1" />
                        <p className="text-emerald-50/90 text-[13px] italic font-medium leading-relaxed tracking-wide">
                          {t(`briefing.quotes.${briefing.data.quote_key}`) as string}
                        </p>
                      </motion.div>
                    )}
                  </div>
                </div>
                <button onClick={() => window.location.href = '/calendar'} className="px-6 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold border border-white/10 text-sm transition-all active:scale-95">{t('briefing.view_calendar') as string}</button>
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
        <button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-start to-primary-end rounded-2xl text-white font-black shadow-lg shadow-primary-start/20 transition-all active:scale-95"><Plus size={22} strokeWidth={3} /> {t('dashboard.newCase') as string}</button>
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
              <input required placeholder={t('dashboard.caseTitle') as string} value={newCaseData.title} onChange={(e) => setNewCaseData(p => ({...p, title: e.target.value}))} className="glass-input w-full rounded-2xl px-5 py-3 outline-none focus:ring-2 ring-primary-start text-white" />
              <div className="pt-6 border-t border-white/10 space-y-3">
                <input required placeholder={t('dashboard.clientName') as string} value={newCaseData.clientName} onChange={(e) => setNewCaseData(p => ({...p, clientName: e.target.value}))} className="glass-input w-full rounded-2xl px-5 py-3 outline-none text-white" />
                <input placeholder={t('dashboard.clientEmail') as string} value={newCaseData.clientEmail} onChange={(e) => setNewCaseData(p => ({...p, clientEmail: e.target.value}))} className="glass-input w-full rounded-2xl px-5 py-3 outline-none text-white" />
                <input placeholder={t('dashboard.clientPhone') as string} value={newCaseData.clientPhone} onChange={(e) => setNewCaseData(p => ({...p, clientPhone: e.target.value}))} className="glass-input w-full rounded-2xl px-5 py-3 outline-none text-white" />
              </div>
              <div className="flex justify-end gap-4 mt-8">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-6 py-2 font-bold text-white/60 hover:text-white transition-all">{t('general.cancel') as string}</button>
                <button type="submit" disabled={isCreating} className="px-8 py-3 rounded-2xl bg-primary-start text-white font-black shadow-xl flex items-center gap-2 active:scale-95">{isCreating ? <Loader2 className="animate-spin h-5 w-5" /> : t('general.create') as string}</button>
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