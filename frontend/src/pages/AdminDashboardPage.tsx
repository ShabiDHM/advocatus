// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - ADMIN DASHBOARD V5.1 (CLEANUP)
// 1. FIX: Removed unused 'ArrowUpCircle' and 'Organization' imports.
// 2. STATUS: Zero warnings. Unified view is stable.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Search, Loader2, ShieldAlert, ChevronsUpDown, Crown, Trash2, Briefcase, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiService } from '../services/api';
import { User } from '../data/types';

// A new combined type for our unified list
type UnifiedAdminUser = User & { firmName?: string; tier?: string };

const AdminDashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [unifiedUsers, setUnifiedUsers] = useState<UnifiedAdminUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [showUsers, setShowUsers] = useState(true);

    useEffect(() => {
        loadAdminData();
    }, []);

    const loadAdminData = async () => {
        setIsLoading(true);
        try {
            // Fetch both and merge them
            const orgData = await apiService.getOrganizations();
            const userData = await apiService.getAllUsers();
            
            const mergedUsers: UnifiedAdminUser[] = userData
                .filter(user => user && user.id)
                .map(user => {
                    const org = orgData.find(o => o.id === user.id || o.owner_id === user.id);
                    return {
                        ...user,
                        firmName: org?.name,
                        tier: org?.tier || 'TIER_1'
                    };
                });
            
            // Sort to put pending users at the top
            mergedUsers.sort((a, b) => {
                if (a.subscription_status !== 'ACTIVE' && b.subscription_status === 'ACTIVE') return -1;
                if (a.subscription_status === 'ACTIVE' && b.subscription_status !== 'ACTIVE') return 1;
                return 0;
            });

            setUnifiedUsers(mergedUsers);

        } catch (error) {
            console.error("Failed to load admin data", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handlePromoteUser = async (user: UnifiedAdminUser) => {
        if (!window.confirm(`Promote user ${user.username} to a Firm (Tier 2)?`)) return;
        try {
            await apiService.upgradeOrganizationTier(user.id, 'TIER_2');
            loadAdminData();
        } catch (error) {
            console.error("Failed to promote user", error);
        }
    };

    const handleToggleUserStatus = async (user: UnifiedAdminUser) => {
        const newStatus = user.subscription_status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE';
        try {
            await apiService.updateUser(user.id, { subscription_status: newStatus });
            loadAdminData();
        } catch (error) {
            console.error("Status update failed", error);
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm(t('admin.confirmDelete', 'Are you sure?'))) return;
        try {
            await apiService.deleteUser(userId);
            loadAdminData();
        } catch (error) {
            console.error("Delete failed", error);
            alert("Failed to delete user.");
        }
    };
    
    const filteredUsers = unifiedUsers.filter(user => 
        user.username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.firmName?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const totalFirms = unifiedUsers.filter(u => u.tier === 'TIER_2').length;
    const pendingUsers = unifiedUsers.filter(u => u.subscription_status !== 'ACTIVE').length;

    if (isLoading) return <div className="flex justify-center items-center h-screen"><Loader2 className="animate-spin h-12 w-12 text-primary-start" /></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 min-h-screen">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2 tracking-tight flex items-center gap-3">
                    <ShieldAlert className="text-primary-start" size={32} />
                    {t('admin.title')}
                </h1>
                <p className="text-text-secondary">{t('admin.subtitle')}</p>
            </div>

            {/* STATS CARDS */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.totalOrgs')}</p><h3 className="text-3xl font-bold text-white">{totalFirms}</h3></div>
                    <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20"><Crown size={24} /></div>
                </div>
                <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.totalUsers')}</p><h3 className="text-3xl font-bold text-white">{unifiedUsers.length}</h3></div>
                    <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20"><Users size={24} /></div>
                </div>
                <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.pendingApproval')}</p><h3 className="text-3xl font-bold text-white">{pendingUsers}</h3></div>
                    <div className="p-3 rounded-xl bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"><AlertTriangle size={24} /></div>
                </div>
            </div>

            {/* UNIFIED USER MANAGEMENT TABLE */}
            <div className="mt-8">
                 <button onClick={() => setShowUsers(!showUsers)} className="w-full glass-panel p-4 rounded-xl flex justify-between items-center hover:bg-white/5 transition-colors">
                    <h3 className="text-lg font-bold text-gray-400">{t('admin.userManagement')}</h3>
                    <ChevronsUpDown className={`text-gray-500 transition-transform ${showUsers ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                {showUsers && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden mt-4">
                        <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl">
                             <div className="p-5 border-b border-white/5 flex justify-end items-center bg-white/5">
                                <div className="relative w-full sm:w-auto">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
                                    <input type="text" placeholder={t('admin.searchOrgs')} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="glass-input pl-10 pr-4 py-2 w-full sm:w-64 text-sm rounded-xl" />
                                </div>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm text-text-secondary">
                                    <thead className="bg-black/20 text-gray-400 uppercase text-xs font-bold">
                                        <tr>
                                            <th className="px-6 py-4">{t('admin.userDetails')}</th>
                                            <th className="px-6 py-4">{t('admin.firmName')}</th>
                                            <th className="px-6 py-4">{t('admin.tier')}</th>
                                            <th className="px-6 py-4">{t('admin.gatekeeperStatus')}</th>
                                            <th className="px-6 py-4 text-right">{t('admin.actions')}</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {filteredUsers.map((user) => (
                                            <tr key={user.id} className={`hover:bg-white/5 transition-colors ${user.subscription_status !== 'ACTIVE' ? 'bg-yellow-500/5' : ''}`}>
                                                <td className="px-6 py-4">
                                                    <div className="font-bold text-white">{user.username}</div>
                                                    <div className="text-xs text-gray-500 font-mono">{user.email}</div>
                                                </td>
                                                <td className="px-6 py-4 font-bold text-white">{user.firmName || 'N/A'}</td>
                                                <td className="px-6 py-4">
                                                     <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${user.tier === 'TIER_2' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-gray-500/10 text-gray-400 border-gray-500/20'}`}>
                                                        {user.tier}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                     {user.subscription_status === 'ACTIVE' ? (
                                                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-bold">
                                                          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> {t('admin.active')}
                                                        </span>
                                                     ) : (
                                                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 text-xs font-bold">
                                                          <div className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" /> {t('admin.pending')}
                                                        </span>
                                                     )}
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <div className="flex justify-end gap-2">
                                                        {user.role !== 'ADMIN' && user.tier !== 'TIER_2' && (
                                                            <button onClick={() => handlePromoteUser(user)} className="p-2 hover:bg-purple-500/10 text-purple-400 rounded-lg border border-purple-500/20 transition-colors flex items-center gap-1" title={t('admin.promote')}>
                                                                <Briefcase size={14} /> {t('admin.promote')}
                                                            </button>
                                                        )}
                                                        <button onClick={() => handleToggleUserStatus(user)} className={`p-2 rounded-lg text-xs font-bold border transition-colors flex items-center gap-1 min-w-[100px] justify-center ${user.subscription_status === 'ACTIVE' ? "hover:bg-red-500/10 text-red-400 border-red-500/20" : "bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border-emerald-500/30"}`} >
                                                            {user.subscription_status === 'ACTIVE' ? (<><XCircle size={14} /> {t('admin.deactivate')}</>) : (<><CheckCircle size={14} /> {t('admin.activate')}</>)}
                                                        </button>
                                                        <button onClick={() => handleDeleteUser(user.id)} className="p-2 hover:bg-red-500/10 text-red-400 rounded-lg border border-red-500/20 transition-colors" title={t('admin.delete')}>
                                                            <Trash2 size={16} />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </motion.div>
                )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default AdminDashboardPage;