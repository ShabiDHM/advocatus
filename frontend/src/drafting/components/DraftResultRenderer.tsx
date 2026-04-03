// FILE: src/drafting/components/DraftResultRenderer.tsx
// ARCHITECTURE: PROFESSIONAL LEGAL FORMATTING & INLINE HIGHLIGHTERS (FIXED SPACING & OVERFLOW)

import React from 'react';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const highlightPlaceholders = (text: string) => {
  if (!text) return text;
  const parts = text.split(/(\[[^\]]+\])/g);
  return parts.map((part, i) => {
    if (part.startsWith('[') && part.endsWith(']')) {
      return (
        <span 
          key={i} 
          className="bg-yellow-100 text-yellow-900 border border-yellow-300 px-1 py-0.5 rounded-sm font-bold shadow-sm mx-0.5"
          title="Të dhëna që duhet të plotësohen"
        >
          {part}
        </span>
      );
    }
    return part;
  });
};

export const DraftResultRenderer: React.FC<{ text: string; t: TFunction }> = React.memo(({ text, t }) => {
  const disclaimer = t('drafting.subtitle', 'Kjo përgjigje është gjeneruar nga Juristi AI, vetëm për referencë.');

  return (
    <div className="legal-document flex flex-col h-full font-serif w-full max-w-full">
      <div className="legal-content text-black flex-1 w-full overflow-x-auto">
        <style>
          {`
            .legal-content .markdown-body {
              word-wrap: break-word;
              word-break: break-word;
              white-space: normal;
              overflow-wrap: break-word;
            }
            .legal-content p, .legal-content li, .legal-content h1, .legal-content h2, .legal-content h3 {
              word-wrap: break-word;
              word-break: break-word;
              white-space: normal;
            }
          `}
        </style>
        <div className="markdown-body w-full max-w-full">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Reduced margins for headings
              h1: ({ node, ...props }) => <h1 {...props} className="text-black font-black uppercase text-center mb-4 text-xl tracking-wide" />,
              h2: ({ node, ...props }) => <h2 {...props} className="text-black font-bold uppercase text-center mt-4 mb-3 text-lg" />,
              h3: ({ node, ...props }) => <h3 {...props} className="text-black font-bold uppercase mt-3 mb-2 text-base" />,
              
              strong: ({ node, ...props }) => <strong {...props} className="text-black font-black" />,
              
              p: ({ node, children, ...props }) => {
                return (
                  <p {...props} className="text-black mb-2 leading-relaxed text-justify whitespace-normal break-words">
                    {React.Children.map(children, child => {
                      if (typeof child === 'string') {
                        return highlightPlaceholders(child);
                      }
                      return child;
                    })}
                  </p>
                );
              },
              
              // Reduced list spacing and padding
              ul: ({ node, ...props }) => <ul {...props} className="list-disc pl-5 mb-2 space-y-1 text-black text-justify break-words" />,
              ol: ({ node, ...props }) => <ol {...props} className="list-decimal pl-5 mb-2 space-y-1 text-black text-justify break-words" />,
              li: ({ node, children, ...props }) => (
                <li {...props} className="text-black leading-relaxed pl-1 break-words">
                  {React.Children.map(children, child => {
                    if (typeof child === 'string') {
                      return highlightPlaceholders(child);
                    }
                    return child;
                  })}
                </li>
              ),
              
              blockquote: ({ node, ...props }) => (
                <blockquote {...props} className="border-l-4 border-gray-400 pl-4 py-1 my-3 text-gray-800 italic bg-gray-50 break-words" />
              ),
              
              code: ({ node, inline, ...props }: any) => {
                if (inline) {
                  return <code {...props} className="font-mono text-sm bg-gray-100 px-1 rounded text-black break-words" />;
                }
                return <code {...props} className="block bg-gray-100 p-3 rounded-lg my-3 font-mono text-sm text-black overflow-x-auto whitespace-pre-wrap break-words" />;
              }
            }}
          >
            {text}
          </ReactMarkdown>
        </div>
      </div>
      
      {/* Footer Disclaimer - reduced top margin */}
      <div className="mt-8 pt-3 border-t border-gray-300 text-center shrink-0">
        <p className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">
          {disclaimer}
        </p>
      </div>
    </div>
  );
});