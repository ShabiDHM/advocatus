// FILE: src/pages/CalendarPage.tsx
// PHOENIX PROTOCOL - CALENDAR V21.0 (GLASSMORPHISM UNIFICATION)
// 1. REFACTOR: Replaced custom panel styles with standard glass utilities (glass-panel, glass-high, glass-input, glass-button).
// 2. CONSISTENCY: Uses the same color variables (primary-start, secondary-start, accent-start) as CaseCard.
// 3. UI: Preserved all existing functionality and animations.
// 4. STATUS: 100% consistent with System Architectural Snapshot.

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { CalendarEvent, Case, CalendarEventCreateRequest } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  format, addMonths, subMonths, startOfMonth, getDay, getDaysInMonth, 
  isSameDay, isToday as isTodayFns, parseISO, startOfWeek, addDays, Locale
} from 'date-fns';
import { sq, enUS } from 'date-fns/locale'; 
import {
  Calendar as CalendarIcon, Clock, MapPin, Users, AlertCircle, Plus, ChevronLeft, ChevronRight,
  Search, FileText, Gavel, AlertTriangle, XCircle, Bell, ChevronDown, Scale, MessageSquare,
  Eye, EyeOff, ShieldAlert, History, Filter, Loader2, ChevronRight as ChevronRightIcon
} from 'lucide-react';
import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import '../styles/DatePicker.css';
import DayEventsModal from '../components/DayEventsModal';

const DatePicker = (ReactDatePicker as any).default;
const localeMap: { [key: string]: Locale } = { sq: sq, al: sq, en: enUS };

interface EventDetailModalProps { event: CalendarEvent; onClose: () => void; onUpdate: () => void; }
interface CreateEventModalProps { cases: Case[]; existingEvents: CalendarEvent[]; onClose: () => void; onCreate: () => void; }
type ViewMode = 'month' | 'list';

const getEventStyle = (type: string, category?: string) => {
    // Uses Tailwind color variables for consistency
    if (category === 'FACT') {
        return { 
            border: 'border-white/10', bg: 'bg-white/5 hover:bg-white/10', 
            text: 'text-text-secondary', indicator: 'bg-text-secondary', 
            icon: <History size={12} className="text-text-secondary" /> 
        };
    }
    switch (type) {
      case 'DEADLINE': return { border: 'border-accent-start/30', bg: 'bg-accent-start/10 hover:bg-accent-start/20', text: 'text-accent-start', indicator: 'bg-accent-start', icon: <AlertTriangle size={12} className="text-accent-start" /> };
      case 'HEARING': return { border: 'border-secondary-start/30', bg: 'bg-secondary-start/10 hover:bg-secondary-start/20', text: 'text-secondary-start', indicator: 'bg-secondary-start', icon: <Gavel size={12} className="text-secondary-start" /> };
      case 'MEETING': return { border: 'border-primary-start/30', bg: 'bg-primary-start/10 hover:bg-primary-start/20', text: 'text-primary-start', indicator: 'bg-primary-start', icon: <Users size={12} className="text-primary-start" /> };
      case 'FILING': return { border: 'border-amber-500/30', bg: 'bg-amber-500/10 hover:bg-amber-500/20', text: 'text-amber-400', indicator: 'bg-amber-500', icon: <FileText size={12} className="text-amber-400" /> };
      case 'COURT_DATE': return { border: 'border-orange-500/30', bg: 'bg-orange-500/10 hover:bg-orange-500/20', text: 'text-orange-400', indicator: 'bg-orange-500', icon: <Scale size={12} className="text-orange-400" /> };
      case 'CONSULTATION': return { border: 'border-emerald-500/30', bg: 'bg-emerald-500/10 hover:bg-emerald-500/20', text: 'text-emerald-400', indicator: 'bg-emerald-500', icon: <MessageSquare size={12} className="text-emerald-400" /> };
      default: return { border: 'border-white/10', bg: 'bg-white/5 hover:bg-white/10', text: 'text-text-secondary', indicator: 'bg-text-secondary', icon: <CalendarIcon size={12} className="text-text-secondary" /> };
    }
};

const getEventId = (event: CalendarEvent): string => (event as any).id || (event as any)._id || '';

