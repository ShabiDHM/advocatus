// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - DASHBOARD V14.0 (ZERO HARDCODED COLORS)
// V14.0: Të gjitha ngjyrat kaluar në semantike — role-*, status-info, danger-start, etj.

import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, Loader2, AlertTriangle, CheckCircle2, ShieldAlert, 
  PartyPopper, Coffee, Timer, Trash2, Calendar, Search, X,
  Shield, Swords, Scale, Mic
} from 'lucide-react';
import { apiService } from '../services/api';
import { Case, CreateCaseRequest, CalendarEvent, BriefingResponse, RiskAlert } from '../data/types'; 
import CaseCard from '../components/CaseCard';
import DayEventsModal from '../components/DayEventsModal';
import { CreateEventModal, EventInitialValues } from '../components/calendar/CreateEventModal';
import { VoiceEventRecorder, ParsedVoiceEvent } from '../components/calendar/VoiceEventRecorder';
import { isSameDay, parseISO } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { getCurrentBriefingHoliday } from '../utils/kosovoHolidays';

type ClientPositionType = 'PLAINTIFF' | 'DEFENDANT' | 'NEUTRAL';

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [todaysEvents, setTodaysEvents] = useState<CalendarEvent[]>([]);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const [briefing, setBriefing] = useState<BriefingResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  
  const [clientPosition, setClientPosition] = useState<ClientPositionType>('PLAINTIFF');
  const [newCaseData, setNewCaseData] = useState({ 
    title: '', 
    clientName: '', 
    clientEmail: '', 
    clientPhone: '' 
  });
  
  const [now, setNow] = useState<number>(Date.now());
  const [fetchTimestamp, setFetchTimestamp] = useState<number>(Date.now());

  const [caseToDeleteId, setCaseToDeleteId] = useState<string | null>(null);
  const [isDeletingCase, setIsDeletingCase] = useState(false);
  
  const [searchTerm, setSearchTerm] = useState('');

  // VOICE — state
  const [isVoiceRecorderOpen, setIsVoiceRecorderOpen] = useState(false);
  const [isVoiceEventCreateOpen, setIsVoiceEventCreateOpen] = useState(false);
  const [voiceInitialValues, setVoiceInitialValues] = useState<EventInitialValues | undefined>(undefined);

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

  // Ngjyra e kartës tregon nivelin e rrezikut — semantic tokens
  const theme = useMemo(() => {
    const status = effectiveBriefing?.status || 'OPTIMAL';
    switch (status) {
      case 'HOLIDAY':
        return {
          bg: 'from-status-info/5 via-transparent to-transparent',
          border: 'border-status-info/30',
          icon: <PartyPopper className="h-5 w-5 text-status-info" />
        };
      case 'WEEKEND':
        return {
          bg: 'from-status-info/5 via-transparent to-transparent',
          border: 'border-status-info/30',
          icon: <Coffee className="h-5 w-5 text-status-info" />
        };
      case 'CRITICAL':
        return {
          bg: 'from-danger-start/10 via-danger-start/5 to-transparent',
          border: 'border-danger-start/40',
          icon: <ShieldAlert className="h-5 w-5 animate-pulse text-danger-start" />
        };
      case 'WARNING':
        return {
          bg: 'from-warning-start/10 via-warning-start/5 to-transparent',
          border: 'border-warning-start/40',
          icon: <AlertTriangle className="h-5 w-5 text-warning-start" />
        };
      default:
        return {
          bg: 'from-success-start/5 via-transparent to-transparent',
          border: 'border-success-start/30',
          icon: <CheckCircle2 className="h-5 w-5 text-success-start" />
        };
    }
  }, [effectiveBriefing?.status]);

  const loadData = async (silent: boolean = false) => {
    if (!silent) setIsLoading(true);
    setLoadError(null);
    try {
      const [cData, bData, eData] = await Promise.all([
        apiService.getCases(),
        apiService.getBriefing(),
        apiService.getCalendarEvents()
      ]);
      setCases(Array.isArray(cData) ? cData : []);
      setBriefing(bData);
      setFetchTimestamp(Date.now());

      if (Array.isArray(eData)) {
        const today = new Date();
        const matches = eData.filter(e => isSameDay(parseISO(e.start_date), today));
        setTodaysEvents(matches);
      }
    } catch (error) {
      console.error("Sync Failed:", error);
      if (!silent) {
        setLoadError(t('error.loadFailed', 'Dështoi ngarkimi i të dhënave. Provoni përsëri.'));
      }
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData(false);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      loadData(true);
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handler = () => loadData(true);
    window.addEventListener('calendar:event-changed', handler);
    return () => window.removeEventListener('calendar:event-changed', handler);
  }, []);

  const handleVoiceParsed = (parsed: ParsedVoiceEvent, _transcription: string) => {
    const initial: EventInitialValues = {
      title: parsed.title,
      description: parsed.description,
      event_type: parsed.event_type,
      priority: parsed.priority,
      location: parsed.location,
      category: parsed.category,
      start_date: parsed.start_date,
    };
    setVoiceInitialValues(initial);
    setIsVoiceRecorderOpen(false);
    setIsVoiceEventCreateOpen(true);
  };

  const handleCloseVoiceEventCreate = () => {
    setIsVoiceEventCreateOpen(false);
    setVoiceInitialValues(undefined);
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
        status: 'open',
        ...({ 
          client_position: clientPosition
        } as any)
      };
      await apiService.createCase(payload);
      setShowCreateModal(false);
      setNewCaseData({ title: '', clientName: '', clientEmail: '', clientPhone: '' });
      setClientPosition('PLAINTIFF');
      loadData(false);
    } catch {
      alert(t('error.generic', 'Ndodhi një gabim gjatë krijimit të lëndës.'));
    } finally {
      setIsCreating(false);
    }
  };

  const confirmDeleteCase = async () => {
    if (!caseToDeleteId) return;
    setIsDeletingCase(true);
    try {
      await apiService.deleteCase(caseToDeleteId);
      await loadData(false);
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

  const inputClasses = "w-full px-4 h-11 bg-input border border-main rounded-xl text-text-primary placeholder:text-text-muted text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/40 focus:border-primary-start transition-all";
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
        <div className="space-y-2">
          {effectiveBriefing!.risk_radar!.map((item: RiskAlert) => {
            const isCritical = item.level === 'LEVEL_1_PREKLUZIV';
            return (
              <div
                key={item.id}
                className={`p-3 rounded-xl border flex items-center justify-between gap-3 backdrop-blur-xl transition-all ${
                  isCritical
                    ? 'bg-danger-start/10 border-danger-start/25'
                    : 'bg-warning-start/10 border-warning-start/20'
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                    isCritical ? 'bg-danger-start animate-ping' : 'bg-warning-start'
                  }`} />
                  <span className={`text-xs sm:text-sm font-bold tracking-tight truncate ${
                    isCritical ? 'text-danger-start' : 'text-warning-start'
                  }`}>
                    {item.title}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-surface/60 rounded-lg border border-main shrink-0">
                  <Timer size={12} className={isCritical ? 'text-danger-start' : 'text-warning-start'} />
                  <span className="text-[11px] font-bold font-mono text-text-primary tabular-nums">
                    {formatCountdown(item.seconds_remaining)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    if (todaysEvents.length > 0) {
      const previewEvents = todaysEvents.slice(0, 3);
      return (
        <div className="space-y-2">
          {previewEvents.map(event => (
            <div key={event.id} className="p-3 rounded-xl border border-main bg-surface/60 flex items-center gap-3 shadow-sm">
              <div className="w-1.5 h-1.5 rounded-full bg-primary-start shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-bold text-text-primary truncate">{event.title}</p>
                <p className="text-[10px] text-text-muted">
                  {new Date(event.start_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          ))}
          {todaysEvents.length > 3 && (
            <button className="text-[10px] text-primary-start hover:underline mt-1 hover-lift shadow-sm" onClick={() => setIsBriefingOpen(true)}>
              + {todaysEvents.length - 3} më shumë
            </button>
          )}
        </div>
      );
    }

    return <div className="h-full"></div>;
  };

  if (loadError && !effectiveBriefing) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <div className="glass-panel border border-danger-start/30 bg-danger-start/5 rounded-2xl p-8 text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-danger-start mb-4" />
          <p className="font-bold text-text-primary mb-2">{loadError}</p>
          <button
            type="button"
            onClick={() => loadData(false)}
            className="mt-4 px-6 h-10 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider cursor-pointer"
          >
            Provo Përsëri
          </button>
        </div>
      </div>
    );
  }

  if (!effectiveBriefing && isLoading) {
    return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;
  }

  const getClientFieldLabel = () => {
    if (clientPosition === 'PLAINTIFF') return 'Klienti Juaj (Paditësi / Kallëzuesi)';
    if (clientPosition === 'DEFENDANT') return 'Klienti Juaj (I Padituri / I Denoncuari)';
    return 'Klienti Juaj (Pala A / Kërkuesi)';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-8 h-auto lg:h-[calc(100dvh-64px)] lg:overflow-hidden flex flex-col relative bg-canvas">
      <AnimatePresence mode="wait">
        {effectiveBriefing && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }} 
            animate={{ opacity: 1, y: 0 }} 
            className={`shrink-0 mb-6 rounded-[1.75rem] border overflow-hidden bg-surface transition-colors duration-500 ${theme.border}`}
          >
            <div className={`p-5 sm:p-7 bg-gradient-to-br transition-colors duration-500 ${theme.bg}`}>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
                <div className="flex items-start gap-3.5">
                  <div className={`p-2.5 rounded-xl shrink-0 border bg-surface/60 ${theme.border}`}>
                    {theme.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">
                        {t('briefing.kujdestari_title', 'KUJDESTARI VIRTUAL')}
                      </h2>
                      <div className="w-1.5 h-1.5 rounded-full bg-success-start animate-pulse shrink-0" />
                    </div>
                    <p className="font-bold text-base sm:text-xl text-text-primary tracking-tight leading-snug">
                      {getGreeting()}
                    </p>
                    <p className="text-text-secondary font-medium mt-1 text-xs sm:text-sm italic">
                      {getSubtitle()}
                    </p>
                  </div>
                </div>

                <div className="w-full md:max-w-sm">
                  {getMainContent()}
                </div>

                <div className="shrink-0 w-full md:w-auto">
                  <button 
                    type="button"
                    onClick={() => window.location.href = '/calendar'} 
                    className="h-10 w-full md:w-auto px-5 rounded-xl font-bold text-[11px] uppercase tracking-wider flex items-center justify-center gap-2 bg-primary-start hover:bg-primary-start/90 text-white shadow-md shadow-primary-start/15 hover:scale-[1.02] active:scale-95 transition-all focus:outline-none cursor-pointer"
                  >
                    <Calendar size={14} />
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
            className="w-full h-11 pl-11 pr-4 bg-surface border border-main rounded-xl text-sm text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all shadow-sm"
          />
        </div>

        <button
          type="button"
          onClick={() => setIsVoiceRecorderOpen(true)}
          className="h-11 px-4 sm:px-5 rounded-xl border border-main bg-surface hover:bg-hover text-primary-start font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shrink-0 cursor-pointer"
          title="Regjistro me zë"
        >
          <Mic size={16} strokeWidth={2.5} />
          <span className="hidden sm:inline">Regjistro</span>
        </button>

        <button 
            type="button"
            onClick={() => setShowCreateModal(true)} 
            className="h-11 px-4 sm:px-6 bg-primary-start hover:bg-primary-start/90 text-white flex items-center justify-center gap-2 rounded-xl font-bold text-xs uppercase tracking-wider shrink-0 shadow-lg shadow-primary-start/15 focus:outline-none cursor-pointer"
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

      <AnimatePresence>
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[100] p-4 overflow-y-auto custom-finance-scroll">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 15 }} 
              animate={{ opacity: 1, scale: 1, y: 0 }} 
              exit={{ opacity: 0, scale: 0.95 }} 
              className="w-full max-w-lg p-6 sm:p-8 rounded-3xl shadow-2xl border border-main bg-card text-text-primary"
            >
              <div className="flex justify-between items-center mb-6 border-b border-main pb-3">
                <h2 className="text-lg sm:text-xl font-bold tracking-tight uppercase text-text-primary">
                  {t('dashboard.createCaseTitle', 'Krijo Rast të Ri')}
                </h2>
                <button 
                  onClick={() => setShowCreateModal(false)}
                  className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors cursor-pointer"
                  aria-label="Mbyll"
                >
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleCreateCase} className="space-y-4">
                <div className="space-y-1.5">
                  <label className={labelClasses}>Pozicioni i Klientit Tuaj</label>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setClientPosition('PLAINTIFF')}
                      className={`h-11 px-2 rounded-xl text-[11px] font-black uppercase tracking-wider flex items-center justify-center gap-1.5 border transition-all cursor-pointer ${
                        clientPosition === 'PLAINTIFF'
                          ? 'bg-role-plaintiff text-white border-role-plaintiff shadow-md'
                          : 'bg-surface border-main text-text-secondary hover:bg-hover'
                      }`}
                    >
                      <Swords size={13} />
                      <span className="truncate">Paditës</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setClientPosition('DEFENDANT')}
                      className={`h-11 px-2 rounded-xl text-[11px] font-black uppercase tracking-wider flex items-center justify-center gap-1.5 border transition-all cursor-pointer ${
                        clientPosition === 'DEFENDANT'
                          ? 'bg-role-defendant text-white border-role-defendant shadow-md'
                          : 'bg-surface border-main text-text-secondary hover:bg-hover'
                      }`}
                    >
                      <Shield size={13} />
                      <span className="truncate">I Paditur</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setClientPosition('NEUTRAL')}
                      className={`h-11 px-2 rounded-xl text-[11px] font-black uppercase tracking-wider flex items-center justify-center gap-1.5 border transition-all cursor-pointer ${
                        clientPosition === 'NEUTRAL'
                          ? 'bg-role-neutral text-white border-role-neutral shadow-md'
                          : 'bg-surface border-main text-text-secondary hover:bg-hover'
                      }`}
                    >
                      <Scale size={13} />
                      <span className="truncate">Neutral</span>
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className={labelClasses}>Titulli i Lëndës</label>
                  <input 
                    required 
                    placeholder={t('dashboard.caseTitle', 'p.sh. Padi Civile / Kallëzim Penal')} 
                    value={newCaseData.title} 
                    onChange={(e) => setNewCaseData(p => ({...p, title: e.target.value}))} 
                    className={inputClasses} 
                  />
                </div>

                <div className="pt-3 border-t border-main space-y-3">
                  <div>
                    <label className={labelClasses}>{getClientFieldLabel()}</label>
                    <input 
                      required 
                      placeholder="Emri dhe Mbiemri i Klientit" 
                      value={newCaseData.clientName} 
                      onChange={(e) => setNewCaseData(p => ({...p, clientName: e.target.value}))} 
                      className={inputClasses} 
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className={labelClasses}>Email (Opsionale)</label>
                      <input 
                        placeholder="klienti@email.com" 
                        value={newCaseData.clientEmail} 
                        onChange={(e) => setNewCaseData(p => ({...p, clientEmail: e.target.value}))} 
                        className={inputClasses} 
                      />
                    </div>
                    <div>
                      <label className={labelClasses}>Telefoni (Opsionale)</label>
                      <input 
                        placeholder="+383 4X XXX XXX" 
                        value={newCaseData.clientPhone} 
                        onChange={(e) => setNewCaseData(p => ({...p, clientPhone: e.target.value}))} 
                        className={inputClasses} 
                      />
                    </div>
                  </div>
                </div>

                <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-5 border-t border-main">
                  <button 
                    type="button" 
                    onClick={() => setShowCreateModal(false)} 
                    className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:bg-hover border border-main transition-all focus:outline-none cursor-pointer"
                  >
                    {t('general.cancel', 'Anulo')}
                  </button>
                  <button 
                    type="submit" 
                    disabled={isCreating} 
                    className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-bold bg-primary-start hover:bg-primary-start/90 text-white flex items-center justify-center gap-2 focus:outline-none shadow-lg shadow-primary-start/20 cursor-pointer"
                  >
                    {isCreating ? <Loader2 className="animate-spin h-4 w-4" /> : t('general.create', 'Krijo')}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {caseToDeleteId && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[110] p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md p-6 sm:p-8 rounded-3xl shadow-2xl text-center border border-main bg-card text-text-primary"
            >
              <div className="w-16 h-16 bg-danger-start/10 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-danger-start/25">
                <Trash2 className="h-8 w-8 text-danger-start" />
              </div>

              <h2 className="text-lg sm:text-xl font-bold mb-2 uppercase tracking-tight text-text-primary">
                {t('caseDelete.confirmTitle', 'Fshij Rastin?')}
              </h2>

              <p className="text-text-secondary text-xs sm:text-sm mb-6 leading-relaxed italic font-medium">
                {t('caseDelete.confirmMessage', 'Kjo veprim është i pakthyeshëm. Të gjitha dokumentet do të fshihen.')}
              </p>

              <div className="flex gap-3 justify-center">
                <button
                  type="button"
                  onClick={() => setCaseToDeleteId(null)}
                  className="w-full h-11 rounded-xl text-sm font-semibold text-text-secondary hover:bg-hover border border-main transition-all focus:outline-none cursor-pointer"
                >
                  {t('general.cancel', 'Anulo')}
                </button>
                <button
                  type="button"
                  onClick={confirmDeleteCase}
                  disabled={isDeletingCase}
                  className="w-full h-11 rounded-xl bg-danger-start hover:bg-danger-start/90 text-white font-black flex items-center justify-center gap-2 active:scale-95 text-xs uppercase tracking-wider disabled:opacity-50 transition-all focus:outline-none shadow-lg shadow-danger-start/30 cursor-pointer"
                >
                  {isDeletingCase ? <Loader2 className="animate-spin h-4 w-4" /> : t('general.delete', 'Fshij')}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <DayEventsModal isOpen={isBriefingOpen} onClose={() => setIsBriefingOpen(false)} date={new Date()} events={todaysEvents} t={t} onAddEvent={() => { setIsBriefingOpen(false); window.location.href = '/calendar'; }} />

      <VoiceEventRecorder
        isOpen={isVoiceRecorderOpen}
        onClose={() => setIsVoiceRecorderOpen(false)}
        onParsed={handleVoiceParsed}
      />

      {isVoiceEventCreateOpen && (
        <CreateEventModal
          cases={cases}
          existingEvents={todaysEvents}
          onClose={handleCloseVoiceEventCreate}
          onCreate={() => loadData(false)}
          initialValues={voiceInitialValues}
          prefillSource="voice"
        />
      )}
    </div>
  );
};

export default DashboardPage;