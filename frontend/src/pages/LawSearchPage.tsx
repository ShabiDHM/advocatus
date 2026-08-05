// FILE: src/pages/LawSearchPage.tsx
// PHOENIX PROTOCOL - LAW SEARCH V25.0 (EXACT ACADEMIC & STATUTE FILENAMES MATCHING)

import { useState, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, Scale, ArrowLeft, ChevronDown, Check, ShieldCheck, BookOpen, GraduationCap, Gavel } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiService, API_V1_URL } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import FileViewerModal from '../components/FileViewerModal';

// EXACT STATUTORY FILENAMES FROM YOUR DIRECTORY
const EXACT_STATUTORY_FILES = [
  "KUSHTETUTA_E_REPUBLIKËS_SË_KOSOVËS.pdf",
  "KODI_NR._06_L-074_KODI_PENAL_I_REPUBLIKËS_SË_KOSOVËS.pdf",
  "KODI_NR._08_L-032_I_PROCEDURËS_PENALE.pdf",
  "KODI_NR._06_L-006_I_DREJTËSISË_PËR_TË_MITUR.pdf",
  "LIGJI_NR._03_L-006_PËR_PROCEDURËN_KONTESTIMORE.pdf",
  "LIGJI_NR._04_L-077_PËR_MARRËDHËNIET_E_DETYRIMEVE.pdf",
  "LIGJI_NR._04_L-139_PËR_PROCEDURËN_PËRMBARIMORE.pdf",
  "LIGJI_NR._04_L-161_PËR_SIGURINË_DHE_SHËNDETIN_NË_PUNË.pdf",
  "LIGJI_Nr._05_L-029_PËR_TATIMIN_NË_TË_ARDHURAT_E_KORPORATAVE.pdf",
  "LIGJI_NR._06_L-016__PËR_SHOQËRITË_TREGTARE.pdf",
  "LIGJI_NR._06_L-082__PËR_MBROJTJEN_E_TË_DHËNAVE_PERSONALE.pdf",
  "LIGJI_NR._06_L-084______PËR_MBROJTJEN_E_FËMIJËS.pdf",
  "LIGJI_NR._08_L-257_PËR_ADMINISTRIMIN_E_PROCEDURAVE_TATIMORE.pdf",
  "LIGJI_NR._2004_32_LIGJI_PËR_FAMILJEN_I_KOSOVËS.pdf",
  "LIGJI__NR._03_L-212_I_PUNËS.pdf",
  "Udhëzues-Praktik-mbi-Qasjen-në-Drejtësi-ALB03.pdf"
];

// EXACT ACADEMIC FILENAMES FROM YOUR DIRECTORY
const EXACT_ACADEMIC_FILES = [
  "AKADEMIA_E_DREJT_2025_Case_Law_Kosovo_web.pdf",
  "AKADEMIA_E_DREJT_2025_departamenti-per-sherbime-ligjore-dhe-te-pergjithshme.pdf",
  "AKADEMIA_E_DREJT_2025_document_5518127434628652358.pdf",
  "AKADEMIA_E_DREJT_2025_doracak-dhe-udhezues.pdf",
  "AKADEMIA_E_DREJT_2025_Drejtesia_Mjedisore_Shq_.pdf",
  "AKADEMIA_E_DREJT_2025_InstitutiGjyqesor.pdf",
  "AKADEMIA_E_DREJT_2025_konkluzionet-per-unfikim-te-praktikes-gjyqesore.pdf",
  "AKADEMIA_E_DREJT_2025_Kosovo_Commentary_2024_ALB_web.pdf",
  "AKADEMIA_E_DREJT_2025_KS_Special_investigative_measures_web.pdf",
  "AKADEMIA_E_DREJT_2025_ligji.pdf",
  "AKADEMIA_E_DREJT_2025_RedirectToLocalizedContent.pdf",
  "AKADEMIA_E_DREJT_2025_rregulloret.pdf"
];

