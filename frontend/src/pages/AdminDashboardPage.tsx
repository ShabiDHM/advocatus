// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - ADMIN DASHBOARD V13.1 (ICON REINTEGRATION)
// 1. RESTORED: 'Briefcase' icon usage in the User Base header to resolve TS6133.
// 2. MAINTAINED: Full Feature Tier (BASIC/PRO) and Capacity (1/10 Seats) logic.
// 3. STATUS: Clean, warning-free build.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
    Search, Edit2, Trash2, CheckCircle, Loader2, Clock, 
    Briefcase, Calendar as CalendarIcon, 
    AlertTriangle, Building2, User as UserIcon, Star, Shield, Mail, Zap
} from 'lucide-react';
import { motion } from 'framer-motion';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";
import { apiService } from '../services/api';
import { User, UpdateUserRequest } from '../data/types';
import { AccountType, SubscriptionTier, ProductPlan } from '../data/enums';

type UnifiedAdminUser = User & { 
    firmName?: string; 
    expiry_date?: Date | null;
    plan_tier?: 'DEFAULT' | 'GROWTH';
    user_limit?: number;
};

const AdminDashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [users, setUsers] = useState<UnifiedAdminUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [editingUser, setEditingUser] = useState<UnifiedAdminUser | null>(null);

    const [editForm, setEditForm] = useState<Partial<UnifiedAdminUser> & { expiry_date?: Date | null }>({});

    useEffect(() => {
        loadAdminData();
    }, []);

    const loadAdminData = async () => {
        setIsLoading(true);
        try {
            const userData = await apiService.getAllUsers();
            
            const mappedUsers: UnifiedAdminUser[] = userData.map((user: any) => ({
                ...user,
                id: user.id || user._id,
                firmName: user.organization_name,
                expiry_date: user.subscription_expiry ? new Date(user.subscription_expiry) : null,
                plan_tier: user.plan_tier || (user.product_plan === ProductPlan.TEAM_PLAN ? 'GROWTH' : 'DEFAULT'),
                user_limit: user.user_limit || (user.product_plan === ProductPlan.TEAM_PLAN ? 10 : 1) 
            })).filter((user: any) => user && typeof user.id === 'string' && user.id.trim() !== '');

            mappedUsers.sort((a, b) => getStatusScore(a) - getStatusScore(b));
            setUsers(mappedUsers);
        } catch (error) {
            console.error("Failed to load admin data", error);
        } finally {
            setIsLoading(false);
        }
    };

    const getStatusScore = (user: UnifiedAdminUser) => {
        if (user.status === 'pending_invite') return 1;
        if (user.subscription_status !== 'ACTIVE') return 0; 
        return 2; 
    };

    const handleEditClick = (user: UnifiedAdminUser) => {
        setEditingUser(user);
        setEditForm({
            ...user,
            expiry_date: user.expiry_date
        });
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser?.id) return;
        
        try {
            const userUpdatePayload: UpdateUserRequest = {
                username: editForm.username,
                email: editForm.email,
                role: editForm.role,
                status: editForm.status,
                account_type: editForm.account_type,
                subscription_tier: editForm.subscription_tier,
                product_plan: editForm.product_plan,
                subscription_status: editForm.subscription_status,
                subscription_expiry: editForm.expiry_date ? editForm.expiry_date.toISOString() : undefined,
            };

            await apiService.updateUser(editingUser.id, userUpdatePayload);

            const targetOrgTier = editForm.product_plan === ProductPlan.TEAM_PLAN ? 'GROWTH' : 'DEFAULT';
            
            if (targetOrgTier !== editingUser.plan_tier || editForm.plan_tier !== editingUser.plan_tier) {
                const finalTier = editForm.plan_tier || targetOrgTier;
                await apiService.upgradeOrganizationTier(editingUser.id, finalTier);
            }

            setEditingUser(null);
            setTimeout(() => loadAdminData(), 200); 
        } catch (error: any) {
            const msg = error.response?.data?.detail || t('error.generic', 'Gabim.');
            alert(msg);
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

    const renderStatusBadge = (user: UnifiedAdminUser) => {
        const isExpired = user.expiry_date && user.expiry_date < new Date();

        if (user.status === 'pending_invite') {
            return <span className="flex items-center text-amber-400 bg-amber-400/10 px-2 py-1 rounded-lg text-xs font-bold w-fit border border-amber-500/20"><Mail className="w-3 h-3 mr-1" /> FTESË</span>;
        }
        if (user.subscription_status === 'ACTIVE') {
            if (isExpired) {
                return <span className="flex items-center text-red-400 bg-red-400/10 px-2 py-1 rounded-lg text-xs font-bold w-fit border border-red-500/20"><AlertTriangle className="w-3 h-3 mr-1" /> SKADUAR</span>;
            }
            return <span className="flex items-center text-green-400 bg-green-400/10 px-2 py-1 rounded-lg text-xs font-bold w-fit border border-green-500/20"><CheckCircle className="w-3 h-3 mr-1" /> AKTIV</span>;
        }
        return <span className="flex items-center text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded-lg text-xs font-bold w-fit border border-yellow-500/20"><Clock className="w-3 h-3 mr-1" /> PRITJE</span>;
    };

    const filteredUsers = users.filter(u =>
        u.username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.email?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <style>{`.dark-select { color-scheme: dark; } .react-datepicker-wrapper { width: 100%; }`}</style>
            
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">{t('admin.title')}</h1>
                <p className="text-gray-400">Juristi SaaS Administration: Features & Capacity</p>
            </div>

            <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge overflow-hidden">
                <div className="p-4 border-b border-glass-edge flex justify-between items-center bg-white/5">
                    <div className="flex items-center gap-2">
                        <Briefcase className="w-5 h-5 text-primary-start" />
                        <h3 className="text-lg font-semibold text-white">User Base</h3>
                    </div>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                        <input type="text" placeholder="Kërko..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 pr-4 py-2 bg-black/40 border border-white/10 rounded-lg text-sm text-white outline-none focus:ring-1 focus:ring-primary-start" />
                    </div>
                </div>

                <div className="w-full overflow-x-auto">
                    <table className="w-full text-left text-sm text-gray-400">
                        <thead className="bg-black/20 text-white uppercase text-xs font-bold">
                            <tr>
                                <th className="px-6 py-4">User</th>
                                <th className="px-6 py-4 text-center">Plan Type</th>
                                <th className="px-6 py-4">Feature Tier</th>
                                <th className="px-6 py-4">Capacity</th>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {filteredUsers.map((user) => (
                                <tr key={user.id} className="hover:bg-white/5 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="font-medium text-white">{user.username}</div>
                                        <div className="text-xs text-gray-500">{user.email}</div>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        {user.account_type === AccountType.ORGANIZATION ? <Building2 className="w-4 h-4 text-purple-400 mx-auto" /> : <UserIcon className="w-4 h-4 text-gray-500 mx-auto" />}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            {user.subscription_tier === SubscriptionTier.PRO ? <Zap className="w-3 h-3 text-yellow-400" /> : <Shield className="w-3 h-3 text-gray-500" />}
                                            <span className={`text-xs font-bold uppercase ${user.subscription_tier === SubscriptionTier.PRO ? 'text-yellow-400' : 'text-gray-400'}`}>
                                                {user.subscription_tier}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col gap-1">
                                            <div className="flex items-center gap-2">
                                                {user.product_plan === ProductPlan.TEAM_PLAN ? <Star className="w-3 h-3 text-amber-400" /> : <UserIcon className="w-3 h-3 text-gray-500" />}
                                                <span className={`text-xs font-bold ${user.product_plan === ProductPlan.TEAM_PLAN ? 'text-amber-400' : 'text-gray-400'}`}>
                                                    {user.product_plan} ({user.user_limit} Seats)
                                                </span>
                                            </div>
                                            {user.expiry_date && (
                                                <div className="flex items-center text-[10px] text-gray-500">
                                                    <CalendarIcon className="w-3 h-3 mr-1" /> {user.expiry_date.toLocaleDateString()}
                                                </div>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">{renderStatusBadge(user)}</td>
                                    <td className="px-6 py-4 text-right space-x-2 whitespace-nowrap">
                                        <button onClick={() => handleEditClick(user)} className="p-2 bg-blue-500/10 text-blue-400 rounded-lg border border-blue-500/20"><Edit2 className="w-4 h-4" /></button>
                                        <button onClick={() => handleDeleteUser(user.id)} className="p-2 bg-red-500/10 text-red-400 rounded-lg border border-red-500/20"><Trash2 className="w-4 h-4" /></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {editingUser && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="bg-[#1f2937] border border-white/10 p-6 rounded-2xl w-full max-w-lg shadow-2xl overflow-y-auto max-h-[90vh]">
                        <h3 className="text-xl font-bold text-white mb-6 border-b border-white/10 pb-4">Manage SaaS Profile: {editingUser.username}</h3>
                        <form onSubmit={handleUpdateUser} className="space-y-6">
                            
                            <div className="p-4 bg-yellow-500/5 rounded-xl border border-yellow-500/20 space-y-4">
                                <h4 className="text-xs font-bold text-yellow-400 uppercase tracking-widest flex items-center gap-2"><Zap size={14}/> Features & AI Access</h4>
                                <div>
                                    <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">Subscription Tier</label>
                                    <select value={editForm.subscription_tier} onChange={e => setEditForm({ ...editForm, subscription_tier: e.target.value as SubscriptionTier })} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none dark-select">
                                        <option value={SubscriptionTier.BASIC}>BASIC (Standard)</option>
                                        <option value={SubscriptionTier.PRO}>PRO (AI + Forensics)</option>
                                    </select>
                                </div>
                            </div>

                            <div className="p-4 bg-emerald-500/5 rounded-xl border border-emerald-500/20 space-y-4">
                                <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-widest flex items-center gap-2"><Star size={14}/> Capacity & Quotas</h4>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">Product Plan</label>
                                        <select value={editForm.product_plan} onChange={e => setEditForm({ ...editForm, product_plan: e.target.value as ProductPlan })} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none dark-select">
                                            <option value={ProductPlan.SOLO_PLAN}>SOLO (1 Seat)</option>
                                            <option value={ProductPlan.TEAM_PLAN}>TEAM (10 Seats)</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">Account Type</label>
                                        <select value={editForm.account_type} onChange={e => setEditForm({ ...editForm, account_type: e.target.value as AccountType })} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none dark-select">
                                            <option value={AccountType.SOLO}>Individual</option>
                                            <option value={AccountType.ORGANIZATION}>Firm/Organization</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            <div className="p-4 bg-white/5 rounded-xl border border-white/10 space-y-4">
                                <h4 className="text-xs font-bold text-primary-300 uppercase tracking-widest flex items-center gap-2"><Clock size={14}/> Lifecycle & Status</h4>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">Gatekeeper Status</label>
                                        <select value={editForm.subscription_status} onChange={e => setEditForm({ ...editForm, subscription_status: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none dark-select">
                                            <option value="ACTIVE">ACTIVE (Access Granted)</option>
                                            <option value="INACTIVE">INACTIVE (Access Denied)</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">Expiry Date</label>
                                        <DatePicker selected={editForm.expiry_date} onChange={(date) => setEditForm({ ...editForm, expiry_date: date })} className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white outline-none" placeholderText="No Expiry" dateFormat="dd/MM/yyyy" />
                                    </div>
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
                                <button type="button" onClick={() => setEditingUser(null)} className="px-4 py-2 text-gray-400 hover:text-white">Cancel</button>
                                <button type="submit" className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-lg font-bold shadow-lg">Save SaaS Profile</button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default AdminDashboardPage;