// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - LAW SEARCH V36.0 (CLEAN TYPESCRIPT COMMENTS)

import { useState, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, Scale, ArrowLeft, ChevronDown, Check, ShieldCheck, GraduationCap, Gavel } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import FileViewerModal from '../components/FileViewerModal';

const OFFICIAL_STATUTORY_LAWS = [
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

const DEFAULT_ACADEMIC_LAWS: string[] = [];

function normalizeForDisplay(title: string): string {
  return title.trim().replace(/\s+/g, ' ');
}

export default function LawSearchPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState<'statutes' | 'academic' | 'caselaw'>('statutes');
  const [filterQuery, setFilterQuery] = useState('');
  const [statuteTitles, setStatuteTitles] = useState<string[]>(OFFICIAL_STATUTORY_LAWS);
  const [academicTitles, setAcademicTitles] = useState<string[]>(DEFAULT_ACADEMIC_LAWS);
  const [caselawTitles, setCaselawTitles] = useState<string[]>([]);
  
  const [isOpen, setIsOpen] = useState(false);
  const [selectedPdfFilename, setSelectedPdfFilename] = useState<string | null>(null);
  const [initialPageNumber, setInitialPageNumber] = useState<number>(1);
  const [showPdfModal, setShowPdfModal] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiService.getLawTitles()
      .then((res: any) => {
        if (res) {
          if (res.statutes && res.statutes.length > 0) {
            setStatuteTitles(Array.from(new Set([...res.statutes, ...OFFICIAL_STATUTORY_LAWS])));
          }
          if (res.academic_manuals && Array.isArray(res.academic_manuals)) {
            setAcademicTitles(res.academic_manuals);
          }
          if (res.case_law && Array.isArray(res.case_law)) {
            setCaselawTitles(res.case_law);
          }
        }
      })
      .catch((err) => {
        console.warn("[LawSearchPage] Using default Kosovo statutes fallback:", err);
      });
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeList = useMemo(() => {
    if (activeTab === 'academic') return academicTitles;
    if (activeTab === 'caselaw') return caselawTitles;
    return statuteTitles;
  }, [activeTab, statuteTitles, academicTitles, caselawTitles]);

  const filteredTitles = useMemo(() => {
    if (!filterQuery.trim()) return activeList;
    const lower = filterQuery.toLowerCase();
    return activeList.filter(title => normalizeForDisplay(title).toLowerCase().includes(lower));
  }, [activeList, filterQuery]);

  const handleSelectLaw = async (lawTitle: string) => {
    setIsOpen(false);

    if (activeTab === 'academic' || activeTab === 'caselaw' || lawTitle.toLowerCase().endsWith('.pdf')) {
      setSelectedPdfFilename(lawTitle);

      // Query starting page for this case or document
      try {
        const res = await apiService.axiosInstance.get('/laws/case-page', { params: { law_title: lawTitle } });
        if (res.data && res.data.page) {
          setInitialPageNumber(res.data.page);
        } else {
          setInitialPageNumber(1);
        }
      } catch {
        setInitialPageNumber(1);
      }

      setShowPdfModal(true);
    } else {
      navigate(`/laws/overview?lawTitle=${encodeURIComponent(lawTitle)}`);
    }
  };

  const pdfUrl = useMemo(() => {
    if (!selectedPdfFilename) return null;
    
    const nameWithPdf = selectedPdfFilename.toLowerCase().endsWith('.pdf') 
      ? selectedPdfFilename 
      : `${selectedPdfFilename}.pdf`;

    const encoded = encodeURIComponent(nameWithPdf);

    if (activeTab === 'academic') {
      return `${API_V1_URL}/laws/academia/pdf/${encoded}`;
    }
    if (activeTab === 'caselaw') {
      return `${API_V1_URL}/laws/caselaw/pdf/${encoded}`;
    }
    return `${API_V1_URL}/laws/pdf/${encoded}`;
  }, [selectedPdfFilename, activeTab]);

  const modalFilename = useMemo(() => {
    if (!selectedPdfFilename) return 'DokumentLigjor.pdf';
    return selectedPdfFilename.toLowerCase().endsWith('.pdf')
      ? selectedPdfFilename
      : `${selectedPdfFilename}.pdf`;
  }, [selectedPdfFilename]);

  return (
    <motion.div className="w-full min-h-screen pb-16 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-4xl mx-auto px-4 sm:px-8 pt-28">
        
        {/* Navigation & Header */}
        <div className="flex flex-col gap-4 mb-6">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface/40 border border-main text-text-secondary hover:text-text-primary transition-colors hover-lift shadow-sm w-fit cursor-pointer"
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
                Zgjidh Materialin Ligjor
              </h1>
            </div>
            
            <div className="px-4 py-2 bg-primary-start/10 border border-primary-start/20 rounded-xl text-primary-start font-mono text-xs font-bold">
              {activeList.length} {activeTab === 'statutes' ? 'Kodet Zyrtare' : activeTab === 'academic' ? 'Udhëzues' : 'Aktgjykime'}
            </div>
          </div>
        </div>

        {/* ALL 3 CATEGORY SWITCHER TABS */}
        <div className="flex items-center gap-2 mb-6 bg-surface p-1.5 rounded-2xl border border-main shadow-sm overflow-x-auto">
          <button
            type="button"
            onClick={() => { setActiveTab('statutes'); setIsOpen(false); setFilterQuery(''); }}
            className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
              activeTab === 'statutes' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Scale size={15} />
            <span>Kodet Zyrtare ({statuteTitles.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('academic'); setIsOpen(false); setFilterQuery(''); }}
            className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
              activeTab === 'academic' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <GraduationCap size={15} />
            <span>Akademia e Drejtësisë ({academicTitles.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('caselaw'); setIsOpen(false); setFilterQuery(''); }}
            className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
              activeTab === 'caselaw' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Gavel size={15} />
            <span>Aktgjykimet ({caselawTitles.length})</span>
          </button>
        </div>

        {/* SELECTOR CONTAINER */}
        <div className="glass-panel p-6 sm:p-8 mb-12 shadow-sm border border-main bg-surface rounded-3xl relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="w-full flex items-center justify-between px-6 py-5 bg-canvas border border-main hover:border-primary-start/60 rounded-2xl shadow-sm text-sm sm:text-base font-bold text-text-primary transition-all group hover-lift cursor-pointer"
          >
            <div className="flex items-center gap-3.5 min-w-0 pr-4">
              <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl shrink-0 border border-primary-start/20">
                {activeTab === 'academic' ? <GraduationCap size={20} /> : activeTab === 'caselaw' ? <Gavel size={20} /> : <Scale size={20} />}
              </div>
              <span className="truncate text-left font-bold text-sm sm:text-base text-text-primary">
                {activeTab === 'academic'
                  ? 'Zgjidh udhëzuesin nga Akademia e Drejtësisë...'
                  : activeTab === 'caselaw'
                  ? 'Zgjidh aktgjykimin apo praktikën gjyqësore...'
                  : 'Zgjidh ligjin zyrtar nga lista...'}
              </span>
            </div>

            <ChevronDown size={20} className={`text-text-muted group-hover:text-primary-start transition-transform duration-200 shrink-0 ${isOpen ? 'rotate-180 text-primary-start' : ''}`} />
          </button>

          <AnimatePresence>
            {isOpen && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
                className="mt-3 w-full bg-canvas border border-main rounded-2xl shadow-2xl overflow-hidden z-50 p-3"
              >
                <div className="relative mb-2">
                  <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-primary-start pointer-events-none" />
                  <input
                    type="text"
                    value={filterQuery}
                    onChange={(e) => setFilterQuery(e.target.value)}
                    placeholder="Kërko me emër ose fjalë kyçe..."
                    className="w-full pl-10 pr-9 py-3 bg-surface border border-main rounded-xl text-xs sm:text-sm font-bold text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 transition-all"
                    autoFocus
                  />
                  {filterQuery && (
                    <button
                      type="button"
                      onClick={() => setFilterQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-danger-start p-1"
                    >
                      <X size={14} />
                    </button>
                  )}
                </div>

                <div className="max-h-80 overflow-y-auto custom-scrollbar space-y-1 pr-1">
                  {filteredTitles.length === 0 ? (
                    <div className="p-6 text-center text-xs text-text-muted font-bold">
                      Nuk u gjet asnjë material në këtë kategori
                    </div>
                  ) : (
                    filteredTitles.map((lawTitle, idx) => {
                      const displayTitle = normalizeForDisplay(lawTitle);
                      return (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSelectLaw(lawTitle)}
                          className="w-full text-left p-3.5 rounded-xl flex items-center justify-between text-xs sm:text-sm font-bold text-text-primary hover:bg-hover hover:text-primary-start transition-all cursor-pointer group"
                        >
                          <div className="flex items-center gap-3 min-w-0 pr-3">
                            {activeTab === 'academic' ? (
                              <GraduationCap size={16} className="text-text-muted group-hover:text-primary-start shrink-0 transition-colors" />
                            ) : activeTab === 'caselaw' ? (
                              <Gavel size={16} className="text-text-muted group-hover:text-primary-start shrink-0 transition-colors" />
                            ) : (
                              <Scale size={16} className="text-text-muted group-hover:text-primary-start shrink-0 transition-colors" />
                            )}
                            <span className="truncate leading-relaxed">{displayTitle}</span>
                          </div>
                          <Check size={16} className="opacity-0 group-hover:opacity-100 text-primary-start shrink-0 transition-opacity" />
                        </button>
                      );
                    })
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

        </div>

      </div>

      {/* UNIFIED CANVAS PDF ENGINE WITH EXACT STARTING PAGE JUMP */}
      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: modalFilename,
            mime_type: 'application/pdf',
          }}
          directUrl={pdfUrl}
          isAuth={true}
          initialPage={initialPageNumber}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </motion.div>
  );
}