// FILE: /advocatus-frontend/src/pages/CalendarPage.tsx
// PHOENIX PROTOCOL - DEFINITIVE VERSION WITH TYPE FIXES
// FIXES APPLIED:
// 1. ✅ Added Locale import from date-fns
// 2. ✅ Removed unused formatFullDateTime function
// 3. ✅ Fixed all TypeScript type errors

import React, { useState, useEffect } from 'react';
import { CalendarEvent, Case, CalendarEventCreateRequest } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
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
  Locale // ✅ FIX: Added Locale import
} from 'date-fns';
import { sq } from 'date-fns/locale';
import {
  Calendar as CalendarIcon, Clock, MapPin, Users, AlertCircle, Plus, ChevronLeft, ChevronRight,
  Search, FileText, Gavel, Briefcase, AlertTriangle, XCircle, Bell, ChevronDown
} from 'lucide-react';

import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import '../styles/DatePicker.css';

const DatePicker = (ReactDatePicker as any).default;

// ✅ FIX: Proper locale mapping with Locale type
const localeMap: { [key: string]: Locale } = { 
  al: sq,  // Map 'al' (Albanian) to 'sq' (date-fns locale)
  en: undefined as unknown as Locale // English uses default locale
};

interface EventDetailModalProps { event: CalendarEvent; onClose: () => void; onUpdate: () => void; }
interface CreateEventModalProps { cases: Case[]; onClose: () => void; onCreate: () => void; }
type ViewMode = 'month' | 'list';

const getEventTypeIcon = (type: CalendarEvent['event_type']) => {
    switch (type) {
      case 'DEADLINE': return <AlertTriangle className="h-4 w-4" />;
      case 'HEARING': return <Gavel className="h-4 w-4" />;
      case 'MEETING': return <Users className="h-4 w-4" />;
      case 'FILING': return <FileText className="h-4 w-4" />;
      case 'COURT_DATE': return <Gavel className="h-4 w-4" />;
      case 'CONSULTATION': return <Briefcase className="h-4 w-4" />;
      default: return <CalendarIcon className="h-4 w-4" />;
    }
};

const getEventTypeColor = (eventType: CalendarEvent['event_type']) => {
    switch (eventType) {
      case 'DEADLINE': return 'text-red-300 bg-red-900/20 border-red-600';
      case 'HEARING': return 'text-purple-300 bg-purple-900/20 border-purple-600';
      case 'MEETING': return 'text-blue-300 bg-blue-900/20 border-blue-600';
      case 'FILING': return 'text-yellow-300 bg-yellow-900/20 border-yellow-600';
      case 'COURT_DATE': return 'text-orange-300 bg-orange-900/20 border-orange-600';
      case 'CONSULTATION': return 'text-green-300 bg-green-900/20 border-green-600';
      default: return 'text-gray-300 bg-gray-900/20 border-gray-600';
    }
};

