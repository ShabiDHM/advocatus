// FILE: src/components/business/TeamTab.tsx
// PHOENIX PROTOCOL - TEAM TAB V1.3 (SAFE REMOVAL)
// 1. FIX: 'handleRemoveMember' now calls the specialized 'removeOrganizationMember' API.
// 2. SAFETY: Ensures Member's cases/docs are transferred to Owner before deletion.
// 3. UI: Fully functional dropdown menus for actions.

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    UserPlus, Mail, CheckCircle, X, Loader2, 
    AlertTriangle, Briefcase, Crown, MoreHorizontal, Trash2
} from 'lucide-react';
import { apiService } from '../../services/api';
import { User } from '../../data/types';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';

export const TeamTab: React.FC = () => {
    const { t } = useTranslation();
    const { user: currentUser } = useAuth(); 
    
    const [members, setMembers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    
    // Invite State
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviting, setInviting] = useState(false);
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [inviteResult, setInviteResult] = useState<string | null>(null);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    
    // Dropdown State
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    // Hardcoded for now until we fetch Org details from backend object
    const MAX_SEATS = 5; 

    useEffect(() => {
        fetchMembers();
    }, []);

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setOpenMenuId(null);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const fetchMembers = async () => {
        try {
            const data = await apiService.getOrganizationMembers();
            setMembers(data);
        } catch (error) {
            console.error("Failed to fetch team", error);
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
            setInviteResult(res.message);
            setInviteEmail(""); 
        } catch (err: any) {
            const detail = err.response?.data?.detail || "Failed to invite.";
            setErrorMsg(detail);
        } finally {
            setInviting(false);
        }
    };

    const handleRemoveMember = async (userId: string) => {
        if (!window.confirm(t('team.confirmRemove', 'Are you sure you want to remove this member? Their cases will be transferred to you.'))) return;
        
        // Optimistic UI update
        const originalMembers = [...members];
        setMembers(members.filter(m => m.id !== userId));
        setOpenMenuId(null);

        try {
            // PHOENIX FIX: Call specific organization removal endpoint (Safe Transfer)
            await apiService.removeOrganizationMember(userId);
        } catch (error) {
            console.error("Failed to remove member", error);
            // Revert on failure
            setMembers(originalMembers);
            alert("Failed to remove member.");
        }
    };

    if (loading) return <div className="flex justify-center h-64 items-center"><Loader2 className="animate-spin text-primary-start w-10 h-10" /></div>;

    const usedSeats = members.length;
    const availableSeats = MAX_SEATS - usedSeats;
    const progressPercent = (usedSeats / MAX_SEATS) * 100;

    // Permissions Check
    const isCurrentUserOwner = currentUser?.role === 'ADMIN' || (currentUser as any)?.organization_role === 'OWNER' || (currentUser as any)?.org_role === 'OWNER';

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-8 pb-20">
            
            {/* Header / Stats Panel */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2 glass-panel rounded-3xl p-8 relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-primary-start to-primary-end" />
                    <div className="flex justify-between items-start">
                        <div>
                            <h2 className="text-2xl font-bold text-white mb-2">{t('team.manageTeam', 'Manage Team')}</h2>
                            <p className="text-text-secondary text-sm max-w-lg">{t('team.description', 'Invite colleagues to collaborate on cases and documents.')}</p>
                        </div>
                        <button 
                            onClick={() => setShowInviteModal(true)}
                            disabled={availableSeats <= 0}
                            className="bg-primary-start/20 hover:bg-primary-start/30 text-primary-300 border border-primary-start/50 px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <UserPlus size={18} /> {t('team.inviteButton', 'Invite Member')}
                        </button>
                    </div>
                </div>

                {/* Seat Usage Card */}
                <div className="glass-panel rounded-3xl p-8 flex flex-col justify-center relative overflow-hidden">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-accent-start to-accent-end" />
                    <div className="flex justify-between items-center mb-4">
                        <span className="text-gray-400 font-bold text-xs uppercase tracking-wider">{t('team.planUsage', 'Plan Usage')}</span>
                        <span className={`px-2 py-1 rounded text-xs font-bold ${availableSeats <= 0 ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                            {availableSeats > 0 ? 'Active' : 'Limit Reached'}
                        </span>
                    </div>
                    <div className="flex items-end gap-2 mb-2">
                        <span className="text-4xl font-bold text-white">{usedSeats}</span>
                        <span className="text-lg text-gray-500 mb-1">/ {MAX_SEATS}</span>
                    </div>
                    <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-primary-start to-accent-start transition-all duration-1000" style={{ width: `${progressPercent}%` }} />
                    </div>
                    <p className="text-xs text-gray-500 mt-4 text-center">
                        {availableSeats <= 0 
                            ? t('team.upgradePrompt', 'Upgrade for more seats') 
                            : t('team.seatsRemaining', { count: availableSeats })}
                    </p>
                </div>
            </div>

            {/* Members List */}
            <div className="glass-panel rounded-3xl p-1 overflow-visible min-h-[300px]">
                <table className="w-full text-left">
                    <thead className="bg-white/5 text-gray-400 text-xs uppercase tracking-wider">
                        <tr>
                            <th className="px-6 py-4 font-bold">{t('team.user', 'User')}</th>
                            <th className="px-6 py-4 font-bold">{t('team.role', 'Role')}</th>
                            <th className="px-6 py-4 font-bold">{t('team.status', 'Status')}</th>
                            <th className="px-6 py-4 font-bold text-right">{t('team.actions', 'Actions')}</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-sm">
                        {members.map((member) => {
                            const safeMember = member as any;
                            const memberRole = safeMember.organization_role || safeMember.org_role || safeMember.role;
                            const isMemberOwner = memberRole === 'OWNER';
                            const isSelf = currentUser?.id === member.id;

                            return (
                                <tr key={member.id} className="hover:bg-white/5 transition-colors group relative">
                                    <td className="px-6 py-4">
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
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            {isMemberOwner ? <Crown size={14} className="text-yellow-500" /> : <Briefcase size={14} className="text-gray-500" />}
                                            <span className={isMemberOwner ? 'text-yellow-500 font-bold' : 'text-gray-300'}>{memberRole}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-bold ${member.subscription_status === 'INACTIVE' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'}`}>
                                            <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${member.subscription_status === 'INACTIVE' ? 'bg-yellow-400' : 'bg-emerald-400'}`} /> 
                                            {member.subscription_status === 'INACTIVE' ? 'Pending' : 'Active'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        {/* DROPDOWN MENU TRIGGER */}
                                        <div className="relative inline-block text-left" ref={openMenuId === member.id ? menuRef : null}>
                                            <button 
                                                onClick={() => setOpenMenuId(openMenuId === member.id ? null : member.id)}
                                                className={`p-2 rounded-lg transition-colors ${openMenuId === member.id ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-white hover:bg-white/5'}`}
                                            >
                                                <MoreHorizontal size={20} />
                                            </button>

                                            {/* DROPDOWN MENU */}
                                            <AnimatePresence>
                                                {openMenuId === member.id && (
                                                    <motion.div 
                                                        initial={{ opacity: 0, scale: 0.95, y: -10 }}
                                                        animate={{ opacity: 1, scale: 1, y: 0 }}
                                                        exit={{ opacity: 0, scale: 0.95, y: -10 }}
                                                        transition={{ duration: 0.1 }}
                                                        className="absolute right-0 mt-2 w-48 bg-[#1a1f2e] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden"
                                                    >
                                                        <div className="py-1">
                                                            {isCurrentUserOwner && !isSelf ? (
                                                                <button 
                                                                    onClick={() => handleRemoveMember(member.id)}
                                                                    className="w-full text-left px-4 py-3 text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2 transition-colors"
                                                                >
                                                                    <Trash2 size={16} />
                                                                    {t('team.removeMember', 'Remove Member')}
                                                                </button>
                                                            ) : (
                                                                <div className="px-4 py-3 text-sm text-gray-500 italic text-center">
                                                                    {isSelf ? "Current User" : "No Actions"}
                                                                </div>
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

            {/* Invite Modal */}
            <AnimatePresence>
                {showInviteModal && (
                    <div className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <motion.div 
                            initial={{ scale: 0.9, opacity: 0 }} 
                            animate={{ scale: 1, opacity: 1 }} 
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="glass-high w-full max-w-md p-8 rounded-3xl shadow-2xl relative"
                        >
                            <button onClick={() => setShowInviteModal(false)} className="absolute top-6 right-6 text-gray-500 hover:text-white"><X size={24} /></button>
                            
                            <div className="mb-6">
                                <div className="w-12 h-12 rounded-2xl bg-primary-start/20 flex items-center justify-center mb-4 text-primary-start">
                                    <UserPlus size={24} />
                                </div>
                                <h3 className="text-2xl font-bold text-white">{t('team.inviteTitle', 'Invite Member')}</h3>
                                <p className="text-gray-400 text-sm mt-1">{t('team.inviteSubtitle', 'Send an invitation link to a colleague.')}</p>
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
                                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">{t('general.email')}</label>
                                        <div className="relative">
                                            <Mail className="absolute left-4 top-3.5 w-5 h-5 text-gray-500" />
                                            <input 
                                                autoFocus
                                                type="email" 
                                                required
                                                value={inviteEmail}
                                                onChange={(e) => setInviteEmail(e.target.value)}
                                                className="glass-input w-full pl-12 pr-4 py-3.5 rounded-xl text-white" 
                                                placeholder="colleague@firm.com"
                                            />
                                        </div>
                                    </div>

                                    <div className="flex gap-3 pt-2">
                                        <button type="button" onClick={() => setShowInviteModal(false)} className="flex-1 py-3.5 rounded-xl text-gray-400 hover:bg-white/5 font-bold transition-colors">
                                            {t('general.cancel')}
                                        </button>
                                        <button 
                                            type="submit" 
                                            disabled={inviting}
                                            className="flex-1 py-3.5 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold shadow-lg shadow-primary-start/20 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 disabled:cursor-wait flex items-center justify-center gap-2"
                                        >
                                            {inviting ? <Loader2 className="animate-spin w-5 h-5" /> : <UserPlus size={18} />}
                                            {t('team.sendInvite', 'Send Invite')}
                                        </button>
                                    </div>
                                </form>
                            ) : (
                                <div className="space-y-6">
                                    <div className="p-4 rounded-xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-200 flex items-center gap-3">
                                        <CheckCircle className="flex-shrink-0" size={20} />
                                        <span className="font-medium">{inviteResult}</span>
                                    </div>
                                    <button 
                                        onClick={() => { setShowInviteModal(false); setInviteResult(null); fetchMembers(); }} 
                                        className="w-full py-3.5 bg-white/10 hover:bg-white/20 text-white rounded-xl font-bold transition-colors"
                                    >
                                        {t('general.close')}
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