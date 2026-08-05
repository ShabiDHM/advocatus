// FILE: src/components/calendar/EventDetailModal.tsx
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { format, parseISO } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { Clock, MapPin, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CalendarEvent } from '../../data/types';
import { apiService } from '../../services/api';
import { useLockBodyScroll } from '../../hooks/useLockBodyScroll';
import { localeMap, getEventStyle, getEventId } from '../../utils/calendarHelpers';

interface EventDetailModalProps {
  event: CalendarEvent;
  onClose: () => void;
  onUpdate: () => void;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose, onUpdate }) => {
  const { t, i18n } = useTranslation();
  const currentLocale = localeMap[i18n.language] || enUS;
  const [isDeleting, setIsDeleting] = useState(false);

  useLockBodyScroll(true);

  const formatEventDate = (dateString: string) => {
    const date = parseISO(dateString);
    const formatStr = event.is_all_day ? 'dd MMMM yyyy' : 'dd MMMM yyyy, HH:mm';
    return format(date, formatStr, { locale: currentLocale });
  };

  const handleDelete = async () => {
    if (!window.confirm(t('calendar.detailModal.deleteConfirm') as string)) return;
    const eventId = getEventId(event);
    if (!eventId) return;
    setIsDeleting(true);
    try {
      await apiService.deleteCalendarEvent(eventId);
      onUpdate();
      onClose();
    } catch (error: any) {
      alert(error.response?.data?.message || t('calendar.detailModal.deleteFailed'));
    } finally {
      setIsDeleting(false);
    }
  };

  const style = getEventStyle(event.event_type, event.category);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-[2000]">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-panel w-full max-w-2xl p-6 sm:p-8 rounded-[2rem] shadow-2xl border border-main bg-canvas overflow-hidden"
      >
        <div className="flex items-start justify-between mb-8">
          <div className="flex items-start space-x-5">
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center border ${style.border} ${style.bg} ${style.text} shadow-inner`}>
              {React.cloneElement(style.icon as React.ReactElement, { size: 28 })}
            </div>
            <div className="min-w-0">
              <h2 className="text-2xl font-bold text-text-primary mb-2 leading-tight">{event.title}</h2>
              <div className="flex flex-wrap gap-2">
                <span className={`text-[11px] px-3 py-1 rounded-full font-bold uppercase tracking-wider ${style.text} bg-surface border ${style.border}`}>
                  {t(`calendar.types.${event.event_type}`)}
                </span>
                <span className="text-[11px] px-3 py-1 rounded-full border border-main bg-surface text-text-secondary font-bold uppercase tracking-wider">
                  {t(`calendar.priorities.${event.priority}`)}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="flex items-center justify-center w-11 h-11 rounded-xl text-text-muted hover:text-text-primary hover:bg-hover transition-colors focus:outline-none"
            aria-label="Close details"
          >
            <XCircle className="h-6 w-6" />
          </button>
        </div>
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-surface/50 p-5 rounded-2xl border border-main">
            <div>
              <h3 className="text-[11px] font-bold text-text-secondary uppercase tracking-widest mb-2">{t('calendar.detailModal.startDate')}</h3>
              <div className="flex items-center text-text-primary text-sm font-bold">
                <Clock className="h-4 w-4 mr-2 text-primary-start" />
                {formatEventDate(event.start_date)}
              </div>
            </div>
            {event.end_date && (
              <div>
                <h3 className="text-[11px] font-bold text-text-secondary uppercase tracking-widest mb-2">{t('calendar.detailModal.endDate')}</h3>
                <div className="flex items-center text-text-primary text-sm font-bold">
                  <Clock className="h-4 w-4 mr-2 text-primary-start" />
                  {formatEventDate(event.end_date)}
                </div>
              </div>
            )}
          </div>
          {event.location && (
            <div className="flex items-center gap-4 px-2 py-1">
              <div className="p-2 rounded-lg bg-primary-start/10 text-primary-start">
                <MapPin size={18} />
              </div>
              <p className="text-sm font-semibold text-text-secondary">{event.location}</p>
            </div>
          )}
          {event.description && (
            <div className="px-2 py-4 border-t border-main">
              <p className="text-sm leading-relaxed text-text-secondary italic">{event.description}</p>
            </div>
          )}
        </div>
        <div className="flex flex-col-reverse sm:flex-row gap-3 mt-8 pt-6 border-t border-main">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-colors focus:outline-none"
          >
            {t('general.cancel', 'Anulo')}
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting}
            className="w-full sm:w-auto px-6 h-11 bg-danger-start/10 hover:bg-danger-start/20 text-danger-start border border-danger-start/20 rounded-xl font-bold text-sm transition focus:outline-none disabled:opacity-50"
          >
            Fshij
          </button>
        </div>
      </motion.div>
    </div>
  );
};