function formatDisplayTitle(filename: string): string {
  return filename
    .replace(/\.pdf$/i, '')
    .replace(/_/g, ' ')
    .replace(/-/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export default function LawSearchPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState<'statutes' | 'academic' | 'caselaw'>('statutes');
  const [filterQuery, setFilterQuery] = useState('');
  const [statuteTitles, setStatuteTitles] = useState<string[]>(EXACT_STATUTORY_FILES);
  const [academicTitles, setAcademicTitles] = useState<string[]>(EXACT_ACADEMIC_FILES);
  
  const [isOpen, setIsOpen] = useState(false);
  const [selectedPdfFilename, setSelectedPdfFilename] = useState<string | null>(null);
  const [showPdfModal, setShowPdfModal] = useState(false);

  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiService.getLawTitles()
      .then((res: any) => {
        if (res) {
          if (res.statutes && res.statutes.length > 0) {
            setStatuteTitles(Array.from(new Set([...res.statutes, ...EXACT_STATUTORY_FILES])));
          }
          if (res.academic_manuals && res.academic_manuals.length > 0) {
            setAcademicTitles(Array.from(new Set([...res.academic_manuals, ...EXACT_ACADEMIC_FILES])));
          }
        }
      })
      .catch((err) => {
        console.warn("[LawSearchPage] Using default Kosovo files fallback:", err);
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
    if (activeTab === 'caselaw') return academicTitles;
    return statuteTitles;
  }, [activeTab, statuteTitles, academicTitles]);

  const filteredTitles = useMemo(() => {
    if (!filterQuery.trim()) return activeList;
    const lower = filterQuery.toLowerCase();
    return activeList.filter(file => {
      const display = formatDisplayTitle(file).toLowerCase();
      return file.toLowerCase().includes(lower) || display.includes(lower);
    });
  }, [activeList, filterQuery]);

  const handleSelectLaw = (lawFileOrTitle: string) => {
    setIsOpen(false);

    // IF ACADEMIC OR COURT DECISION: DIRECT B2 CANVAS PDF ENGINE (FileViewerModal)
    if (
      activeTab === 'academic' ||
      activeTab === 'caselaw' ||
      lawFileOrTitle.toUpperCase().includes('AKADEMIA') ||
      lawFileOrTitle.toLowerCase().endsWith('.pdf')
    ) {
      setSelectedPdfFilename(lawFileOrTitle);
      setShowPdfModal(true);
    } else {
      // OFFICIAL STATUTES: NAVIGATE TO TABLE OF CONTENTS
      navigate(`/laws/overview?lawTitle=${encodeURIComponent(lawFileOrTitle)}`);
    }
  };

  const pdfUrl = selectedPdfFilename ? `${API_V1_URL}/laws/pdf/${encodeURIComponent(selectedPdfFilename)}` : null;

  return (
    <motion.div className="w-full min-h-screen pb-16 bg-canvas text-text-primary" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="max-w-4xl mx-auto px-4 sm:px-8 pt-28">
        
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
                Zgjidh Ligjin ose Udhëzuesin
              </h1>
            </div>
            
            <div className="px-4 py-2 bg-primary-start/10 border border-primary-start/20 rounded-xl text-primary-start font-mono text-xs font-bold">
              {activeList.length} {activeTab === 'statutes' ? 'Kodet Zyrtare' : 'Udhëzues & Materiale'}
            </div>
          </div>
        </div>

        {/* CATEGORY SWITCHER TABS */}
        <div className="flex items-center gap-2 mb-6 bg-surface p-1.5 rounded-2xl border border-main shadow-sm overflow-x-auto">
          <button
            type="button"
            onClick={() => { setActiveTab('statutes'); setIsOpen(false); }}
            className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
              activeTab === 'statutes' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Scale size={15} />
            <span>Kodet Zyrtare ({statuteTitles.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('academic'); setIsOpen(false); }}
            className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
              activeTab === 'academic' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <GraduationCap size={15} />
            <span>Akademia 2025 ({academicTitles.length})</span>
          </button>

          <button
            type="button"
            onClick={() => { setActiveTab('caselaw'); setIsOpen(false); }}
            className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
              activeTab === 'caselaw' ? 'bg-primary-start text-white shadow-md' : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Gavel size={15} />
            <span>Aktgjykimet</span>
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
                      Nuk u gjet asnjë material me këtë emër
                    </div>
                  ) : (
                    filteredTitles.map((lawFile, idx) => {
                      const displayTitle = formatDisplayTitle(lawFile);
                      return (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleSelectLaw(lawFile)}
                          className="w-full text-left p-3.5 rounded-xl flex items-center justify-between text-xs sm:text-sm font-bold text-text-primary hover:bg-hover hover:text-primary-start transition-all cursor-pointer group"
                        >
                          <div className="flex items-center gap-3 min-w-0 pr-3">
                            {activeTab === 'academic' ? (
                              <BookOpen size={16} className="text-text-muted group-hover:text-primary-start shrink-0 transition-colors" />
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

      {/* UNIFIED CANVAS PDF ENGINE (FileViewerModal) */}
      {showPdfModal && pdfUrl && (
        <FileViewerModal
          documentData={{
            file_name: selectedPdfFilename || 'Udhëzues Akademik.pdf',
            mime_type: 'application/pdf',
          }}
          directUrl={pdfUrl}
          isAuth={true}
          onClose={() => setShowPdfModal(false)}
          t={t}
        />
      )}
    </motion.div>
  );
}