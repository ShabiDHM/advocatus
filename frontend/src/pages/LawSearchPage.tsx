// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - LAW SEARCH V19.0 (DIRECT STATUTORY LAW DIRECTORY - ZERO HALLUCINATIONS)

import { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, Scale, ArrowLeft, ChevronRight, BookOpen, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { motion } from 'framer-motion';

const DEFAULT_STATUTORY_LAWS = [
  "KUSHTETUTA E REPUBLIKËS SË KOSOVËS",
  "KODI NR. 06/L-074 KODI PENAL I REPUBLIKËS SË KOSOVËS",
  "KODI NR. 08/L-032 I PROCEDURËS PENALE",
  "KODI NR. 06/L-006 I DREJTËSISË PËR TË MITUR",
  "LIGJI NR. 03/L-006 PËR PROCEDURËN KONTESTIMORE",
  "LIGJI NR. 04/L-077 PËR MARRËDHËNIET E DETYRIMEVE",
  "LIGJI NR. 04/L-139 PËR PROCEDURËN PËRMBARIMORE",
  "LIGJI NR. 04/L-161 PËR SIGURINË DHE SHËNDETIN NË PUNË",
  "LIGJI NR. 05/L-029 PËR TATIMIN NË TË ARDHURAT E KORPORATAVE",
  "LIGJI NR. 06/L-016 PËR SHOQËRITË TREGTARE",
  "LIGJI NR. 06/L-082 PËR MBROJTJEN E TË DHËNAVE PERSONALE",
  "LIGJI NR. 06/L-084 PËR MBROJTJEN E FËMIJËS",
  "LIGJI NR. 08/L-257 PËR ADMINISTRIMIN E PROCEDURAVE TATIMORE",
  "LIGJI NR. 2004/32 LIGJI PËR FAMILJEN I KOSOVËS",
  "LIGJI NR. 03/L-212 I PUNËS"
];

function normalizeForDisplay(title: string): string {
  return title.trim().replace(/\s+/g, ' ');
}

export default function LawSearchPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [filterQuery, setFilterQuery] = useState('');
  const [statuteTitles, setStatuteTitles] = useState<string[]>(DEFAULT_STATUTORY_LAWS);
  const [loadingTitles, setLoadingTitles] = useState(false);

  useEffect(() => {
    setLoadingTitles(true);
    apiService.getLawTitles()
      .then((res: any) => {
        if (res) {
          const apiStatutes = res.statutes || res.all_titles || [];
          if (apiStatutes.length > 0) {
            const merged = new Set([...apiStatutes, ...DEFAULT_STATUTORY_LAWS]);
            setStatuteTitles(Array.from(merged));
          }
        }
      })
      .catch((err) => {
        console.warn("[LawSearchPage] Using default Kosovo statutes fallback:", err);
      })
      .finally(() => setLoadingTitles(false));
  }, []);

  const filteredStatutes = useMemo(() => {
    if (!filterQuery.trim()) return statuteTitles;
    const lower = filterQuery.toLowerCase();
    return statuteTitles.filter(title => normalizeForDisplay(title).toLowerCase().includes(lower));
  }, [statuteTitles, filterQuery]);

  const handleOpenLaw = (lawTitle: string) => {
    navigate(`/laws/overview?lawTitle=${encodeURIComponent(lawTitle)}`);
  };

  return (
    <motion.div className="w-full min-h-screen pb-16 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-6xl mx-auto px-4 sm:px-8 pt-28">
        
        {/* Navigation & Header */}
        <div className="flex flex-col gap-4 mb-8">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface/40 border border-border-main text-text-secondary hover:text-text-primary transition-colors hover-lift shadow-sm w-fit cursor-pointer"
          >
            <ArrowLeft size={16} />
            <span className="text-xs font-black uppercase tracking-widest">{t('general.back', 'Kthehu')}</span>
          </button>

          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <div className="flex items-center gap-2 text-primary-start mb-1">
                <ShieldCheck size={18} />
                <span className="text-[10px] font-black uppercase tracking-widest">VERIFIKIM ZYRTAR (100%)</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-text-primary tracking-tight">
                Biblioteka e Kodeve dhe Ligjeve Zyrtare
              </h1>
            </div>
            
            <div className="px-4 py-2 bg-primary-start/10 border border-primary-start/20 rounded-xl text-primary-start font-mono text-xs font-bold">
              {statuteTitles.length} Kodet Zyrtare
            </div>
          </div>
        </div>

        {/* Filter Input Bar */}
        <div className="glass-panel p-4 sm:p-6 mb-8 shadow-sm border border-border-main bg-surface rounded-3xl">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-primary-start pointer-events-none" />
            <input
              type="text"
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Filtro sipas emrit të ligjit (p.sh. Penal, Procedurë, Familjen, Punës)..."
              className="w-full pl-12 pr-12 py-4 bg-canvas border border-border-main rounded-2xl text-sm sm:text-base font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all"
              autoFocus
            />
            {filterQuery && (
              <button
                type="button"
                onClick={() => setFilterQuery('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-text-muted hover:text-danger-start transition-colors p-1"
              >
                <X className="h-5 w-5" />
              </button>
            )}
          </div>
        </div>

        {/* Law Cards Directory Grid */}
        {loadingTitles ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="glass-panel p-6 rounded-2xl animate-pulse bg-surface/50 border border-border-main h-24" />
            ))}
          </div>
        ) : filteredStatutes.length === 0 ? (
          <div className="glass-panel p-12 text-center border border-border-main rounded-3xl bg-surface flex flex-col items-center">
            <BookOpen className="h-12 w-12 text-text-muted mb-3" />
            <p className="text-text-primary font-bold text-base">Nuk u gjet asnjë ligj me këtë emër</p>
            <p className="text-xs text-text-muted mt-1">Provoni një fjalë tjetër si "Penal", "Civil", ose "Kushtetuta"</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredStatutes.map((lawTitle, idx) => {
              const displayTitle = normalizeForDisplay(lawTitle);
              return (
                <div
                  key={idx}
                  onClick={() => handleOpenLaw(lawTitle)}
                  className="glass-panel p-5 sm:p-6 rounded-2xl border border-border-main hover:border-primary-start/60 bg-surface hover:bg-hover transition-all group flex items-center justify-between gap-4 cursor-pointer hover-lift shadow-xs"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="p-3 rounded-xl bg-primary-start/10 text-primary-start border border-primary-start/20 shrink-0 group-hover:bg-primary-start group-hover:text-white transition-colors">
                      <Scale size={20} />
                    </div>
                    <div className="min-w-0">
                      <span className="text-[9px] font-mono text-primary-start font-black uppercase tracking-wider block mb-0.5">
                        KODI LIGJOR ZYRTAR
                      </span>
                      <h3 className="text-xs sm:text-sm font-black text-text-primary group-hover:text-primary-start transition-colors leading-snug line-clamp-2">
                        {displayTitle}
                      </h3>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0 text-primary-start">
                    <span className="text-xs font-bold hidden sm:inline group-hover:underline">Lexo Kodin</span>
                    <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>
    </motion.div>
  );
}