// FILE: src/components/chat/MarkdownRenderer.tsx
// PHOENIX PROTOCOL - MARKDOWN RENDERER V32.0 (INSTANT EVIDENCE DOCUMENT PREVIEW LINK HANDLER)

import React from 'react';
import { LawCitationLink } from '../LawCitationLink';
import { FileText } from 'lucide-react';

export const buildMarkdownComponents = () => ({
  h1: ({ node, ...props }: any): React.JSX.Element => (
    <h1 className="text-lg font-bold text-text-primary mb-2 mt-3 border-b border-main pb-1 uppercase tracking-tight" {...props} />
  ),
  h2: ({ node, ...props }: any): React.JSX.Element => (
    <h2 className="text-base font-semibold text-primary-start mb-1.5 mt-2" {...props} />
  ),
  h3: ({ node, ...props }: any): React.JSX.Element => (
    <h3 className="text-sm font-semibold text-text-primary mb-1 mt-1.5 flex items-center gap-2" {...props} />
  ),
  p: ({ node, ...props }: any): React.JSX.Element => (
    <p className="mb-2 last:mb-0 leading-relaxed text-text-secondary" {...props} />
  ),
  li: ({ node, ...props }: any): React.JSX.Element => (
    <li className="mb-1 leading-relaxed text-text-secondary" {...props} />
  ),
  a: ({ href, children }: any): React.JSX.Element => {
    const rawText = String(children || '').trim();
    const rawHref = String(href || '').trim();

    // 1. LAW CITATIONS (/laws/...)
    if (rawHref.startsWith('/laws/')) {
      try {
        const url = new URL(rawHref, window.location.origin);
        const lawTitle = url.searchParams.get('lawTitle') || 'Ligj i Paidentifikuar';
        const articleNum = url.searchParams.get('articleNumber') || '1';
        const fullMatch = String(children || `${lawTitle} - Neni ${articleNum}`);

        return <LawCitationLink lawTitle={lawTitle} articleNum={articleNum} fullMatch={fullMatch} targetUrl={rawHref} />;
      } catch {
        return <LawCitationLink lawTitle="Ligj" articleNum="1" fullMatch={String(children || 'Referencë Ligjore')} targetUrl={rawHref} />;
      }
    }

    // 2. EVIDENCE DOCUMENT CITATION PILLS (e.g. .pdf, .jpg, .doc, or file links in chat)
    const isDocLink = rawHref.toLowerCase().endsWith('.pdf') || 
                      rawText.toLowerCase().endsWith('.pdf') || 
                      rawHref.includes('/documents/') ||
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
          className="inline-flex items-center gap-1.5 px-2 py-0.5 my-0.5 rounded-lg bg-primary-start/10 hover:bg-primary-start/20 border border-primary-start/30 text-primary-start font-bold text-xs transition-all hover-lift cursor-pointer focus:outline-none"
          title="Klikoni për të hapur skedarin e provës"
        >
          <FileText size={12} className="shrink-0" />
          <span className="underline decoration-primary-start/40">{children}</span>
        </button>
      );
    }

    // 3. GENERIC EXTERNAL LINKS
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary-start font-semibold underline decoration-primary-start/30 hover:decoration-primary-start transition-colors"
      >
        {children}
      </a>
    );
  },
});