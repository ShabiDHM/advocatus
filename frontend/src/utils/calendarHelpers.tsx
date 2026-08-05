// FILE: src/utils/calendarHelpers.tsx
import React from 'react';
import { CalendarEvent } from '../data/types';
import { sq, enUS } from 'date-fns/locale';
import { Locale } from 'date-fns';
import {
  History,
  AlertTriangle,
  Gavel,
  Users,
  FileText,
  Scale,
  MessageSquare,
  Calendar as CalendarIcon,
} from 'lucide-react';

export const localeMap: { [key: string]: Locale } = { sq, al: sq, en: enUS };

export const getEventStyle = (type: string, category?: string): {
  border: string;
  bg: string;
  text: string;
  indicator: string;
  icon: React.JSX.Element;
} => {
  if (category === 'FACT') {
    return {
      border: 'border-main',
      bg: 'bg-surface/50 hover:bg-surface/80',
      text: 'text-text-secondary',
      indicator: 'bg-text-secondary',
      icon: <History size={12} className="text-text-secondary" />,
    };
  }
  switch (type) {
    case 'DEADLINE':
      return {
        border: 'border-accent-start/30',
        bg: 'bg-accent-start/10 hover:bg-accent-start/20',
        text: 'text-accent-start',
        indicator: 'bg-accent-start',
        icon: <AlertTriangle size={12} className="text-accent-start" />,
      };
    case 'HEARING':
      return {
        border: 'border-secondary-start/30',
        bg: 'bg-secondary-start/10 hover:bg-secondary-start/20',
        text: 'text-secondary-start',
        indicator: 'bg-secondary-start',
        icon: <Gavel size={12} className="text-secondary-start" />,
      };
    case 'MEETING':
      return {
        border: 'border-primary-start/30',
        bg: 'bg-primary-start/10 hover:bg-primary-start/20',
        text: 'text-primary-start',
        indicator: 'bg-primary-start',
        icon: <Users size={12} className="text-primary-start" />,
      };
    case 'FILING':
      return {
        border: 'border-amber-500/30',
        bg: 'bg-amber-500/10 hover:bg-amber-500/20',
        text: 'text-amber-400',
        indicator: 'bg-amber-500',
        icon: <FileText size={12} className="text-amber-400" />,
      };
    case 'COURT_DATE':
      return {
        border: 'border-orange-500/30',
        bg: 'bg-orange-500/10 hover:bg-orange-500/20',
        text: 'text-orange-400',
        indicator: 'bg-orange-500',
        icon: <Scale size={12} className="text-orange-400" />,
      };
    case 'CONSULTATION':
      return {
        border: 'border-emerald-500/30',
        bg: 'bg-emerald-500/10 hover:bg-emerald-500/20',
        text: 'text-emerald-400',
        indicator: 'bg-emerald-500',
        icon: <MessageSquare size={12} className="text-emerald-400" />,
      };
    default:
      return {
        border: 'border-main',
        bg: 'bg-surface/50 hover:bg-surface/80',
        text: 'text-text-secondary',
        indicator: 'bg-text-secondary',
        icon: <CalendarIcon size={12} className="text-text-secondary" />,
      };
  }
};

export const getEventId = (event: CalendarEvent): string => (event as any).id || (event as any)._id || '';