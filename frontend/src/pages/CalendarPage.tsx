// FILE: src/pages/CalendarPage.tsx
// PHOENIX PROTOCOL - CLEANUP & RESTORATION
// 1. FIX: Removed unused imports (Briefcase, Filter) to resolve TS6133.
// 2. FIX: Restored the 'Priority' dropdown in the toolbar to utilize 'setFilterPriority'.
// 3. STATUS: Clean build with full filtering capabilities.

import React, { useState, useEffect } from 'react';
import { CalendarEvent, Case, CalendarEventCreateRequest } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  format, 
  addMonths, 
  subMonths, 
  startOfMonth, 
  getDay, 
  getDaysInMonth, 
  isSameDay, 
  isToday as isTodayFns, 
  parseISO, 
  startOfWeek, 
  addDays,
  Locale 
} from 'date-fns';
import { sq, enUS } from 'date-fns/locale'; 
import {
  Calendar as CalendarIcon, Clock, MapPin, Users, AlertCircle, Plus, ChevronLeft, ChevronRight,
  Search, FileText, Gavel, AlertTriangle, XCircle, Bell, ChevronDown, Scale, MessageSquare
} from 'lucide-react';

import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import '../styles/DatePicker.css';

const DatePicker = (ReactDatePicker as any).default;

const localeMap: { [key: string]: Locale } = { 
  sq: sq, 
  al: sq, 
  en: enUS
};

interface EventDetailModalProps { event: CalendarEvent; onClose: () => void; onUpdate: () => void; }
interface CreateEventModalProps { cases: Case[]; onClose: () => void; onCreate: () => void; }
type ViewMode = 'month' | 'list';

// --- VISUAL HELPERS ---
const getEventStyle = (type: string) => {
    switch (type) {
      case 'DEADLINE': return { border: 'border-red-500', bg: 'bg-red-500/10', text: 'text-red-400', icon: <AlertTriangle size={12} /> };
      case 'HEARING': return { border: 'border-purple-500', bg: 'bg-purple-500/10', text: 'text-purple-400', icon: <Gavel size={12} /> };
      case 'MEETING': return { border: 'border-blue-500', bg: 'bg-blue-500/10', text: 'text-blue-400', icon: <Users size={12} /> };
      case 'FILING': return { border: 'border-yellow-500', bg: 'bg-yellow-500/10', text: 'text-yellow-400', icon: <FileText size={12} /> };
      case 'COURT_DATE': return { border: 'border-orange-500', bg: 'bg-orange-500/10', text: 'text-orange-400', icon: <Scale size={12} /> };
      case 'CONSULTATION': return { border: 'border-emerald-500', bg: 'bg-emerald-500/10', text: 'text-emerald-400', icon: <MessageSquare size={12} /> };
      default: return { border: 'border-gray-500', bg: 'bg-gray-500/10', text: 'text-gray-400', icon: <CalendarIcon size={12} /> };
    }
};

const getEventId = (event: CalendarEvent): string => {
    const eventWithAny = event as any;
    return event.id || eventWithAny._id || '';
};

