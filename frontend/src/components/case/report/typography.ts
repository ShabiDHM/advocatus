// FILE: frontend/src/components/case/report/typography.ts
// PHOENIX PROTOCOL - REPORT TYPOGRAPHY V1.1
// V1.1: LINE-HEIGHT REDUCED — 1.7 → 1.55 (serif lexohet më kompakt).

export const FONT_LEVELS = [
  { label: '85%',  base: 13,    h1: 18,  h2: 15,   h3: 13.5, line: 1.5  },
  { label: '100%', base: 14.5,  h1: 20,  h2: 17,   h3: 15,   line: 1.55 },
  { label: '115%', base: 16,    h1: 22,  h2: 18.5, h3: 16.5, line: 1.6  },
  { label: '130%', base: 18,    h1: 25,  h2: 21,   h3: 18.5, line: 1.65 },
];

export const REPORT_FONT = {
  serif: 'Georgia, "Iowan Old Style", "Charter", "Times New Roman", serif',
  sans:  'Inter, system-ui, -apple-system, "Segoe UI", sans-serif',
  mono:  '"JetBrains Mono", "SF Mono", Consolas, monospace',
} as const;

export const STATUS_MARK = {
  ok:     '✓',
  fail:   '✗',
  warn:   '▲',
  hint:   '○',
  forbid: '■',
} as const;

export const SCORE_STYLES = {
  high: { text: 'text-emerald-500', label: 'Shkëlqyeshëm' },
  mid:  { text: 'text-amber-500',   label: 'Mirë' },
  low:  { text: 'text-rose-500',    label: 'Dobët' },
};

export const getScoreStyle = (score: number) => {
  if (score >= 85) return SCORE_STYLES.high;
  if (score >= 60) return SCORE_STYLES.mid;
  return SCORE_STYLES.low;
};

export const READINESS_STYLES: Record<string, { color: string; label: string }> = {
  READY:       { color: 'text-emerald-500', label: 'GATI' },
  'NEEDS WORK':{ color: 'text-amber-500',   label: 'KËRKON PUNË' },
  INCOMPLETE:  { color: 'text-rose-500',    label: 'I PËRPLOTË' },
  UNKNOWN:     { color: 'text-slate-500',   label: 'I PANJOHUR' },
};

export const formatShortDate = (isoDate?: string | Date | null): string => {
  if (!isoDate) return '';
  try {
    const d = typeof isoDate === 'string' ? new Date(isoDate) : isoDate;
    if (isNaN(d.getTime())) return '';
    const day = d.getDate().toString().padStart(2, '0');
    const month = (d.getMonth() + 1).toString().padStart(2, '0');
    const year = d.getFullYear().toString().slice(-2);
    const hours = d.getHours().toString().padStart(2, '0');
    const minutes = d.getMinutes().toString().padStart(2, '0');
    return `${day}.${month}.${year}, ${hours}:${minutes}`;
  } catch {
    return '';
  }
};