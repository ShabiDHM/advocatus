// FILE: src/components/chat/MarkdownRenderer.tsx
import React from 'react';
import { LawCitationLink } from '../LawCitationLink';

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
    if (href?.startsWith('/laws/')) {
      try {
        const url = new URL(href, window.location.origin);
        const lawTitle = url.searchParams.get('lawTitle') || 'Ligj i Paidentifikuar';
        const articleNum = url.searchParams.get('articleNumber') || '1';
        const fullMatch = String(children || `${lawTitle} - Neni ${articleNum}`);

        return <LawCitationLink lawTitle={lawTitle} articleNum={articleNum} fullMatch={fullMatch} targetUrl={href} />;
      } catch {
        return <LawCitationLink lawTitle="Ligj" articleNum="1" fullMatch={String(children || 'Referencë Ligjore')} targetUrl={href} />;
      }
    }
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