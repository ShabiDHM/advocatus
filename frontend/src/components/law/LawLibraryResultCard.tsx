// FILE: src/components/law/LawLibraryResultCard.tsx
import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Scale, ArrowRight, Link as LinkIcon } from 'lucide-react';
import { LawResult } from './lawLibraryTypes';

interface LawLibraryResultCardProps {
  result: LawResult;
  index: number;
}

export const LawLibraryResultCard: React.FC<LawLibraryResultCardProps> = ({ result, index }) => {
  const articleNum = result.article_number || '1';
  const articleUrl = `/laws/article?lawTitle=${encodeURIComponent(result.law_title)}&articleNumber=${encodeURIComponent(
    articleNum
  )}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      key={result.chunk_id || index}
    >
      <Link
        to={articleUrl}
        className="glass-panel p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 group hover-lift border border-main hover:border-primary-start/60 rounded-2xl bg-surface"
      >
        <div className="flex flex-col gap-2 flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="bg-primary-start/10 text-primary-start border border-primary-start/20 px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider flex items-center gap-1.5">
              <Scale size={12} /> Referencë Ligjore
            </span>
            {result.article_number && (
              <span className="bg-canvas text-text-primary border border-main px-2.5 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider">
                Neni {result.article_number}
              </span>
            )}
          </div>

          <h2 className="text-base sm:text-lg font-black text-text-primary group-hover:text-primary-start transition-colors truncate">
            {result.law_title}
          </h2>

          {result.text && <p className="text-xs sm:text-sm text-text-secondary line-clamp-2 leading-relaxed">{result.text}</p>}

          {result.source && (
            <div className="flex items-center gap-2 mt-0.5">
              <LinkIcon size={12} className="text-text-muted" />
              <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider truncate max-w-xl">
                {result.source}
              </span>
            </div>
          )}
        </div>

        <div className="hidden sm:flex w-10 h-10 rounded-xl bg-canvas border border-main items-center justify-center text-text-muted group-hover:text-white group-hover:bg-primary-start group-hover:border-primary-start transition-all shrink-0">
          <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
        </div>
      </Link>
    </motion.div>
  );
};