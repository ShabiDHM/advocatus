// FILE: src/utils/kosovoHolidays.ts
// PHOENIX PROTOCOL - KOSOVO HOLIDAY ENGINE V1.5 (ALIGNMENT FIXED)
// 1. FIXED: Aligned all keys with translation.json (fiter_bajram, labor_day, etc.).
// 2. RETAINED: Full Kosovo Law substitution rule (Weekend -> Monday).
// 3. RETAINED: Catholic and Orthodox Easter algorithms.

import { isSameDay, addDays, getDay } from 'date-fns';

export type HolidayType = 'LEGAL' | 'RELIGIOUS' | 'INTERNATIONAL';

export interface Holiday {
  name: string;
  type: HolidayType;
  date: Date;
  greetingKey: string; 
  isMoveable: boolean;
}

const fixedDefinitions: { name: string, type: HolidayType, key: string, month: number, day: number }[] = [
  { name: 'Viti i Ri', type: 'LEGAL', key: 'new_year', month: 1, day: 1 },
  { name: 'Krishtlindjet Ortodokse', type: 'RELIGIOUS', key: 'orthodox_christmas', month: 1, day: 7 },
  { name: 'Dita e Pavarësisë', type: 'LEGAL', key: 'independence_day', month: 2, day: 17 },
  { name: 'Dita e Kushtetutës', type: 'LEGAL', key: 'constitution_day', month: 4, day: 9 },
  { name: 'Dita e Punëtorëve', type: 'INTERNATIONAL', key: 'labor_day', month: 5, day: 1 },
  { name: 'Dita e Evropës', type: 'INTERNATIONAL', key: 'europe_day', month: 5, day: 9 },
  { name: 'Krishtlindjet Katolike', type: 'RELIGIOUS', key: 'catholic_christmas', month: 12, day: 25 },
];

function calculateCatholicEaster(year: number): Date {
  const a = year % 19, b = Math.floor(year / 100), c = year % 100, d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30, i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31), day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}

function calculateOrthodoxEaster(year: number): Date {
  let a = year % 19, b = year % 4, c = year % 7, d = (19 * a + 15) % 30, e = (2 * b + 4 * c + 6 * d + 6) % 7, f = d + e, day = f + 22, month = 3;
  if (day > 31) { day -= 31; month = 4; }
  return addDays(new Date(year, month - 1, day), 13);
}

const eidDates: Record<string, { fitr: [number, number], adha: [number, number] }> = {
  '2024': { fitr: [4, 10], adha: [6, 16] },
  '2025': { fitr: [3, 31], adha: [6, 6] },
  '2026': { fitr: [3, 20], adha: [5, 27] },
};

function applySubstitutionRule(date: Date): Date {
  const dayOfWeek = getDay(date);
  if (dayOfWeek === 0) return addDays(date, 1);
  if (dayOfWeek === 6) return addDays(date, 2);
  return date;
}

export function getHolidaysForYear(year: number): Holiday[] {
  const holidays: Holiday[] = [];
  fixedDefinitions.forEach(def => {
    holidays.push({ name: def.name, type: def.type, date: applySubstitutionRule(new Date(year, def.month - 1, def.day)), greetingKey: def.key, isMoveable: false });
  });
  holidays.push({ name: 'Pashkët Katolike', type: 'RELIGIOUS', date: calculateCatholicEaster(year), greetingKey: 'catholic_easter', isMoveable: true });
  holidays.push({ name: 'Pashkët Ortodokse', type: 'RELIGIOUS', date: calculateOrthodoxEaster(year), greetingKey: 'orthodox_easter', isMoveable: true });
  const eids = eidDates[String(year)];
  if (eids) {
    holidays.push({ name: 'Fitër Bajrami', type: 'RELIGIOUS', date: applySubstitutionRule(new Date(year, eids.fitr[0] - 1, eids.fitr[1])), greetingKey: 'fiter_bajram', isMoveable: true });
    holidays.push({ name: 'Kurban Bajrami', type: 'RELIGIOUS', date: applySubstitutionRule(new Date(year, eids.adha[0] - 1, eids.adha[1])), greetingKey: 'kurban_bajram', isMoveable: true });
  }
  return holidays;
}

export function getHolidayForDate(date: Date): Holiday | null {
  const holidays = getHolidaysForYear(date.getFullYear());
  return holidays.find(h => isSameDay(h.date, date)) || null;
}

export interface HolidayBriefing {
  isHoliday: boolean;
  holiday: Holiday | null;
  greeting: string;
}

export function getCurrentBriefingHoliday(date: Date, t: (key: string) => string): HolidayBriefing {
  const holiday = getHolidayForDate(date);
  if (!holiday) return { isHoliday: false, holiday: null, greeting: '' };
  return {
    isHoliday: true,
    holiday,
    greeting: t(`holidays.${holiday.greetingKey}`),
  };
}