// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V27.0 (MOBILE UI POLISH)
// 1. UI: Optimized 'Virtual Guardian' card for mobile (font scaling, padding adjustments).
// 2. UI: Improved 'Case Management' header alignment for small screens.
// 3. LOGIC: Preserved all real-time ticking and deletion logic.

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
      case 'HOLIDAY': return { style: 'from-indigo-950 to-black border-indigo-500/50', icon: <PartyPopper className="h-5 w-5 sm:h-6 sm:w-6 text-indigo-400" /> };
      case 'WEEKEND': return { style: 'from-teal-950 to-black border-teal-500/50', icon: <Coffee className="h-5 w-5 sm:h-6 sm:w-6 text-teal-400" /> };
      case 'CRITICAL': return { style: 'from-red-950 via-red-900/40 to-black border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.2)]', icon: <ShieldAlert className="h-5 w-5 sm:h-6 sm:w-6 animate-pulse text-red-500" /> };
      case 'WARNING': return { style: 'from-amber-950 to-black border-amber-500/50', icon: <AlertTriangle className="h-5 w-5 sm:h-6 sm:w-6 text-amber-400" /> };
      default: return { style: 'from-emerald-950 to-black border-emerald-500/50', icon: <CheckCircle2 className="h-5 w-5 sm:h-6 sm:w-6 text-emerald-400" /> };
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

  const handleDeleteCase = (caseId: string) => {
    setCaseToDeleteId(caseId); 
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-8 h-full flex flex-col">
      <AnimatePresence mode="wait">
        {briefing && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className={`shrink-0 mb-8 rounded-2xl shadow-2xl border ${theme.style.split(' ')[2]} overflow-hidden ring-1 ring-white/5`}>
            <div className={`p-5 sm:p-6 bg-gradient-to-br ${theme.style}`}>
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6 sm:gap-8">
                
                {/* 1. GUARDIAN IDENTITY - Mobile Optimized */}
                <div className="flex items-start gap-3 sm:gap-5">
                  <div className="p-2.5 sm:p-3 bg-white/10 rounded-xl backdrop-blur-md shrink-0 shadow-inner border border-white/5">
                    {theme.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-[9px] sm:text-[10px] font-black uppercase tracking-[0.2em] text-white/40 mb-1">
                      {t('briefing.kujdestari_title', 'KUJDESTARI VIRTUAL')}
                    </h2>
                    <p className="font-bold text-lg sm:text-2xl text-white tracking-tight leading-snug break-words">
                        {t(`briefing.greetings.${briefing.greeting_key}`, briefing.data || {}) as string}
                    </p>
                    <p className="text-white/60 font-medium mt-1.5 text-xs sm:text-sm italic leading-relaxed">
                        {t(`briefing.messages.${briefing.message_key}`, { 
                          ...(briefing.data || {}), 
                          holiday_name: briefing.data?.holiday ? t(`holidays.${briefing.data.holiday}`) : '' 
                        }) as string}
                    </p>
                  </div>
                </div>

                {/* 2. RISK RADAR & QUOTES */}
                <div className="flex-1 w-full max-w-2xl">
                    {briefing.risk_radar && briefing.risk_radar.length > 0 ? (
                        <div className="space-y-2.5">
                            <h3 className="text-[9px] font-black uppercase tracking-[0.2em] text-white/30 ml-1">RADARI I RREZIKUT</h3>
                            {briefing.risk_radar.map((item: RiskAlert) => (
                                <motion.div 
                                    key={item.id} 
                                    className={`p-2.5 sm:p-3 rounded-xl border flex items-center justify-between gap-3 backdrop-blur-md ${
                                        item.level === 'LEVEL_1_PREKLUZIV' 
                                        ? 'bg-red-500/10 border-red-500/30' 
                                        : 'bg-amber-500/10 border-amber-500/20'
                                    }`}
                                >
                                    <div className="flex items-center gap-2.5 min-w-0">
                                        <div className={`w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full shrink-0 ${item.level === 'LEVEL_1_PREKLUZIV' ? 'bg-red-500 animate-ping' : 'bg-amber-500'}`} />
                                        <span className={`text-xs sm:text-sm font-bold truncate ${item.level === 'LEVEL_1_PREKLUZIV' ? 'text-red-100' : 'text-amber-100'}`}>
                                            {item.title}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-1.5 px-2 py-1 bg-black/40 rounded-lg border border-white/5 shrink-0">
                                        <Timer size={12} className={item.level === 'LEVEL_1_PREKLUZIV' ? 'text-red-400' : 'text-amber-400'} />
                                        <span className="text-[10px] sm:text-xs font-mono font-bold text-white tabular-nums">
                                            {formatCountdown(item.seconds_remaining)}
                                        </span>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    ) : (
                        <div className="h-full flex items-center">
                            {briefing.status === 'OPTIMAL' && briefing.data?.quote_key && (
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-start gap-3 p-3.5 bg-white/5 rounded-xl border border-white/10 italic w-full">
                                    <QuoteIcon size={14} className="text-emerald-400 shrink-0 mt-0.5 opacity-50" />
                                    <p className="text-white/70 text-xs sm:text-sm leading-relaxed tracking-wide">
                                        {t(`briefing.quotes.${briefing.data.quote_key}`) as string}
                                    </p>
                                </motion.div>
                            )}
                        </div>
                    )}
                </div>
                
                {/* 3. CALENDAR ACTION */}
                <button 
                    onClick={() => window.location.href = '/calendar'} 
                    className="w-full lg:w-auto px-5 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold border border-white/10 text-xs tracking-widest uppercase transition-all active:scale-95 shrink-0 flex items-center justify-center gap-2"
                >
                    <Calendar size={14} className="opacity-70" />
                    {t('briefing.view_calendar', 'Kalendari')}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Case Management Header - Clean & Aligned */}
      <div className="flex flex-row justify-between items-end mb-6 gap-4">
        <div>
          <h1 className="text-2xl sm:text-4xl font-black text-white tracking-tighter">
            {t('dashboard.mainTitle', 'Pasqyra e Rasteve')}
          </h1>
          <p className="text-xs sm:text-base text-gray-400 font-medium mt-1">
            {t('dashboard.subtitle', 'Menaxhoni rastet tuaja.')}
          </p>
        </div>
        <button 
            onClick={() => setShowCreateModal(true)} 
            className="flex items-center gap-2 px-4 py-2.5 sm:px-6 sm:py-3 bg-blue-600 hover:bg-blue-500 rounded-xl sm:rounded-2xl text-white font-bold shadow-lg shadow-blue-900/20 transition-all active:scale-95 shrink-0"
        >
          <Plus size={18} strokeWidth={3} /> 
          <span className="text-xs sm:text-sm">{t('dashboard.newCase', 'Rast i Ri')}</span>
        </button>
      </div>

      {/* Main Grid */}
      {isLoading ? (
        <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-10 w-10 text-blue-500" /></div>
      ) : (
        <div className="flex-1 overflow-y-auto custom-scrollbar pb-8">
          {cases.length === 0 ? (
             <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
                    <ShieldAlert size={32} className="opacity-20" />
                </div>
                <p>Nuk u gjetën raste.</p>
             </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                {cases.map((c) => (<CaseCard key={c.id} caseData={c} onDelete={handleDeleteCase} />))}
            </div>
          )}
        </div>
      )}

      {/* CREATE MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-[#1a1b1e] border border-white/10 w-full max-w-md p-6 sm:p-8 rounded-3xl shadow-2xl">
            <h2 className="text-2xl font-black text-white mb-6 tracking-tight">{t('dashboard.createCaseTitle', 'Krijo Rast të Ri')}</h2>
            <form onSubmit={handleCreateCase} className="space-y-4">
              <input required placeholder={t('dashboard.caseTitle', 'Titulli i Lëndës')} value={newCaseData.title} onChange={(e) => setNewCaseData(p => ({...p, title: e.target.value}))} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none focus:ring-2 ring-blue-500 text-white placeholder-gray-500" />
              <div className="pt-4 border-t border-white/10 space-y-3">
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Të dhënat e klientit</p>
                <input required placeholder={t('dashboard.clientName', 'Emri i Klientit')} value={newCaseData.clientName} onChange={(e) => setNewCaseData(p => ({...p, clientName: e.target.value}))} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none focus:border-white/20 text-white placeholder-gray-500" />
                <input placeholder={t('dashboard.clientEmail', 'Email')} value={newCaseData.clientEmail} onChange={(e) => setNewCaseData(p => ({...p, clientEmail: e.target.value}))} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none focus:border-white/20 text-white placeholder-gray-500" />
                <input placeholder={t('dashboard.clientPhone', 'Telefon')} value={newCaseData.clientPhone} onChange={(e) => setNewCaseData(p => ({...p, clientPhone: e.target.value}))} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 outline-none focus:border-white/20 text-white placeholder-gray-500" />
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowCreateModal(false)} className="px-5 py-2.5 font-bold text-gray-400 hover:text-white transition-all text-sm">{t('general.cancel', 'Anulo')}</button>
                <button type="submit" disabled={isCreating} className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold shadow-lg flex items-center gap-2 active:scale-95 text-sm">
                    {isCreating ? <Loader2 className="animate-spin h-4 w-4" /> : t('general.create', 'Krijo')}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}

      {/* DELETE CONFIRMATION MODAL */}
      {caseToDeleteId && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[110] p-4">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }} 
            animate={{ opacity: 1, scale: 1 }} 
            className="bg-[#1a1b1e] border border-red-500/30 w-full max-w-sm p-6 rounded-3xl shadow-2xl text-center"
          >
            <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-red-500/20">
                <Trash2 className="h-8 w-8 text-red-500" />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">{t('caseDelete.confirmTitle', 'Fshij Rastin?')}</h2>
            <p className="text-gray-400 text-sm mb-6 leading-relaxed">{t('caseDelete.confirmMessage', 'Kjo veprim është i pakthyeshëm. Të gjitha dokumentet dhe të dhënat e këtij rasti do të fshihen.')}</p>
            <div className="flex justify-center gap-3">
              <button 
                type="button" 
                onClick={() => setCaseToDeleteId(null)} 
                className="flex-1 px-4 py-2.5 font-bold text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-xl transition-all text-sm"
              >
                {t('general.cancel', 'Anulo')}
              </button>
              <button 
                type="button" 
                onClick={confirmDeleteCase} 
                disabled={isDeletingCase}
                className="flex-1 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold shadow-lg flex items-center justify-center gap-2 active:scale-95 text-sm disabled:opacity-50"
              >
                {isDeletingCase ? <Loader2 className="animate-spin h-4 w-4" /> : t('general.delete', 'Fshij')}
              </button>
            </div>
          </motion.div>
        </div>
      )}

      <DayEventsModal isOpen={isBriefingOpen} onClose={() => setIsBriefingOpen(false)} date={new Date()} events={todaysEvents} t={t} onAddEvent={() => { setIsBriefingOpen(false); window.location.href = '/calendar'; }} />
    </div>
  );
};

export default DashboardPage;