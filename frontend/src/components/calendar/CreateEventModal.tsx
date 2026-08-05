// FILE: src/components/calendar/CreateEventModal.tsx
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { isSameDay, parseISO } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { ShieldAlert, Eye, EyeOff, ChevronDown, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import * as ReactDatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import '../../styles/DatePicker.css';

import { CalendarEvent, Case, CalendarEventCreateRequest } from '../../data/types';
import { apiService } from '../../services/api';
import { useLockBodyScroll } from '../../hooks/useLockBodyScroll';
import { localeMap } from '../../utils/calendarHelpers';

const DatePicker = (ReactDatePicker as any).default;

interface CreateEventModalProps {
  cases: Case[];
  existingEvents: CalendarEvent[];
  onClose: () => void;
  onCreate: () => void;
}

export const CreateEventModal: React.FC<CreateEventModalProps> = ({ cases, existingEvents, onClose, onCreate }) => {
  const { t, i18n } = useTranslation();
  const currentLocale = localeMap[i18n.language] || enUS;
  const [isCreating, setIsCreating] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [eventDate, setEventDate] = useState<Date | null>(null);
  const [conflictWarning, setConflictWarning] = useState<string | null>(null);
  const [isPublic, setIsPublic] = useState(false);
  const [formData, setFormData] = useState<
    Omit<CalendarEventCreateRequest, 'attendees' | 'start_date' | 'end_date'> & { attendees: string }
  >({
    case_id: '',
    title: '',
    description: '',
    event_type: 'MEETING',
    location: '',
    attendees: '',
    is_all_day: true,
    priority: 'MEDIUM',
    notes: '',
  });

  useLockBodyScroll(true);

  useEffect(() => {
    if (!eventDate) {
      setConflictWarning(null);
      return;
    }
    const hasConflict = existingEvents.some((ev) => isSameDay(parseISO(ev.start_date), eventDate));
    setConflictWarning(hasConflict ? (t('calendar.conflictWarning', 'Kujdes: Keni ngjarje të tjera.') as string) : null);
  }, [eventDate, existingEvents, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventDate) return;
    setIsCreating(true);
    try {
      const cleanDate = new Date(Date.UTC(eventDate.getFullYear(), eventDate.getMonth(), eventDate.getDate(), 12, 0, 0)).toISOString();
      const payload: any = {
        ...formData,
        start_date: cleanDate,
        end_date: cleanDate,
        attendees: formData.attendees ? formData.attendees.split(',').map((a) => a.trim()) : [],
        is_public: isPublic,
        category: 'AGENDA',
        notes: isPublic ? formData.notes + '\n[CLIENT_VISIBLE]' : formData.notes,
      };
      await apiService.createCalendarEvent(payload);
      onCreate();
      onClose();
    } catch (error: any) {
      alert(error.response?.data?.message || 'Dështoi krijimi.');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-3 z-[2000]">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel w-full max-w-lg max-h-[90vh] p-6 sm:p-8 rounded-[2.5rem] flex flex-col shadow-2xl border border-main bg-canvas overflow-hidden"
      >
        <div className="flex justify-between items-center mb-6 shrink-0">
          <h2 className="text-xl font-bold text-text-primary uppercase tracking-wider">{t('calendar.createModal.title')}</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex items-center justify-center w-11 h-11 rounded-xl text-text-muted hover:text-text-primary hover:bg-hover transition-colors focus:outline-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>
        {conflictWarning && (
          <div className="bg-warning-start/15 border border-warning-start/20 rounded-xl p-4 mb-4 flex items-center gap-4 animate-pulse">
            <ShieldAlert className="text-warning-start h-5 w-5 shrink-0" />
            <span className="text-warning-start text-xs font-bold">{conflictWarning}</span>
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex flex-col flex-grow overflow-hidden">
          <div className="overflow-y-auto pr-2 space-y-4 flex-grow custom-finance-scroll">
            <div className="space-y-1.5">
              <label className="block text-[10px] font-bold text-primary-start uppercase tracking-widest ml-1">
                {t('calendar.createModal.relatedCase')}
              </label>
              <select
                required
                value={formData.case_id}
                onChange={(e) => setFormData((prev) => ({ ...prev, case_id: e.target.value }))}
                className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/45"
              >
                <option value="" className="bg-canvas">Zgjidhni rastin...</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id} className="bg-canvas">
                    {c.title || c.case_number}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="block text-[10px] font-bold text-primary-start uppercase tracking-widest ml-1">
                {t('calendar.createModal.eventTitle')}
              </label>
              <input
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-[10px] font-bold text-primary-start uppercase tracking-widest ml-1">Lloji</label>
                <select
                  value={formData.event_type}
                  onChange={(e) => setFormData((prev) => ({ ...prev, event_type: e.target.value as CalendarEvent['event_type'] }))}
                  className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/45"
                >
                  {Object.keys(t('calendar.types', { returnObjects: true }) as object).map((key) => (
                    <option key={key} value={key} className="bg-canvas">
                      {t(`calendar.types.${key}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="block text-[10px] font-bold text-primary-start uppercase tracking-widest ml-1">Prioriteti</label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData((prev) => ({ ...prev, priority: e.target.value as CalendarEvent['priority'] }))}
                  className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/45"
                >
                  {Object.keys(t('calendar.priorities', { returnObjects: true }) as object).map((key) => (
                    <option key={key} value={key} className="bg-canvas">
                      {t(`calendar.priorities.${key}`)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="block text-[10px] font-bold text-primary-start uppercase tracking-widest ml-1">Data</label>
              <DatePicker
                selected={eventDate}
                onChange={(date: Date | null) => setEventDate(date)}
                locale={currentLocale}
                dateFormat="dd.MM.yyyy"
                placeholderText="Klikoni për datën"
                className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all"
                portalId="react-datepicker-portal"
                required
              />
            </div>

            <div
              className="bg-surface border border-main rounded-2xl p-4 flex items-center justify-between cursor-pointer"
              onClick={() => setIsPublic(!isPublic)}
            >
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-xl transition-colors ${isPublic ? 'bg-primary-start text-white animate-pulse' : 'bg-canvas text-text-secondary'}`}>
                  {isPublic ? <Eye size={18} /> : <EyeOff size={18} />}
                </div>
                <div>
                  <h4 className={`text-sm font-bold ${isPublic ? 'text-primary-start' : 'text-text-secondary'}`}>{isPublic ? 'Publike' : 'Private'}</h4>
                  <p className="text-[10px] text-text-secondary/50 uppercase tracking-widest">Për klientin</p>
                </div>
              </div>
              <div className={`w-10 h-5 rounded-full relative transition-colors ${isPublic ? 'bg-primary-start' : 'bg-surface'}`}>
                <div className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full transition-transform ${isPublic ? 'translate-x-5' : 'translate-x-0'}`} />
              </div>
            </div>

            {!showAdvanced && (
              <button
                type="button"
                onClick={() => setShowAdvanced(true)}
                className="w-full text-[11px] font-bold text-text-secondary uppercase flex items-center justify-center gap-2 py-3 hover:text-text-primary transition-all focus:outline-none"
              >
                <ChevronDown size={14} /> Detaje Shtesë
              </button>
            )}

            {showAdvanced && (
              <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4 pt-2">
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-bold text-primary-start uppercase tracking-widest ml-1">Përshkrimi</label>
                  <textarea
                    rows={3}
                    value={formData.description}
                    onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                    className="w-full p-4 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all resize-none"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-[10px] font-bold text-primary-start uppercase tracking-widest ml-1">Vendi</label>
                  <input
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData((prev) => ({ ...prev, location: e.target.value }))}
                    className="w-full px-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start transition-all"
                  />
                </div>
              </motion.div>
            )}
          </div>

          <div className="flex flex-col-reverse sm:flex-row gap-3 pt-6 mt-auto border-t border-main">
            <button
              type="button"
              onClick={onClose}
              className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-all focus:outline-none"
            >
              Anulo
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="w-full sm:w-auto px-6 h-11 rounded-xl font-bold text-sm tracking-widest uppercase shadow-lg bg-primary-start hover:bg-opacity-95 text-white flex items-center justify-center gap-2 focus:outline-none shadow-primary-start/15 disabled:opacity-50"
            >
              {isCreating ? <Loader2 className="animate-spin h-5 w-5 mx-auto" /> : 'Krijo'}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};