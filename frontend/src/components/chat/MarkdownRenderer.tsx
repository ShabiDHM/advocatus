// FILE: src/components/chat/MarkdownRenderer.tsx
// PHOENIX PROTOCOL - UNIFIED FORENSIC CITATION & RESPONSIVE RENDERER V51.0
// 100% COMPLETE CODE • ZERO DUPLICATIONS • CENTRALIZED PRECEDENT & LAW LINKING

import React from 'react';
import { LawCitationLink } from '../LawCitationLink';
import { PrecedentCitationLink } from '../PrecedentCitationLink';
import { FileText, ExternalLink } from 'lucide-react';

const getNodeText = (node: any): string => {
  if (!node) return '';
  if (typeof node === 'string') return node;
  if (typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(getNodeText).join('');
  if (node.props && node.props.children) return getNodeText(node.props.children);
  return '';
};

// ============================================================================
// MAIN MARKDOWN COMPONENTS BUILDER (ZERO-OVERFLOW, RESPONSIVE TABLES & CARDS)
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
  // 🔗 LINKET INTERAKTIVE: CITIME LIGJORE & PRECEDENTË TË CENTRALIZUAR
  // =========================================================================
  a: ({ href, children }: any): React.JSX.Element => {
    const rawText = getNodeText(children).trim();
    const rawHref = String(href || '').trim();

    // 1. PRECEDENTËT E GJYKATËS SUPREME (Rev, PML, A.NR, KMLP etj.)
    const isPrecedent =
      /\b(PML|Rev|REV|KMLP|ANR|A\.NR|AC|CA|PKR|AP|AGJ|CP)\.?\s*(?:Nr\.?|nr\.?)?\s*(\d+[\w\/\.\-]*\/\d{2,4}|\d+)\b/i.test(rawText) ||
      rawHref.includes('/laws/search?q=') ||
      rawHref.includes('caseNumber=');

    if (isPrecedent) {
      const cleanLabel = rawText.replace(/^\[+|\]+$/g, '').trim();
      return <PrecedentCitationLink caseNumber={cleanLabel} />;
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