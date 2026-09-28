// FILE: frontend/src/components/case/report/ReportComponents.tsx
// PHOENIX PROTOCOL - REPORT MARKDOWN COMPONENTS V1.3
// V1.3: PARAMETERIZED — buildReportComponents(options) merr h1Label dhe
//       h1PrefixStrips. Kjo lejon ripërdorim për Verifiko + Audit.
// V1.2: VISIBILITY FIXES (border-solid, priority badges, SUGJERIM nested).
// V1.1: SPACING + INFO BLOCK.
// V1.0: Redesign profesional serif.

import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { LawCitationLink } from '../../LawCitationLink';
import { PrecedentCitationLink } from '../../PrecedentCitationLink';
import { STATUS_MARK } from './typography';

// ───────────────────────────────────────────────────────────────────────────
// TYPES
// ───────────────────────────────────────────────────────────────────────────

type StatusKey = 'ok' | 'fail' | 'warn' | 'hint' | null;

export interface ReportComponentsOptions {
  /** Etiketa që shfaqet sipër titullit (default: "Raport Verifikimi"). */
  h1Label?: string;
  /** RegExp që hiqen nga fillimi i H1, me radhë. */
  h1PrefixStrips?: RegExp[];
}

// ───────────────────────────────────────────────────────────────────────────
// STATUS DETECTION
// ───────────────────────────────────────────────────────────────────────────

const STATUS_BY_MARK: Record<string, StatusKey> = {
  [STATUS_MARK.ok]:     'ok',
  [STATUS_MARK.fail]:   'fail',
  [STATUS_MARK.warn]:   'warn',
  [STATUS_MARK.hint]:   'hint',
};

const STATUS_LEFT_BORDER: Record<NonNullable<StatusKey>, string> = {
  ok:   'border-l-emerald-500',
  fail: 'border-l-rose-500',
  warn: 'border-l-amber-500',
  hint: 'border-l-sky-500',
};

const STATUS_SYMBOL_COLOR: Record<NonNullable<StatusKey>, string> = {
  ok:   'text-emerald-500',
  fail: 'text-rose-500',
  warn: 'text-amber-500',
  hint: 'text-sky-500',
};

const detectStatus = (text: string): StatusKey => {
  const trimmed = text.trim();
  for (const [mark, key] of Object.entries(STATUS_BY_MARK)) {
    if (trimmed.startsWith(mark)) return key;
  }
  return null;
};

const stripMarker = (text: string): string => {
  for (const mark of Object.values(STATUS_MARK)) {
    if (text.trim().startsWith(mark)) {
      return text.trim().slice(mark.length).trim();
    }
  }
  return text;
};

const isSugjerim = (text: string): boolean => {
  const t = text.trim().toUpperCase();
  return t.startsWith('▲ SUGJERIM') || t.startsWith('SUGJERIM');
};

// ───────────────────────────────────────────────────────────────────────────
// HELPERS
// ───────────────────────────────────────────────────────────────────────────

