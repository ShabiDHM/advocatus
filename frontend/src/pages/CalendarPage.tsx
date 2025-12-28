// FILE: src/pages/CalendarPage.tsx
// PHOENIX PROTOCOL - CALENDAR V9.0 (SYMMETRICAL LAYOUT)
// 1. SYMMETRY FIX: Applied 'items-stretch' and 'flex-1' to force equal column heights on Desktop.
// 2. LAYOUT: The 'Upcoming Alerts' panel now expands to align with the bottom of the calendar.
// 3. VISUALS: Preserved Glassmorphism and Glow effects.

import React, { useState, useEffect, useRef } from 'react';
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
  Search, FileText, Gavel, AlertTriangle, XCircle, Bell, ChevronDown, Scale, MessageSquare,
  Eye, EyeOff, ShieldAlert
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

const getEventStyle = (type: string) => {
    switch (type) {
      case 'DEADLINE': return { border: 'border-rose-500/50', bg: 'bg-rose-500/10 hover:bg-rose-500/20', text: 'text-rose-200', indicator: 'bg-rose-500', icon: <AlertTriangle size={12} className="text-rose-400" /> };
      case 'HEARING': return { border: 'border-purple-500/50', bg: 'bg-purple-500/10 hover:bg-purple-500/20', text: 'text-purple-200', indicator: 'bg-purple-500', icon: <Gavel size={12} className="text-purple-400" /> };
      case 'MEETING': return { border: 'border-blue-500/50', bg: 'bg-blue-500/10 hover:bg-blue-500/20', text: 'text-blue-200', indicator: 'bg-blue-500', icon: <Users size={12} className="text-blue-400" /> };
      case 'FILING': return { border: 'border-amber-500/50', bg: 'bg-amber-500/10 hover:bg-amber-500/20', text: 'text-amber-200', indicator: 'bg-amber-500', icon: <FileText size={12} className="text-amber-400" /> };
      case 'COURT_DATE': return { border: 'border-orange-500/50', bg: 'bg-orange-500/10 hover:bg-orange-500/20', text: 'text-orange-200', indicator: 'bg-orange-500', icon: <Scale size={12} className="text-orange-400" /> };
      case 'CONSULTATION': return { border: 'border-emerald-500/50', bg: 'bg-emerald-500/10 hover:bg-emerald-500/20', text: 'text-emerald-200', indicator: 'bg-emerald-500', icon: <MessageSquare size={12} className="text-emerald-400" /> };
      default: return { border: 'border-slate-500/50', bg: 'bg-slate-500/10 hover:bg-slate-500/20', text: 'text-slate-200', indicator: 'bg-slate-500', icon: <CalendarIcon size={12} className="text-slate-400" /> };
    }
};

const getEventId = (event: CalendarEvent): string => (event as any).id || (event as any)._id || '';

