// FILE: src/components/business/TeamTab.tsx
// PHOENIX PROTOCOL - TEAM TAB V5.0 (ENTERPRISE GRANULAR CASE ACCESS CONTROL)

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    UserPlus, Mail, CheckCircle, X, Loader2, 
    AlertTriangle, Briefcase, Crown, MoreHorizontal, Trash2,
    Send, ShieldCheck, CheckSquare, Square
} from 'lucide-react';
import { User as UserIcon } from 'lucide-react';
import { apiService } from '../../services/api';
import { User, Organization, Case } from '../../data/types';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';
import { createPortal } from 'react-dom';
import { useLockBodyScroll } from '../../hooks/useLockBodyScroll';

export const TeamTab: React.FC = () => {
    const { t } = useTranslation();
    const { user: currentUser } = useAuth(); 
    
    const [members, setMembers] = useState<User[]>([]);
    const [organization, setOrganization] = useState<Organization | null>(null);
    const [firmCases, setFirmCases] = useState<Case[]>([]);
    const [loading, setLoading] = useState(true);
    
    const [inviteEmail, setInviteEmail] = useState("");
    const [inviting, setInviting] = useState(false);
    const [showInviteModal, setShowInviteModal] = useState(false);
    const [inviteResult, setInviteResult] = useState<string | null>(null);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);
    const [infoMsg, setInfoMsg] = useState<string | null>(null);
    
    const [openMenuId, setOpenMenuId] = useState<string | null>(null);
    const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
    const activeButtonRef = useRef<HTMLButtonElement | null>(null);

    // Qasja Granulare
    const [showAccessModal, setShowAccessModal] = useState(false);
    const [selectedMemberForAccess, setSelectedMemberForAccess] = useState<User | null>(null);
    const [memberAccessLevel, setMemberAccessLevel] = useState<'FULL' | 'SELECTIVE'>('FULL');
    const [assignedCaseIds, setAssignedCaseIds] = useState<Set<string>>(new Set());
    const [isSavingAccess, setIsSavingAccess] = useState(false);

    useLockBodyScroll(showInviteModal || showAccessModal);

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

    useEffect(() => {
        if (!openMenuId || !activeButtonRef.current) return;

        const updatePosition = () => {
            if (!activeButtonRef.current) return;
            const rect = activeButtonRef.current.getBoundingClientRect();
            const menuWidth = 192;
            const viewportWidth = window.innerWidth;
            let left = rect.right - menuWidth;
            if (left < 0) left = rect.left;
            if (left + menuWidth > viewportWidth) left = viewportWidth - menuWidth - 8;
            
            setMenuPosition({
                top: rect.bottom + 4,
                left: left,
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
            const [membersData, orgData, casesData] = await Promise.all([
                apiService.getOrganizationMembers(),
                apiService.getOrganization(),
                apiService.getCases()
            ]);
            setMembers(membersData);
            setOrganization(orgData);
            setFirmCases(Array.isArray(casesData) ? casesData : []);
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
        setInfoMsg(null);
        setInviteResult(null);
        try {
            const res = await apiService.inviteMember(inviteEmail);
            if (res.user && res.user.status === 'active') {
                setInfoMsg("Përdoruesi u shtua direkt në ekip pasi ka një llogari ekzistuese.");
            }
            
            setInviteResult("Ftesa u dërgua me sukses! Ju lutem njoftoni kolegun të kontrollojë edhe dosjen 'Spam'.");
            setInviteEmail(""); 
            fetchData();
        } catch (err: any) {
            const errorDetail = err?.response?.data?.detail || err?.message || '';
            const isDuplicateKey = errorDetail.includes('duplicate key') || errorDetail.includes('E11000');
            if (isDuplicateKey) {
                setErrorMsg("Ky email është regjistruar tashmë në sistem ose ka një ftesë aktive.");
            } else {
                setErrorMsg(errorDetail || "Ndodhi një gabim gjatë dërgimit të ftesës. Ju lutem provoni përsëri.");
            }
        } finally {
            setInviting(false);
        }
    };

    const handleRemoveMember = async (userId: string) => {
        if (!window.confirm(t('team.confirm_remove_member', 'A jeni të sigurt që dëshironi ta largoni këtë anëtar nga ekipi?'))) return;
        try {
            await apiService.removeOrganizationMember(userId);
            fetchData();
            setOpenMenuId(null);
        } catch (error) {
            console.error("Failed to remove member", error);
        }
    };

    const handleResendInvite = async (member: User) => {
        alert(`Ridërgo ftesë për ${member.email}`);
        setOpenMenuId(null);
    };

    const handleCancelInvite = async (member: User) => {
        if (!window.confirm(`Anulo ftesën për ${member.email}?`)) return;
        try {
            await apiService.removeOrganizationMember(member.id);
            fetchData();
            setOpenMenuId(null);
        } catch (error) {
            console.error("Failed to cancel invite", error);
        }
    };

    const handleOpenAccessModal = (member: User) => {
        setSelectedMemberForAccess(member);
        setMemberAccessLevel((member as any).org_access_level || 'FULL');
        setAssignedCaseIds(new Set((member as any).assigned_case_ids || []));
        setOpenMenuId(null);
        setShowAccessModal(true);
    };

    const handleSaveAccess = async () => {
        if (!selectedMemberForAccess) return;
        setIsSavingAccess(true);
        try {
            await apiService.axiosInstance.put(`/organizations/members/${selectedMemberForAccess.id}/access`, {
                org_access_level: memberAccessLevel,
                assigned_case_ids: Array.from(assignedCaseIds)
            });
            await fetchData();
            setShowAccessModal(false);
        } catch (error) {
            alert("Dështoi ruajtja e konfigurimit të qasjes.");
        } finally {
            setIsSavingAccess(false);
        }
    };

    const handleMyProfile = () => {
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
    const usedSeats = members.length;
    const availableSeats = Math.max(0, seatLimit - usedSeats);
    const progressPercent = Math.min((usedSeats / seatLimit) * 100, 100);
    
    const isUserAdminOrOwner = currentUser?.role === 'ADMIN' || currentUser?.organization_role === 'OWNER';
    const hasAnyAdminOrOwner = members.some(m => m.role === 'ADMIN' || m.organization_role === 'OWNER');
    const isCurrentUserOwner = isUserAdminOrOwner || (!hasAnyAdminOrOwner && currentUser?.id === members[0]?.id);
    
    const planName = organization?.plan_tier || 'DEFAULT';

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-8 pb-20 bg-canvas">
            
            {/* Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2 glass-panel rounded-3xl p-6 sm:p-8 relative overflow-hidden border border-main bg-surface/10">
                    <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-primary-start to-primary-end" />
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
                        <div>
                            <h2 className="text-2xl font-bold text-text-primary mb-2">{t('team.manage_team_title', 'Menaxhimi i Ekipit')}</h2>
                            <p className="text-text-secondary text-sm max-w-lg leading-relaxed">Ftoni kolegët dhe përcaktoni saktësisht në cilat lëndë ata kanë qasje për të punuar.</p>
                        </div>
                        {isCurrentUserOwner && (
                            <button 
                                type="button"
                                onClick={() => setShowInviteModal(true)}
                                disabled={availableSeats <= 0}
                                className="h-11 px-6 bg-surface hover:bg-hover border border-main text-text-primary rounded-xl font-bold flex items-center gap-2 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shrink-0 w-full sm:w-auto justify-center focus:outline-none"
                            >
                                <UserPlus size={18} /> {t('team.invite_member_button', 'Fto Anëtar')}
                            </button>
                        )}
                    </div>
                </div>

                <div className="glass-panel rounded-3xl p-8 flex flex-col justify-center relative overflow-hidden border border-main bg-surface/10">
                    <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-accent-start to-accent-end" />
                    <div className="flex justify-between items-center mb-4 select-none">
                        <div className="flex items-center gap-2">
                            <span className="text-text-secondary font-bold text-xs uppercase tracking-wider">{t('team.plan_usage_label', 'PËRDORIMI I PLANIT')}</span>
                            <span className="px-2.5 py-0.5 rounded-full bg-primary-start/15 border border-primary-start/20 text-primary-start text-[10px] font-bold">
                                {t(`plan.${planName.toLowerCase()}`, planName)}
                            </span>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-bold ${availableSeats <= 0 ? 'bg-danger-start/20 text-danger-start' : 'bg-status-success/20 text-status-success'}`}>
                            {availableSeats > 0 ? t('team.status_active', 'Aktiv') : t('team.status_limit_reached', 'Limiti u Arrit')}
                        </span>
                    </div>
                    <div className="flex items-end gap-2 mb-2">
                        <span className="text-4xl font-bold text-text-primary font-mono">{usedSeats}</span>
                        <span className="text-lg text-text-muted mb-1 font-semibold">/ {seatLimit}</span>
                    </div>
                    <div className="w-full h-2 bg-surface rounded-full overflow-hidden border border-main">
                        <div className="h-full bg-gradient-to-r from-primary-start to-accent-start transition-all duration-1000" style={{ width: `${progressPercent}%` }} />
                    </div>
                </div>
            </div>

            {/* Members table */}
            <div className="glass-panel rounded-3xl overflow-hidden min-h-[300px] border border-main bg-canvas shadow-sm">
                <div className="overflow-x-auto">
                    <table className="w-full text-left min-w-[600px]">
                        <thead className="bg-surface border-b border-main text-text-primary text-xs uppercase tracking-wider select-none">
                            <tr>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_user', 'Përdoruesi')}</th>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_role', 'Roli')}</th>
                                <th className="px-6 py-4 font-bold whitespace-nowrap">{t('team.table_status', 'Statusi')}</th>
                                <th className="px-6 py-4 font-bold text-right whitespace-nowrap">{t('team.table_actions', 'Veprime')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-main text-sm">
                            {members.map((member) => {
                                const memberRole = member.organization_role || member.role;
                                const isOwner = memberRole === 'OWNER';
                                const isSelf = currentUser?.id === member.id;
                                const isPending = member.status === 'pending_invite';
                                const accessLvl = (member as any).org_access_level || 'FULL';
                                
                                return (
                                    <tr key={member.id} className="hover:bg-hover transition-colors group relative">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-full bg-surface flex items-center justify-center text-text-primary font-bold border border-main">
                                                    {member.username.substring(0, 2).toUpperCase()}
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-1 flex-wrap">
                                                        <span className="font-bold text-text-primary">{member.username}</span>
                                                        {isSelf && (
                                                            <span className="text-[10px] font-black uppercase tracking-widest bg-primary-start/10 text-primary-start px-2 py-1 rounded-md ml-2 select-none">
                                                                {t('team.label_current_user_short', 'TI')}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="text-xs text-text-muted font-mono">{member.email}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex items-center gap-2">
                                                    {isOwner ? <Crown size={14} className="text-warning-start" /> : <Briefcase size={14} className="text-text-muted" />}
                                                    <span className={isOwner ? 'text-warning-start font-bold' : 'text-text-secondary'}>{memberRole}</span>
                                                </div>
                                                {!isOwner && !isPending && (
                                                    <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded w-max border ${accessLvl === 'FULL' ? 'bg-primary-start/10 text-primary-start border-primary-start/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                                                        {accessLvl === 'FULL' ? 'QASJE E PLOTË' : 'QASJE E KUFIZUAR'}
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-bold select-none ${isPending ? 'bg-warning-start/10 text-warning-start border-warning-start/20' : 'bg-status-success/15 text-status-success border-status-success/20'}`}>
                                                <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${isPending ? 'bg-warning-start' : 'bg-status-success'}`} /> 
                                                {isPending ? t('team.status_pending', 'Ftesë') : t('team.status_active', 'Aktiv')}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right whitespace-nowrap">
                                            <div className="flex justify-end">
                                                <button
                                                    type="button"
                                                    onClick={(e) => handleOpenMenu(e, member.id)}
                                                    className="flex items-center justify-center w-11 h-11 -mr-2 text-text-muted hover:text-text-primary transition-colors focus:outline-none"
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

            {/* Dropdown Portal */}
            {openMenuId && createPortal(
                <motion.div
                    key="team-dropdown-portal"
                    id="team-dropdown-portal"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="fixed z-[9999] w-52 rounded-xl shadow-2xl border border-main bg-canvas overflow-hidden"
                    style={{ 
                        top: menuPosition.top, 
                        left: menuPosition.left
                    }}
                >
                    <div className="py-1">
                        {(() => {
                            const member = members.find(m => m.id === openMenuId);
                            if (!member) return null;
                            const isSelf = currentUser?.id === member.id;
                            const isPending = member.status === 'pending_invite';
                            const isOwner = member.organization_role === 'OWNER';

                            if (isSelf) {
                                return (
                                    <button 
                                        type="button"
                                        onClick={handleMyProfile}
                                        className="w-full text-left px-4 h-11 text-sm font-bold text-text-primary flex items-center gap-3 transition-colors hover:bg-hover focus:outline-none"
                                    >
                                        <UserIcon size={16} className="text-text-muted" /> Profili Im
                                    </button>
                                );
                            }

                            if (isPending) {
                                return (
                                    <>
                                        <button 
                                            type="button"
                                            onClick={() => handleResendInvite(member)}
                                            className="w-full text-left px-4 h-11 text-sm font-bold text-text-primary flex items-center gap-3 transition-colors hover:bg-hover focus:outline-none"
                                        >
                                            <Send size={16} className="text-primary-start" /> Ridërgo Ftesën
                                        </button>
                                        <button 
                                            type="button"
                                            onClick={() => handleCancelInvite(member)}
                                            className="w-full text-left px-4 h-11 text-sm font-bold text-rose-500 flex items-center gap-3 transition-colors hover:bg-rose-500/10 focus:outline-none"
                                        >
                                            <X size={16} /> Anulo Ftesën
                                        </button>
                                    </>
                                );
                            }

                            return (
                                <>
                                    {!isOwner && isCurrentUserOwner && (
                                        <button 
                                            type="button"
                                            onClick={() => handleOpenAccessModal(member)}
                                            className="w-full text-left px-4 h-11 text-sm font-bold text-primary-start flex items-center gap-3 transition-colors hover:bg-hover border-b border-main focus:outline-none"
                                        >
                                            <ShieldCheck size={16} /> Menaxho Qasjen
                                        </button>
                                    )}
                                    <button 
                                        type="button"
                                        onClick={() => handleRemoveMember(member.id)}
                                        className="w-full text-left px-4 h-11 text-sm font-bold text-rose-500 flex items-center gap-3 transition-colors hover:bg-rose-500/10 focus:outline-none"
                                    >
                                        <Trash2 size={16} /> Largo nga Ekipi
                                    </button>
                                </>
                            );
                        })()}
                    </div>
                </motion.div>,
                document.body
            )}

            {/* QASJA GRANULARE MODAL */}
            <AnimatePresence>
                {showAccessModal && selectedMemberForAccess && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="glass-panel border border-main w-full max-w-2xl p-6 sm:p-8 rounded-3xl shadow-2xl relative bg-canvas flex flex-col max-h-[90vh]">
                            <div className="flex justify-between items-center mb-6 border-b border-main pb-4 shrink-0">
                                <div>
                                    <h3 className="text-xl font-bold text-text-primary tracking-tight">Qasja në Lëndë</h3>
                                    <p className="text-xs text-text-secondary mt-1">Konfiguro autorizimet për: <strong className="text-text-primary">{selectedMemberForAccess.username}</strong></p>
                                </div>
                                <button 
                                    onClick={() => setShowAccessModal(false)} 
                                    className="p-2 text-text-muted hover:text-text-primary hover:bg-hover rounded-xl transition-colors focus:outline-none"
                                >
                                    <X size={20} />
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto pr-2 custom-finance-scroll space-y-6">
                                {/* Type of Access */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div 
                                        onClick={() => setMemberAccessLevel('FULL')}
                                        className={`p-4 rounded-2xl border cursor-pointer transition-all ${memberAccessLevel === 'FULL' ? 'bg-primary-start/10 border-primary-start shadow-sm' : 'bg-surface border-main hover:bg-hover'}`}
                                    >
                                        <h4 className="text-sm font-bold text-text-primary flex items-center gap-2 mb-1">
                                            {memberAccessLevel === 'FULL' ? <CheckCircle size={16} className="text-primary-start" /> : <div className="w-4 h-4 rounded-full border border-text-muted" />}
                                            Qasje e Plotë
                                        </h4>
                                        <p className="text-xs text-text-secondary leading-snug pl-6">Anëtari ka qasje në të gjitha lëndët e zyrës, përfshirë lëndët e reja që do të krijohen.</p>
                                    </div>
                                    <div 
                                        onClick={() => setMemberAccessLevel('SELECTIVE')}
                                        className={`p-4 rounded-2xl border cursor-pointer transition-all ${memberAccessLevel === 'SELECTIVE' ? 'bg-amber-500/10 border-amber-500 shadow-sm' : 'bg-surface border-main hover:bg-hover'}`}
                                    >
                                        <h4 className="text-sm font-bold text-text-primary flex items-center gap-2 mb-1">
                                            {memberAccessLevel === 'SELECTIVE' ? <CheckCircle size={16} className="text-amber-500" /> : <div className="w-4 h-4 rounded-full border border-text-muted" />}
                                            Qasje e Kufizuar
                                        </h4>
                                        <p className="text-xs text-text-secondary leading-snug pl-6">Zgjidhni manualisht vetëm ato lëndë ku ky anëtar lejohet të lexojë dhe editojë dosjen.</p>
                                    </div>
                                </div>

                                {/* List of Cases for Selective Access */}
                                {memberAccessLevel === 'SELECTIVE' && (
                                    <div className="space-y-3 animate-in fade-in slide-in-from-top-4">
                                        <h4 className="text-xs font-black uppercase tracking-widest text-text-muted border-b border-main pb-2">Zgjidh Lëndët e Lejuara</h4>
                                        <div className="space-y-2">
                                            {firmCases.length === 0 ? (
                                                <p className="text-sm text-text-secondary italic">Nuk ka asnjë lëndë të hapur në zyrën tuaj.</p>
                                            ) : (
                                                firmCases.map(c => {
                                                    const isChecked = assignedCaseIds.has(c.id);
                                                    return (
                                                        <div 
                                                            key={c.id} 
                                                            onClick={() => {
                                                                setAssignedCaseIds(prev => {
                                                                    const nSet = new Set(prev);
                                                                    if (nSet.has(c.id)) nSet.delete(c.id);
                                                                    else nSet.add(c.id);
                                                                    return nSet;
                                                                });
                                                            }}
                                                            className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-all ${isChecked ? 'bg-primary-start/5 border-primary-start/50' : 'bg-surface border-main hover:bg-hover'}`}
                                                        >
                                                            {isChecked ? <CheckSquare size={18} className="text-primary-start shrink-0" /> : <Square size={18} className="text-text-muted shrink-0" />}
                                                            <div className="min-w-0">
                                                                <p className="text-sm font-bold text-text-primary truncate">{c.title || c.case_name || 'Rast pa Titull'}</p>
                                                                <p className="text-[10px] text-text-muted font-mono">{c.case_number}</p>
                                                            </div>
                                                        </div>
                                                    )
                                                })
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-5 mt-4 border-t border-main shrink-0">
                                <button type="button" onClick={() => setShowAccessModal(false)} className="h-11 px-6 rounded-xl font-bold text-sm bg-surface border border-main text-text-secondary hover:text-text-primary hover:bg-hover transition-all focus:outline-none">
                                    Anulo
                                </button>
                                <button 
                                    type="button" 
                                    onClick={handleSaveAccess} 
                                    disabled={isSavingAccess}
                                    className="h-11 px-8 rounded-xl font-bold text-sm bg-primary-start hover:bg-primary-start/90 text-white shadow-lg shadow-primary-start/20 flex items-center justify-center gap-2 transition-all focus:outline-none disabled:opacity-50"
                                >
                                    {isSavingAccess ? <Loader2 size={16} className="animate-spin" /> : "Ruaj Ndryshimet"}
                                </button>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Invite Modal */}
            <AnimatePresence>
                {showInviteModal && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }} className="glass-panel border border-main w-full max-w-md p-6 sm:p-8 rounded-3xl shadow-2xl relative bg-canvas">
                            <button 
                                type="button"
                                onClick={() => { setShowInviteModal(false); setInviteResult(null); setInfoMsg(null); }} 
                                className="absolute top-6 right-6 text-text-muted hover:text-text-primary transition-colors focus:outline-none"
                                aria-label="Close"
                            >
                                <X size={24} />
                            </button>
                            
                            <div className="mb-6 select-none">
                                <div className="w-12 h-12 rounded-2xl bg-primary-start/10 border border-primary-start/20 flex items-center justify-center mb-4 text-primary-start">
                                    <UserPlus size={24} />
                                </div>
                                <h3 className="text-2xl font-bold text-text-primary">{t('team.invite_modal_title', 'Fto një Koleg')}</h3>
                                <p className="text-text-secondary text-sm mt-1">{t('team.invite_modal_subtitle', 'Shkruani email-in e kolegut tuaj për ta ftuar në ekip.')}</p>
                            </div>

                            {!inviteResult ? (
                                <form onSubmit={handleInvite} className="space-y-6">
                                    {errorMsg && (
                                        <div className="p-4 rounded-xl bg-danger-start/15 border border-danger-start/20 text-danger-start flex items-start gap-3">
                                            <AlertTriangle className="flex-shrink-0 mt-0.5" size={18} />
                                            <span className="text-sm font-bold">{errorMsg}</span>
                                        </div>
                                    )}
                                    {infoMsg && (
                                        <div className="p-4 rounded-xl bg-primary-start/15 border border-primary-start/20 text-primary-start flex items-start gap-3">
                                            <AlertTriangle className="flex-shrink-0 mt-0.5" size={18} />
                                            <span className="text-sm font-bold">{infoMsg}</span>
                                        </div>
                                    )}
                                    <div className="space-y-1.5">
                                        <label className="text-xs font-bold text-text-muted uppercase tracking-wider">{t('general.email_label', 'EMAIL')}</label>
                                        <div className="relative">
                                            <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                                            <input autoFocus type="email" required value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} className="w-full pl-12 pr-4 h-11 bg-surface border border-main rounded-xl text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all" placeholder={t('general.email_placeholder', 'emri@zyra.com')} />
                                        </div>
                                    </div>
                                    <button type="submit" disabled={inviting} className="btn-primary w-full h-11 rounded-xl font-bold shadow-lg hover:scale-[1.01] active:scale-95 transition-all flex items-center justify-center gap-2 focus:outline-none">
                                        {inviting ? <Loader2 className="animate-spin w-5 h-5" /> : <UserPlus size={18} />}
                                        {t('team.button_send_invite', 'Dërgo Ftesën')}
                                    </button>
                                </form>
                            ) : (
                                <div className="space-y-6 text-center">
                                    <div className="p-4 rounded-xl bg-status-success/15 border border-status-success/20 text-status-success flex items-center justify-center gap-3">
                                        <CheckCircle className="flex-shrink-0" size={20} />
                                        <span className="font-semibold text-sm leading-relaxed">{inviteResult}</span>
                                    </div>
                                    <button type="button" onClick={() => { setShowInviteModal(false); setInviteResult(null); setInfoMsg(null); }} className="btn-secondary w-full h-11 rounded-xl font-bold transition-all focus:outline-none">
                                        {t('general.button_close', 'Mbyll')}
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