// FILE: src/drafting/components/DraftResultRenderer.tsx
// PHOENIX PROTOCOL - DRAFT RENDERER V2.5 (FORCE BLACK TEXT)

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
      <div className="legal-content text-black [&>*]:text-black [&_strong]:text-black [&_h1]:text-black [&_h2]:text-black [&_h3]:text-black [&_p]:text-black">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ node, ...props }) => <h1 {...props} className="text-black font-bold uppercase text-center mb-6 text-xl" />,
            h2: ({ node, ...props }) => <h2 {...props} className="text-black font-bold uppercase text-center my-4 text-lg" />,
            h3: ({ node, ...props }) => <h3 {...props} className="text-black font-bold uppercase my-3" />,
            strong: ({ node, ...props }) => <strong {...props} className="text-black font-bold" />,
            p: ({ node, ...props }) => {
              const content = String(props.children);
              if (content.includes('AI') || content.includes('referencë')) {
                return (
                  <p className="text-center italic mt-12 pt-4 border-t border-gray-300 text-xs text-gray-500">
                    {disclaimer}
                  </p>
                );
              }
              return <p {...props} className="text-black mb-4 leading-relaxed" />;
            },
          }}
        >
          {processedText}
        </ReactMarkdown>
      </div>
    </div>
  );
});