const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose, onUpdate }) => {
    const { t, i18n } = useTranslation();
    const currentLocale = localeMap[i18n.language] || enUS; 
    const [isDeleting, setIsDeleting] = useState(false);
    const isMidnight = (dateString: string) => { const d = parseISO(dateString); return d.getHours() === 0 && d.getMinutes() === 0; };
    const formatEventDate = (dateString: string) => { const date = parseISO(dateString); const formatStr = (event.is_all_day || isMidnight(dateString)) ? 'dd MMMM yyyy' : 'dd MMMM yyyy, HH:mm'; return format(date, formatStr, { locale: currentLocale }); };
    const handleDelete = async () => { if (!window.confirm(t('calendar.detailModal.deleteConfirm'))) return; const eventId = getEventId(event); if (!eventId) return; setIsDeleting(true); try { await apiService.deleteCalendarEvent(eventId); onUpdate(); onClose(); } catch (error: any) { alert(error.response?.data?.message || t('calendar.detailModal.deleteFailed')); } finally { setIsDeleting(false); } };
    const style = getEventStyle(event.event_type);
    const isShared = (event as any).is_public === true;

    return (
        <div className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center p-4 z-[100]">
            <div className="glass-high border border-white/10 rounded-3xl p-8 w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
                <div className="flex items-start justify-between mb-8">
                    <div className="flex items-start space-x-5">
                        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center border ${style.border} ${style.bg} ${style.text}`}>
                            {React.cloneElement(style.icon as React.ReactElement, { size: 28 })}
                        </div>
                        <div>
                            <div className="flex items-center gap-3">
                                <h2 className="text-2xl font-bold text-white mb-2">{event.title}</h2>
                                {isShared && (
                                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase border border-emerald-500/30">
                                        <Eye size={10} /> {t('calendar.clientLabel', 'Klienti')}
                                    </span>
                                )}
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <span className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${style.bg} ${style.text} border ${style.border} border-opacity-30`}>{t(`calendar.types.${event.event_type}`)}</span>
                                <span className={`text-xs px-2.5 py-1 rounded-full border border-white/20 text-gray-300`}>{t(`calendar.priorities.${event.priority}`)}</span>
                            </div>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full transition-colors"><XCircle className="h-6 w-6 text-gray-400 hover:text-white" /></button>
                </div>
                <div className="space-y-6">
                    {event.description && (<div className="bg-white/5 p-4 rounded-xl border border-white/10"><h3 className="text-xs font-bold text-gray-500 uppercase mb-2">{t('calendar.detailModal.description')}</h3><p className="text-gray-200 text-sm leading-relaxed">{event.description}</p></div>)}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                        <div><h3 className="text-xs font-bold text-gray-500 uppercase mb-1">{t('calendar.detailModal.startDate')}</h3><div className="flex items-center text-white"><Clock className="h-4 w-4 mr-2 text-primary-start" />{formatEventDate(event.start_date)}</div></div>
                        {event.end_date && event.end_date !== event.start_date && <div><h3 className="text-xs font-bold text-gray-500 uppercase mb-1">{t('calendar.detailModal.endDate')}</h3><div className="flex items-center text-white"><Clock className="h-4 w-4 mr-2 text-primary-start" />{formatEventDate(event.end_date)}</div></div>}
                    </div>
                    {event.location && <div><h3 className="text-xs font-bold text-gray-500 uppercase mb-1">{t('calendar.detailModal.location')}</h3><div className="flex items-center text-white"><MapPin className="h-4 w-4 mr-2 text-primary-start" />{event.location}</div></div>}
                    {event.attendees && event.attendees.length > 0 && (<div><h3 className="text-xs font-bold text-gray-500 uppercase mb-1">{t('calendar.detailModal.attendees')}</h3><div className="flex flex-wrap gap-2">{event.attendees.map((att, i) => (<span key={i} className="flex items-center text-xs bg-white/5 px-2 py-1 rounded border border-white/10 text-gray-300"><Users className="h-3 w-3 mr-1.5" />{att}</span>))}</div></div>)}
                    {event.notes && (<div><h3 className="text-xs font-bold text-gray-500 uppercase mb-2">{t('calendar.detailModal.notes')}</h3><p className="text-gray-400 italic text-sm">{event.notes}</p></div>)}
                </div>
                <div className="flex space-x-4 mt-8 pt-6 border-t border-white/10">
                    <button onClick={onClose} className="flex-1 px-4 py-3 border border-white/10 rounded-xl text-gray-300 hover:bg-white/5 transition font-medium">{t('calendar.detailModal.close')}</button>
                    <button onClick={handleDelete} disabled={isDeleting} className="flex-1 px-4 py-3 bg-red-600/10 hover:bg-red-600/20 text-red-500 border border-red-600/30 rounded-xl transition font-medium disabled:opacity-50">{isDeleting ? t('calendar.detailModal.deleting') : t('calendar.detailModal.delete')}</button>
                </div>
            </div>
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

    const [formData, setFormData] = useState<Omit<CalendarEventCreateRequest, 'attendees' | 'start_date' | 'end_date'> & { attendees: string }>({ 
        case_id: '', title: '', description: '', event_type: 'MEETING', location: '', attendees: '', is_all_day: true, priority: 'MEDIUM', notes: '' 
    });
    
    useEffect(() => {
        if (!eventDate) {
            setConflictWarning(null);
            return;
        }
        const checkStart = eventDate;
        const hasConflict = existingEvents.some(ev => {
            const start = parseISO(ev.start_date);
            return isSameDay(start, checkStart);
        });
        if (hasConflict) {
            setConflictWarning(t('calendar.conflictWarning', "Kujdes: Keni ngjarje të tjera..."));
        } else {
            setConflictWarning(null);
        }
    }, [eventDate, existingEvents, t]);

    const handleSubmit = async (e: React.FormEvent) => { 
        e.preventDefault(); 
        if (!eventDate) { alert(t('calendar.createModal.dateTimePlaceholder')); return; } 
        setIsCreating(true); 
        
        try {
            const cleanDate = new Date(Date.UTC(eventDate.getFullYear(), eventDate.getMonth(), eventDate.getDate(), 12, 0, 0));
            const isoDate = cleanDate.toISOString();

            const payload: any = { 
                ...formData, 
                start_date: isoDate, 
                end_date: isoDate, 
                attendees: formData.attendees ? formData.attendees.split(',').map(a => a.trim()) : [],
                is_public: isPublic 
            }; 
            
            if (!payload.notes) payload.notes = "";
            if (isPublic) payload.notes += "\n[CLIENT_VISIBLE]";

            await apiService.createCalendarEvent(payload); 
            onCreate(); 
            onClose(); 
        } catch (error: any) { 
            alert(error.response?.data?.message || t('calendar.createModal.createFailed')); 
        } finally { 
            setIsCreating(false); 
        } 
    };
    
    const formElementClasses = "glass-input block w-full px-4 py-2.5 rounded-xl";
    
    return (
        <div className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center p-4 z-[100]">
            <div className="glass-high border border-white/10 rounded-3xl p-8 w-full max-w-lg max-h-[90vh] flex flex-col shadow-2xl animate-in fade-in zoom-in-95 duration-200">
                <h2 className="text-2xl font-bold text-white mb-6 flex-shrink-0">{t('calendar.createModal.title')}</h2>
                
                {conflictWarning && (
                    <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 mb-4 flex items-center gap-3 animate-pulse">
                        <ShieldAlert className="text-amber-400 h-5 w-5" />
                        <span className="text-amber-200 text-xs font-bold">{conflictWarning}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="flex flex-col flex-grow overflow-hidden">
                    <div className="overflow-y-auto pr-2 space-y-5 flex-grow custom-scrollbar">
                        <div>
                            <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.relatedCase')}</label>
                            <select required value={formData.case_id} onChange={(e) => setFormData(prev => ({ ...prev, case_id: e.target.value }))} className={formElementClasses}>
                                <option value="" className="bg-gray-900 text-gray-200">{t('calendar.createModal.selectCase')}</option>
                                {cases.map(c => <option key={c.id} value={c.id} className="bg-gray-900 text-gray-200">{c.title || c.case_name || c.case_number}</option>)}
                            </select>
                        </div>
                        <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.eventTitle')}</label><input type="text" required value={formData.title} onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))} className={formElementClasses} /></div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.eventType')}</label>
                                <select value={formData.event_type} onChange={(e) => setFormData(prev => ({ ...prev, event_type: e.target.value as CalendarEvent['event_type'] }))} className={formElementClasses}>
                                    {Object.keys(t('calendar.types', { returnObjects: true })).map(key => <option key={key} value={key} className="bg-gray-900 text-gray-200">{t(`calendar.types.${key}`)}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.priority')}</label>
                                <select value={formData.priority} onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value as CalendarEvent['priority'] }))} className={formElementClasses}>
                                    {Object.keys(t('calendar.priorities', { returnObjects: true })).map(key => <option key={key} value={key} className="bg-gray-900 text-gray-200">{t(`calendar.priorities.${key}`)}</option>)}
                                </select>
                            </div>
                        </div>
                        <div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.eventDate')}</label><DatePicker selected={eventDate} onChange={(date: Date | null) => setEventDate(date)} locale={currentLocale} dateFormat="dd.MM.yyyy" placeholderText={t('calendar.createModal.dateTimePlaceholder')} className={formElementClasses} portalId="react-datepicker-portal" required /></div>
                        
                        <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-3 flex items-center justify-between cursor-pointer" onClick={() => setIsPublic(!isPublic)}>
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg ${isPublic ? 'bg-indigo-500 text-white' : 'bg-white/10 text-gray-400'}`}>
                                    {isPublic ? <Eye size={18} /> : <EyeOff size={18} />}
                                </div>
                                <div>
                                    <h4 className={`text-sm font-bold ${isPublic ? 'text-indigo-200' : 'text-gray-400'}`}>
                                        {isPublic ? t('calendar.visibilityPublic', 'Publike') : t('calendar.visibilityPrivate', 'Private')}
                                    </h4>
                                    <p className="text-[10px] text-gray-500">
                                        {isPublic ? t('calendar.visibilityPublicDesc') : t('calendar.visibilityPrivateDesc')}
                                    </p>
                                </div>
                            </div>
                            <div className={`w-10 h-5 rounded-full relative transition-colors ${isPublic ? 'bg-indigo-500' : 'bg-gray-700'}`}>
                                <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-transform ${isPublic ? 'translate-x-5' : 'translate-x-0'}`} />
                            </div>
                        </div>

                        {!showAdvanced && <div className="pt-2 text-center"><button type="button" onClick={() => setShowAdvanced(true)} className="text-sm text-primary-start hover:text-primary-end flex items-center justify-center mx-auto"><ChevronDown className="h-4 w-4 mr-1" />{t('calendar.createModal.addDetails')}</button></div>}
                        {showAdvanced && <div className="space-y-5 pt-2 border-t border-white/5"><div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.description')}</label><textarea rows={3} value={formData.description} onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))} className={formElementClasses} /></div><div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.location')}</label><input type="text" value={formData.location} onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))} className={formElementClasses} /></div><div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.attendees')}</label><input type="text" value={formData.attendees} onChange={(e) => setFormData(prev => ({ ...prev, attendees: e.target.value }))} className={formElementClasses} /></div><div><label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('calendar.createModal.notes')}</label><textarea rows={2} value={formData.notes} onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))} className={formElementClasses} /></div></div>}
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
  const [selectedDateForModal, setSelectedDateForModal] = useState<Date | null>(null);
  const [isDayModalOpen, setIsDayModalOpen] = useState(false);
  const hasCheckedForToday = useRef(false);

  const currentLocale = localeMap[i18n.language] || enUS;

  useEffect(() => { loadData(); }, []);

  useEffect(() => {
    if (!loading && events.length > 0 && !hasCheckedForToday.current) {
        const today = new Date();
        const todaysEvents = events.filter(e => isSameDay(parseISO(e.start_date), today));
        if (todaysEvents.length > 0) {
            setSelectedDateForModal(today);
            setIsDayModalOpen(true);
        }
        hasCheckedForToday.current = true;
    }
  }, [loading, events]);

  const loadData = async () => {
    try {
      setLoading(true); setError('');
      const [eventsData, casesData] = await Promise.all([apiService.getCalendarEvents(), apiService.getCases()]);
      setEvents(eventsData); setCases(casesData);
    } catch (error: any) { setError(error.response?.data?.message || error.message || t('calendar.loadFailure')); } 
    finally { setLoading(false); }
  };

  const handleDayClick = (day: Date) => { setSelectedDateForModal(day); setIsDayModalOpen(true); };
  const navigateMonth = (direction: 'prev' | 'next') => { setCurrentDate(direction === 'prev' ? subMonths(currentDate, 1) : addMonths(currentDate, 1)); };

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
        const today = new Date(); today.setHours(0, 0, 0, 0); 
        const sevenDaysFromNow = new Date(today); sevenDaysFromNow.setDate(today.getDate() + 7); sevenDaysFromNow.setHours(23, 59, 59, 999); 
        return eventDate >= today && eventDate <= sevenDaysFromNow;
    })
    .sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
    .slice(0, 5);

  const selectedDayEvents = filteredEvents.filter(e => selectedDateForModal && isSameDay(parseISO(e.start_date), selectedDateForModal));
  
  const renderListView = () => (
    <div className="glass-panel rounded-3xl overflow-hidden flex-1 h-full">
        {filteredEvents.length === 0 ? (
            <div className="p-8 text-center text-text-secondary">{t('calendar.noEventsFound', 'Nuk u gjetën ngjarje.')}</div>
        ) : (
            <div className="divide-y divide-white/5 h-full overflow-y-auto custom-scrollbar">
                {filteredEvents.sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime()).map(event => {
                        const style = getEventStyle(event.event_type);
                        const isShared = (event as any).is_public === true || (event.notes && event.notes.includes("CLIENT_VISIBLE"));
                        return (
                            <div key={getEventId(event)} onClick={() => setSelectedEvent(event)} className="p-4 hover:bg-white/5 cursor-pointer transition-colors flex items-center justify-between group">
                                <div className="flex items-start space-x-4">
                                    <div className="flex-shrink-0 mt-1 text-center min-w-[50px]">
                                        <div className="text-xs text-text-secondary uppercase">{format(parseISO(event.start_date), 'MMM', { locale: currentLocale })}</div>
                                        <div className={`text-xl font-bold text-white`}>{format(parseISO(event.start_date), 'dd')}</div>
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <h4 className="text-base font-medium text-white group-hover:text-primary-start transition-colors">{event.title}</h4>
                                            {isShared && <div title={t('calendar.clientLabel')}><Eye size={12} className="text-emerald-400" /></div>}
                                        </div>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className={`text-[10px] px-2 py-0.5 rounded border ${style.border} ${style.bg} ${style.text} flex items-center gap-1`}>{style.icon} {t(`calendar.types.${event.event_type}`)}</span>
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

  const renderMonthView = () => {
    const monthStart = startOfMonth(currentDate);
    const daysInMonth = getDaysInMonth(currentDate);
    const weekStartsOn = currentLocale?.options?.weekStartsOn ?? 1; 
    const firstDayOfMonth = getDay(monthStart);
    const startingDayIndex = (firstDayOfMonth - weekStartsOn + 7) % 7;
    // Glass Cell Styles - Flex Col to fill available space
    const cellClass = "min-h-[100px] border-r border-b border-white/5 relative group transition-colors hover:bg-white/5 flex flex-col";
    const days = Array.from({ length: startingDayIndex }, (_, i) => <div key={`empty-${i}`} className={`${cellClass} bg-black/10`} />);

    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), day);
      const dayEvents = filteredEvents.filter(event => isSameDay(parseISO(event.start_date), date));
      const today = isTodayFns(date);
      
      days.push(
        <div key={day} className={`${cellClass} p-1 ${today ? 'bg-primary-start/10' : ''}`} onClick={() => handleDayClick(date)}>
          <div className={`text-xs font-medium mb-1 flex justify-between items-center p-1 ${today ? 'text-primary-start' : 'text-gray-400'}`}>
            <span className={`w-7 h-7 flex items-center justify-center rounded-full ${today ? 'bg-primary-start text-white shadow-lg shadow-primary-start/40' : ''}`}>{day}</span>
            {today && <span className="hidden sm:inline text-[9px] font-bold uppercase tracking-wider opacity-80">{t('calendar.today')}</span>}
          </div>
          <div className="flex-1 w-full space-y-1 overflow-visible relative">
            {dayEvents.slice(0, 4).map(event => {
              const style = getEventStyle(event.event_type);
              const eventId = getEventId(event);
              const isHovered = hoveredEventId === eventId;
              const isShared = (event as any).is_public === true || (event.notes && event.notes.includes("CLIENT_VISIBLE"));

              return (
                <div key={eventId} className="relative w-full">
                    <button 
                        onClick={(e) => { e.stopPropagation(); setSelectedEvent(event); }}
                        onMouseEnter={() => setHoveredEventId(eventId)}
                        onMouseLeave={() => setHoveredEventId(null)}
                        className={`w-full text-left px-2 py-1 rounded-md border flex items-center gap-1.5 transition-all duration-200 shadow-sm ${style.bg} ${style.border} group-hover:shadow-md ${isHovered ? 'scale-[1.02] z-10 ring-1 ring-white/20' : ''}`}
                    >
                        <div className={`w-1.5 h-1.5 rounded-full ${style.indicator} shadow-[0_0_5px_currentColor]`} />
                        <span className={`text-[10px] font-medium truncate ${style.text} flex-1`}>{event.title}</span>
                        {isShared && <Eye size={8} className="text-emerald-400 ml-auto" />}
                    </button>
                    {/* Tooltip */}
                    <AnimatePresence>
                        {isHovered && (<motion.div initial={{ opacity: 0, scale: 0.9, y: 10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9, y: 5 }} transition={{ duration: 0.15 }} className="absolute left-0 top-full mt-2 z-[999] w-64 glass-high p-3 rounded-xl" style={{ minWidth: '200px' }}><div className="relative z-10"><div className={`text-[10px] font-bold uppercase mb-1.5 flex items-center gap-1.5 ${style.text}`}>{style.icon} {t(`calendar.types.${event.event_type}`)}</div><div className="text-white font-bold text-sm mb-1 line-clamp-2 leading-tight">{event.title}</div><div className="text-gray-400 text-xs mb-2 line-clamp-2">{event.description || t('general.notAvailable')}</div><div className="pt-2 border-t border-white/10 text-gray-500 text-[10px] flex justify-between font-mono"><span>{format(parseISO(event.start_date), 'HH:mm')}</span><span className={`${event.priority === 'CRITICAL' ? 'text-rose-500 font-bold' : 'text-gray-400'}`}>{t(`calendar.priorities.${event.priority}`)}</span></div></div></motion.div>)}
                    </AnimatePresence>
                </div>
              );
            })}
            {dayEvents.length > 4 && (<div className="text-[10px] text-gray-500/80 px-1 text-center font-medium hover:text-white transition-colors cursor-pointer">+{dayEvents.length - 4} {t('calendar.moreEvents')}</div>)}
          </div>
        </div>
      );
    }
    const totalCells = Math.ceil(days.length / 7) * 7;
    while(days.length < totalCells) days.push(<div key={`empty-end-${days.length}`} className={`${cellClass} bg-black/10`} />);
    const weekStarts = startOfWeek(new Date(), { weekStartsOn });
    const weekDays = Array.from({ length: 7 }, (_, i) => format(addDays(weekStarts, i), 'EEEEEE', { locale: currentLocale }));
    
    // PHOENIX: Added 'flex-1' to allow vertical expansion
    return (<div className="glass-panel rounded-3xl shadow-2xl overflow-hidden flex flex-col flex-1 h-full"><div className="grid grid-cols-7 bg-white/5 border-b border-white/10 shrink-0">{weekDays.map(day => <div key={day} className="py-3 text-center text-xs font-bold text-gray-400 uppercase tracking-wider">{day}</div>)}</div><div className="grid grid-cols-7 border-l border-t border-white/5 flex-1 auto-rows-fr">{days}</div></div>);
  };
  
  const monthName = format(currentDate, 'LLLL yyyy', { locale: currentLocale });
  if (loading) return <div className="flex items-center justify-center h-screen"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div></div>;

  return (
    <div className="min-h-screen font-sans text-gray-100 flex flex-col">
        <div id="react-datepicker-portal"></div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 flex flex-col">
            <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-6 mb-8 shrink-0">
                <div><h1 className="text-3xl font-bold text-white flex items-center gap-3"><CalendarIcon className="text-primary-start h-8 w-8" /><span className="capitalize">{monthName}</span></h1><p className="text-gray-400 mt-1 ml-1">{t('calendar.pageSubtitle')}</p></div>
                <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto"><div className="flex items-center bg-white/5 border border-white/10 rounded-xl p-1"><button onClick={() => navigateMonth('prev')} className="p-2 hover:bg-white/10 rounded-lg transition-colors"><ChevronLeft size={20} /></button><button onClick={() => setCurrentDate(new Date())} className="px-4 text-sm font-medium hover:text-white transition-colors">{t('calendar.today')}</button><button onClick={() => navigateMonth('next')} className="p-2 hover:bg-white/10 rounded-lg transition-colors"><ChevronRight size={20} /></button></div><button onClick={() => setIsCreateModalOpen(true)} className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-primary-start to-primary-end hover:shadow-lg hover:shadow-primary-start/20 text-white rounded-xl font-bold transition-all"><Plus size={18} /> <span className="hidden sm:inline">{t('calendar.newEvent')}</span></button></div>
            </div>
            {error && <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-4 mb-6 flex items-center space-x-3 shrink-0"><AlertCircle className="h-5 w-5 text-red-400" /><span className="text-red-200 text-sm">{error}</span></div>}
            
            {/* PHOENIX SYMMETRY FIX: items-stretch to force equal height */}
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-8 flex-1 items-stretch">
                <div className="xl:col-span-3 flex flex-col gap-6 h-full">
                    <div className="flex flex-col sm:flex-row gap-3 shrink-0">
                        <div className="relative flex-grow">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                            <input type="text" placeholder={t('calendar.searchPlaceholder')} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="glass-input w-full pl-10 pr-4 py-2.5 rounded-xl text-sm" />
                        </div>
                        <div className="flex gap-2">
                            <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="glass-input px-3 py-2.5 rounded-xl text-sm cursor-pointer">
                                <option value="ALL" className="bg-gray-900 text-gray-200">{t('calendar.allTypes')}</option>
                                {Object.keys(t('calendar.types', { returnObjects: true })).map(key => <option key={key} value={key} className="bg-gray-900 text-gray-200">{t(`calendar.types.${key}`)}</option>)}
                            </select>
                            <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)} className="glass-input px-3 py-2.5 rounded-xl text-sm cursor-pointer">
                                <option value="ALL" className="bg-gray-900 text-gray-200">{t('calendar.allPriorities')}</option>
                                {Object.keys(t('calendar.priorities', { returnObjects: true })).map(key => <option key={key} value={key} className="bg-gray-900 text-gray-200">{t(`calendar.priorities.${key}`)}</option>)}
                            </select>
                            <div className="flex bg-white/5 p-1 rounded-xl border border-white/10">
                                <button onClick={() => setViewMode('month')} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${viewMode === 'month' ? 'bg-white text-black shadow' : 'text-gray-400 hover:text-white'}`}>{t('calendar.month')}</button>
                                <button onClick={() => setViewMode('list')} className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${viewMode === 'list' ? 'bg-white text-black shadow' : 'text-gray-400 hover:text-white'}`}>{t('calendar.list')}</button>
                            </div>
                        </div>
                    </div>
                    {/* Calendar Container fills remaining space */}
                    {viewMode === 'month' ? renderMonthView() : renderListView()}
                </div>
                
                {/* Side Panels - Flex Col to allow expansion */}
                <div className="xl:col-span-1 flex flex-col gap-6 h-full">
                    <div className="glass-panel p-6 rounded-3xl relative overflow-hidden flex-1 flex flex-col">
                        <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none"><Bell size={64} /></div>
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2 shrink-0"><Bell className="text-yellow-400" size={18} />{t('calendar.upcomingAlerts')}</h3>
                        <div className="space-y-3 flex-1 overflow-y-auto custom-scrollbar">
                            {upcomingAlerts.length === 0 ? (<div className="h-full flex items-center justify-center"><p className="text-gray-500 text-sm text-center">{t('calendar.noUpcomingEvents')}</p></div>) : (upcomingAlerts.map(ev => { const style = getEventStyle(ev.event_type); return (<button key={getEventId(ev)} onClick={() => setSelectedEvent(ev)} className="w-full flex gap-3 items-start group text-left p-2 rounded-lg hover:bg-white/5 transition-colors"><div className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${style.indicator}`} /><div className="min-w-0"><h4 className="text-sm font-medium text-gray-200 group-hover:text-primary-start transition-colors truncate">{ev.title}</h4><p className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">{format(parseISO(ev.start_date), 'dd MMM')} <span className={`text-[9px] px-1.5 py-0.5 rounded border ${style.border} ${style.bg} ${style.text} uppercase`}>{t(`calendar.types.${ev.event_type}`)}</span></p></div></button>)}))}
                        </div>
                    </div>
                    <div className="glass-panel p-6 rounded-3xl shrink-0">
                        <h3 className="text-lg font-bold text-white mb-4">{t('calendar.eventTypes')}</h3>
                        <div className="space-y-2">
                            {Object.keys(t('calendar.types', { returnObjects: true })).map((key) => { const style = getEventStyle(key); return (<div key={key} className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors cursor-pointer" onClick={() => setFilterType(filterType === key ? 'ALL' : key)}><div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${style.border} ${style.bg} ${style.text}`}>{style.icon}</div><span className={`text-sm ${filterType === key ? 'text-white font-bold' : 'text-gray-400'}`}>{t(`calendar.types.${key}`)}</span>{filterType === key && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-white animate-pulse" />}</div>)})}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {selectedEvent && <EventDetailModal event={selectedEvent} onClose={() => setSelectedEvent(null)} onUpdate={loadData} />}
        {isCreateModalOpen && <CreateEventModal cases={cases} existingEvents={events} onClose={() => setIsCreateModalOpen(false)} onCreate={loadData} />}
        <DayEventsModal isOpen={isDayModalOpen} onClose={() => setIsDayModalOpen(false)} date={selectedDateForModal} events={selectedDayEvents} t={t} onAddEvent={() => { setIsDayModalOpen(false); setIsCreateModalOpen(true); }} />
    </div>
  );
};

export default CalendarPage;