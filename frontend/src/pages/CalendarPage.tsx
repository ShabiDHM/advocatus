// FILE: src/pages/CalendarPage.tsx
// PHOENIX PROTOCOL - CALENDAR PAGE V4.0 (COMPACT MOBILE CONTROLS + MONTH DEFAULT)
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { CalendarEvent, Case } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { format, addMonths, subMonths, isSameDay, parseISO } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { AlertCircle, Plus, ChevronLeft, ChevronRight, Search, History, Loader2, Menu, X, Mic } from 'lucide-react';

import DayEventsModal from '../components/DayEventsModal';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';
import { localeMap } from '../utils/calendarHelpers';
import { EventDetailModal } from '../components/calendar/EventDetailModal';
import { CreateEventModal, EventInitialValues } from '../components/calendar/CreateEventModal';
import { VoiceEventRecorder, ParsedVoiceEvent } from '../components/calendar/VoiceEventRecorder';
import { CalendarSidebar } from '../components/calendar/CalendarSidebar';
import { CalendarListView } from '../components/calendar/CalendarListView';
import { CalendarMonthView } from '../components/calendar/CalendarMonthView';

type ViewMode = 'month' | 'list';

const UPCOMING_EVENT_TYPES = ['DEADLINE', 'HEARING', 'COURT_DATE', 'FILING'];
const INACTIVE_STATUSES = ['CANCELLED', 'COMPLETED', 'RESOLVED'];

const CalendarPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('ALL');
  const [showFacts, setShowFacts] = useState(false);
  const [isDayModalOpen, setIsDayModalOpen] = useState(false);
  const [selectedDateForModal, setSelectedDateForModal] = useState<Date | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const currentLocale = localeMap[i18n.language] || enUS;

  // VOICE — state
  const [isVoiceRecorderOpen, setIsVoiceRecorderOpen] = useState(false);
  const [voiceInitialValues, setVoiceInitialValues] = useState<EventInitialValues | undefined>(undefined);
  const [voicePrefillSource, setVoicePrefillSource] = useState<'voice' | 'manual' | undefined>(undefined);

  const lastEventsJsonRef = useRef<string>('');

  useLockBodyScroll(isSidebarOpen);

  const loadData = useCallback(async (isInitial: boolean = false) => {
    try {
      if (isInitial) {
        setLoading(true);
        setError('');
      }
      const [eventsData, casesData] = await Promise.all([
        apiService.getCalendarEvents(),
        apiService.getCases()
      ]);

      const newJson = JSON.stringify(eventsData);
      if (newJson !== lastEventsJsonRef.current) {
        lastEventsJsonRef.current = newJson;
        setEvents(eventsData);
      }
      setCases(casesData);
    } catch {
      if (isInitial) {
        setError(t('calendar.loadFailure') as string);
      }
    } finally {
      if (isInitial) {
        setLoading(false);
      }
    }
  }, [t]);

  useEffect(() => {
    loadData(true);
  }, [loadData]);

  useEffect(() => {
    const interval = setInterval(() => {
      loadData(false);
    }, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentDate(direction === 'prev' ? subMonths(currentDate, 1) : addMonths(currentDate, 1));
  };

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const matchesSearch = `${event.title} ${event.description || ''}`.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = filterType === 'ALL' || event.event_type === filterType;
      const matchesCategory = showFacts || event.category === 'AGENDA';
      return matchesSearch && matchesType && matchesCategory;
    });
  }, [events, searchTerm, filterType, showFacts]);

  const upcomingAlerts = useMemo(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);

    return events
      .filter((event) => {
        if (event.category !== 'AGENDA') return false;
        if (!UPCOMING_EVENT_TYPES.includes(event.event_type)) return false;
        const status = (event as any).status;
        if (status && INACTIVE_STATUSES.includes(status)) return false;
        const eventDate = new Date(event.start_date);
        if (eventDate.getTime() < now.getTime()) return false;
        return true;
      })
      .sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
      .slice(0, 10);
  }, [events]);

  const handleVoiceParsed = useCallback((parsed: ParsedVoiceEvent, _transcription: string) => {
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
    setVoicePrefillSource('voice');
    setIsVoiceRecorderOpen(false);
    setIsCreateModalOpen(true);
  }, []);

  const handleOpenCreateManually = () => {
    setVoiceInitialValues(undefined);
    setVoicePrefillSource(undefined);
    setIsCreateModalOpen(true);
  };

  const handleCloseCreateModal = () => {
    setIsCreateModalOpen(false);
    setVoiceInitialValues(undefined);
    setVoicePrefillSource(undefined);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100dvh-64px)] bg-canvas">
        <Loader2 className="animate-spin text-primary-start w-10 h-10" />
      </div>
    );
  }

  const sidebarContent = (
    <CalendarSidebar
      upcomingAlerts={upcomingAlerts}
      filterType={filterType}
      onFilterTypeChange={setFilterType}
      onSelectEvent={setSelectedEvent}
      currentLocale={currentLocale}
      t={t}
    />
  );

  return (
    <div className="h-auto lg:h-[calc(100dvh-64px)] overflow-y-auto lg:overflow-hidden bg-canvas flex flex-col font-sans selection:bg-primary-start/30">
      <div id="react-datepicker-portal"></div>
      <div className="flex-1 flex flex-col max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 gap-4 sm:gap-6 min-h-0 bg-canvas">
        {error && (
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="shrink-0 bg-danger-start/10 border border-danger-start/30 rounded-2xl p-4 flex items-center gap-4">
            <AlertCircle className="h-5 w-5 text-danger-start" />
            <span className="text-danger-start text-sm font-bold">{error}</span>
          </motion.div>
        )}

        {/* RRESHTI 1: Navigimi i Datës + Menu */}
        <div className="shrink-0 flex items-center justify-between gap-4 w-full h-auto sm:h-11">
          <div className="flex items-center gap-4">
            <div className="glass-panel flex items-center p-1 shrink-0 border border-main bg-surface h-11">
              <button type="button" onClick={() => navigateMonth('prev')} className="flex items-center justify-center w-9 h-9 hover:bg-hover rounded-xl transition-all focus:outline-none">
                <ChevronLeft size={18} className="text-text-secondary" />
              </button>
              <button type="button" onClick={() => setCurrentDate(new Date())} className="px-4 sm:px-5 text-[11px] font-bold uppercase tracking-widest text-text-secondary hover:text-text-primary transition-colors focus:outline-none">
                {t('calendar.today')}
              </button>
              <button type="button" onClick={() => navigateMonth('next')} className="flex items-center justify-center w-9 h-9 hover:bg-hover rounded-xl transition-all focus:outline-none">
                <ChevronRight size={18} className="text-text-secondary" />
              </button>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-xl font-bold text-text-primary tracking-tight capitalize select-none">
                {format(currentDate, 'LLLL yyyy', { locale: currentLocale })}
              </h1>
            </div>
          </div>
          <button type="button" onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="xl:hidden flex items-center justify-center w-11 h-11 text-text-secondary hover:text-text-primary focus:outline-none shrink-0">
            <Menu size={20} />
          </button>
        </div>

        {/* RRESHTI 2: Kontrollet e Kompaktuara [🎤] [Afatet] [Muaji|Lista] [+] */}
        <div className="shrink-0 flex items-center gap-1.5 sm:gap-2 w-full h-11">
          {/* Voice/Mic */}
          <button
            type="button"
            onClick={() => setIsVoiceRecorderOpen(true)}
            className="h-11 w-11 sm:w-auto sm:px-4 rounded-xl border border-main bg-surface hover:bg-hover text-primary-start font-bold text-xs uppercase tracking-widest flex items-center justify-center gap-2 transition-all focus:outline-none shrink-0 cursor-pointer"
            title="Regjistro me zë"
            aria-label="Regjistro me zë"
          >
            <Mic size={16} strokeWidth={2.5} />
            <span className="hidden sm:inline">Regjistro</span>
          </button>

          {/* Afatet */}
          <button
            type="button"
            onClick={() => setShowFacts(!showFacts)}
            className={`h-11 px-2.5 sm:px-5 flex-1 sm:flex-none rounded-xl text-[10px] sm:text-xs font-bold uppercase tracking-wider transition-all focus:outline-none flex items-center justify-center gap-1.5 cursor-pointer ${
              showFacts
                ? 'bg-primary-start text-white border-primary-start shadow-lg shadow-primary-start/15 border'
                : 'border border-main text-text-secondary hover:bg-hover bg-surface'
            }`}
            title={showFacts ? 'Shfaq vetëm afatet' : 'Shfaq gjithçka'}
          >
            <History size={13} className="shrink-0" />
            <span className="truncate">{showFacts ? 'Gjithçka' : 'Afatet'}</span>
          </button>

          {/* Muaji | Lista */}
          <div className="flex p-0.5 rounded-xl border border-main bg-surface h-11 items-center shrink-0">
            <button
              type="button"
              onClick={() => setViewMode('month')}
              className={`px-2.5 sm:px-5 h-10 rounded-lg text-[10px] sm:text-xs font-bold uppercase tracking-wider transition-all focus:outline-none cursor-pointer ${
                viewMode === 'month' ? 'bg-primary-start text-white shadow-md' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              Muaji
            </button>
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={`px-2.5 sm:px-5 h-10 rounded-lg text-[10px] sm:text-xs font-bold uppercase tracking-wider transition-all focus:outline-none cursor-pointer ${
                viewMode === 'list' ? 'bg-primary-start text-white shadow-md' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              Lista
            </button>
          </div>

          {/* Plus / Ngjarje e Re */}
          <button
            type="button"
            onClick={handleOpenCreateManually}
            className="h-11 w-11 sm:w-auto sm:px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-primary-start/15 focus:outline-none shrink-0 cursor-pointer"
            title={t('calendar.newEvent') as string}
            aria-label={t('calendar.newEvent') as string}
          >
            <Plus size={18} strokeWidth={3} />
            <span className="hidden sm:inline">{t('calendar.newEvent')}</span>
          </button>
        </div>

        {/* RRESHTI 3: Kërkimi */}
        <div className="shrink-0 flex flex-col sm:flex-row gap-4 items-center h-auto sm:h-11">
          <div className="relative flex-1 h-11 w-full">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
            <input
              type="text"
              placeholder={t('calendar.searchPlaceholder') as string}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-11 pl-12 pr-6 rounded-xl text-sm font-semibold border border-main bg-surface text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all"
            />
          </div>
        </div>

        {/* KALENDARI */}
        <div className="flex-1 grid grid-cols-1 xl:grid-cols-4 gap-8 min-h-0 relative bg-canvas">
          <div className="xl:col-span-3 flex flex-col min-h-0 bg-canvas">
            {viewMode === 'list' ? (
              <CalendarListView filteredEvents={filteredEvents} onSelectEvent={setSelectedEvent} currentLocale={currentLocale} t={t} />
            ) : (
              <CalendarMonthView
                currentDate={currentDate}
                filteredEvents={filteredEvents}
                onSelectEvent={setSelectedEvent}
                onSelectDateForModal={(date) => {
                  setSelectedDateForModal(date);
                  setIsDayModalOpen(true);
                }}
                currentLocale={currentLocale}
                t={t}
              />
            )}
          </div>

          <div className="hidden xl:flex xl:col-span-1 flex-col gap-8 min-h-0 bg-canvas">{sidebarContent}</div>
        </div>
      </div>

      <AnimatePresence>
        {isSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 z-[1000] xl:hidden backdrop-blur-xs"
              onClick={() => setIsSidebarOpen(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'tween', duration: 0.3 }}
              className="fixed right-0 top-0 h-full w-80 max-w-[85vw] bg-canvas border-l border-main shadow-2xl z-[1001] flex flex-col p-6 gap-6 overflow-y-auto custom-finance-scroll"
            >
              <div className="flex justify-between items-center mb-2 shrink-0">
                <h3 className="text-lg font-black text-text-primary">Filtrat & Njoftimet</h3>
                <button type="button" onClick={() => setIsSidebarOpen(false)} className="p-2 text-text-secondary hover:text-text-primary focus:outline-none">
                  <X size={20} />
                </button>
              </div>
              {sidebarContent}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {selectedEvent && <EventDetailModal event={selectedEvent} onClose={() => setSelectedEvent(null)} onUpdate={() => loadData(false)} />}

      {isCreateModalOpen && (
        <CreateEventModal
          cases={cases}
          existingEvents={events}
          onClose={handleCloseCreateModal}
          onCreate={() => loadData(false)}
          initialValues={voiceInitialValues}
          prefillSource={voicePrefillSource}
        />
      )}

      <VoiceEventRecorder
        isOpen={isVoiceRecorderOpen}
        onClose={() => setIsVoiceRecorderOpen(false)}
        onParsed={handleVoiceParsed}
      />

      <DayEventsModal
        isOpen={isDayModalOpen}
        onClose={() => setIsDayModalOpen(false)}
        date={selectedDateForModal}
        events={filteredEvents.filter((e) => selectedDateForModal && isSameDay(parseISO(e.start_date), selectedDateForModal))}
        t={t}
        onAddEvent={() => {
          setIsDayModalOpen(false);
          handleOpenCreateManually();
        }}
      />
    </div>
  );
};

export default CalendarPage;