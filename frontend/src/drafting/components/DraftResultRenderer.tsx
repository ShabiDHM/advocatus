// FILE: src/drafting/components/DraftResultRenderer.tsx
// ARCHITECTURE: PROFESSIONAL LEGAL FORMATTING & SMART PLACEHOLDERS

import React from 'react';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const preprocessLegalText = (text: string): string => {
  // Highlight Placeholders: Safely converts [PLACEHOLDER] into inline markdown code `[PLACEHOLDER]`
  // The Regex ignores standard Markdown links [text](url) and images ![alt](url)
  let processed = text.replace(/(?<!\!)\[([^\]]+)\](?!\()/g, '`[$1]`');
  
  // Ensure signature blocks align cleanly (double line breaks before them)
  processed = processed.replace(/(PËR PALËN|NËNSHKRIMI|PËR PËRFAQËSUESIN):/gi, '\n\n**$1:**');
  
  return processed;
};

export const DraftResultRenderer: React.FC<{ text: string; t: TFunction }> = React.memo(({ text, t }) => {
  const processedText = preprocessLegalText(text);
  const disclaimer = t('drafting.subtitle', 'Ky dokument është gjeneruar nga inteligjenca artificiale. Ju lutemi rishikojeni me kujdes para përdorimit zyrtar.');

  return (
    <div className="legal-document flex flex-col h-full">
      <div className="legal-content text-black flex-1">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // Headings: Clean, bold, uppercase, centered for H1/H2
            h1: ({ node, ...props }) => <h1 {...props} className="text-black font-black uppercase text-center mb-8 text-xl tracking-wide" />,
            h2: ({ node, ...props }) => <h2 {...props} className="text-black font-bold uppercase text-center mt-8 mb-4 text-lg" />,
            h3: ({ node, ...props }) => <h3 {...props} className="text-black font-bold uppercase mt-6 mb-3 text-base" />,
            
            // Text constraints: Justified text is mandatory for legal contracts
            strong: ({ node, ...props }) => <strong {...props} className="text-black font-black" />,
            p: ({ node, ...props }) => <p {...props} className="text-black mb-4 leading-relaxed text-justify" />,
            
            // Lists: Properly indented for legal articles and clauses
            ul: ({ node, ...props }) => <ul {...props} className="list-disc pl-8 mb-4 space-y-2 text-black text-justify" />,
            ol: ({ node, ...props }) => <ol {...props} className="list-decimal pl-8 mb-4 space-y-2 text-black text-justify" />,
            li: ({ node, ...props }) => <li {...props} className="text-black leading-relaxed pl-2" />,
            
            // Smart Placeholders: Rendered as bright yellow blocks so they cannot be missed before printing
            code: ({ node, inline, ...props }: any) => {
              if (inline) {
                return (
                  <code 
                    {...props} 
                    className="bg-warning-start/20 text-warning-start border border-warning-start/30 px-1.5 py-0.5 rounded font-bold font-mono text-[0.9em] shadow-sm" 
                  />
                );
              }
              return <code {...props} className="block bg-gray-100 p-4 rounded-lg my-4 font-mono text-sm text-black" />;
            },
            
            // Blockquotes: Used for indented legal citations
            blockquote: ({ node, ...props }) => (
              <blockquote {...props} className="border-l-4 border-gray-400 pl-4 py-1 my-4 text-gray-800 italic bg-gray-50" />
            )
          }}
        >
          {processedText}
        </ReactMarkdown>
      </div>
      
      {/* Footer Disclaimer - Safely placed outside markdown parsing to prevent data loss */}
      <div className="mt-16 pt-4 border-t border-gray-300 text-center shrink-0">
        <p className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">
          {disclaimer}
        </p>
      </div>
    </div>
  );
});