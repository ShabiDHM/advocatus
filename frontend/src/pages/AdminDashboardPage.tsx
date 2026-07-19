// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - ADMIN DASHBOARD V6.2 (TEAM PLAN SEAT LIMIT UPDATED TO 5)
// POLISH: Implemented mobile-friendly layout cards, integrated useLockBodyScroll hooks, and updated border tokens.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
    Search, Edit2, Trash2, CheckCircle, Loader2, Clock, 
    Briefcase, Calendar as CalendarIcon, 
    AlertTriangle, Building2, User as UserIcon, Star, Shield, Mail, Zap, Key
} from 'lucide-react';
import { motion } from 'framer-motion';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";
import { apiService } from '../services/api';
import { User, UpdateUserRequest } from '../data/types';
import { AccountType, SubscriptionTier, ProductPlan } from '../data/enums';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

type UnifiedAdminUser = User & { 
    firmName?: string; 
    expiry_date?: Date | null;
    plan_tier?: 'DEFAULT' | 'GROWTH';
    user_limit?: number;
};

type UserRole = 'ADMIN' | 'LAWYER' | 'CLIENT' | 'STANDARD';

const AdminDashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [users, setUsers] = useState<UnifiedAdminUser[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [editingUser, setEditingUser] = useState<UnifiedAdminUser | null>(null);

    const [editForm, setEditForm] = useState<Partial<UnifiedAdminUser> & { expiry_date?: Date | null }>({});

    // Prevent background scrolling while edit profile modal is open
    useLockBodyScroll(!!editingUser);

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
                user_limit: user.user_limit || (user.product_plan === ProductPlan.TEAM_PLAN ? 5 : 1) 
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
            const msg = error.response?.data?.detail || t('common.error_occurred');
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
            return <span className="flex items-center text-warning-start bg-warning-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-warning-start/20"><Mail className="w-3.5 h-3.5 mr-1" /> {t('admin.status.invite_pending', 'FTESË')}</span>;
        }
        if (user.subscription_status === 'ACTIVE') {
            if (isExpired) {
                return <span className="flex items-center text-danger-start bg-danger-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-danger-start/20"><AlertTriangle className="w-3.5 h-3.5 mr-1" /> {t('admin.status.expired', 'SKADUAR')}</span>;
            }
            return <span className="flex items-center text-success-start bg-success-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-success-start/20"><CheckCircle className="w-3.5 h-3.5 mr-1" /> {t('admin.status.active', 'AKTIV')}</span>;
        }
        return <span className="flex items-center text-warning-start bg-warning-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-warning-start/20"><Clock className="w-3.5 h-3.5 mr-1" /> {t('admin.status.pending', 'PRITJE')}</span>;
    };

    const filteredUsers = users.filter(u =>
        u.username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.email?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-canvas">
            <style>{`.dark-select { color-scheme: dark; } .react-datepicker-wrapper { width: 100%; }`}</style>
            
            <div className="mb-8 select-none">
                <h1 className="text-3xl font-bold text-text-primary mb-2">{t('admin.dashboard_title', 'Administrimi i Juristi.tech')}</h1>
                <p className="text-text-secondary">{t('admin.dashboard_subtitle', 'Menaxhimi i Funksioneve dhe Kapacitetit')}</p>
            </div>

            <div className="glass-panel rounded-2xl border border-main overflow-hidden bg-canvas">
                {/* Search Header Row */}
                <div className="p-4 border-b border-main flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-surface">
                    <div className="flex items-center gap-2 select-none h-11 sm:h-auto">
                        <Briefcase className="w-5 h-5 text-primary-start" />
                        <h3 className="text-base sm:text-lg font-bold text-text-primary">{t('admin.user_base_title', 'Baza e Përdoruesve')}</h3>
                    </div>
                    <div className="relative w-full sm:w-64 h-11 flex items-center">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                        <input 
                            type="text" 
                            placeholder={t('general.search_placeholder', 'Kërko...')} 
                            value={searchQuery} 
                            onChange={(e) => setSearchQuery(e.target.value)} 
                            className="w-full h-11 sm:h-9 pl-9 pr-4 bg-canvas border border-main rounded-xl text-sm text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all"
                        />
                    </div>
                </div>

                {/* Mobile view stacked cards layout */}
                <div className="grid grid-cols-1 gap-4 p-4 md:hidden">
                    {filteredUsers.length === 0 ? (
                        <div className="py-12 text-center text-text-secondary italic text-sm font-medium">Asnjë përdorues nuk u gjet.</div>
                    ) : (
                        filteredUsers.map((user) => (
                            <div key={user.id} className="glass-panel p-4 rounded-xl border border-main bg-surface/10 space-y-4">
                                <div className="flex items-start justify-between">
                                    <div className="min-w-0 flex-1 pr-2">
                                        <div className="font-bold text-text-primary text-base truncate">{user.username}</div>
                                        <div className="text-xs text-text-muted mt-0.5 truncate">{user.email}</div>
                                    </div>
                                    {renderStatusBadge(user)}
                                </div>
                                
                                <div className="space-y-2 text-xs text-text-secondary border-t border-b border-main py-3 select-none">
                                    <div className="flex items-center justify-between">
                                        <span className="text-text-muted">Lloji:</span>
                                        <span className="font-bold flex items-center gap-1">
                                            {user.account_type === AccountType.ORGANIZATION ? <Building2 className="w-3.5 h-3.5" /> : <UserIcon className="w-3.5 h-3.5" />}
                                            {user.account_type}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-text-muted">Abonimi:</span>
                                        <span className="font-bold uppercase flex items-center gap-1">
                                            {user.subscription_tier === SubscriptionTier.PRO ? <Zap className="w-3.5 h-3.5 text-warning-start animate-pulse" /> : <Shield className="w-3.5 h-3.5 text-text-muted" />}
                                            {user.subscription_tier}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <span className="text-text-muted">Kapaciteti:</span>
                                        <span className="font-bold">{user.product_plan} ({user.user_limit} Vende)</span>
                                    </div>
                                    {user.expiry_date && (
                                        <div className="flex items-center justify-between">
                                            <span className="text-text-muted">Skadimi:</span>
                                            <span className="font-mono">{user.expiry_date.toLocaleDateString()}</span>
                                        </div>
                                    )}
                                </div>

                                <div className="grid grid-cols-2 gap-3 pt-1">
                                    <button 
                                        type="button"
                                        onClick={() => handleEditClick(user)} 
                                        className="flex items-center justify-center gap-2 h-11 bg-primary-start/10 text-primary-start rounded-xl border border-primary-start/20 hover:bg-primary-start/20 transition-all font-bold text-xs uppercase focus:outline-none"
                                    >
                                        <Edit2 className="w-4 h-4" /> Ndrysho
                                    </button>
                                    <button 
                                        type="button"
                                        onClick={() => handleDeleteUser(user.id)} 
                                        className="flex items-center justify-center gap-2 h-11 bg-danger-start/10 text-danger-start rounded-xl border border-danger-start/20 hover:bg-danger-start/20 transition-all font-bold text-xs uppercase focus:outline-none"
                                    >
                                        <Trash2 className="w-4 h-4" /> Fshij
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>

                {/* Desktop view standard data table (hidden on mobile) */}
                <div className="w-full overflow-x-auto hidden md:block">
                    <table className="w-full text-left text-sm text-text-secondary">
                        <thead className="bg-surface text-text-primary uppercase text-xs font-bold border-b border-main select-none">
                            <tr>
                                <th className="px-6 py-4">{t('admin.table.user', 'Përdoruesi')}</th>
                                <th className="px-6 py-4 text-center">{t('admin.table.plan_type', 'Tipi i Planit')}</th>
                                <th className="px-6 py-4">{t('admin.table.feature_tier', 'Niveli i Funksioneve')}</th>
                                <th className="px-6 py-4">{t('admin.table.capacity', 'Kapaciteti')}</th>
                                <th className="px-6 py-4">{t('admin.table.status', 'Statusi')}</th>
                                <th className="px-6 py-4 text-right">{t('admin.table.actions', 'Veprime')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-main">
                            {filteredUsers.map((user) => (
                                <tr key={user.id} className="hover:bg-hover transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="font-bold text-text-primary">{user.username}</div>
                                        <div className="text-xs text-text-muted">{user.email}</div>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        {user.account_type === AccountType.ORGANIZATION ? <Building2 className="w-4 h-4 text-secondary-start mx-auto" /> : <UserIcon className="w-4 h-4 text-text-muted mx-auto" />}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            {user.subscription_tier === SubscriptionTier.PRO ? <Zap className="w-3 h-3 text-warning-start" /> : <Shield className="w-3 h-3 text-text-muted" />}
                                            <span className={`text-xs font-bold uppercase ${user.subscription_tier === SubscriptionTier.PRO ? 'text-warning-start' : 'text-text-muted'}`}>
                                                {user.subscription_tier}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col gap-1">
                                            <div className="flex items-center gap-2">
                                                {user.product_plan === ProductPlan.TEAM_PLAN ? <Star className="w-3 h-3 text-warning-start animate-pulse" /> : <UserIcon className="w-3 h-3 text-text-muted" />}
                                                <span className={`text-xs font-bold ${user.product_plan === ProductPlan.TEAM_PLAN ? 'text-warning-start' : 'text-text-muted'}`}>
                                                    {user.product_plan} ({user.user_limit} {t('admin.seats', 'Vende')})
                                                </span>
                                            </div>
                                            {user.expiry_date && (
                                                <div className="flex items-center text-[10px] text-text-muted font-mono">
                                                    <CalendarIcon className="w-3 h-3 mr-1" /> {user.expiry_date.toLocaleDateString()}
                                                </div>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">{renderStatusBadge(user)}</td>
                                    <td className="px-6 py-4 text-right space-x-2 whitespace-nowrap">
                                        <button 
                                            type="button"
                                            onClick={() => handleEditClick(user)} 
                                            className="p-2 bg-primary-start/10 text-primary-start rounded-lg border border-primary-start/20 hover:bg-primary-start/20 transition-colors focus:outline-none"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                        <button 
                                            type="button"
                                            onClick={() => handleDeleteUser(user.id)} 
                                            className="p-2 bg-danger-start/10 text-danger-start rounded-lg border border-danger-start/20 hover:bg-danger-start/20 transition-colors focus:outline-none"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Editing SaaS Profile Modal with lock prevented viewport scrolls */}
            {editingUser && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto custom-finance-scroll">
                    <motion.div 
                        initial={{ scale: 0.95, opacity: 0 }} 
                        animate={{ scale: 1, opacity: 1 }} 
                        className="glass-panel border border-main p-6 rounded-2xl w-full max-w-lg shadow-2xl overflow-y-auto max-h-[90vh] bg-canvas"
                    >
                        <h3 className="text-xl font-bold text-text-primary mb-6 border-b border-main pb-4 tracking-tight select-none">
                            {t('admin.manage_saas_profile', 'Menaxho Profilin SaaS')}: {editingUser.username}
                        </h3>
                        <form onSubmit={handleUpdateUser} className="space-y-6">
                            
                            {/* Role Management Section */}
                            <div className="p-4 bg-primary-start/5 rounded-xl border border-primary-start/20 space-y-4">
                                <h4 className="text-xs font-bold text-primary-start uppercase tracking-widest flex items-center gap-2 select-none">
                                    <Key size={14} /> {t('admin.section_role', 'Roli i Përdoruesit')}
                                </h4>
                                <div className="space-y-1.5">
                                    <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                        {t('admin.label_role', 'Roli')}
                                    </label>
                                    <select 
                                        value={editForm.role || 'STANDARD'} 
                                        onChange={e => setEditForm({ 
                                            ...editForm, 
                                            role: e.target.value as UserRole
                                        })} 
                                        className="w-full rounded-xl px-3 h-11 bg-surface border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                    >
                                        <option value="STANDARD" className="bg-canvas text-text-primary">{t('admin.option_role_standard', 'STANDARD (Përdorues i zakonshëm)')}</option>
                                        <option value="ADMIN" className="bg-canvas text-text-primary">{t('admin.option_role_admin', 'ADMIN (Administrator)')}</option>
                                    </select>
                                </div>
                            </div>

                            <div className="p-4 bg-warning-start/5 rounded-xl border border-warning-start/20 space-y-4">
                                <h4 className="text-xs font-bold text-warning-start uppercase tracking-widest flex items-center gap-2 select-none">
                                    <Zap size={14} /> {t('admin.section_features_ai', 'Funksionet & Aksesi AI')}
                                </h4>
                                <div className="space-y-1.5">
                                    <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                        {t('admin.label_subscription_tier', 'Niveli i Abonimit')}
                                    </label>
                                    <select 
                                        value={editForm.subscription_tier} 
                                        onChange={e => setEditForm({ ...editForm, subscription_tier: e.target.value as SubscriptionTier })} 
                                        className="w-full rounded-xl px-3 h-11 bg-surface border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                    >
                                        <option value={SubscriptionTier.BASIC} className="bg-canvas text-text-primary">{t('admin.option_tier_basic', 'BASIC (Standard)')}</option>
                                        <option value={SubscriptionTier.PRO} className="bg-canvas text-text-primary">{t('admin.option_tier_pro', 'PRO (AI + Forenzika)')}</option>
                                    </select>
                                </div>
                            </div>

                            <div className="p-4 bg-status-success/5 rounded-xl border border-status-success/20 space-y-4">
                                <h4 className="text-xs font-bold text-status-success uppercase tracking-widest flex items-center gap-2 select-none">
                                    <Star size={14} /> {t('admin.section_capacity_quotas', 'Kapaciteti & Kuotat')}
                                </h4>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            {t('admin.label_product_plan', 'Plani i Produktit')}
                                        </label>
                                        <select 
                                            value={editForm.product_plan} 
                                            onChange={e => setEditForm({ ...editForm, product_plan: e.target.value as ProductPlan })} 
                                            className="w-full rounded-xl px-3 h-11 bg-surface border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                        >
                                            <option value={ProductPlan.SOLO_PLAN} className="bg-canvas text-text-primary">{t('admin.option_plan_solo', 'SOLO (1 Vend)')}</option>
                                            <option value={ProductPlan.TEAM_PLAN} className="bg-canvas text-text-primary">{t('admin.option_plan_team', 'TEAM (5 Vende)')}</option>
                                        </select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            {t('admin.label_account_type', 'Tipi i Llogarisë')}
                                        </label>
                                        <select 
                                            value={editForm.account_type} 
                                            onChange={e => setEditForm({ ...editForm, account_type: e.target.value as AccountType })} 
                                            className="w-full rounded-xl px-3 h-11 bg-surface border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                        >
                                            <option value={AccountType.SOLO} className="bg-canvas text-text-primary">{t('admin.option_account_individual', 'Individual')}</option>
                                            <option value={AccountType.ORGANIZATION} className="bg-canvas text-text-primary">{t('admin.option_account_organization', 'Firmë/Organizatë')}</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            <div className="p-4 bg-surface border border-main space-y-4 rounded-xl">
                                <h4 className="text-xs font-bold text-primary-start uppercase tracking-widest flex items-center gap-2 select-none">
                                    <Clock size={14} /> {t('admin.section_lifecycle_status', 'Cikli i Jetës & Statusi')}
                                </h4>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            {t('admin.label_gatekeeper_status', 'Statusi i Gatekeeper')}
                                        </label>
                                        <select 
                                            value={editForm.subscription_status} 
                                            onChange={e => setEditForm({ ...editForm, subscription_status: e.target.value })} 
                                            className="w-full rounded-xl px-3 h-11 bg-canvas border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                        >
                                            <option value="ACTIVE" className="bg-canvas text-text-primary">{t('admin.option_status_active', 'ACTIVE (Akses i Lejuar)')}</option>
                                            <option value="INACTIVE" className="bg-canvas text-text-primary">{t('admin.option_status_inactive', 'INACTIVE (Akses i Refuzuar)')}</option>
                                        </select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            {t('admin.label_expiry_date', 'Data e Skadimit')}
                                        </label>
                                        <DatePicker 
                                            selected={editForm.expiry_date} 
                                            onChange={(date) => setEditForm({ ...editForm, expiry_date: date })} 
                                            className="w-full rounded-xl px-3 h-11 bg-canvas border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20" 
                                            placeholderText={t('admin.placeholder_no_expiry', 'Pa Skadim')} 
                                            dateFormat="dd/MM/yyyy" 
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-6 border-t border-main">
                                <button 
                                    type="button" 
                                    onClick={() => setEditingUser(null)} 
                                    className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-all focus:outline-none"
                                >
                                    {t('general.cancel', 'Anulo')}
                                </button>
                                <button 
                                    type="submit" 
                                    className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-bold bg-primary-start hover:bg-opacity-95 text-white shadow-lg shadow-primary-start/15 focus:outline-none"
                                >
                                    {t('admin.button_save_profile', 'Ruaj Profilin SaaS')}
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default AdminDashboardPage;