const getPriorityColor = (priorityValue: CalendarEvent['priority']) => {
    switch (priorityValue) {
      case 'CRITICAL': return 'text-red-300 bg-red-900/20 border-red-600';
      case 'HIGH': return 'text-orange-300 bg-orange-900/20 border-orange-600';
      case 'MEDIUM': return 'text-yellow-300 bg-yellow-900/20 border-yellow-600';
      case 'LOW': return 'text-green-300 bg-green-900/20 border-green-600';
      default: return 'text-gray-300 bg-gray-900/20 border-gray-600';
    }
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

  // ✅ FIX: Proper locale handling with Albanian support
  const currentLocale = localeMap[i18n.language as keyof typeof localeMap] || undefined;

  useEffect(() => { 
    console.log('[Calendar] Loading data with locale:', i18n.language);
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
      console.log('[Calendar] Data loaded successfully:', { 
        events: eventsData.length, 
        cases: casesData.length 
      });
    } catch (error: any) {
      console.error('[Calendar] Failed to load data:', error);
      setError(error.response?.data?.message || error.message || t('calendar.loadFailure'));
    } finally { 
      setLoading(false); 
    }
  };

  // ✅ FIX: Removed unused formatFullDateTime function - it's now in EventDetailModal
  const formatTime = (dateString: string) => 
    format(parseISO(dateString), 'HH:mm', { locale: currentLocale });

  const formatDateTime = (dateString: string) => 
    format(parseISO(dateString), 'dd.MM.yyyy HH:mm', { locale: currentLocale });

  const navigateMonth = (direction: 'prev' | 'next') => {
    setCurrentDate(direction === 'prev' ? subMonths(currentDate, 1) : addMonths(currentDate, 1));
  };

  const filteredEvents = events.filter(event => {
    const searchContent = `${event.title} ${event.description || ''} ${event.location || ''}`.toLowerCase();
    return searchContent.includes(searchTerm.toLowerCase()) && 
           (filterType === 'ALL' || event.event_type === filterType) && 
           (filterPriority === 'ALL' || event.priority === filterPriority);
  });

  const upcomingEvents = filteredEvents
    .filter(event => new Date(event.start_date) >= new Date())
    .sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
    .slice(0, 5);

  const renderMonthView = () => {
    const monthStart = startOfMonth(currentDate);
    const daysInMonth = getDaysInMonth(currentDate);
    const weekStartsOn = currentLocale?.options?.weekStartsOn ?? 1; // Monday as default start
    const firstDayOfMonth = getDay(monthStart);
    
    // Calculate starting day index based on locale week start
    const startingDayIndex = (firstDayOfMonth - weekStartsOn + 7) % 7;

    const days = Array.from({ length: startingDayIndex }, (_, i) => 
      <div key={`empty-${i}`} className="min-h-[120px] border border-glass-edge/50 bg-background-dark/50"></div>
    );

    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), day);
      const dayEvents = filteredEvents.filter(event => isSameDay(parseISO(event.start_date), date));
      const today = isTodayFns(date);
      
      days.push(
        <div key={day} className={`min-h-[120px] border border-glass-edge/50 p-2 bg-background-light/30 ${today ? 'ring-2 ring-primary-start' : ''}`}>
          <div className={`text-sm font-medium mb-2 ${today ? 'text-primary-start' : 'text-text-primary'}`}>
            {day}
            {today && <span className="ml-2 text-xs">({t('calendar.today')})</span>}
          </div>
          <div className="space-y-1">
            {dayEvents.slice(0, 3).map(event => (
              <button 
                key={event.id} 
                onClick={() => setSelectedEvent(event)} 
                className={`w-full text-left px-2 py-1 rounded text-xs truncate border ${getEventTypeColor(event.event_type)}`}
              >
                {formatTime(event.start_date)} - {event.title}
              </button>
            ))}
            {dayEvents.length > 3 && (
              <div className="text-xs text-text-secondary px-2">
                {t('calendar.moreEvents', { count: dayEvents.length - 3 })}
              </div>
            )}
          </div>
        </div>
      );
    }

    const totalCells = Math.ceil(days.length / 7) * 7;
    while(days.length < totalCells) {
        days.push(
          <div 
            key={`empty-end-${days.length}`} 
            className="min-h-[120px] border border-glass-edge/50 bg-background-dark/50"
          ></div>
        );
    }

    // Generate week days based on current locale
    const weekStarts = startOfWeek(new Date(), { weekStartsOn });
    const weekDays = Array.from({ length: 7 }, (_, i) => 
      format(addDays(weekStarts, i), 'EEEEEE', { locale: currentLocale })
    );

    return (
        <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge rounded-2xl overflow-hidden shadow-xl">
            <div className="grid grid-cols-7 bg-background-dark/50">
                {weekDays.map(day => (
                  <div key={day} className="p-3 text-center text-sm font-semibold text-text-primary border-r border-glass-edge/50 last:border-r-0">
                    {day}
                  </div>
                ))}
            </div>
            <div className="grid grid-cols-7">{days}</div>
        </div>
    );
  };

  // Format month name with proper Albanian locale
  const monthName = format(currentDate, 'LLLL yyyy', { locale: currentLocale });

  if (loading) { 
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-start"></div>
      </div>
    ); 
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-text-primary">
        <div id="react-datepicker-portal"></div>
        
        {/* Header Section */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-text-primary mb-2">
                {t('calendar.pageTitle')}
              </h1>
              <p className="text-text-secondary">{t('calendar.pageSubtitle')}</p>
            </div>
            <div className="mt-4 lg:mt-0">
              <button 
                onClick={() => setIsCreateModalOpen(true)} 
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-xl shadow-lg text-sm font-medium text-white bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 transition-opacity duration-200"
              >
                <Plus className="h-4 w-4 mr-2" />
                {t('calendar.newEvent')}
              </button>
            </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-900/50 border border-red-600 rounded-2xl p-4 mb-6 flex items-center space-x-2">
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {/* Main Calendar Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            <div className="lg:col-span-3 space-y-6">
                {/* Calendar Controls */}
                <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge p-4 rounded-2xl shadow-xl">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
                        <div className="flex items-center space-x-4">
                            <button 
                              onClick={() => navigateMonth('prev')} 
                              className="p-2 text-text-secondary hover:text-white hover:bg-background-dark/50 rounded-lg transition-colors"
                            >
                              <ChevronLeft className="h-5 w-5" />
                            </button>
                            <h2 className="text-xl font-semibold text-text-primary capitalize">
                              {monthName}
                            </h2>
                            <button 
                              onClick={() => navigateMonth('next')} 
                              className="p-2 text-text-secondary hover:text-white hover:bg-background-dark/50 rounded-lg transition-colors"
                            >
                              <ChevronRight className="h-5 w-5" />
                            </button>
                            <button 
                              onClick={() => setCurrentDate(new Date())} 
                              className="px-3 py-1 text-sm text-text-secondary hover:text-white hover:bg-background-dark/50 rounded-md transition-colors border border-glass-edge"
                            >
                              {t('calendar.today')}
                            </button>
                        </div>
                        <div className="flex items-center space-x-2 bg-background-dark/50 p-1 rounded-xl border border-glass-edge">
                            <button 
                              onClick={() => setViewMode('month')} 
                              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                                viewMode === 'month' ? 'bg-primary-start text-white shadow' : 'text-text-secondary hover:text-white'
                              }`}
                            >
                              {t('calendar.month')}
                            </button>
                            <button 
                              onClick={() => setViewMode('list')} 
                              className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
                                viewMode === 'list' ? 'bg-primary-start text-white shadow' : 'text-text-secondary hover:text-white'
                              }`}
                            >
                              {t('calendar.list')}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Search and Filters */}
                <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
                    <div className="flex-1 relative">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-text-secondary" />
                        <input 
                          type="text" 
                          placeholder={t('calendar.searchPlaceholder')} 
                          value={searchTerm} 
                          onChange={(e) => setSearchTerm(e.target.value)} 
                          className="block w-full pl-10 pr-3 py-2 border border-glass-edge rounded-xl bg-background-dark/50 text-white placeholder-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-start" 
                        />
                    </div>
                    <select 
                      value={filterType} 
                      onChange={(e) => setFilterType(e.target.value)} 
                      className="px-3 py-2 border border-glass-edge rounded-xl bg-background-dark/50 text-white focus:outline-none focus:ring-2 focus:ring-primary-start"
                    >
                      <option value="ALL">{t('calendar.allTypes')}</option>
                      {Object.keys(t('calendar.types', { returnObjects: true })).map(key => (
                        <option key={key} value={key}>
                          {t(`calendar.types.${key}`)}
                        </option>
                      ))}
                    </select>
                    <select 
                      value={filterPriority} 
                      onChange={(e) => setFilterPriority(e.target.value)} 
                      className="px-3 py-2 border border-glass-edge rounded-xl bg-background-dark/50 text-white focus:outline-none focus:ring-2 focus:ring-primary-start"
                    >
                      <option value="ALL">{t('calendar.allPriorities')}</option>
                      {Object.keys(t('calendar.priorities', { returnObjects: true })).map(key => (
                        <option key={key} value={key}>
                          {t(`calendar.priorities.${key}`)}
                        </option>
                      ))}
                    </select>
                </div>

                {/* Calendar View */}
                {viewMode === 'month' && renderMonthView()}
            </div>

            {/* Sidebar */}
            <div className="lg:col-span-1 space-y-6">
                {/* Upcoming Events */}
                <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge p-6 rounded-2xl shadow-xl">
                    <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center">
                        <Bell className="h-5 w-5 mr-2 text-yellow-400" />
                        {t('calendar.upcomingEvents')}
                    </h3>
                    {upcomingEvents.length === 0 ? (
                      <p className="text-text-secondary text-sm">{t('calendar.noUpcomingEvents')}</p>
                    ) : (
                      <div className="space-y-3">
                        {upcomingEvents.map(event => (
                          <button 
                            key={event.id} 
                            onClick={() => setSelectedEvent(event)} 
                            className="w-full text-left p-3 bg-background-dark/50 hover:bg-background-dark/80 rounded-lg transition-colors border border-glass-edge/50"
                          >
                            <div className="flex items-start space-x-2">
                                <div className={`p-1 rounded border ${getEventTypeColor(event.event_type)}`}>
                                  {getEventTypeIcon(event.event_type)}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-white truncate">
                                      {event.title}
                                    </p>
                                    <p className="text-xs text-text-secondary mt-1">
                                      {formatDateTime(event.start_date)}
                                    </p>
                                </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                </div>

                {/* Event Types Legend */}
                <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge p-6 rounded-2xl shadow-xl">
                    <h3 className="text-lg font-semibold text-text-primary mb-4">
                      {t('calendar.eventTypes')}
                    </h3>
                    <div className="space-y-2">
                      {Object.entries(t('calendar.types', { returnObjects: true })).map(([key, label]) => (
                        <div key={key} className="flex items-center space-x-2">
                          <span className={`px-2 py-1 rounded text-xs border ${getEventTypeColor(key as CalendarEvent['event_type'])}`}>
                            {getEventTypeIcon(key as CalendarEvent['event_type'])}
                          </span>
                          <span className="text-sm text-text-secondary">{label as string}</span>
                        </div>
                      ))}
                    </div>
                </div>
            </div>
        </div>

        {/* Modals */}
        {selectedEvent && (
          <EventDetailModal 
            event={selectedEvent} 
            onClose={() => setSelectedEvent(null)} 
            onUpdate={loadData} 
          />
        )}
        {isCreateModalOpen && (
          <CreateEventModal 
            cases={cases} 
            onClose={() => setIsCreateModalOpen(false)} 
            onCreate={loadData} 
          />
        )}
    </div>
  );
};

// Event Detail Modal Component
const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose, onUpdate }) => {
    const { t, i18n } = useTranslation();
    const currentLocale = localeMap[i18n.language as keyof typeof localeMap] || undefined;
    const [isDeleting, setIsDeleting] = useState(false);

    // ✅ FIX: Moved formatFullDateTime inside the modal where it's used
    const formatFullDateTime = (dateString: string) => 
      format(parseISO(dateString), 'dd MMMM yyyy, HH:mm', { locale: currentLocale });

    const handleDelete = async () => { 
      if (!window.confirm(t('calendar.detailModal.deleteConfirm'))) return; 
      setIsDeleting(true); 
      try { 
        await apiService.deleteCalendarEvent(event.id); 
        onUpdate(); 
        onClose(); 
      } catch (error) { 
        alert(t('calendar.detailModal.deleteFailed')); 
      } finally { 
        setIsDeleting(false); 
      } 
    };

    const getDetailEventTypeColor = (type: CalendarEvent['event_type']) => {
      switch (type) {
        case 'DEADLINE': return 'from-red-600 to-red-500';
        case 'HEARING': return 'from-purple-600 to-purple-500';
        case 'MEETING': return 'from-blue-600 to-blue-500';
        case 'FILING': return 'from-yellow-600 to-yellow-500';
        case 'COURT_DATE': return 'from-orange-600 to-orange-500';
        case 'CONSULTATION': return 'from-green-600 to-green-500';
        default: return 'from-gray-600 to-gray-500';
      }
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-background-dark/80 backdrop-blur-xl border border-glass-edge rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
                {/* Header */}
                <div className="flex items-start justify-between mb-6">
                  <div className="flex items-start space-x-4">
                    <div className={`bg-gradient-to-br ${getDetailEventTypeColor(event.event_type)} p-3 rounded-xl text-white`}>
                      {getEventTypeIcon(event.event_type)}
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold text-white mb-1">{event.title}</h2>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs px-2 py-1 rounded-full bg-background-light/50 text-text-secondary border border-glass-edge/50">
                          {t(`calendar.types.${event.event_type}`)}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded-full border ${getPriorityColor(event.priority)}`}>
                          {t(`calendar.priorities.${event.priority}`)}
                        </span>
                      </div>
                    </div>
                  </div>
                  <button onClick={onClose} className="text-text-secondary hover:text-white transition-colors">
                    <XCircle className="h-6 w-6" />
                  </button>
                </div>

                {/* Event Details */}
                <div className="space-y-4">
                  {event.description && (
                    <div>
                      <h3 className="text-sm font-medium text-text-secondary mb-1">
                        {t('calendar.detailModal.description')}
                      </h3>
                      <p className="text-white">{event.description}</p>
                    </div>
                  )}
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <h3 className="text-sm font-medium text-text-secondary mb-1">
                        {t('calendar.detailModal.startDate')}
                      </h3>
                      <div className="flex items-center text-white">
                        <Clock className="h-4 w-4 mr-2 text-text-secondary" />
                        {formatFullDateTime(event.start_date)}
                      </div>
                    </div>
                    {event.end_date && (
                      <div>
                        <h3 className="text-sm font-medium text-text-secondary mb-1">
                          {t('calendar.detailModal.endDate')}
                        </h3>
                        <div className="flex items-center text-white">
                          <Clock className="h-4 w-4 mr-2 text-text-secondary" />
                          {formatFullDateTime(event.end_date)}
                        </div>
                      </div>
                    )}
                  </div>

                  {event.location && (
                    <div>
                      <h3 className="text-sm font-medium text-text-secondary mb-1">
                        {t('calendar.detailModal.location')}
                      </h3>
                      <div className="flex items-center text-white">
                        <MapPin className="h-4 w-4 mr-2 text-text-secondary" />
                        {event.location}
                      </div>
                    </div>
                  )}

                  {event.attendees && event.attendees.length > 0 && (
                    <div>
                      <h3 className="text-sm font-medium text-text-secondary mb-1">
                        {t('calendar.detailModal.attendees')}
                      </h3>
                      <div className="flex items-center text-white">
                        <Users className="h-4 w-4 mr-2 text-text-secondary" />
                        {event.attendees.join(', ')}
                      </div>
                    </div>
                  )}

                  {event.notes && (
                    <div>
                      <h3 className="text-sm font-medium text-text-secondary mb-1">
                        {t('calendar.detailModal.notes')}
                      </h3>
                      <p className="text-white bg-background-light/50 rounded-lg p-3 border border-glass-edge/50">
                        {event.notes}
                      </p>
                    </div>
                  )}
                </div>

                {/* Action Buttons */}
                <div className="flex space-x-3 mt-6 pt-6 border-t border-glass-edge/50">
                  <button 
                    onClick={onClose} 
                    className="flex-1 px-4 py-2 border border-glass-edge rounded-md text-text-secondary hover:bg-background-light/50 transition duration-200"
                  >
                    {t('calendar.detailModal.close')}
                  </button>
                  <button 
                    onClick={handleDelete} 
                    disabled={isDeleting}
                    className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-md transition duration-200"
                  >
                    {isDeleting ? t('calendar.detailModal.deleting') : t('calendar.detailModal.delete')}
                  </button>
                </div>
            </div>
        </div>
    );
};

// Create Event Modal Component (unchanged, just for completeness)
const CreateEventModal: React.FC<CreateEventModalProps> = ({ cases, onClose, onCreate }) => {
  const { t, i18n } = useTranslation();
  const currentLocale = localeMap[i18n.language as keyof typeof localeMap] || undefined;
  const [isCreating, setIsCreating] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [eventDate, setEventDate] = useState<Date | null>(null);

  const [formData, setFormData] = useState<Omit<CalendarEventCreateRequest, 'attendees' | 'start_date' | 'end_date'> & { attendees: string }>({
    case_id: '', 
    title: '', 
    description: '', 
    event_type: 'MEETING', 
    location: '', 
    attendees: '', 
    is_all_day: false, 
    priority: 'MEDIUM', 
    notes: ''
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventDate) {
      alert(t('calendar.createModal.dateTimePlaceholder'));
      return;
    }
    
    setIsCreating(true);
    try {
      const payload: CalendarEventCreateRequest = {
        ...formData,
        start_date: eventDate.toISOString(),
        end_date: eventDate.toISOString(),
        attendees: formData.attendees ? formData.attendees.split(',').map(a => a.trim()) : [],
      };
      
      await apiService.createCalendarEvent(payload);
      onCreate();
      onClose();
    } catch (error: any) {
      alert(error.response?.data?.message || t('calendar.createModal.createFailed'));
    } finally { 
      setIsCreating(false); 
    }
  };

  const formElementClasses = "block w-full px-3 py-2 border border-glass-edge rounded-md bg-background-light/50 text-white placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-start";

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-background-dark/80 backdrop-blur-xl border border-glass-edge rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl">
        <h2 className="text-2xl font-bold text-white mb-6">{t('calendar.createModal.title')}</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Form content remains the same as previous version */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t('calendar.createModal.relatedCase')}
            </label>
            <select 
              required 
              value={formData.case_id} 
              onChange={(e) => setFormData(prev => ({ ...prev, case_id: e.target.value }))} 
              className={formElementClasses}
            >
              <option value="">{t('calendar.createModal.selectCase')}</option>
              {cases.map(c => (
                <option key={c.id} value={c.id}>{c.case_name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t('calendar.createModal.eventTitle')}
            </label>
            <input 
              type="text" 
              required 
              value={formData.title} 
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))} 
              className={formElementClasses} 
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                {t('calendar.createModal.eventType')}
              </label>
              <select 
                value={formData.event_type} 
                onChange={(e) => setFormData(prev => ({ ...prev, event_type: e.target.value as CalendarEvent['event_type'] }))} 
                className={formElementClasses}
              >
                {Object.keys(t('calendar.types', { returnObjects: true })).map(key => (
                  <option key={key} value={key}>{t(`calendar.types.${key}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                {t('calendar.createModal.priority')}
              </label>
              <select 
                value={formData.priority} 
                onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value as CalendarEvent['priority'] }))} 
                className={formElementClasses}
              >
                {Object.keys(t('calendar.priorities', { returnObjects: true })).map(key => (
                  <option key={key} value={key}>{t(`calendar.priorities.${key}`)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              {t('calendar.createModal.eventDate')}
            </label>
            <DatePicker
              selected={eventDate}
              onChange={(date: Date | null) => setEventDate(date)}
              locale={currentLocale}
              dateFormat="dd.MM.yyyy HH:mm"
              placeholderText={t('calendar.createModal.dateTimePlaceholder')}
              className={formElementClasses}
              portalId="react-datepicker-portal"
              showTimeSelect
              timeIntervals={15}
              required
            />
          </div>

          {!showAdvanced && (
            <div className="pt-2">
              <button 
                type="button" 
                onClick={() => setShowAdvanced(true)} 
                className="text-sm text-primary-start hover:text-primary-end flex items-center"
              >
                <ChevronDown className="h-4 w-4 mr-1" />
                {t('calendar.createModal.addDetails')}
              </button>
            </div>
          )}

          {showAdvanced && (
            <div className="space-y-4 pt-2">
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  {t('calendar.createModal.description')}
                </label>
                <textarea 
                  rows={3} 
                  value={formData.description} 
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))} 
                  className={formElementClasses} 
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  {t('calendar.createModal.location')}
                </label>
                <input 
                  type="text" 
                  value={formData.location} 
                  onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))} 
                  className={formElementClasses} 
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  {t('calendar.createModal.attendees')}
                </label>
                <input 
                  type="text" 
                  value={formData.attendees} 
                  onChange={(e) => setFormData(prev => ({ ...prev, attendees: e.target.value }))} 
                  className={formElementClasses} 
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1">
                  {t('calendar.createModal.notes')}
                </label>
                <textarea 
                  rows={2} 
                  value={formData.notes} 
                  onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))} 
                  className={formElementClasses} 
                />
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-text-secondary">
              {t('calendar.createModal.allDay')}
            </span>
            <button 
              type="button" 
              onClick={() => setFormData(prev => ({...prev, is_all_day: !prev.is_all_day}))} 
              className={`${formData.is_all_day ? 'bg-primary-start' : 'bg-background-light/50'} relative inline-flex h-6 w-11 items-center rounded-full transition-colors`}
            >
              <span className={`${formData.is_all_day ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}/>
            </button>
          </div>

          <div className="flex space-x-3 pt-4">
            <button 
              type="button" 
              onClick={onClose} 
              className="flex-1 px-4 py-2 border border-glass-edge rounded-md text-text-secondary hover:bg-background-light/50 transition duration-200"
            >
              {t('calendar.createModal.cancel')}
            </button>
            <button 
              type="submit" 
              disabled={isCreating} 
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-md transition duration-200"
            >
              {isCreating ? t('calendar.createModal.creating') : t('calendar.createModal.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CalendarPage;