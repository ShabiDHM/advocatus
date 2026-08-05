// FILE: src/components/calendar/CalendarSidebar.tsx
import React from 'react';
import { format, parseISO } from 'date-fns';
import { Locale } from 'date-fns';
import { Bell, Filter } from 'lucide-react';
import { TFunction } from 'i18next';
import { CalendarEvent } from '../../data/types';
import { getEventStyle, getEventId } from '../../utils/calendarHelpers';

interface CalendarSidebarProps {
  upcomingAlerts: CalendarEvent[];
  filterType: string;
  onFilterTypeChange: (type: string) => void;
  onSelectEvent: (event: CalendarEvent) => void;
  currentLocale: Locale;
  t: TFunction;
}

export const CalendarSidebar: React.FC<CalendarSidebarProps> = ({
  upcomingAlerts,
  filterType,
  onFilterTypeChange,
  onSelectEvent,
  currentLocale,
  t,
}) => {
  return (
    <div className="flex flex-col gap-8 min-h-0 bg-canvas">
      <div className="glass-panel flex-1 p-6 sm:p-8 rounded-[2.5rem] relative overflow-hidden flex flex-col border border-main bg-canvas">
        <h3 className="text-xs font-black text-text-primary mb-8 flex items-center gap-3 uppercase tracking-wider select-none">
          <Bell className="text-accent-start animate-bounce" size={16} />
          {t('calendar.upcomingAlerts')}
        </h3>
        <div className="flex-1 overflow-y-auto custom-finance-scroll space-y-6 pr-2">
          {upcomingAlerts.length === 0 ? (
            <div className="h-full flex items-center justify-center text-center px-4 italic text-text-secondary text-sm font-medium">
              S'ka afate.
            </div>
          ) : (
            upcomingAlerts.map((ev) => {
              const style = getEventStyle(ev.event_type, ev.category);
              return (
                <button
                  type="button"
                  key={getEventId(ev)}
                  onClick={() => onSelectEvent(ev)}
                  className="w-full flex gap-5 items-start group text-left p-4 rounded-2xl hover:bg-hover transition-all border border-transparent hover:border-main focus:outline-none active:scale-95"
                >
                  <div className={`mt-2 w-2 h-2 rounded-full shrink-0 ${style.indicator} shadow-[0_0_12px_currentColor]`} />
                  <div className="min-w-0 flex-1">
                    <h4 className="text-sm font-bold text-text-secondary group-hover:text-primary-start transition-colors truncate tracking-tight">
                      {ev.title}
                    </h4>
                    <p className="text-[11px] text-text-secondary/50 mt-2 font-bold uppercase tracking-wider">
                      {format(parseISO(ev.start_date), 'dd MMM', { locale: currentLocale })} • {t(`calendar.types.${ev.event_type}`)}
                    </p>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      <div className="glass-panel p-6 sm:p-8 rounded-[2.5rem] shrink-0 border border-main bg-canvas">
        <h3 className="text-sm font-black text-text-primary mb-6 uppercase tracking-wider flex items-center gap-3 select-none">
          <Filter size={16} className="text-primary-start" /> {t('calendar.eventTypes')}
        </h3>
        <div className="space-y-2 overflow-y-auto max-h-[220px] custom-scrollbar pr-2">
          {Object.keys(t('calendar.types', { returnObjects: true }) as object).map((key) => {
            const style = getEventStyle(key);
            return (
              <div
                key={key}
                className="flex items-center gap-4 p-3 rounded-2xl hover:bg-hover transition-all cursor-pointer border border-transparent hover:border-main"
                onClick={() => onFilterTypeChange(filterType === key ? 'ALL' : key)}
              >
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${style.border} ${style.bg} ${style.text} shadow-inner`}>
                  {React.cloneElement(style.icon as React.ReactElement, { size: 16 })}
                </div>
                <span className={`text-[12px] uppercase tracking-wider font-semibold ${filterType === key ? 'text-text-primary' : 'text-text-secondary'}`}>
                  {t(`calendar.types.${key}`)}
                </span>
                {filterType === key && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-start" />}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};