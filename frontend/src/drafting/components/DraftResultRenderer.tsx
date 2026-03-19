// src/drafting/components/DraftResultRenderer.tsx
import React from 'react';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const preprocessHeadings = (text: string): string => {
  const lines = text.split('\n');
  const knownSections = ['BAZA LIGJORE', 'ARSYETIMI', 'PETITUMI', 'KONKLUZIONI', 'VENDIM', 'NENET'];
  return lines.map(line => {
    const trimmed = line.trim();
    if (trimmed.length === 0) return line;
    if (trimmed.toUpperCase().startsWith('NËNSHKRIMI') || trimmed.toUpperCase().startsWith('NENSHKRIMI')) return `> ${trimmed}`;
    const isUppercase = /^[A-ZËÇÜÖÄ\s\d\.,\-–—:]+$/.test(trimmed);
    if (!isUppercase) return line;
    const withoutColon = trimmed.replace(/:$/, '').toUpperCase();
    if (knownSections.some(s => withoutColon.includes(s))) {
      return `### ${trimmed.endsWith(':') ? trimmed : `${trimmed}:`}`;
    }
    if (trimmed.length < 100) return `## ${line}`;
    return line;
  }).join('\n');
};

export const DraftResultRenderer: React.FC<{ text: string; t: TFunction }> = React.memo(({ text, t }) => {
  const processedText = preprocessHeadings(text);
  const disclaimer = t('drafting.subtitle');

  return (
    <div className="legal-document">
      <div className="legal-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ node, ...props }) => <h1 {...props} />,
            h2: ({ node, ...props }) => <h2 {...props} />,
            h3: ({ node, ...props }) => <h3 {...props} />,
            blockquote: ({ node, ...props }) => <blockquote {...props} />,
            strong: ({ node, ...props }) => <strong {...props} />,
            p: ({ node, ...props }) => {
              const content = String(props.children);
              if (content.includes('AI') || content.includes('referencë')) {
                return (
                  <p className="text-center italic mt-12 pt-4 border-t border-black text-[9pt] opacity-60">
                    {disclaimer}
                  </p>
                );
              }
              return <p {...props} />;
            },
          }}
        >
          {processedText}
        </ReactMarkdown>
      </div>
    </div>
  );
});