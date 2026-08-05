// FILE: src/components/calendar/CalendarMonthView.tsx
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format, startOfMonth, getDay, getDaysInMonth, isSameDay, isToday as isTodayFns, parseISO, startOfWeek, addDays } from 'date-fns';
import { Locale } from 'date-fns';
import { TFunction } from 'i18next';
import { CalendarEvent } from '../../data/types';
import { getEventStyle, getEventId } from '../../utils/calendarHelpers';

interface CalendarMonthViewProps {
  currentDate: Date;
  filteredEvents: CalendarEvent[];
  onSelectEvent: (event: CalendarEvent) => void;
  onSelectDateForModal: (date: Date) => void;
  currentLocale: Locale;
  t: TFunction;
}

export const CalendarMonthView: React.FC<CalendarMonthViewProps> = ({
  currentDate,
  filteredEvents,
  onSelectEvent,
  onSelectDateForModal,
  currentLocale,
  t,
}) => {
  const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);

  const monthStart = startOfMonth(currentDate);
  const daysInMonth = getDaysInMonth(currentDate);
  const weekStartsOn = currentLocale?.options?.weekStartsOn ?? 1;
  const firstDayOfMonth = getDay(monthStart);
  const startingDayIndex = (firstDayOfMonth - weekStartsOn + 7) % 7;
  const cellClass = "min-h-[100px] sm:min-h-[130px] border-r border-b border-main relative group transition-all hover:bg-surface/30 flex flex-col cursor-pointer bg-canvas";

  const days = Array.from({ length: startingDayIndex }, (_, i) => (
    <div key={`empty-${i}`} className={`${cellClass} bg-surface/10`} />
  ));

  for (let day = 1; day <= daysInMonth; day++) {
    const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), day);
    const dayEvents = filteredEvents.filter((event) => isSameDay(parseISO(event.start_date), date));
    const today = isTodayFns(date);

    days.push(
      <div key={day} className={`${cellClass} p-1 ${today ? 'bg-primary-start/5' : ''}`} onClick={() => onSelectDateForModal(date)}>
        <div className={`text-xs font-black mb-2 flex justify-between items-center p-2 ${today ? 'text-primary-start' : 'text-text-secondary'}`}>
          <span className={`w-7 h-7 flex items-center justify-center rounded-xl transition-all ${today ? 'bg-primary-start text-white shadow-xl shadow-primary-start/30' : 'group-hover:text-text-primary'}`}>
            {day}
          </span>
        </div>
        <div className="flex-1 w-full space-y-1.5 px-1 overflow-visible relative">
          {dayEvents.slice(0, 3).map((event) => {
            const style = getEventStyle(event.event_type, event.category);
            const eventId = getEventId(event);
            return (
              <div key={eventId} className="relative w-full">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectEvent(event);
                  }}
                  onMouseEnter={() => setHoveredEventId(eventId)}
                  onMouseLeave={() => setHoveredEventId(null)}
                  className={`w-full text-left px-2 py-1 rounded-lg border flex items-center gap-2 transition-all duration-300 ${style.bg} ${style.border} group-hover:shadow-lg focus:outline-none ${
                    hoveredEventId === eventId ? 'scale-[1.05] z-50 ring-2 ring-white/10 shadow-black shadow-2xl' : ''
                  }`}
                >
                  <div className={`w-1.5 h-1.5 rounded-full ${style.indicator} shrink-0`} />
                  <span className={`text-[10px] font-bold truncate ${style.text} flex-1 tracking-tight`}>{event.title}</span>
                </button>
                <AnimatePresence>
                  {hoveredEventId === eventId && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="absolute left-0 bottom-full mb-3 z-[100] w-64 glass-panel p-4 rounded-2xl shadow-2xl pointer-events-none border border-main bg-canvas"
                    >
                      <div className={`text-[10px] font-black uppercase mb-2 flex items-center gap-2 ${style.text}`}>
                        {style.icon} {t(`calendar.types.${event.event_type}`)}
                      </div>
                      <div className="text-text-primary font-bold text-sm mb-2">{event.title}</div>
                      <div className="text-text-secondary text-[11px] line-clamp-2 italic mb-3">{event.description || t('general.notAvailable')}</div>
                      <div className="pt-3 border-t border-main text-text-secondary text-[10px] flex justify-between font-bold">
                        <span>{format(parseISO(event.start_date), 'HH:mm')}</span>
                        <span className="text-primary-start uppercase">{t(`calendar.priorities.${event.priority}`)}</span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  const totalCells = Math.ceil(days.length / 7) * 7;
  while (days.length < totalCells) days.push(<div key={`empty-end-${days.length}`} className={`${cellClass} bg-surface/10`} />);

  const weekStarts = startOfWeek(new Date(), { weekStartsOn });
  const weekDays = Array.from({ length: 7 }, (_, i) => format(addDays(weekStarts, i), 'EEEEEE', { locale: currentLocale }));

  return (
    <div className="glass-panel flex-1 flex flex-col rounded-[2.5rem] overflow-hidden border border-main bg-canvas">
      <div className="grid grid-cols-7 bg-surface border-b border-main shrink-0">
        {weekDays.map((day) => (
          <div key={day} className="py-4 text-center text-[11px] font-black text-text-secondary uppercase tracking-widest">
            {day}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 border-l border-t border-main flex-1 overflow-y-auto custom-finance-scroll bg-canvas">{days}</div>
    </div>
  );
};