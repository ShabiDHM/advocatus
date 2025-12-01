// FILE: src/components/FindingsModal.tsx
// PHOENIX PROTOCOL - DATE PARSING HARDENING
// 1. REGEX: Enhanced to handle "Data: 15 Dhjetor", separators like "-", and extra whitespace.
// 2. LOGIC: Added 'Smart Year' deduction if year is missing.
// 3. UX: "Shto në Kalendar" button now appears more reliably.

import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { Finding, CalendarEventCreateRequest } from '../data/types';
import { apiService } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Lightbulb, FileText, Search, CalendarPlus, Check, Loader2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface FindingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  findings: Finding[];
}

const scrollbarStyles = `
  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }
`;

// PHOENIX: Enhanced Date Parser
const extractDateFromText = (text: string): string | undefined => {
    if (!text) return undefined;
    const cleanText = text.toLowerCase().replace(/\s+/g, ' ').trim();

    // 1. Numeric Format: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
    const numericMatch = cleanText.match(/(\d{1,2})[./-](\d{1,2})[./-](\d{4})/);
    if (numericMatch) {
        return `${numericMatch[3]}-${numericMatch[2].padStart(2, '0')}-${numericMatch[1].padStart(2, '0')}`;
    }

    // 2. Albanian Month Map
    const albanianMonths: { [key: string]: string } = {
        'janar': '01', 'shkurt': '02', 'mars': '03', 'prill': '04', 'maj': '05', 'qershor': '06',
        'korrik': '07', 'gusht': '08', 'shtator': '09', 'tetor': '10', 'nëntor': '11', 'nentor': '11', 'dhjetor': '12'
    };

    // 3. Text Format with Year: "15 Dhjetor 2025", "15-Dhjetor-2025"
    // Allows optional separators (space, dot, dash)
    for (const [monthName, monthNum] of Object.entries(albanianMonths)) {
        // Regex explains:
        // (\d{1,2})  -> Day (1 or 2 digits)
        // [\s.-]+    -> Separator (space, dot, dash)
        // ${monthName} -> Month Name
        // [\s.-]+    -> Separator
        // (\d{4})    -> Year (4 digits)
        const regexWithYear = new RegExp(`(\\d{1,2})[\\s.-]+${monthName}[\\s.-]+(\\d{4})`);
        const match = cleanText.match(regexWithYear);
        if (match) {
            return `${match[2]}-${monthNum}-${match[1].padStart(2, '0')}`;
        }
    }

    // 4. Text Format WITHOUT Year: "15 Dhjetor" -> Assume Current or Next Year
    // Useful for "jo më vonë se 25 Dhjetor"
    for (const [monthName, monthNum] of Object.entries(albanianMonths)) {
        const regexNoYear = new RegExp(`(\\d{1,2})[\\s.-]+${monthName}(?!\\w)`); // Negative lookahead to ensure we don't cut off words
        const match = cleanText.match(regexNoYear);
        if (match) {
            const day = match[1].padStart(2, '0');
            const currentYear = new Date().getFullYear();
            const currentMonth = new Date().getMonth() + 1;
            
            // Logic: If the month has passed this year, assume next year.
            // Example: If today is Dec 2025, and text is "Janar", assume "Janar 2026".
            let year = currentYear;
            if (parseInt(monthNum) < currentMonth) {
                year = currentYear + 1;
            }
            return `${year}-${monthNum}-${day}`;
        }
    }

    return undefined; 
};

