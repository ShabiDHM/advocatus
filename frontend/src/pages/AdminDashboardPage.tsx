// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - ADMIN DASHBOARD V6.1 (CLEANUP)
// 1. FIX: Removed unused imports ('Shield', 'AnimatePresence', 'Organization').
// 2. STATUS: Clean, warning-free code matching the restored UI.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Search, Edit2, Trash2, CheckCircle, Loader2, Clock, Briefcase, Crown, ArrowUpCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { apiService } from '../services/api';
import { User, UpdateUserRequest } from '../data/types';

// Unified type for display
type UnifiedAdminUser = User & { 
    firmName?: string; 
    tier?: string;
    organization_role?: string; 
    plan_tier?: string;
};

const AdminDashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [users, setUsers] = useState<UnifiedAdminUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [editingUser, setEditingUser] = useState<UnifiedAdminUser | null>(null);
    const [editForm, setEditForm] = useState<UpdateUserRequest & { plan_tier?: string }>({});

    useEffect(() => {
        loadAdminData();
    }, []);

    const loadAdminData = async () => {
        setIsLoading(true);
        try {
            const orgData = await apiService.getOrganizations();
            const userData = await apiService.getAllUsers();
            
            const mergedUsers: UnifiedAdminUser[] = userData.map((user: any) => {
                const org = orgData.find(o => o.id === user.id || o.owner_id === user.id);
                return {
                    ...user,
                    id: user.id || user._id,
                    role: user.role || 'STANDARD',
                    status: user.status || 'inactive',
                    subscription_status: user.subscription_status || 'INACTIVE',
                    plan_tier: user.plan_tier || 'SOLO',
                    organization_role: user.organization_role || 'OWNER',
                    firmName: org?.name,
                    tier: org?.tier || 'TIER_1'
                };
            }).filter((user: any) => user && typeof user.id === 'string' && user.id.trim() !== '');

            // Sort: Pending users first
            mergedUsers.sort((a, b) => {
                if (a.subscription_status !== 'ACTIVE' && b.subscription_status === 'ACTIVE') return -1;
                if (a.subscription_status === 'ACTIVE' && b.subscription_status !== 'ACTIVE') return 1;
                return 0;
            });

            setUsers(mergedUsers);
        } catch (error) {
            console.error("Failed to load admin data", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleEditClick = (user: UnifiedAdminUser) => {
        setEditingUser(user);
        setEditForm({
            username: user.username,
            email: user.email,
            role: user.role,
            subscription_status: user.subscription_status,
            status: user.status,
            plan_tier: user.plan_tier
        });
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser?.id) return;
        
        try {
            await apiService.updateUser(editingUser.id, editForm);
            setEditingUser(null);
            loadAdminData(); 
        } catch (error) {
            console.error("Failed to update user", error);
            alert(t('error.generic', 'Ndodhi një gabim.'));
        }
    };

    const handlePromoteUser = async (user: UnifiedAdminUser) => {
        if (!window.confirm(`Promote user ${user.username} to a Firm (Tier 2)?`)) return;
        try {
            await apiService.upgradeOrganizationTier(user.id, 'TIER_2');
            loadAdminData();
        } catch (error) {
            console.error("Failed to promote user", error);
            alert("Failed to promote user.");
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm(t('admin.confirmDelete', 'A jeni të sigurt?'))) return;
        try {
            await apiService.deleteUser(userId);
            loadAdminData();
        } catch (error) {
            console.error("Failed to delete user", error);
        }
    };

    const filteredUsers = users.filter(u =>
        u.username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.firmName?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const renderStatusBadge = (user: UnifiedAdminUser) => {
        // PHOENIX: Check Subscription Status (Gatekeeper)
        if (user.subscription_status === 'ACTIVE') {
            return <span className="flex items-center text-green-400 bg-green-400/10 px-2 py-1 rounded-full text-xs font-medium w-fit"><CheckCircle className="w-3 h-3 mr-1" /> {t('admin.statuses.ACTIVE', 'Aktive')}</span>;
        }
        return <span className="flex items-center text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded-full text-xs font-medium w-fit"><Clock className="w-3 h-3 mr-1" /> {t('admin.statuses.INACTIVE', 'Në Pritje')}</span>;
    };

    if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 overflow-hidden">
            <style>{`.dark-select { color-scheme: dark; }`}</style>

            <div className="mb-8">
                <h1 className="text-3xl font-bold text-text-primary mb-2">{t('admin.title', 'Paneli i Administratorit')}</h1>
                <p className="text-text-secondary">{t('admin.subtitle', 'Menaxhimi i përdoruesve dhe sistemit.')}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between shadow-lg">
                    <div><p className="text-text-secondary text-sm font-medium">{t('admin.totalUsers', 'Total Përdorues')}</p><h3 className="text-3xl font-bold text-white">{users.length}</h3></div>
                    <div className="p-3 rounded-xl bg-blue-500/20 text-blue-400"><Users /></div>
                </div>
                <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between shadow-lg">
                    <div><p className="text-text-secondary text-sm font-medium">{t('admin.totalOrgs', 'Total Firma')}</p><h3 className="text-3xl font-bold text-emerald-400">{users.filter(u => u.tier === 'TIER_2').length}</h3></div>
                    <div className="p-3 rounded-xl bg-emerald-500/20 text-emerald-400"><Briefcase /></div>
                </div>
                <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between shadow-lg">
                    <div><p className="text-text-secondary text-sm font-medium">{t('admin.pendingApproval', 'Në Pritje')}</p><h3 className="text-3xl font-bold text-yellow-500">{users.filter(u => u.subscription_status !== 'ACTIVE').length}</h3></div>
                    <div className="p-3 rounded-xl bg-yellow-500/20 text-yellow-400"><Clock /></div>
                </div>
            </div>

            <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge overflow-hidden shadow-xl flex flex-col">
                <div className="p-4 border-b border-glass-edge flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white/5 gap-4">
                    <h3 className="text-lg font-semibold text-white">{t('admin.registeredUsers', 'Përdoruesit e Regjistruar')}</h3>
                    <div className="relative w-full sm:w-auto">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
                        <input type="text" placeholder={t('general.search', 'Kërko...')} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full sm:w-64 pl-9 pr-4 py-2 bg-black/40 border border-white/10 rounded-lg text-sm text-white focus:ring-1 focus:ring-primary-start outline-none" />
                    </div>
                </div>

                <div className="w-full overflow-x-auto scrollbar-hide">
                    <table className="w-full text-left text-sm text-text-secondary min-w-[1000px]">
                        <thead className="bg-black/20 text-text-primary uppercase text-xs">
                            <tr>
                                <th className="px-6 py-3 font-semibold tracking-wider">{t('admin.table.user', 'Përdoruesi')}</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">Organizata</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">Plani (Tier)</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">{t('admin.table.role', 'Roli')}</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">{t('admin.table.status', 'Statusi')}</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">{t('admin.table.registered', 'Regjistruar')}</th>
                                <th className="px-6 py-3 text-right font-semibold tracking-wider">{t('general.actions', 'Veprime')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {filteredUsers.map((user) => (
                                <tr key={user.id} className="hover:bg-white/5 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center">
                                            <div className="w-8 h-8 rounded-full bg-primary-start/20 flex items-center justify-center text-primary-start font-bold mr-3 border border-primary-start/30 shrink-0">
                                                {user.username.charAt(0).toUpperCase()}
                                            </div>
                                            <div className="min-w-0">
                                                <div className="font-medium text-white truncate max-w-[120px] sm:max-w-xs">{user.username}</div>
                                                <div className="text-xs text-gray-500 truncate max-w-[120px] sm:max-w-xs">{user.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-xs font-medium text-white">{user.firmName || 'N/A'}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            {user.tier === 'TIER_2' && <Crown className="w-3 h-3 text-purple-400" />}
                                            <span className={`text-xs font-mono uppercase ${user.tier === 'TIER_2' ? 'text-purple-400 font-bold' : 'text-gray-400'}`}>
                                                {user.tier || 'TIER_1'}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4"><span className={`px-2 py-1 rounded-full text-xs font-medium border ${user.role.toUpperCase() === 'ADMIN' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>{user.role}</span></td>
                                    <td className="px-6 py-4">{renderStatusBadge(user)}</td>
                                    <td className="px-6 py-4 whitespace-nowrap">{new Date(user.created_at).toLocaleDateString()}</td>
                                    <td className="px-6 py-4 text-right space-x-2 whitespace-nowrap">
                                        {/* PHOENIX: Promote Button (Only for Non-Admins & Tier 1) */}
                                        {user.role !== 'ADMIN' && user.tier !== 'TIER_2' && (
                                            <button onClick={() => handlePromoteUser(user)} className="bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 hover:text-purple-300 p-2 rounded-lg transition-colors border border-purple-500/20" title="Promote to Firm"><ArrowUpCircle className="w-4 h-4" /></button>
                                        )}
                                        <button onClick={() => handleEditClick(user)} className="bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 hover:text-blue-300 p-2 rounded-lg transition-colors border border-blue-500/20" title={t('general.edit', 'Ndrysho')}><Edit2 className="w-4 h-4" /></button>
                                        <button onClick={() => handleDeleteUser(user.id)} className="bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 p-2 rounded-lg transition-colors border border-red-500/20" title={t('general.delete', 'Fshi')}><Trash2 className="w-4 h-4" /></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {editingUser && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <motion.div 
                        initial={{ scale: 0.95, opacity: 0 }} 
                        animate={{ scale: 1, opacity: 1 }} 
                        className="bg-[#1f2937] border border-white/10 p-6 rounded-2xl w-full max-w-md shadow-2xl max-h-[90vh] overflow-y-auto"
                    >
                        <h3 className="text-xl font-bold text-white mb-6 border-b border-white/10 pb-4">{t('admin.editModal.title', 'Ndrysho Përdoruesin')}</h3>
                        <form onSubmit={handleUpdateUser} className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-gray-400 uppercase mb-1">{t('admin.editModal.username', 'Emri i Përdoruesit')}</label>
                                <input type="text" value={editForm.username || ''} onChange={e => setEditForm({ ...editForm, username: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-primary-start outline-none" />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-400 uppercase mb-1">{t('admin.editModal.email', 'Email')}</label>
                                <input type="email" value={editForm.email || ''} onChange={e => setEditForm({ ...editForm, email: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-primary-start outline-none" />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 uppercase mb-1">{t('admin.editModal.role', 'Roli')}</label>
                                    <select value={editForm.role || 'STANDARD'} onChange={e => setEditForm({ ...editForm, role: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-primary-start outline-none dark-select">
                                        <option value="STANDARD">{t('admin.roles.STANDARD', 'Përdorues')}</option>
                                        <option value="ADMIN">{t('admin.roles.ADMIN', 'Admin')}</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 uppercase mb-1">{t('admin.editModal.subscriptionStatus', 'Statusi (Gatekeeper)')}</label>
                                    <select 
                                        value={editForm.subscription_status} 
                                        onChange={e => setEditForm({ ...editForm, subscription_status: e.target.value })} 
                                        className={`w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-primary-start outline-none dark-select font-bold ${editForm.subscription_status === 'ACTIVE' ? 'text-green-400' : 'text-yellow-400'}`}
                                    >
                                        <option value="ACTIVE">ACTIVE (Lejo)</option>
                                        <option value="INACTIVE">INACTIVE (Blloko)</option>
                                    </select>
                                </div>
                            </div>
                            
                            <div>
                                <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Paketa (Plan Tier)</label>
                                <select 
                                    value={editForm.plan_tier || 'SOLO'} 
                                    onChange={e => setEditForm({ ...editForm, plan_tier: e.target.value })} 
                                    className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-amber-500 outline-none font-mono dark-select"
                                >
                                    <option value="SOLO">SOLO (1 Përdorues)</option>
                                    <option value="STARTUP">STARTUP (5 Përdorues)</option>
                                    <option value="GROWTH">GROWTH (10 Përdorues)</option>
                                    <option value="ENTERPRISE">ENTERPRISE (50+)</option>
                                </select>
                            </div>
                            
                            <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-white/10">
                                <button type="button" onClick={() => setEditingUser(null)} className="px-4 py-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors">{t('general.cancel', 'Anulo')}</button>
                                <button type="submit" className="px-6 py-2 rounded-lg bg-primary-start hover:bg-primary-end text-white font-semibold shadow-lg shadow-primary-start/20 transition-all">{t('general.save', 'Ruaj')}</button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default AdminDashboardPage;