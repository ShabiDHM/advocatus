// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V32.0 (MOBILE GREETING FIX)
// 1. REFACTOR: Mobile greeting now breaks after comma (e.g., "Mirëmëngjes,\nShaban Bala").
// 2. CONSISTENCY: Uses same glass styles, all existing functionality preserved.
// 3. STATUS: 100% consistent with System Architectural Snapshot.

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, Loader2, AlertTriangle, CheckCircle2, ShieldAlert, 
  PartyPopper, Coffee, Quote as QuoteIcon, Timer, Trash2, Calendar
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
  
  const [now, setNow] = useState<number>(Date.now());
  const [fetchTimestamp, setFetchTimestamp] = useState<number>(Date.now());

  const [caseToDeleteId, setCaseToDeleteId] = useState<string | null>(null);
  const [isDeletingCase, setIsDeletingCase] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatCountdown = (initialSeconds: number) => {
    const elapsedSeconds = Math.floor((now - fetchTimestamp) / 1000);
    const remaining = initialSeconds - elapsedSeconds;
    if (remaining <= 0) return t('adminBriefing.metric.today', 'Sot');
    const h = Math.floor(remaining / 3600);
    const m = Math.floor((remaining % 3600) / 60);
    const s = remaining % 60;
    return `${h}h ${m}m ${s}s`;
  };

  const theme = useMemo(() => {
    const status = briefing?.status || 'OPTIMAL';
    switch (status) {
      case 'HOLIDAY': return { style: 'from-indigo-950/40 to-black/40 border-indigo-500/50', icon: <PartyPopper className="h-6 w-6 text-indigo-400" /> };
      case 'WEEKEND': return { style: 'from-teal-950/40 to-black/40 border-teal-500/50', icon: <Coffee className="h-6 w-6 text-teal-400" /> };
      case 'CRITICAL': return { style: 'from-red-950/40 via-red-900/40 to-black/40 border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.2)]', icon: <ShieldAlert className="h-6 w-6 animate-pulse text-red-500" /> };
      case 'WARNING': return { style: 'from-amber-950/40 to-black/40 border-amber-500/50', icon: <AlertTriangle className="h-6 w-6 text-amber-400" /> };
      default: return { style: 'from-emerald-950/40 to-black/40 border-emerald-500/50', icon: <CheckCircle2 className="h-6 w-6 text-emerald-400" /> };
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
      setFetchTimestamp(Date.now());
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
      alert(t('error.generic', 'Ndodhi një gabim.'));
    } finally {
      setIsCreating(false);
    }
  };

  const confirmDeleteCase = async () => {
    if (!caseToDeleteId) return;
    setIsDeletingCase(true);
    try {
      await apiService.deleteCase(caseToDeleteId);
      await loadData();
      setCaseToDeleteId(null);
    } catch (error) {
      alert(t('error.caseDeleteFailed', 'Dështoi fshirja e rastit.'));
    } finally {
      setIsDeletingCase(false);
    }
  };

  // Standardized glass input and label classes
  const inputClasses = "glass-input w-full px-5 py-3.5 rounded-2xl text-sm transition-all placeholder:text-text-secondary/50";
  const labelClasses = "block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-8 h-full flex flex-col relative">
      <AnimatePresence mode="wait">
        {briefing && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }} 
            animate={{ opacity: 1, y: 0 }} 
            className={`shrink-0 mb-8 rounded-[2rem] border backdrop-blur-md overflow-hidden shadow-2xl ${theme.style.split(' ')[2]}`}
          >
            <div className={`p-6 sm:p-8 bg-gradient-to-br ${theme.style}`}>
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-8">
                <div className="flex items-start gap-5">
                  <div className="glass-high p-4 rounded-2xl shrink-0 border border-white/10 shadow-xl">
                    {theme.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-white/40 mb-2">
                      {t('briefing.kujdestari_title', 'KUJDESTARI VIRTUAL')}
                    </h2>
                    {/* Mobile-friendly greeting: split at first comma */}
                    <p className="font-black text-xl sm:text-2xl text-white tracking-tight leading-tight">
                      {(() => {
                        const fullGreeting = t(`briefing.greetings.${briefing.greeting_key}`, briefing.data || {}) as string;
                        const commaIndex = fullGreeting.indexOf(',');
                        if (commaIndex === -1) return fullGreeting;
                        const before = fullGreeting.substring(0, commaIndex + 1); // include comma
                        const after = fullGreeting.substring(commaIndex + 1).trim();
                        return (
                          <>
                            <span className="block sm:inline">{before}</span>
                            <span className="block sm:inline sm:ml-1">{after}</span>
                          </>
                        );
                      })()}
                    </p>
                    <p className="text-white/60 font-semibold mt-2 text-sm sm:text-base italic">
                        {t(`briefing.messages.${briefing.message_key}`, { 
                          ...(briefing.data || {}), 
                          holiday_name: briefing.data?.holiday ? t(`holidays.${briefing.data.holiday}`) : '' 
                        }) as string}
                    </p>
                  </div>
                </div>

                <div className="flex-1 w-full max-w-2xl">
                    {briefing.risk_radar && briefing.risk_radar.length > 0 ? (
                        <div className="space-y-3">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-white/30 ml-1 italic">RADARI I RREZIKUT</h3>
                            {briefing.risk_radar.map((item: RiskAlert) => (
                                <div key={item.id} className={`p-4 rounded-2xl border flex items-center justify-between gap-4 backdrop-blur-xl transition-all ${item.level === 'LEVEL_1_PREKLUZIV' ? 'bg-red-500/10 border-red-500/30' : 'bg-amber-500/10 border-amber-500/20'}`}>
                                    <div className="flex items-center gap-3 min-w-0">
                                        <div className={`w-2 h-2 rounded-full shrink-0 ${item.level === 'LEVEL_1_PREKLUZIV' ? 'bg-red-500 animate-ping' : 'bg-amber-500'}`} />
                                        <span className={`text-xs sm:text-sm font-black uppercase tracking-tight ${item.level === 'LEVEL_1_PREKLUZIV' ? 'text-red-100' : 'text-amber-100'}`}>
                                            {item.title}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-1.5 bg-black/40 rounded-xl border border-white/5 shrink-0">
                                        <Timer size={14} className={item.level === 'LEVEL_1_PREKLUZIV' ? 'text-red-400' : 'text-amber-400'} />
                                        <span className="text-xs font-black font-mono text-white tabular-nums">{formatCountdown(item.seconds_remaining)}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="h-full flex items-center">
                            {briefing.status === 'OPTIMAL' && briefing.data?.quote_key && (
                                <div className="glass-panel p-5 rounded-2xl w-full">
                                    <QuoteIcon size={18} className="text-primary-start shrink-0 mt-1 opacity-40 inline mr-2" />
                                    <span className="text-white/70 text-sm sm:text-base leading-relaxed tracking-wide font-medium">
                                        {t(`briefing.quotes.${briefing.data.quote_key}`) as string}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}
                </div>
                
                <button 
                    onClick={() => window.location.href = '/calendar'} 
                    className="glass-button w-full lg:w-auto px-8 py-4 rounded-2xl font-black text-[10px] tracking-[0.2em] uppercase flex items-center justify-center gap-3"
                >
                    <Calendar size={18} className="opacity-50" />
                    {t('briefing.view_calendar', 'Kalendari')}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex flex-row justify-between items-end mb-8 gap-4 px-2">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            {t('dashboard.mainTitle', 'Pasqyra e Rasteve')}
          </h1>
          <p className="text-xs sm:text-sm text-gray-500 font-bold mt-1 uppercase tracking-widest opacity-60">
            {t('dashboard.subtitle', 'Menaxhimi i Lëndëve Aktive')}
          </p>
        </div>
        <button 
            onClick={() => setShowCreateModal(true)} 
            className="flex items-center gap-3 px-6 py-3.5 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-2xl hover:shadow-primary-start/20 rounded-2xl text-white font-black text-xs uppercase tracking-[0.1em] transition-all active:scale-95 shrink-0"
        >
          <Plus size={18} strokeWidth={4} /> 
          <span className="hidden sm:inline">{t('dashboard.newCase', 'Rast i Ri')}</span>
        </button>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-12 w-12 text-primary-start" /></div>
      ) : (
        <div className="flex-1 overflow-y-auto custom-scrollbar pb-8">
          {cases.length === 0 ? (
             <div className="glass-panel flex flex-col items-center justify-center py-24 text-gray-600">
                <div className="w-20 h-20 bg-white/5 rounded-3xl flex items-center justify-center mb-6 border border-white/5">
                    <ShieldAlert size={40} className="opacity-20" />
                </div>
                <p className="font-black uppercase tracking-widest text-xs italic">Nuk u gjetën raste aktive.</p>
             </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {cases.map((c) => (<CaseCard key={c.id} caseData={c} onDelete={(id) => setCaseToDeleteId(id)} />))}
            </div>
          )}
        </div>
      )}

      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 bg-background-dark/60 backdrop-blur-xl flex items-center justify-center z-[100] p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }} 
              animate={{ opacity: 1, scale: 1, y: 0 }} 
              exit={{ opacity: 0, scale: 0.95 }} 
              className="glass-high w-full max-w-lg p-8 sm:p-10 rounded-[3rem] shadow-2xl shadow-black/60"
            >
              <h2 className="text-2xl font-bold text-white mb-8 tracking-tight uppercase">{t('dashboard.createCaseTitle', 'Krijo Rast të Ri')}</h2>
              <form onSubmit={handleCreateCase} className="space-y-6">
                <div>
                  <label className={labelClasses}>Lënda</label>
                  <input required placeholder={t('dashboard.caseTitle', 'Titulli i Lëndës')} value={newCaseData.title} onChange={(e) => setNewCaseData(p => ({...p, title: e.target.value}))} className={inputClasses} />
                </div>
                <div className="pt-6 border-t border-white/10 space-y-5">
                  <p className={labelClasses}>Detajet e Klientit</p>
                  <input required placeholder={t('dashboard.clientName', 'Emri i Klientit')} value={newCaseData.clientName} onChange={(e) => setNewCaseData(p => ({...p, clientName: e.target.value}))} className={inputClasses} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <input placeholder={t('dashboard.clientEmail', 'Email')} value={newCaseData.clientEmail} onChange={(e) => setNewCaseData(p => ({...p, clientEmail: e.target.value}))} className={inputClasses} />
                    <input placeholder={t('dashboard.clientPhone', 'Telefon')} value={newCaseData.clientPhone} onChange={(e) => setNewCaseData(p => ({...p, clientPhone: e.target.value}))} className={inputClasses} />
                  </div>
                </div>
                <div className="flex justify-between items-center mt-10">
                  <button type="button" onClick={() => setShowCreateModal(false)} className="px-6 py-4 font-bold text-gray-400 hover:text-white transition-all text-xs uppercase tracking-widest">{t('general.cancel', 'Anulo')}</button>
                  <button type="submit" disabled={isCreating} className="glass-button px-10 h-14 rounded-2xl flex items-center justify-center gap-3 active:scale-95 text-xs uppercase tracking-widest disabled:opacity-50">
                      {isCreating ? <Loader2 className="animate-spin h-5 w-5" /> : t('general.create', 'Krijo')}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {caseToDeleteId && (
          <div className="fixed inset-0 bg-background-dark/60 backdrop-blur-xl flex items-center justify-center z-[110] p-4">
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="glass-high w-full max-w-md p-10 rounded-[3rem] shadow-2xl text-center border border-rose-500/30">
              <div className="w-20 h-20 bg-rose-500/10 rounded-3xl flex items-center justify-center mx-auto mb-6 border border-rose-500/20 shadow-inner">
                  <Trash2 className="h-10 w-10 text-rose-500" />
              </div>
              <h2 className="text-2xl font-black text-white mb-3 uppercase tracking-tight">{t('caseDelete.confirmTitle', 'Fshij Rastin?')}</h2>
              <p className="text-gray-400 text-sm mb-10 leading-relaxed italic font-medium">{t('caseDelete.confirmMessage', 'Kjo veprim është i pakthyeshëm. Të gjitha dokumentet do të fshihen.')}</p>
              <div className="flex justify-center gap-5">
                <button type="button" onClick={() => setCaseToDeleteId(null)} className="glass-button flex-1 h-14 rounded-2xl text-[10px] uppercase tracking-widest">{t('general.cancel', 'Anulo')}</button>
                <button type="button" onClick={confirmDeleteCase} disabled={isDeletingCase} className="flex-1 h-14 rounded-2xl bg-rose-600 hover:bg-rose-500 text-white font-black shadow-lg flex items-center justify-center gap-3 active:scale-95 text-[10px] uppercase tracking-widest disabled:opacity-50 transition-all">
                  {isDeletingCase ? <Loader2 className="animate-spin h-5 w-5" /> : t('general.delete', 'Fshij')}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <DayEventsModal isOpen={isBriefingOpen} onClose={() => setIsBriefingOpen(false)} date={new Date()} events={todaysEvents} t={t} onAddEvent={() => { setIsBriefingOpen(false); window.location.href = '/calendar'; }} />
    </div>
  );
};

export default DashboardPage;