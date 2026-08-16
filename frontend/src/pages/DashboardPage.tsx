// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V9.5 (HIGH-CONTRAST THEME-AWARE DESTRUCTION MODAL)

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
  
  const [searchTerm, setSearchTerm] = useState('');

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
      setCases(Array.isArray(cData) ? cData : []);
      setBriefing(bData);
      setFetchTimestamp(Date.now());
      if (!hasCheckedBriefing.current && Array.isArray(eData) && eData.length > 0) {
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

  const filteredCases = useMemo(() => {
    if (!searchTerm.trim()) return cases;
    const term = searchTerm.toLowerCase();
    return cases.filter(c => {
      const titleStr = typeof c.title === 'string' ? c.title.toLowerCase() : '';
      const nameStr = typeof c.client?.name === 'string' ? c.client.name.toLowerCase() : '';
      const emailStr = typeof c.client?.email === 'string' ? c.client.email.toLowerCase() : '';
      return titleStr.includes(term) || nameStr.includes(term) || emailStr.includes(term);
    });
  }, [cases, searchTerm]);

  const inputClasses = "w-full px-5 h-11 bg-surface border border-main rounded-xl text-text-primary placeholder:text-text-disabled text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all";
  const labelClasses = "block text-[10px] font-black text-primary-start uppercase tracking-widest mb-1.5 ml-1";

  const getGreeting = (): string => {
    if (holidayBriefing.isHoliday) {
      return holidayBriefing.greeting || '';
    }
    if (effectiveBriefing) {
      const raw = t(`briefing.greetings.${effectiveBriefing.greeting_key}`, effectiveBriefing.data || {});
      const fullGreeting = typeof raw === 'string' ? raw : (raw ? String(raw) : '');
      if (!fullGreeting) return '';
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
      return holidayBriefing.greeting || '';
    }
    if (effectiveBriefing) {
      const raw = t(`briefing.messages.${effectiveBriefing.message_key}`, { 
        ...(effectiveBriefing.data || {}), 
        holiday_name: effectiveBriefing.data?.holiday ? t(`holidays.${effectiveBriefing.data.holiday}`) : '' 
      });
      return typeof raw === 'string' ? raw : (raw ? String(raw) : '');
    }
    return '';
  };

  const getMainContent = () => {
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

    const hasRiskRadar = effectiveBriefing?.risk_radar && effectiveBriefing.risk_radar.length > 0;
    if (hasRiskRadar) {
      return (
        <div className="space-y-3">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-text-secondary/30 ml-1 italic">RADARI I RREZIKUT</h3>
          {effectiveBriefing!.risk_radar!.map((item: RiskAlert) => (
            <div key={item.id} className={`p-4 rounded-2xl border border-main flex items-center justify-between gap-4 backdrop-blur-xl transition-all ${item.level === 'LEVEL_1_PREKLUZIV' ? 'bg-danger-start/10 border-danger-start/20' : 'bg-warning-start/10 border-warning-start/20'}`}>
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-2 h-2 rounded-full shrink-0 ${item.level === 'LEVEL_1_PREKLUZIV' ? 'bg-danger-start animate-ping' : 'bg-warning-start'}`} />
                <span className={`text-xs sm:text-sm font-black uppercase tracking-tight ${item.level === 'LEVEL_1_PREKLUZIV' ? 'text-danger-start' : 'text-warning-start'}`}>
                  {item.title}
                </span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-black/40 rounded-xl border border-main shrink-0">
                <Timer size={14} className={item.level === 'LEVEL_1_PREKLUZIV' ? 'text-danger-start' : 'text-warning-start'} />
                <span className="text-xs font-black font-mono text-text-primary tabular-nums">{formatCountdown(item.seconds_remaining)}</span>
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (todaysEvents.length > 0) {
      const previewEvents = todaysEvents.slice(0, 3);
      return (
        <div className="space-y-2">
          <h3 className="text-[10px] font-black uppercase tracking-[0.3em] text-text-secondary/30 ml-1 italic">NGJARJE SOT</h3>
          {previewEvents.map(event => (
            <div key={event.id} className="p-3 rounded-xl border border-main bg-surface/10 flex items-center gap-3">
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

    return <div className="h-full"></div>;
  };

  if (!effectiveBriefing && !isLoading) {
    return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-8 h-auto lg:h-[calc(100dvh-64px)] lg:overflow-hidden flex flex-col relative bg-canvas">
      <AnimatePresence mode="wait">
        {effectiveBriefing && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }} 
            animate={{ opacity: 1, y: 0 }} 
            className="glass-panel shrink-0 mb-6 rounded-[2rem] border border-main backdrop-blur-md overflow-hidden shadow-sm"
          >
            <div className="p-5 sm:p-8 bg-gradient-to-br briefing-gradient-optimal">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                {/* Left: Greeting */}
                <div className="flex items-start gap-4">
                  <div className="glass-panel p-3 rounded-2xl shrink-0 border border-main shadow-sm bg-surface">
                    {theme.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1.5">
                      <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">
                        {t('briefing.kujdestari_title', 'KUJDESTARI VIRTUAL')}
                      </h2>
                      <div className="w-1.5 h-1.5 rounded-full bg-status-success animate-pulse shrink-0" />
                    </div>
                    <p className="font-bold text-lg sm:text-2xl text-text-primary tracking-tight leading-snug">
                      {getGreeting()}
                    </p>
                    <p className="text-text-secondary font-semibold mt-1 text-xs sm:text-sm italic">
                      {getSubtitle()}
                    </p>
                  </div>
                </div>

                {/* Middle: Risk/Events content */}
                <div className="w-full md:max-w-xs">
                  {getMainContent()}
                </div>

                {/* Right: Calendar Button */}
                <div className="shrink-0 w-full md:w-auto">
                  <button 
                    type="button"
                    onClick={() => window.location.href = '/calendar'} 
                    className="h-11 w-full md:w-auto px-5 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2.5 bg-primary-start hover:bg-opacity-95 text-white shadow-lg shadow-primary-start/15 hover:scale-[1.02] active:scale-95 transition-all focus:outline-none"
                  >
                    <Calendar size={16} />
                    {t('briefing.view_calendar', 'Kalendari')}
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-center gap-3 w-full h-11 shrink-0 mb-6 px-1">
        <div className="relative flex-1 h-11">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-text-muted" size={18} />
          <input
            type="text"
            placeholder={t('dashboard.searchPlaceholder', 'Kërko rast...')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full h-11 pl-11 pr-4 bg-surface border border-main rounded-xl text-sm text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all"
          />
        </div>
        <button 
            type="button"
            onClick={() => setShowCreateModal(true)} 
            className="h-11 px-4 sm:px-6 bg-primary-start hover:bg-opacity-95 text-white flex items-center justify-center gap-2 rounded-xl font-bold text-xs uppercase tracking-wider shrink-0 shadow-lg shadow-primary-start/15 focus:outline-none"
            title={t('dashboard.newCase', 'Rast i Ri')}
        >
          <Plus size={16} strokeWidth={3} /> 
          <span className="hidden sm:inline">{t('dashboard.newCase', 'Rast i Ri')}</span>
        </button>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center"><Loader2 className="animate-spin h-12 w-12 text-primary-start" /></div>
      ) : (
        <div className="flex-1 overflow-y-auto custom-finance-scroll pb-8">
          {filteredCases.length === 0 ? (
             <div className="glass-panel flex flex-col items-center justify-center py-20 border border-main bg-surface">
                <div className="w-16 h-16 bg-hover rounded-2xl flex items-center justify-center mb-4 border border-main">
                    <ShieldAlert size={36} className="opacity-25 text-text-secondary" />
                </div>
                <p className="font-bold uppercase tracking-wider text-xs italic text-text-secondary">
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

      {/* Modals */}
      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4 overflow-y-auto custom-finance-scroll">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }} 
              animate={{ opacity: 1, scale: 1, y: 0 }} 
              exit={{ opacity: 0, scale: 0.95 }} 
              className="glass-panel w-full max-w-lg p-6 sm:p-8 rounded-[2rem] shadow-2xl border border-main bg-canvas"
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-text-primary tracking-tight uppercase">{t('dashboard.createCaseTitle', 'Krijo Rast të Ri')}</h2>
                <button 
                  onClick={() => setShowCreateModal(false)}
                  className="flex items-center justify-center w-11 h-11 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl focus:outline-none"
                  aria-label="Close"
                >
                  ✕
                </button>
              </div>
              <form onSubmit={handleCreateCase} className="space-y-4">
                <div className="space-y-1.5">
                  <label className={labelClasses}>Lënda</label>
                  <input required placeholder={t('dashboard.caseTitle', 'Titulli i Lëndës')} value={newCaseData.title} onChange={(e) => setNewCaseData(p => ({...p, title: e.target.value}))} className={inputClasses} />
                </div>
                <div className="pt-4 border-t border-main space-y-4">
                  <p className={labelClasses}>Detajet e Klientit</p>
                  <input required placeholder={t('dashboard.clientName', 'Emri i Klientit')} value={newCaseData.clientName} onChange={(e) => setNewCaseData(p => ({...p, clientName: e.target.value}))} className={inputClasses} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <input placeholder={t('dashboard.clientEmail', 'Email')} value={newCaseData.clientEmail} onChange={(e) => setNewCaseData(p => ({...p, clientEmail: e.target.value}))} className={inputClasses} />
                    <input placeholder={t('dashboard.clientPhone', 'Telefon')} value={newCaseData.clientPhone} onChange={(e) => setNewCaseData(p => ({...p, clientPhone: e.target.value}))} className={inputClasses} />
                  </div>
                </div>
                <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-6 border-t border-main">
                  <button type="button" onClick={() => setShowCreateModal(false)} className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-all focus:outline-none">{t('general.cancel', 'Anulo')}</button>
                  <button type="submit" disabled={isCreating} className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-bold bg-primary-start hover:bg-opacity-95 text-white flex items-center justify-center gap-2 focus:outline-none shadow-lg shadow-primary-start/15">
                      {isCreating ? <Loader2 className="animate-spin h-4 w-4" /> : t('general.create', 'Krijo')}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {/* DELETION CONFIRMATION MODAL WITH THEME-AWARE CONTRAST */}
        {caseToDeleteId && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[110] p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-panel w-full max-w-md p-6 sm:p-8 rounded-[2rem] shadow-2xl text-center border border-main bg-surface"
            >
              <div className="w-16 h-16 bg-rose-500/10 rounded-2xl flex items-center justify-center mx-auto mb-5 border border-rose-500/30">
                <Trash2 className="h-8 w-8 text-rose-500" />
              </div>
              <h2 className="text-xl font-bold text-text-primary mb-2 uppercase tracking-tight">
                {t('caseDelete.confirmTitle', 'Fshij Rastin?')}
              </h2>
              <p className="text-text-secondary text-sm mb-6 leading-relaxed italic font-medium">
                {t('caseDelete.confirmMessage', 'Kjo veprim është i pakthyeshëm. Të gjitha dokumentet do të fshihen.')}
              </p>
              <div className="flex gap-3 justify-center">
                <button
                  type="button"
                  onClick={() => setCaseToDeleteId(null)}
                  className="w-full h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-all focus:outline-none"
                >
                  {t('general.cancel', 'Anulo')}
                </button>
                <button
                  type="button"
                  onClick={confirmDeleteCase}
                  disabled={isDeletingCase}
                  className="w-full h-11 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-black flex items-center justify-center gap-2 active:scale-95 text-xs uppercase tracking-wider disabled:opacity-50 transition-all focus:outline-none shadow-lg shadow-rose-600/25 cursor-pointer"
                >
                  {isDeletingCase ? <Loader2 className="animate-spin h-4 w-4" /> : t('general.delete', 'Fshij')}
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