// FILE: src/components/calendar/CalendarListView.tsx
import React from 'react';
import { format, parseISO } from 'date-fns';
import { Locale } from 'date-fns';
import { ChevronRight as ChevronRightIcon, Eye } from 'lucide-react';
import { TFunction } from 'i18next';
import { CalendarEvent } from '../../data/types';
import { getEventStyle, getEventId } from '../../utils/calendarHelpers';

interface CalendarListViewProps {
  filteredEvents: CalendarEvent[];
  onSelectEvent: (event: CalendarEvent) => void;
  currentLocale: Locale;
  t: TFunction;
}

export const CalendarListView: React.FC<CalendarListViewProps> = ({ filteredEvents, onSelectEvent, currentLocale, t }) => {
  return (
    <div className="glass-panel flex-1 flex flex-col rounded-[2.5rem] overflow-hidden min-h-[350px] border border-main bg-canvas">
      <div className="flex-1 overflow-y-auto custom-finance-scroll divide-y divide-main px-6 sm:px-8">
        {filteredEvents.length === 0 ? (
          <div className="py-24 text-center text-text-secondary italic text-sm font-medium">{t('calendar.noEventsFound')}</div>
        ) : (
          filteredEvents
            .sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
            .map((event) => {
              const style = getEventStyle(event.event_type, event.category);
              const isShared = (event as any).is_public === true || (event.notes && event.notes.includes('CLIENT_VISIBLE'));
              return (
                <div
                  key={getEventId(event)}
                  onClick={() => onSelectEvent(event)}
                  className="py-5 sm:py-6 cursor-pointer transition-all flex items-center justify-between group px-2 rounded-2xl mt-1 first:mt-0"
                >
                  <div className="flex items-start space-x-5 min-w-0 flex-1">
                    <div className="flex-shrink-0 text-center min-w-[60px] p-2 rounded-2xl bg-surface/30 border border-main group-hover:border-primary-start/50 group-hover:bg-primary-start/5 transition-all">
                      <div className="text-[10px] text-text-secondary uppercase font-black tracking-widest">
                        {format(parseISO(event.start_date), 'MMM', { locale: currentLocale })}
                      </div>
                      <div className="text-2xl font-black text-text-primary leading-none mt-1">
                        {format(parseISO(event.start_date), 'dd')}
                      </div>
                    </div>
                    <div className="min-w-0 flex-1 pr-4">
                      <h4 className="text-base font-bold text-text-primary group-hover:text-primary-start transition-colors truncate">
                        {event.title}
                      </h4>
                      <div className="flex items-center gap-3 mt-2">
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${style.border} ${style.bg} ${style.text} font-black uppercase tracking-widest`}>
                          {t(`calendar.types.${event.event_type}`)}
                        </span>
                        {isShared && <Eye size={12} className="text-status-success animate-pulse" />}
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
};