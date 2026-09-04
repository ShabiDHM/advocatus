// FILE: src/components/chat/MarkdownRenderer.tsx
// PHOENIX PROTOCOL - STRICT UNIFIED FORENSIC TOOLTIP & RESPONSIVE TABLE ENGINE V50.0

import React, { useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { LawCitationLink } from '../LawCitationLink';
import { FileText, ExternalLink, Landmark, ShieldCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const getNodeText = (node: any): string => {
  if (!node) return '';
  if (typeof node === 'string') return node;
  if (typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(getNodeText).join('');
  if (node.props && node.props.children) return getNodeText(node.props.children);
  return '';
};

// ============================================================================
// COMPONENT: PRECEDENT CITATION LINK (SUPREME COURT PRECEDENT BADGE)
// ============================================================================
const PrecedentCitationLink: React.FC<{ cleanLabel: string }> = ({ cleanLabel }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const fetchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [coords, setCoords] = useState({ top: 0, tooltipLeft: 0, arrowOffset: 0 });
  const containerRef = useRef<HTMLSpanElement>(null);

  const updateCoordinates = () => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const tooltipWidth = viewportWidth < 640 ? 300 : 340;
      const margin = 16;

      const idealLeft = rect.left + rect.width / 2;
      const minLeft = tooltipWidth / 2 + margin;
      const maxLeft = viewportWidth - tooltipWidth / 2 - margin;
      const clampedLeft = Math.max(minLeft, Math.min(idealLeft, maxLeft));
      const arrowOffset = idealLeft - clampedLeft;

      setCoords({
        top: rect.top + window.scrollY,
        tooltipLeft: clampedLeft,
        arrowOffset: arrowOffset,
      });
    }
  };

  const handleMouseEnter = () => {
    updateCoordinates();
    if (fetchTimeoutRef.current) clearTimeout(fetchTimeoutRef.current);
    fetchTimeoutRef.current = setTimeout(() => {
      setShowTooltip(true);
    }, 180);
  };

  const handleMouseLeave = () => {
    if (fetchTimeoutRef.current) {
      clearTimeout(fetchTimeoutRef.current);
      fetchTimeoutRef.current = null;
    }
    setShowTooltip(false);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowTooltip(false);
    window.dispatchEvent(
      new CustomEvent('open_precedent_preview', {
        detail: { caseNumber: cleanLabel }
      })
    );
  };

  const tooltipContent = (
    <AnimatePresence>
      {showTooltip && (
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.95 }}
          transition={{ duration: 0.12 }}
          className="absolute w-72 sm:w-80 p-4 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 border-2 border-amber-500/60 rounded-2xl shadow-2xl z-[9999] pointer-events-none ring-1 ring-black/10 dark:ring-white/10"
          style={{
            top: `${coords.top - 8}px`,
            left: `${coords.tooltipLeft}px`,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-1.5 font-bold text-xs text-amber-500">
              <ShieldCheck size={16} />
              <span>Precedent Zyrtar i Verifikuar</span>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded font-bold bg-amber-500/10 text-amber-500">
              SUPREME
            </span>
          </div>

          <div className="text-xs font-bold text-slate-900 dark:text-white mb-1 leading-snug">
            Gjykata Supreme e Kosovës • {cleanLabel}
          </div>

          <div className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed mb-2.5">
            Qëndrim parimor gjyqësor i detyrueshëm. Kliko për të hapur aktgjykimin origjinal në format PDF.
          </div>

          <div className="flex items-center justify-between text-[10px] font-mono bg-slate-100 dark:bg-slate-950 p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
            <span>Integriteti i Dosjes:</span>
            <span className="font-bold text-amber-500">
              Aktgjykim Origjinal (PDF) ✓
            </span>
          </div>

          <div
            className="absolute top-full -translate-x-1/2 -mt-[2px] border-[8px] border-transparent pointer-events-none"
            style={{
              borderTopColor: 'var(--tw-prose-body, currentColor)',
              opacity: 0.6,
              left: `calc(50% + ${coords.arrowOffset}px)`,
            }}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <span
      ref={containerRef}
      className="inline-flex items-center align-baseline mx-0.5 my-0.5 max-w-full"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button
        type="button"
        onClick={handleClick}
        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/25 text-amber-500 font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs max-w-full cursor-pointer focus:outline-none"
      >
        <Landmark size={13} className="shrink-0 opacity-80" />
        <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanLabel}</span>
      </button>

      {createPortal(tooltipContent, document.body)}
    </span>
  );
};

// ============================================================================
// MAIN MARKDOWN COMPONENTS BUILDER ME MBROJTJE NDAJ OVERFLOW DHE TABELA ELEGANTE
// ============================================================================
export const buildMarkdownComponents = () => ({
  h1: ({ node, ...props }: any): React.JSX.Element => (
    <h1
      className="text-base sm:text-lg font-black text-text-primary mt-4 mb-2 pb-1 border-b border-main tracking-tight uppercase"
      {...props}
    />
  ),
  h2: ({ node, ...props }: any): React.JSX.Element => (
    <h2
      className="text-sm sm:text-base font-bold text-primary-start mt-3.5 mb-1.5 tracking-tight uppercase"
      {...props}
    />
  ),
  h3: ({ node, ...props }: any): React.JSX.Element => (
    <h3
      className="text-xs sm:text-sm font-bold text-text-primary mt-3 mb-1 flex items-center gap-1.5 uppercase tracking-wide"
      {...props}
    />
  ),
  p: ({ node, ...props }: any): React.JSX.Element => (
    <p className="mb-2.5 last:mb-0 leading-relaxed text-text-secondary text-xs sm:text-sm break-words" {...props} />
  ),
  ul: ({ node, ...props }: any): React.JSX.Element => (
    <ul className="list-disc list-inside space-y-1 my-2 text-text-secondary pl-1 text-xs sm:text-sm" {...props} />
  ),
  ol: ({ node, ...props }: any): React.JSX.Element => (
    <ol className="list-decimal list-inside space-y-1.5 my-2 text-text-secondary pl-1 text-xs sm:text-sm" {...props} />
  ),
  li: ({ node, ...props }: any): React.JSX.Element => (
    <li className="leading-relaxed text-text-secondary break-words" {...props} />
  ),
  strong: ({ node, ...props }: any): React.JSX.Element => (
    <strong className="font-bold text-text-primary" {...props} />
  ),
  blockquote: ({ node, ...props }: any): React.JSX.Element => (
    <blockquote
      className="border-l-2 border-primary-start/40 pl-3.5 my-2.5 italic text-text-secondary bg-surface/50 py-1 rounded-r-lg break-words"
      {...props}
    />
  ),

  // =========================================================================
  // 🛡️ TABELAT RESPONSIVE: MBROJTJE TOTALE NGA DALJA JASHTË KUTISË
  // =========================================================================
  table: ({ node, ...props }: any): React.JSX.Element => (
    <div className="w-full my-3 overflow-x-auto rounded-xl border border-main bg-surface/30 shadow-xs custom-finance-scroll">
      <table className="w-full min-w-[500px] text-left border-collapse text-xs" {...props} />
    </div>
  ),
  thead: ({ node, ...props }: any): React.JSX.Element => (
    <thead className="bg-surface/80 border-b border-main text-text-primary font-bold tracking-wider uppercase text-[11px]" {...props} />
  ),
  tbody: ({ node, ...props }: any): React.JSX.Element => (
    <tbody className="divide-y divide-main/40 text-text-secondary" {...props} />
  ),
  tr: ({ node, ...props }: any): React.JSX.Element => (
    <tr className="hover:bg-hover/40 transition-colors" {...props} />
  ),
  th: ({ node, ...props }: any): React.JSX.Element => (
    <th className="px-3.5 py-2.5 font-bold text-text-primary whitespace-nowrap" {...props} />
  ),
  td: ({ node, children, ...props }: any): React.JSX.Element => {
    // Kontrollo nëse qeliza përmban tekst raw të linkut të formatit [Neni X](url)
    const textContent = getNodeText(children);
    const linkMatch = textContent.match(/\[(.*?)\]\((.*?)\)/);

    if (linkMatch) {
      const label = linkMatch[1];
      const targetUrl = linkMatch[2];
      const surroundingText = textContent.replace(linkMatch[0], '').trim();

      return (
        <td className="px-3.5 py-2.5 align-top leading-relaxed break-words max-w-[280px]" {...props}>
          <div className="flex flex-wrap items-center gap-1">
            <LawCitationLink
              lawTitle={label}
              articleNum=""
              fullMatch={label}
              targetUrl={targetUrl}
            />
            {surroundingText && <span className="text-text-secondary text-[11px]">{surroundingText}</span>}
          </div>
        </td>
      );
    }

    return (
      <td className="px-3.5 py-2.5 align-top leading-relaxed break-words max-w-[280px] sm:max-w-[340px]" {...props}>
        {children}
      </td>
    );
  },

  // =========================================================================
  // 🛡️ BLLOQET E KRONOLOGJISË DHE KODIT: MBROJTJE ME THYERJE RRESHTI
  // =========================================================================
  pre: ({ node, ...props }: any): React.JSX.Element => (
    <div className="w-full my-3 overflow-x-auto rounded-xl border border-main bg-surface/70 p-3 shadow-inner custom-finance-scroll">
      <pre className="text-xs font-mono whitespace-pre-wrap break-words leading-relaxed text-text-primary" {...props} />
    </div>
  ),
  code: ({ node, inline, className, children, ...props }: any): React.JSX.Element => {
    if (inline) {
      return (
        <code className="px-1.5 py-0.5 rounded-md bg-surface border border-main font-mono text-[11px] text-primary-start font-semibold" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="font-mono text-xs text-text-primary whitespace-pre-wrap break-words" {...props}>
        {children}
      </code>
    );
  },

  // =========================================================================
  // 🔗 LINKET INTERAKTIVE TË NENEVE, PRECEDENTËVE DHE DOKUMENTEVE
  // =========================================================================
  a: ({ href, children }: any): React.JSX.Element => {
    const rawText = getNodeText(children).trim();
    const rawHref = String(href || '').trim();

    // 1. PRECEDENTËT E GJYKATËS SUPREME (Rev ose PML)
    const isPrecedent =
      /\b(PML|Rev|REV|AC|CA|PKR|AP|AGJ)\.?\s*(?:Nr\.?|nr\.?)\s*(\d+\/\d{2,4})\b/i.test(rawText) ||
      rawHref.includes('/laws/library?q=') ||
      rawHref.includes('/laws/search?q=') ||
      rawHref.includes('caseNumber=');

    if (isPrecedent) {
      const cleanLabel = rawText.replace(/^\[+|\]+$/g, '').trim();
      return <PrecedentCitationLink cleanLabel={cleanLabel} />;
    }

    // 2. LIDHJET ME NENET STATUTORE LIGJORE
    if (rawHref.startsWith('/laws/article') || rawHref.startsWith('/laws/')) {
      try {
        const url = new URL(rawHref, window.location.origin);
        const lawTitle = url.searchParams.get('lawTitle') || 'Ligj';
        const articleNum = url.searchParams.get('articleNumber') || '1';
        const fullMatch = rawText || `${lawTitle} - Neni ${articleNum}`;

        return (
          <LawCitationLink
            lawTitle={lawTitle}
            articleNum={articleNum}
            fullMatch={fullMatch}
            targetUrl={rawHref}
          />
        );
      } catch {
        return (
          <LawCitationLink
            lawTitle="Ligj"
            articleNum="1"
            fullMatch={rawText || 'Referencë Ligjore'}
            targetUrl={rawHref}
          />
        );
      }
    }

    // 3. DOKUMENTET E DOSJES (PDF / SHKRESA)
    const isDocLink =
      rawHref.toLowerCase().includes('/documents/') ||
      rawHref.toLowerCase().endsWith('.pdf') ||
      rawText.toLowerCase().endsWith('.pdf') ||
      /\.(pdf|png|jpg|jpeg|docx?)$/i.test(rawText) ||
      /\.(pdf|png|jpg|jpeg|docx?)$/i.test(rawHref);

    if (isDocLink) {
      return (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            window.dispatchEvent(
              new CustomEvent('open_document_preview', {
                detail: { fileName: rawText, href: rawHref }
              })
            );
          }}
          className="inline-flex items-center gap-1.5 px-2.5 py-0.5 mx-1 my-0.5 rounded-lg bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 cursor-pointer focus:outline-none shadow-sm align-baseline"
        >
          <FileText size={12} className="shrink-0 text-primary-start" />
          <span className="underline decoration-primary-start/40">{rawText || children}</span>
        </button>
      );
    }

    // 4. LINKET E JASHTME
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-primary-start font-semibold underline decoration-primary-start/30 hover:decoration-primary-start transition-colors mx-0.5 break-words"
      >
        <span>{children}</span>
        <ExternalLink size={11} className="shrink-0 opacity-70" />
      </a>
    );
  },
});

export default buildMarkdownComponents;