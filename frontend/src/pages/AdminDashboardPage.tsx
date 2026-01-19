// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - ADMIN DASHBOARD V10.1 (SEQUENTIAL UPDATES)
// 1. FIX: Enforces sequential execution of 'updateUser' and 'updateSubscription'.
// 2. LOGIC: Prioritizes subscription update to ensure Plan Tier changes stick.
// 3. STATUS: Fixes the issue where Plan remains 'SOLO' after edit.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
    Users, Search, Edit2, Trash2, CheckCircle, Loader2, Clock, 
    Briefcase, Crown, Calendar as CalendarIcon, 
    AlertTriangle, Building2 
} from 'lucide-react';
import { motion } from 'framer-motion';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";
import { apiService } from '../services/api';
import { User, UpdateUserRequest, SubscriptionUpdate } from '../data/types';

type UnifiedAdminUser = User & { 
    firmName?: string; 
    tier?: string;
    organization_role?: string; 
    plan_tier?: string;
    expiry_date?: Date | null;
};

const AdminDashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [users, setUsers] = useState<UnifiedAdminUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [editingUser, setEditingUser] = useState<UnifiedAdminUser | null>(null);

    const [editForm, setEditForm] = useState<UpdateUserRequest & { plan_tier?: string; expiry_date?: Date | null }>({});

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
                const effectiveTier = (org?.tier === 'TIER_2' || user.plan_tier === 'STARTUP') ? 'TIER_2' : 'TIER_1';
                const firmDisplayName = org?.name || user.organization_name; 

                return {
                    ...user,
                    id: user.id || user._id,
                    role: user.role || 'STANDARD',
                    status: user.status || 'inactive',
                    subscription_status: user.subscription_status || 'INACTIVE',
                    plan_tier: user.plan_tier || 'SOLO',
                    organization_role: user.organization_role || 'OWNER',
                    firmName: firmDisplayName, 
                    tier: effectiveTier,
                    expiry_date: user.subscription_expiry ? new Date(user.subscription_expiry) : null
                };
            }).filter((user: any) => user && typeof user.id === 'string' && user.id.trim() !== '');

            mergedUsers.sort((a, b) => {
                const scoreA = getStatusScore(a);
                const scoreB = getStatusScore(b);
                return scoreA - scoreB;
            });

            setUsers(mergedUsers);
        } catch (error) {
            console.error("Failed to load admin data", error);
        } finally {
            setIsLoading(false);
        }
    };

    const getStatusScore = (user: UnifiedAdminUser) => {
        if (user.subscription_status !== 'ACTIVE') return 0; 
        if (user.expiry_date && user.expiry_date < new Date()) return 1; 
        return 2; 
    };

    const handleEditClick = (user: UnifiedAdminUser) => {
        setEditingUser(user);
        setEditForm({
            username: user.username,
            email: user.email,
            role: user.role,
            subscription_status: user.subscription_status,
            status: user.status,
            plan_tier: user.plan_tier || 'SOLO',
            expiry_date: user.expiry_date
        });
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser?.id) return;
        
        try {
            // PHOENIX FIX: Run updates sequentially to prevent race conditions.
            
            // 1. Update Subscription & Plan FIRST (Critical)
            const subData: SubscriptionUpdate = {
                status: editForm.subscription_status || 'INACTIVE',
                plan_tier: editForm.plan_tier,
                expiry_date: editForm.expiry_date ? editForm.expiry_date.toISOString() : undefined
            };
            await apiService.updateSubscription(editingUser.id, subData);

            // 2. Update Basic Info SECOND
            await apiService.updateUser(editingUser.id, {
                username: editForm.username,
                email: editForm.email,
                role: editForm.role
            });

            setEditingUser(null);
            // Small delay to allow DB propagation
            setTimeout(() => loadAdminData(), 500); 
        } catch (error) {
            console.error("Failed to update user", error);
            alert(t('error.generic', 'Ndodhi një gabim.'));
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm(t('admin.confirmDelete', 'A jeni të sigurt? Kjo do të fshijë TË GJITHA të dhënat.'))) return;
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
        const isExpired = user.expiry_date && user.expiry_date < new Date();
        
        if (user.subscription_status === 'ACTIVE') {
            if (isExpired) {
                return (
                    <div className="flex flex-col items-start gap-1">
                        <span className="flex items-center text-red-400 bg-red-400/10 px-2 py-1 rounded-lg text-xs font-bold w-fit border border-red-500/20">
                            <AlertTriangle className="w-3 h-3 mr-1" /> EXPIRED
                        </span>
                        <span className="text-[10px] text-red-300 font-mono">
                            {user.expiry_date?.toLocaleDateString()}
                        </span>
                    </div>
                );
            }
            return <span className="flex items-center text-green-400 bg-green-400/10 px-2 py-1 rounded-lg text-xs font-bold w-fit border border-green-500/20"><CheckCircle className="w-3 h-3 mr-1" /> {t('admin.statuses.ACTIVE', 'Aktive')}</span>;
        }
        return <span className="flex items-center text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded-lg text-xs font-bold w-fit border border-yellow-500/20"><Clock className="w-3 h-3 mr-1" /> {t('admin.statuses.INACTIVE', 'Në Pritje')}</span>;
    };

    if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 overflow-hidden">
            <style>{`.dark-select { color-scheme: dark; } .react-datepicker-wrapper { width: 100%; }`}</style>

            <div className="mb-8">
                <h1 className="text-3xl font-bold text-text-primary mb-2">{t('admin.title', 'Paneli i Administratorit')}</h1>
                <p className="text-text-secondary">{t('admin.subtitle', 'Menaxhimi i përdoruesve dhe sistemit.')}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between shadow-lg">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.totalUsers', 'Total Përdorues')}</p><h3 className="text-3xl font-bold text-white">{users.length}</h3></div>
                    <div className="p-3 rounded-xl bg-blue-500/20 text-blue-400"><Users /></div>
                </div>
                <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between shadow-lg">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.totalOrgs', 'Total Firma')}</p><h3 className="text-3xl font-bold text-emerald-400">{users.filter(u => u.plan_tier === 'STARTUP').length}</h3></div>
                    <div className="p-3 rounded-xl bg-emerald-500/20 text-emerald-400"><Building2 /></div>
                </div>
                <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between shadow-lg">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.pendingApproval', 'Në Pritje')}</p><h3 className="text-3xl font-bold text-yellow-500">{users.filter(u => u.subscription_status !== 'ACTIVE').length}</h3></div>
                    <div className="p-3 rounded-xl bg-yellow-500/20 text-yellow-400"><Clock /></div>
                </div>
            </div>

            <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge overflow-hidden shadow-xl flex flex-col">
                <div className="p-4 border-b border-glass-edge flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white/5 gap-4">
                    <h3 className="text-lg font-semibold text-white">{t('admin.userManagement', 'Menaxhimi i Përdoruesve')}</h3>
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
                                <th className="px-6 py-3 font-semibold tracking-wider">Plani & Skadenca</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">{t('admin.table.role', 'Roli')}</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">{t('admin.table.status', 'Statusi')}</th>
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
                                        {(user.plan_tier === 'STARTUP' || user.tier === 'TIER_2' || user.firmName) ? (
                                            <div className="flex items-center gap-2">
                                                <Building2 className="w-4 h-4 text-purple-400" />
                                                <span className="text-white font-medium">{user.firmName || "Firm (No Name)"}</span>
                                            </div>
                                        ) : (
                                            <span className="text-xs text-gray-500">Individual</span>
                                        )}
                                    </td>

                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <div className="flex items-center gap-2 mb-1">
                                                {user.plan_tier !== 'SOLO' && <Crown className="w-3 h-3 text-amber-400" />}
                                                <span className={`text-xs font-mono uppercase font-bold ${user.plan_tier === 'STARTUP' ? 'text-purple-400' : 'text-gray-300'}`}>
                                                    {user.plan_tier || 'SOLO'}
                                                </span>
                                            </div>
                                            {user.expiry_date && (
                                                <div className="flex items-center text-[10px] text-gray-500">
                                                    <CalendarIcon className="w-3 h-3 mr-1" />
                                                    {user.expiry_date.toLocaleDateString()}
                                                </div>
                                            )}
                                        </div>
                                    </td>
                                    
                                    <td className="px-6 py-4"><span className={`px-2 py-1 rounded-full text-xs font-medium border ${user.role.toUpperCase() === 'ADMIN' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>{user.role}</span></td>
                                    <td className="px-6 py-4">{renderStatusBadge(user)}</td>
                                    
                                    <td className="px-6 py-4 text-right space-x-2 whitespace-nowrap">
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
                    <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="bg-[#1f2937] border border-white/10 p-6 rounded-2xl w-full max-w-lg shadow-2xl overflow-visible">
                        <h3 className="text-xl font-bold text-white mb-6 border-b border-white/10 pb-4">Menaxho Përdoruesin: {editingUser.username}</h3>
                        <form onSubmit={handleUpdateUser} className="space-y-4">
                            
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Username</label>
                                    <input type="text" value={editForm.username || ''} onChange={e => setEditForm({ ...editForm, username: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none focus:border-primary-start" />
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Email</label>
                                    <input type="email" value={editForm.email || ''} onChange={e => setEditForm({ ...editForm, email: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none focus:border-primary-start" />
                                </div>
                            </div>

                            <div className="p-4 bg-white/5 rounded-xl border border-white/10 space-y-4">
                                <h4 className="text-sm font-bold text-primary-300 flex items-center gap-2"><Briefcase size={16}/> Abonimi</h4>
                                
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Statusi (Gatekeeper)</label>
                                        <select 
                                            value={editForm.subscription_status} 
                                            onChange={e => setEditForm({ ...editForm, subscription_status: e.target.value })} 
                                            className={`w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 outline-none dark-select font-bold ${editForm.subscription_status === 'ACTIVE' ? 'text-green-400' : 'text-yellow-400'}`}
                                        >
                                            <option value="ACTIVE">ACTIVE (Lejo)</option>
                                            <option value="INACTIVE">INACTIVE (Blloko)</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Plani</label>
                                        <select value={editForm.plan_tier || 'SOLO'} onChange={e => setEditForm({ ...editForm, plan_tier: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none dark-select">
                                            <option value="SOLO">SOLO (Individual)</option>
                                            <option value="STARTUP">STARTUP (Organizatë - 5 Users)</option>
                                        </select>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Data e Skadimit</label>
                                    <DatePicker 
                                        selected={editForm.expiry_date} 
                                        onChange={(date) => setEditForm({ ...editForm, expiry_date: date })} 
                                        className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none focus:border-primary-start"
                                        placeholderText="Pa limit (No Expiry)"
                                        dateFormat="dd/MM/yyyy"
                                    />
                                    <p className="text-[10px] text-gray-500 mt-1">Lëre bosh për akses të përhershëm.</p>
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 pt-4">
                                <button type="button" onClick={() => setEditingUser(null)} className="px-4 py-2 text-gray-400 hover:text-white transition-colors">{t('general.cancel', 'Anulo')}</button>
                                <button type="submit" className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-lg font-bold shadow-lg shadow-primary-start/20">{t('general.save', 'Ruaj')}</button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default AdminDashboardPage;