const FindingCard: React.FC<{ finding: Finding; t: any }> = ({ finding, t }) => {
    const [showEventForm, setShowEventForm] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isSaved, setIsSaved] = useState(false);
    
    // Auto-detect date
    const detectedDate = extractDateFromText(finding.finding_text);
    
    // Form State
    const [eventDate, setEventDate] = useState(detectedDate || new Date().toISOString().split('T')[0]);
    const [eventTitle, setEventTitle] = useState(finding.finding_text.substring(0, 60) + (finding.finding_text.length > 60 ? '...' : ''));
    const [eventType, setEventType] = useState('DEADLINE');

    const handleCreateEvent = async () => {
        if (!eventDate || !eventTitle) return;
        setIsSaving(true);
        try {
            const payload: CalendarEventCreateRequest = {
                title: eventTitle,
                description: `Burimi: ${finding.finding_text}\nDokumenti: ${finding.document_name || 'N/A'}`,
                start_date: new Date(eventDate).toISOString(),
                end_date: new Date(eventDate).toISOString(),
                is_all_day: true,
                event_type: eventType,
                case_id: finding.case_id,
                priority: 'HIGH'
            };
            
            await apiService.createCalendarEvent(payload);
            setIsSaved(true);
            
            setTimeout(() => {
                setShowEventForm(false);
            }, 2000);

        } catch (error) {
            console.error("Failed to create event:", error);
            alert(t('error.generic') || "Failed to create event");
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="group relative p-4 sm:p-5 bg-background-dark rounded-xl border border-glass-edge/30 hover:border-primary-start/50 transition-all duration-300 shadow-sm overflow-hidden"
        >
            <div className="absolute left-0 top-4 bottom-4 w-1 bg-gradient-to-b from-yellow-400 to-orange-500 rounded-r-full opacity-70 group-hover:opacity-100 transition-opacity" />
            
            <div className="pl-3">
                <p className="text-sm sm:text-base text-gray-200 leading-relaxed font-medium">
                    {finding.finding_text}
                </p>
                
                <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-2 px-2 py-1 rounded-md bg-black/20 border border-white/5 text-xs text-gray-400 w-full sm:w-auto">
                        <FileText className="h-3 w-3 text-yellow-500 flex-shrink-0" />
                        <span className="font-medium text-gray-300 whitespace-nowrap">{t('caseView.findingSource')}:</span>
                        <span className="truncate max-w-full">{finding.document_name || finding.document_id}</span>
                    </div>
                    
                    <div className="flex items-center gap-2">
                        {finding.confidence_score !== undefined && finding.confidence_score > 0 && (
                            <div className="flex items-center gap-1.5" title={t('caseView.confidenceScore')}>
                                <Search className="h-3 w-3 text-accent-start" />
                                <span className="text-xs font-mono text-accent-start">{Math.round(finding.confidence_score * 100)}%</span>
                            </div>
                        )}
                        
                        {/* Add to Calendar Button - Show if detection works OR manual override allowed */}
                        {!isSaved && !showEventForm && (
                            <button 
                                onClick={() => setShowEventForm(true)}
                                className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium border transition-colors ${
                                    detectedDate 
                                    ? 'bg-indigo-500/20 hover:bg-indigo-500/40 text-indigo-300 border-indigo-500/30'
                                    : 'bg-gray-700/30 hover:bg-gray-700/50 text-gray-400 border-gray-600/30'
                                }`}
                                title={detectedDate ? `Data e gjetur: ${detectedDate}` : 'Data nuk u gjet automatikisht'}
                            >
                                <CalendarPlus className="h-3.5 w-3.5" />
                                <span>{t('calendar.addToCalendar', 'Shto në Kalendar')}</span>
                            </button>
                        )}
                    </div>
                </div>

                {/* Inline Event Creation Form */}
                <AnimatePresence>
                    {showEventForm && (
                        <motion.div 
                            initial={{ height: 0, opacity: 0, marginTop: 0 }}
                            animate={{ height: 'auto', opacity: 1, marginTop: 16 }}
                            exit={{ height: 0, opacity: 0, marginTop: 0 }}
                            className="overflow-hidden border-t border-white/10 pt-4"
                        >
                            {isSaved ? (
                                <div className="flex items-center justify-center p-3 text-green-400 gap-2 bg-green-900/20 rounded-lg border border-green-500/30">
                                    <Check className="h-5 w-5" />
                                    <span className="text-sm font-medium">{t('calendar.eventSaved', 'Ngjarja u ruajt me sukses!')}</span>
                                </div>
                            ) : (
                                <div className="space-y-3 bg-black/20 p-3 rounded-lg border border-white/5">
                                    <div className="flex items-center justify-between">
                                        <h4 className="text-xs font-bold text-gray-400 uppercase flex items-center gap-2">
                                            <CalendarPlus className="h-3 w-3" />
                                            {t('calendar.newEvent', 'Ngjarje e Re')}
                                        </h4>
                                        {detectedDate && (
                                            <span className="text-[10px] text-indigo-400 px-1.5 py-0.5 bg-indigo-500/10 rounded border border-indigo-500/20">
                                                AI Detected
                                            </span>
                                        )}
                                    </div>
                                    
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        <div className="space-y-1">
                                            <label className="text-xs text-gray-500">{t('calendar.date', 'Data')}</label>
                                            <input 
                                                type="date" 
                                                value={eventDate}
                                                onChange={(e) => setEventDate(e.target.value)}
                                                className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:border-indigo-500 outline-none transition-colors"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-xs text-gray-500">{t('calendar.type', 'Lloji')}</label>
                                            <select 
                                                value={eventType}
                                                onChange={(e) => setEventType(e.target.value)}
                                                className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:border-indigo-500 outline-none transition-colors"
                                            >
                                                <option value="DEADLINE">{t('calendar.deadline', 'Afat Ligjor')}</option>
                                                <option value="HEARING">{t('calendar.hearing', 'Seancë')}</option>
                                                <option value="MEETING">{t('calendar.meeting', 'Takim')}</option>
                                                <option value="FILING">{t('calendar.filing', 'Depozitim')}</option>
                                            </select>
                                        </div>
                                    </div>
                                    
                                    <div className="space-y-1">
                                        <label className="text-xs text-gray-500">{t('calendar.title', 'Titulli')}</label>
                                        <input 
                                            type="text" 
                                            value={eventTitle}
                                            onChange={(e) => setEventTitle(e.target.value)}
                                            className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm text-white focus:border-indigo-500 outline-none transition-colors"
                                        />
                                    </div>

                                    <div className="flex justify-end gap-2 pt-2">
                                        <button 
                                            onClick={() => setShowEventForm(false)}
                                            className="px-3 py-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                                        >
                                            {t('general.cancel', 'Anulo')}
                                        </button>
                                        <button 
                                            onClick={handleCreateEvent}
                                            disabled={isSaving}
                                            className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded flex items-center gap-2 disabled:opacity-50 transition-colors shadow-lg shadow-indigo-500/20"
                                        >
                                            {isSaving ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                                            {t('general.save', 'Ruaj')}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
};

const FindingsModal: React.FC<FindingsModalProps> = ({ isOpen, onClose, findings }) => {
  const { t } = useTranslation();

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = 'unset';
    }
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const modalContent = (
    <AnimatePresence>
        <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[9999] p-0 sm:p-4"
            onClick={onClose}
        >
            <motion.div 
                initial={{ scale: 0.9, opacity: 0, y: 20 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.9, opacity: 0, y: 20 }}
                className="bg-background-dark w-full h-full sm:h-auto sm:max-h-[90vh] sm:max-w-3xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-glass-edge sm:border-opacity-50"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="p-4 sm:p-6 border-b border-glass-edge flex justify-between items-center bg-background-light/90 backdrop-blur-md flex-shrink-0 gap-4">
                    <h2 className="text-lg sm:text-2xl font-bold text-text-primary flex items-center gap-2 min-w-0">
                        <div className="p-1.5 bg-yellow-400/10 rounded-lg flex-shrink-0">
                             <Lightbulb className="text-yellow-400 h-5 w-5 sm:h-6 sm:w-6" />
                        </div>
                        <span className="truncate">{t('caseView.findingsTitle')}</span>
                        <span className="text-xs font-medium px-2 py-1 rounded-full bg-background-dark border border-glass-edge text-text-secondary flex-shrink-0">
                            {findings.length}
                        </span>
                    </h2>
                    
                    <button 
                        onClick={onClose} 
                        className="p-2 text-text-secondary hover:text-white hover:bg-white/10 rounded-full transition-colors flex-shrink-0"
                        title={t('general.close', 'Mbyll')}
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-4 sm:p-6 overflow-y-auto flex-1 custom-scrollbar relative bg-background-dark/50">
                    <style>{scrollbarStyles}</style>

                    {findings.length === 0 ? (
                        <div className="text-center text-text-secondary py-10">
                            <p>{t('caseView.noFindings', 'Asnjë gjetje nuk është identifikuar ende.')}</p>
                        </div>
                    ) : (
                        <div className="space-y-4 pb-4">
                            {findings.map((finding, index) => (
                                <FindingCard key={finding.id || index} finding={finding} t={t} />
                            ))}
                        </div>
                    )}
                </div>
                
                {/* Footer */}
                <div className="p-4 border-t border-glass-edge bg-background-dark/80 text-center flex-shrink-0 safe-area-pb">
                    <button onClick={onClose} className="w-full sm:w-auto px-6 py-3 sm:py-2 bg-background-light hover:bg-white/10 border border-glass-edge text-white rounded-xl font-medium transition-all shadow-lg active:scale-95">
                        {t('general.close', 'Mbyll')}
                    </button>
                </div>
            </motion.div>
        </motion.div>
    </AnimatePresence>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};

export default FindingsModal;