const extractText = (node: React.ReactNode): string => {
  if (typeof node === 'string') return node;
  if (typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (React.isValidElement(node)) {
    return extractText((node.props as any).children);
  }
  return '';
};

const splitByBr = (items: React.ReactNode[]): React.ReactNode[][] => {
  const rows: React.ReactNode[][] = [[]];
  for (const item of items) {
    if (React.isValidElement(item) && item.type === 'br') {
      rows.push([]);
    } else {
      rows[rows.length - 1].push(item);
    }
  }
  return rows.filter((r) => r.length > 0);
};

// ───────────────────────────────────────────────────────────────────────────
// PRIORITY BADGE (#K1, #R1, #O1)
// ───────────────────────────────────────────────────────────────────────────

const PRIORITY_STYLES = {
  K: { badge: 'bg-rose-500/15 text-rose-500 border-rose-500/40', label: 'KRITIKE' },
  R: { badge: 'bg-amber-500/15 text-amber-500 border-amber-500/40', label: 'E RËNDËSISHME' },
  O: { badge: 'bg-sky-500/15 text-sky-500 border-sky-500/40', label: 'OPSIONALE' },
} as const;

const PriorityBadge: React.FC<{ code: string }> = ({ code }) => {
  const m = code.match(/^\[#([KRO])(\d+)\]$/);
  if (!m) return <>{code}</>;
  const [, kind, num] = m;
  const style = PRIORITY_STYLES[kind as 'K' | 'R' | 'O'];
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border font-sans text-[10px] font-bold uppercase tracking-wide mr-2 ${style.badge}`}
      title={style.label}
    >
      <span>{kind}{num}</span>
    </span>
  );
};

// ───────────────────────────────────────────────────────────────────────────
// SHARED COMPONENTS
// ───────────────────────────────────────────────────────────────────────────

const Strong = ({ children }: any) => {
  const text = extractText(children);
  const m = text.match(/^\[#([KRO])(\d+)\]$/);
  if (m) {
    return <PriorityBadge code={text} />;
  }
  return <strong className="font-semibold text-text-primary">{children}</strong>;
};

const InfoBlock: React.FC<{ items: React.ReactNode[] }> = ({ items }) => {
  const rows = splitByBr(items);

  return (
    <div className="my-5 py-3 border-y border-main/40 space-y-2">
      {rows.map((row, i) => {
        const label = extractText(row[0]).replace(/:\s*$/, '');
        const value = row.slice(1);

        return (
          <div key={i} className="flex items-baseline gap-4">
            <span className="font-sans text-[10px] uppercase tracking-[0.15em] text-text-muted font-medium min-w-[110px] shrink-0">
              {label}
            </span>
            <span className="flex-1 font-serif text-sm text-text-primary leading-relaxed">
              {value}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// ───────────────────────────────────────────────────────────────────────────
// BUILD COMPONENTS
// ───────────────────────────────────────────────────────────────────────────

const DEFAULT_H1_PREFIX_STRIPS: RegExp[] = [
  /^RAPORT VERIFIKIMI\s*—\s*/,
  /^RAPORT AUDITIMI\s*—\s*/,
  /^RAPORT\s*—\s*/,
];

export const buildReportComponents = (options: ReportComponentsOptions = {}) => {
  const h1Label = options.h1Label ?? 'Raport Verifikimi';
  const h1PrefixStrips = options.h1PrefixStrips ?? DEFAULT_H1_PREFIX_STRIPS;

  return {
    h1: ({ children }: any) => {
      let title = String(children);
      for (const re of h1PrefixStrips) {
        title = title.replace(re, '');
      }
      title = title.trim();

      return (
        <header className="mb-4 pb-4 border-b-2 border-text-primary/15">
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-text-muted mb-2 flex items-center gap-2">
            <ShieldCheck size={12} className="text-primary-start" />
            {h1Label}
          </p>
          <h1 className="font-serif text-2xl sm:text-3xl font-semibold text-text-primary tracking-tight leading-tight">
            {title}
          </h1>
        </header>
      );
    },

    h2: ({ children }: any) => {
      const text = String(children);
      const m = text.match(/^(\d+)\.\s+(.+)$/);
      if (m) {
        return (
          <h2 className="mt-5 mb-3 pb-2 border-b border-main/50 flex items-baseline gap-3">
            <span className="font-mono text-sm font-bold text-text-muted tabular-nums">
              {m[1].padStart(2, '0')}
            </span>
            <span className="font-serif text-base sm:text-lg font-semibold text-text-primary tracking-tight uppercase">
              {m[2]}
            </span>
          </h2>
        );
      }
      return (
        <h2 className="mt-5 mb-3 pb-2 border-b border-main/50 font-serif text-base sm:text-lg font-semibold text-text-primary tracking-tight uppercase">
          {children}
        </h2>
      );
    },

    h3: ({ children }: any) => {
      const text = String(children);
      const m = text.match(/^([A-Z])\.\s+(.+)$/);
      if (m) {
        return (
          <h3 className="mt-5 mb-2 font-serif text-sm sm:text-base font-semibold text-text-primary">
            <span className="text-text-muted mr-2">{m[1]}.</span>
            {m[2]}
          </h3>
        );
      }
      return (
        <h3 className="mt-5 mb-2 font-serif text-sm sm:text-base font-semibold text-text-primary">
          {children}
        </h3>
      );
    },

    h4: ({ children }: any) => (
      <h4 className="mt-4 mb-2 font-serif text-sm font-semibold text-text-primary italic">
        {children}
      </h4>
    ),

    p: ({ children }: any) => {
      const arr = React.Children.toArray(children);
      const combined = extractText(arr);

      if (
        combined.includes('Dokumenti:') &&
        combined.includes('Data:') &&
        combined.includes('Gatishmëria:')
      ) {
        return <InfoBlock items={arr} />;
      }

      return (
        <p className="font-serif text-text-primary leading-relaxed mb-3">
          {children}
        </p>
      );
    },

    ul: ({ children }: any) => (
      <ul className="list-none pl-0 mb-3 space-y-0.5">
        {children}
      </ul>
    ),

    ol: ({ children }: any) => (
      <ol className="list-decimal pl-6 mb-3 space-y-1 font-serif text-text-primary">
        {children}
      </ol>
    ),

    li: ({ children }: any) => {
      const firstText = Array.isArray(children) ? String(children[0] ?? '') : String(children ?? '');

      if (isSugjerim(firstText)) {
        const cleaned =
          Array.isArray(children)
            ? [stripMarker(String(children[0] ?? '')).replace(/^SUGJERIM\s*[—-]\s*/i, ''), ...children.slice(1)]
            : stripMarker(String(children)).replace(/^SUGJERIM\s*[—-]\s*/i, '');
        return (
          <li className="flex items-start gap-2 pl-8 mb-2 text-text-muted">
            <span className="font-sans text-[9px] uppercase tracking-widest font-bold mt-1 shrink-0">
              Sugjerim
            </span>
            <span className="flex-1 font-serif text-sm text-text-secondary italic leading-relaxed">
              {cleaned}
            </span>
          </li>
        );
      }

      const status = detectStatus(firstText);

      if (status) {
        const borderClass = STATUS_LEFT_BORDER[status];
        const symbolClass = STATUS_SYMBOL_COLOR[status];
        const symbol = STATUS_MARK[status];

        const cleaned =
          Array.isArray(children)
            ? [stripMarker(String(children[0] ?? '')), ...children.slice(1)]
            : stripMarker(String(children));

        return (
          <li
            className={`flex items-start gap-3 pl-4 py-1.5 mb-1 border-l-2 border-solid ${borderClass} bg-transparent`}
          >
            <span className={`shrink-0 font-mono text-xs leading-relaxed mt-0.5 ${symbolClass}`}>
              {symbol}
            </span>
            <span className="flex-1 font-serif text-text-primary leading-relaxed">
              {cleaned}
            </span>
          </li>
        );
      }

      return (
        <li className="flex items-start gap-3 pl-4 mb-1">
          <span className="w-1 h-1 rounded-full bg-text-muted/60 mt-2.5 shrink-0" />
          <span className="flex-1 font-serif text-text-primary leading-relaxed">
            {children}
          </span>
        </li>
      );
    },

    strong: Strong,

    em: ({ children }: any) => (
      <em className="italic text-text-secondary">{children}</em>
    ),

    code: ({ children }: any) => (
      <code className="px-1.5 py-0.5 rounded bg-canvas/60 border border-main/60 font-mono text-[0.9em] text-primary-start">
        {children}
      </code>
    ),

    hr: () => <hr className="my-4 border-0 border-t border-main/30" />,

    blockquote: ({ children }: any) => (
      <blockquote className="my-4 pl-4 py-2 border-l-2 border-solid border-text-muted/40 italic font-serif text-text-secondary leading-relaxed">
        {children}
      </blockquote>
    ),

    a: ({ children, href }: any) => {
      const hrefStr = typeof href === 'string' ? href : '';
      if (hrefStr.includes('/laws/article')) {
        return <LawCitationLink lawTitle="" articleNum="" fullMatch={String(children)} targetUrl={hrefStr} />;
      }
      if (hrefStr.includes('/laws/search')) {
        return <PrecedentCitationLink caseNumber={String(children)} />;
      }
      return (
        <a
          href={hrefStr}
          className="text-primary-start hover:text-primary-end underline underline-offset-2 transition-colors"
          target="_blank"
          rel="noopener noreferrer"
        >
          {children}
        </a>
      );
    },

    table: ({ children }: any) => (
      <div className="overflow-x-auto my-4 border border-main/60 rounded-md">
        <table className="min-w-full text-xs font-serif">{children}</table>
      </div>
    ),

    thead: ({ children }: any) => (
      <thead className="bg-canvas/40 border-b border-main/60">{children}</thead>
    ),

    th: ({ children }: any) => (
      <th className="px-3 py-2 text-left font-sans font-semibold text-text-primary uppercase tracking-wide text-[10px]">
        {children}
      </th>
    ),

    td: ({ children }: any) => (
      <td className="px-3 py-2 border-t border-main/30 text-text-primary">
        {children}
      </td>
    ),
  };
};