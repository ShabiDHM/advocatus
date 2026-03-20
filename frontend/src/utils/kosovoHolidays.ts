// FILE: src/utils/kosovoHolidays.ts
// PHOENIX PROTOCOL - KOSOVO HOLIDAY ENGINE V1.2 (TIMEZONE SAFE)

import { isSameDay, addDays } from 'date-fns';

// ============ 1. HOLIDAY DEFINITIONS ============

export type HolidayType = 'LEGAL' | 'RELIGIOUS' | 'INTERNATIONAL';

export interface Holiday {
  name: string;
  type: HolidayType;
  date: Date;
  greetingKey?: string; // for i18n
  isMoveable: boolean;
}

// Fixed holidays (same date every year)
export const fixedHolidays: Omit<Holiday, 'date'>[] = [
  { name: 'Viti i Ri', type: 'LEGAL', greetingKey: 'new_year', isMoveable: false },
  { name: 'Dita e Pavarësisë së Kosovës', type: 'LEGAL', greetingKey: 'independence_day', isMoveable: false },
  { name: 'Dita e Kushtetutës së Kosovës', type: 'LEGAL', greetingKey: 'constitution_day', isMoveable: false },
  { name: 'Dita e Evropës', type: 'INTERNATIONAL', greetingKey: 'europe_day', isMoveable: false },
  { name: 'Dita e Çlirimit të Kosovës', type: 'LEGAL', greetingKey: 'liberation_day', isMoveable: false },
  { name: 'Dita e Forcës së Sigurisë së Kosovës', type: 'LEGAL', greetingKey: 'security_force_day', isMoveable: false },
  { name: 'Dita e Mësuesit', type: 'INTERNATIONAL', greetingKey: 'teachers_day', isMoveable: false },
];

function getFixedHoliday(holiday: typeof fixedHolidays[0], year: number): Holiday {
  let monthDay: [number, number];
  switch (holiday.name) {
    case 'Viti i Ri': monthDay = [1, 1]; break;
    case 'Dita e Pavarësisë së Kosovës': monthDay = [2, 17]; break;
    case 'Dita e Kushtetutës së Kosovës': monthDay = [4, 9]; break;
    case 'Dita e Evropës': monthDay = [5, 9]; break;
    case 'Dita e Çlirimit të Kosovës': monthDay = [6, 12]; break;
    case 'Dita e Forcës së Sigurisë së Kosovës': monthDay = [11, 30]; break;
    case 'Dita e Mësuesit': monthDay = [3, 7]; break;
    default: monthDay = [1, 1];
  }
  const [month, day] = monthDay;
  return { ...holiday, date: new Date(year, month - 1, day) };
}

// Catholic Easter
function calculateCatholicEaster(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}

// Orthodox Easter
function calculateOrthodoxEaster(year: number): Date {
  let a = year % 19;
  let b = year % 4;
  let c = year % 7;
  let d = (19 * a + 15) % 30;
  let e = (2 * b + 4 * c + 6 * d + 6) % 7;
  let f = d + e;
  let day = f + 22;
  let month = 3;
  if (day > 31) {
    day -= 31;
    month = 4;
  }
  const julianDate = new Date(year, month - 1, day);
  return addDays(julianDate, 13);
}

// Eid approximations (for 2024–2035)
const eidDates: Record<string, { fitr: [number, number], adha: [number, number] }> = {
  '2024': { fitr: [4, 10], adha: [6, 16] },
  '2025': { fitr: [3, 31], adha: [6, 6] },
  '2026': { fitr: [3, 20], adha: [5, 27] },
  '2027': { fitr: [3, 9], adha: [5, 16] },
  '2028': { fitr: [2, 27], adha: [5, 4] },
  '2029': { fitr: [2, 14], adha: [4, 23] },
  '2030': { fitr: [2, 3], adha: [4, 12] },
  '2031': { fitr: [1, 23], adha: [4, 1] },
  '2032': { fitr: [1, 12], adha: [3, 20] },
  '2033': { fitr: [1, 1], adha: [3, 9] },
  '2034': { fitr: [12, 21], adha: [2, 26] },
  '2035': { fitr: [12, 10], adha: [2, 15] },
};

function getEidHolidays(year: number): Holiday[] {
  const yearStr = String(year);
  const eid = eidDates[yearStr];
  if (!eid) return [];
  const fitrDate = new Date(year, eid.fitr[0] - 1, eid.fitr[1]);
  const adhaDate = new Date(year, eid.adha[0] - 1, eid.adha[1]);
  return [
    { name: 'Fitër Bajrami', type: 'RELIGIOUS', date: fitrDate, greetingKey: 'eid_fitr', isMoveable: true },
    { name: 'Kurban Bajrami', type: 'RELIGIOUS', date: adhaDate, greetingKey: 'eid_adha', isMoveable: true },
  ];
}

export function getHolidaysForYear(year: number): Holiday[] {
  const holidays: Holiday[] = [];
  fixedHolidays.forEach(h => holidays.push(getFixedHoliday(h, year)));
  holidays.push({ name: 'Pashkët Katolike', type: 'RELIGIOUS', date: calculateCatholicEaster(year), greetingKey: 'easter_catholic', isMoveable: true });
  holidays.push({ name: 'Pashkët Ortodokse', type: 'RELIGIOUS', date: calculateOrthodoxEaster(year), greetingKey: 'easter_orthodox', isMoveable: true });
  holidays.push(...getEidHolidays(year));
  return holidays;
}

// Normalize to local date (midnight)
function normalizeDate(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

export function getHolidayForDate(date: Date): Holiday | null {
  const normalized = normalizeDate(date);
  const year = normalized.getFullYear();
  const holidays = getHolidaysForYear(year);
  return holidays.find(h => isSameDay(normalizeDate(h.date), normalized)) || null;
}

export interface HolidayBriefing {
  isHoliday: boolean;
  holiday: Holiday | null;
  greeting: string; // translated message
}

export function getCurrentBriefingHoliday(date: Date, t: (key: string) => string): HolidayBriefing {
  const holiday = getHolidayForDate(date);
  if (!holiday) {
    return { isHoliday: false, holiday: null, greeting: '' };
  }
  const greetingKey = holiday.greetingKey || 'holiday_generic';
  return {
    isHoliday: true,
    holiday,
    greeting: t(`holidays.${greetingKey}`),
  };
}