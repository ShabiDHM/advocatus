// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V25.0 (REAL-TIME RISK RADAR)
// 1. FIX: Integrated 'now' state into countdown calculation to resolve TS6133.
// 2. FEAT: Implemented dynamic ticking for Risk Radar (seconds decrease in real-time).
// 3. CLEANUP: Synchronized with restored types and removed unused declarations.

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, Loader2, AlertTriangle, CheckCircle2, ShieldAlert, 
  PartyPopper, Coffee, Quote as QuoteIcon, Timer
} from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent, BriefingResponse, RiskAlert } from '../data/types'; 
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
  
  // PHOENIX: Real-time clock to drive the Risk Radar ticks
  const [now, setNow] = useState<number>(Date.now());
  const [fetchTimestamp, setFetchTimestamp] = useState<number>(Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatCountdown = (initialSeconds: number) => {
    // Calculate elapsed time since the data was fetched
    const elapsedSeconds = Math.floor((now - fetchTimestamp) / 1000);
    const remaining = initialSeconds - elapsedSeconds;

    if (remaining <= 0) return t('adminBriefing.metric.today') as string;
    
    const h = Math.floor(remaining / 3600);
    const m = Math.floor((remaining % 3600) / 60);
    const s = remaining % 60;
    return `${h}h ${m}m ${s}s`;
  };

  const theme = useMemo(() => {
    const status = briefing?.status || 'OPTIMAL';
    switch (status) {
      case 'HOLIDAY': return { style: 'from-indigo-950 to-black border-indigo-500/50', icon: <PartyPopper className="h-6 w-6 text-indigo-400" /> };
      case 'WEEKEND': return { style: 'from-teal-950 to-black border-teal-500/50', icon: <Coffee className="h-6 w-6 text-teal-400" /> };
      case 'CRITICAL': return { style: 'from-red-950 via-red-900/40 to-black border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.2)]', icon: <ShieldAlert className="h-6 w-6 animate-pulse text-red-500" /> };
      case 'WARNING': return { style: 'from-amber-950 to-black border-amber-500/50', icon: <AlertTriangle className="h-6 w-6 text-amber-400" /> };
      default: return { style: 'from-emerald-950 to-black border-emerald-500/50', icon: <CheckCircle2 className="h-6 w-6 text-emerald-400" /> };
    }
  }, [briefing?.status]);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [cData, bData, eData] = await Promise.all([
        apiService.getCases(),
        apiService.getBriefing(),
        apiService.getCalendarEvents()
      ]);
      
      setCases(cData);
      setBriefing(bData);
      setFetchTimestamp(Date.now()); // Mark the exact time data was received

      if (!hasCheckedBriefing.current && eData.length > 0) {
        const today = new Date();
        const matches = eData.filter(e => isSameDay(parseISO(e.start_date), today));
        if (matches.length > 0) {
          setTodaysEvents(matches);
          setIsBriefingOpen(true);
        }
        hasCheckedBriefing.current = true;
      }
    } catch (error) {
      console.error("Sync Failed:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    try {
      const payload: CreateCaseRequest = { 
        case_number: `R-${Date.now().toString().slice(-6)}`, 
        title: newCaseData.title, 
        clientName: newCaseData.clientName, 
        clientEmail: newCaseData.clientEmail, 
        clientPhone: newCaseData.clientPhone, 
        status: 'open' 
      };
      await apiService.createCase(payload);
      setShowCreateModal(false);
      setNewCaseData({ title: '', clientName: '', clientEmail: '', clientPhone: '' });
      loadData();
    } catch {
      alert(t('error.generic') as string);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-8 h-full flex flex-col">
      <AnimatePresence mode="wait">
        {briefing && (
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className={`shrink-0 mb-8 rounded-2xl shadow-2xl border ${theme.style.split(' ')[2]} overflow-hidden ring-1 ring-white/5`}>
            <div className={`p-6 bg-gradient-to-br ${theme.style}`}>
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-8">
                {/* Guardian Identity */}
                <div className="flex items-start gap-5">
                  <div className="p-3 bg-white/10 rounded-xl backdrop-blur-md shrink-0">{theme.icon}</div>
                  <div>
                    <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-white/40 mb-1.5">{t('briefing.kujdestari_title') as string}</h2>
                    <p className="font-bold text-2xl text-white tracking-tight leading-none">
                        {t(`briefing.greetings.${briefing.greeting_key}`, briefing.data || {}) as string}
                    </p>
                    <p className="text-white/60 font-medium mt-2 text-sm italic">
                        {t(`briefing.messages.${briefing.message_key}`, { 
                          ...(briefing.data || {}), 
                          holiday_name: briefing.data?.holiday ? t(`holidays.${briefing.data.holiday}`) : '' 
                        }) as string}
                    </p>
                  </div>
                </div>

                {/* Risk Radar / Wisdom Triage */}
                <div className="flex-1 max-w-2xl">
                    {briefing.risk_radar && briefing.risk_radar.length > 0 ? (
                        <div className="space-y-3">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-white/30 ml-1">RADARI I RREZIKUT</h3>
                            {briefing.risk_radar.map((item: RiskAlert) => (
                                <motion.div 
                                    key={item.id} 
                                    className={`p-3 rounded-xl border flex items-center justify-between gap-4 backdrop-blur-md ${
                                        item.level === 'LEVEL_1_PREKLUZIV' 
                                        ? 'bg-red-500/10 border-red-500/30' 
                                        : 'bg-amber-500/10 border-amber-500/20'
                                    }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`w-2 h-2 rounded-full ${item.level === 'LEVEL_1_PREKLUZIV' ? 'bg-red-500 animate-ping' : 'bg-amber-500'}`} />
                                        <span className={`text-sm font-bold truncate max-w-[150px] md:max-w-md ${item.level === 'LEVEL_1_PREKLUZIV' ? 'text-red-100' : 'text-amber-100'}`}>
                                            {item.title}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-1 bg-black/40 rounded-lg border border-white/5 shrink-0">
                                        <Timer size={14} className={item.level === 'LEVEL_1_PREKLUZIV' ? 'text-red-400' : 'text-amber-400'} />
                                        <span className="text-[12px] font-mono font-bold text-white tabular-nums">
                                            {formatCountdown(item.seconds_remaining)}
                                        </span>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    ) : (
                        <div className="h-full flex items-center">
                            {briefing.status === 'OPTIMAL' && briefing.data?.quote_key && (
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-4 p-4 bg-white/5 rounded-2xl border border-white/10 italic">
                                    <QuoteIcon size={16} className="text-emerald-400 shrink-0 mt-1 opacity-50" />
                                    <p className="text-white/70 text-sm leading-relaxed tracking-wide">
                                        {t(`briefing.quotes.${briefing.data.quote_key}`) as string}
                                    </p>
                                </motion.div>
                            )}
                        </div>
                    )}
                </div>
                
                <button onClick={() => window.location.href = '/calendar'} className="px-6 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold border border-white/10 text-xs tracking-widest uppercase transition-all active:scale-95 shrink-0">
                    {t('briefing.view_calendar') as string}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Case Management Header */}
      <div className="flex justify-between items-center mb-6 flex-shrink-0">
        <div>
          <h1 className="text-4xl font-black text-text-primary tracking-tighter">{t('dashboard.mainTitle') as string}</h1>
          <p className="text-text-secondary font-medium mt-1">{t('dashboard.subtitle') as string}</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-start to-primary-end rounded-2xl text-white font-black shadow-lg shadow-primary-start/20 transition-all active:scale-95">
          <Plus size={22} strokeWidth={3} /> {t('dashboard.newCase') as string}
        </button>
      </div>

      {/* Main Grid */}
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-10 w-10 text-primary-start" /></div>
      ) : (
        <div className="flex-1 overflow-y-auto custom-scrollbar pr-2 pb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cases.map((c) => (<CaseCard key={c.id} caseData={c} onDelete={() => loadData()} />))}
          </div>
        </div>
      )}

      {/* Modals */}
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