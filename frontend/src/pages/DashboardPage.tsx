// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V8.1 (Removed fallback message)

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, Loader2, AlertTriangle, CheckCircle2, ShieldAlert, 
  PartyPopper, Coffee, Timer, Trash2, Calendar, Search
} from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent, BriefingResponse, RiskAlert } from '../data/types'; 
import CaseCard from '../components/CaseCard';
import DayEventsModal from '../components/DayEventsModal';
import { isSameDay, parseISO } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { getCurrentBriefingHoliday } from '../utils/kosovoHolidays';

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
  
  // Search state
  const [searchTerm, setSearchTerm] = useState('');

  // Client-side holiday detection (runs on every render)
  const holidayBriefing = useMemo(() => {
    const today = new Date();
    return getCurrentBriefingHoliday(today, (key: string) => t(key));
  }, [t]);

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

  // Final briefing: if holiday, create synthetic; else use backend
  const effectiveBriefing = useMemo((): BriefingResponse | null => {
    if (holidayBriefing.isHoliday) {
      return {
        status: 'HOLIDAY',
        greeting_key: `greeting.${holidayBriefing.holiday?.greetingKey || 'holiday'}`,
        message_key: `message.${holidayBriefing.holiday?.greetingKey || 'holiday'}`,
        data: {
          holiday: holidayBriefing.holiday?.name,
        },
        risk_radar: briefing?.risk_radar || [],
        count: 1,
      };
    }
    return briefing;
  }, [holidayBriefing, briefing]);

  const theme = useMemo(() => {
    const status = effectiveBriefing?.status || 'OPTIMAL';
    switch (status) {
      case 'HOLIDAY': 
        return { 
          style: 'from-indigo-950/40 to-black/40 border-indigo-500/50', 
          icon: <PartyPopper className="h-6 w-6 text-indigo-400" /> 
        };
      case 'WEEKEND': 
        return { 
          style: 'from-indigo-950/40 to-black/40 border-indigo-500/50', 
          icon: <Coffee className="h-6 w-6 text-indigo-400" /> 
        };
      case 'CRITICAL': 
        return { 
          style: 'from-red-950/40 via-red-900/40 to-black/40 border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.2)]', 
          icon: <ShieldAlert className="h-6 w-6 animate-pulse text-red-500" /> 
        };
      case 'WARNING': 
        return { 
          style: 'from-amber-950/40 to-black/40 border-amber-500/50', 
          icon: <AlertTriangle className="h-6 w-6 text-amber-400" /> 
        };
      default: 
        return { 
          style: 'from-indigo-950/40 to-black/40 border-indigo-500/50', 
          icon: <CheckCircle2 className="h-6 w-6 text-indigo-400" /> 
        };
    }
  }, [effectiveBriefing?.status]);

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

  // Filter cases based on search term
  const filteredCases = useMemo(() => {
    if (!searchTerm.trim()) return cases;
    const term = searchTerm.toLowerCase();
    return cases.filter(c => 
      c.title?.toLowerCase().includes(term) ||
      c.client?.name?.toLowerCase().includes(term) ||
      c.client?.email?.toLowerCase().includes(term)
    );
  }, [cases, searchTerm]);

  const inputClasses = "glass-input w-full px-5 py-3.5 rounded-2xl text-sm transition-all placeholder:text-text-secondary/50 border border-border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40";
  const labelClasses = "block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1";

  // Helper to get the correct greeting (prioritizing holiday, else backend)
  const getGreeting = (): string => {
    if (holidayBriefing.isHoliday) {
      return holidayBriefing.greeting;
    }
    if (effectiveBriefing) {
      const fullGreeting = t(`briefing.greetings.${effectiveBriefing.greeting_key}`, effectiveBriefing.data || {}) as string;
      const commaIndex = fullGreeting.indexOf(',');
      if (commaIndex === -1) return fullGreeting;
      const before = fullGreeting.substring(0, commaIndex + 1);
      const after = fullGreeting.substring(commaIndex + 1).trim();
      return `${before} ${after}`;
    }
    return '';
  };

  const getSubtitle = (): string => {
    if (holidayBriefing.isHoliday) {
      return holidayBriefing.greeting;
    }
    if (effectiveBriefing) {
      return t(`briefing.messages.${effectiveBriefing.message_key}`, { 
        ...(effectiveBriefing.data || {}), 
        holiday_name: effectiveBriefing.data?.holiday ? t(`holidays.${effectiveBriefing.data.holiday}`) : '' 
      }) as string;
    }
    return '';
  };

  // Strict priority content for the right panel (no motivational quote, no fallback message)
  const getMainContent = () => {
    // Priority 1: Holiday
    if (holidayBriefing.isHoliday) {
      return (
        <div className="h-full flex items-center justify-center text-center">
          <div className="space-y-2">
            <PartyPopper className="w-8 h-8 text-primary-start mx-auto opacity-70" />
            <p className="text-text-secondary text-sm italic">{holidayBriefing.greeting}</p>
          </div>
        </div>
      );
    }

    // Priority 2: Risk Alerts
    const hasRiskRadar = effectiveBriefing?.risk_radar && effectiveBriefing.risk_radar.length > 0;
    if (hasRiskRadar) {
      return (
        <div className="space-y-3">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-text-secondary/30 ml-1 italic">RADARI I RREZIKUT</h3>
          {effectiveBriefing!.risk_radar!.map((item: RiskAlert) => (
            <div key={item.id} className={`p-4 rounded-2xl border border-border-main flex items-center justify-between gap-4 backdrop-blur-xl transition-all ${item.level === 'LEVEL_1_PREKLUZIV' ? 'bg-danger-start/10' : 'bg-warning-start/10'}`}>
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-2 h-2 rounded-full shrink-0 ${item.level === 'LEVEL_1_PREKLUZIV' ? 'bg-danger-start animate-ping' : 'bg-warning-start'}`} />
                <span className={`text-xs sm:text-sm font-black uppercase tracking-tight ${item.level === 'LEVEL_1_PREKLUZIV' ? 'text-danger-start' : 'text-warning-start'}`}>
                  {item.title}
                </span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-black/40 rounded-xl border border-white/5 shrink-0">
                <Timer size={14} className={item.level === 'LEVEL_1_PREKLUZIV' ? 'text-danger-start' : 'text-warning-start'} />
                <span className="text-xs font-black font-mono text-text-primary tabular-nums">{formatCountdown(item.seconds_remaining)}</span>
              </div>
            </div>
          ))}
        </div>
      );
    }

    // Priority 3: Today's Events
    if (todaysEvents.length > 0) {
      const previewEvents = todaysEvents.slice(0, 3);
      return (
        <div className="space-y-2">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-text-secondary/30 ml-1 italic">NGJARJE SOT</h3>
          {previewEvents.map(event => (
            <div key={event.id} className="p-3 rounded-xl border border-border-main bg-surface/10 flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-primary-start" />
              <div>
                <p className="text-xs font-bold text-text-primary">{event.title}</p>
                <p className="text-[10px] text-text-muted">
                  {new Date(event.start_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))}
          {todaysEvents.length > 3 && (
            <button className="text-[10px] text-primary-start hover:underline mt-2 hover-lift shadow-sm" onClick={() => setIsBriefingOpen(true)}>
              + {todaysEvents.length - 3} më shumë
            </button>
          )}
        </div>
      );
    }

    // No content – return empty div (removed fallback message)
    return <div className="h-full"></div>;
  };

  if (!effectiveBriefing && !isLoading) {
    return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-8 h-full flex flex-col relative bg-canvas">
      <AnimatePresence mode="wait">
        {effectiveBriefing && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }} 
            animate={{ opacity: 1, y: 0 }} 
            className={`glass-panel shrink-0 mb-8 rounded-[2rem] border border-border-main backdrop-blur-md overflow-hidden shadow-sm briefing-gradient-optimal`}
          >
            <div className="p-6 sm:p-8 bg-gradient-to-br briefing-gradient-optimal">
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-8">
                <div className="flex items-start gap-5">
                  <div className="glass-panel p-4 rounded-2xl shrink-0 border border-border-main shadow-sm">
                    {theme.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-[10px] font-black uppercase tracking-[0.3em] text-text-secondary/40 mb-2">
                      {t('briefing.kujdestari_title', 'KUJDESTARI VIRTUAL')}
                    </h2>
                    <p className="font-black text-xl sm:text-2xl text-text-primary tracking-tight leading-tight">
                      {getGreeting()}
                    </p>
                    <p className="text-text-secondary font-semibold mt-2 text-sm sm:text-base italic">
                      {getSubtitle()}
                    </p>
                  </div>
                </div>

                <div className="flex-1 w-full max-w-2xl">
                  {getMainContent()}
                </div>
                
                <button 
                  onClick={() => window.location.href = '/calendar'} 
                  className="btn-secondary w-full lg:w-auto px-8 py-4 rounded-2xl font-black text-[10px] tracking-[0.2em] uppercase flex items-center justify-center gap-3 hover-lift shadow-sm"
                >
                  <Calendar size={18} className="opacity-50" />
                  {t('briefing.view_calendar', 'Kalendari')}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header with Search and Create Button - Removed old heading */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8 px-2">
        {/* Search input */}
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-text-muted" size={18} />
          <input
            type="text"
            placeholder={t('dashboard.searchPlaceholder', 'Kërko rast...')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="glass-input w-full pl-11 pr-4 py-3 rounded-xl text-sm border-border-main bg-surface focus:border-primary-start"
          />
        </div>
        
        <button 
            onClick={() => setShowCreateModal(true)} 
            className="btn-primary flex items-center gap-3 px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-[0.1em] active:scale-[0.98] shrink-0 hover-lift shadow-sm"
        >
          <Plus size={18} strokeWidth={4} /> 
          <span className="hidden sm:inline">{t('dashboard.newCase', 'Rast i Ri')}</span>
        </button>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-12 w-12 text-primary-start" /></div>
      ) : (
        <div className="flex-1 overflow-y-auto custom-scrollbar pb-8">
          {filteredCases.length === 0 ? (
             <div className="glass-panel flex flex-col items-center justify-center py-24 border border-border-main">
                <div className="w-20 h-20 bg-surface/50 rounded-3xl flex items-center justify-center mb-6 border border-border-main">
                    <ShieldAlert size={40} className="opacity-20 text-text-secondary" />
                </div>
                <p className="font-black uppercase tracking-widest text-xs italic text-text-secondary">
                  {searchTerm ? t('dashboard.noSearchResults', 'Nuk u gjet asnjë rast për këtë kërkim.') : t('dashboard.noCases', 'Nuk u gjetën raste aktive.')}
                </p>
             </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {filteredCases.map((c) => (<CaseCard key={c.id} caseData={c} onDelete={(id) => setCaseToDeleteId(id)} />))}
            </div>
          )}
        </div>
      )}

      {/* Modals (unchanged) */}
      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 bg-canvas/60 backdrop-blur-xl flex items-center justify-center z-[100] p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }} 
              animate={{ opacity: 1, scale: 1, y: 0 }} 
              exit={{ opacity: 0, scale: 0.95 }} 
              className="glass-panel w-full max-w-lg p-8 sm:p-10 rounded-[3rem] shadow-sm border border-border-main"
            >
              <h2 className="text-2xl font-bold text-text-primary mb-8 tracking-tight uppercase">{t('dashboard.createCaseTitle', 'Krijo Rast të Ri')}</h2>
              <form onSubmit={handleCreateCase} className="space-y-6">
                <div>
                  <label className={labelClasses}>Lënda</label>
                  <input required placeholder={t('dashboard.caseTitle', 'Titulli i Lëndës')} value={newCaseData.title} onChange={(e) => setNewCaseData(p => ({...p, title: e.target.value}))} className={inputClasses} />
                </div>
                <div className="pt-6 border-t border-border-main space-y-5">
                  <p className={labelClasses}>Detajet e Klientit</p>
                  <input required placeholder={t('dashboard.clientName', 'Emri i Klientit')} value={newCaseData.clientName} onChange={(e) => setNewCaseData(p => ({...p, clientName: e.target.value}))} className={inputClasses} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <input placeholder={t('dashboard.clientEmail', 'Email')} value={newCaseData.clientEmail} onChange={(e) => setNewCaseData(p => ({...p, clientEmail: e.target.value}))} className={inputClasses} />
                    <input placeholder={t('dashboard.clientPhone', 'Telefon')} value={newCaseData.clientPhone} onChange={(e) => setNewCaseData(p => ({...p, clientPhone: e.target.value}))} className={inputClasses} />
                  </div>
                </div>
                <div className="flex justify-between items-center mt-10">
                  <button type="button" onClick={() => setShowCreateModal(false)} className="px-6 py-4 font-bold text-text-secondary hover:text-text-primary transition-all text-xs uppercase tracking-widest">{t('general.cancel', 'Anulo')}</button>
                  <button type="submit" disabled={isCreating} className="btn-primary px-10 h-14 rounded-2xl flex items-center justify-center gap-3 active:scale-95 text-xs uppercase tracking-widest disabled:opacity-50 hover-lift shadow-sm">
                      {isCreating ? <Loader2 className="animate-spin h-5 w-5" /> : t('general.create', 'Krijo')}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {caseToDeleteId && (
          <div className="fixed inset-0 bg-canvas/60 backdrop-blur-xl flex items-center justify-center z-[110] p-4">
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="glass-panel w-full max-w-md p-10 rounded-[3rem] shadow-sm text-center border border-border-main">
              <div className="w-20 h-20 bg-danger-start/10 rounded-3xl flex items-center justify-center mx-auto mb-6 border border-border-main shadow-inner">
                  <Trash2 className="h-10 w-10 text-danger-start" />
              </div>
              <h2 className="text-2xl font-black text-text-primary mb-3 uppercase tracking-tight">{t('caseDelete.confirmTitle', 'Fshij Rastin?')}</h2>
              <p className="text-text-secondary text-sm mb-10 leading-relaxed italic font-medium">{t('caseDelete.confirmMessage', 'Kjo veprim është i pakthyeshëm. Të gjitha dokumentet do të fshihen.')}</p>
              <div className="flex justify-center gap-5">
                <button type="button" onClick={() => setCaseToDeleteId(null)} className="btn-secondary flex-1 h-14 rounded-2xl text-[10px] uppercase tracking-widest hover-lift shadow-sm">{t('general.cancel', 'Anulo')}</button>
                <button type="button" onClick={confirmDeleteCase} disabled={isDeletingCase} className="flex-1 h-14 rounded-2xl bg-danger-start hover:bg-danger-start/80 text-text-primary font-black flex items-center justify-center gap-3 active:scale-95 text-[10px] uppercase tracking-widest disabled:opacity-50 transition-all hover-lift shadow-sm">
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