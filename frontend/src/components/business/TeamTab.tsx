// FILE: src/components/business/TeamTab.tsx
// PHOENIX PROTOCOL - ALWAYS SHOW THREE DOTS, CONTEXT-AWARE MENU (FIXED DUPLICATE IDENTIFIER)

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    UserPlus, Mail, CheckCircle, X, Loader2, 
    AlertTriangle, Briefcase, Crown, MoreHorizontal, Trash2,
    Send
} from 'lucide-react';
import { User as UserIcon } from 'lucide-react'; // Renamed to avoid conflict with type User
import { apiService } from '../../services/api';
import { User, Organization } from '../../data/types'; // Type import
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';
import { createPortal } from 'react-dom';

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
    const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
    const activeButtonRef = useRef<HTMLButtonElement | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (openMenuId) {
                const portalMenu = document.getElementById('team-dropdown-portal');
                const isClickInsideButton = activeButtonRef.current?.contains(event.target as Node);
                const isClickInsidePortal = portalMenu?.contains(event.target as Node);
                if (!isClickInsideButton && !isClickInsidePortal) {
                    setOpenMenuId(null);
                    activeButtonRef.current = null;
                }
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [openMenuId]);

    // Position the dropdown when openMenuId changes
    useEffect(() => {
        if (!openMenuId || !activeButtonRef.current) return;

        const updatePosition = () => {
            if (!activeButtonRef.current) return;
            const rect = activeButtonRef.current.getBoundingClientRect();
            const menuWidth = 192; // w-48 = 192px
            const viewportWidth = window.innerWidth;
            let left = rect.right - menuWidth;
            if (left < 0) left = rect.left;
            if (left + menuWidth > viewportWidth) left = viewportWidth - menuWidth - 8;
            setMenuPosition({
                top: rect.bottom + window.scrollY + 4,
                left: left + window.scrollX,
            });
        };

        updatePosition();
        window.addEventListener('resize', updatePosition);
        window.addEventListener('scroll', updatePosition);
        return () => {
            window.removeEventListener('resize', updatePosition);
            window.removeEventListener('scroll', updatePosition);
        };
    }, [openMenuId]);

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
            setOpenMenuId(null);
        } catch (error) {
            console.error("Failed to remove member", error);
        }
    };

    const handleResendInvite = async (member: User) => {
        console.log(`Resend invite to ${member.email} (API to be implemented)`);
        // TODO: implement API call to resend invitation
        alert(`Ridërgo ftesë për ${member.email} (coming soon)`);
        setOpenMenuId(null);
    };

    const handleCancelInvite = async (member: User) => {
        if (!window.confirm(`Anulo ftesën për ${member.email}?`)) return;
        console.log(`Cancel invite for ${member.email} (API to be implemented)`);
        // TODO: implement API call to cancel pending invitation
        alert(`Ftesa u anulua për ${member.email} (coming soon)`);
        // Optionally remove from list or refetch
        fetchData();
        setOpenMenuId(null);
    };

    const handleMyProfile = () => {
        console.log("Navigate to profile (to be implemented)");
        alert("Profili Im - redirect to profile page (coming soon)");
        setOpenMenuId(null);
    };

    const handleOpenMenu = (e: React.MouseEvent<HTMLButtonElement>, memberId: string) => {
        e.stopPropagation();
        const button = e.currentTarget;
        activeButtonRef.current = button;
        setOpenMenuId(openMenuId === memberId ? null : memberId);
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
                {/* First glass-panel: Title & Invite button */}
                <div className="md:col-span-2 glass-panel rounded-3xl p-6 sm:p-8 relative overflow-hidden border-x border-b border-border-main">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-primary-start to-primary-end" />
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
                        <div>
                            <h2 className="text-2xl font-bold text-text-primary mb-2">{t('team.manage_team_title')}</h2>
                            <p className="text-text-secondary text-sm max-w-lg">{t('team.manage_team_subtitle')}</p>
                        </div>
                        {isCurrentUserOwner && (
                            <button 
                                onClick={() => setShowInviteModal(true)}
                                disabled={availableSeats <= 0}
                                className="btn-secondary border border-primary-start/50 px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shrink-0 w-full sm:w-auto justify-center"
                            >
                                <UserPlus size={18} /> {t('team.invite_member_button')}
                            </button>
                        )}
                    </div>
                </div>

                {/* Plan usage card */}
                <div className="glass-panel rounded-3xl p-8 flex flex-col justify-center relative overflow-hidden border border-border-main">
                    <div className="absolute top-0 w-full h-1.5 bg-gradient-to-r from-accent-start to-accent-end" />
                    <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-2">
                            <span className="text-text-secondary font-bold text-xs uppercase tracking-wider">{t('team.plan_usage_label')}</span>
                            <span className="px-2 py-0.5 rounded-full bg-primary-start/10 border border-primary-start/20 text-primary-start text-[10px] font-bold">
                                {t(`plan.${planName.toLowerCase()}`)}
                            </span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-bold ${availableSeats <= 0 ? 'bg-danger-start/20 text-danger-start' : 'bg-success-start/20 text-success-start'}`}>
                            {availableSeats > 0 ? t('team.status_active') : t('team.status_limit_reached')}
                        </span>
                    </div>
                    <div className="flex items-end gap-2 mb-2">
                        <span className="text-4xl font-bold text-text-primary">{usedSeats}</span>
                        <span className="text-lg text-text-muted mb-1">/ {seatLimit}</span>
                    </div>
                    <div className="w-full h-2 bg-surface/20 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-primary-start to-accent-start transition-all duration-1000" style={{ width: `${progressPercent}%` }} />
                    </div>
                </div>
            </div>

            {/* Members table */}
            <div className="glass-panel rounded-3xl overflow-hidden min-h-[300px] border border-border-main">
                <div className="overflow-x-auto">
                    <table className="w-full text-left min-w-[600px]">
                        <thead className="bg-surface/30 text-text-muted text-xs uppercase tracking-wider">
                            <tr>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_user')}</th>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_role')}</th>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_status')}</th>
                                <th className="px-6 py-4 font-bold text-right whitespace-nowrap">{t('team.table_actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border-main text-sm">
                            {members.map((member) => {
                                const memberRole = member.organization_role || member.role;
                                const isOwner = memberRole === 'OWNER';
                                const isSelf = currentUser?.id === member.id;
                                const isPending = member.status === 'pending_invite';
                                return (
                                    <tr key={member.id} className="hover:bg-surface/20 transition-colors group relative">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-surface/50 to-surface/70 flex items-center justify-center text-text-primary font-bold border border-border-main">
                                                    {member.username.substring(0, 2).toUpperCase()}
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-1 flex-wrap">
                                                        <span className="font-bold text-text-primary">{member.username}</span>
                                                        {isSelf && (
                                                            <span className="text-[10px] font-black uppercase tracking-widest bg-primary-start/10 text-primary-start px-2 py-1 rounded-md ml-2">
                                                                {t('team.label_current_user_short', 'TI')}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="text-xs text-text-muted">{member.email}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2">
                                                {isOwner ? <Crown size={14} className="text-warning-start" /> : <Briefcase size={14} className="text-text-muted" />}
                                                <span className={isOwner ? 'text-warning-start font-bold' : 'text-text-secondary'}>{memberRole}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-bold ${isPending ? 'bg-warning-start/10 text-warning-start border-warning-start/20' : 'bg-success-start/10 text-success-start border-success-start/20'}`}>
                                                <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${isPending ? 'bg-warning-start' : 'bg-success-start'}`} /> 
                                                {isPending ? t('team.status_pending') : t('team.status_active')}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right whitespace-nowrap">
                                            <div className="flex justify-end">
                                                <button
                                                    onClick={(e) => handleOpenMenu(e, member.id)}
                                                    className="p-2 text-text-muted hover:text-text-primary transition-colors flex items-center justify-center"
                                                    aria-label="Veprimet"
                                                >
                                                    <MoreHorizontal size={20} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Dropdown Portal - Context-Aware Menu */}
            {openMenuId && createPortal(
                <motion.div
                    key="team-dropdown-portal"
                    id="team-dropdown-portal"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="fixed z-[9999] w-48 rounded-xl shadow-2xl overflow-hidden"
                    style={{ 
                        top: menuPosition.top, 
                        left: menuPosition.left,
                        backgroundColor: '#0B0F1A',
                        border: '1px solid rgba(255,255,255,0.1)'
                    }}
                >
                    <div className="py-1">
                        {(() => {
                            const member = members.find(m => m.id === openMenuId);
                            if (!member) return null;
                            const isSelf = currentUser?.id === member.id;
                            const isPending = member.status === 'pending_invite';

                            if (isSelf) {
                                return (
                                    <button 
                                        onClick={handleMyProfile}
                                        className="w-full text-left px-4 py-3 text-sm font-bold text-text-primary flex items-center gap-3 transition-colors hover:bg-white/5"
                                    >
                                        <UserIcon size={16} /> Profili Im
                                    </button>
                                );
                            }

                            if (isPending) {
                                return (
                                    <>
                                        <button 
                                            onClick={() => handleResendInvite(member)}
                                            className="w-full text-left px-4 py-3 text-sm font-bold text-text-primary flex items-center gap-3 transition-colors hover:bg-white/5"
                                        >
                                            <Send size={16} /> Ridërgo Ftesën
                                        </button>
                                        <button 
                                            onClick={() => handleCancelInvite(member)}
                                            className="w-full text-left px-4 py-3 text-sm font-bold text-danger-start flex items-center gap-3 transition-colors hover:bg-danger-start/10"
                                        >
                                            <X size={16} /> Anulo Ftesën
                                        </button>
                                    </>
                                );
                            }

                            // Active member (not self, not pending)
                            return (
                                <button 
                                    onClick={() => handleRemoveMember(member.id)}
                                    className="w-full text-left px-4 py-3 text-sm font-bold text-danger-start flex items-center gap-3 transition-colors hover:bg-danger-start/10"
                                >
                                    <Trash2 size={16} /> Largo nga Ekipi
                                </button>
                            );
                        })()}
                    </div>
                </motion.div>,
                document.body
            )}

            {/* Invite Modal (unchanged) */}
            <AnimatePresence>
                {showInviteModal && (
                    <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="glass-panel border border-border-main w-full max-w-md p-8 rounded-3xl shadow-2xl relative">
                            <button onClick={() => { setShowInviteModal(false); setInviteResult(null); }} className="absolute top-6 right-6 text-text-muted hover:text-text-primary transition-colors"><X size={24} /></button>
                            
                            <div className="mb-6">
                                <div className="w-12 h-12 rounded-2xl bg-primary-start/20 flex items-center justify-center mb-4 text-primary-start">
                                    <UserPlus size={24} />
                                </div>
                                <h3 className="text-2xl font-bold text-text-primary">{t('team.invite_modal_title')}</h3>
                                <p className="text-text-secondary text-sm mt-1">{t('team.invite_modal_subtitle')}</p>
                            </div>

                            {!inviteResult ? (
                                <form onSubmit={handleInvite} className="space-y-6">
                                    {errorMsg && (
                                        <div className="p-4 rounded-xl bg-danger-start/20 border border-danger-start/30 text-danger-start flex items-start gap-3">
                                            <AlertTriangle className="flex-shrink-0 mt-0.5" size={18} />
                                            <span className="text-sm">{errorMsg}</span>
                                        </div>
                                    )}
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-text-muted uppercase tracking-wider">{t('general.email_label')}</label>
                                        <div className="relative">
                                            <Mail className="absolute left-4 top-3.5 w-5 h-5 text-text-muted" />
                                            <input autoFocus type="email" required value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="glass-input w-full pl-12 pr-4 py-3.5 rounded-xl text-text-primary" placeholder={t('general.email_placeholder')} />
                                        </div>
                                    </div>
                                    <button type="submit" disabled={inviting} className="btn-primary w-full py-3.5 rounded-xl font-bold shadow-lg hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2">
                                        {inviting ? <Loader2 className="animate-spin w-5 h-5" /> : <UserPlus size={18} />}
                                        {t('team.button_send_invite')}
                                    </button>
                                </form>
                            ) : (
                                <div className="space-y-6 text-center">
                                    <div className="p-4 rounded-xl bg-success-start/20 border border-success-start/30 text-success-start flex items-center justify-center gap-3">
                                        <CheckCircle className="flex-shrink-0" size={20} />
                                        <span className="font-medium">{inviteResult}</span>
                                    </div>
                                    <button onClick={() => { setShowInviteModal(false); setInviteResult(null); }} className="btn-secondary w-full py-3.5 rounded-xl font-bold transition-colors">
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