// --- MAIN COMPONENT ---
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
  const [filterPriority, setFilterPriority] = useState<string>('ALL');
  
  const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);

  const currentLocale = localeMap[i18n.language] || enUS;

  useEffect(() => { 
    loadData(); 
  }, []);

  const loadData = async () => {
    try {
      setLoading(true); 
      setError('');
      const [eventsData, casesData] = await Promise.all([
        apiService.getCalendarEvents(), 
        apiService.getCases()
      ]);
      setEvents(eventsData);
      setCases(casesData);
    } catch (error: any) {
      setError(error.response?.data?.message || error.message || t('calendar.loadFailure'));
    } finally { 
      setLoading(false); 
    }
  };

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentDate(direction === 'prev' ? subMonths(currentDate, 1) : addMonths(currentDate, 1));
  };

  const filteredEvents = events.filter(event => {
    const searchContent = `${event.title} ${event.description || ''} ${event.location || ''}`.toLowerCase();
    return searchContent.includes(searchTerm.toLowerCase()) && 
           (filterType === 'ALL' || event.event_type === filterType) && 
           (filterPriority === 'ALL' || event.priority === filterPriority);
  });

  const upcomingAlerts = events
    .filter(event => {
        if (!['DEADLINE', 'HEARING', 'COURT_DATE'].includes(event.event_type)) return false;
        const eventDate = parseISO(event.start_date);
        const today = new Date();
        today.setHours(0, 0, 0, 0); 
        const sevenDaysFromNow = new Date(today);
        sevenDaysFromNow.setDate(today.getDate() + 7);
        sevenDaysFromNow.setHours(23, 59, 59, 999); 
        return eventDate >= today && eventDate <= sevenDaysFromNow;
    })
    .sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
    .slice(0, 5);

  // --- LIST VIEW ---
  const renderListView = () => (
    <div className="bg-background-light/20 backdrop-blur-md border border-white/10 rounded-3xl shadow-xl overflow-hidden">
        {filteredEvents.length === 0 ? (
            <div className="p-8 text-center text-text-secondary">
                {t('calendar.noEventsFound', 'Nuk u gjetën ngjarje.')}
            </div>
        ) : (
            <div className="divide-y divide-white/5">
                {filteredEvents
                    .sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
                    .map(event => {
                        const style = getEventStyle(event.event_type);
                        return (
                            <div key={getEventId(event)} onClick={() => setSelectedEvent(event)} className="p-4 hover:bg-white/5 cursor-pointer transition-colors flex items-center justify-between group">
                                <div className="flex items-start space-x-4">
                                    <div className="flex-shrink-0 mt-1 text-center min-w-[50px]">
                                        <div className="text-xs text-text-secondary uppercase">{format(parseISO(event.start_date), 'MMM', { locale: currentLocale })}</div>
                                        <div className={`text-xl font-bold ${style.text}`}>{format(parseISO(event.start_date), 'dd')}</div>
                                    </div>
                                    <div>
                                        <h4 className="text-base font-medium text-white group-hover:text-primary-start transition-colors">{event.title}</h4>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className={`text-[10px] px-2 py-0.5 rounded border ${style.border} ${style.bg} ${style.text} flex items-center gap-1`}>
                                                {style.icon} {t(`calendar.types.${event.event_type}`)}
                                            </span>
                                            <span className="text-xs text-text-secondary truncate max-w-[200px]">{event.description}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
            </div>
        )}
    </div>
  );

  // --- MONTH VIEW ---
  const renderMonthView = () => {
    const monthStart = startOfMonth(currentDate);
    const daysInMonth = getDaysInMonth(currentDate);
    const weekStartsOn = currentLocale?.options?.weekStartsOn ?? 1; 
    const firstDayOfMonth = getDay(monthStart);
    const startingDayIndex = (firstDayOfMonth - weekStartsOn + 7) % 7;
    const cellClass = "min-h-[100px] sm:min-h-[130px] border-r border-b border-white/5 relative group transition-colors hover:bg-white/5";

    const days = Array.from({ length: startingDayIndex }, (_, i) => 
      <div key={`empty-${i}`} className={`${cellClass} bg-black/20`} />
    );

    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), day);
      const dayEvents = filteredEvents.filter(event => isSameDay(parseISO(event.start_date), date));
      const today = isTodayFns(date);
      
      days.push(
        <div key={day} className={`${cellClass} p-1.5 ${today ? 'bg-primary-start/10' : ''}`}>
          <div className={`text-xs sm:text-sm font-medium mb-1.5 flex justify-between items-center ${today ? 'text-primary-start' : 'text-gray-400'}`}>
            <span className={`w-6 h-6 flex items-center justify-center rounded-full ${today ? 'bg-primary-start text-white shadow-lg shadow-primary-start/40' : ''}`}>
                {day}
            </span>
            {today && <span className="hidden sm:inline text-[10px] font-bold uppercase tracking-wider mr-1">Sot</span>}
          </div>

          <div className="space-y-1 overflow-y-auto max-h-[90px] custom-scrollbar">
            {dayEvents.slice(0, 4).map(event => {
              const style = getEventStyle(event.event_type);
              const eventId = getEventId(event);
              
              return (
                <div key={eventId} className="relative">
                    <button 
                        onClick={() => setSelectedEvent(event)}
                        onMouseEnter={() => setHoveredEventId(eventId)}
                        onMouseLeave={() => setHoveredEventId(null)}
                        className={`w-full text-left px-1.5 py-0.5 rounded-r-md border-l-[3px] text-[10px] truncate ${style.border} ${style.bg} ${style.text} hover:brightness-125 transition-all`}
                    >
                        <div className="flex items-center gap-1.5">
                            {style.icon}
                            <span className="truncate font-medium">{event.title}</span>
                        </div>
                    </button>

                    <AnimatePresence>
                        {hoveredEventId === eventId && (
                            <motion.div 
                                initial={{ opacity: 0, y: 5, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                className="absolute left-0 top-full mt-1 z-50 w-64 bg-gray-900 border border-white/20 rounded-xl p-3 shadow-2xl pointer-events-none"
                            >
                                <div className={`text-xs font-bold uppercase mb-1 ${style.text} flex items-center gap-1.5`}>
                                    {style.icon} {t(`calendar.types.${event.event_type}`)}
                                </div>
                                <div className="text-white font-semibold text-sm mb-1">{event.title}</div>
                                {event.description && <div className="text-gray-400 text-xs mb-2 line-clamp-2">{event.description}</div>}
                                <div className="pt-2 border-t border-white/10 text-gray-500 text-[10px] flex justify-between">
                                    <span>{format(parseISO(event.start_date), 'HH:mm')}</span>
                                    <span className={`uppercase font-bold ${event.priority === 'CRITICAL' ? 'text-red-500' : 'text-gray-500'}`}>{event.priority}</span>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
              );
            })}
            {dayEvents.length > 4 && (
              <div className="text-[10px] text-text-secondary px-1 text-center font-medium opacity-60">
                +{dayEvents.length - 4} Të tjera
              </div>
            )}
          </div>
        </div>
      );
    }
    
    const totalCells = Math.ceil(days.length / 7) * 7;
    while(days.length < totalCells) days.push(<div key={`empty-end-${days.length}`} className={`${cellClass} bg-black/20`} />);

    const weekStarts = startOfWeek(new Date(), { weekStartsOn });
    const weekDays = Array.from({ length: 7 }, (_, i) => format(addDays(weekStarts, i), 'EEEEEE', { locale: currentLocale }));

    return (
        <div className="bg-background-light/20 backdrop-blur-md border border-white/10 rounded-3xl overflow-hidden shadow-2xl">
            <div className="grid grid-cols-7 bg-white/5 border-b border-white/10">
                {weekDays.map(day => <div key={day} className="py-3 text-center text-xs font-bold text-gray-400 uppercase tracking-wider">{day}</div>)}
            </div>
            <div className="grid grid-cols-7 border-l border-t border-white/5">{days}</div>
        </div>
    );
  };

  const monthName = format(currentDate, 'LLLL yyyy', { locale: currentLocale });
  if (loading) return <div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;

  return (
    <div className="min-h-screen bg-background-dark font-sans text-gray-100">
        <div id="react-datepicker-portal"></div>
        
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-6 mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <CalendarIcon className="text-primary-start h-8 w-8" />
                        <span className="capitalize">{monthName}</span>
                    </h1>
                    <p className="text-gray-400 mt-1 ml-1">{t('calendar.pageSubtitle', 'Planifikimi dhe Afatet Ligjore')}</p>
                </div>

                <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto">
                    <div className="flex items-center bg-background-light/30 border border-white/10 rounded-xl p-1">
                        <button onClick={() => navigateMonth('prev')} className="p-2 hover:bg-white/10 rounded-lg transition-colors"><ChevronLeft size={20} /></button>
                        <button onClick={() => setCurrentDate(new Date())} className="px-4 text-sm font-medium hover:text-white transition-colors">{t('calendar.today')}</button>
                        <button onClick={() => navigateMonth('next')} className="p-2 hover:bg-white/10 rounded-lg transition-colors"><ChevronRight size={20} /></button>
                    </div>

                    <button onClick={() => setIsCreateModalOpen(true)} className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white rounded-xl font-bold shadow-lg shadow-primary-start/20 transition-all">
                        <Plus size={18} /> <span className="hidden sm:inline">{t('calendar.newEvent')}</span>
                    </button>
                </div>
            </div>

            {error && <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-4 mb-6 flex items-center space-x-3"><AlertCircle className="h-5 w-5 text-red-400" /><span className="text-red-200 text-sm">{error}</span></div>}

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
                <div className="xl:col-span-3 space-y-6">
                    {/* Toolbar */}
                    <div className="flex flex-col sm:flex-row gap-3">
                        <div className="relative flex-grow">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                            <input 
                                type="text" 
                                placeholder={t('calendar.searchPlaceholder')} 
                                value={searchTerm} 
                                onChange={(e) => setSearchTerm(e.target.value)} 
                                className="w-full pl-10 pr-4 py-2.5 bg-background-light/20 border border-white/10 rounded-xl text-sm focus:outline-none focus:border-primary-start/50 transition-all" 
                            />
                        </div>
                        <div className="flex gap-2">
                            {/* Type Filter */}
                            <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="px-3 py-2.5 bg-background-light/20 border border-white/10 rounded-xl text-sm focus:outline-none focus:border-primary-start/50">
                                <option value="ALL">{t('calendar.allTypes')}</option>
                                {Object.keys(t('calendar.types', { returnObjects: true })).map(key => <option key={key} value={key}>{t(`calendar.types.${key}`)}</option>)}
                            </select>
                            
                            {/* Priority Filter - Restored */}
                            <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)} className="px-3 py-2.5 bg-background-light/20 border border-white/10 rounded-xl text-sm focus:outline-none focus:border-primary-start/50">
                                <option value="ALL">{t('calendar.allPriorities')}</option>
                                {Object.keys(t('calendar.priorities', { returnObjects: true })).map(key => <option key={key} value={key}>{t(`calendar.priorities.${key}`)}</option>)}
                            </select>

                            <div className="flex bg-background-light/20 p-1 rounded-xl border border-white/10">
                                <button onClick={() => setViewMode('month')} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${viewMode === 'month' ? 'bg-white text-black shadow' : 'text-gray-400 hover:text-white'}`}>{t('calendar.month')}</button>
                                <button onClick={() => setViewMode('list')} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${viewMode === 'list' ? 'bg-white text-black shadow' : 'text-gray-400 hover:text-white'}`}>{t('calendar.list')}</button>
                            </div>
                        </div>
                    </div>

                    {viewMode === 'month' ? renderMonthView() : renderListView()}
                </div>

                <div className="xl:col-span-1 space-y-6">
                    <div className="bg-background-light/20 backdrop-blur-md border border-white/10 rounded-3xl p-6 shadow-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none"><Bell size={64} /></div>
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <Bell className="text-yellow-400" size={18} />
                            Afatet e Ardhshme
                        </h3>
                        
                        <div className="space-y-3">
                            {upcomingAlerts.length === 0 ? (
                                <p className="text-gray-500 text-sm text-center py-4">{t('calendar.noUpcomingEvents')}</p>
                            ) : (
                                upcomingAlerts.map(ev => {
                                    const style = getEventStyle(ev.event_type);
                                    return (
                                        <button key={getEventId(ev)} onClick={() => setSelectedEvent(ev)} className="w-full flex gap-3 items-start group text-left">
                                            <div className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${style.bg.replace('/10', '')}`} />
                                            <div className="min-w-0">
                                                <h4 className="text-sm font-medium text-gray-200 group-hover:text-primary-start transition-colors truncate">{ev.title}</h4>
                                                <p className="text-xs text-gray-500 mt-0.5">
                                                    {format(parseISO(ev.start_date), 'dd MMM')} • <span className={style.text}>{t(`calendar.types.${ev.event_type}`)}</span>
                                                </p>
                                            </div>
                                        </button>
                                    )
                                })
                            )}
                        </div>
                    </div>

                    <div className="bg-background-light/20 backdrop-blur-md border border-white/10 rounded-3xl p-6 shadow-xl">
                        <h3 className="text-lg font-bold text-white mb-4">{t('calendar.eventTypes')}</h3>
                        <div className="space-y-2">
                            {Object.keys(t('calendar.types', { returnObjects: true })).map((key) => {
                                const style = getEventStyle(key);
                                return (
                                    <div key={key} className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer" onClick={() => setFilterType(filterType === key ? 'ALL' : key)}>
                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${style.border} ${style.bg} ${style.text}`}>
                                            {style.icon}
                                        </div>
                                        <span className={`text-sm ${filterType === key ? 'text-white font-bold' : 'text-gray-400'}`}>{t(`calendar.types.${key}`)}</span>
                                        {filterType === key && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-white animate-pulse" />}
                                    </div>
                                )
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {selectedEvent && <EventDetailModal event={selectedEvent} onClose={() => setSelectedEvent(null)} onUpdate={loadData} />}
        {isCreateModalOpen && <CreateEventModal cases={cases} onClose={() => setIsCreateModalOpen(false)} onCreate={loadData} />}
    </div>
  );
};

const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose, onUpdate }) => {
    const { t, i18n } = useTranslation();
    const currentLocale = localeMap[i18n.language] || enUS; 
    const [isDeleting, setIsDeleting] = useState(false);

    const isMidnight = (dateString: string) => {
        const d = parseISO(dateString);
        return d.getHours() === 0 && d.getMinutes() === 0;
    };

    const formatEventDate = (dateString: string) => {
      const date = parseISO(dateString);
      const formatStr = (event.is_all_day || isMidnight(dateString)) ? 'dd MMMM yyyy' : 'dd MMMM yyyy, HH:mm';
      return format(date, formatStr, { locale: currentLocale });
    };

    const handleDelete = async () => { 
      if (!window.confirm(t('calendar.detailModal.deleteConfirm'))) return; 
      const eventId = getEventId(event);
      if (!eventId) return;
      setIsDeleting(true); 
      try { await apiService.deleteCalendarEvent(eventId); onUpdate(); onClose(); } 
      catch (error: any) { alert(error.response?.data?.message || t('calendar.detailModal.deleteFailed')); } 
      finally { setIsDeleting(false); } 
    };

    const style = getEventStyle(event.event_type);

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-[100]">
            <div className="bg-[#1f2937] border border-white/10 rounded-3xl p-8 w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl relative">
                
                <div className="flex items-start justify-between mb-8">
                  <div className="flex items-start space-x-5">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center border ${style.border} ${style.bg} ${style.text}`}>
                        {React.cloneElement(style.icon as React.ReactElement, { size: 28 })}
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-white mb-2">{event.title}</h2>
                      <div className="flex flex-wrap gap-2">
                        <span className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${style.bg} ${style.text} border ${style.border} border-opacity-30`}>
                            {t(`calendar.types.${event.event_type}`)}
                        </span>
                        <span className={`text-xs px-2.5 py-1 rounded-full border border-white/20 text-gray-300`}>
                            {t(`calendar.priorities.${event.priority}`)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors"><XCircle className="h-6 w-6 text-gray-400 hover:text-white" /></button>
                </div>

                <div className="space-y-6">
                  {event.description && (
                      <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                          <h3 className="text-xs font-bold text-gray-500 uppercase mb-2">{t('calendar.detailModal.description')}</h3>
                          <p className="text-gray-200 text-sm leading-relaxed">{event.description}</p>
                      </div>
                  )}
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div><h3 className="text-xs font-bold text-gray-500 uppercase mb-1">{t('calendar.detailModal.startDate')}</h3><div className="flex items-center text-white"><Clock className="h-4 w-4 mr-2 text-primary-start" />{formatEventDate(event.start_date)}</div></div>
                    {event.end_date && event.end_date !== event.start_date && <div><h3 className="text-xs font-bold text-gray-500 uppercase mb-1">{t('calendar.detailModal.endDate')}</h3><div className="flex items-center text-white"><Clock className="h-4 w-4 mr-2 text-primary-start" />{formatEventDate(event.end_date)}</div></div>}
                  </div>
                  
                  {event.location && <div><h3 className="text-xs font-bold text-gray-500 uppercase mb-1">{t('calendar.detailModal.location')}</h3><div className="flex items-center text-white"><MapPin className="h-4 w-4 mr-2 text-primary-start" />{event.location}</div></div>}
                  
                  {event.attendees && event.attendees.length > 0 && (
                      <div>
                          <h3 className="text-xs font-bold text-gray-500 uppercase mb-1">{t('calendar.detailModal.attendees')}</h3>
                          <div className="flex flex-wrap gap-2">
                              {event.attendees.map((att, i) => (
                                  <span key={i} className="flex items-center text-xs bg-white/5 px-2 py-1 rounded border border-white/10 text-gray-300">
                                      <Users className="h-3 w-3 mr-1.5" />{att}
                                  </span>
                              ))}
                          </div>
                      </div>
                  )}
                  
                  {event.notes && (
                      <div>
                          <h3 className="text-xs font-bold text-gray-500 uppercase mb-2">{t('calendar.detailModal.notes')}</h3>
                          <p className="text-gray-400 italic text-sm">{event.notes}</p>
                      </div>
                  )}
                </div>

                <div className="flex space-x-4 mt-8 pt-6 border-t border-white/10">
                  <button onClick={onClose} className="flex-1 px-4 py-3 border border-white/10 rounded-xl text-gray-300 hover:bg-white/5 transition font-medium">{t('calendar.detailModal.close')}</button>
                  <button onClick={handleDelete} disabled={isDeleting} className="flex-1 px-4 py-3 bg-red-600/10 hover:bg-red-600/20 text-red-500 border border-red-600/30 rounded-xl transition font-medium disabled:opacity-50">{isDeleting ? t('calendar.detailModal.deleting') : t('calendar.detailModal.delete')}</button>
                </div>
            </div>
        </div>
    );
};

const CreateEventModal: React.FC<CreateEventModalProps> = ({ cases, onClose, onCreate }) => {
  const { t, i18n } = useTranslation();
  const currentLocale = localeMap[i18n.language] || enUS; 
  const [isCreating, setIsCreating] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [eventDate, setEventDate] = useState<Date | null>(null);

  const [formData, setFormData] = useState<Omit<CalendarEventCreateRequest, 'attendees' | 'start_date' | 'end_date'> & { attendees: string }>({
    case_id: '', title: '', description: '', event_type: 'MEETING', location: '', attendees: '', 
    is_all_day: true, 
    priority: 'MEDIUM', notes: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventDate) { alert(t('calendar.createModal.dateTimePlaceholder')); return; }
    setIsCreating(true);
    try {
      const payload: CalendarEventCreateRequest = {
        ...formData,
        start_date: eventDate.toISOString(),
        end_date: eventDate.toISOString(),
        attendees: formData.attendees ? formData.attendees.split(',').map(a => a.trim()) : [],
      };
      await apiService.createCalendarEvent(payload);
      onCreate(); onClose();
    } catch (error: any) { alert(error.response?.data?.message || t('calendar.createModal.createFailed')); } 
    finally { setIsCreating(false); }
  };

  const formElementClasses = "block w-full px-4 py-2.5 border border-white/10 rounded-xl bg-black/40 text-white placeholder:text-gray-500 focus:outline-none focus:border-primary-start/50 transition-all";

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-[100]">
      <div className="bg-[#1f2937] border border-white/10 rounded-3xl p-8 w-full max-w-lg max-h-[90vh] flex flex-col shadow-2xl">
        <h2 className="text-2xl font-bold text-white mb-6 flex-shrink-0">{t('calendar.createModal.title')}</h2>
        
        <form onSubmit={handleSubmit} className="flex flex-col flex-grow overflow-hidden">
          <div className="overflow-y-auto pr-2 space-y-5 flex-grow custom-scrollbar">
              
              <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.relatedCase')}</label>
              <select required value={formData.case_id} onChange={(e) => setFormData(prev => ({ ...prev, case_id: e.target.value }))} className={formElementClasses}>
                <option value="">{t('calendar.createModal.selectCase')}</option>
                {cases.map(c => <option key={c.id} value={c.id}>{c.title || c.case_name || c.case_number}</option>)}
              </select>
              </div>
              
              <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.eventTitle')}</label><input type="text" required value={formData.title} onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))} className={formElementClasses} /></div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.eventType')}</label><select value={formData.event_type} onChange={(e) => setFormData(prev => ({ ...prev, event_type: e.target.value as CalendarEvent['event_type'] }))} className={formElementClasses}>{Object.keys(t('calendar.types', { returnObjects: true })).map(key => <option key={key} value={key}>{t(`calendar.types.${key}`)}</option>)}</select></div>
                <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.priority')}</label><select value={formData.priority} onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value as CalendarEvent['priority'] }))} className={formElementClasses}>{Object.keys(t('calendar.priorities', { returnObjects: true })).map(key => <option key={key} value={key}>{t(`calendar.priorities.${key}`)}</option>)}</select></div>
              </div>
              
              <div>
                <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.eventDate')}</label>
                <DatePicker
                    selected={eventDate}
                    onChange={(date: Date | null) => setEventDate(date)}
                    locale={currentLocale}
                    dateFormat="dd.MM.yyyy"
                    placeholderText={t('calendar.createModal.dateTimePlaceholder')}
                    className={formElementClasses}
                    portalId="react-datepicker-portal"
                    required
                />
              </div>
              
              {!showAdvanced && <div className="pt-2 text-center"><button type="button" onClick={() => setShowAdvanced(true)} className="text-sm text-primary-start hover:text-primary-end flex items-center justify-center mx-auto"><ChevronDown className="h-4 w-4 mr-1" />{t('calendar.createModal.addDetails')}</button></div>}
              
              {showAdvanced && <div className="space-y-5 pt-2 border-t border-white/5">
                  <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.description')}</label><textarea rows={3} value={formData.description} onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))} className={formElementClasses} /></div>
                  <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.location')}</label><input type="text" value={formData.location} onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))} className={formElementClasses} /></div>
                  <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.attendees')}</label><input type="text" value={formData.attendees} onChange={(e) => setFormData(prev => ({ ...prev, attendees: e.target.value }))} className={formElementClasses} /></div>
                  <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.notes')}</label><textarea rows={2} value={formData.notes} onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))} className={formElementClasses} /></div>
              </div>}
          </div>

          <div className="flex space-x-4 pt-6 mt-auto flex-shrink-0 border-t border-white/10">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-3 border border-white/10 rounded-xl text-gray-300 hover:bg-white/5 transition font-medium">{t('calendar.createModal.cancel')}</button>
            <button type="submit" disabled={isCreating} className="flex-1 px-4 py-3 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 disabled:opacity-50 text-white rounded-xl transition font-bold shadow-lg shadow-primary-start/20">{isCreating ? t('calendar.createModal.creating') : t('calendar.createModal.create')}</button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CalendarPage;