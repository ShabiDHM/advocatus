// FILE: src/pages/ClientPortalPage.tsx
// PHOENIX PROTOCOL - CLIENT PORTAL V1.1 (LINT FREE)
// 1. CLEANUP: Removed unused imports (CheckCircle, MessageSquare).
// 2. LOGIC: Remains identical to V1.0.

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
    Calendar, Clock, AlertCircle, Loader2, 
    FileText, Gavel, Users, Scale, ShieldCheck 
} from 'lucide-react';
import axios from 'axios';
import { API_V1_URL } from '../services/api';

// Simple types for the public view
interface PublicEvent {
    title: string;
    date: string;
    type: string;
    description: string;
}

interface PublicCaseData {
    case_number: string;
    title: string;
    client_name: string;
    status: string;
    timeline: PublicEvent[];
}

const getEventIcon = (type: string) => {
    switch (type) {
        case 'DEADLINE': return <AlertCircle className="text-rose-400" />;
        case 'HEARING': return <Gavel className="text-purple-400" />;
        case 'MEETING': return <Users className="text-blue-400" />;
        case 'FILING': return <FileText className="text-amber-400" />;
        case 'COURT_DATE': return <Scale className="text-orange-400" />;
        default: return <Calendar className="text-gray-400" />;
    }
};

const ClientPortalPage: React.FC = () => {
    const { caseId } = useParams<{ caseId: string }>();
    const [data, setData] = useState<PublicCaseData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        const fetchPublicData = async () => {
            try {
                // Direct Axios call to bypass Interceptors
                const response = await axios.get(`${API_V1_URL}/cases/public/${caseId}/timeline`);
                setData(response.data);
            } catch (err) {
                console.error(err);
                setError("Kjo dosje nuk u gjet ose nuk keni qasje.");
            } finally {
                setLoading(false);
            }
        };

        if (caseId) fetchPublicData();
    }, [caseId]);

    if (loading) return (
        <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center text-white">
            <Loader2 className="w-10 h-10 animate-spin text-indigo-500 mb-4" />
            <p className="text-gray-400 animate-pulse">Duke u lidhur me sistemin ligjor...</p>
        </div>
    );

    if (error || !data) return (
        <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center p-4">
            <div className="bg-red-500/10 border border-red-500/20 p-8 rounded-2xl text-center max-w-md">
                <ShieldCheck className="w-12 h-12 text-red-400 mx-auto mb-4" />
                <h1 className="text-xl font-bold text-white mb-2">Qasja u Refuzua</h1>
                <p className="text-gray-400">{error}</p>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-950 font-sans text-gray-100 selection:bg-indigo-500/30">
            {/* Header / Branding */}
            <header className="bg-gray-900/50 backdrop-blur-md border-b border-white/5 sticky top-0 z-10">
                <div className="max-w-3xl mx-auto px-6 py-4 flex justify-between items-center">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                            <Scale className="text-white w-6 h-6" />
                        </div>
                        <div>
                            <h1 className="font-bold text-lg leading-tight tracking-tight">Juristi Portal</h1>
                            <p className="text-xs text-gray-500 font-medium">Qasje e Sigurt për Klientin</p>
                        </div>
                    </div>
                    <div className="px-3 py-1 bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-bold rounded-full uppercase tracking-wider flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                        {data.status}
                    </div>
                </div>
            </header>

            <main className="max-w-3xl mx-auto px-6 py-12">
                {/* Case Info Card */}
                <motion.div 
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-gray-900 border border-white/10 rounded-3xl p-8 mb-12 shadow-2xl relative overflow-hidden"
                >
                    <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />
                    
                    <span className="text-indigo-400 text-xs font-bold uppercase tracking-wider mb-2 block">{data.case_number}</span>
                    <h2 className="text-3xl font-bold text-white mb-2">{data.title}</h2>
                    <p className="text-gray-400">Klienti: <span className="text-white font-medium">{data.client_name}</span></p>
                </motion.div>

                {/* Timeline */}
                <h3 className="text-xl font-bold text-white mb-8 flex items-center gap-3">
                    <Clock className="text-gray-500" />
                    Kronologjia e Çështjes
                </h3>

                <div className="relative border-l-2 border-white/10 ml-3.5 space-y-12 pb-12">
                    {data.timeline.length === 0 ? (
                        <div className="ml-8 p-6 bg-white/5 rounded-2xl border border-dashed border-white/10 text-gray-500 italic">
                            Nuk ka ngjarje publike për të shfaqur momentalisht.
                        </div>
                    ) : (
                        data.timeline.map((event, index) => (
                            <motion.div 
                                key={index}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: index * 0.1 }}
                                className="relative ml-8"
                            >
                                {/* Dot on the line */}
                                <div className="absolute -left-[41px] top-0 bg-gray-950 p-1">
                                    <div className="w-4 h-4 rounded-full bg-indigo-500 border-4 border-gray-950 shadow-[0_0_10px_rgba(99,102,241,0.5)]" />
                                </div>

                                <div className="bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-colors group">
                                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-3">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 bg-gray-800 rounded-lg border border-white/5 text-gray-300 group-hover:text-indigo-400 transition-colors">
                                                {getEventIcon(event.type)}
                                            </div>
                                            <div>
                                                <h4 className="text-lg font-bold text-white">{event.title}</h4>
                                                <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">{event.type}</span>
                                            </div>
                                        </div>
                                        <div className="text-sm font-mono text-gray-400 bg-black/20 px-3 py-1 rounded-lg border border-white/5 whitespace-nowrap">
                                            {new Date(event.date).toLocaleDateString('sq-AL', { year: 'numeric', month: 'long', day: 'numeric' })}
                                        </div>
                                    </div>
                                    {event.description && (
                                        <p className="text-gray-400 text-sm leading-relaxed border-t border-white/5 pt-3 mt-2">
                                            {event.description}
                                        </p>
                                    )}
                                </div>
                            </motion.div>
                        ))
                    )}
                </div>
                
                <div className="text-center text-gray-600 text-xs mt-12 pt-8 border-t border-white/5">
                    &copy; {new Date().getFullYear()} Juristi AI. Të gjitha të drejtat e rezervuara.
                </div>
            </main>
        </div>
    );
};

export default ClientPortalPage;