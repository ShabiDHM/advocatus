// FILE: src/components/law/LawArticleContent.tsx
// PHOENIX PROTOCOL - RESPONSIVE MOBILE & TABLET LAW ARTICLE CONTENT

import React from 'react';
import { FileText, ExternalLink } from 'lucide-react';
import { ArticleData } from './lawArticleTypes';
import { TFunction } from 'i18next';

interface LawArticleContentProps {
  article: ArticleData;
  rawArtNum: string;
  onOpenPdf: () => void;
  t: TFunction;
}

export const LawArticleContent: React.FC<LawArticleContentProps> = ({
  article,
  rawArtNum,
  onOpenPdf,
  t,
}) => {
  const isPreamble =
    rawArtNum === '0' ||
    rawArtNum.toLowerCase() === 'preambula' ||
    rawArtNum.toLowerCase() === 'hyrja';

  const articleHeading = isPreamble ? 'Preambula' : `${t('lawArticle.article', 'Neni')} ${rawArtNum}`;

  return (
    <div className="flex flex-col overflow-hidden shadow-sm border border-main rounded-2xl bg-canvas">
      {/* Header i Ligjit */}
      <div className="px-4 sm:px-8 py-4 sm:py-6 border-b border-main bg-surface/50">
        <div className="flex flex-col gap-3">
          <div className="flex items-center">
            <button
              type="button"
              onClick={onOpenPdf}
              className="h-8 sm:h-9 px-3 sm:px-3.5 flex items-center gap-1.5 sm:gap-2 bg-primary-start/10 hover:bg-primary-start/20 text-primary-start border border-primary-start/30 rounded-xl text-[11px] sm:text-xs font-semibold transition-all hover-lift cursor-pointer"
              title="Shiko dokumentin PDF të plotë"
            >
              <FileText size={13} />
              <span>Dokumenti PDF</span>
              <ExternalLink size={11} className="opacity-80 shrink-0" />
            </button>
          </div>

          {/* Titulli Kryesor me Font Dinamik */}
          <h1 className="text-base sm:text-xl md:text-2xl font-black text-text-primary leading-snug tracking-tight">
            {article.law_title}
          </h1>
        </div>
      </div>

      {/* Fleta e Dokumentit me Përshtatje të Plotë në Mobile */}
      <div className="px-2 sm:px-6 md:px-8 py-4 sm:py-10 flex justify-center bg-canvas">
        <div className="w-full max-w-[85ch] bg-surface border border-main rounded-2xl shadow-md p-4 sm:p-10 md:p-12 relative">
          
          {/* Titulli i Nenit */}
          <div className="text-center pb-4 sm:pb-5 mb-5 sm:mb-7 border-b border-main">
            <h2 className="text-xl sm:text-2xl md:text-3xl font-black text-text-primary uppercase tracking-wide font-serif">
              {articleHeading}
            </h2>
          </div>

          {/* Teksti i Nenit me Tipografi të Qartë */}
          <div className="text-[14px] sm:text-[16px] md:text-[17px] text-text-primary leading-[1.75] sm:leading-[1.85] font-normal whitespace-pre-line text-left font-serif tracking-normal selection:bg-primary-start/20">
            {article.text}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LawArticleContent;