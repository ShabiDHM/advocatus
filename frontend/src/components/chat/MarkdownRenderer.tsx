// FILE: src/components/chat/MarkdownRenderer.tsx
// PHOENIX PROTOCOL - MARKDOWN RENDERER V45.0 (NATIVE TOOLTIP PURGED)

import React from 'react';
import { LawCitationLink } from '../LawCitationLink';
import { FileText, ExternalLink, Landmark } from 'lucide-react';

const getNodeText = (node: any): string => {
  if (!node) return '';
  if (typeof node === 'string') return node;
  if (typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(getNodeText).join('');
  if (node.props && node.props.children) return getNodeText(node.props.children);
  return '';
};

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
    <p className="mb-2.5 last:mb-0 leading-relaxed text-text-secondary text-xs sm:text-sm" {...props} />
  ),
  ul: ({ node, ...props }: any): React.JSX.Element => (
    <ul className="list-disc list-inside space-y-1 my-2 text-text-secondary pl-1 text-xs sm:text-sm" {...props} />
  ),
  ol: ({ node, ...props }: any): React.JSX.Element => (
    <ol className="list-decimal list-inside space-y-1.5 my-2 text-text-secondary pl-1 text-xs sm:text-sm" {...props} />
  ),
  li: ({ node, ...props }: any): React.JSX.Element => (
    <li className="leading-relaxed text-text-secondary" {...props} />
  ),
  strong: ({ node, ...props }: any): React.JSX.Element => (
    <strong className="font-bold text-text-primary" {...props} />
  ),
  blockquote: ({ node, ...props }: any): React.JSX.Element => (
    <blockquote
      className="border-l-2 border-primary-start/40 pl-3.5 my-2.5 italic text-text-secondary bg-surface/50 py-1 rounded-r-lg"
      {...props}
    />
  ),
  a: ({ href, children }: any): React.JSX.Element => {
    const rawText = getNodeText(children).trim();
    const rawHref = String(href || '').trim();

    // 1. SUPREME COURT PRECEDENTS (PML, Rev, AC, CA, AGJ, PKR)
    const isPrecedent =
      /\b(PML|Rev|AC|CA|PKR|AP|AGJ)\.?\s*(?:Nr\.?|nr\.?)\s*(\d+\/\d{2,4})\b/i.test(rawText) ||
      rawHref.includes('/laws/library?q=') ||
      rawHref.includes('/laws/search?q=') ||
      rawHref.includes('caseNumber=');

    if (isPrecedent) {
      const cleanLabel = rawText.replace(/^\[+|\]+$/g, '').trim();

      return (
        <span className="inline-flex items-center align-baseline mx-0.5 my-0.5">
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              window.dispatchEvent(
                new CustomEvent('open_precedent_preview', {
                  detail: { caseNumber: cleanLabel }
                })
              );
            }}
            // Hequr atributi 'title' për të shmangur native tooltip të browser-it
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-500 hover:text-amber-400 font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 shadow-xs cursor-pointer focus:outline-none"
          >
            <Landmark size={12} className="shrink-0 text-amber-500" />
            <span className="truncate max-w-[260px] sm:max-w-[340px]">{cleanLabel}</span>
          </button>
        </span>
      );
    }

    // 2. STATUTE ARTICLE LINKS (Kalon tek LawCitationLink ku ndodhet Hover-i i ri)
    if (rawHref.startsWith('/laws/article') || rawHref.startsWith('/laws/')) {
      try {
        const url = new URL(rawHref, window.location.origin);
        const lawTitle = url.searchParams.get('lawTitle') || 'Ligj i Paidentifikuar';
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

    // 3. EVIDENCE DOCUMENT LINKS
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
          // Hequr 'title'
          className="inline-flex items-center gap-1.5 px-2.5 py-0.5 mx-1 my-0.5 rounded-lg bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start font-bold text-xs transition-all hover:scale-[1.02] active:scale-95 cursor-pointer focus:outline-none shadow-sm align-baseline"
        >
          <FileText size={12} className="shrink-0 text-primary-start" />
          <span className="underline decoration-primary-start/40">{rawText || children}</span>
        </button>
      );
    }

    // 4. GENERIC EXTERNAL LINKS
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        // Hequr 'title'
        className="inline-flex items-center gap-1 text-primary-start font-semibold underline decoration-primary-start/30 hover:decoration-primary-start transition-colors mx-0.5"
      >
        <span>{children}</span>
        <ExternalLink size={11} className="shrink-0 opacity-70" />
      </a>
    );
  },
});

export default buildMarkdownComponents;