const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose, onUpdate }) => {
    const { t, i18n } = useTranslation();
    const currentLocale = localeMap[i18n.language] || enUS; 
    const [isDeleting, setIsDeleting] = useState(false);
    const formatEventDate = (dateString: string) => { const date = parseISO(dateString); const formatStr = event.is_all_day ? 'dd MMMM yyyy' : 'dd MMMM yyyy, HH:mm'; return format(date, formatStr, { locale: currentLocale }); };
    const handleDelete = async () => { if (!window.confirm(t('calendar.detailModal.deleteConfirm') as string)) return; const eventId = getEventId(event); if (!eventId) return; setIsDeleting(true); try { await apiService.deleteCalendarEvent(eventId); onUpdate(); onClose(); } catch (error: any) { alert(error.response?.data?.message || t('calendar.detailModal.deleteFailed')); } finally { setIsDeleting(false); } };
    const style = getEventStyle(event.event_type, event.category);

    return (
        <div className="fixed inset-0 bg-background-dark/60 backdrop-blur-xl flex items-center justify-center p-4 z-[2000]">
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="glass-high w-full max-w-2xl p-8 rounded-[2rem] shadow-2xl shadow-black/50 overflow-hidden">
                <div className="flex items-start justify-between mb-8">
                    <div className="flex items-start space-x-5">
                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center border ${style.border} ${style.bg} ${style.text} shadow-inner`}>{React.cloneElement(style.icon as React.ReactElement, { size: 28 })}</div>
                        <div className="min-w-0">
                            <h2 className="text-2xl font-bold text-text-primary mb-2 leading-tight">{event.title}</h2>
                            <div className="flex flex-wrap gap-2">
                                <span className={`text-[11px] px-3 py-1 rounded-full font-bold uppercase tracking-wider ${style.text} bg-white/5 border ${style.border}`}>{t(`calendar.types.${event.event_type}`)}</span>
                                <span className={`text-[11px] px-3 py-1 rounded-full border border-white/10 bg-white/5 text-text-secondary font-bold uppercase tracking-wider`}>{t(`calendar.priorities.${event.priority}`)}</span>
                            </div>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors text-text-secondary hover:text-white"><XCircle className="h-6 w-6" /></button>
                </div>
                <div className="space-y-6">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-white/5 p-5 rounded-2xl border border-white/10">
                        <div><h3 className="text-[11px] font-bold text-text-secondary uppercase tracking-widest mb-2">{t('calendar.detailModal.startDate')}</h3><div className="flex items-center text-white text-sm font-bold"><Clock className="h-4 w-4 mr-2 text-primary-start" />{formatEventDate(event.start_date)}</div></div>
                        {event.end_date && <div><h3 className="text-[11px] font-bold text-text-secondary uppercase tracking-widest mb-2">{t('calendar.detailModal.endDate')}</h3><div className="flex items-center text-white text-sm font-bold"><Clock className="h-4 w-4 mr-2 text-primary-start" />{formatEventDate(event.end_date)}</div></div>}
                    </div>
                    {event.location && (<div className="flex items-center gap-4 px-2 py-1"><div className="p-2 rounded-lg bg-primary-start/10 text-primary-start"><MapPin size={18} /></div><p className="text-sm font-semibold text-text-secondary">{event.location}</p></div>)}
                    {event.description && (<div className="px-2 py-4 border-t border-white/5"><p className="text-sm leading-relaxed text-text-secondary italic">{event.description}</p></div>)}
                </div>
                <div className="flex gap-4 mt-8 pt-6 border-t border-white/10">
                    <button onClick={onClose} className="glass-button flex-1 h-12 rounded-xl text-sm">Mbyll</button>
                    <button onClick={handleDelete} disabled={isDeleting} className="flex-1 h-12 bg-rose-600/10 hover:bg-rose-600/20 text-rose-500 border border-rose-500/20 rounded-xl font-bold text-sm transition disabled:opacity-50">Fshij</button>
                </div>
            </motion.div>
        </div>
    );
};

const CreateEventModal: React.FC<CreateEventModalProps> = ({ cases, existingEvents, onClose, onCreate }) => {
    const { t, i18n } = useTranslation();
    const currentLocale = localeMap[i18n.language] || enUS; 
    const [isCreating, setIsCreating] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [eventDate, setEventDate] = useState<Date | null>(null);
    const [conflictWarning, setConflictWarning] = useState<string | null>(null);
    const [isPublic, setIsPublic] = useState(false);
    const [formData, setFormData] = useState<Omit<CalendarEventCreateRequest, 'attendees' | 'start_date' | 'end_date'> & { attendees: string }>({ case_id: '', title: '', description: '', event_type: 'MEETING', location: '', attendees: '', is_all_day: true, priority: 'MEDIUM', notes: '' });
    
    useEffect(() => {
        if (!eventDate) { setConflictWarning(null); return; }
        const hasConflict = existingEvents.some(ev => isSameDay(parseISO(ev.start_date), eventDate));
        setConflictWarning(hasConflict ? t('calendar.conflictWarning', "Kujdes: Keni ngjarje të tjera.") as string : null);
    }, [eventDate, existingEvents, t]);

    const handleSubmit = async (e: React.FormEvent) => { 
        e.preventDefault(); 
        if (!eventDate) return; 
        setIsCreating(true); 
        try {
            const cleanDate = new Date(Date.UTC(eventDate.getFullYear(), eventDate.getMonth(), eventDate.getDate(), 12, 0, 0)).toISOString();
            const payload: any = { ...formData, start_date: cleanDate, end_date: cleanDate, attendees: formData.attendees ? formData.attendees.split(',').map(a => a.trim()) : [], is_public: isPublic, category: 'AGENDA', notes: isPublic ? (formData.notes + "\n[CLIENT_VISIBLE]") : formData.notes }; 
            await apiService.createCalendarEvent(payload); 
            onCreate(); onClose(); 
        } catch (error: any) { alert(error.response?.data?.message || "Dështoi krijimi."); } finally { setIsCreating(false); } 
    };
    
    return (
        <div className="fixed inset-0 bg-background-dark/60 backdrop-blur-xl flex items-center justify-center p-3 z-[2000]">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-high w-full max-w-lg max-h-[90vh] p-8 sm:p-10 rounded-[2.5rem] flex flex-col shadow-2xl overflow-hidden">
                <h2 className="text-2xl font-bold text-text-primary mb-8 shrink-0 tracking-tight uppercase tracking-wider">{t('calendar.createModal.title')}</h2>
                {conflictWarning && (<div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-6 flex items-center gap-4 animate-pulse"><ShieldAlert className="text-amber-400 h-5 w-5 shrink-0" /><span className="text-amber-200 text-xs font-bold">{conflictWarning}</span></div>)}
                <form onSubmit={handleSubmit} className="flex flex-col flex-grow overflow-hidden">
                    <div className="overflow-y-auto pr-2 space-y-5 flex-grow custom-scrollbar">
                        <div><label className="block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1">{t('calendar.createModal.relatedCase')}</label><select required value={formData.case_id} onChange={(e) => setFormData(prev => ({ ...prev, case_id: e.target.value }))} className="glass-input w-full px-4 py-3 rounded-xl"><option value="" className="bg-background-dark">Zgjidhni rastin...</option>{cases.map(c => <option key={c.id} value={c.id} className="bg-background-dark">{c.title || c.case_number}</option>)}</select></div>
                        <div><label className="block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1">{t('calendar.createModal.eventTitle')}</label><input type="text" required value={formData.title} onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))} className="glass-input w-full px-4 py-3 rounded-xl" /></div>
                        <div className="grid grid-cols-2 gap-4">
                            <div><label className="block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1">Lloji</label><select value={formData.event_type} onChange={(e) => setFormData(prev => ({ ...prev, event_type: e.target.value as CalendarEvent['event_type'] }))} className="glass-input w-full px-4 py-3 rounded-xl">{Object.keys(t('calendar.types', { returnObjects: true }) as object).map(key => <option key={key} value={key} className="bg-background-dark">{t(`calendar.types.${key}`)}</option>)}</select></div>
                            <div><label className="block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1">Prioriteti</label><select value={formData.priority} onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value as CalendarEvent['priority'] }))} className="glass-input w-full px-4 py-3 rounded-xl">{Object.keys(t('calendar.priorities', { returnObjects: true }) as object).map(key => <option key={key} value={key} className="bg-background-dark">{t(`calendar.priorities.${key}`)}</option>)}</select></div>
                        </div>
                        <div><label className="block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1">Data</label><DatePicker selected={eventDate} onChange={(date: Date | null) => setEventDate(date)} locale={currentLocale} dateFormat="dd.MM.yyyy" placeholderText="Klikoni për datën" className="glass-input w-full px-4 py-3 rounded-xl" portalId="react-datepicker-portal" required /></div>
                        
                        <div className="bg-white/5 border border-white/10 rounded-2xl p-4 flex items-center justify-between cursor-pointer" onClick={() => setIsPublic(!isPublic)}><div className="flex items-center gap-4"><div className={`p-3 rounded-xl transition-colors ${isPublic ? 'bg-primary-start text-white' : 'bg-white/10 text-text-secondary'}`}>{isPublic ? <Eye size={18} /> : <EyeOff size={18} />}</div><div><h4 className={`text-sm font-bold ${isPublic ? 'text-primary-start' : 'text-text-secondary'}`}>{isPublic ? 'Publike' : 'Private'}</h4><p className="text-[10px] text-text-secondary/50 uppercase tracking-widest">Për klientin</p></div></div><div className={`w-10 h-5 rounded-full relative transition-colors ${isPublic ? 'bg-primary-start' : 'bg-gray-700'}`}><div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-transform ${isPublic ? 'translate-x-5' : 'translate-x-0'}`} /></div></div>

                        {!showAdvanced && (
                            <button type="button" onClick={() => setShowAdvanced(true)} className="w-full text-[11px] font-bold text-text-secondary uppercase flex items-center justify-center gap-2 py-3 hover:text-white transition-all">
                                <ChevronDown size={14} /> Detaje Shtesë
                            </button>
                        )}
                        
                        {showAdvanced && (
                            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5 pt-2">
                                <div><label className="block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1">Përshkrimi</label><textarea rows={3} value={formData.description} onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))} className="glass-input w-full px-4 py-3 rounded-xl" /></div>
                                <div><label className="block text-[11px] font-bold text-primary-start uppercase tracking-widest mb-2 ml-1">Vendi</label><input type="text" value={formData.location} onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))} className="glass-input w-full px-4 py-3 rounded-xl" /></div>
                            </motion.div>
                        )}
                    </div>

                    <div className="flex gap-4 pt-8 mt-auto border-t border-white/10">
                        <button type="button" onClick={onClose} className="flex-1 h-12 rounded-xl text-text-secondary font-bold text-sm hover:text-white transition-all">Anulo</button>
                        <button type="submit" disabled={isCreating} className="flex-1 h-12 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold text-sm tracking-widest uppercase shadow-lg shadow-primary-start/20 transition-all">{isCreating ? <Loader2 className="animate-spin h-5 w-5 mx-auto" /> : 'Krijo'}</button>
                    </div>
                </form>
            </motion.div>
        </div>
    );
};

const CalendarPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('ALL');
  const [showFacts, setShowFacts] = useState(false);
  const [isDayModalOpen, setIsDayModalOpen] = useState(false);
  const [selectedDateForModal, setSelectedDateForModal] = useState<Date | null>(null);
  const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);
  const currentLocale = localeMap[i18n.language] || enUS;

  const loadData = useCallback(async () => {
    try { setLoading(true); setError(''); const [eventsData, casesData] = await Promise.all([apiService.getCalendarEvents(), apiService.getCases()]); setEvents(eventsData); setCases(casesData); } catch (err: any) { setError(t('calendar.loadFailure') as string); } finally { setLoading(false); }
  }, [t]);
  useEffect(() => { loadData(); }, [loadData]);

  const navigateMonth = (direction: 'prev' | 'next') => { setCurrentDate(direction === 'prev' ? subMonths(currentDate, 1) : addMonths(currentDate, 1)); };

  const filteredEvents = useMemo(() => {
    return events.filter(event => {
        const matchesSearch = `${event.title} ${event.description || ''}`.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = filterType === 'ALL' || event.event_type === filterType;
        const matchesCategory = showFacts || event.category === 'AGENDA';
        return matchesSearch && matchesType && matchesCategory;
    });
  }, [events, searchTerm, filterType, showFacts]);

  const upcomingAlerts = useMemo(() => {
    return events.filter(event => event.category === 'AGENDA' && ['DEADLINE', 'HEARING'].includes(event.event_type)).sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime()).slice(0, 10);
  }, [events]);

  const renderListView = () => (
    <div className="glass-panel flex-1 flex flex-col rounded-[2.5rem] overflow-hidden min-h-0">
        <div className="flex-1 overflow-y-auto custom-scrollbar divide-y divide-white/5 px-6 sm:px-8">
            {filteredEvents.length === 0 ? (<div className="py-24 text-center text-text-secondary italic text-sm font-medium">{t('calendar.noEventsFound')}</div>) : (
                filteredEvents.sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime()).map(event => {
                    const style = getEventStyle(event.event_type, event.category);
                    const isShared = (event as any).is_public === true || (event.notes && event.notes.includes("CLIENT_VISIBLE"));
                    return (
                        <div key={getEventId(event)} onClick={() => setSelectedEvent(event)} className="py-5 sm:py-6 cursor-pointer transition-all flex items-center justify-between group px-2 rounded-2xl mt-1 first:mt-0">
                            <div className="flex items-start space-x-5 min-w-0 flex-1">
                                <div className="flex-shrink-0 text-center min-w-[60px] p-2 rounded-2xl bg-white/5 border border-white/10 group-hover:border-primary-start/50 group-hover:bg-primary-start/5 transition-all">
                                    <div className="text-[10px] text-text-secondary uppercase font-black tracking-widest">{format(parseISO(event.start_date), 'MMM', { locale: currentLocale })}</div>
                                    <div className="text-2xl font-black text-text-primary leading-none mt-1">{format(parseISO(event.start_date), 'dd')}</div>
                                </div>
                                <div className="min-w-0 flex-1 pr-4">
                                    <h4 className="text-base font-bold text-text-primary group-hover:text-primary-start transition-colors truncate">{event.title}</h4>
                                    <div className="flex items-center gap-3 mt-2">
                                        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${style.border} ${style.bg} ${style.text} font-black uppercase tracking-widest`}>{t(`calendar.types.${event.event_type}`)}</span>
                                        {isShared && <Eye size={12} className="text-emerald-500" />}
                                        {event.description && <span className="text-xs text-text-secondary truncate italic">{event.description}</span>}
                                    </div>
                                </div>
                            </div>
                            <ChevronRightIcon size={20} className="text-text-secondary group-hover:text-primary-start transition-all transform group-hover:translate-x-1 shrink-0" />
                        </div>
                    );
                })
            )}
        </div>
    </div>
  );

  const renderMonthView = () => {
    const monthStart = startOfMonth(currentDate);
    const daysInMonth = getDaysInMonth(currentDate);
    const weekStartsOn = currentLocale?.options?.weekStartsOn ?? 1; 
    const firstDayOfMonth = getDay(monthStart);
    const startingDayIndex = (firstDayOfMonth - weekStartsOn + 7) % 7;
    const cellClass = "min-h-[100px] sm:min-h-[130px] border-r border-b border-white/5 relative group transition-all hover:bg-white/5 flex flex-col cursor-pointer";
    const days = Array.from({ length: startingDayIndex }, (_, i) => <div key={`empty-${i}`} className={`${cellClass} bg-black/20`} />);
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), day);
      const dayEvents = filteredEvents.filter(event => isSameDay(parseISO(event.start_date), date));
      const today = isTodayFns(date);
      days.push(
        <div key={day} className={`${cellClass} p-1 ${today ? 'bg-primary-start/5' : ''}`} onClick={() => { setSelectedDateForModal(date); setIsDayModalOpen(true); }}>
          <div className={`text-xs font-black mb-2 flex justify-between items-center p-2 ${today ? 'text-primary-start' : 'text-text-secondary'}`}>
            <span className={`w-7 h-7 flex items-center justify-center rounded-xl transition-all ${today ? 'bg-primary-start text-white shadow-xl shadow-primary-start/30' : 'group-hover:text-white'}`}>{day}</span>
          </div>
          <div className="flex-1 w-full space-y-1.5 px-1 overflow-visible relative">
            {dayEvents.slice(0, 3).map(event => {
              const style = getEventStyle(event.event_type, event.category);
              const eventId = getEventId(event);
              return (
                <div key={eventId} className="relative w-full">
                    <button onClick={(e) => { e.stopPropagation(); setSelectedEvent(event); }} onMouseEnter={() => setHoveredEventId(eventId)} onMouseLeave={() => setHoveredEventId(null)} className={`w-full text-left px-2 py-1 rounded-lg border flex items-center gap-2 transition-all duration-300 ${style.bg} ${style.border} group-hover:shadow-lg ${hoveredEventId === eventId ? 'scale-[1.05] z-50 ring-2 ring-white/10 shadow-black shadow-2xl' : ''}`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${style.indicator} shrink-0`} />
                        <span className={`text-[10px] font-bold truncate ${style.text} flex-1 tracking-tight`}>{event.title}</span>
                    </button>
                    <AnimatePresence>{hoveredEventId === eventId && (<motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="absolute left-0 bottom-full mb-3 z-[100] w-64 glass-high p-4 rounded-2xl shadow-2xl pointer-events-none"><div className={`text-[10px] font-black uppercase mb-2 flex items-center gap-2 ${style.text}`}>{style.icon} {t(`calendar.types.${event.event_type}`)}</div><div className="text-white font-bold text-sm mb-2">{event.title}</div><div className="text-text-secondary text-[11px] line-clamp-2 italic mb-3">{event.description || t('general.notAvailable')}</div><div className="pt-3 border-t border-white/10 text-text-secondary text-[10px] flex justify-between font-bold"><span>{format(parseISO(event.start_date), 'HH:mm')}</span><span className="text-primary-start uppercase">{t(`calendar.priorities.${event.priority}`)}</span></div></motion.div>)}</AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      );
    }
    const totalCells = Math.ceil(days.length / 7) * 7;
    while(days.length < totalCells) days.push(<div key={`empty-end-${days.length}`} className={`${cellClass} bg-black/20`} />);
    const weekStarts = startOfWeek(new Date(), { weekStartsOn });
    const weekDays = Array.from({ length: 7 }, (_, i) => format(addDays(weekStarts, i), 'EEEEEE', { locale: currentLocale }));
    return (<div className="glass-panel flex-1 flex flex-col rounded-[2.5rem] overflow-hidden"><div className="grid grid-cols-7 bg-white/10 border-b border-white/10 shrink-0">{weekDays.map(day => <div key={day} className="py-4 text-center text-[11px] font-black text-text-secondary uppercase tracking-widest">{day}</div>)}</div><div className="grid grid-cols-7 border-l border-t border-white/5 flex-1 overflow-y-auto custom-scrollbar">{days}</div></div>);
  };
  
  if (loading) return <div className="flex items-center justify-center h-[calc(100dvh-64px)]"><Loader2 className="animate-spin text-primary-start w-10 h-10" /></div>;

  return (
    <div className="h-[calc(100dvh-64px)] overflow-hidden bg-transparent flex flex-col font-sans selection:bg-primary-start/30">
        <div id="react-datepicker-portal"></div>
        <div className="flex-1 flex flex-col max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 gap-6 min-h-0">
            {error && (<motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="shrink-0 bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 flex items-center gap-4"><AlertCircle className="h-5 w-5 text-rose-500" /><span className="text-rose-100 text-sm font-bold">{error}</span></motion.div>)}

            <div className="shrink-0 flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-4">
                <div className="flex items-center justify-between sm:justify-start gap-4">
                    <div className="glass-panel flex items-center p-1.5 shrink-0">
                        <button onClick={() => navigateMonth('prev')} className="p-2 hover:bg-white/10 rounded-xl transition-all active:scale-90"><ChevronLeft size={20} /></button>
                        <button onClick={() => setCurrentDate(new Date())} className="px-5 text-[11px] font-bold uppercase tracking-widest text-text-secondary hover:text-white transition-colors">{t('calendar.today')}</button>
                        <button onClick={() => navigateMonth('next')} className="p-2 hover:bg-white/10 rounded-xl transition-all active:scale-90"><ChevronRight size={20} /></button>
                    </div>
                    <div className="hidden sm:block"><h1 className="text-2xl font-bold text-text-primary tracking-tight capitalize">{format(currentDate, 'LLLL yyyy', { locale: currentLocale })}</h1></div>
                </div>
                <button onClick={() => setIsCreateModalOpen(true)} className="glass-button flex items-center justify-center gap-3 px-8 h-12 rounded-2xl text-xs uppercase tracking-widest">
                    <Plus size={18} strokeWidth={3} /> {t('calendar.newEvent')}
                </button>
            </div>
            
            <div className="shrink-0 flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1 h-12">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
                    <input type="text" placeholder={t('calendar.searchPlaceholder') as string} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="glass-input w-full h-full pl-12 pr-6 rounded-2xl text-sm font-medium" />
                </div>
                <div className="flex gap-4 h-12 sm:w-auto">
                    <button onClick={() => setShowFacts(!showFacts)} className={`glass-button flex items-center justify-center gap-3 px-6 rounded-2xl text-xs font-bold uppercase tracking-wider ${showFacts ? 'bg-primary-start text-white' : ''}`}><History size={14} /> {showFacts ? 'Gjithçka' : 'Afatet'}</button>
                    <div className="glass-panel flex p-1.5 rounded-2xl">
                        <button onClick={() => setViewMode('month')} className={`px-5 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all ${viewMode === 'month' ? 'bg-white text-black shadow-xl shadow-white/10' : 'text-text-secondary hover:text-white'}`}>Muaji</button>
                        <button onClick={() => setViewMode('list')} className={`px-5 rounded-xl text-[10px] font-bold uppercase tracking-wider transition-all ${viewMode === 'list' ? 'bg-white text-black shadow-xl shadow-white/10' : 'text-text-secondary hover:text-white'}`}>Lista</button>
                    </div>
                </div>
            </div>

            <div className="flex-1 grid grid-cols-1 xl:grid-cols-4 gap-8 min-h-0">
                <div className="xl:col-span-3 flex flex-col min-h-0">{viewMode === 'list' ? renderListView() : renderMonthView()}</div>
                <div className="hidden xl:flex xl:col-span-1 flex-col gap-8 min-h-0">
                    <div className="glass-panel flex-1 p-8 rounded-[2.5rem] relative overflow-hidden flex flex-col">
                        <h3 className="text-sm font-semibold text-white/90 mb-8 flex items-center gap-3 uppercase tracking-wider"><Bell className="text-accent-start" size={16} />{t('calendar.upcomingAlerts')}</h3>
                        <div className="flex-1 overflow-y-auto custom-scrollbar space-y-6 pr-2">
                            {upcomingAlerts.length === 0 ? (<div className="h-full flex items-center justify-center text-center px-4 italic text-text-secondary text-sm font-medium">S'ka afate.</div>) : (upcomingAlerts.map(ev => { const style = getEventStyle(ev.event_type, ev.category); return (<button key={getEventId(ev)} onClick={() => setSelectedEvent(ev)} className="w-full flex gap-5 items-start group text-left p-4 rounded-2xl hover:bg-white/5 transition-all border border-transparent hover:border-white/10 active:scale-95"><div className={`mt-2 w-2 h-2 rounded-full shrink-0 ${style.indicator} shadow-[0_0_12px_currentColor]`} /><div className="min-w-0 flex-1"><h4 className="text-sm font-bold text-text-secondary group-hover:text-primary-start transition-colors truncate tracking-tight">{ev.title}</h4><p className="text-[11px] text-text-secondary/50 mt-2 font-bold uppercase tracking-wider">{format(parseISO(ev.start_date), 'dd MMM')} • {t(`calendar.types.${ev.event_type}`)}</p></div></button>)}))}
                        </div>
                    </div>
                    <div className="glass-panel p-8 rounded-[2.5rem] shrink-0">
                        <h3 className="text-sm font-semibold text-white/90 mb-6 uppercase tracking-wider flex items-center gap-3"><Filter size={16} className="text-primary-start" /> {t('calendar.eventTypes')}</h3>
                        <div className="space-y-2 overflow-y-auto max-h-[220px] custom-scrollbar pr-2">
                            {Object.keys(t('calendar.types', { returnObjects: true }) as object).map((key) => { 
                                const style = getEventStyle(key); return (<div key={key} className="flex items-center gap-4 p-3 rounded-2xl hover:bg-white/5 transition-all cursor-pointer border border-transparent hover:border-white/5" onClick={() => setFilterType(filterType === key ? 'ALL' : key)}><div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${style.border} ${style.bg} ${style.text} shadow-inner`}>{React.cloneElement(style.icon as React.ReactElement, { size: 16 })}</div><span className={`text-[12px] uppercase tracking-wider font-medium ${filterType === key ? 'text-white' : 'text-text-secondary'}`}>{t(`calendar.types.${key}`)}</span>{filterType === key && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-start" />}</div>);
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {selectedEvent && <EventDetailModal event={selectedEvent} onClose={() => setSelectedEvent(null)} onUpdate={loadData} />}
        {isCreateModalOpen && <CreateEventModal cases={cases} existingEvents={events} onClose={() => setIsCreateModalOpen(false)} onCreate={loadData} />}
        <DayEventsModal isOpen={isDayModalOpen} onClose={() => setIsDayModalOpen(false)} date={selectedDateForModal} events={filteredEvents.filter(e => selectedDateForModal && isSameDay(parseISO(e.start_date), selectedDateForModal))} t={t} onAddEvent={() => { setIsDayModalOpen(false); setIsCreateModalOpen(true); }} />
    </div>
  );
};

export default CalendarPage;