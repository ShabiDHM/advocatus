// FILE: src/drafting/components/DraftResultRenderer.tsx
// ARCHITECTURE: PROFESSIONAL LEGAL FORMATTING & INLINE HIGHLIGHTERS

import React from 'react';
import { TFunction } from 'i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// ============================================================================
// LEGAL TEXT PARSER: PROFESSIONAL PLACEHOLDER HIGHLIGHTING
// ============================================================================
// Instead of hacking the markdown syntax with backticks, we safely parse 
// text nodes and apply a professional yellow "highlighter" to bracketed text.
const highlightPlaceholders = (text: string) => {
  if (!text) return text;
  
  // Split the text by brackets: e.g., "Më datë [DATA] në [QYTETI]"
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
    <div className="legal-document flex flex-col h-full font-serif">
      <div className="legal-content text-black flex-1">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // Typography Enforcements: Professional, solid black text.
            h1: ({ node, ...props }) => <h1 {...props} className="text-black font-black uppercase text-center mb-8 text-xl tracking-wide" />,
            h2: ({ node, ...props }) => <h2 {...props} className="text-black font-bold uppercase text-center mt-8 mb-4 text-lg" />,
            h3: ({ node, ...props }) => <h3 {...props} className="text-black font-bold uppercase mt-6 mb-3 text-base" />,
            
            // Text constraints: Justified text is mandatory for legal contracts
            strong: ({ node, ...props }) => <strong {...props} className="text-black font-black" />,
            
            // Parse Paragraphs for Placeholders
            p: ({ node, children, ...props }) => {
              return (
                <p {...props} className="text-black mb-4 leading-relaxed text-justify whitespace-pre-wrap">
                  {React.Children.map(children, child => {
                    if (typeof child === 'string') {
                      return highlightPlaceholders(child);
                    }
                    return child;
                  })}
                </p>
              );
            },
            
            // Parse Lists for Placeholders
            ul: ({ node, ...props }) => <ul {...props} className="list-disc pl-8 mb-4 space-y-2 text-black text-justify" />,
            ol: ({ node, ...props }) => <ol {...props} className="list-decimal pl-8 mb-4 space-y-2 text-black text-justify" />,
            li: ({ node, children, ...props }) => (
              <li {...props} className="text-black leading-relaxed pl-2">
                {React.Children.map(children, child => {
                  if (typeof child === 'string') {
                    return highlightPlaceholders(child);
                  }
                  return child;
                })}
              </li>
            ),
            
            // Blockquotes: Used for indented legal citations
            blockquote: ({ node, ...props }) => (
              <blockquote {...props} className="border-l-4 border-gray-400 pl-4 py-1 my-4 text-gray-800 italic bg-gray-50" />
            ),

            // Ensure actual code blocks (if the AI hallucinates them) don't break the UI
            code: ({ node, inline, ...props }: any) => {
              if (inline) {
                return <code {...props} className="font-mono text-sm bg-gray-100 px-1 rounded text-black" />;
              }
              return <code {...props} className="block bg-gray-100 p-4 rounded-lg my-4 font-mono text-sm text-black overflow-x-auto whitespace-pre-wrap" />;
            }
          }}
        >
          {text}
        </ReactMarkdown>
      </div>
      
      {/* Footer Disclaimer */}
      <div className="mt-16 pt-4 border-t border-gray-300 text-center shrink-0">
        <p className="text-[10px] uppercase tracking-widest text-gray-500 font-bold">
          {disclaimer}
        </p>
      </div>
    </div>
  );
});