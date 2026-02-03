// FILE: src/components/business/TeamTab.tsx
// PHOENIX PROTOCOL - TEAM TAB V2.3 (i18n & SYNC FIX)
// 1. FIXED: Removed all hardcoded English strings to support multi-language.
// 2. FIXED: Logic now utilizes backend 'current_active_users' for accurate progress.
// 3. STATUS: Production Ready & Fully Internationalized.

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    UserPlus, Mail, CheckCircle, X, Loader2, 
    AlertTriangle, Briefcase, Crown, MoreHorizontal, Trash2
} from 'lucide-react';
import { apiService } from '../../services/api';
import { User, Organization } from '../../data/types';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';

export const TeamTab: React.FC = () => {
    const { t } = useTranslation();
    const { user: currentUser } = useAuth(); 
    
    const [members, setMembers] = useState<User[]>([]);
    const [organization, setOrganization] = useState<Organization | null>(null);
    const [loading, setLoading] = useState(true);
    
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviting, setInviting] = useState(false);
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [inviteResult, setInviteResult] = useState<string | null>(null);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchData();
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setOpenMenuId(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const fetchData = async () => {
        try {
            const [membersData, orgData] = await Promise.all([
                apiService.getOrganizationMembers(),
                apiService.getOrganization()
            ]);
            setMembers(membersData);
            setOrganization(orgData);
        } catch (error) {
            console.error("Failed to fetch team data", error);
        } finally {
            setLoading(false);
        }
    };

    const handleInvite = async (e: React.FormEvent) => {
        e.preventDefault();
        setInviting(true);
        setErrorMsg(null);
        setInviteResult(null);
        try {
            const res = await apiService.inviteMember(inviteEmail);
            setInviteResult(res.message || t('team.invite_success_detail'));
            setInviteEmail(""); 
            fetchData();
        } catch (err: any) {
            const detail = err.response?.data?.detail || t('team.invite_error_generic');
            setErrorMsg(detail);
        } finally {
            setInviting(false);
        }
    };

    const handleRemoveMember = async (userId: string) => {
        if (!window.confirm(t('team.confirm_remove_member'))) return;
        try {
            await apiService.removeOrganizationMember(userId);
            fetchData();
        } catch (error) {
            console.error("Failed to remove member", error);
        }
    };

    if (loading) return <div className="flex justify-center h-64 items-center"><Loader2 className="animate-spin text-primary-start w-10 h-10" /></div>;

    const seatLimit = organization?.user_limit || 1; 
    const usedSeats = organization?.current_active_users || members.length;
    const availableSeats = seatLimit - usedSeats;
    const progressPercent = Math.min((usedSeats / seatLimit) * 100, 100);
    const isCurrentUserOwner = currentUser?.role === 'ADMIN' || currentUser?.organization_role === 'OWNER';
    const planName = organization?.plan_tier || 'DEFAULT';

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-8 pb-20">
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2 glass-panel rounded-3xl p-6 sm:p-8 relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-primary-start to-primary-end" />
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
                        <div>
                            <h2 className="text-2xl font-bold text-white mb-2">{t('team.manage_team_title')}</h2>
                            <p className="text-text-secondary text-sm max-w-lg">{t('team.manage_team_subtitle')}</p>
                        </div>
                        {isCurrentUserOwner && (
                            <button 
                                onClick={() => setShowInviteModal(true)}
                                disabled={availableSeats <= 0}
                                className="bg-primary-start/20 hover:bg-primary-start/30 text-primary-300 border border-primary-start/50 px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shrink-0 w-full sm:w-auto justify-center"
                            >
                                <UserPlus size={18} /> {t('team.invite_member_button')}
                            </button>
                        )}
                    </div>
                </div>

                <div className="glass-panel rounded-3xl p-8 flex flex-col justify-center relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-accent-start to-accent-end" />
                    <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-2">
                            <span className="text-gray-400 font-bold text-xs uppercase tracking-wider">{t('team.plan_usage_label')}</span>
                            <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-bold">
                                {planName}
                            </span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-bold ${availableSeats <= 0 ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                            {availableSeats > 0 ? t('team.status_active') : t('team.status_limit_reached')}
                        </span>
                    </div>
                    <div className="flex items-end gap-2 mb-2">
                        <span className="text-4xl font-bold text-white">{usedSeats}</span>
                        <span className="text-lg text-gray-500 mb-1">/ {seatLimit}</span>
                    </div>
                    <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-primary-start to-accent-start transition-all duration-1000" style={{ width: `${progressPercent}%` }} />
                    </div>
                </div>
            </div>

            <div className="glass-panel rounded-3xl overflow-hidden min-h-[300px]">
                <div className="overflow-x-auto">
                    <table className="w-full text-left min-w-[600px]">
                        <thead className="bg-white/5 text-gray-400 text-xs uppercase tracking-wider">
                            <tr>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_user')}</th>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_role')}</th>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_status')}</th>
                                <th className="px-6 py-4 font-bold text-right whitespace-nowrap">{t('team.table_actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-sm">
                            {members.map((member) => {
                                const memberRole = member.organization_role || member.role;
                                const isMemberOwner = memberRole === 'OWNER';
                                const isSelf = currentUser?.id === member.id;

                                return (
                                    <tr key={member.id} className="hover:bg-white/5 transition-colors group relative">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center text-white font-bold border border-white/10">
                                                    {member.username.substring(0, 2).toUpperCase()}
                                                </div>
                                                <div>
                                                    <div className="font-bold text-white">{member.username}</div>
                                                    <div className="text-xs text-gray-500">{member.email}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2">
                                                {isMemberOwner ? <Crown size={14} className="text-yellow-500" /> : <Briefcase size={14} className="text-gray-500" />}
                                                <span className={isMemberOwner ? 'text-yellow-500 font-bold' : 'text-gray-300'}>{memberRole}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-bold ${member.status === 'pending_invite' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'}`}>
                                                <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${member.status === 'pending_invite' ? 'bg-yellow-400' : 'bg-emerald-400'}`} /> 
                                                {member.status === 'pending_invite' ? t('team.status_pending') : t('team.status_active')}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right whitespace-nowrap">
                                            <div className="relative inline-block text-left">
                                                <button onClick={() => setOpenMenuId(openMenuId === member.id ? null : member.id)} className="p-2 text-gray-500 hover:text-white transition-colors">
                                                    <MoreHorizontal size={20} />
                                                </button>
                                                <AnimatePresence>
                                                    {openMenuId === member.id && (
                                                        <motion.div initial={{ opacity: 0, scale: 0.95, y: -10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: -10 }} className="absolute right-0 mt-2 w-48 bg-[#1a1f2e] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden" ref={menuRef}>
                                                            <div className="py-1">
                                                                {isCurrentUserOwner && !isSelf ? (
                                                                    <button onClick={() => handleRemoveMember(member.id)} className="w-full text-left px-4 py-3 text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2 transition-colors">
                                                                        <Trash2 size={16} /> {t('team.action_remove')}
                                                                    </button>
                                                                ) : (
                                                                    <div className="px-4 py-3 text-sm text-gray-500 italic text-center">{isSelf ? t('team.label_current_user') : t('team.label_no_actions')}</div>
                                                                )}
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </AnimatePresence>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Invite Modal */}
            <AnimatePresence>
                {showInviteModal && (
                    <div className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="glass-high w-full max-w-md p-8 rounded-3xl shadow-2xl relative">
                            <button onClick={() => { setShowInviteModal(false); setInviteResult(null); }} className="absolute top-6 right-6 text-gray-500 hover:text-white"><X size={24} /></button>
                            
                            <div className="mb-6">
                                <div className="w-12 h-12 rounded-2xl bg-primary-start/20 flex items-center justify-center mb-4 text-primary-start">
                                    <UserPlus size={24} />
                                </div>
                                <h3 className="text-2xl font-bold text-white">{t('team.invite_modal_title')}</h3>
                                <p className="text-gray-400 text-sm mt-1">{t('team.invite_modal_subtitle')}</p>
                            </div>

                            {!inviteResult ? (
                                <form onSubmit={handleInvite} className="space-y-6">
                                    {errorMsg && (
                                        <div className="p-4 rounded-xl bg-red-500/20 border border-red-500/30 text-red-200 flex items-start gap-3">
                                            <AlertTriangle className="flex-shrink-0 mt-0.5" size={18} />
                                            <span className="text-sm">{errorMsg}</span>
                                        </div>
                                    )}
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">{t('general.email_label')}</label>
                                        <div className="relative">
                                            <Mail className="absolute left-4 top-3.5 w-5 h-5 text-gray-500" />
                                            <input autoFocus type="email" required value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="glass-input w-full pl-12 pr-4 py-3.5 rounded-xl text-white" placeholder={t('general.email_placeholder')} />
                                        </div>
                                    </div>
                                    <button type="submit" disabled={inviting} className="w-full py-3.5 bg-primary-start text-white rounded-xl font-bold shadow-lg shadow-primary-start/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2">
                                        {inviting ? <Loader2 className="animate-spin w-5 h-5" /> : <UserPlus size={18} />}
                                        {t('team.button_send_invite')}
                                    </button>
                                </form>
                            ) : (
                                <div className="space-y-6 text-center">
                                    <div className="p-4 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-200 flex items-center justify-center gap-3">
                                        <CheckCircle className="flex-shrink-0" size={20} />
                                        <span className="font-medium">{inviteResult}</span>
                                    </div>
                                    <button onClick={() => { setShowInviteModal(false); setInviteResult(null); }} className="w-full py-3.5 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold transition-colors">
                                        {t('general.button_close')}
                                    </button>
                                </div>
                            )}
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};